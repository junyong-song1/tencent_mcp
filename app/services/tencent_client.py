"""Tencent Cloud client service with async support."""
import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
    TencentCloudSDKException,
)
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.mdl.v20200326 import mdl_client, models as mdl_models
from tencentcloud.mdc.v20200828 import mdc_client, models as mdc_models

from app.config import get_settings
from app.models.enums import ChannelStatus

logger = logging.getLogger(__name__)


class TencentCloudClient:
    """Unified client for Tencent Cloud services."""

    def __init__(
        self,
        secret_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """Initialize Tencent Cloud SDK clients."""
        settings = get_settings()
        self._secret_id = secret_id or settings.TENCENT_SECRET_ID
        self._secret_key = secret_key or settings.TENCENT_SECRET_KEY
        self._region = region or settings.TENCENT_REGION
        self._cache_ttl = settings.CACHE_TTL_SECONDS
        self._timeout = settings.API_REQUEST_TIMEOUT
        self._max_workers = settings.THREAD_POOL_WORKERS

        self._linkage_cache: Dict = {}
        self._cache_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=self._max_workers)

        logger.info("TencentCloudClient initialized")

    def _get_mdc_client(self) -> mdc_client.MdcClient:
        """Get a thread-safe MDC client."""
        cred = credential.Credential(self._secret_id, self._secret_key)
        http_profile = HttpProfile()
        http_profile.reqTimeout = self._timeout
        client_profile = ClientProfile(httpProfile=http_profile)
        return mdc_client.MdcClient(cred, self._region, client_profile)

    def _get_mdl_client(self) -> mdl_client.MdlClient:
        """Get a thread-safe MDL client."""
        cred = credential.Credential(self._secret_id, self._secret_key)
        http_profile = HttpProfile()
        http_profile.reqTimeout = self._timeout
        client_profile = ClientProfile(httpProfile=http_profile)
        return mdl_client.MdlClient(cred, self._region, client_profile)

    def _normalize_mdl_status(self, state: str) -> str:
        """Normalize MediaLive status."""
        state_lower = str(state).lower()
        if "running" in state_lower or "start" in state_lower:
            return ChannelStatus.RUNNING.value
        elif "idle" in state_lower:
            return ChannelStatus.IDLE.value
        elif "stop" in state_lower:
            return ChannelStatus.STOPPED.value
        elif "error" in state_lower or "alert" in state_lower:
            return ChannelStatus.ERROR.value
        return ChannelStatus.UNKNOWN.value

    def _normalize_streamlink_status(self, state: str) -> str:
        """Normalize StreamLink status."""
        state_str = str(state).lower()
        if any(x in state_str for x in ["running", "start", "active", "online"]):
            return ChannelStatus.RUNNING.value
        elif any(x in state_str for x in ["idle", "wait"]):
            return ChannelStatus.IDLE.value
        elif any(x in state_str for x in ["stop", "off"]):
            return ChannelStatus.STOPPED.value
        elif any(x in state_str for x in ["error", "alert", "failed", "fail"]):
            return ChannelStatus.ERROR.value
        return ChannelStatus.UNKNOWN.value

    def list_mdl_channels(self) -> List[Dict]:
        """List StreamLive channels."""
        try:
            client = self._get_mdl_client()
            req = mdl_models.DescribeStreamLiveChannelsRequest()
            resp = client.DescribeStreamLiveChannels(req)
            info_list = resp.Infos if hasattr(resp, "Infos") else []

            cache_key = "mdl_batch_inputs"
            input_map = {}
            input_name_map = {}

            with self._cache_lock:
                cached = self._linkage_cache.get(cache_key)
                if cached and (time.time() - cached["timestamp"] < self._cache_ttl):
                    input_map = cached["data"]
                    input_name_map = cached.get("name_map", {})

            if not input_map:
                try:
                    inp_req = mdl_models.DescribeStreamLiveInputsRequest()
                    inp_resp = client.DescribeStreamLiveInputs(inp_req)
                    all_inputs = inp_resp.Infos if hasattr(inp_resp, "Infos") else []

                    for inp in all_inputs:
                        endpoints = []
                        settings = getattr(inp, "InputSettings", [])
                        for sett in settings:
                            addr = getattr(sett, "InputAddress", "")
                            app = getattr(sett, "AppName", "")
                            stream = getattr(sett, "StreamName", "")
                            src_url = getattr(sett, "SourceUrl", "")

                            if addr and app and stream:
                                endpoints.append(f"{addr}/{app}/{stream}")
                            elif addr:
                                endpoints.append(addr)
                            if src_url:
                                endpoints.append(src_url)

                        if not endpoints and hasattr(inp, "InputAddressList"):
                            for addr_info in getattr(inp, "InputAddressList", []):
                                ip = getattr(addr_info, "Ip", "")
                                if ip:
                                    endpoints.append(ip)

                        inp_id = str(getattr(inp, "Id", "")).strip()
                        if inp_id:
                            input_map[inp_id] = list(set(endpoints))
                            input_name = getattr(inp, "Name", "")
                            if input_name:
                                input_name_map[inp_id] = input_name

                    with self._cache_lock:
                        self._linkage_cache[cache_key] = {
                            "data": input_map,
                            "name_map": input_name_map,
                            "timestamp": time.time(),
                        }
                except Exception as e:
                    logger.error(f"Failed to fetch batch inputs: {e}")

            channels = []
            for info in info_list:
                ch_id = getattr(info, "Id", "")
                ch_name = getattr(info, "Name", "Unknown Channel")
                ch_state = getattr(info, "State", "unknown")
                attached_inputs = getattr(info, "AttachedInputs", [])

                input_endpoints = []
                input_details = []
                for att in attached_inputs:
                    att_id = str(getattr(att, "Id", att)).strip()
                    if att_id in input_map:
                        input_endpoints.extend(input_map[att_id])

                    input_name = getattr(att, "Name", "")
                    if not input_name and att_id in input_name_map:
                        input_name = input_name_map[att_id]
                    if not input_name:
                        input_name = att_id

                    input_details.append({"id": att_id, "name": input_name})

                channels.append({
                    "id": ch_id,
                    "name": ch_name,
                    "status": self._normalize_mdl_status(ch_state),
                    "service": "StreamLive",
                    "type": "channel",
                    "input_attachments": input_details,
                    "input_endpoints": list(set(input_endpoints)),
                })

            return channels

        except Exception as e:
            logger.error(f"Failed to list MediaLive channels: {e}")
            return []

    def _fetch_single_flow_detail(self, flow_id: str) -> Dict:
        """Fetch detailed flow info."""
        try:
            time.sleep(0.05)
            client = self._get_mdc_client()
            req = mdc_models.DescribeStreamLinkFlowRequest()
            req.FlowId = flow_id
            resp = client.DescribeStreamLinkFlow(req)

            if hasattr(resp, "Info"):
                info = resp.Info
                output_urls = []

                if hasattr(info, "OutputGroup"):
                    for og in info.OutputGroup:
                        protocol = getattr(og, "Protocol", "")
                        if protocol == "RTMP_PULL":
                            continue

                        if protocol == "RTMP" or "streamlive" in getattr(og, "OutputName", "").lower():
                            if hasattr(og, "RTMPSettings") and og.RTMPSettings:
                                dests = getattr(og.RTMPSettings, "Destinations", [])
                                for d in dests:
                                    url = getattr(d, "Url", "")
                                    key = getattr(d, "StreamKey", "")
                                    if url and key:
                                        full_url = url + ("/" if not url.endswith("/") else "") + key
                                        output_urls.append(full_url)
                                    elif url:
                                        output_urls.append(url)

                input_group = getattr(info, "InputGroup", [])
                input_details = []
                for inp in input_group:
                    input_details.append({
                        "id": getattr(inp, "InputId", ""),
                        "name": getattr(inp, "InputName", "") or getattr(inp, "InputId", "") or "Unknown",
                        "protocol": getattr(inp, "Protocol", ""),
                    })

                return {
                    "id": flow_id,
                    "output_urls": output_urls,
                    "status": self._normalize_streamlink_status(getattr(info, "State", "unknown")),
                    "inputs_count": len(input_group),
                    "input_details": input_details,
                }

        except Exception as e:
            logger.error(f"Failed to fetch detail for {flow_id}: {e}")

        return {"id": flow_id, "output_urls": [], "status": "unknown", "inputs_count": 0, "input_details": []}

    def list_streamlink_inputs(self) -> List[Dict]:
        """List StreamLink flows."""
        try:
            client = self._get_mdc_client()
            req = mdc_models.DescribeStreamLinkFlowsRequest()
            req.PageNum = 1
            req.PageSize = 100
            resp = client.DescribeStreamLinkFlows(req)
            summary_list = resp.Infos if hasattr(resp, "Infos") else []

            flow_details = {}
            cache_key = "mdc_linkage_details"
            need_fetch = True

            with self._cache_lock:
                cached = self._linkage_cache.get(cache_key)
                if cached and (time.time() - cached["timestamp"] < self._cache_ttl):
                    flow_details = cached["data"]
                    summary_ids = set(f.FlowId for f in summary_list)
                    if summary_ids.issubset(set(flow_details.keys())):
                        need_fetch = False

            if need_fetch:
                ids = [f.FlowId for f in summary_list]
                results = list(self.executor.map(self._fetch_single_flow_detail, ids))
                flow_details = {res["id"]: res for res in results}
                with self._cache_lock:
                    self._linkage_cache[cache_key] = {"data": flow_details, "timestamp": time.time()}

            inputs = []
            for info in summary_list:
                flow_id = getattr(info, "FlowId", "")
                detail = flow_details.get(flow_id, {})

                inputs.append({
                    "id": flow_id,
                    "name": getattr(info, "FlowName", "Unknown Flow"),
                    "status": detail.get("status", self._normalize_streamlink_status(getattr(info, "State", "unknown"))),
                    "service": "StreamLink",
                    "type": "flow",
                    "output_urls": detail.get("output_urls", []),
                    "input_attachments": detail.get("input_details", []),
                })

            logger.info(f"Found {len(inputs)} StreamLink resources")
            return inputs

        except Exception as e:
            logger.error(f"Failed to list StreamLink flows: {e}")
            return []

    def list_all_resources(self) -> List[Dict]:
        """List all resources across all services."""
        all_resources = []

        f_mdl = self.executor.submit(self.list_mdl_channels)
        f_link = self.executor.submit(self.list_streamlink_inputs)

        mdl_channels = f_mdl.result()
        link_resources = f_link.result()

        all_resources.extend(mdl_channels)
        all_resources.extend(link_resources)

        logger.info(f"Total resources found: {len(all_resources)}")
        return all_resources

    def start_mdl_channel(self, channel_id: str) -> Dict:
        """Start MediaLive channel."""
        try:
            client = self._get_mdl_client()
            req = mdl_models.StartStreamLiveChannelRequest()
            req.Id = channel_id
            client.StartStreamLiveChannel(req)
            return {"success": True, "message": "MediaLive channel started successfully"}
        except TencentCloudSDKException as e:
            logger.error(f"Failed to start MediaLive channel: {e}")
            return {"success": False, "message": str(e)}

    def stop_mdl_channel(self, channel_id: str) -> Dict:
        """Stop MediaLive channel."""
        try:
            client = self._get_mdl_client()
            req = mdl_models.StopStreamLiveChannelRequest()
            req.Id = channel_id
            client.StopStreamLiveChannel(req)
            return {"success": True, "message": "MediaLive channel stopped successfully"}
        except TencentCloudSDKException as e:
            logger.error(f"Failed to stop MediaLive channel: {e}")
            return {"success": False, "message": str(e)}

    def start_streamlink_input(self, input_id: str) -> Dict:
        """Start StreamLink flow."""
        try:
            client = self._get_mdc_client()
            client.call_json("StartStreamLinkFlow", {"FlowId": input_id})
            return {"success": True, "message": "StreamLink flow started successfully"}
        except TencentCloudSDKException as e:
            logger.error(f"Failed to start StreamLink flow: {e}")
            return {"success": False, "message": str(e)}

    def stop_streamlink_input(self, input_id: str) -> Dict:
        """Stop StreamLink flow."""
        try:
            client = self._get_mdc_client()
            client.call_json("StopStreamLinkFlow", {"FlowId": input_id})
            return {"success": True, "message": "StreamLink flow stopped successfully"}
        except TencentCloudSDKException as e:
            logger.error(f"Failed to stop StreamLink flow: {e}")
            return {"success": False, "message": str(e)}

    def control_resource(self, resource_id: str, service: str, action: str) -> Dict:
        """Control a resource (start/stop/restart)."""
        if service in ["StreamLive", "MediaLive"]:
            if action == "start":
                return self.start_mdl_channel(resource_id)
            elif action == "stop":
                return self.stop_mdl_channel(resource_id)
            elif action == "restart":
                stop_result = self.stop_mdl_channel(resource_id)
                if stop_result["success"]:
                    return self.start_mdl_channel(resource_id)
                return stop_result

        elif service in ["StreamLink", "MediaConnect"]:
            if action == "start":
                return self.start_streamlink_input(resource_id)
            elif action == "stop":
                return self.stop_streamlink_input(resource_id)
            elif action == "restart":
                stop_result = self.stop_streamlink_input(resource_id)
                if stop_result["success"]:
                    return self.start_streamlink_input(resource_id)
                return stop_result

        return {"success": False, "message": f"Action {action} not supported for {service}"}

    def get_resource_details(self, resource_id: str, service: str) -> Optional[Dict]:
        """Get detailed information about a resource."""
        try:
            if service in ["StreamLive", "MediaLive"]:
                client = self._get_mdl_client()
                req = mdl_models.DescribeStreamLiveChannelRequest()
                req.Id = resource_id
                resp = client.DescribeStreamLiveChannel(req)
                info = resp.Info

                input_details = []
                for att in getattr(info, "AttachedInputs", []):
                    att_id = str(getattr(att, "Id", att)).strip()
                    input_details.append({
                        "id": att_id,
                        "name": getattr(att, "Name", "") or att_id,
                    })

                return {
                    "id": info.Id,
                    "name": info.Name,
                    "status": self._normalize_mdl_status(info.State),
                    "service": "StreamLive",
                    "type": "channel",
                    "input_attachments": input_details,
                }

            elif service in ["StreamLink", "MediaConnect"]:
                client = self._get_mdc_client()
                req = mdc_models.DescribeStreamLinkFlowRequest()
                req.FlowId = resource_id
                resp = client.DescribeStreamLinkFlow(req)

                if hasattr(resp, "Info"):
                    info = resp.Info
                    input_group = getattr(info, "InputGroup", [])
                    input_details = []
                    for inp in input_group:
                        input_details.append({
                            "id": getattr(inp, "InputId", ""),
                            "name": getattr(inp, "InputName", "") or getattr(inp, "InputId", "") or "Unknown",
                            "protocol": getattr(inp, "Protocol", ""),
                        })

                    return {
                        "id": getattr(info, "FlowId", resource_id),
                        "name": getattr(info, "FlowName", ""),
                        "status": self._normalize_streamlink_status(getattr(info, "State", "")),
                        "service": "StreamLink",
                        "type": "flow",
                        "input_group": input_details,
                    }

        except Exception as e:
            logger.error(f"Failed to get resource details: {e}")

        return None

    def prewarm_cache(self) -> None:
        """Pre-warm linkage caches in background."""
        logger.info("Pre-warming Tencent Cloud linkage cache...")
        self.executor.submit(self.list_all_resources)

    def clear_cache(self) -> None:
        """Clear all caches."""
        with self._cache_lock:
            self._linkage_cache.clear()
        logger.info("Linkage cache cleared")

    def search_resources(self, keywords: List[str]) -> List[Dict]:
        """Search resources by keywords."""
        all_resources = self.list_all_resources()

        if not keywords:
            return all_resources

        filtered = []
        for resource in all_resources:
            name = resource.get("name", "").lower()
            if any(keyword.lower() in name for keyword in keywords):
                filtered.append(resource)

        return filtered


class AsyncTencentClient:
    """Async wrapper for TencentCloudClient."""

    def __init__(self, sync_client: Optional[TencentCloudClient] = None):
        self._sync = sync_client or TencentCloudClient()

    async def list_all_resources(self) -> List[Dict]:
        return await asyncio.to_thread(self._sync.list_all_resources)

    async def list_mdl_channels(self) -> List[Dict]:
        return await asyncio.to_thread(self._sync.list_mdl_channels)

    async def list_streamlink_inputs(self) -> List[Dict]:
        return await asyncio.to_thread(self._sync.list_streamlink_inputs)

    async def control_resource(self, resource_id: str, service: str, action: str) -> Dict:
        return await asyncio.to_thread(self._sync.control_resource, resource_id, service, action)

    async def get_resource_details(self, resource_id: str, service: str) -> Optional[Dict]:
        return await asyncio.to_thread(self._sync.get_resource_details, resource_id, service)

    async def search_resources(self, keywords: List[str]) -> List[Dict]:
        return await asyncio.to_thread(self._sync.search_resources, keywords)

    def clear_cache(self) -> None:
        self._sync.clear_cache()

    def prewarm_cache(self) -> None:
        self._sync.prewarm_cache()
