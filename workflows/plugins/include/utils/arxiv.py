import datetime
import logging

from airflow.exceptions import AirflowSkipException
from airflow.hooks.base import BaseHook
from inspire_schemas.parsers.arxiv import ArxivParser
from sickle import Sickle, oaiexceptions

logger = logging.getLogger(__name__)


def fetch_records(connection_id, metadata_prefix, from_date, until_date=None, set=set):
    """Fetch the xml records for a given set.
    Args:
        connection_id (str): The connection id for the OAI-PMH server.
        metadata_prefix (str): The metadata prefix to use.
        from_date (str): The date from which to fetch records (YYYY-MM-DD).
        until_date (str, optional): The date until which to fetch records (YYYY-MM-DD).
        set (str): The set to fetch records from. Defaults to 'arXiv'.
    Returns:
        list: A list of xml records.
    """

    conn = BaseHook.get_connection(connection_id)
    sickle = Sickle(conn.host)

    oaiargs = {
        "from": from_date,
        "metadataPrefix": metadata_prefix,
    }

    if until_date:
        oaiargs["until"] = until_date

    logger.info(
        f"Collecting records from arXiv from {from_date} "
        f"to {until_date} for set '{set}'"
    )
    try:
        records = list(sickle.ListRecords(set=set, **oaiargs))
    except oaiexceptions.NoRecordsMatch:
        raise AirflowSkipException(f"No records for '{set}'") from None

    return [record.raw for record in records]


def build_records(xml_records, submission_number):
    """Build the records from the arXiv xml response.
    Args:
        xml_records (list): The list of xml records.
        submission_number (str): The submission number for the acquisition source.
    Returns:
        tuple: A tuple containing the list of parsed records and failed records.
    """
    parsed_records = []
    failed_build_records = []
    for record in xml_records:
        try:
            parsed_object = ArxivParser(record)
            parsed_object.parse()
            parsed_object.builder.add_acquisition_source(
                source="arXiv",
                method="hepcrawl",
                date=datetime.datetime.now().isoformat(),
                submission_number=submission_number,
            )
            parsed_records.append(parsed_object.builder.record)
        except Exception:
            failed_build_records.append(record)

    return parsed_records, failed_build_records


def load_records(parsed_records, workflow_management_hook):
    """Load the built records to the backoffice.
    Args:
        parsed_records (list): The list of built records.
        workflow_management_hook: The workflow management hook to use.
    Returns:
        list: The list of failed to load records.
    """
    failed_load_records = []
    for record in parsed_records:
        logger.info(
            f"Loading record: " f"{record.get('arxiv_eprints',[{}])[0].get('value')}"
        )

        workflow_data = {
            "data": record,
            "workflow_type": "HEP_CREATE",
        }
        try:
            logger.info(f"Loading record: {record.get('control_number')}")
            workflow_management_hook.post_workflow(
                workflow_data=workflow_data,
            )
        except Exception:
            logger.error(f"Failed to load record: {record.get('control_number')}")
            failed_load_records.append(record)

    return failed_load_records
