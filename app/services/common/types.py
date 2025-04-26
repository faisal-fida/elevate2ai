from typing import Dict, List, Optional, TypedDict, Literal
from dataclasses import dataclass


# Common type definitions
MediaType = Literal["image", "video"]
PlatformType = Literal["instagram", "linkedin", "tiktok"]
ContentType = Literal["events", "destination", "promo", "tips", "seasonal", "reels", "generic"]
WorkflowStateType = Literal[
    "init",
    "waiting_for_promo",
    "waiting_for_approval",
    "platform_selection",
    "content_type_selection",
    "same_content_confirmation",
    "platform_specific_content",
    "caption_input",
    "schedule_selection",
    "confirmation",
    "post_execution",
]


class MediaItem(TypedDict):
    """Type definition for a media item"""

    type: MediaType
    url: str
    caption: Optional[str]


class ButtonItem(TypedDict):
    """Type definition for a button item"""

    id: str
    title: str


class SectionItem(TypedDict):
    """Type definition for a section item"""

    title: str
    rows: List[ButtonItem]


@dataclass
class WorkflowContext:
    """Data class for workflow context"""

    # Original fields
    caption: str = ""
    image_urls: List[str] = None
    original_text: str = ""

    # Fields for social media posting workflow
    selected_platforms: List[str] = None
    content_types: Dict[str, str] = None
    same_content_across_platforms: bool = False
    schedule_time: str = ""
    platform_specific_captions: Dict[str, str] = None
    current_platform_index: int = 0
    post_status: Dict[str, bool] = None
    common_content_types: List[str] = None

    def __post_init__(self):
        """Initialize default values for None fields"""
        if self.image_urls is None:
            self.image_urls = []
        if self.selected_platforms is None:
            self.selected_platforms = []
        if self.content_types is None:
            self.content_types = {}
        if self.platform_specific_captions is None:
            self.platform_specific_captions = {}
        if self.post_status is None:
            self.post_status = {}
        if self.common_content_types is None:
            self.common_content_types = []
