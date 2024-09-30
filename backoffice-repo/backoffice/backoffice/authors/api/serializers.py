from backoffice.authors.constants import (
    AuthorResolutionDags,
    WorkflowType,
    author_workflow_types,
)
from backoffice.authors.models import AuthorWorkflow
from backoffice.workflows.api.serializers import (
    ResolutionSerializer,
    WorkflowDocumentSerializer,
    WorkflowSerializer,
)
from backoffice.workflows.constants import StatusChoices
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer
from rest_framework import serializers


@extend_schema_serializer(
    exclude_fields=[
        "_created_at",
        "_updated_at",
    ],  # Exclude internal fields from schema
    examples=[
        OpenApiExample(
            "Author Workflow Serializer",
            summary="Author Workflow Serializer no data",
            description="Author Workflow Serializer",
            value={
                "workflow_type": WorkflowType.AUTHOR_CREATE,
                "status": StatusChoices.RUNNING,
                "data": {},
            },
        ),
    ],
)
class AuthorWorkflowSerializer(WorkflowSerializer):
    def validate_workflow_type(self, value):
        if value not in author_workflow_types:
            raise serializers.ValidationError(
                f"The field `workflow_type` should be on of {author_workflow_types}"
            )
        return value

    class Meta(WorkflowSerializer.Meta):
        model = AuthorWorkflow


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            "Accept",
            description="Author Workflow Serializer",
            value={"value": "accept", "create_ticket": False},
        ),
        OpenApiExample(
            "Reject",
            description="Author Workflow Serializer",
            value={"value": "reject", "create_ticket": False},
        ),
    ],
)
class AuthorResolutionSerializer(ResolutionSerializer):
    value = serializers.ChoiceField(choices=AuthorResolutionDags)


class AuthorWorkflowDocumentSerializer(WorkflowDocumentSerializer):
    pass
