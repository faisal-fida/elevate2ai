# This file makes the workflow directory a Python package

"""
Workflow management for the WhatsApp conversation flow.

This package handles the state machine that manages user conversations,
processes user inputs, and coordinates the appropriate responses based on the conversation state.
"""

from app.services.workflow.manager import WorkflowManager

__all__ = ["WorkflowManager"]
