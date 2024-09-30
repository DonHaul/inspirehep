from os import environ

from django_elasticsearch_dsl_drf.serializers import DocumentSerializer
from rest_framework import serializers

from backoffice.workflows.constants import DECISION_CHOICES
from backoffice.workflows.documents import WorkflowDocument
from backoffice.workflows.models import Decision, Workflow, WorkflowTicket


class WorkflowTicketSerializer(serializers.ModelSerializer):
    ticket_url = serializers.SerializerMethodField()
    workflow = serializers.PrimaryKeyRelatedField(queryset=Workflow.objects.all())

    class Meta:
        model = WorkflowTicket
        fields = "__all__"

    def get_ticket_url(self, obj):
        return (
            f"{environ.get('SERVICENOW_URL')}"
            f"/nav_to.do?uri=/u_request_fulfillment.do?sys_id={obj.ticket_id}"
        )


class DecisionSerializer(serializers.ModelSerializer):
    workflow = serializers.PrimaryKeyRelatedField(queryset=Workflow.objects.all())

    class Meta:
        model = Decision
        fields = "__all__"


class WorkflowSerializer(serializers.ModelSerializer):
    tickets = WorkflowTicketSerializer(many=True, read_only=True)
    decisions = DecisionSerializer(many=True, read_only=True)

    class Meta:
        model = Workflow
        fields = "__all__"


class WorkflowDocumentSerializer(DocumentSerializer):
    class Meta:
        document = WorkflowDocument
        fields = "__all__"


class ResolutionSerializer(serializers.Serializer):
    value = serializers.ChoiceField(choices=DECISION_CHOICES)
    create_ticket = serializers.BooleanField(default=False)
