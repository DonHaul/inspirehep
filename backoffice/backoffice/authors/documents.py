from django.conf import settings
from django_opensearch_dsl.registries import registry

from backoffice.authors.models import AuthorWorkflow
from backoffice.common.documents import BaseWorkflowDocument


@registry.register_document
class AuthorWorkflowDocument(BaseWorkflowDocument):
    class Index(BaseWorkflowDocument.Index):
        name = settings.OPENSEARCH_INDEX_NAMES.get(settings.AUTHORS_DOCUMENTS)

    class Django(BaseWorkflowDocument.Django):
        model = AuthorWorkflow
