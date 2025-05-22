from enum import Enum


class FieldSource(Enum):
    """Source types for template fields"""

    USER_INPUT = "user_input"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"
