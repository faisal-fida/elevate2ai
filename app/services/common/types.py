from typing import Dict, List, Optional, TypedDict, Literal, Any
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

    # New fields for image inclusion feature
    include_images: bool = True  # Default to including images
    waiting_for_image_decision: bool = (
        False  # Flag to track if we're waiting for user's decision
    )

    # New fields for template-based content generation
    destination_name: str = ""  # For destination templates
    event_name: str = ""  # For event templates
    price_text: str = ""  # For promotional templates
    template_id: str = ""  # Selected template ID
    template_type: str = ""  # Type of template (destination, events, etc.)
    template_data: Dict[str, Any] = None  # Data for template rendering
    validation_errors: List[str] = None  # Errors from template validation

    # Media asset fields for different template requirements
    event_image: str = ""  # For event templates (client upload)
    video_background: str = ""  # For video-based templates
    logo_url: str = ""  # Client's logo

    # Media selection and upload tracking
    media_source: MediaSourceType = "search"  # Default to search (vs upload)
    waiting_for_media_upload: bool = False  # Flag for tracking media upload
    is_video_content: bool = False  # Flag for tracking if we're working with video
    video_urls: List[str] = None  # URLs of video backgrounds
    selected_video: str = ""  # Selected video URL
    media_prompts: Dict[str, str] = None  # Custom prompts for media requests
    needs_destination_name: bool = False  # Flag for needing destination name
    needs_event_name: bool = False  # Flag for needing event name
    needs_price_text: bool = False  # Flag for needing price text
    needs_event_image: bool = False  # Flag for needing event image

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
        if self.template_data is None:
            self.template_data = {}
        if self.validation_errors is None:
            self.validation_errors = []
        if self.video_urls is None:
            self.video_urls = []
        if self.media_prompts is None:
            self.media_prompts = {}
