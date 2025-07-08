import asyncio
import datetime
import logging

import asyncpg  # efficient async Postgres driver
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


class PostgresNotifyTrigger(BaseTrigger):
    def __init__(self, dsn: str, channel: str):
        super().__init__()
        self.dsn = dsn
        self.channel = channel

    def serialize(self):
        return (
            "literature.literature_create_init.PostgresNotifyTrigger",
            {
                "dsn": self.dsn,
                "channel": self.channel,
            },
        )

    async def run2(self):
        print("Starting Postgres Notify Listener...")

        # Connect to the PostgreSQL database
        conn = await asyncpg.connect(
            user="postgres",
            password="postgres",
            database="backoffice",
            host="host.docker.internal",  # Use 'db' if running in Docker
        )
        # yield TriggerEvent({"status": "success", "payload": "no"})

        async def handle_notify(connection, pid, channel, payload):
            print(f"Got NOTIFY: channel={channel}, pid={pid}, payload={payload}")
            yield TriggerEvent({"status": "success", "payload": "maybe"})

        # yield TriggerEvent({"status": "success", "payload": "www"})

        # Add listener to a channel
        await conn.add_listener("my_channel", handle_notify)
        print("Listening on 'my_channel'...")

        try:
            while True:
                await asyncio.sleep(1)  # Keep the loop alive
        finally:
            await conn.close()
            yield TriggerEvent({"status": "success", "payload": "finito"})

    async def run(self):
        try:
            conn = await asyncpg.connect(self.dsn)
            await conn.add_listener(self.channel, self._notify_handler)

            # Use an event to wait for the signal
            self._event = asyncio.Event()
            self._message = None

            await self._event.wait()
            await conn.remove_listener(self.channel, self._notify_handler)
            await conn.close()

            yield TriggerEvent({"status": "success", "payload": self._message})

        except Exception as e:
            yield TriggerEvent({"status": "error", "message": str(e)})

    def _notify_handler(self, connection, pid, channel, payload):
        self._message = payload
        self._event.set()


class PostgresNotifySensor(BaseSensorOperator):
    def __init__(self, dsn: str, channel: str, **kwargs):
        super().__init__(**kwargs)
        self.dsn = dsn
        self.channel = channel

    def execute(self, context: Context):
        print("Starting PostgresNotifySensor execution...")
        self.defer(
            trigger=PostgresNotifyTrigger(dsn=self.dsn, channel=self.channel),
            method_name="execute_complete",
        )

    def execute_complete(self, context: Context, event):
        if not event or event.get("status") != "success":
            raise AirflowException(f"PostgresNotifySensor failed: {event}")
        self.log.info(f"Received Postgres notification: {event['payload']}")


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

    wow2 = PostgresNotifySensor(
        task_id="wow2",
        dsn="postgresql://postgres:postgres@db:5432/backoffice",
        channel="task_completed",
    )
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
        >> wow2
        >> wow
        >> check_is_running()
        >> run()
    )


literature_create_initialization_dag()
