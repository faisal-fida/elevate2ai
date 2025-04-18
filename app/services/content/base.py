from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

class ContentProvider(ABC):
    """Base interface for content generation providers"""
    
    @abstractmethod
    async def generate_caption(self, text: str) -> str:
        """Generate a caption for the given text"""
        pass

    @abstractmethod
    async def get_image(self, query: str) -> Optional[str]:
        """Get an image URL for the given query"""
        pass

class ImageProvider(ABC):
    """Base interface for image providers"""
    
    @abstractmethod
    async def search_images(self, query: str, limit: int = 1) -> List[str]:
        """Search for images matching the query"""
        pass

class ContentResult:
    """Value object for content generation results"""
    
    def __init__(self, caption: str, image_url: Optional[str] = None):
        self.caption = caption
        self.image_url = image_url

    def to_dict(self) -> Dict[str, Any]:
        return {
            "caption": self.caption,
            "image_url": self.image_url
        }