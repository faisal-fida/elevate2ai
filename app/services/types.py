from typing import Dict, List, Optional, TypedDict, Literal, Any
from pydantic import BaseModel, Field


# Common type definitions
MediaType = Literal["image", "video"]
PlatformType = Literal["instagram", "linkedin", "tiktok"]
ContentType = Literal[
    "events", "destination", "promo", "tips", "seasonal", "reels", "generic"
]
WorkflowStateType = Literal[
    "init",
    "waiting_for_promo",
    "waiting_for_approval",
    "content_type_selection",
    "platform_selection_for_content",
    "caption_input",
    "schedule_selection",
    "confirmation",
    "image_inclusion_decision",
    "post_execution",
    # New states for template-specific input collection
    "waiting_for_destination",
    "waiting_for_event_name",
    "waiting_for_price",
    "waiting_for_event_image",
    # Media selection states
    "media_source_selection",
    "waiting_for_media_upload",
    "video_selection",
]

# Media source options
MediaSourceType = Literal["upload", "search"]


class MediaItem(Dict[str, str]):
    """Media item for WhatsApp messages"""

    pass


class ButtonItem(TypedDict):
    """Type definition for a button item"""

    id: str
    title: str


class SectionItem(TypedDict):
    """Type definition for a section item"""

    title: str
    rows: List[ButtonItem]


class WorkflowContext(BaseModel):
    """Context for workflow state"""

    # Core content fields
    caption: str = ""
    original_text: str = ""
    selected_content_type: str = ""

    # Platform selection
    selected_platforms: List[str] = Field(default_factory=list)
    content_types: Dict[str, str] = Field(default_factory=dict)
    supported_platforms: List[str] = Field(
        default_factory=lambda: ["instagram", "linkedin"]
    )

    # Media fields
    selected_image: str = ""
    selected_video: str = ""
    image_urls: List[str] = Field(default_factory=list)
    video_urls: List[str] = Field(default_factory=list)
    is_video_content: bool = False

    # Template-specific fields
    event_name: str = ""
    destination_name: str = ""
    price_text: str = ""
    event_image: str = ""
    template_id: str = ""
    template_type: str = ""
    template_data: Dict[str, Any] = Field(default_factory=dict)

    # Platform-specific outputs
    platform_images: Dict[str, str] = Field(default_factory=dict)
    platform_specific_captions: Dict[str, str] = Field(default_factory=dict)

    # Workflow control
    schedule_time: str = ""
    media_source: str = "search"
    waiting_for_image_decision: bool = False

    # Status tracking
    post_status: Dict[str, bool] = Field(default_factory=dict)
    current_platform_index: int = 0

    # Media metadata from WhatsApp
    media_metadata: Optional[Dict[str, Dict[str, str]]] = None

    # Legacy/compatibility fields - consider removing in future versions
    include_images: bool = True
    video_background: str = ""  # Used by some templates

    class Config:
        arbitrary_types_allowed = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for state manager compatibility"""
        return self.model_dump()
