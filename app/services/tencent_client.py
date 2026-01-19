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

    def _get_mdp_client(self):
        """Get a thread-safe MDP (StreamPackage) client."""
        if not STREAMPACKAGE_AVAILABLE:
            return None
        cred = credential.Credential(self._secret_id, self._secret_key)
        http_profile = HttpProfile()
        http_profile.reqTimeout = self._timeout
        http_profile.endpoint = "mdp.intl.tencentcloudapi.com"
        client_profile = ClientProfile(httpProfile=http_profile)
        return mdp_client.MdpClient(cred, self._region, client_profile)

    def _get_css_client(self):
        """Get a thread-safe CSS (Live) client."""
        if not CSS_AVAILABLE:
            return None
        cred = credential.Credential(self._secret_id, self._secret_key)
        http_profile = HttpProfile()
        http_profile.reqTimeout = self._timeout
        client_profile = ClientProfile(httpProfile=http_profile)
        return live_client.LiveClient(cred, self._region, client_profile)

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
            
            for att in attached_inputs:
                att_id = str(getattr(att, "Id", att)).strip()
                att_name = getattr(att, "Name", "") or att_id
                
                # Check for failover settings
                failover_settings = getattr(att, "FailOverSettings", None)
                if failover_settings:
                    secondary_id = getattr(failover_settings, "SecondaryInputId", "")
                    if secondary_id:
                        secondary_input_id = str(secondary_id).strip()
                
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
