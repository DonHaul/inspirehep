from django.db import models


class WorkflowType(models.TextChoices):
    HEP_CREATE = "HEP_CREATE", "HEP create"
    HEP_UPDATE = "HEP_UPDATE", "HEP update"
    AUTHOR_CREATE = "AUTHOR_CREATE", "Author create"
    AUTHOR_UPDATE = "AUTHOR_UPDATE", "Author update"
