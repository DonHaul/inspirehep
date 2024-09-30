from django.db import models

from backoffice.workflows.workflow_types import WorkflowType

author_workflow_types = [
    WorkflowType.AUTHOR_CREATE,
    WorkflowType.AUTHOR_UPDATE,
]


class AuthorResolutionDags(models.TextChoices):
    accept = "accept", "author_create_approved_dag"
    reject = "reject", "author_create_rejected_dag"
    accept_curate = "accept_curate", "author_create_approved_dag"


class AuthorCreateDags(models.TextChoices):
    initialize = "author_create_initialization_dag", "initialize"
    approve = "author_create_approved_dag", "approve"
    reject = "author_create_rejected_dag", "reject"


class AuthorUpdateDags(models.TextChoices):
    initialize = "author_update_dag", "initialize"
