import datetime
import logging
import random

from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.providers.postgres.hooks.postgres import PostgresHook
from hooks.backoffice.workflow_management_hook import LITERATURE
from include.utils.alerts import dag_failure_callback

logger = logging.getLogger(__name__)


@dag(
    params={
        "workflow_id": Param(type="string", default="4"),
        "data": Param(type="object", default={}),
        "collection": Param(type="string", default=LITERATURE),
    },
    start_date=datetime.datetime(2024, 5, 5),
    schedule=None,
    catchup=False,
    on_failure_callback=dag_failure_callback,
    tags=[LITERATURE],
)
def hep_create_init():
    """
    Initialize a DAG for author create workflow.

    Tasks:
    1. create_ticket_on_author_create: Creates a ticket using the InspireHttpHook
        to call the API endpoint.
    2. set_author_create_workflow_status_to_approval: Sets the workflow status
        to "approval" using the WorkflowManagementHook.

    """

    @task.short_circuit(ignore_downstream_trigger_rules=False)
    def check_for_blocking_workflows(**context):
        hook = PostgresHook(postgres_conn_id="backoffice_db_connection")
        result = hook.get_first(
            "SELECT id FROM public.hep_hepworkflow WHERE data @> '{\"arxiv\": 1}';"
        )

        return not result

    @task.branch
    def check_matches(**context):
        is_exact_match = random.choice([True, False])
        is_fuzzy_match = random.choice([True, False])

        context["ti"].xcom_push(key="is_update", value=is_exact_match or is_fuzzy_match)

        if is_exact_match:
            return "waiting_for_exact_approval"

        if is_fuzzy_match:
            return "waiting_for_fuzzy_approval"

        return "auto_reject"

    @task
    def waiting_for_exact_approval(**context):
        print("waiting_for_exact_approval")

    @task
    def waiting_for_fuzzy_approval(**context):
        print("waiting_for_fuzzy_approval")

    @task
    def auto_reject(**context):
        print("Auto Reject")

    @task
    def enhance(**context):
        print("Enhance")

    @task
    def auto_approve(**context):
        print("auto_approve")

    auto_reject_task = auto_reject()

    (
        check_for_blocking_workflows()
        >> check_matches()
        >> [
            waiting_for_exact_approval(),
            waiting_for_fuzzy_approval(),
            auto_reject_task,
        ]
    )
    auto_reject_task >> enhance() >> auto_approve()


hep_create_init()
