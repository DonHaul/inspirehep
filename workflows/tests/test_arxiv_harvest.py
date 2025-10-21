from unittest.mock import patch

import pytest
from airflow.exceptions import AirflowException, AirflowSkipException
from airflow.models import DagBag
from airflow.models.variable import Variable
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from hooks.backoffice.workflow_management_hook import HEP, WorkflowManagementHook
from include.utils.arxiv import build_records, fetch_records, load_records
from include.utils.s3 import write_object
from sickle.oaiexceptions import NoRecordsMatch

from tests.test_utils import task_test

dagbag = DagBag()
s3_hook = S3Hook(aws_conn_id="s3_conn")
bucket_name = Variable.get("s3_bucket_name")


class TestArxivHarvest:
    dag = dagbag.get_dag("arxiv_harvest_dag")
    connection_id = "arxiv_oaipmh_connection"
    workflow_management_hook = WorkflowManagementHook(HEP)

    @pytest.mark.vcr
    def test_fetch_records_logical_date(self):
        xml_records = fetch_records(
            self.connection_id,
            "arXiv",
            from_date="2025-07-01",
            until_date="",
            set="physics:hep-th",
        )

        assert len(xml_records)
        assert "oai:arXiv.org:2101.11905" in xml_records[0]
        assert "oai:arXiv.org:2207.10712" in xml_records[1]

    @pytest.mark.vcr
    def test_fetch_records_with_from_until(self):
        xml_records = fetch_records(
            self.connection_id,
            "arXiv",
            from_date="2025-07-01",
            until_date="2025-07-01",
            set="physics:hep-th",
        )

        assert len(xml_records)
        assert "oai:arXiv.org:2101.11905" in xml_records[0]
        assert "oai:arXiv.org:2207.10712" in xml_records[1]

    @patch("sickle.Sickle.ListRecords", side_effect=NoRecordsMatch)
    def test_fetch_no_records(self, mock_list_records):
        with pytest.raises(AirflowSkipException):
            fetch_records(
                self.connection_id,
                "arXiv",
                from_date="2025-07-01",
                until_date="",
                set="physics:hep-th",
            )

    def test_build_records(self, datadir):
        xml_files = ["arxiv1608.06937.xml", "arxiv2007.03037.xml"]

        xml_records = []
        for xml_file in xml_files:
            xml_string = (datadir / xml_file).read_text(encoding="utf-8")
            xml_records.append(xml_string)

        parsed_records, failed_build_records = build_records(xml_records, "12345")

        assert len(parsed_records) == 2
        assert "acquisition_source" in parsed_records[0]
        for parsed_record in parsed_records:
            assert parsed_record["acquisition_source"]["source"] == "arXiv"
            assert parsed_record["acquisition_source"]["method"] == "hepcrawl"
            assert {"datetime", "submission_number"}.issubset(
                parsed_record["acquisition_source"]
            )
        assert len(failed_build_records) == 0

    def test_build_records_bad(self, datadir):
        xml_files = ["arxiv1608.06937.xml", "arxiv2007.03037-bad.xml"]

        xml_records = []
        for xml_file in xml_files:
            xml_string = (datadir / xml_file).read_text(encoding="utf-8")
            xml_records.append(xml_string)

        parsed_records, failed_build_records = build_records(xml_records, "12345")
        assert len(parsed_records) == 1
        assert len(failed_build_records) == 1

    @pytest.mark.vcr
    def test_load_records_failed(self):
        parsed_records = [
            {
                "document_type": ["article"],
                "_collections": ["Literature"],
                "titles": [{"title": "Test Workflow Management Hook"}],
            },
            {
                "document_type": ["article"],
                "_collections": ["Literature"],
            },
        ]

        failed_load_records = load_records(
            parsed_records, self.workflow_management_hook
        )
        assert len(failed_load_records) == 1

    @pytest.mark.vcr
    @patch(
        "hooks.backoffice.workflow_management_hook.WorkflowManagementHook.post_workflow"
    )
    def test_load_records_multiple(self, mock_post_workflow):
        parsed_records = [
            {
                "workflow_type": "HEP_CREATE",
                "data": {
                    "document_type": ["article"],
                    "_collections": ["Literature"],
                    "titles": [{"title": "Test Workflow Management Hook"}],
                },
            },
            {
                "workflow_type": "HEP_CREATE",
                "data": {
                    "document_type": ["article"],
                    "_collections": ["Literature"],
                    "titles": [{"title": "Test Workflow Management Hook"}],
                },
            },
        ]

        failed_load_records = load_records(
            parsed_records, self.workflow_management_hook
        )
        assert mock_post_workflow.call_count == 2
        assert len(failed_load_records) == 0

    def test_check_failures_success(self):
        s3_keys = [
            write_object(
                s3_hook,
                {"failed_build_records": [], "failed_load_records": []},
                bucket_name,
            )
            for _ in range(2)
        ]

        task_test(
            dag_id="arxiv_harvest_dag",
            task_id="check_failures",
            params={"failed_record_keys": s3_keys},
        )

    def test_check_failures_fail(self):
        s3_keys = [
            write_object(s3_hook, {"failed_build_records": []}, bucket_name)
            for _ in range(2)
        ]
        s3_keys.append(
            write_object(s3_hook, {"failed_build_records": ["record"]}, bucket_name)
        )

        with pytest.raises(AirflowException) as exc_info:
            task_test(
                dag_id="arxiv_harvest_dag",
                task_id="check_failures",
                params={"failed_record_keys": s3_keys},
            )
        assert "The following records failed: ['record']" in str(exc_info.value)
