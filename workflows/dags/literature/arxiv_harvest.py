import datetime
import logging

from airflow.decorators import dag, task
from airflow.exceptions import AirflowException
from airflow.macros import ds_add
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.sdk import Param, Variable
from hooks.backoffice.workflow_management_hook import HEP, WorkflowManagementHook
from include.utils.alerts import FailedDagNotifier
from include.utils.arxiv import build_records, fetch_records, load_records
from include.utils.s3 import read_object, write_object

logger = logging.getLogger(__name__)


@dag(
    start_date=datetime.datetime(2024, 11, 28),
    schedule="0 2 * * *",
    catchup=False,
    tags=["literature", "arxiv", "harvest"],
    params={
        "metadata_prefix": Param(type=["null", "string"], default="arXiv"),
        "from": Param(type=["null", "string"], default=None),
        "until": Param(type=["null", "string"], default=None),
        "sets": Param(
            type="array",
            default=[
                "cs",
                "econ",
                "eess",
                "math",
                "physics",
                "physics:astro-ph",
                "physics:cond-mat",
                "physics:gr-qc",
                "physics:hep-ex",
                "physics:hep-lat",
                "physics:hep-ph",
                "physics:hep-th",
                "physics:math-ph",
                "physics:nlin",
                "physics:nucl-ex",
                "physics:nucl-th",
                "physics:physics",
                "physics:quant-ph",
                "q-bio",
                "q-fin",
                "stat",
            ],
        ),
    },
    on_failure_callback=FailedDagNotifier(),
)
def arxiv_harvest_dag():
    """Defines the DAG for the arXiv harvest workflow.

    Tasks:
    1. fetch_records: fetches records from arXiv using OAI-PMH protocol for each set.
    2. build_records: converts the raw XML records into json using the ArxivParser.
    3. load_record: pushes records to the backoffice
    4. check_failures: checks and reports any failed records
    """

    @task
    def get_sets(**context):
        """Collects the ids of the records that have been updated in the last two days.

        Returns: list of sets
        """
        return context["params"]["sets"]

    @task
    def process_records(set, **context):
        """Process the record by downloading the versions,
        building the record and loading it to inspirehep.
         Args: set (str): The arXiv set to fetch records from.
        """

        workflow_management_hook = WorkflowManagementHook(HEP)

        s3_hook = S3Hook(aws_conn_id="s3_conn")
        bucket_name = Variable.get("s3_bucket_name")

        from_date = context["params"]["from"] or ds_add(context["ds"], -1)
        until_date = context["params"]["until"]

        xml_records = fetch_records(
            connection_id="arxiv_oaipmh_connection",
            metadata_prefix=context["params"]["metadata_prefix"],
            from_date=from_date,
            until_date=until_date,
            set=set,
        )

        parsed_records, failed_build_records = build_records(
            xml_records, context["run_id"]
        )

        failed_load_records = load_records(parsed_records, workflow_management_hook)

        return write_object(
            s3_hook,
            {
                "failed_build_records": failed_build_records,
                "failed_load_records": failed_load_records,
            },
            bucket_name,
        )

    @task
    def check_failures(failed_record_keys):
        """Check if there are any failed records and raise an exception if there are.

        Args: failed_records (list): The list of failed records.
        Raises: AirflowException: If there are any failed records.
        """

        s3_hook = S3Hook(aws_conn_id="s3_conn")
        bucket_name = Variable.get("s3_bucket_name")

        def gather_failed_records(record_keys):
            failed_records = []
            for record_key in record_keys:
                record_data = read_object(s3_hook, bucket_name, record_key)
                failed_records.extend(record_data.get("failed_build_records", []))
                failed_records.extend(record_data.get("failed_load_records", []))
            return failed_records

        failed_records = gather_failed_records(failed_record_keys)

        if len(failed_records) > 0:
            raise AirflowException(f"The following records failed: {failed_records}")

        logger.info("No failed records")

    sets = get_sets()
    failed_load_record_keys = process_records.expand(set=sets)
    check_failures(failed_load_record_keys)


arxiv_harvest_dag()
