"""Resource data models."""
from typing import List, Optional

from pydantic import BaseModel, Field

from .enums import ChannelStatus, ServiceType


class InputAttachment(BaseModel):
    """Input attachment information."""

    id: str
    name: str
    protocol: Optional[str] = None


class Resource(BaseModel):
    """Tencent Cloud resource (StreamLive channel or StreamLink flow)."""

    id: str
    name: str
    status: ChannelStatus = ChannelStatus.UNKNOWN
    service: ServiceType
    type: str = "channel"  # "channel" or "flow"
    input_attachments: List[InputAttachment] = Field(default_factory=list)
    input_endpoints: List[str] = Field(default_factory=list)
    output_urls: List[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class ResourceHierarchy(BaseModel):
    """Hierarchical grouping of parent resource with linked children."""

    parent: Resource
    children: List[Resource] = Field(default_factory=list)
