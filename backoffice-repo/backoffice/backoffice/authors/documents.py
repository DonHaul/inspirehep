from django.conf import settings
from django_opensearch_dsl.registries import registry

from backoffice.workflows.documents import WorkflowDocument


@registry.register_document
class AuthorWorkflowDocument(WorkflowDocument):
    class Index(WorkflowDocument.Index):
        name = settings.OPENSEARCH_INDEX_NAMES["authors"]
