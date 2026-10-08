"""Local workflow domain; all remote effects are board outbox intents.

The caller owns Git integration, execution permissions and actual verification.
An approval's source describes provenance; it never grants host capabilities.
"""

from .service import WorkflowService

__all__ = ["WorkflowService"]
