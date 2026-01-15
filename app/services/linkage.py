"""Service for determining linkage between StreamLink and StreamLive resources."""
import logging
import re
from typing import Dict, List, Set

from app.config import get_settings

logger = logging.getLogger(__name__)


class LinkageMatcher:
    """
    Determines technical linkage between StreamLink flows and StreamLive channels
    by matching output URLs to input endpoints.
    """

    IGNORE_TOKENS = frozenset([
        "rtmp", "srt", "rtmp_pull", "rtp", "hls",
        "1935", "57716", "live", "http", "https"
    ])

    @classmethod
    def normalize_url(cls, url: str) -> str:
        """Normalize URL for comparison."""
        if not url:
            return ""
        return re.sub(r"/+", "/", url.strip().lower()).strip("/")

    @classmethod
    def extract_url_parts(cls, url: str) -> List[str]:
        """Extract meaningful parts from URL."""
        if not url:
            return []
        url_clean = url.strip().lower()
        parts = re.split(r"[:/@?]", url_clean)
        return [p for p in parts if p and p not in cls.IGNORE_TOKENS]

    @classmethod
    def get_stream_key(cls, url: str) -> str:
        """Extract the stream key from URL."""
        parts = cls.extract_url_parts(url)
        return parts[-1] if parts else ""

    @classmethod
    def is_url_match(cls, output_url: str, input_endpoint: str) -> bool:
        """Check if a StreamLink output URL matches a StreamLive input endpoint."""
        if not output_url or not input_endpoint:
            return False

        out_norm = cls.normalize_url(output_url)
        in_norm = cls.normalize_url(input_endpoint)

        if out_norm == in_norm:
            return True

        out_key = cls.get_stream_key(output_url)
        in_key = cls.get_stream_key(input_endpoint)

        if out_key and in_key:
            settings = get_settings()
            if len(out_key) >= settings.MIN_STREAM_KEY_LENGTH and out_key == in_key:
                return True

        return False

    @classmethod
    def find_linked_flows(
        cls,
        live_channel: Dict,
        link_flows: List[Dict],
        exclude_ids: Set[str] = None,
    ) -> List[Dict]:
        """Find StreamLink flows that feed into a StreamLive channel."""
        exclude_ids = exclude_ids or set()
        endpoints = live_channel.get("input_endpoints", [])
        linked = []

        for flow in link_flows:
            if flow.get("id") in exclude_ids:
                continue

            output_urls = flow.get("output_urls", [])
            is_linked = False

            for out_url in output_urls:
                for endpoint in endpoints:
                    if cls.is_url_match(out_url, endpoint):
                        is_linked = True
                        break
                if is_linked:
                    break

            if is_linked:
                linked.append(flow)

        return linked


class ResourceHierarchyBuilder:
    """Builds hierarchy of resources based on technical linkage."""

    @staticmethod
    def build_hierarchy(channels: List[Dict]) -> List[Dict]:
        """Group channels into parent-children hierarchy based on linkage."""
        lives = [c for c in channels if c.get("service") == "StreamLive"]
        links = [c for c in channels if c.get("service") == "StreamLink"]

        hierarchy = []
        assigned_link_ids = set()

        for live in lives:
            linked_flows = LinkageMatcher.find_linked_flows(live, links, assigned_link_ids)

            for flow in linked_flows:
                assigned_link_ids.add(flow["id"])

            hierarchy.append({"parent": live, "children": linked_flows})

        for link in links:
            if link["id"] not in assigned_link_ids:
                hierarchy.append({"parent": link, "children": []})

        return hierarchy


class ResourceFilter:
    """Filter resources based on keyword, status, and service criteria."""

    @staticmethod
    def matches_keyword(resource: Dict, keyword: str) -> bool:
        """Check if resource matches keyword search."""
        if not keyword:
            return True
        keyword_lower = keyword.lower()
        name = resource.get("name", "").lower()
        resource_id = resource.get("id", "").lower()
        return keyword_lower in name or keyword_lower in resource_id

    @staticmethod
    def matches_status(resource: Dict, status_filter: str) -> bool:
        """Check if resource matches status filter."""
        if status_filter == "all":
            return True
        resource_status = resource.get("status", "")
        if status_filter == "stopped":
            return resource_status in ["stopped", "idle"]
        return resource_status == status_filter

    @staticmethod
    def matches_service(resource: Dict, service_filter: str) -> bool:
        """Check if resource matches service filter."""
        if service_filter == "all":
            return True
        return resource.get("service") == service_filter

    @classmethod
    def filter_hierarchy(
        cls,
        hierarchy: List[Dict],
        service_filter: str = "all",
        status_filter: str = "all",
        keyword: str = "",
    ) -> List[Dict]:
        """Apply hierarchy-aware filtering to resource groups."""
        filtered = []

        for group in hierarchy:
            parent = group["parent"]
            children = group["children"]

            p_keyword = cls.matches_keyword(parent, keyword)
            p_status = cls.matches_status(parent, status_filter)
            p_service = cls.matches_service(parent, service_filter)

            if p_keyword:
                matching_children = [
                    c
                    for c in children
                    if cls.matches_status(c, status_filter)
                    and cls.matches_service(c, service_filter)
                ]

                if p_service and p_status:
                    filtered.append({"parent": parent, "children": matching_children})
                elif matching_children:
                    filtered.append({"parent": parent, "children": matching_children})
            else:
                matching_children = [
                    c
                    for c in children
                    if cls.matches_keyword(c, keyword)
                    and cls.matches_status(c, status_filter)
                    and cls.matches_service(c, service_filter)
                ]
                if matching_children:
                    filtered.append({"parent": parent, "children": matching_children})

        filtered.sort(key=lambda x: x["parent"].get("name", ""))
        return filtered


def group_and_filter_resources(
    channels: List[Dict],
    service_filter: str = "all",
    status_filter: str = "all",
    keyword: str = "",
) -> List[Dict]:
    """Convenience function to build hierarchy and apply filters."""
    hierarchy = ResourceHierarchyBuilder.build_hierarchy(channels)
    return ResourceFilter.filter_hierarchy(hierarchy, service_filter, status_filter, keyword)
