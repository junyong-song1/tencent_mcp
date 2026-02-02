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

# Optional imports for StreamPackage and CSS
# StreamPackage uses MDP (Media Distribution Platform) SDK, not MSP
try:
    from tencentcloud.mdp.v20200527 import mdp_client, models as mdp_models
    STREAMPACKAGE_AVAILABLE = True
except ImportError:
    STREAMPACKAGE_AVAILABLE = False
    logger.debug("StreamPackage SDK (MDP) not available. Install with: pip install tencentcloud-sdk-python-mdp")

try:
    from tencentcloud.live.v20180801 import live_client, models as live_models
    CSS_AVAILABLE = True
except ImportError:
    CSS_AVAILABLE = False
    logger.debug("CSS SDK (Live) not available")


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

        # Pre-create SDK clients for reuse (thread-safe)
        self._cred = credential.Credential(self._secret_id, self._secret_key)
        self._http_profile = HttpProfile()
        self._http_profile.reqTimeout = self._timeout
        self._client_profile = ClientProfile(httpProfile=self._http_profile)

        # Cached client instances
        self._mdc_client: Optional[mdc_client.MdcClient] = None
        self._mdl_client: Optional[mdl_client.MdlClient] = None
        self._mdp_client = None
        self._css_client = None
        self._client_init_lock = threading.Lock()

        logger.info("TencentCloudClient initialized")

    def _get_mdc_client(self) -> mdc_client.MdcClient:
        """Get cached MDC client (thread-safe)."""
        if self._mdc_client is None:
            with self._client_init_lock:
                if self._mdc_client is None:
                    self._mdc_client = mdc_client.MdcClient(
                        self._cred, self._region, self._client_profile
                    )
        return self._mdc_client

    def _get_mdl_client(self) -> mdl_client.MdlClient:
        """Get cached MDL client (thread-safe)."""
        if self._mdl_client is None:
            with self._client_init_lock:
                if self._mdl_client is None:
                    self._mdl_client = mdl_client.MdlClient(
                        self._cred, self._region, self._client_profile
                    )
        return self._mdl_client

    def _get_mdp_client(self):
        """Get cached MDP (StreamPackage) client (thread-safe)."""
        if not STREAMPACKAGE_AVAILABLE:
            return None
        if self._mdp_client is None:
            with self._client_init_lock:
                if self._mdp_client is None:
                    http_profile = HttpProfile()
                    http_profile.reqTimeout = self._timeout
                    http_profile.endpoint = "mdp.intl.tencentcloudapi.com"
                    client_profile = ClientProfile(httpProfile=http_profile)
                    self._mdp_client = mdp_client.MdpClient(
                        self._cred, self._region, client_profile
                    )
        return self._mdp_client

    def _get_css_client(self):
        """Get cached CSS (Live) client (thread-safe)."""
        if not CSS_AVAILABLE:
            return None
        if self._css_client is None:
            with self._client_init_lock:
                if self._css_client is None:
                    self._css_client = live_client.LiveClient(
                        self._cred, self._region, self._client_profile
                    )
        return self._css_client

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
        """List StreamLink flows with incremental detail fetching."""
        try:
            client = self._get_mdc_client()
            req = mdc_models.DescribeStreamLinkFlowsRequest()
            req.PageNum = 1
            req.PageSize = 100
            resp = client.DescribeStreamLinkFlows(req)
            summary_list = resp.Infos if hasattr(resp, "Infos") else []

            cache_key = "mdc_linkage_details"
            flow_details = {}
            ids_to_fetch = []

            with self._cache_lock:
                cached = self._linkage_cache.get(cache_key)
                if cached:
                    flow_details = cached.get("data", {}).copy()

            # Find which flows need detail fetching (new or not in cache)
            for f in summary_list:
                flow_id = f.FlowId
                if flow_id not in flow_details:
                    ids_to_fetch.append(flow_id)

            # Only fetch details for new/missing flows
            if ids_to_fetch:
                logger.info(f"Fetching details for {len(ids_to_fetch)} new flows (skipping {len(summary_list) - len(ids_to_fetch)} cached)")
                results = list(self.executor.map(self._fetch_single_flow_detail, ids_to_fetch))
                for res in results:
                    flow_details[res["id"]] = res

                with self._cache_lock:
                    self._linkage_cache[cache_key] = {"data": flow_details, "timestamp": time.time()}
            else:
                logger.debug(f"All {len(summary_list)} flows found in cache")

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

    def _fetch_all_resources_sync(self) -> List[Dict]:
        """Fetch all resources (internal, no cache)."""
        all_resources = []

        f_mdl = self.executor.submit(self.list_mdl_channels)
        f_link = self.executor.submit(self.list_streamlink_inputs)

        mdl_channels = f_mdl.result()
        link_resources = f_link.result()

        all_resources.extend(mdl_channels)
        all_resources.extend(link_resources)

        return all_resources

    def list_all_resources(self, force_refresh: bool = False) -> List[Dict]:
        """List all resources with stale-while-revalidate caching.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of all resources (may be stale if background refresh is in progress)
        """
        cache_key = "all_resources"
        stale_ttl = self._cache_ttl  # 120s - after this, trigger background refresh
        max_ttl = self._cache_ttl * 5  # 600s - after this, force synchronous refresh

        with self._cache_lock:
            cached = self._linkage_cache.get(cache_key)

        now = time.time()

        # Force refresh requested
        if force_refresh:
            cached = None

        # No cache or cache too old - synchronous fetch required
        if not cached or (now - cached["timestamp"] > max_ttl):
            all_resources = self._fetch_all_resources_sync()
            with self._cache_lock:
                self._linkage_cache[cache_key] = {
                    "data": all_resources,
                    "timestamp": now,
                    "refreshing": False,
                }
            logger.info(f"Total resources found: {len(all_resources)} (fresh)")
            return all_resources

        # Cache exists - check if stale
        cache_age = now - cached["timestamp"]
        is_stale = cache_age > stale_ttl
        is_refreshing = cached.get("refreshing", False)

        # If stale and not already refreshing, trigger background refresh
        if is_stale and not is_refreshing:
            with self._cache_lock:
                self._linkage_cache[cache_key]["refreshing"] = True

            def background_refresh():
                try:
                    fresh_data = self._fetch_all_resources_sync()
                    with self._cache_lock:
                        self._linkage_cache[cache_key] = {
                            "data": fresh_data,
                            "timestamp": time.time(),
                            "refreshing": False,
                        }
                    logger.info(f"Background refresh complete: {len(fresh_data)} resources")
                except Exception as e:
                    logger.error(f"Background refresh failed: {e}")
                    with self._cache_lock:
                        if cache_key in self._linkage_cache:
                            self._linkage_cache[cache_key]["refreshing"] = False

            self.executor.submit(background_refresh)
            logger.debug(f"Returning stale cache ({cache_age:.1f}s old), background refresh started")

        # Return cached data immediately
        result = cached["data"]
        logger.info(f"Total resources found: {len(result)} (cached, {cache_age:.1f}s old)")
        return result

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

    def _get_streampackage_input_status(self, streampackage_id: str) -> Optional[Dict]:
        """
        Get StreamPackage channel input status (main/backup).
        
        Returns:
            Dict with active_input (main/backup) and input details
        """
        if not STREAMPACKAGE_AVAILABLE:
            return None
        
        try:
            client = self._get_mdp_client()
            if not client:
                return None
            
            # Describe StreamPackage channel
            req = mdp_models.DescribeStreamPackageChannelRequest()
            req.Id = streampackage_id
            
            resp = client.DescribeStreamPackageChannel(req)
            if not hasattr(resp, "Info"):
                return None
            
            info = resp.Info
            
            # Check Points.Inputs (input URLs for primary and backup)
            points = getattr(info, "Points", None)
            input_urls = []
            if points:
                inputs = getattr(points, "Inputs", [])
                for inp in inputs:
                    inp_url = getattr(inp, "Url", "")
                    if inp_url:
                        input_urls.append(inp_url)
            
            # Also check InputSettings if available
            input_settings = getattr(info, "InputSettings", [])
            input_details = []
            
            # Use InputSettings if available, otherwise use Points.Inputs
            if input_settings:
                for idx, inp_setting in enumerate(input_settings):
                    inp_id = getattr(inp_setting, "InputId", "")
                    inp_name = getattr(inp_setting, "InputName", "") or f"Input{idx+1}"
                    inp_url = getattr(inp_setting, "InputUrl", "") or (input_urls[idx] if idx < len(input_urls) else "")
                    
                    input_details.append({
                        "id": inp_id,
                        "name": inp_name,
                        "url": inp_url,
                    })
            else:
                # Use Points.Inputs directly if InputSettings is not available
                for idx, inp_url in enumerate(input_urls):
                    input_details.append({
                        "id": f"input_{idx+1}",
                        "name": f"Input{idx+1}",
                        "url": inp_url,
                    })
            
            # StreamPackage API doesn't directly tell which input is active
            # But we can infer from the input URLs and order
            # First input is typically primary/main, second is backup
            active_input_type = None
            active_input_id = None
            
            if input_details:
                # If only one input has URL, that's the active one
                active_inputs = [inp for inp in input_details if inp.get("url")]
                if len(active_inputs) == 1:
                    active_input = active_inputs[0]
                    active_input_id = active_input["id"]
                    inp_name = active_input["name"].lower()
                    if "backup" in inp_name or "_b" in inp_name:
                        active_input_type = "backup"
                    else:
                        active_input_type = "main"
                elif len(active_inputs) > 1:
                    # Multiple inputs - first is typically main
                    active_input = active_inputs[0]
                    active_input_id = active_input["id"]
                    active_input_type = "main"
            
            return {
                "streampackage_id": streampackage_id,
                "active_input": active_input_type,
                "active_input_id": active_input_id,
                "input_details": input_details,
            }
            
        except Exception as e:
            logger.debug(f"Could not get StreamPackage input status: {e}")
            return None

    def _get_css_stream_status(self, stream_name: str, domain: str = None) -> Optional[Dict]:
        """
        Get CSS stream status to verify which origin is active.
        
        Args:
            stream_name: Stream name (app/stream format)
            domain: CSS domain (optional)
        
        Returns:
            Dict with stream status and origin information
        """
        if not CSS_AVAILABLE:
            return None
        
        try:
            client = self._get_css_client()
            if not client:
                return None
            
            # DescribeLiveStreamState to check if stream is active
            req = live_models.DescribeLiveStreamStateRequest()
            if domain:
                req.DomainName = domain
            
            # Parse stream name (format: app/stream)
            parts = stream_name.split("/")
            if len(parts) >= 2:
                req.AppName = parts[0]
                req.StreamName = "/".join(parts[1:])
            else:
                req.StreamName = stream_name
            
            resp = client.DescribeLiveStreamState(req)
            
            stream_state = getattr(resp, "StreamState", "")
            is_active = stream_state in ["active", "ACTIVE"]
            
            return {
                "stream_name": stream_name,
                "stream_state": stream_state,
                "is_active": is_active,
            }
            
        except Exception as e:
            logger.debug(f"Could not get CSS stream status: {e}")
            return None

    def _get_active_pipeline_from_logs(self, channel_id: str, hours: int = 24) -> Optional[Dict]:
        """
        Get active pipeline (main/backup) from channel logs.

        Checks PipelineFailover and PipelineRecover events to determine
        which pipeline is currently serving.

        Args:
            channel_id: StreamLive channel ID
            hours: How many hours of logs to check (default: 24)

        Returns:
            Dict with:
                - active_pipeline: "main" or "backup"
                - last_event_type: Last failover-related event type
                - last_event_time: Timestamp of last event
                - failover_count: Number of failovers in the period
        """
        try:
            from datetime import datetime, timedelta, timezone

            client = self._get_mdl_client()

            log_req = mdl_models.DescribeStreamLiveChannelLogsRequest()
            log_req.ChannelId = channel_id
            log_req.StartTime = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
            log_req.EndTime = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            log_resp = client.DescribeStreamLiveChannelLogs(log_req)

            if not log_resp.Infos:
                return {
                    "active_pipeline": "main",  # Default to main if no logs
                    "last_event_type": None,
                    "last_event_time": None,
                    "failover_count": 0,
                    "message": "로그 없음 - 기본값(main) 사용",
                }

            infos = log_resp.Infos

            # Collect failover events from both pipelines
            failover_events = []

            for pipeline_attr in ['Pipeline0', 'Pipeline1']:
                pipeline_logs = getattr(infos, pipeline_attr, None)
                if not pipeline_logs:
                    continue

                logs = pipeline_logs if isinstance(pipeline_logs, list) else [pipeline_logs]
                for log in logs:
                    log_type = getattr(log, 'Type', '')
                    log_time = getattr(log, 'Time', '')

                    # Only interested in failover-related events
                    if log_type in ['PipelineFailover', 'PipelineRecover']:
                        failover_events.append({
                            'type': log_type,
                            'time': log_time,
                            'pipeline': pipeline_attr,
                        })

            if not failover_events:
                return {
                    "active_pipeline": "main",  # Default to main if no failover events
                    "last_event_type": None,
                    "last_event_time": None,
                    "failover_count": 0,
                    "message": "Failover 이벤트 없음 - main으로 서비스 중",
                }

            # Sort by time (most recent first)
            failover_events.sort(key=lambda x: x['time'], reverse=True)

            # Count failovers
            failover_count = sum(1 for e in failover_events if e['type'] == 'PipelineFailover')

            # Determine active pipeline from the most recent event
            last_event = failover_events[0]
            last_event_type = last_event['type']
            last_event_time = last_event['time']

            # Logic:
            # - PipelineFailover (most recent) → backup is active
            # - PipelineRecover (most recent) → main is active
            if last_event_type == 'PipelineFailover':
                active_pipeline = "backup"
                message = f"PipelineFailover 발생 ({last_event_time}) - backup으로 서비스 중"
            else:  # PipelineRecover
                active_pipeline = "main"
                message = f"PipelineRecover 완료 ({last_event_time}) - main으로 서비스 중"

            logger.info(f"Channel {channel_id}: {message}")

            return {
                "active_pipeline": active_pipeline,
                "last_event_type": last_event_type,
                "last_event_time": last_event_time,
                "failover_count": failover_count,
                "all_events": failover_events[:10],  # Keep last 10 events for reference
                "message": message,
            }

        except Exception as e:
            logger.warning(f"Could not get active pipeline from logs for channel {channel_id}: {e}")
            return None

    def get_channel_input_status(self, channel_id: str) -> Optional[Dict]:
        """
        Get active input status (main/backup) for a StreamLive channel.
        
        Returns:
            Dict with active_input (main/backup), input_details, and failover_info
        """
        try:
            client = self._get_mdl_client()
            
            # 1. Get channel details with failover settings and StreamPackage connection
            channel_req = mdl_models.DescribeStreamLiveChannelRequest()
            channel_req.Id = channel_id
            channel_resp = client.DescribeStreamLiveChannel(channel_req)
            info = channel_resp.Info
            
            attached_inputs = getattr(info, "AttachedInputs", [])
            if not attached_inputs:
                return {
                    "channel_id": channel_id,
                    "channel_name": getattr(info, "Name", ""),
                    "active_input": None,
                    "message": "연결된 입력이 없습니다.",
                }
            
            # Get StreamPackage ID from OutputGroups
            streampackage_id = None
            if hasattr(info, "OutputGroups") and info.OutputGroups:
                for og in info.OutputGroups:
                    if hasattr(og, "StreamPackageSettings"):
                        sp_settings = og.StreamPackageSettings
                        streampackage_id = getattr(sp_settings, "Id", None)
                        if streampackage_id:
                            break
            
            # Extract input details and failover settings
            input_details = []
            primary_input_id = None
            secondary_input_id = None
            failover_loss_threshold = None
            failover_recover_behavior = None
            
            for att in attached_inputs:
                att_id = str(getattr(att, "Id", att)).strip()
                att_name = getattr(att, "Name", "") or att_id
                
                # Check for failover settings
                failover_settings = getattr(att, "FailOverSettings", None)
                if failover_settings:
                    secondary_id = getattr(failover_settings, "SecondaryInputId", "")
                    if secondary_id:
                        secondary_input_id = str(secondary_id).strip()
                        if failover_loss_threshold is None:
                            failover_loss_threshold = getattr(failover_settings, "LossThreshold", None)
                        if failover_recover_behavior is None:
                            failover_recover_behavior = getattr(failover_settings, "RecoverBehavior", None)
                
                input_details.append({
                    "id": att_id,
                    "name": att_name,
                    "is_primary": True,  # First attached input is typically primary
                })
                
                if primary_input_id is None:
                    primary_input_id = att_id
            
            # 2. Use QueryInputStreamState to determine active input/source (PRIMARY METHOD - MOST RELIABLE)
            # This API directly returns which source addresses are active (Status == 1)
            active_input_id = None
            active_source_address = None  # Track which source address is active (for Input Source Redundancy)
            input_states = {}
            source_status_by_input = {}  # Map input_id -> {source_address: status, type: main/backup}
            
            try:
                input_ids = [inp["id"] for inp in input_details]
                for inp_id in input_ids:
                    try:
                        query_req = mdl_models.QueryInputStreamStateRequest()
                        query_req.Id = inp_id  # Only Id parameter is required (not ChannelId + InputId)
                        
                        query_resp = client.QueryInputStreamState(query_req)
                        
                        if hasattr(query_resp, "Info") and query_resp.Info:
                            info_obj = query_resp.Info
                            
                            # Get InputStreamInfoList from Info
                            if hasattr(info_obj, "InputStreamInfoList") and info_obj.InputStreamInfoList:
                                stream_infos = info_obj.InputStreamInfoList
                                
                                active_sources = []
                                for stream_info in stream_infos:
                                    input_address = getattr(stream_info, "InputAddress", "")
                                    app_name = getattr(stream_info, "AppName", "")
                                    stream_name = getattr(stream_info, "StreamName", "")
                                    status = getattr(stream_info, "Status", 0)
                                    
                                    # Determine source type from address
                                    source_type = None
                                    if "ap-seoul-1" in input_address.lower():
                                        source_type = "main"
                                    elif "ap-seoul-2" in input_address.lower():
                                        source_type = "backup"
                                    
                                    # Build full URL
                                    full_url = f"{input_address}/{app_name}/{stream_name}" if input_address else ""
                                    
                                    if status == 1:  # Status 1 means active
                                        active_sources.append({
                                            "address": input_address,
                                            "url": full_url,
                                            "type": source_type,
                                            "status": status
                                        })
                                        
                                        # Set active input and source address
                                        if not active_input_id:
                                            active_input_id = inp_id
                                            active_source_address = full_url
                                        
                                        logger.info(f"QueryInputStreamState: Input {inp_id} has active source {source_type} at {input_address}")
                                
                                # Store source status information
                                source_status_by_input[inp_id] = {
                                    "active_sources": active_sources,
                                    "input_id": inp_id,
                                    "input_name": getattr(info_obj, "InputName", ""),
                                    "protocol": getattr(info_obj, "Protocol", "")
                                }
                                
                                # If we found active sources, we can break (found the active input)
                                if active_sources:
                                    input_states[inp_id] = input_states.get(inp_id, {})
                                    input_states[inp_id]["status"] = 1
                                    input_states[inp_id]["is_active"] = True
                                    input_states[inp_id]["active_sources"] = active_sources
                                    
                                    # Use first active source as primary
                                    if active_sources:
                                        primary_source = active_sources[0]
                                        active_source_address = primary_source["url"]
                                        
                    except Exception as e:
                        logger.debug(f"Could not query state for input {inp_id}: {e}")
                        continue
            except Exception as e:
                logger.warning(f"QueryInputStreamState failed: {e}")
            
            # 3. Fallback: Use input statistics to determine active input
            if not active_input_id:
                try:
                    # Use DescribeStreamLiveChannelInputStatistics to check which input is active
                    # This API shows real-time statistics for each input
                    stats_req = mdl_models.DescribeStreamLiveChannelInputStatisticsRequest()
                    stats_req.ChannelId = channel_id
                    # StartTime and EndTime are optional - if empty, returns current statistics
                    
                    stats_resp = client.DescribeStreamLiveChannelInputStatistics(stats_req)
                    if hasattr(stats_resp, "Infos") and stats_resp.Infos:
                        max_bandwidth = 0
                        for stat_info in stats_resp.Infos:
                            inp_id = getattr(stat_info, "InputId", "")
                            network_in = getattr(stat_info, "NetworkIn", 0)
                            network_valid = getattr(stat_info, "NetworkValid", False)
                            
                            input_states[inp_id] = {
                                "bandwidth": network_in,
                                "network_valid": network_valid,
                            }
                            
                            # Active input is the one with valid network and highest bandwidth
                            if network_valid and network_in > max_bandwidth:
                                max_bandwidth = network_in
                                active_input_id = inp_id
                        
                        # If no input has valid network, check if any has bandwidth > 0
                        if not active_input_id:
                            for stat_info in stats_resp.Infos:
                                inp_id = getattr(stat_info, "InputId", "")
                                network_in = getattr(stat_info, "NetworkIn", 0)
                                if network_in > 0:
                                    active_input_id = inp_id
                                    break
                except Exception as e:
                    logger.warning(f"Could not get input statistics: {e}")
            
            # 4. Fallback: Check StreamLink flows to determine active input/source
            # This works for both Channel-level Failover and Input Source Redundancy
            # Only use if QueryInputStreamState didn't provide active source
            if not active_source_address:
                try:
                    from app.services.linkage import LinkageMatcher
                    
                    # Get all StreamLink flows
                    flows = self.list_streamlink_inputs()
                    
                    # Find flows linked to this channel
                    channel_info = {
                        "id": channel_id,
                        "input_endpoints": [],
                    }
                    # Get input endpoints from channel details
                    channel_details = self.get_resource_details(channel_id, "StreamLive")
                    if channel_details:
                        # Reconstruct input endpoints from input attachments
                        all_inputs = self.list_mdl_channels()
                        for ch in all_inputs:
                            if ch.get("id") == channel_id:
                                channel_info["input_endpoints"] = ch.get("input_endpoints", [])
                                break
                    
                    linked_flows = LinkageMatcher.find_linked_flows(channel_info, flows)
                    
                    # Check which StreamLink flow is running and connected to which input
                    flow_type_by_input = {}  # Map input_id to flow type (main/backup)
                    flow_type_by_source = {}  # Map source address to flow type (for Input Source Redundancy)
                    
                    for flow in linked_flows:
                        if flow.get("status") == "running":
                            flow_output_urls = flow.get("output_urls", [])
                            flow_name = flow.get("name", "").lower()
                            
                            # Determine if this is main or backup flow from name
                            is_backup_flow = "_b" in flow_name or "backup" in flow_name
                            is_main_flow = "_m" in flow_name or ("main" in flow_name and not is_backup_flow)
                            
                            # Match output URL to input endpoint to find which input/source is active
                            for inp in input_details:
                                inp_id = inp["id"]
                                
                                # Get input endpoints for this input
                                inp_endpoints = []
                                matched_source = None
                                
                                for endpoint in channel_info.get("input_endpoints", []):
                                    # Check if this endpoint matches the flow output
                                    for flow_url in flow_output_urls:
                                        # Normalize URLs for comparison
                                        endpoint_norm = endpoint.lower().strip().rstrip("/")
                                        flow_url_norm = flow_url.lower().strip().rstrip("/")
                                        
                                        # Extract stream key for comparison
                                        endpoint_key = endpoint.split("/")[-1] if "/" in endpoint else endpoint
                                        flow_key = flow_url.split("/")[-1] if "/" in flow_url else flow_url
                                        
                                        if endpoint_key == flow_key or endpoint_norm == flow_url_norm or endpoint_norm in flow_url_norm or flow_url_norm in endpoint_norm:
                                            inp_endpoints.append(endpoint)
                                            
                                            # For Input Source Redundancy: determine which source address is active
                                            # ap-seoul-1 typically means main, ap-seoul-2 means backup
                                            if "ap-seoul-1" in endpoint.lower() or "ap-seoul-1" in flow_url.lower():
                                                matched_source = "main"
                                                active_source_address = endpoint
                                            elif "ap-seoul-2" in endpoint.lower() or "ap-seoul-2" in flow_url.lower():
                                                matched_source = "backup"
                                                active_source_address = endpoint
                                            
                                            break
                                
                                if inp_endpoints:
                                    if not active_input_id:
                                        active_input_id = inp_id
                                    
                                    # Store flow type for this input
                                    if is_backup_flow:
                                        flow_type_by_input[inp_id] = "backup"
                                        if matched_source:
                                            flow_type_by_source[matched_source] = "backup"
                                    elif is_main_flow:
                                        flow_type_by_input[inp_id] = "main"
                                        if matched_source:
                                            flow_type_by_source[matched_source] = "main"
                                    
                                    # For Input Source Redundancy: use source address type if available
                                    if matched_source:
                                        flow_type_by_input[inp_id] = matched_source
                                    
                                    logger.info(f"Found active input {inp_id} via StreamLink flow {flow.get('name')} (backup={is_backup_flow}, main={is_main_flow}, source={matched_source})")
                                    
                                    # If we found a match, we can break (one flow per input typically)
                                    break
                            
                            if active_input_id:
                                break
                except Exception as e:
                    logger.debug(f"Could not determine active input from StreamLink: {e}")
            
            # 5. Multi-stage verification: Check StreamPackage input status
            streampackage_result = None
            if streampackage_id:
                try:
                    streampackage_result = self._get_streampackage_input_status(streampackage_id)
                    if streampackage_result and streampackage_result.get("active_input"):
                        # StreamPackage에서 확인된 활성 입력이 있으면 우선 사용
                        sp_active = streampackage_result.get("active_input")
                        logger.info(f"StreamPackage confirms active input: {sp_active}")
                        
                        # StreamPackage의 입력과 StreamLive 입력을 매칭
                        # StreamPackage 입력 URL이 StreamLive 출력과 매칭되는지 확인
                        # (간접적으로 StreamLive의 어떤 입력이 활성인지 추론)
                except Exception as e:
                    logger.debug(f"Could not verify via StreamPackage: {e}")
            
            # 6. Multi-stage verification: Check CSS stream status
            css_result = None
            try:
                # Get StreamPackage endpoints to find CSS stream info
                if streampackage_id:
                    # StreamPackage가 연결되어 있으면 CSS 검증 시도
                    streampackage_connected = True
                    stream_flowing = False
                    
                    if streampackage_result:
                        # StreamPackage 입력이 활성화되어 있으면 스트림이 흐르고 있다고 간주
                        sp_input_details = streampackage_result.get("input_details", [])
                        stream_flowing = any(inp.get("url") for inp in sp_input_details) if sp_input_details else False
                    else:
                        # StreamPackage 결과가 없어도 연결은 확인됨
                        stream_flowing = None  # 확인 불가
                    
                    css_result = {
                        "streampackage_connected": streampackage_connected,
                        "stream_flowing": stream_flowing,
                    }
            except Exception as e:
                logger.debug(f"Could not verify via CSS: {e}")
            
            # 7. Determine active input type (main/backup) with multi-stage verification
            # PRIORITY ORDER:
            # 0. DescribeStreamLiveChannelLogs - MOST RELIABLE (PipelineFailover/PipelineRecover events)
            # 1. QueryInputStreamState - Shows which sources have signal (Status == 1)
            # 2. StreamLink flow type
            # 3. StreamPackage result
            # 4. FailOverSettings
            # 5. Input name pattern
            # 6. Input order
            active_input_type = None
            verification_sources = []  # Track which sources confirmed the result
            is_input_source_redundancy = False  # Track if this is Input Source Redundancy mode
            log_based_result = None  # Store log-based detection result

            # Priority 0: Log-based detection (MOST RELIABLE)
            # This checks PipelineFailover/PipelineRecover events to determine actual serving pipeline
            try:
                log_based_result = self._get_active_pipeline_from_logs(channel_id, hours=24)
                if log_based_result and log_based_result.get("active_pipeline"):
                    active_input_type = log_based_result["active_pipeline"]
                    verification_sources.append("ChannelLogs")

                    # Check for Input Source Redundancy based on QueryInputStreamState
                    if source_status_by_input:
                        for inp_id, source_info in source_status_by_input.items():
                            active_sources = source_info.get("active_sources", [])
                            if len(active_sources) > 1:
                                is_input_source_redundancy = True
                                verification_sources.append("InputSourceRedundancy")
                                break

                    logger.info(f"Log-based detection: {active_input_type} (event: {log_based_result.get('last_event_type')})")
            except Exception as e:
                logger.debug(f"Log-based detection failed: {e}")

            # Priority 1: QueryInputStreamState - Use only if log-based detection didn't work
            # Note: QueryInputStreamState only tells us which sources have signal, not which is serving
            if not active_input_type and active_input_id:
                if active_input_id in source_status_by_input:
                    source_info = source_status_by_input[active_input_id]
                    active_sources = source_info.get("active_sources", [])

                    if active_sources:
                        # If only one source has signal, that's the active one
                        if len(active_sources) == 1:
                            primary_source = active_sources[0]
                            active_input_type = primary_source.get("type")
                            active_source_address = primary_source.get("url")
                            verification_sources.append("QueryInputStreamState")
                            logger.info(f"QueryInputStreamState: Only one active source: {active_input_type}")
                        else:
                            # Multiple sources have signal - can't determine from this alone
                            # Default to main unless log-based detection said otherwise
                            is_input_source_redundancy = True
                            if not active_input_type:
                                active_input_type = "main"  # Default assumption
                                verification_sources.append("QueryInputStreamState(default)")
                            verification_sources.append("InputSourceRedundancy")
                            logger.info(f"QueryInputStreamState: Multiple active sources, using default/log-based: {active_input_type}")

            if active_input_id and not active_input_type:
                # Priority 2: StreamLink flow type (fallback - if QueryInputStreamState didn't work)
                if active_input_id in flow_type_by_input:
                    active_input_type = flow_type_by_input[active_input_id]
                    verification_sources.append("StreamLink")
                    
                    # Check if this is Input Source Redundancy (same input, different source addresses)
                    if active_source_address:
                        is_input_source_redundancy = True
                        verification_sources.append("InputSourceRedundancy")
                    
                    # CSS 검증도 추가 (스트림이 흐르고 있음을 확인)
                    if css_result and css_result.get("stream_flowing"):
                        verification_sources.append("CSS")
                
                # Priority 2: StreamPackage result (fallback - input order only)
                elif streampackage_result and streampackage_result.get("active_input"):
                    # StreamPackage 결과는 입력 순서 기반이므로 보조 확인용
                    active_input_type = streampackage_result.get("active_input")
                    verification_sources.append("StreamPackage")
                    # CSS 검증도 추가 (StreamPackage를 통해 간접 확인)
                    if css_result and css_result.get("stream_flowing"):
                        verification_sources.append("CSS")
                
                # Priority 3: Primary/Secondary from FailOverSettings
                elif active_input_id == primary_input_id:
                    active_input_type = "main"
                    verification_sources.append("FailOverSettings")
                elif active_input_id == secondary_input_id:
                    active_input_type = "backup"
                    verification_sources.append("FailOverSettings")
                
                # Priority 4: Input name pattern
                else:
                    for inp in input_details:
                        if inp["id"] == active_input_id:
                            inp_name = inp.get("name", "").lower()
                            if "backup" in inp_name or "_b" in inp_name or "fv_" in inp_name:
                                active_input_type = "backup"
                                verification_sources.append("InputName")
                            elif "main" in inp_name or "_m" in inp_name:
                                active_input_type = "main"
                                verification_sources.append("InputName")
                            else:
                                # Last resort: first input is main, second is backup
                                idx = input_details.index(inp)
                                active_input_type = "main" if idx == 0 else "backup"
                                verification_sources.append("InputOrder")
                            break
            
            # Build result with multi-stage verification info
            result = {
                "channel_id": channel_id,
                "channel_name": getattr(info, "Name", ""),
                "active_input": active_input_type,
                "active_input_id": active_input_id,
                "primary_input_id": primary_input_id,
                "secondary_input_id": secondary_input_id,
                "failover_loss_threshold": failover_loss_threshold,
                "failover_recover_behavior": failover_recover_behavior,
                "input_details": input_details,
                "input_states": input_states,
                "verification_sources": verification_sources,
                "verification_level": len(verification_sources),
                "is_input_source_redundancy": is_input_source_redundancy,
                "active_source_address": active_source_address,
            }
            
            # Add StreamPackage verification info
            if streampackage_result:
                result["streampackage_verification"] = {
                    "streampackage_id": streampackage_id,
                    "active_input": streampackage_result.get("active_input"),
                    "input_details": streampackage_result.get("input_details", []),
                }
            
            # Add CSS verification info
            if css_result:
                result["css_verification"] = {
                    "streampackage_connected": css_result.get("streampackage_connected", False),
                    "stream_flowing": css_result.get("stream_flowing", False),
                }

            # Add log-based detection info (MOST RELIABLE)
            if log_based_result:
                result["log_based_detection"] = {
                    "active_pipeline": log_based_result.get("active_pipeline"),
                    "last_event_type": log_based_result.get("last_event_type"),
                    "last_event_time": log_based_result.get("last_event_time"),
                    "failover_count": log_based_result.get("failover_count", 0),
                    "message": log_based_result.get("message"),
                }

            if active_input_type:
                active_name = next(
                    (inp["name"] for inp in input_details if inp["id"] == active_input_id),
                    active_input_id
                )
                result["active_input_name"] = active_name

                # Build message with verification sources and log info
                sources_str = ", ".join(verification_sources) if verification_sources else "기본"

                # Add failover event info if available
                if log_based_result and log_based_result.get("last_event_type"):
                    event_info = f" | 마지막 이벤트: {log_based_result['last_event_type']}"
                    if log_based_result.get("failover_count", 0) > 0:
                        event_info += f" (24h 내 failover {log_based_result['failover_count']}회)"
                else:
                    event_info = ""

                result["message"] = f"현재 활성 입력: {active_input_type.upper()} ({active_name}) [검증: {sources_str}]{event_info}"
            else:
                result["message"] = "활성 입력을 확인할 수 없습니다."
            
            return result
            
        except TencentCloudSDKException as e:
            logger.error(f"Tencent Cloud SDK error getting input status: {e}")
            return {
                "channel_id": channel_id,
                "active_input": None,
                "message": f"API 오류: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Failed to get channel input status: {e}", exc_info=True)
            return {
                "channel_id": channel_id,
                "active_input": None,
                "message": f"오류 발생: {str(e)}",
            }

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

    def list_streampackage_channels(self) -> List[Dict]:
        """List StreamPackage channels."""
        if not STREAMPACKAGE_AVAILABLE:
            logger.warning("StreamPackage SDK not available")
            return []

        try:
            client = self._get_mdp_client()
            if not client:
                return []

            req = mdp_models.DescribeStreamPackageChannelsRequest()
            resp = client.DescribeStreamPackageChannels(req)

            channels = []
            if hasattr(resp, "Infos") and resp.Infos:
                for info in resp.Infos:
                    channel_id = getattr(info, "Id", "")
                    channel_name = getattr(info, "Name", "")
                    state = getattr(info, "State", "unknown")

                    # Get input details
                    input_details = []
                    points = getattr(info, "Points", None)
                    if points:
                        inputs = getattr(points, "Inputs", [])
                        for inp in inputs:
                            input_details.append({
                                "id": getattr(inp, "InputId", ""),
                                "name": getattr(inp, "InputName", ""),
                                "url": getattr(inp, "Url", ""),
                            })

                    channels.append({
                        "id": channel_id,
                        "name": channel_name or "Unknown Channel",
                        "status": self._normalize_streamlink_status(state),  # Similar status format
                        "service": "StreamPackage",
                        "type": "channel",
                        "input_details": input_details,
                    })

            logger.info(f"Found {len(channels)} StreamPackage channels")
            return channels

        except Exception as e:
            logger.error(f"Failed to list StreamPackage channels: {e}")
            return []

    def get_streampackage_channel_details(self, channel_id: str) -> Optional[Dict]:
        """Get detailed information about a StreamPackage channel."""
        if not STREAMPACKAGE_AVAILABLE:
            return None

        try:
            result = self._get_streampackage_input_status(channel_id)
            if not result:
                return None

            # Get additional channel info
            client = self._get_mdp_client()
            if not client:
                return result

            req = mdp_models.DescribeStreamPackageChannelRequest()
            req.Id = channel_id
            resp = client.DescribeStreamPackageChannel(req)

            if hasattr(resp, "Info"):
                info = resp.Info
                result.update({
                    "name": getattr(info, "Name", ""),
                    "state": getattr(info, "State", ""),
                    "protocol": getattr(info, "Protocol", ""),
                })

            return result

        except Exception as e:
            logger.error(f"Failed to get StreamPackage channel details: {e}")
            return None

    def get_flow_statistics(self, flow_id: str) -> Optional[Dict]:
        """Get real-time statistics for a StreamLink flow.

        Uses DescribeStreamLinkFlowRealtimeStatus to get current bitrate, fps, codec, resolution.

        Args:
            flow_id: StreamLink flow ID

        Returns:
            Dict with statistics:
                - bitrate: Current bitrate in bps
                - bitrate_mbps: Current bitrate in Mbps (formatted)
                - fps: Frame rate
                - state: Connection state
                - video_codec: Video codec (from media stats if available)
                - audio_codec: Audio codec (from media stats if available)
                - resolution: Video resolution (from media stats if available)
                - connected_time: Connection duration
        """
        try:
            client = self._get_mdc_client()

            # Get realtime status (most current data)
            req = mdc_models.DescribeStreamLinkFlowRealtimeStatusRequest()
            req.FlowId = flow_id

            resp = client.DescribeStreamLinkFlowRealtimeStatus(req)

            result = {
                "flow_id": flow_id,
                "bitrate": 0,
                "bitrate_mbps": "0",
                "fps": 0,
                "state": "unknown",
                "video_codec": None,
                "audio_codec": None,
                "resolution": None,
                "connected_time": None,
                "inputs": [],
                "outputs": [],
            }

            if hasattr(resp, "Datas") and resp.Datas:
                for item in resp.Datas:
                    # CommonStatus contains bitrate and state
                    common_status = getattr(item, "CommonStatus", None)
                    item_type = getattr(item, "Type", "")
                    input_id = getattr(item, "InputId", "")
                    output_id = getattr(item, "OutputId", "")

                    if common_status:
                        bitrate = getattr(common_status, "Bitrate", 0) or 0
                        state = getattr(common_status, "State", "unknown")
                        connected_time = getattr(common_status, "ConnectedTime", "")

                        item_data = {
                            "type": item_type,
                            "input_id": input_id,
                            "output_id": output_id,
                            "bitrate": bitrate,
                            "bitrate_mbps": f"{bitrate / 1_000_000:.2f}" if bitrate else "0",
                            "state": state,
                            "connected_time": connected_time,
                        }

                        # Categorize by type
                        if item_type.lower() == "input":
                            result["inputs"].append(item_data)
                            # Use input stats as primary (sum up if multiple)
                            result["bitrate"] += bitrate
                            if state != "unknown" and result["state"] == "unknown":
                                result["state"] = state
                            if connected_time and not result["connected_time"]:
                                result["connected_time"] = connected_time
                        elif item_type.lower() == "output":
                            result["outputs"].append(item_data)

                    # Check protocol-specific status for additional info
                    protocol = getattr(item, "Protocol", "")
                    if protocol == "SRT":
                        srt_status = getattr(item, "SRTStatus", None)
                        if srt_status:
                            # SRT provides RTT, packet loss info
                            item_data["rtt"] = getattr(srt_status, "RTT", None)
                            item_data["recv_packet_loss_rate"] = getattr(srt_status, "RecvPacketLossRate", None)
                            item_data["send_packet_loss_rate"] = getattr(srt_status, "SendPacketLossRate", None)

                # If input bitrate is 0, use output bitrate (some flows only report output)
                if result["bitrate"] == 0 and result["outputs"]:
                    output_bitrate = sum(o.get("bitrate", 0) for o in result["outputs"])
                    if output_bitrate > 0:
                        result["bitrate"] = output_bitrate
                        # Also get state from output if input state is unknown
                        if result["state"] == "unknown":
                            for o in result["outputs"]:
                                if o.get("state") and o["state"] != "unknown":
                                    result["state"] = o["state"]
                                    break

                # Calculate total bitrate in Mbps
                if result["bitrate"] > 0:
                    result["bitrate_mbps"] = f"{result['bitrate'] / 1_000_000:.2f}"

            # Try to get media info (codec, resolution) from statistics API
            try:
                from datetime import datetime, timedelta, timezone

                media_req = mdc_models.DescribeStreamLinkFlowMediaStatisticsRequest()
                media_req.FlowId = flow_id
                media_req.Type = "Input"
                media_req.Period = "5s"  # 5 second granularity
                media_req.StartTime = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
                media_req.EndTime = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                media_resp = client.DescribeStreamLinkFlowMediaStatistics(media_req)

                if hasattr(media_resp, "Infos") and media_resp.Infos:
                    # Get the most recent media info
                    for info in media_resp.Infos:
                        video = getattr(info, "Video", None)
                        audio = getattr(info, "Audio", None)

                        if video:
                            fps = getattr(video, "Fps", 0) or 0
                            if fps > 0 and result["fps"] == 0:
                                result["fps"] = fps

                        # Try to get codec info from statistics API
                        # Note: The DescribeStreamLinkFlowStatistics may provide more detail
                        break  # Only need the most recent
            except Exception as e:
                logger.debug(f"Could not get media statistics for flow {flow_id}: {e}")

            # Try to get additional stats (fps, codec) from statistics API
            try:
                from datetime import datetime, timedelta, timezone

                stats_req = mdc_models.DescribeStreamLinkFlowStatisticsRequest()
                stats_req.FlowId = flow_id
                stats_req.Type = "Input"
                stats_req.Period = "5s"
                stats_req.StartTime = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
                stats_req.EndTime = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                stats_resp = client.DescribeStreamLinkFlowStatistics(stats_req)

                if hasattr(stats_resp, "Infos") and stats_resp.Infos:
                    # Get the most recent stats
                    for info_arr in stats_resp.Infos:
                        flow_stats_list = getattr(info_arr, "FlowStatistics", [])
                        if flow_stats_list:
                            # Get most recent entry
                            latest = flow_stats_list[-1] if isinstance(flow_stats_list, list) else flow_stats_list

                            video = getattr(latest, "Video", None)
                            audio = getattr(latest, "Audio", None)

                            if video:
                                fps = getattr(video, "Fps", 0) or 0
                                if fps > 0 and result["fps"] == 0:
                                    result["fps"] = fps
                                rate = getattr(video, "Rate", 0) or 0
                                if rate > 0 and result["bitrate"] == 0:
                                    result["bitrate"] = rate
                                    result["bitrate_mbps"] = f"{rate / 1_000_000:.2f}"

                            if audio:
                                audio_rate = getattr(audio, "Rate", 0) or 0
                                # Could add audio rate to total if needed
                            break  # Only need most recent
            except Exception as e:
                logger.debug(f"Could not get flow statistics for flow {flow_id}: {e}")

            logger.info(f"Flow {flow_id} stats: {result['bitrate_mbps']} Mbps, {result['fps']} fps, state={result['state']}")
            return result

        except TencentCloudSDKException as e:
            logger.error(f"Failed to get flow statistics for {flow_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting flow statistics for {flow_id}: {e}")
            return None

    def get_flow_statistics_batch(self, flow_ids: List[str]) -> Dict[str, Optional[Dict]]:
        """Get statistics for multiple flows in parallel with caching.

        Uses a 60-second cache to avoid API rate limits (20 req/sec).

        Args:
            flow_ids: List of flow IDs

        Returns:
            Dict mapping flow_id to statistics (or None if failed)
        """
        results = {}
        ids_to_fetch = []
        cache_ttl = 60  # 60 seconds cache for flow stats

        # Check cache first
        now = time.time()
        with self._cache_lock:
            for flow_id in flow_ids:
                cache_key = f"flow_stats_{flow_id}"
                cached = self._linkage_cache.get(cache_key)
                if cached and (now - cached["timestamp"] < cache_ttl):
                    results[flow_id] = cached["data"]
                else:
                    ids_to_fetch.append(flow_id)

        if not ids_to_fetch:
            logger.debug(f"All {len(flow_ids)} flow stats from cache")
            return results

        logger.info(f"Fetching stats for {len(ids_to_fetch)} flows ({len(flow_ids) - len(ids_to_fetch)} from cache)")

        def fetch_stats(flow_id: str) -> tuple:
            return (flow_id, self.get_flow_statistics(flow_id))

        # Submit tasks in parallel but limit concurrency to avoid rate limit
        # Tencent API limit is 20 req/sec, so we fetch in batches
        batch_size = 15  # Safe margin under 20 req/sec limit
        for i in range(0, len(ids_to_fetch), batch_size):
            batch = ids_to_fetch[i:i + batch_size]
            futures = [self.executor.submit(fetch_stats, fid) for fid in batch]

            for future in futures:
                try:
                    flow_id, stats = future.result(timeout=self._timeout)
                    results[flow_id] = stats

                    # Cache the result
                    with self._cache_lock:
                        self._linkage_cache[f"flow_stats_{flow_id}"] = {
                            "data": stats,
                            "timestamp": time.time(),
                        }
                except Exception as e:
                    logger.error(f"Failed to get stats in batch: {e}")

            # Small delay between batches to respect rate limit
            if i + batch_size < len(ids_to_fetch):
                time.sleep(0.5)

        return results

    def list_css_domains(self) -> List[Dict]:
        """List CSS (Cloud Streaming Service) domains."""
        if not CSS_AVAILABLE:
            logger.warning("CSS SDK not available")
            return []

        try:
            client = self._get_css_client()
            if not client:
                return []

            req = live_models.DescribeLiveDomainsRequest()
            resp = client.DescribeLiveDomains(req)

            domains = []
            if hasattr(resp, "DomainList") and resp.DomainList:
                for domain_info in resp.DomainList:
                    domain_name = getattr(domain_info, "DomainName", "")
                    domain_type = getattr(domain_info, "DomainType", "")
                    status = getattr(domain_info, "Status", "")
                    cname = getattr(domain_info, "Cname", "")

                    domains.append({
                        "domain": domain_name,
                        "type": domain_type,
                        "status": status,
                        "cname": cname,
                        "service": "CSS",
                    })

            logger.info(f"Found {len(domains)} CSS domains")
            return domains

        except Exception as e:
            logger.error(f"Failed to list CSS domains: {e}")
            return []

    def list_css_streams(self, domain: Optional[str] = None) -> List[Dict]:
        """List active CSS streams."""
        if not CSS_AVAILABLE:
            logger.warning("CSS SDK not available")
            return []

        try:
            client = self._get_css_client()
            if not client:
                return []

            # If domain is provided, get streams for that domain
            if domain:
                req = live_models.DescribeLiveStreamOnlineListRequest()
                req.DomainName = domain
                req.PageNum = 1
                req.PageSize = 100

                resp = client.DescribeLiveStreamOnlineList(req)
                streams = []

                if hasattr(resp, "OnlineInfo") and resp.OnlineInfo:
                    for stream_info in resp.OnlineInfo:
                        stream_name = getattr(stream_info, "StreamName", "")
                        app_name = getattr(stream_info, "AppName", "")
                        publish_time = getattr(stream_info, "PublishTime", "")
                        expire_time = getattr(stream_info, "ExpireTime", "")

                        streams.append({
                            "stream_name": stream_name,
                            "app_name": app_name,
                            "full_name": f"{app_name}/{stream_name}",
                            "domain": domain,
                            "publish_time": publish_time,
                            "expire_time": expire_time,
                            "service": "CSS",
                        })

                return streams
            else:
                # List all domains first, then get streams for each
                domains = self.list_css_domains()
                all_streams = []

                for domain_info in domains:
                    domain_name = domain_info.get("domain")
                    if domain_name:
                        domain_streams = self.list_css_streams(domain_name)
                        all_streams.extend(domain_streams)

                return all_streams

        except Exception as e:
            logger.error(f"Failed to list CSS streams: {e}")
            return []

    def get_css_stream_details(self, stream_name: str, domain: Optional[str] = None) -> Optional[Dict]:
        """Get detailed information about a CSS stream."""
        if not CSS_AVAILABLE:
            return None

        try:
            result = self._get_css_stream_status(stream_name, domain)
            if not result:
                return None

            # Get additional stream info
            client = self._get_css_client()
            if not client:
                return result

            # Try to get stream push info
            try:
                push_req = live_models.DescribeLiveStreamPushInfoListRequest()
                if domain:
                    push_req.DomainName = domain

                parts = stream_name.split("/")
                if len(parts) >= 2:
                    push_req.AppName = parts[0]
                    push_req.StreamName = "/".join(parts[1:])
                else:
                    push_req.StreamName = stream_name

                push_resp = client.DescribeLiveStreamPushInfoList(push_req)
                if hasattr(push_resp, "DataInfoList") and push_resp.DataInfoList:
                    push_info = push_resp.DataInfoList[0]
                    result.update({
                        "push_url": getattr(push_info, "StreamUrl", ""),
                        "push_domain": getattr(push_info, "DomainName", ""),
                        "push_app": getattr(push_info, "AppName", ""),
                        "push_stream": getattr(push_info, "StreamName", ""),
                    })
            except Exception as e:
                logger.debug(f"Could not get push info: {e}")

            return result

        except Exception as e:
            logger.error(f"Failed to get CSS stream details: {e}")
            return None

    def get_css_stream_bandwidth(
        self,
        stream_name: str,
        domain: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Get CSS stream bandwidth and traffic information.
        
        Args:
            stream_name: Stream name (app/stream format)
            domain: CSS domain (optional)
            start_time: Start time in ISO format
            end_time: End time in ISO format
        
        Returns:
            Dict with bandwidth and traffic information
        """
        if not CSS_AVAILABLE:
            return None

        try:
            from datetime import datetime, timedelta, timezone

            client = self._get_css_client()
            if not client:
                return None

            # Use DescribeStreamDayPlayInfoList for bandwidth/traffic
            req = live_models.DescribeStreamDayPlayInfoListRequest()
            
            if domain:
                req.DomainName = domain

            # Parse stream name
            parts = stream_name.split("/")
            if len(parts) >= 2:
                req.AppName = parts[0]
                req.StreamName = "/".join(parts[1:])
            else:
                req.StreamName = stream_name

            # Set time range (default: last 24 hours)
            if not start_time:
                start_time = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
            if not end_time:
                end_time = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            req.StartTime = start_time
            req.EndTime = end_time

            resp = client.DescribeStreamDayPlayInfoList(req)

            if hasattr(resp, "DataInfoList") and resp.DataInfoList:
                total_bandwidth = 0
                total_traffic = 0
                daily_info = []

                for data_info in resp.DataInfoList:
                    bandwidth = getattr(data_info, "Bandwidth", 0)
                    flux = getattr(data_info, "Flux", 0)
                    time_str = getattr(data_info, "Time", "")

                    total_bandwidth += bandwidth
                    total_traffic += flux

                    daily_info.append({
                        "time": time_str,
                        "bandwidth": bandwidth,  # bps
                        "traffic": flux,  # bytes
                    })

                return {
                    "stream_name": stream_name,
                    "domain": domain,
                    "start_time": start_time,
                    "end_time": end_time,
                    "total_bandwidth": total_bandwidth,  # Total bandwidth in bps
                    "total_traffic": total_traffic,  # Total traffic in bytes
                    "average_bandwidth": total_bandwidth / len(daily_info) if daily_info else 0,
                    "daily_info": daily_info,
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get CSS stream bandwidth: {e}")
            return None

    def get_css_stream_quality(
        self,
        stream_name: str,
        domain: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Get CSS stream quality information (bitrate, framerate, resolution, etc.).
        
        Args:
            stream_name: Stream name (app/stream format)
            domain: CSS domain (optional)
        
        Returns:
            Dict with stream quality information
        """
        if not CSS_AVAILABLE:
            return None

        try:
            client = self._get_css_client()
            if not client:
                return None

            # Get push quality info
            push_req = live_models.DescribeStreamPushInfoListRequest()
            if domain:
                push_req.DomainName = domain

            parts = stream_name.split("/")
            if len(parts) >= 2:
                push_req.AppName = parts[0]
                push_req.StreamName = "/".join(parts[1:])
            else:
                push_req.StreamName = stream_name

            push_resp = client.DescribeStreamPushInfoList(push_req)

            quality_info = {
                "stream_name": stream_name,
                "domain": domain,
            }

            if hasattr(push_resp, "DataInfoList") and push_resp.DataInfoList:
                push_info = push_resp.DataInfoList[0]

                # Extract quality information
                quality_info.update({
                    "push_url": getattr(push_info, "StreamUrl", ""),
                    "push_domain": getattr(push_info, "DomainName", ""),
                    "push_app": getattr(push_info, "AppName", ""),
                    "push_stream": getattr(push_info, "StreamName", ""),
                    "push_time": getattr(push_info, "PushTime", ""),
                    "client_ip": getattr(push_info, "ClientIp", ""),
                })

                # Try to get detailed push quality (if available in newer API versions)
                # Note: Some fields may not be available in all API versions
                try:
                    # These fields might be available in DescribeStreamPushInfoList
                    video_codec = getattr(push_info, "VideoCodec", "")
                    audio_codec = getattr(push_info, "AudioCodec", "")
                    video_bitrate = getattr(push_info, "VideoBitrate", 0)
                    audio_bitrate = getattr(push_info, "AudioBitrate", 0)
                    video_fps = getattr(push_info, "VideoFps", 0)
                    resolution = getattr(push_info, "Resolution", "")

                    if video_codec or audio_codec:
                        quality_info["codec"] = {
                            "video": video_codec,
                            "audio": audio_codec,
                        }
                    if video_bitrate or audio_bitrate:
                        quality_info["bitrate"] = {
                            "video": video_bitrate,  # bps
                            "audio": audio_bitrate,  # bps
                            "total": video_bitrate + audio_bitrate,
                        }
                    if video_fps:
                        quality_info["framerate"] = video_fps
                    if resolution:
                        quality_info["resolution"] = resolution
                except Exception:
                    pass  # Quality fields may not be available

            # Get play quality info
            try:
                play_req = live_models.DescribeStreamPlayInfoListRequest()
                if domain:
                    play_req.DomainName = domain

                parts = stream_name.split("/")
                if len(parts) >= 2:
                    play_req.AppName = parts[0]
                    play_req.StreamName = "/".join(parts[1:])
                else:
                    play_req.StreamName = stream_name

                # Get recent play info (last hour)
                from datetime import datetime, timedelta, timezone
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(hours=1)

                play_req.StartTime = start_time.strftime("%Y-%m-%d %H:%M:%S")
                play_req.EndTime = end_time.strftime("%Y-%m-%d %H:%M:%S")

                play_resp = client.DescribeStreamPlayInfoList(play_req)

                if hasattr(play_resp, "DataInfoList") and play_resp.DataInfoList:
                    play_info = play_resp.DataInfoList[0]

                    # Extract play quality and viewer info
                    play_bandwidth = getattr(play_info, "Bandwidth", 0)
                    play_flux = getattr(play_info, "Flux", 0)
                    play_time = getattr(play_info, "Time", "")

                    quality_info["play_info"] = {
                        "bandwidth": play_bandwidth,  # bps
                        "traffic": play_flux,  # bytes
                        "time": play_time,
                    }

                    # Try to get viewer count (if available)
                    try:
                        # Note: Viewer count might be in a different field or API
                        # This is a placeholder - actual field name may vary
                        viewer_count = getattr(play_info, "Online", 0) or getattr(play_info, "ViewerCount", 0)
                        if viewer_count:
                            quality_info["viewer_count"] = viewer_count
                    except Exception:
                        pass

            except Exception as e:
                logger.debug(f"Could not get play quality info: {e}")

            return quality_info if quality_info.get("push_url") or quality_info.get("play_info") else None

        except Exception as e:
            logger.error(f"Failed to get CSS stream quality: {e}")
            return None

    def get_css_stream_events(
        self,
        stream_name: str,
        domain: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        hours: int = 24,
    ) -> List[Dict]:
        """
        Get CSS stream events (start, stop, etc.).
        
        Args:
            stream_name: Stream name (app/stream format)
            domain: CSS domain (optional)
            start_time: Start time in ISO format
            end_time: End time in ISO format
            hours: Number of hours to look back
        
        Returns:
            List of stream events
        """
        if not CSS_AVAILABLE:
            return []

        try:
            from datetime import datetime, timedelta, timezone

            client = self._get_css_client()
            if not client:
                return []

            req = live_models.DescribeLiveStreamEventListRequest()
            
            if domain:
                req.DomainName = domain

            # Parse stream name
            parts = stream_name.split("/")
            if len(parts) >= 2:
                req.AppName = parts[0]
                req.StreamName = "/".join(parts[1:])
            else:
                req.StreamName = stream_name

            # Set time range
            if not start_time:
                start_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
            if not end_time:
                end_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

            req.StartTime = start_time
            req.EndTime = end_time

            resp = client.DescribeLiveStreamEventList(req)

            events = []
            if hasattr(resp, "EventList") and resp.EventList:
                for event in resp.EventList:
                    event_type = getattr(event, "EventType", "")
                    event_time = getattr(event, "Time", "")
                    event_status = getattr(event, "Status", "")

                    events.append({
                        "service": "CSS",
                        "resource_id": stream_name,
                        "domain": domain,
                        "event_type": event_type,
                        "time": event_time,
                        "status": event_status,
                        "timestamp": event_time,
                    })

            # Sort by time (most recent first)
            events.sort(key=lambda x: x.get('time', ''), reverse=True)

            return events

        except Exception as e:
            logger.error(f"Failed to get CSS stream events: {e}")
            return []

    def get_streamlive_channel_logs(
        self,
        channel_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        hours: int = 24,
        event_types: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Get StreamLive channel logs.
        
        Args:
            channel_id: StreamLive channel ID
            start_time: Start time in ISO format (optional)
            end_time: End time in ISO format (optional)
            hours: Number of hours to look back (if start_time not provided)
            event_types: Filter by event types (optional, e.g., ["PipelineFailover", "PipelineRecover"])
        
        Returns:
            List of log entries with type, time, pipeline, message
        """
        try:
            from datetime import datetime, timedelta, timezone

            client = self._get_mdl_client()

            log_req = mdl_models.DescribeStreamLiveChannelLogsRequest()
            log_req.ChannelId = channel_id

            if start_time:
                log_req.StartTime = start_time
            else:
                log_req.StartTime = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")

            if end_time:
                log_req.EndTime = end_time
            else:
                log_req.EndTime = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            log_resp = client.DescribeStreamLiveChannelLogs(log_req)

            if not log_resp.Infos:
                return []

            infos = log_resp.Infos
            all_logs = []

            # Collect logs from both pipelines
            for pipeline_attr in ['Pipeline0', 'Pipeline1']:
                pipeline_name = "Pipeline A (Main)" if pipeline_attr == 'Pipeline0' else "Pipeline B (Backup)"
                pipeline_logs = getattr(infos, pipeline_attr, None)
                if not pipeline_logs:
                    continue

                logs = pipeline_logs if isinstance(pipeline_logs, list) else [pipeline_logs]
                for log in logs:
                    log_type = getattr(log, 'Type', '')
                    log_time = getattr(log, 'Time', '')
                    log_message = getattr(log, 'Message', '')

                    # Filter by event types if specified
                    if event_types and log_type not in event_types:
                        continue

                    all_logs.append({
                        "service": "StreamLive",
                        "resource_id": channel_id,
                        "pipeline": pipeline_name,
                        "event_type": log_type,
                        "time": log_time,
                        "message": log_message,
                        "timestamp": log_time,
                    })

            # Sort by time (most recent first)
            all_logs.sort(key=lambda x: x.get('time', ''), reverse=True)

            return all_logs

        except Exception as e:
            logger.error(f"Failed to get StreamLive channel logs: {e}")
            return []

    def get_streamlink_flow_logs(
        self,
        flow_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        hours: int = 24,
    ) -> List[Dict]:
        """
        Get StreamLink flow logs/events.
        
        Note: StreamLink may not have direct log API, so we use flow status history.
        
        Args:
            flow_id: StreamLink flow ID
            start_time: Start time in ISO format (optional)
            end_time: End time in ISO format (optional)
            hours: Number of hours to look back
        
        Returns:
            List of log entries
        """
        try:
            from datetime import datetime, timezone

            # StreamLink doesn't have direct log API, so we get flow details
            # and infer events from status changes
            client = self._get_mdc_client()
            req = mdc_models.DescribeStreamLinkFlowRequest()
            req.FlowId = flow_id
            resp = client.DescribeStreamLinkFlow(req)

            if not hasattr(resp, "Info"):
                return []

            info = resp.Info
            logs = []

            # Get current state as an event
            state = getattr(info, "State", "")
            state_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            logs.append({
                "service": "StreamLink",
                "resource_id": flow_id,
                "event_type": "StateChange",
                "time": state_time,
                "message": f"Current state: {state}",
                "state": state,
                "timestamp": state_time,
            })

            # Note: StreamLink may not provide historical logs via API
            # This is a limitation - we can only see current state

            return logs

        except Exception as e:
            logger.error(f"Failed to get StreamLink flow logs: {e}")
            return []

    def get_streampackage_channel_logs(
        self,
        channel_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        hours: int = 24,
    ) -> List[Dict]:
        """
        Get StreamPackage channel logs/events.
        
        Note: StreamPackage may not have direct log API, so we use channel status.
        
        Args:
            channel_id: StreamPackage channel ID
            start_time: Start time in ISO format (optional)
            end_time: End time in ISO format (optional)
            hours: Number of hours to look back
        
        Returns:
            List of log entries
        """
        try:
            from datetime import datetime, timezone

            if not STREAMPACKAGE_AVAILABLE:
                return []

            client = self._get_mdp_client()
            if not client:
                return []

            req = mdp_models.DescribeStreamPackageChannelRequest()
            req.Id = channel_id
            resp = client.DescribeStreamPackageChannel(req)

            if not hasattr(resp, "Info"):
                return []

            info = resp.Info
            logs = []

            # Get current state as an event
            state = getattr(info, "State", "")
            state_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            logs.append({
                "service": "StreamPackage",
                "resource_id": channel_id,
                "event_type": "StateChange",
                "time": state_time,
                "message": f"Current state: {state}",
                "state": state,
                "timestamp": state_time,
            })

            # Get input status
            input_status = self._get_streampackage_input_status(channel_id)
            if input_status:
                active_input = input_status.get("active_input")
                if active_input:
                    logs.append({
                        "service": "StreamPackage",
                        "resource_id": channel_id,
                        "event_type": "InputStatus",
                        "time": state_time,
                        "message": f"Active input: {active_input}",
                        "active_input": active_input,
                        "timestamp": state_time,
                    })

            # Note: StreamPackage may not provide historical logs via API
            # This is a limitation - we can only see current state

            return logs

        except Exception as e:
            logger.error(f"Failed to get StreamPackage channel logs: {e}")
            return []

    def get_css_stream_logs(
        self,
        stream_name: str,
        domain: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        hours: int = 24,
    ) -> List[Dict]:
        """
        Get CSS stream logs/events.
        
        Args:
            stream_name: Stream name (app/stream format)
            domain: CSS domain (optional)
            start_time: Start time in ISO format (optional)
            end_time: End time in ISO format (optional)
            hours: Number of hours to look back
        
        Returns:
            List of log entries
        """
        try:
            from datetime import datetime, timezone

            if not CSS_AVAILABLE:
                return []

            client = self._get_css_client()
            if not client:
                return []

            logs = []

            # Get current stream state
            stream_status = self._get_css_stream_status(stream_name, domain)
            if stream_status:
                state_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                is_active = stream_status.get("is_active", False)
                stream_state = stream_status.get("stream_state", "")

                logs.append({
                    "service": "CSS",
                    "resource_id": stream_name,
                    "domain": domain,
                    "event_type": "StreamState",
                    "time": state_time,
                    "message": f"Stream state: {stream_state} (active: {is_active})",
                    "stream_state": stream_state,
                    "is_active": is_active,
                    "timestamp": state_time,
                })

            # Try to get push info history (if available)
            try:
                push_req = live_models.DescribeLiveStreamPushInfoListRequest()
                if domain:
                    push_req.DomainName = domain

                parts = stream_name.split("/")
                if len(parts) >= 2:
                    push_req.AppName = parts[0]
                    push_req.StreamName = "/".join(parts[1:])
                else:
                    push_req.StreamName = stream_name

                push_resp = client.DescribeLiveStreamPushInfoList(push_req)
                if hasattr(push_resp, "DataInfoList") and push_resp.DataInfoList:
                    for push_info in push_resp.DataInfoList:
                        push_time = getattr(push_info, "PushTime", "")
                        if push_time:
                            logs.append({
                                "service": "CSS",
                                "resource_id": stream_name,
                                "domain": domain,
                                "event_type": "PushInfo",
                                "time": push_time,
                                "message": f"Push info available",
                                "push_url": getattr(push_info, "StreamUrl", ""),
                                "timestamp": push_time,
                            })
            except Exception as e:
                logger.debug(f"Could not get CSS push info: {e}")

            # Note: CSS may have limited historical log API
            # This is a limitation - we can only see current state and recent push info

            return logs

        except Exception as e:
            logger.error(f"Failed to get CSS stream logs: {e}")
            return []

    def get_integrated_logs(
        self,
        channel_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        hours: int = 24,
        services: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None,
    ) -> Dict:
        """
        Get integrated logs from StreamLive, StreamLink, StreamPackage, and CSS.
        
        Args:
            channel_id: StreamLive channel ID (primary resource)
            start_time: Start time in ISO format (optional)
            end_time: End time in ISO format (optional)
            hours: Number of hours to look back
            services: Filter by services (optional, e.g., ["StreamLive", "StreamLink"])
            event_types: Filter by event types (optional)
        
        Returns:
            Dict with integrated logs from all services
        """
        try:
            from app.services.linkage import ResourceHierarchyBuilder

            # Get StreamLive logs
            streamlive_logs = []
            if not services or "StreamLive" in services:
                streamlive_logs = self.get_streamlive_channel_logs(
                    channel_id=channel_id,
                    start_time=start_time,
                    end_time=end_time,
                    hours=hours,
                    event_types=event_types,
                )

            # Get linked StreamLink flows
            streamlink_logs = []
            if not services or "StreamLink" in services:
                resources = self.list_all_resources()
                hierarchy = ResourceHierarchyBuilder.build_hierarchy(resources)

                for h in hierarchy:
                    if h["parent"].get("id") == channel_id:
                        for child in h["children"]:
                            flow_id = child.get("id")
                            if flow_id:
                                flow_logs = self.get_streamlink_flow_logs(
                                    flow_id=flow_id,
                                    start_time=start_time,
                                    end_time=end_time,
                                    hours=hours,
                                )
                                streamlink_logs.extend(flow_logs)
                        break

            # Get StreamPackage logs (if connected)
            streampackage_logs = []
            if not services or "StreamPackage" in services:
                # Get StreamPackage ID from channel input status
                input_status = self.get_channel_input_status(channel_id)
                if input_status and "streampackage_verification" in input_status:
                    sp_id = input_status["streampackage_verification"].get("streampackage_id")
                    if sp_id:
                        sp_logs = self.get_streampackage_channel_logs(
                            channel_id=sp_id,
                            start_time=start_time,
                            end_time=end_time,
                            hours=hours,
                        )
                        streampackage_logs.extend(sp_logs)

            # Get CSS logs (if connected)
            css_logs = []
            if not services or "CSS" in services:
                # Try to find CSS streams related to this channel
                # This is indirect - we need to find CSS streams that might be related
                # For now, we'll get CSS streams from StreamPackage if available
                if streampackage_logs:
                    # CSS streams are typically related to StreamPackage
                    # We can list active CSS streams and match them
                    all_css_streams = self.list_css_streams()
                    for css_stream in all_css_streams[:10]:  # Limit to first 10 for performance
                        stream_name = css_stream.get("full_name", "")
                        if stream_name:
                            css_stream_logs = self.get_css_stream_logs(
                                stream_name=stream_name,
                                start_time=start_time,
                                end_time=end_time,
                                hours=hours,
                            )
                            css_logs.extend(css_stream_logs)

            # Combine all logs
            all_logs = streamlive_logs + streamlink_logs + streampackage_logs + css_logs

            # Sort by timestamp (most recent first)
            all_logs.sort(key=lambda x: x.get('timestamp', x.get('time', '')), reverse=True)

            # Filter by event types if specified
            if event_types:
                all_logs = [log for log in all_logs if log.get('event_type') in event_types]

            # Generate summary statistics
            event_counts = {}
            service_counts = {}
            for log in all_logs:
                event_type = log.get('event_type', 'Unknown')
                service = log.get('service', 'Unknown')
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
                service_counts[service] = service_counts.get(service, 0) + 1

            return {
                "channel_id": channel_id,
                "start_time": start_time or (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_time": end_time or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "total_logs": len(all_logs),
                "service_counts": service_counts,
                "event_counts": event_counts,
                "logs": all_logs,
                "streamlive_logs": streamlive_logs,
                "streamlink_logs": streamlink_logs,
                "streampackage_logs": streampackage_logs,
                "css_logs": css_logs,
            }

        except Exception as e:
            from datetime import datetime, timedelta, timezone
            logger.error(f"Failed to get integrated logs: {e}", exc_info=True)
            return {
                "channel_id": channel_id,
                "start_time": start_time or (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end_time": end_time or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "total_logs": 0,
                "error": str(e),
                "logs": [],
                "service_counts": {},
                "event_counts": {},
            }


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

    async def get_flow_statistics(self, flow_id: str) -> Optional[Dict]:
        return await asyncio.to_thread(self._sync.get_flow_statistics, flow_id)

    async def get_flow_statistics_batch(self, flow_ids: List[str]) -> Dict[str, Optional[Dict]]:
        return await asyncio.to_thread(self._sync.get_flow_statistics_batch, flow_ids)

    def clear_cache(self) -> None:
        self._sync.clear_cache()

    def prewarm_cache(self) -> None:
        self._sync.prewarm_cache()
