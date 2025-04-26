from __future__ import annotations
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class BaseWorkflowContext:
    """Base class for all workflow contexts."""
    pass


@dataclass
class PromoWorkflowContext(BaseWorkflowContext):
    """Context for the promotional content workflow."""
    caption: str = ""
    image_urls: List[str] = None
    original_text: str = ""

    def __post_init__(self):
        if self.image_urls is None:
            self.image_urls = []


@dataclass
class SocialMediaWorkflowContext(BaseWorkflowContext):
    """Context for the social media posting workflow."""
    # Content fields
    caption: str = ""
    selected_platforms: List[str] = None
    content_types: Dict[str, str] = None
    same_content_across_platforms: bool = False
    schedule_time: str = ""
    platform_specific_captions: Dict[str, str] = None
    
    # State tracking fields
    current_platform_index: int = 0
    post_status: Dict[str, bool] = None
    common_content_types: List[str] = None

    def __post_init__(self):
        if self.selected_platforms is None:
            self.selected_platforms = []
        if self.content_types is None:
            self.content_types = {}
        if self.platform_specific_captions is None:
            self.platform_specific_captions = {}
        if self.post_status is None:
            self.post_status = {}
