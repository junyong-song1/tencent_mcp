"""Tests for TencentCloudClient with mocking."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock config before importing TencentCloudClient
@pytest.fixture(autouse=True)
def mock_config():
    """Mock config for all tests."""
    with patch.dict('os.environ', {
        'TENCENT_SECRET_ID': 'test_secret_id',
        'TENCENT_SECRET_KEY': 'test_secret_key',
        'TENCENT_REGION': 'ap-seoul',
    }):
        yield


class MockChannelInfo:
    """Mock MDL Channel Info response."""
    def __init__(self, channel_id, name, state, attached_inputs=None):
        self.Id = channel_id
        self.Name = name
        self.State = state
        self.AttachedInputs = attached_inputs or []


class MockInputInfo:
    """Mock MDL Input Info response."""
    def __init__(self, input_id, name, input_settings=None):
        self.Id = input_id
        self.Name = name
        self.InputSettings = input_settings or []
        self.InputAddressList = []


class MockFlowInfo:
    """Mock MDC Flow Info response."""
    def __init__(self, flow_id, flow_name, state):
        self.FlowId = flow_id
        self.FlowName = flow_name
        self.State = state


class MockAttachedInput:
    """Mock attached input info."""
    def __init__(self, input_id, name=""):
        self.Id = input_id
        self.Name = name


class TestTencentCloudClient:
    """Test cases for TencentCloudClient."""

    @pytest.fixture
    def client(self):
        """Create a TencentCloudClient with mocked SDK clients."""
        with patch('tencent_cloud_client.credential.Credential'):
            with patch('tencent_cloud_client.mdl_client.MdlClient') as mock_mdl:
                with patch('tencent_cloud_client.mdc_client.MdcClient') as mock_mdc:
                    from tencent_cloud_client import TencentCloudClient
                    client = TencentCloudClient()
                    client._mock_mdl = mock_mdl
                    client._mock_mdc = mock_mdc
                    return client

    def test_init(self, client):
        """Test client initialization."""
        assert client._cache_ttl == 120
        assert client._linkage_cache == {}
        assert client._cache_lock is not None

    def test_normalize_mdl_status_running(self, client):
        """Test MDL status normalization for running states."""
        assert client._normalize_mdl_status("RUNNING") == "running"
        assert client._normalize_mdl_status("starting") == "running"
        assert client._normalize_mdl_status("Started") == "running"

    def test_normalize_mdl_status_stopped(self, client):
        """Test MDL status normalization for stopped states."""
        assert client._normalize_mdl_status("IDLE") == "idle"
        assert client._normalize_mdl_status("stopped") == "stopped"
        assert client._normalize_mdl_status("STOPPED") == "stopped"

    def test_normalize_mdl_status_error(self, client):
        """Test MDL status normalization for error states."""
        assert client._normalize_mdl_status("error") == "error"
        assert client._normalize_mdl_status("ALERT") == "error"

    def test_normalize_mdl_status_unknown(self, client):
        """Test MDL status normalization for unknown states."""
        assert client._normalize_mdl_status("unknown_state") == "unknown"
        assert client._normalize_mdl_status("") == "unknown"

    def test_normalize_streamlink_status(self, client):
        """Test StreamLink status normalization."""
        assert client._normalize_streamlink_status("running") == "running"
        assert client._normalize_streamlink_status("active") == "running"
        assert client._normalize_streamlink_status("idle") == "idle"
        assert client._normalize_streamlink_status("stopped") == "stopped"
        assert client._normalize_streamlink_status("error") == "error"

    @patch('tencent_cloud_client.mdl_client.MdlClient')
    @patch('tencent_cloud_client.credential.Credential')
    def test_list_mdl_channels_success(self, mock_cred, mock_mdl_cls):
        """Test listing MDL channels successfully."""
        # Setup mock response
        mock_client = Mock()
        mock_mdl_cls.return_value = mock_client

        mock_response = Mock()
        mock_response.Infos = [
            MockChannelInfo("ch-001", "Test Channel 1", "RUNNING", [MockAttachedInput("inp-001")]),
            MockChannelInfo("ch-002", "Test Channel 2", "IDLE", []),
        ]
        mock_client.DescribeStreamLiveChannels.return_value = mock_response

        # Mock inputs response
        mock_inputs_response = Mock()
        mock_inputs_response.Infos = [
            MockInputInfo("inp-001", "Input 1"),
        ]
        mock_client.DescribeStreamLiveInputs.return_value = mock_inputs_response

        from tencent_cloud_client import TencentCloudClient
        client = TencentCloudClient()
        channels = client.list_mdl_channels()

        assert len(channels) == 2
        assert channels[0]["id"] == "ch-001"
        assert channels[0]["name"] == "Test Channel 1"
        assert channels[0]["status"] == "running"
        assert channels[0]["service"] == "StreamLive"

    @patch('tencent_cloud_client.mdl_client.MdlClient')
    @patch('tencent_cloud_client.credential.Credential')
    def test_list_mdl_channels_empty(self, mock_cred, mock_mdl_cls):
        """Test listing MDL channels when none exist."""
        mock_client = Mock()
        mock_mdl_cls.return_value = mock_client

        mock_response = Mock()
        mock_response.Infos = []
        mock_client.DescribeStreamLiveChannels.return_value = mock_response

        mock_inputs_response = Mock()
        mock_inputs_response.Infos = []
        mock_client.DescribeStreamLiveInputs.return_value = mock_inputs_response

        from tencent_cloud_client import TencentCloudClient
        client = TencentCloudClient()
        channels = client.list_mdl_channels()

        assert channels == []

    @patch('tencent_cloud_client.mdl_client.MdlClient')
    @patch('tencent_cloud_client.credential.Credential')
    def test_list_mdl_channels_api_error(self, mock_cred, mock_mdl_cls):
        """Test listing MDL channels when API fails."""
        mock_client = Mock()
        mock_mdl_cls.return_value = mock_client
        mock_client.DescribeStreamLiveChannels.side_effect = Exception("API Error")

        from tencent_cloud_client import TencentCloudClient
        client = TencentCloudClient()
        channels = client.list_mdl_channels()

        assert channels == []

    @patch('tencent_cloud_client.mdl_client.MdlClient')
    @patch('tencent_cloud_client.credential.Credential')
    def test_start_mdl_channel_success(self, mock_cred, mock_mdl_cls):
        """Test starting MDL channel successfully."""
        mock_client = Mock()
        mock_mdl_cls.return_value = mock_client
        mock_client.StartStreamLiveChannel.return_value = Mock()

        from tencent_cloud_client import TencentCloudClient
        client = TencentCloudClient()
        result = client.start_mdl_channel("ch-001")

        assert result["success"] is True
        assert result["status"] == "running"
        mock_client.StartStreamLiveChannel.assert_called_once()

    @patch('tencent_cloud_client.mdl_client.MdlClient')
    @patch('tencent_cloud_client.credential.Credential')
    def test_stop_mdl_channel_success(self, mock_cred, mock_mdl_cls):
        """Test stopping MDL channel successfully."""
        mock_client = Mock()
        mock_mdl_cls.return_value = mock_client
        mock_client.StopStreamLiveChannel.return_value = Mock()

        from tencent_cloud_client import TencentCloudClient
        client = TencentCloudClient()
        result = client.stop_mdl_channel("ch-001")

        assert result["success"] is True
        assert result["status"] == "stopped"

    @patch('tencent_cloud_client.mdl_client.MdlClient')
    @patch('tencent_cloud_client.credential.Credential')
    def test_start_mdl_channel_failure(self, mock_cred, mock_mdl_cls):
        """Test starting MDL channel when API fails."""
        from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

        mock_client = Mock()
        mock_mdl_cls.return_value = mock_client
        mock_client.StartStreamLiveChannel.side_effect = TencentCloudSDKException("Error", "Test error")

        from tencent_cloud_client import TencentCloudClient
        client = TencentCloudClient()
        result = client.start_mdl_channel("ch-001")

        assert result["success"] is False
        assert "Failed" in result["message"]

    @patch('tencent_cloud_client.mdc_client.MdcClient')
    @patch('tencent_cloud_client.credential.Credential')
    def test_list_streamlink_inputs_success(self, mock_cred, mock_mdc_cls):
        """Test listing StreamLink inputs successfully."""
        mock_client = Mock()
        mock_mdc_cls.return_value = mock_client

        # Mock flows list response
        mock_flows_response = Mock()
        mock_flows_response.Infos = [
            MockFlowInfo("flow-001", "Test Flow 1", "running"),
            MockFlowInfo("flow-002", "Test Flow 2", "idle"),
        ]
        mock_client.DescribeStreamLinkFlows.return_value = mock_flows_response

        # Mock flow detail response
        mock_detail_response = Mock()
        mock_detail_response.Info = Mock()
        mock_detail_response.Info.OutputGroup = []
        mock_detail_response.Info.InputGroup = []
        mock_detail_response.Info.State = "running"
        mock_client.DescribeStreamLinkFlow.return_value = mock_detail_response

        from tencent_cloud_client import TencentCloudClient
        with patch('tencent_cloud_client.mdl_client.MdlClient'):
            client = TencentCloudClient()
            inputs = client.list_streamlink_inputs()

        assert len(inputs) == 2
        assert inputs[0]["service"] == "StreamLink"

    def test_control_resource_unsupported_action(self, client):
        """Test control_resource with unsupported action."""
        result = client.control_resource("ch-001", "StreamLive", "invalid_action")
        assert result["success"] is False
        assert "not supported" in result["message"]

    def test_control_resource_unsupported_service(self, client):
        """Test control_resource with unsupported service."""
        result = client.control_resource("ch-001", "UnknownService", "start")
        assert result["success"] is False

    def test_clear_cache(self, client):
        """Test cache clearing."""
        client._linkage_cache["test_key"] = {"data": "test"}
        assert len(client._linkage_cache) == 1

        client.clear_cache()

        assert len(client._linkage_cache) == 0


class TestTencentCloudClientCache:
    """Test cases for caching behavior."""

    @patch('tencent_cloud_client.mdl_client.MdlClient')
    @patch('tencent_cloud_client.credential.Credential')
    def test_cache_hit(self, mock_cred, mock_mdl_cls):
        """Test that cached data is used within TTL."""
        mock_client = Mock()
        mock_mdl_cls.return_value = mock_client

        mock_response = Mock()
        mock_response.Infos = [MockChannelInfo("ch-001", "Test", "RUNNING")]
        mock_client.DescribeStreamLiveChannels.return_value = mock_response

        # Need at least one input for cache to have data (empty dict is falsy)
        mock_inputs_response = Mock()
        mock_inputs_response.Infos = [MockInputInfo("inp-001", "Test Input")]
        mock_client.DescribeStreamLiveInputs.return_value = mock_inputs_response

        from tencent_cloud_client import TencentCloudClient
        client = TencentCloudClient()

        # First call - should hit API
        client.list_mdl_channels()
        call_count_1 = mock_client.DescribeStreamLiveInputs.call_count

        # Second call - should use cache
        client.list_mdl_channels()
        call_count_2 = mock_client.DescribeStreamLiveInputs.call_count

        # Should not call API again for inputs (cached)
        assert call_count_2 == call_count_1

    @patch('tencent_cloud_client.mdl_client.MdlClient')
    @patch('tencent_cloud_client.credential.Credential')
    def test_cache_thread_safety(self, mock_cred, mock_mdl_cls):
        """Test that cache operations are thread-safe."""
        import threading

        mock_client = Mock()
        mock_mdl_cls.return_value = mock_client

        mock_response = Mock()
        mock_response.Infos = [MockChannelInfo("ch-001", "Test", "RUNNING")]
        mock_client.DescribeStreamLiveChannels.return_value = mock_response

        mock_inputs_response = Mock()
        mock_inputs_response.Infos = []
        mock_client.DescribeStreamLiveInputs.return_value = mock_inputs_response

        from tencent_cloud_client import TencentCloudClient
        client = TencentCloudClient()

        errors = []

        def concurrent_access():
            try:
                for _ in range(10):
                    client.list_mdl_channels()
                    client.clear_cache()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=concurrent_access) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors: {errors}"


class TestLinkageService:
    """Test cases for LinkageService."""

    def test_normalize_url(self):
        """Test URL normalization."""
        from linkage_service import LinkageMatcher

        assert LinkageMatcher.normalize_url("rtmp://host//path/") == "rtmp:/host/path"
        assert LinkageMatcher.normalize_url("  srt://host:1234  ") == "srt:/host:1234"
        assert LinkageMatcher.normalize_url("") == ""

    def test_is_url_match_exact(self):
        """Test exact URL matching."""
        from linkage_service import LinkageMatcher

        assert LinkageMatcher.is_url_match(
            "rtmp://host/app/stream",
            "rtmp://host/app/stream"
        )

        assert LinkageMatcher.is_url_match(
            "rtmp://host//app//stream/",
            "rtmp://host/app/stream"
        )

    def test_is_url_match_stream_key(self):
        """Test stream key matching."""
        from linkage_service import LinkageMatcher

        # Long stream keys (>= MIN_STREAM_KEY_LENGTH=10) should match
        assert LinkageMatcher.is_url_match(
            "rtmp://host1/live/stream_key_12345678",
            "rtmp://host2/app/stream_key_12345678"
        )

        # Short stream keys (< 10 chars) should not match
        assert not LinkageMatcher.is_url_match(
            "rtmp://host1/live/short",
            "rtmp://host2/app/short"
        )

    def test_is_url_match_no_match(self):
        """Test non-matching URLs."""
        from linkage_service import LinkageMatcher

        assert not LinkageMatcher.is_url_match(
            "rtmp://host/app/stream1",
            "rtmp://host/app/stream2"
        )

        assert not LinkageMatcher.is_url_match("", "rtmp://host/app")
        assert not LinkageMatcher.is_url_match("rtmp://host/app", "")

    def test_build_hierarchy(self):
        """Test hierarchy building."""
        from linkage_service import ResourceHierarchyBuilder

        channels = [
            {"id": "ch-001", "service": "StreamLive", "input_endpoints": ["rtmp://host/app/stream_key_1234567890"]},
            {"id": "flow-001", "service": "StreamLink", "output_urls": ["rtmp://host/app/stream_key_1234567890"]},
            {"id": "flow-002", "service": "StreamLink", "output_urls": ["rtmp://other/path"]},
        ]

        hierarchy = ResourceHierarchyBuilder.build_hierarchy(channels)

        assert len(hierarchy) == 2  # One group for ch-001 + flow-001, one standalone for flow-002

        # Find the StreamLive group
        live_group = next(g for g in hierarchy if g["parent"]["id"] == "ch-001")
        assert len(live_group["children"]) == 1
        assert live_group["children"][0]["id"] == "flow-001"

    def test_filter_hierarchy_by_keyword(self):
        """Test filtering by keyword."""
        from linkage_service import ResourceFilter

        hierarchy = [
            {"parent": {"id": "ch-001", "name": "Sports Channel", "status": "running", "service": "StreamLive"}, "children": []},
            {"parent": {"id": "ch-002", "name": "News Channel", "status": "running", "service": "StreamLive"}, "children": []},
        ]

        filtered = ResourceFilter.filter_hierarchy(hierarchy, keyword="sports")

        assert len(filtered) == 1
        assert filtered[0]["parent"]["name"] == "Sports Channel"

    def test_filter_hierarchy_by_status(self):
        """Test filtering by status."""
        from linkage_service import ResourceFilter

        hierarchy = [
            {"parent": {"id": "ch-001", "name": "Channel 1", "status": "running", "service": "StreamLive"}, "children": []},
            {"parent": {"id": "ch-002", "name": "Channel 2", "status": "stopped", "service": "StreamLive"}, "children": []},
        ]

        filtered = ResourceFilter.filter_hierarchy(hierarchy, status_filter="running")

        assert len(filtered) == 1
        assert filtered[0]["parent"]["status"] == "running"

    def test_filter_hierarchy_by_service(self):
        """Test filtering by service."""
        from linkage_service import ResourceFilter

        hierarchy = [
            {"parent": {"id": "ch-001", "name": "Channel 1", "status": "running", "service": "StreamLive"}, "children": []},
            {"parent": {"id": "flow-001", "name": "Flow 1", "status": "running", "service": "StreamLink"}, "children": []},
        ]

        filtered = ResourceFilter.filter_hierarchy(hierarchy, service_filter="StreamLink")

        assert len(filtered) == 1
        assert filtered[0]["parent"]["service"] == "StreamLink"
