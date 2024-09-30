from django.db import models

from backoffice.authors.constants import (
    AuthorCreateDags,
    AuthorResolutionDags,
    AuthorUpdateDags,
)
from backoffice.workflows.workflow_types import WorkflowType

# tickets
TICKET_TYPES = (
    ("author_create_curation", "Author create curation"),
    ("author_create_user", "Author create user"),
    ("author_update_curation", "Author update curation"),
)
DEFAULT_TICKET_TYPE = "author_create_curation"

# workflows


class StatusChoices(models.TextChoices):
    RUNNING = "running", "Running"
    APPROVAL = "approval", "Waiting for approva"
    COMPLETED = "completed", "Completed"
    ERROR = "error", "Error"


DEFAULT_STATUS_CHOICE = StatusChoices.RUNNING


DEFAULT_WORKFLOW_TYPE = WorkflowType.HEP_CREATE


DECISION_CHOICES = AuthorResolutionDags.choices

WORKFLOW_DAGS = {
    WorkflowType.HEP_CREATE: "",
    WorkflowType.HEP_UPDATE: "",
    WorkflowType.AUTHOR_CREATE: AuthorCreateDags,
    WorkflowType.AUTHOR_UPDATE: AuthorUpdateDags,
}
