import logging

from backoffice.authors.api.serializers import (
    AuthorResolutionSerializer,
    AuthorWorkflowDocumentSerializer,
    AuthorWorkflowSerializer,
)
from backoffice.authors.constants import AuthorResolutionDags
from backoffice.authors.documents import AuthorWorkflowDocument
from backoffice.workflows.api.views import WorkflowDocumentView, WorkflowViewSet

logger = logging.getLogger(__name__)


class AuthorWorkflowViewSet(WorkflowViewSet):
    serializer_class = AuthorWorkflowSerializer
    resolution_serializer = AuthorResolutionSerializer
    resolution_dags = AuthorResolutionDags


class AuthorWorkflowDocumentView(WorkflowDocumentView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search = self.search.extra(track_total_hits=True)

    document = AuthorWorkflowDocument
    serializer_class = AuthorWorkflowDocumentSerializer
    search_fields = {
        "data.ids.value",
        "data.ids.schema",
        "data.name.value",
        "data.name.preferred_name",
        "data.email_addresses.value",
    }
