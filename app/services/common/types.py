from typing import Dict, List, Optional, TypedDict, Literal
from dataclasses import dataclass


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
    selected_image: str = ""  # The selected image URL

    # Fields for social media posting workflow
    selected_content_type: str = ""  # The content type selected by the user
    selected_platforms: List[str] = None  # Platforms selected for the content type
    content_types: Dict[str, str] = None  # For backward compatibility
    schedule_time: str = ""
    platform_specific_captions: Dict[str, str] = None
    current_platform_index: int = 0
    post_status: Dict[str, bool] = None
    supported_platforms: List[str] = (
        None  # Platforms that support the selected content type
    )
    platform_images: Dict[str, str] = None  # Platform-specific edited images

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
        if self.supported_platforms is None:
            self.supported_platforms = []
        if self.platform_images is None:
            self.platform_images = {}
