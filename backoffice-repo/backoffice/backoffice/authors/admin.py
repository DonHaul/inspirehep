# Register your models here.
from django.contrib import admin

from backoffice.authors.models import AuthorWorkflow
from backoffice.workflows.admin import WorkflowAdmin, WorkflowsAdminSite


class AuthorWorkflowsAdminSite(WorkflowsAdminSite):
    """
    Custom admin site for managing author workflows.

    This admin site extends the default Django admin site to include additional
    functionality for managing author workflows. It checks whether the user has the
    necessary permissions to access the admin site by verifying that they are
    an active user and either a superuser or a member of the 'curator' group.
    """


@admin.register(AuthorWorkflow)
class AuthorWorkflowAdmin(WorkflowAdmin):
    """
    Admin class for Author Workflow model. Define get, update and delete permissions.
    """
