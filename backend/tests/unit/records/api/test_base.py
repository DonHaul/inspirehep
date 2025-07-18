#
# Copyright (C) 2019 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.
import mock
from helpers.providers.faker import faker
from inspirehep.records.api import (
    AuthorsRecord,
    ExperimentsRecord,
    InspireRecord,
    InstitutionsRecord,
    JobsRecord,
    JournalsRecord,
)
from inspirehep.records.api.conferences import ConferencesRecord
from inspirehep.records.api.data import DataRecord
from inspirehep.records.api.literature import LiteratureRecord
from inspirehep.records.api.seminars import SeminarsRecord


def test_strip_empty_values():
    empty_fields = {"empty_string": "", "empty_array": [], "empty_dict": {}}
    data = faker.record("lit")
    data.update(empty_fields)
    data_stripped = InspireRecord.strip_empty_values(data)

    assert "empty_string" not in data_stripped
    assert "empty_array" not in data_stripped
    assert "empty_dict" not in data_stripped


def test_get_subclasses_from_inspire_records():
    expected = {
        "lit": LiteratureRecord,
        "aut": AuthorsRecord,
        "job": JobsRecord,
        "jou": JournalsRecord,
        "exp": ExperimentsRecord,
        "con": ConferencesRecord,
        "dat": DataRecord,
        "ins": InstitutionsRecord,
        "sem": SeminarsRecord,
    }
    subclasses = InspireRecord.get_subclasses()

    assert subclasses == expected


def test_get_records_pid_from_field():
    data = {
        "references": [
            {
                "record": "http://labs.inspirehep.net/api/literature/98765",
                "reference": {
                    "misc": ["abcd", "defg"],
                    "label": "qwerty",
                    "record": {
                        "$ref": "http://labs.inspirehep.net/api/literature/339134"
                    },
                },
            }
        ],
        "publication_info": {"year": 1984},
        "some_stuff": {"other_stuff": "not_related"},
        "different_field": "http://labs.inspirehep.net/api/literature/329134",
        "other_record": {"$ref": ["http://labs.inspirehep.net/api/literature/319136"]},
    }

    path_1 = "references.reference.record"
    expected_1 = [("lit", "339134")]

    path_2 = "some_stuff"
    expected_2 = []

    path_3 = "other_record"
    expected_3 = [("lit", "319136")]

    assert InspireRecord._get_linked_pids_from_field(data, path_1) == expected_1
    assert InspireRecord._get_linked_pids_from_field(data, path_2) == expected_2
    assert InspireRecord._get_linked_pids_from_field(data, path_3) == expected_3


def test_get_subclasses():
    subclasses = InspireRecord.get_subclasses()
    expected_subclasses = {
        "lit": LiteratureRecord,
        "aut": AuthorsRecord,
        "job": JobsRecord,
        "jou": JournalsRecord,
        "exp": ExperimentsRecord,
        "con": ConferencesRecord,
        "dat": DataRecord,
        "ins": InstitutionsRecord,
        "sem": SeminarsRecord,
    }

    assert subclasses == expected_subclasses


@mock.patch("invenio_records.api.Record.get_record")
@mock.patch(
    "inspirehep.records.api.base.PidStoreBase.get_pid_type_from_schema",
    return_value="lit",
)
@mock.patch(
    "inspirehep.records.api.literature.LiteratureRecord.get_record",
    return_value=LiteratureRecord({}),
)
def test_finding_proper_class_in_get_record_lit(
    get_record_mock, get_pid_mock, invenio_record_mock
):
    created_record = InspireRecord.get_record("something")
    expected_record_type = LiteratureRecord

    assert isinstance(created_record, expected_record_type)


@mock.patch("invenio_records.api.Record.get_record")
@mock.patch(
    "inspirehep.records.api.base.PidStoreBase.get_pid_type_from_schema",
    return_value="aut",
)
@mock.patch(
    "inspirehep.records.api.authors.AuthorsRecord.get_record",
    return_value=AuthorsRecord(data={}),
)
def test_finding_proper_class_in_get_record_aut(
    get_record_mock, get_pid_mock, invenio_record_mock
):
    created_record = InspireRecord.get_record("something")
    expected_record_type = AuthorsRecord

    assert isinstance(created_record, expected_record_type)


@mock.patch("inspirehep.records.api.base.InspireRecord._get_records_ids_by_pids")
def test_get_records_ids_by_pids_function_is_properly_called_with_parameters(PI_mock):
    pids = [("lit", 1), ("lit", 2), ("lit", 3), ("lit", 4), ("lit", 5)]
    ids_generator = InspireRecord.get_records_ids_by_pids(pids, 3)
    # Calling generator to process all elements so mocked function
    # _get_records_ids_by_pids will be called with parameters
    [t for t in ids_generator]
    expected_call_list = [
        mock.call([("lit", 1), ("lit", 2), ("lit", 3)]),
        mock.call([("lit", 4), ("lit", 5)]),
    ]

    assert PI_mock.call_count == 2
    assert PI_mock.call_args_list == expected_call_list
