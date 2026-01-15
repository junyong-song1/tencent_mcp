"""Tencent Cloud SDK client for multi-service management."""
import logging
import time
import threading
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.common_client import CommonClient
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.live.v20180801 import live_client, models as live_models
from tencentcloud.vod.v20180717 import vod_client, models as vod_models
from tencentcloud.mdl.v20200326 import mdl_client, models as mdl_models
from tencentcloud.mdc.v20200828 import mdc_client, models as mdc_models

from config import Config

logger = logging.getLogger(__name__)

MDL_SDK_AVAILABLE = True
STREAMLINK_AVAILABLE = True

class ChannelStatus:
    """Channel status constants."""
    RUNNING = "running"
    IDLE = "idle"
    STOPPED = "stopped"
    ERROR = "error"
    UNKNOWN = "unknown"

class TencentCloudClient:
    """Unified client for Tencent Cloud services (MediaLive, MediaConnect/StreamLink, CSS, VOD)."""

    def __init__(self):
        """Initialize Tencent Cloud SDK clients."""
        self.cred = credential.Credential(
            Config.TENCENT_SECRET_ID,
            Config.TENCENT_SECRET_KEY
        )
        self.region = Config.TENCENT_REGION

        # Cache for linkage metadata
        self._linkage_cache = {}
        self._cache_ttl = Config.CACHE_TTL_SECONDS
        self._cache_lock = threading.Lock()  # Thread-safe cache access

        # Shared executor for parallel tasks
        self.executor = ThreadPoolExecutor(max_workers=Config.THREAD_POOL_WORKERS)

        logger.info("Tencent Cloud client initialized (Thread-safe mode)")

    def _get_mdc_client(self):
        """Get a thread-safe MDC client."""
        cred = credential.Credential(Config.TENCENT_SECRET_ID, Config.TENCENT_SECRET_KEY)
        http_profile = HttpProfile()
        http_profile.reqTimeout = Config.API_REQUEST_TIMEOUT
        client_profile = ClientProfile(httpProfile=http_profile)
        return mdc_client.MdcClient(cred, Config.TENCENT_REGION, client_profile)

    def _get_mdl_client(self):
        """Get a thread-safe MDL client."""
        cred = credential.Credential(Config.TENCENT_SECRET_ID, Config.TENCENT_SECRET_KEY)
        http_profile = HttpProfile()
        http_profile.reqTimeout = Config.API_REQUEST_TIMEOUT
        client_profile = ClientProfile(httpProfile=http_profile)
        return mdl_client.MdlClient(cred, Config.TENCENT_REGION, client_profile)

    def list_mdl_channels(self) -> List[Dict]:
        """
        List StreamLive (MediaLive) channels with batch linkage data.
        """
        try:
            client = self._get_mdl_client()
            # 1. Fetch all channels
            req = mdl_models.DescribeStreamLiveChannelsRequest()
            resp = client.DescribeStreamLiveChannels(req)
            info_list = resp.Infos if hasattr(resp, "Infos") else []

            # 2. Fetch all inputs in batch for linkage (thread-safe cache access)
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
                        # Correct field for inputs is InputSettings or similar depending on type
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

                        # Fallback for some input types that use different fields
                        if not endpoints and hasattr(inp, "InputAddressList"):
                            for addr_info in getattr(inp, "InputAddressList", []):
                                ip = getattr(addr_info, "Ip", "")
                                if ip: endpoints.append(ip)

                        inp_id = str(getattr(inp, "Id", "")).strip()
                        if inp_id:
                            input_map[inp_id] = list(set(endpoints))
                            # Input 이름도 저장
                            input_name = getattr(inp, "Name", "")
                            if input_name:
                                input_name_map[inp_id] = input_name

                    logger.info(f"Populated MDL input_map with {len(input_map)} entries")
                    with self._cache_lock:
                        self._linkage_cache[cache_key] = {"data": input_map, "name_map": input_name_map, "timestamp": time.time()}
                except Exception as e:
                    import traceback
                    logger.error(f"Failed to fetch batch inputs: {e}")
                    logger.error(traceback.format_exc())

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
                    else:
                        logger.debug(f"Input ID {att_id} not found in input_map")
                    
                    # Input 상세 정보 수집 (ID와 이름만)
                    # 먼저 AttachedInputs에서 이름 확인
                    input_name = getattr(att, "Name", "")
                    # 없으면 캐시된 이름 맵에서 찾기
                    if not input_name and att_id in input_name_map:
                        input_name = input_name_map[att_id]
                    # 그래도 없으면 ID 사용
                    if not input_name:
                        input_name = att_id
                    
                    input_details.append({
                        "id": att_id,
                        "name": input_name,
                    })

                channels.append({
                    "id": ch_id,
                    "name": ch_name,
                    "status": self._normalize_mdl_status(ch_state),
                    "service": "StreamLive",
                    "type": "channel",
                    "input_attachments": input_details,  # 실제 Input 정보 리스트
                    "input_endpoints": list(set(input_endpoints)),
                })
            return channels


        except Exception as e:
            logger.error(f"Failed to list MediaLive channels: {e}")
            return []

    def get_mdl_channel_status(self, channel_id: str) -> str:
        """Get MediaLive channel status."""
        try:
            req = mdl_models.DescribeStreamLiveChannelRequest()
            req.Id = channel_id
            resp = self.mdl_client.DescribeStreamLiveChannel(req)
            if hasattr(resp, "Info"):
                return self._normalize_mdl_status(getattr(resp.Info, "State", ""))
            return ChannelStatus.UNKNOWN
        except Exception as e:
            logger.error(f"Failed to get MediaLive channel status: {e}")
            return ChannelStatus.UNKNOWN

    def start_mdl_channel(self, channel_id: str) -> Dict:
        """Start MediaLive channel."""
        try:
            client = self._get_mdl_client()
            req = mdl_models.StartStreamLiveChannelRequest()
            req.Id = channel_id
            client.StartStreamLiveChannel(req)

            return {
                "success": True,
                "message": "MediaLive channel started successfully",
                "status": ChannelStatus.RUNNING,
            }

        except TencentCloudSDKException as e:
            logger.error(f"Failed to start MediaLive channel: {e}")
            return {
                "success": False,
                "message": f"Failed to start channel: {str(e)}",
                "status": ChannelStatus.UNKNOWN,
            }
        except Exception as e:
            logger.error(f"Failed to start MediaLive channel: {e}")
            return {
                "success": False,
                "message": f"Failed to start channel: {str(e)}",
                "status": ChannelStatus.UNKNOWN,
            }

    def stop_mdl_channel(self, channel_id: str) -> Dict:
        """Stop MediaLive channel."""
        try:
            client = self._get_mdl_client()
            req = mdl_models.StopStreamLiveChannelRequest()
            req.Id = channel_id
            client.StopStreamLiveChannel(req)

            return {
                "success": True,
                "message": "MediaLive channel stopped successfully",
                "status": ChannelStatus.STOPPED,
            }

        except TencentCloudSDKException as e:
            logger.error(f"Failed to stop MediaLive channel: {e}")
            return {
                "success": False,
                "message": f"Failed to stop channel: {str(e)}",
                "status": ChannelStatus.UNKNOWN,
            }
        except Exception as e:
            logger.error(f"Failed to stop MediaLive channel: {e}")
            return {
                "success": False,
                "message": f"Failed to stop channel: {str(e)}",
                "status": ChannelStatus.UNKNOWN,
            }

    # ===== StreamLink (MediaConnect) =====


    def _reconstruct_output_urls(self, og) -> List[str]:
        """Helper to reconstruct URLs from OutputGroup metadata if direct URL is missing."""
        urls = []
        try:
            protocol = getattr(og, "Protocol", "")
            
            # 1. Check RTMPSettings.Destinations (Common for RTMP Push to StreamLive)
            # This is the most important for StreamLink -> StreamLive linkage
            if protocol == "RTMP" and hasattr(og, "RTMPSettings") and og.RTMPSettings:
                dests = getattr(og.RTMPSettings, "Destinations", [])
                for d in dests:
                    url = getattr(d, "Url", "")
                    key = getattr(d, "StreamKey", "")
                    if url and key:
                        # Combine URL and StreamKey properly
                        # URL might end with / or not, StreamKey should be appended
                        if url.endswith("/"):
                            full_url = url + key
                        else:
                            full_url = url + "/" + key
                        urls.append(full_url)
                    elif url:
                        # URL only (might already contain stream key)
                        urls.append(url)
            
            # 2. Check SRTSettings.Destinations (Common for SRT Linkage)
            if protocol == "SRT" and hasattr(og, "SRTSettings") and og.SRTSettings:
                dests = getattr(og.SRTSettings, "Destinations", [])
                for d in dests:
                    dip = getattr(d, "Ip", "")
                    dport = getattr(d, "Port", 57716)
                    if dip:
                        urls.append(f"srt://{dip}:{dport}")

            # 3. Check StreamUrls (if available directly)
            if hasattr(og, "StreamUrls"):
                for stream_url in getattr(og, "StreamUrls", []):
                    url = getattr(stream_url, "Url", "")
                    if url:
                        urls.append(url)

            # 4. Fallback to OutputAddressList (Listener Mode or generic)
            addr_list = getattr(og, "OutputAddressList", [])
            for addr_info in addr_list:
                ip = getattr(addr_info, "Ip", "")
                if not ip: continue
                
                if protocol == "SRT":
                    port = 57716
                    if hasattr(og, "SRTSettings") and og.SRTSettings:
                        port = getattr(og.SRTSettings, "Port", 57716)
                    urls.append(f"srt://{ip}:{port}")
                elif protocol == "RTMP":
                    app = ""
                    stream = ""
                    if hasattr(og, "RTMPSettings") and og.RTMPSettings:
                        app = getattr(og.RTMPSettings, "AppName", "")
                        stream = getattr(og.RTMPSettings, "StreamKey", "")
                    urls.append(f"rtmp://{ip}/{app}/{stream}")
                else:
                    urls.append(f"{protocol.lower()}://{ip}")
        except Exception as e:
            logger.debug(f"Failed to reconstruct URL: {e}")
        return list(set(urls)) # Unique URLs


    def _fetch_single_flow_detail(self, flow_id: str) -> Dict:
        """Fetch detailed flow info for linkage metadata (Thread-safe)."""
        try:
            # Minimal jitter (50ms) to avoid thundering herd while maintaining speed
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
                        # Only include RTMP outputs that go to StreamLive (not RTMP_PULL for monitoring)
                        protocol = getattr(og, "Protocol", "")
                        output_name = getattr(og, "OutputName", "")
                        
                        # Skip RTMP_PULL outputs (these are for monitoring, not StreamLive)
                        if protocol == "RTMP_PULL":
                            continue
                        
                        # Prefer outputs that go to StreamLive (name contains "streamlive" or protocol is RTMP)
                        if protocol == "RTMP" or "streamlive" in output_name.lower():
                            # First try to reconstruct URLs (this handles RTMPSettings.Destinations properly)
                            reconstructed = self._reconstruct_output_urls(og)
                            if reconstructed:
                                output_urls.extend(reconstructed)
                            else:
                                # Fallback: Try direct StreamUrls if available
                                if hasattr(og, "StreamUrls"):
                                    for u in og.StreamUrls:
                                        if hasattr(u, "Url") and u.Url:
                                            output_urls.append(u.Url)
                
                # Input 정보 수집
                input_group = getattr(info, "InputGroup", [])
                input_details = []
                for inp in input_group:
                    input_id = getattr(inp, "InputId", "")
                    input_name = getattr(inp, "InputName", "")
                    protocol = getattr(inp, "Protocol", "")
                    
                    input_details.append({
                        "id": input_id or "",
                        "name": input_name or input_id or "Unknown",
                        "protocol": protocol or "",
                    })
                
                return {
                    "id": flow_id,
                    "output_urls": output_urls,
                    "status": self._normalize_streamlink_status(getattr(info, "State", "unknown")),
                    "inputs_count": len(input_group),
                    "input_details": input_details,  # 실제 Input 정보 리스트
                }
        except Exception as e:
            import traceback
            logger.error(f"Failed to fetch detail for {flow_id}: {e}")
            logger.error(traceback.format_exc())
            return {"id": flow_id, "output_urls": [], "status": "unknown", "inputs_count": 0, "input_details": []}

    def list_streamlink_inputs(self) -> List[Dict]:
        """
        List all StreamLink (MediaConnect) resources using official MDC SDK with parallel detailed fetching.
        """
        try:
            client = self._get_mdc_client()
            # 1. DescribeStreamLinkFlows (Batch Summary)
            req = mdc_models.DescribeStreamLinkFlowsRequest()
            req.PageNum = 1
            req.PageSize = 100
            resp = client.DescribeStreamLinkFlows(req)
            summary_list = resp.Infos if hasattr(resp, 'Infos') else []

            # 2. Parallel fetch detailed info for OutputGroups (thread-safe cache access)
            flow_details = {}
            cache_key = "mdc_linkage_details"
            need_fetch = True

            with self._cache_lock:
                cached = self._linkage_cache.get(cache_key)
                if cached and (time.time() - cached["timestamp"] < self._cache_ttl):
                    flow_details = cached["data"]
                    # Only trust cache if it has data for all summary_list IDs
                    summary_ids = set(f.FlowId for f in summary_list)
                    if summary_ids.issubset(set(flow_details.keys())):
                        need_fetch = False

            if need_fetch:
                ids = [f.FlowId for f in summary_list]
                results = list(self.executor.map(self._fetch_single_flow_detail, ids))
                flow_details = {}
                for res in results:
                    flow_details[res["id"]] = res
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
                    "input_attachments": detail.get("input_details", []),  # 실제 Input 정보 리스트
                })

            logger.info(f"Found {len(inputs)} StreamLink resources via official MDC SDK (Parallel Detailing)")
            return inputs

        except Exception as e:
            logger.error(f"Failed to list StreamLink flows: {e}")
            return []

    def get_streamlink_input_status(self, input_id: str) -> str:
        """Get StreamLink flow/input status."""
        try:
            # StreamLink Flow 상태 조회
            client = self._get_mdc_client()
            req = mdc_models.DescribeStreamLinkFlowRequest()
            req.FlowId = input_id
            resp = client.DescribeStreamLinkFlow(req)

            if hasattr(resp, "Info"):
                return self._normalize_streamlink_status(resp.Info.State)
            return ChannelStatus.UNKNOWN

        except TencentCloudSDKException as e:
            logger.error(f"Failed to get StreamLink flow status: {e}")
            return ChannelStatus.UNKNOWN
        except Exception as e:
            logger.error(f"Failed to get StreamLink flow status: {e}")
            return ChannelStatus.UNKNOWN

    def start_streamlink_input(self, input_id: str) -> Dict:
        """Start StreamLink flow/input."""
        try:
            # StreamLink Flow 시작 API
            # API: StartStreamLinkFlow
            client = self._get_mdc_client()
            client.call_json("StartStreamLinkFlow", {"FlowId": input_id})

            return {
                "success": True,
                "message": "StreamLink flow started successfully",
                "status": ChannelStatus.RUNNING,
            }

        except TencentCloudSDKException as e:
            logger.error(f"Failed to start StreamLink flow: {e}")
            return {
                "success": False,
                "message": f"Failed to start flow: {str(e)}",
                "status": ChannelStatus.UNKNOWN,
            }
        except Exception as e:
            logger.error(f"Failed to start StreamLink flow: {e}")
            return {
                "success": False,
                "message": f"Failed to start flow: {str(e)}",
                "status": ChannelStatus.UNKNOWN,
            }

    def stop_streamlink_input(self, input_id: str) -> Dict:
        """Stop StreamLink flow/input."""
        try:
            # StreamLink Flow 중지 API
            # API: StopStreamLinkFlow
            client = self._get_mdc_client()
            client.call_json("StopStreamLinkFlow", {"FlowId": input_id})

            return {
                "success": True,
                "message": "StreamLink flow stopped successfully",
                "status": ChannelStatus.STOPPED,
            }

        except TencentCloudSDKException as e:
            logger.error(f"Failed to stop StreamLink flow: {e}")
            return {
                "success": False,
                "message": f"Failed to stop flow: {str(e)}",
                "status": ChannelStatus.UNKNOWN,
            }
        except Exception as e:
            logger.error(f"Failed to stop StreamLink flow: {e}")
            return {
                "success": False,
                "message": f"Failed to stop flow: {str(e)}",
                "status": ChannelStatus.UNKNOWN,
            }

    def _normalize_streamlink_status(self, state: str) -> str:
        """Normalize StreamLink status to standard format."""
        # Handle potential integer/enum types from SDK
        state_str = str(state).lower()

        if any(x in state_str for x in ["running", "start", "active", "online"]):
            return ChannelStatus.RUNNING
        elif any(x in state_str for x in ["idle", "wait"]):
            return ChannelStatus.IDLE
        elif any(x in state_str for x in ["stop", "off"]):
            return ChannelStatus.STOPPED
        elif any(x in state_str for x in ["error", "alert", "failed", "fail", "except"]):
            return ChannelStatus.ERROR
        else:
            return ChannelStatus.UNKNOWN

    def list_streamlink_regions(self) -> Dict:
        """List available StreamLink regions."""
        try:
            client = self._get_mdc_client()
            resp = client.call_json("DescribeStreamLinkRegions", {})
            return resp
        except Exception as e:
            logger.error(f"Failed to list StreamLink regions: {e}")
            return {"error": str(e)}

    def create_streamlink_flow(self, flow_name: str, protocol: str = "SRT",
                                max_bandwidth: int = 10, options: Dict = None) -> Dict:
        """
        Create a new StreamLink flow.

        Args:
            flow_name: Name of the flow
            protocol: Protocol type (SRT, RTMP, RTP, HLS_PULL, RTMP_PULL)
            max_bandwidth: Maximum bandwidth in Mbps
            options: Additional options for the flow
        """
        try:
            options = options or {}

            input_config = {
                "InputName": f"{flow_name}_{protocol.lower()}_input",
                "Protocol": protocol.upper(),
                "Description": f"{protocol} input for {flow_name}",
                "AllowIpList": options.get("allow_ip_list", ["0.0.0.0/0"]),
            }

            # Protocol-specific settings
            if protocol.upper() == "SRT":
                input_config["SRTSettings"] = {
                    "Mode": options.get("srt_mode", "LISTENER"),
                    "Latency": options.get("srt_latency", 1000),
                    "RecvLatency": options.get("srt_recv_latency", 1000),
                    "PeerLatency": options.get("srt_peer_latency", 1000),
                    "PeerIdleTimeout": options.get("srt_idle_timeout", 5000),
                }
            elif protocol.upper() == "RTP":
                input_config["RTPSettings"] = {
                    "FEC": options.get("rtp_fec", "none"),
                    "IdleTimeout": options.get("rtp_idle_timeout", 5000),
                }

            params = {
                "FlowName": flow_name,
                "MaxBandwidth": max_bandwidth,
                "InputGroup": [input_config],
            }

            resp = self.mdc_client.call_json("CreateStreamLinkFlow", params)
            logger.info(f"Created StreamLink flow: {flow_name}")
            return resp

        except Exception as e:
            logger.error(f"Failed to create StreamLink flow: {e}")
            return {"error": str(e)}

    def delete_streamlink_flow(self, flow_id: str) -> Dict:
        """Delete a StreamLink flow."""
        try:
            resp = self.mdc_client.call_json("DeleteStreamLinkFlow", {"FlowId": flow_id})
            logger.info(f"Deleted StreamLink flow: {flow_id}")
            return {"success": True, "message": "Flow deleted successfully"}
        except Exception as e:
            logger.error(f"Failed to delete StreamLink flow: {e}")
            return {"success": False, "error": str(e)}

    def get_streamlink_flow_statistics(self, flow_id: str, input_output_id: str,
                                        type_: str = "input", period: str = "1min") -> Dict:
        """Get StreamLink flow media statistics."""
        try:
            from datetime import datetime, timedelta

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)

            params = {
                "FlowId": flow_id,
                "InputOutputId": input_output_id,
                "Type": type_,
                "Period": period,
                "StartTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "EndTime": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

            resp = self.mdc_client.call_json("DescribeStreamLinkFlowMediaStatistics", params)
            return resp
        except Exception as e:
            logger.error(f"Failed to get StreamLink flow statistics: {e}")
            return {"error": str(e)}

    def get_streamlink_flow_logs(self, flow_id: str) -> Dict:
        """Get StreamLink flow logs."""
        try:
            from datetime import datetime, timedelta

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)

            params = {
                "FlowId": flow_id,
                "StartTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "EndTime": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

            resp = self.mdc_client.call_json("DescribeStreamLinkFlowLogs", params)
            return resp
        except Exception as e:
            logger.error(f"Failed to get StreamLink flow logs: {e}")
            return {"error": str(e)}

    def get_streamlink_realtime_status(self, flow_id: str) -> Dict:
        """Get StreamLink flow realtime status."""
        try:
            resp = self.mdc_client.call_json("DescribeStreamLinkFlowRealtimeStatus", {"FlowId": flow_id})
            return resp
        except Exception as e:
            logger.error(f"Failed to get StreamLink realtime status: {e}")
            return {"error": str(e)}

    # ===== MediaLive Extended Operations =====

    def list_mdl_regions(self) -> Dict:
        """List available MediaLive regions."""
        try:
            client = self._get_mdl_client()
            req = mdl_models.DescribeStreamLiveRegionsRequest()
            resp = client.DescribeStreamLiveRegions(req)
            resp = {"Info": {"Regions": [{"Name": r.Name} for r in resp.Info.Regions]}}
            return resp
        except Exception as e:
            logger.error(f"Failed to list MediaLive regions: {e}")
            return {"error": str(e)}

    def list_mdl_inputs(self) -> List[Dict]:
        """List MediaLive inputs."""
        try:
            client = self._get_mdl_client()
            req = mdl_models.DescribeStreamLiveInputsRequest()
            resp = client.DescribeStreamLiveInputs(req)
            return [{"id": i.Id, "name": i.Name, "type": i.Type} for i in resp.Infos]
        except Exception as e:
            logger.error(f"Failed to list MediaLive inputs: {e}")
            return []

    def create_mdl_input(self, input_name: str, input_type: str = "RTMP_PUSH",
                         security_group_ids: List[str] = None) -> Dict:
        """Create a MediaLive input."""
        try:
            params = {
                "Name": input_name,
                "Type": input_type,
            }
            if security_group_ids:
                params["SecurityGroupIds"] = security_group_ids

            client = self._get_mdl_client()
            req = mdl_models.CreateStreamLiveInputRequest()
            req.Name = input_name
            req.Type = input_type
            resp = client.CreateStreamLiveInput(req)
            resp = {"Id": resp.Id}

            logger.info(f"Created MediaLive input: {input_name}")
            return resp
        except Exception as e:
            logger.error(f"Failed to create MediaLive input: {e}")
            return {"error": str(e)}

    def delete_mdl_input(self, input_id: str) -> Dict:
        """Delete a MediaLive input."""
        try:
            client = self._get_mdl_client()
            req = mdl_models.DeleteStreamLiveInputRequest()
            req.Id = input_id
            client.DeleteStreamLiveInput(req)
            return {"success": True, "message": "Input deleted successfully"}
        except Exception as e:
            logger.error(f"Failed to delete MediaLive input: {e}")
            return {"success": False, "error": str(e)}

    def list_mdl_security_groups(self) -> List[Dict]:
        """List MediaLive input security groups."""
        try:
            client = self._get_mdl_client()
            req = mdl_models.DescribeStreamLiveInputSecurityGroupsRequest()
            resp = client.DescribeStreamLiveInputSecurityGroups(req)
            return [{"Id": g.Id, "Name": g.Name, "Whitelist": g.Whitelist} for g in resp.Infos]
        except Exception as e:
            logger.error(f"Failed to list security groups: {e}")
            return []

    def get_mdl_channel_alerts(self, channel_id: str) -> Dict:
        """Get MediaLive channel alerts."""
        try:
            client = self._get_mdl_client()
            req = mdl_models.DescribeStreamLiveChannelAlertsRequest()
            req.ChannelId = channel_id
            resp = client.DescribeStreamLiveChannelAlerts(req)
            return resp
        except Exception as e:
            logger.error(f"Failed to get channel alerts: {e}")
            return {"error": str(e)}

    def get_mdl_channel_logs(self, channel_id: str) -> Dict:
        """Get MediaLive channel logs."""
        try:
            from datetime import datetime, timedelta

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)

            params = {
                "ChannelId": channel_id,
                "StartTime": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "EndTime": end_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

            client = self._get_mdl_client()
            req = mdl_models.DescribeStreamLiveChannelLogsRequest()
            req.ChannelId = channel_id
            req.StartTime = params["StartTime"]
            req.EndTime = params["EndTime"]
            resp = client.DescribeStreamLiveChannelLogs(req)
            return resp
        except Exception as e:
            logger.error(f"Failed to get channel logs: {e}")
            return {"error": str(e)}



    # ===== Unified Methods =====

    def list_all_resources(self) -> List[Dict]:
        """
        List all resources across all services.

        Returns:
            Combined list of all channels, streams, and media
        """
        all_resources = []
        
        # Parallelize the service-level fetching using shared executor
        f_mdl = self.executor.submit(self.list_mdl_channels)
        f_link = self.executor.submit(self.list_streamlink_inputs)
        
        mdl_channels = f_mdl.result()
        link_resources = f_link.result()
            
        all_resources.extend(mdl_channels)
        all_resources.extend(link_resources)

        logger.info(f"Total resources found: {len(all_resources)}")
        return all_resources

    def prewarm_cache(self):
        """Pre-warm linkage caches in background."""
        logger.info("Pre-warming Tencent Cloud linkage cache...")
        self.executor.submit(self.list_all_resources)

    def clear_cache(self):
        """Clear all caches (thread-safe)."""
        with self._cache_lock:
            self._linkage_cache.clear()
        logger.info("Linkage cache cleared")

    def get_resource_details(self, resource_id: str, service: str) -> Optional[Dict]:
        """
        Get detailed information about a specific resource.

        Args:
            resource_id: Resource ID
            service: Service name (StreamLive, StreamLink, CSS, VOD)

        Returns:
            Resource details dictionary
        """
        try:
            if service == "StreamLive" or service == "MediaLive":  # MediaLive는 호환성을 위해 유지
                # SDK 모듈 사용
                client = self._get_mdl_client()
                req = mdl_models.DescribeStreamLiveChannelRequest()
                req.Id = resource_id
                resp = client.DescribeStreamLiveChannel(req)

                info = resp.Info
                attached_inputs = info.AttachedInputs if hasattr(info, 'AttachedInputs') else []
                
                # Input 상세 정보 수집
                input_details = []
                for att in attached_inputs:
                    att_id = str(getattr(att, "Id", att)).strip()
                    input_name = getattr(att, "Name", "")
                    if not input_name:
                        input_name = att_id
                    input_details.append({
                        "id": att_id,
                        "name": input_name,
                    })
                
                return {
                    "id": info.Id,
                    "name": info.Name,
                    "status": self._normalize_mdl_status(info.State),
                    "service": "StreamLive",
                    "type": "channel",
                    "input_attachments": input_details,  # 실제 Input 정보 리스트
                    "output_groups": info.OutputGroups if hasattr(info, 'OutputGroups') else [],
                }

            elif service == "StreamLink" or service == "MediaConnect":
                # StreamLink Flow 상세 정보
                client = self._get_mdc_client()
                req = mdc_models.DescribeStreamLinkFlowRequest()
                req.FlowId = resource_id
                resp = client.DescribeStreamLinkFlow(req)
                
                if hasattr(resp, "Info"):
                    info = resp.Info
                else:
                    return None
                
                # OutputGroup에서 Output 정보 추출
                output_groups = getattr(info, "OutputGroup", [])
                outputs = []
                for output_group in output_groups:
                    stream_urls = getattr(output_group, "StreamUrls", [])
                    for stream_url in stream_urls:
                        outputs.append({
                            "OutputId": getattr(output_group, "OutputId", ""),
                            "OutputName": getattr(output_group, "OutputName", ""),
                            "OutputType": getattr(output_group, "OutputType", ""),
                            "Protocol": getattr(output_group, "Protocol", ""),
                            "Url": getattr(stream_url, "Url", ""),
                            "Label": getattr(stream_url, "Label", ""),
                            "Type": getattr(stream_url, "Type", ""),
                        })
                
                # Input 정보 수집
                input_group = getattr(info, "InputGroup", [])
                input_details = []
                for inp in input_group:
                    input_id = getattr(inp, "InputId", "")
                    input_name = getattr(inp, "InputName", "")
                    protocol = getattr(inp, "Protocol", "")
                    
                    input_details.append({
                        "id": input_id or "",
                        "name": input_name or input_id or "Unknown",
                        "protocol": protocol or "",
                    })
                
                return {
                    "id": getattr(info, "FlowId", resource_id),
                    "name": getattr(info, "FlowName", ""),
                    "status": self._normalize_streamlink_status(getattr(info, "State", "")),
                    "service": "StreamLink",
                    "type": "flow",
                    "input_group": input_details,  # 실제 Input 정보 리스트
                    "outputs": outputs,
                    "output_groups": output_groups,
                }

            # Add CSS and VOD details as needed

        except TencentCloudSDKException as e:
            logger.error(f"Failed to get resource details: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to get resource details: {e}")
            return None

    def control_resource(self, resource_id: str, service: str, action: str) -> Dict:
        """
        Control a resource (start/stop/restart).

        Args:
            resource_id: Resource ID
            service: Service name (StreamLive, StreamLink, CSS, VOD)
            action: Action to perform (start, stop, restart)

        Returns:
            Result dictionary
        """
        if service == "StreamLive" or service == "MediaLive":
            if action == "start":
                return self.start_mdl_channel(resource_id)
            elif action == "stop":
                return self.stop_mdl_channel(resource_id)
            elif action == "restart":
                stop_result = self.stop_mdl_channel(resource_id)
                if stop_result["success"]:
                    return self.start_mdl_channel(resource_id)
                return stop_result

        elif service == "StreamLink" or service == "MediaConnect":
            # StreamLink (MediaConnect) Input 제어
            if action == "start":
                return self.start_streamlink_input(resource_id)
            elif action == "stop":
                return self.stop_streamlink_input(resource_id)
            elif action == "restart":
                stop_result = self.stop_streamlink_input(resource_id)
                if stop_result["success"]:
                    return self.start_streamlink_input(resource_id)
                return stop_result

        elif service == "CSS":
            # Parse CSS stream ID (format: domain/app/stream)
            parts = resource_id.split("/")
            if len(parts) == 3:
                if action == "stop":
                    return self.drop_live_stream(parts[0], parts[1], parts[2])

        return {
            "success": False,
            "message": f"Action {action} not supported for {service}",
            "status": ChannelStatus.UNKNOWN,
        }

    # ===== Helper Methods =====

    def _normalize_mdl_status(self, state: str) -> str:
        """Normalize MediaLive status to standard format."""
        state_lower = state.lower()

        if "running" in state_lower or "start" in state_lower:
            return ChannelStatus.RUNNING
        elif "idle" in state_lower:
            return ChannelStatus.IDLE
        elif "stop" in state_lower:
            return ChannelStatus.STOPPED
        elif "error" in state_lower or "alert" in state_lower:
            return ChannelStatus.ERROR
        else:
            return ChannelStatus.UNKNOWN

    def search_resources(self, keywords: List[str]) -> List[Dict]:
        """
        Search resources by keywords.

        Args:
            keywords: List of search keywords

        Returns:
            Filtered list of resources
        """
        all_resources = self.list_all_resources()

        if not keywords:
            return all_resources

        filtered = []
        for resource in all_resources:
            name = resource.get("name", "").lower()
            if any(keyword.lower() in name for keyword in keywords):
                filtered.append(resource)

        return filtered

    def find_connected_resources(self) -> List[Dict]:
        """
        Find connections between StreamLink Flows and StreamLive Channels.

        Returns:
            List of connection dictionaries with:
            - flow_id, flow_name, output_name, output_url
            - channel_id, channel_name, input_id, input_name
        """
        from urllib.parse import urlparse

        def normalize_url(url):
            """Normalize URL for comparison."""
            if not url:
                return ""
            try:
                parsed = urlparse(url)
                return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            except:
                return url.lower()

        connections = []

        try:
            # StreamLink Flow 목록
            streamlink_flows = self.list_streamlink_inputs()
            
            # StreamLive Channel 목록
            streamlive_channels = self.list_mdl_channels()

            # StreamLink Flow의 Output URL 수집
            flow_outputs_map = {}
            for flow in streamlink_flows:
                flow_id = flow.get('id')
                flow_name = flow.get('name')
                
                flow_details = self.get_resource_details(flow_id, "StreamLink")
                if not flow_details:
                    continue
                    
                flow_outputs = flow_details.get('outputs', [])
                output_urls = []
                for output in flow_outputs:
                    output_url = output.get('Url', '')
                    if output_url:
                        output_urls.append({
                            'url': output_url,
                            'name': output.get('OutputName', ''),
                            'protocol': output.get('Protocol', ''),
                        })
                
                if output_urls:
                    flow_outputs_map[flow_id] = {
                        'flow_name': flow_name,
                        'outputs': output_urls,
                    }

            # StreamLive Channel의 Input URL과 매칭
            for channel in streamlive_channels:
                channel_id = channel.get('id')
                channel_name = channel.get('name')
                
                channel_details = self.get_resource_details(channel_id, "StreamLive")
                if not channel_details:
                    continue
                    
                input_attachments = channel_details.get('input_attachments', [])
                
                for input_att in input_attachments:
                    input_id = input_att.get('Id')
                    
                    try:
                        client = self._get_mdl_client()
                        req = mdl_models.DescribeStreamLiveInputRequest()
                        req.Id = input_id
                        resp = client.DescribeStreamLiveInput(req)
                        input_info = resp.Info
                        input_name = getattr(input_info, "Name", "")
                        input_type = getattr(input_info, "Type", "")
                        input_settings = getattr(input_info, "InputSettings", [])
                        
                        for setting in input_settings:
                            source_url = getattr(setting, "SourceUrl", "")
                            input_address = getattr(setting, "InputAddress", "")
                            
                            input_url = source_url or input_address
                            if not input_url:
                                continue
                                
                            normalized_input = normalize_url(input_url)
                            
                            # StreamLink Flow의 Output URL과 비교
                            for flow_id, flow_data in flow_outputs_map.items():
                                for output in flow_data['outputs']:
                                    output_url = output['url']
                                    normalized_output = normalize_url(output_url)
                                    
                                    # 정확한 매칭
                                    if normalized_output and normalized_input:
                                        if normalized_output == normalized_input or \
                                           normalized_output in normalized_input or \
                                           (normalized_output.split('/')[-1] in normalized_input):
                                            connections.append({
                                                'flow_id': flow_id,
                                                'flow_name': flow_data['flow_name'],
                                                'output_name': output['name'],
                                                'output_url': output_url,
                                                'channel_id': channel_id,
                                                'channel_name': channel_name,
                                                'input_id': input_id,
                                                'input_name': input_name,
                                                'input_type': input_type,
                                                'input_url': input_url,
                                            })
                    except Exception as e:
                        logger.debug(f"Failed to check input {input_id}: {e}")

            # 중복 제거
            unique_connections = {}
            for conn in connections:
                key = f"{conn['flow_id']}:{conn['channel_id']}"
                if key not in unique_connections:
                    unique_connections[key] = conn

            logger.info(f"Found {len(unique_connections)} StreamLink-StreamLive connections")
            return list(unique_connections.values())

        except Exception as e:
            logger.error(f"Failed to find connected resources: {e}")
            return []
