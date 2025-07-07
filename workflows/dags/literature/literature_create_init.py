import asyncio
import datetime
import logging

from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.models.param import Param
from airflow.sensors.base import BaseSensorOperator
from airflow.triggers.base import BaseTrigger, TriggerEvent
from airflow.utils.context import Context
from hooks.backoffice.workflow_management_hook import (
    AUTHORS,
    LITERATURE,
    WorkflowManagementHook,
)
from include.utils.alerts import dag_failure_callback

logger = logging.getLogger(__name__)

workflow_management_hook = WorkflowManagementHook(AUTHORS)


class DBFlagTrigger(BaseTrigger):
    def __init__(self, poll_interval: int = 10):
        print("Initializing DBFlagTrigger...")
        super().__init__()
        self.poll_interval = poll_interval
        self.workflow_management_hook = WorkflowManagementHook(AUTHORS)
        print(f"DBFlagTrigger initialized with poll_interval: {self.poll_interval}")

    def serialize(self):
        print("Serializing DBFlagTrigger...")
        return (
            "literature.literature_create_init.DBFlagTrigger",
            {
                "poll_interval": self.poll_interval,
            },
        )

    async def run(self):
        print("Running DBFlagTrigger...")
        while True:
            print("Checking DB flag...")
            await asyncio.sleep(self.poll_interval)
            try:
                workflow_data = self.workflow_management_hook.get_workflow(
                    workflow_id="00000000-0000-0000-0000-000000001521"
                )

                if workflow_data["status"] == "completed":
                    yield TriggerEvent({"status": "success"})
                    return
            except Exception as e:
                print(f"Error checking DB flag: {e}")
                yield TriggerEvent({"status": "error", "message": str(e)})
                return


class DBFlagSensor(BaseSensorOperator):
    def __init__(self, poll_interval: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.poll_interval = poll_interval

    def execute(self, context: Context):
        print("Starting DBFlagSensor execution...")
        self.defer(
            trigger=DBFlagTrigger(poll_interval=self.poll_interval),
            method_name="execute_complete",
        )

    def execute_complete(self, context: Context, event: TriggerEvent):
        if not event or event["status"] != "success":
            raise AirflowException(f"DBFlagSensor failed: {event}")
        self.log.info("DB flag is set. Continuing DAG execution.")
        return


@dag(
    params={
        "workflow_id": Param(type="string", default=""),
        "data": Param(type="object", default={}),
        "collection": Param(type="string", default=LITERATURE),
    },
    start_date=datetime.datetime(2024, 5, 5),
    schedule=None,
    catchup=False,
    on_failure_callback=dag_failure_callback,
    tags=[LITERATURE],
)
def literature_create_initialization_dag():
    """
    Initialize a DAG for author create workflow.

    Tasks:
    1. create_ticket_on_author_create: Creates a ticket using the InspireHttpHook
        to call the API endpoint.
    2. set_author_create_workflow_status_to_approval: Sets the workflow status
        to "approval" using the WorkflowManagementHook.

    """
    workflow_management_hook = WorkflowManagementHook(AUTHORS)

    @task
    def set_workflow_status_to_running(**context):
        print("Setting workflow status to running")

    wow = DBFlagSensor(task_id="wow")

    @task
    def undeferred(**context):
        return workflow_management_hook.get_workflow(
            workflow_id="00000000-0000-0000-0000-000000001521"
        )

    @task
    def check_is_running(**context):
        print("Deferring")

    @task
    def run(**context):
        print("Running task with context:", context)

    (
        set_workflow_status_to_running()
        >> undeferred()
        >> wow
        >> check_is_running()
        >> run()
    )


literature_create_initialization_dag()
