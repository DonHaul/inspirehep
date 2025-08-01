#
# Copyright (C) 2019 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.
from copy import deepcopy
from uuid import UUID, uuid4

import mock
import orjson
import pytest
import requests_mock
from freezegun import freeze_time
from helpers.providers.faker import faker
from helpers.utils import (
    create_pidstore,
    create_record,
    create_s3_bucket,
    create_s3_file,
)
from inspirehep.files.api import current_s3_instance
from inspirehep.records.api import InspireRecord
from inspirehep.records.api.literature import LiteratureRecord, import_article
from inspirehep.records.errors import (
    ExistingArticleError,
    FileSizeExceededError,
    UnknownImportIdentifierError,
    UnsupportedFileError,
)
from inspirehep.records.models import RecordCitations, RecordsAuthors
from invenio_db import db
from invenio_pidstore.errors import PIDAlreadyExists
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_records.models import RecordMetadata
from jsonschema import ValidationError

KEY = "b50c2ea2d26571e0c5a3411e320586289fd715c2"


def test_literature_create(inspire_app):
    data = faker.record("lit")
    record = LiteratureRecord.create(data)

    control_number = str(record["control_number"])
    record_db = RecordMetadata.query.filter_by(id=record.id).one()

    assert record == record_db.json

    record_pid = PersistentIdentifier.query.filter_by(
        pid_type="lit", pid_value=str(control_number)
    ).one()

    assert record.model.id == record_pid.object_uuid
    assert control_number == record_pid.pid_value


def test_literature_create_with_mutliple_pids(inspire_app):
    doi_value = faker.doi()
    arxiv_value = faker.arxiv()
    data = {"arxiv_eprints": [{"value": arxiv_value}], "dois": [{"value": doi_value}]}
    data = faker.record("lit", with_control_number=True, data=data)

    expected_pids_len = 3
    expected_pid_lit_value = str(data["control_number"])
    expected_pid_arxiv_value = arxiv_value
    expected_pid_doi_value = doi_value

    record = LiteratureRecord.create(data)

    record_lit_pid = PersistentIdentifier.query.filter_by(pid_type="lit").one()
    record_arxiv_pid = PersistentIdentifier.query.filter_by(pid_type="arxiv").one()
    record_doi_pid = PersistentIdentifier.query.filter_by(pid_type="doi").one()

    record_total_pids = PersistentIdentifier.query.filter_by(
        object_uuid=record.id
    ).count()

    assert expected_pids_len == record_total_pids
    assert expected_pid_lit_value == record_lit_pid.pid_value
    assert expected_pid_arxiv_value == record_arxiv_pid.pid_value
    assert expected_pid_doi_value == record_doi_pid.pid_value


def test_literature_create_with_mutliple_updated_pids(inspire_app):
    doi_value = faker.doi()
    arxiv_value = faker.arxiv()
    data = {"arxiv_eprints": [{"value": arxiv_value}], "dois": [{"value": doi_value}]}
    data = faker.record("lit", with_control_number=True, data=data)

    expected_pid_lit_value = str(data["control_number"])
    expected_pid_arxiv_value = arxiv_value
    expected_pid_doi_value = doi_value

    record = LiteratureRecord.create(data)

    record_lit_pid = PersistentIdentifier.query.filter_by(pid_type="lit").one()
    record_arxiv_pid = PersistentIdentifier.query.filter_by(pid_type="arxiv").one()
    record_doi_pid = PersistentIdentifier.query.filter_by(pid_type="doi").one()

    assert expected_pid_lit_value == record_lit_pid.pid_value
    assert expected_pid_arxiv_value == record_arxiv_pid.pid_value
    assert expected_pid_doi_value == record_doi_pid.pid_value

    doi_value_new = faker.doi()
    arxiv_value_new = faker.arxiv()
    data.update(
        {
            "control_number": record["control_number"],
            "arxiv_eprints": [{"value": arxiv_value_new}],
            "dois": [{"value": doi_value_new}],
        }
    )

    record.update(data)

    expected_pid_lit_value = str(data["control_number"])
    expected_pid_arxiv_value = arxiv_value_new
    expected_pid_doi_value = doi_value_new

    record_lit_pid = PersistentIdentifier.query.filter_by(pid_type="lit").one()
    record_arxiv_pid = PersistentIdentifier.query.filter_by(pid_type="arxiv").one()
    record_doi_pid = PersistentIdentifier.query.filter_by(pid_type="doi").one()

    assert expected_pid_lit_value == record_lit_pid.pid_value
    assert expected_pid_arxiv_value == record_arxiv_pid.pid_value
    assert expected_pid_doi_value == record_doi_pid.pid_value


def test_literature_on_delete(inspire_app):
    doi_value = faker.doi()
    arxiv_value = faker.arxiv()
    data = {"arxiv_eprints": [{"value": arxiv_value}], "dois": [{"value": doi_value}]}
    data = faker.record("lit", data=data, with_control_number=True)

    record = LiteratureRecord.create(data)

    expected_pid_lit_value = str(data["control_number"])
    expected_pid_arxiv_value = arxiv_value
    expected_pid_doi_value = doi_value

    record_lit_pid = PersistentIdentifier.query.filter_by(pid_type="lit").one()
    record_arxiv_pid = PersistentIdentifier.query.filter_by(pid_type="arxiv").one()
    record_doi_pid = PersistentIdentifier.query.filter_by(pid_type="doi").one()

    assert expected_pid_lit_value == record_lit_pid.pid_value
    assert expected_pid_arxiv_value == record_arxiv_pid.pid_value
    assert expected_pid_doi_value == record_doi_pid.pid_value

    record.delete()
    record_lit_pid = PersistentIdentifier.query.filter_by(pid_type="lit").one()
    record_arxiv_pid = PersistentIdentifier.query.filter_by(
        pid_type="arxiv"
    ).one_or_none()
    record_doi_pid = PersistentIdentifier.query.filter_by(pid_type="doi").one_or_none()

    assert None is record_arxiv_pid
    assert None is record_doi_pid
    assert record_lit_pid.status == PIDStatus.DELETED


def test_literature_on_delete_through_metadata_update(inspire_app):
    doi_value = faker.doi()
    arxiv_value = faker.arxiv()
    data = {"arxiv_eprints": [{"value": arxiv_value}], "dois": [{"value": doi_value}]}
    data = faker.record("lit", data=data, with_control_number=True)

    record = LiteratureRecord.create(data)

    expected_pid_lit_value = str(data["control_number"])
    expected_pid_arxiv_value = arxiv_value
    expected_pid_doi_value = doi_value

    record_lit_pid = PersistentIdentifier.query.filter_by(pid_type="lit").one()
    record_arxiv_pid = PersistentIdentifier.query.filter_by(pid_type="arxiv").one()
    record_doi_pid = PersistentIdentifier.query.filter_by(pid_type="doi").one()

    assert expected_pid_lit_value == record_lit_pid.pid_value
    assert expected_pid_arxiv_value == record_arxiv_pid.pid_value
    assert expected_pid_doi_value == record_doi_pid.pid_value

    record["deleted"] = True
    record.update(dict(record))
    record_lit_pid = PersistentIdentifier.query.filter_by(pid_type="lit").one()
    record_arxiv_pid = PersistentIdentifier.query.filter_by(
        pid_type="arxiv"
    ).one_or_none()
    record_doi_pid = PersistentIdentifier.query.filter_by(pid_type="doi").one_or_none()

    assert None is record_arxiv_pid
    assert None is record_doi_pid
    assert record_lit_pid.status == PIDStatus.DELETED


def test_literature_create_with_existing_control_number(inspire_app):
    data = faker.record("lit", with_control_number=True)
    existing_object_uuid = uuid4()

    create_pidstore(
        object_uuid=existing_object_uuid,
        pid_type="lit",
        pid_value=data["control_number"],
    )

    with pytest.raises(PIDAlreadyExists):
        LiteratureRecord.create(data)


def test_literature_create_with_arxiv_eprints(inspire_app):
    arxiv_value = faker.arxiv()
    data = {"arxiv_eprints": [{"value": arxiv_value}]}
    data = faker.record("lit", data=data)

    record = LiteratureRecord.create(data)
    record_db = RecordMetadata.query.filter_by(id=record.id).one()

    assert record == record_db.json

    expected_arxiv_pid_value = arxiv_value
    expected_arxiv_pid_type = "arxiv"
    expected_arxiv_pid_provider = "external"

    record_pid_arxiv = PersistentIdentifier.query.filter_by(
        pid_type="arxiv", object_uuid=record.id
    ).one()

    assert record.model.id == record_pid_arxiv.object_uuid
    assert expected_arxiv_pid_value == record_pid_arxiv.pid_value
    assert expected_arxiv_pid_type == record_pid_arxiv.pid_type
    assert expected_arxiv_pid_provider == record_pid_arxiv.pid_provider


def test_literature_create_with_dois(inspire_app):
    doi_value = faker.doi()
    data = {"dois": [{"value": doi_value}]}
    data = faker.record("lit", data=data)

    record = LiteratureRecord.create(data)
    record_db = RecordMetadata.query.filter_by(id=record.id).one()

    assert record == record_db.json

    expected_doi_pid_value = doi_value
    expected_doi_pid_type = "doi"
    expected_doi_pid_provider = "external"
    record_pid_doi = PersistentIdentifier.query.filter_by(
        pid_type="doi", object_uuid=record.id
    ).one()

    assert record.model.id == record_pid_doi.object_uuid
    assert expected_doi_pid_value == record_pid_doi.pid_value
    assert expected_doi_pid_type == record_pid_doi.pid_type
    assert expected_doi_pid_provider == record_pid_doi.pid_provider


def test_literature_create_with_invalid_data(inspire_app):
    data = faker.record("lit", with_control_number=True)
    data["invalid_key"] = "should throw an error"
    record_control_number = str(data["control_number"])

    with pytest.raises(ValidationError):
        LiteratureRecord.create(data)

    record_pid = PersistentIdentifier.query.filter_by(
        pid_value=record_control_number
    ).one_or_none()
    assert record_pid is None


@mock.patch("inspirehep.records.api.literature.uuid.uuid4")
def test_update_authors_uuids_does_not_update_existing_uuids(mock_uuid4, inspire_app):
    mock_uuid4.return_value = UUID("727238f3-8ed6-40b6-97d2-dc3cd1429131")
    author_data = {
        "authors": [
            {
                "full_name": "Ellis, John Richard",
                "uuid": "e14955b0-7e57-41a0-90a8-f4c64eb8f4e9",
            }
        ]
    }
    data = faker.record("lit", data=author_data)
    record = LiteratureRecord.create(data)

    expected_result_create = [
        {
            "full_name": "Ellis, John Richard",
            "uuid": "e14955b0-7e57-41a0-90a8-f4c64eb8f4e9",
        }
    ]

    assert expected_result_create == record["authors"]


def test_literature_create_with_invalid_data_and_mutliple_pids(inspire_app):
    doi_value = faker.doi()
    arxiv_value = faker.arxiv()
    data = {"arxiv_eprints": [{"value": arxiv_value}], "dois": [{"value": doi_value}]}
    data = faker.record("lit", with_control_number=True, data=data)
    data["invalid_key"] = "should throw an error"
    pid_lit_value = str(data["control_number"])
    pid_arxiv_value = arxiv_value
    pid_doi_value = doi_value

    with pytest.raises(ValidationError):
        LiteratureRecord.create(data)

    record_lit_pid = PersistentIdentifier.query.filter_by(
        pid_value=pid_lit_value
    ).one_or_none()
    record_arxiv_pid = PersistentIdentifier.query.filter_by(
        pid_value=pid_arxiv_value
    ).one_or_none()
    record_doi_pid = PersistentIdentifier.query.filter_by(
        pid_value=pid_doi_value
    ).one_or_none()

    assert record_lit_pid is None
    assert record_arxiv_pid is None
    assert record_doi_pid is None


def test_literature_update(inspire_app):
    data = faker.record("lit", with_control_number=True)
    record = LiteratureRecord.create(data)

    assert data["control_number"] == record["control_number"]

    data.update({"titles": [{"title": "UPDATED"}]})
    record.update(data)
    control_number = str(record["control_number"])
    record_updated_db = RecordMetadata.query.filter_by(id=record.id).one()

    assert data == record_updated_db.json

    record_updated_pid = PersistentIdentifier.query.filter_by(
        pid_type="lit", pid_value=str(control_number)
    ).one()

    assert record.model.id == record_updated_pid.object_uuid
    assert control_number == record_updated_pid.pid_value


def test_literature_create_or_update_with_new_record(inspire_app):
    data = faker.record("lit")
    record = LiteratureRecord.create_or_update(data)

    control_number = str(record["control_number"])
    record_db = RecordMetadata.query.filter_by(id=record.id).one()

    assert record == record_db.json

    record_pid = PersistentIdentifier.query.filter_by(
        pid_type="lit", pid_value=str(control_number)
    ).one()

    assert record.model.id == record_pid.object_uuid
    assert control_number == record_pid.pid_value


def test_literature_create_or_update_with_existing_record(inspire_app):
    data = faker.record("lit", with_control_number=True)
    record = LiteratureRecord.create(data)

    assert data["control_number"] == record["control_number"]

    data.update({"titles": [{"title": "UPDATED"}]})

    record_updated = LiteratureRecord.create_or_update(data)
    control_number = str(record_updated["control_number"])

    assert record["control_number"] == record_updated["control_number"]

    record_updated_db = RecordMetadata.query.filter_by(id=record_updated.id).one()

    assert data == record_updated_db.json

    record_updated_pid = PersistentIdentifier.query.filter_by(
        pid_type="lit", pid_value=str(control_number)
    ).one()

    assert record_updated.model.id == record_updated_pid.object_uuid
    assert control_number == record_updated_pid.pid_value


def test_get_record_from_db_depending_on_its_pid_type(inspire_app):
    data = faker.record("lit")
    record = InspireRecord.create(data)
    record_from_db = InspireRecord.get_record(record.id)
    assert isinstance(record_from_db, LiteratureRecord)


def test_dump_for_es(inspire_app):
    additional_fields = {
        "preprint_date": "2016-01-01",
        "publication_info": [{"year": 2015}],
    }
    data = faker.record("lit", data=additional_fields)
    expected_document_type = ["article"]
    record = LiteratureRecord.create(data)
    dump = record.serialize_for_es()

    assert "_ui_display" in dump
    assert "_expanded_authors_display" in dump
    assert "_latex_us_display" in dump
    assert "_latex_eu_display" in dump
    assert "_bibtex_display" in dump
    assert "_cv_format" in dump
    assert "control_number" in dump
    assert record["control_number"] == dump["control_number"]
    assert "id" in dump
    assert record["control_number"] == dump["id"]
    assert expected_document_type == dump["document_type"]

    ui_field = orjson.loads(dump["_ui_display"])
    assert "titles" in ui_field
    assert "document_type" in ui_field
    assert record["titles"] == ui_field["titles"]
    assert record["control_number"] == ui_field["control_number"]


@freeze_time("1994-12-19")
def test_dump_for_es_adds_latex_and_bibtex_displays(inspire_app):
    additional_fields = {
        "titles": [{"title": "Jessica Jones"}],
        "authors": [
            {"full_name": "Castle, Frank"},
            {"full_name": "Smith, John"},
            {"full_name": "Black, Joe Jr."},
            {"full_name": "Jimmy"},
        ],
        "collaborations": [{"value": "LHCb"}],
        "dois": [{"value": "10.1088/1361-6633/aa5514"}],
        "arxiv_eprints": [{"value": "1607.06746", "categories": ["hep-th"]}],
        "publication_info": [
            {
                "journal_title": "Phys.Rev.A",
                "journal_volume": "58",
                "page_start": "500",
                "page_end": "593",
                "artid": "17920",
                "year": 2014,
            }
        ],
        "report_numbers": [{"value": "DESY-17-036"}],
    }
    data = faker.record("lit", data=additional_fields)
    record = LiteratureRecord.create(data)
    texkey = record["texkeys"][0]
    et_al_string = "et al."
    dump = record.serialize_for_es()
    expected_latex_eu_display = (
        f"%\\cite{{{texkey}}}\n\\bibitem{{{texkey}}}\nF.~Castle \\textit{{{et_al_string}}}"
        " [LHCb],\n%``Jessica Jones,''\nPhys. Rev. A \\textbf{58} (2014),"
        " 500-593\ndoi:10.1088/1361-6633/aa5514\n[arXiv:1607.06746 [hep-th]].\n%0"
        " citations counted in INSPIRE as of 19 Dec 1994"
    )
    expected_latex_us_display = (
        f"%\\cite{{{texkey}}}\n\\bibitem{{{texkey}}}\nF.~Castle \\textit{{{et_al_string}}}"
        " [LHCb],\n%``Jessica Jones,''\nPhys. Rev. A \\textbf{58}, 500-593"
        " (2014)\ndoi:10.1088/1361-6633/aa5514\n[arXiv:1607.06746 [hep-th]].\n%0"
        " citations counted in INSPIRE as of 19 Dec 1994"
    )
    expected_bibtex_display = (
        f"@article{{{texkey},\n"
        '    author = "Castle, Frank and Smith, John and Black, Joe Jr. and Jimmy",\n'
        '    collaboration = "LHCb",\n'
        '    title = "{Jessica Jones}",\n'
        '    eprint = "1607.06746",\n'
        '    archivePrefix = "arXiv",\n'
        '    primaryClass = "hep-th",\n'
        '    reportNumber = "DESY-17-036",\n'
        '    doi = "10.1088/1361-6633/aa5514",\n'
        '    journal = "Phys. Rev. A",\n'
        '    volume = "58",\n'
        '    pages = "500--593",\n'
        '    year = "2014"\n'
        "}\n"
    )
    assert expected_latex_eu_display == dump["_latex_eu_display"]
    assert expected_latex_us_display == dump["_latex_us_display"]
    assert expected_bibtex_display == dump["_bibtex_display"]


@mock.patch(
    "inspirehep.records.serializers.bibtex.literature_bibtex.create_bibliography"
)
def test_dump_for_es_catches_bibtex_exception(mock_bibtex, inspire_app):
    mock_bibtex.side_effect = Exception
    data = faker.record("lit")
    record = LiteratureRecord.create(data)
    expected_result = (
        f"% Bibtex generation failed for record {record.get('control_number')}"
    )
    dump = record.serialize_for_es()
    assert expected_result == dump["_bibtex_display"]


def test_create_record_from_db_depending_on_its_pid_type(inspire_app):
    data = faker.record("lit")
    record = InspireRecord.create(data)
    assert isinstance(record, LiteratureRecord)
    assert record.pid_type == "lit"

    record = LiteratureRecord.create(data)
    assert isinstance(record, LiteratureRecord)
    assert record.pid_type == "lit"


def test_create_or_update_record_from_db_depending_on_its_pid_type(inspire_app):
    data = faker.record("lit")
    record = InspireRecord.create_or_update(data)
    assert isinstance(record, LiteratureRecord)
    assert record.pid_type == "lit"

    data_update = {"titles": [{"title": "UPDATED"}]}
    data.update(data_update)
    record = InspireRecord.create_or_update(data)
    assert isinstance(record, LiteratureRecord)
    assert record.pid_type == "lit"


def test_import_article_bad_arxiv_id(inspire_app):
    with pytest.raises(UnknownImportIdentifierError):
        import_article("bad_arXiv:1207.7214")


def test_import_article_bad_doi(inspire_app):
    with pytest.raises(UnknownImportIdentifierError):
        import_article("doi:Th1s1s/n0taD01")


def test_import_article_arxiv_id_already_in_inspire(inspire_app):
    arxiv_value = faker.arxiv()
    data = {"arxiv_eprints": [{"value": arxiv_value}]}
    data = faker.record("lit", with_control_number=True, data=data)
    LiteratureRecord.create(data)

    with pytest.raises(ExistingArticleError):
        import_article(f"arXiv:{arxiv_value}")


def test_import_article_doi_already_in_inspire(inspire_app):
    doi_value = faker.doi()
    data = {"dois": [{"value": doi_value}]}
    data = faker.record("lit", with_control_number=True, data=data)
    LiteratureRecord.create(data)

    with pytest.raises(ExistingArticleError):
        import_article(doi_value)


def test_create_record_update_citation_table(inspire_app):
    data = faker.record("lit")
    record = LiteratureRecord.create(data)

    data2 = faker.record("lit", literature_citations=[record["control_number"]])
    record2 = LiteratureRecord.create(data2)

    assert len(record.model.citations) == 1
    assert len(record.model.references) == 0
    assert len(record2.model.citations) == 0
    assert len(record2.model.references) == 1
    assert len(RecordCitations.query.all()) == 1


def test_update_record_update_citation_table(inspire_app):
    data = faker.record("lit")
    record = LiteratureRecord.create(data)

    data2 = faker.record("lit")
    record2 = LiteratureRecord.create(data2)

    # Cannot use model.citations and model.references
    # when updating record which is not commited,
    # as they will return data from before the update
    assert len(RecordCitations.query.all()) == 0

    data = faker.record(
        "lit", data=record, literature_citations=[record2["control_number"]]
    )
    record.update(data)

    assert len(RecordCitations.query.all()) == 1


def test_complex_records_interactions_in_citation_table(inspire_app):
    records_list = []
    for _i in range(6):
        data = faker.record(
            "lit", literature_citations=[r["control_number"] for r in records_list]
        )
        record = LiteratureRecord.create(data)
        records_list.append(record)

    assert len(records_list[0].model.citations) == 5
    assert len(records_list[0].model.references) == 0

    assert len(records_list[1].model.citations) == 4
    assert len(records_list[1].model.references) == 1

    assert len(records_list[2].model.citations) == 3
    assert len(records_list[2].model.references) == 2

    assert len(records_list[3].model.citations) == 2
    assert len(records_list[3].model.references) == 3

    assert len(records_list[4].model.citations) == 1
    assert len(records_list[4].model.references) == 4

    assert len(records_list[5].model.citations) == 0
    assert len(records_list[5].model.references) == 5


def test_literature_can_cite_data_record(inspire_app):
    data = faker.record("dat")
    record = InspireRecord.create(data)

    data2 = faker.record("lit", data_citations=[record["control_number"]])
    record2 = LiteratureRecord.create(data2)

    assert len(record.model.citations) == 1
    assert len(record.model.references) == 0
    assert len(record2.model.citations) == 0
    assert len(record2.model.references) == 1
    assert len(RecordCitations.query.all()) == 1


def test_literature_cannot_cite_other_than_data_and_literature_record(inspire_app):
    author = InspireRecord.create(faker.record("aut"))
    conference = InspireRecord.create(faker.record("con"))
    experiment = InspireRecord.create(faker.record("exp"))
    institution = InspireRecord.create(faker.record("ins"))
    job = InspireRecord.create(faker.record("job"))
    journal = InspireRecord.create(faker.record("jou"))

    data2 = faker.record(
        "lit",
        literature_citations=[
            author["control_number"],
            conference["control_number"],
            experiment["control_number"],
            institution["control_number"],
            job["control_number"],
            journal["control_number"],
        ],
    )
    record2 = LiteratureRecord.create(data2)

    assert len(record2.model.citations) == 0
    assert len(record2.model.references) == 0
    assert len(RecordCitations.query.all()) == 0


def test_literature_can_cite_only_existing_records(inspire_app):
    data = faker.record("dat")
    record = InspireRecord.create(data)

    data2 = faker.record("lit", data_citations=[record["control_number"], 9999, 9998])
    record2 = LiteratureRecord.create(data2)

    assert len(record.model.citations) == 1
    assert len(record.model.references) == 0
    assert len(record2.model.citations) == 0
    assert len(record2.model.references) == 1
    assert len(RecordCitations.query.all()) == 1


def test_literature_is_not_cited_by_deleted_records(inspire_app):
    data = faker.record("lit")
    record = InspireRecord.create(data)

    data2 = faker.record("lit", literature_citations=[record["control_number"]])
    record2 = LiteratureRecord.create(data2)

    assert len(record.model.citations) == 1
    assert len(record.model.references) == 0
    assert len(record2.model.citations) == 0
    assert len(record2.model.references) == 1
    assert len(RecordCitations.query.all()) == 1

    record2.delete()
    db.session.refresh(record.model)

    assert len(record.model.citations) == 0
    assert len(record.model.references) == 0
    assert len(RecordCitations.query.all()) == 0


def test_literature_citation_count_property(inspire_app):
    data = faker.record("lit")
    record = InspireRecord.create(data)

    data2 = faker.record("lit", literature_citations=[record["control_number"]])
    record2 = LiteratureRecord.create(data2)

    assert record.citation_count == 1
    assert record2.citation_count == 0


def test_literature_without_literature_collection_cannot_cite_record_which_can_be_cited(
    inspire_app,
):
    data1 = faker.record("lit")
    record1 = InspireRecord.create(data1)

    data2 = faker.record(
        "lit",
        data={"_collections": ["Fermilab"]},
        literature_citations=[record1["control_number"]],
    )
    record2 = InspireRecord.create(data2)

    data3 = faker.record("lit", literature_citations=[record1["control_number"]])
    record3 = InspireRecord.create(data3)

    assert len(record1.model.citations) == 1
    assert len(record1.model.references) == 0
    assert len(record2.model.citations) == 0
    assert len(record2.model.references) == 0
    assert len(record3.model.citations) == 0
    assert len(record3.model.references) == 1


@mock.patch("inspirehep.records.api.literature.push_to_orcid")
def test_record_create_not_run_orcid_when_passed_parameter_to_disable_orcid(
    orcid_mock, inspire_app
):
    data1 = faker.record("lit")
    InspireRecord.create(data1, disable_external_push=True)
    assert orcid_mock.call_count == 0


@mock.patch("inspirehep.records.api.literature.push_to_orcid")
def test_record_create_not_skips_orcid_on_default(orcid_mock, inspire_app):
    data1 = faker.record("lit")
    InspireRecord.create(data1)
    assert orcid_mock.call_count == 1


@mock.patch("inspirehep.records.api.mixins.CitationMixin.update_refs_in_citation_table")
def test_record_create_skips_citation_recalculate_when_passed_parameter_to_skip(
    citation_recalculate_mock, inspire_app
):
    data1 = faker.record("lit")
    InspireRecord.create(data1, disable_relations_update=True)
    assert citation_recalculate_mock.call_count == 0


@mock.patch("inspirehep.records.api.mixins.CitationMixin.update_refs_in_citation_table")
def test_record_create_runs_citation_recalculate_on_default(
    citation_recalculate_mock, inspire_app
):
    data1 = faker.record("lit")
    InspireRecord.create(data1)
    assert citation_recalculate_mock.call_count == 1


@mock.patch("inspirehep.records.api.literature.push_to_orcid")
def test_record_update_not_run_orcid_when_passed_parameter_to_disable_orcid(
    orcid_mock, inspire_app
):
    data1 = faker.record("lit")
    data2 = faker.record("lit")
    record1 = InspireRecord.create(data1, disable_external_push=True)
    data2["control_number"] = record1["control_number"]
    record1.update(data2, disable_external_push=True)
    assert orcid_mock.call_count == 0


@mock.patch("inspirehep.records.api.literature.push_to_orcid")
def test_record_update_not_skips_orcid_on_default(orcid_mock, inspire_app):
    data1 = faker.record("lit")
    data2 = faker.record("lit")
    record1 = InspireRecord.create(data1)
    data2["control_number"] = record1["control_number"]
    record1.update(data2)
    assert orcid_mock.call_count == 2


@mock.patch(
    "inspirehep.records.api.literature.LiteratureRecord.update_refs_in_citation_table"
)
def test_record_update_skips_citation_recalculate_when_passed_parameter_to_skip(
    citation_recalculate_mock, inspire_app
):
    data1 = faker.record("lit")
    data2 = faker.record("lit")
    record1 = InspireRecord.create(data1, disable_relations_update=True)
    data2["control_number"] = record1["control_number"]
    record1.update(data2, disable_relations_update=True)
    assert citation_recalculate_mock.call_count == 0


@mock.patch(
    "inspirehep.records.api.literature.LiteratureRecord.update_refs_in_citation_table"
)
def test_record_update_runs_citation_recalculate_on_default(
    citation_recalculate_mock, inspire_app
):
    data1 = faker.record("lit")
    data2 = faker.record("lit")
    record1 = InspireRecord.create(data1)
    data2["control_number"] = record1["control_number"]
    record1.update(data2)
    assert citation_recalculate_mock.call_count == 2


def test_get_modified_references(inspire_app):
    cited_data = faker.record("lit")
    cited_record_1 = InspireRecord.create(cited_data)

    citing_data = faker.record(
        "lit", literature_citations=[cited_record_1["control_number"]]
    )
    citing_record = LiteratureRecord.create(citing_data)

    assert citing_record.get_modified_references() == [cited_record_1.id]

    cited_data_2 = faker.record("lit")
    cited_record_2 = InspireRecord.create(cited_data_2)

    citing_data["references"] = [
        {
            "record": {
                "$ref": f"http://localhost:5000/api/literature/{cited_record_2['control_number']}"
            }
        }
    ]
    citing_data["control_number"] = citing_record["control_number"]
    citing_record.update(citing_data)

    assert citing_record.get_modified_references() == [cited_record_2.id]

    citing_record.delete()

    assert citing_record.get_modified_references() == [cited_record_2.id]


def test_record_cannot_cite_itself(inspire_app):
    data1 = faker.record("lit", with_control_number=True)
    record = create_record(
        "lit", data=data1, literature_citations=[data1["control_number"]]
    )
    assert record.citation_count == 0


@pytest.mark.vcr
def test_documents_with_large_size(inspire_app, override_config):
    with override_config(FILES_SIZE_LIMIT=1, FEATURE_FLAG_ENABLE_FILES=True):
        data = {
            "documents": [
                {
                    "source": "arxiv",
                    "key": "arXiv:nucl-th_9310031.pdf",
                    "url": "https://arxiv.org/pdf/1910.07488.pdf",
                }
            ],
        }
        data = faker.record("lit", data=data)
        with pytest.raises(FileSizeExceededError) as fs_error:
            LiteratureRecord.create(data)
        assert fs_error.value.code == 413


@pytest.mark.vcr
def test_add_record_with_documents_and_figures(inspire_app, s3):
    expected_figure_key = "a29b7e90ba08cd1565146fe81ebbecd5"
    expected_document_key = "f276b50c9e6401b5e212785a496efa4e"
    create_s3_bucket(expected_figure_key)
    create_s3_bucket(expected_document_key)
    data = {
        "documents": [
            {
                "source": "arxiv",
                "key": "arXiv:nucl-th_9310031.pdf",
                "url": "http://inspirehep.net/record/863300/files/fermilab-pub-10-255-e.pdf",
                "original_url": "http://original-url.com/2",
                "filename": "fermilab.pdf",
            }
        ],
        "figures": [
            {
                "url": "https://inspirehep.net/record/1759380/files/channelxi3.png",
                "key": "key",
                "original_url": "http://original-url.com/3",
                "filename": "channel.png",
            }
        ],
    }
    record = create_record("lit", data=data)
    expected_documents = [
        {
            "source": "arxiv",
            "key": expected_document_key,
            "url": current_s3_instance.get_public_url(expected_document_key),
            "original_url": "http://original-url.com/2",
            "filename": "fermilab.pdf",
        }
    ]
    expected_figures = [
        {
            "key": expected_figure_key,
            "url": current_s3_instance.get_public_url(expected_figure_key),
            "filename": "channel.png",
            "original_url": "http://original-url.com/3",
        }
    ]
    assert record["figures"] == expected_figures
    assert record["documents"] == expected_documents
    assert current_s3_instance.file_exists(expected_figure_key) is True
    assert current_s3_instance.file_exists(expected_document_key) is True
    metadata_document = current_s3_instance.get_file_metadata(expected_document_key)
    assert metadata_document["ContentDisposition"] == 'inline; filename="fermilab.pdf"'
    assert metadata_document["ContentType"] == "application/pdf"
    metadata_figure = current_s3_instance.get_file_metadata(expected_figure_key)
    assert metadata_figure["ContentDisposition"] == 'inline; filename="channel.png"'
    assert metadata_figure["ContentType"] == "image/png"


@pytest.mark.vcr
def test_adding_record_with_documents_adds_hidden(inspire_app, s3):
    expected_hidden_document_key = "b88e6b880b32d8ed06b9b740cfb6eb2a"
    create_s3_bucket(expected_hidden_document_key)
    data = {
        "documents": [
            {
                "source": "arxiv",
                "key": "arXiv:nucl-th_9310031.pdf",
                "url": "https://inspirehep.net/files/b88e6b880b32d8ed06b9b740cfb6eb2a",
                "original_url": "http://original-url.com/2",
                "filename": "myhiddenfile.pdf",
                "hidden": True,
            }
        ]
    }
    record = create_record("lit", data=data)
    expected_hidden_document = {
        "source": "arxiv",
        "key": expected_hidden_document_key,
        "url": current_s3_instance.get_public_url(expected_hidden_document_key),
        "original_url": "http://original-url.com/2",
        "filename": "myhiddenfile.pdf",
        "hidden": True,
    }

    assert expected_hidden_document in record["documents"]
    assert current_s3_instance.file_exists(expected_hidden_document_key) is True


@pytest.mark.vcr
def test_adding_record_with_duplicated_documents_and_figures(inspire_app, s3):
    expected_figure_key = "a29b7e90ba08cd1565146fe81ebbecd5"
    expected_document_key = "f276b50c9e6401b5e212785a496efa4e"
    create_s3_bucket(expected_figure_key)
    create_s3_bucket(expected_document_key)
    data = {
        "documents": [
            {
                "source": "arxiv",
                "key": "arXiv:nucl-th_9310031.pdf",
                "url": "http://old.inspirehep.net/record/863300/files/fermilab-pub-10-255-e.pdf",
                "original_url": "http://original-url.com/2",
                "filename": "fermilab.pdf",
            },
            {
                "source": "arxiv",
                "key": "key2",
                "url": "http://old.inspirehep.net/record/863300/files/fermilab-pub-10-255-e.pdf",
                "original_url": "http://original-url.com/1",
                "filename": "fermilab2.pdf",
            },
        ],
        "figures": [
            {
                "url": "https://old.inspirehep.net/record/1759380/files/channelxi3.png",
                "key": "key",
                "original_url": "http://original-url.com/3",
                "filename": "channel.jpg",
            },
            {
                "url": "https://old.inspirehep.net/record/1759380/files/channelxi3.png",
                "key": "key2",
                "original_url": "http://original-url.com/4",
                "filename": "channel2.jpg",
            },
        ],
    }
    record = create_record("lit", data=data)
    expected_documents1 = [
        {
            "source": "arxiv",
            "key": expected_document_key,
            "url": current_s3_instance.get_public_url(expected_document_key),
            "original_url": "http://original-url.com/2",
            "filename": "fermilab.pdf",
        }
    ]

    expected_documents2 = [
        {
            "source": "arxiv",
            "key": expected_document_key,
            "url": current_s3_instance.get_public_url(expected_document_key),
            "original_url": "http://original-url.com/1",
            "filename": "fermilab2.pdf",
        }
    ]

    expected_figures1 = [
        {
            "key": expected_figure_key,
            "url": current_s3_instance.get_public_url(expected_figure_key),
            "filename": "channel.jpg",
            "original_url": "http://original-url.com/3",
        }
    ]

    expected_figures2 = [
        {
            "key": expected_figure_key,
            "url": current_s3_instance.get_public_url(expected_figure_key),
            "filename": "channel2.jpg",
            "original_url": "http://original-url.com/4",
        }
    ]

    # Depending on which thread will be picked up first we can get one of 2 documents and one of 2 figures
    assert (
        record["figures"] == expected_figures1 or record["figures"] == expected_figures2
    )
    assert (
        record["documents"] == expected_documents1
        or record["documents"] == expected_documents2
    )
    assert current_s3_instance.file_exists(expected_figure_key) is True
    assert current_s3_instance.file_exists(expected_document_key) is True


@pytest.mark.vcr
def test_adding_record_with_document_without_filename(inspire_app, s3):
    expected_document_key = "f276b50c9e6401b5e212785a496efa4e"
    create_s3_bucket(expected_document_key)
    data = {
        "documents": [
            {
                "source": "arxiv",
                "key": "key",
                "url": "http://inspirehep.net/record/863300/files/fermilab-pub-10-255-e.pdf",
                "original_url": "http://original-url.com/2",
            }
        ]
    }
    record = create_record("lit", data=data)
    expected_documents = [
        {
            "source": "arxiv",
            "key": expected_document_key,
            "url": current_s3_instance.get_public_url(expected_document_key),
            "original_url": "http://original-url.com/2",
            "filename": "key",
        }
    ]
    assert expected_documents == record["documents"]
    assert current_s3_instance.file_exists(expected_document_key) is True
    metadata_document = current_s3_instance.get_file_metadata(expected_document_key)
    assert metadata_document["ContentDisposition"] == 'inline; filename="key"'


@pytest.mark.vcr
def test_adding_record_with_document_without_filename_or_key(inspire_app, s3):
    expected_document_key = "2604ee85348bddb0f02bee24657a31f9"
    create_s3_bucket(expected_document_key)
    data = {
        "documents": [
            {
                "source": "arxiv",
                "url": "https://arxiv.org/pdf/1007.5048.pdf",
                "original_url": "http://original-url.com/2",
            }
        ]
    }
    record = create_record("lit", data=data, skip_validation=True)
    expected_documents = [
        {
            "source": "arxiv",
            "key": expected_document_key,
            "url": current_s3_instance.get_public_url(expected_document_key),
            "original_url": "http://original-url.com/2",
            "filename": expected_document_key,
        }
    ]
    assert expected_documents == record["documents"]
    assert current_s3_instance.file_exists(expected_document_key) is True
    metadata_document = current_s3_instance.get_file_metadata(expected_document_key)
    assert (
        metadata_document["ContentDisposition"]
        == f'inline; filename="{expected_document_key}"'
    )


@pytest.mark.vcr
def test_adding_record_with_documents_with_existing_file_updates_metadata(
    inspire_app, s3
):
    expected_document_key = "f276b50c9e6401b5e212785a496efa4e"
    create_s3_bucket(expected_document_key)
    data = {
        "documents": [
            {
                "source": "arxiv",
                "key": "key",
                "url": "http://inspirehep.net/record/863300/files/fermilab-pub-10-255-e.pdf",
                "original_url": "http://original-url.com/2",
                "filename": "file1.pdf",
            }
        ]
    }

    create_record("lit", data=deepcopy(data))
    assert current_s3_instance.file_exists(expected_document_key) is True
    metadata_document = current_s3_instance.get_file_metadata(expected_document_key)
    assert metadata_document["ContentDisposition"] == 'inline; filename="file1.pdf"'
    data["documents"][0]["filename"] = "file2.pdf"
    create_record("lit", data=data)
    assert current_s3_instance.file_exists(expected_document_key) is True
    metadata_document = current_s3_instance.get_file_metadata(expected_document_key)
    assert metadata_document["ContentDisposition"] == 'inline; filename="file2.pdf"'


@pytest.mark.vcr
def test_adding_record_with_documents_with_full_url_without_original_url(
    inspire_app, s3
):
    expected_document_key = "f276b50c9e6401b5e212785a496efa4e"
    create_s3_bucket(expected_document_key)
    data = {
        "documents": [
            {
                "source": "arxiv",
                "key": "key",
                "url": "http://inspirehep.net/record/863300/files/fermilab-pub-10-255-e.pdf",
                "filename": "file1.pdf",
            }
        ]
    }
    record = create_record("lit", data=data)
    expected_documents = [
        {
            "source": "arxiv",
            "key": expected_document_key,
            "url": current_s3_instance.get_public_url(expected_document_key),
            "original_url": (
                "http://inspirehep.net/record/863300/files/fermilab-pub-10-255-e.pdf"
            ),
            "filename": "file1.pdf",
        }
    ]
    assert current_s3_instance.file_exists(expected_document_key) is True
    assert expected_documents == record["documents"]


def test_adding_record_with_documents_with_relative_url_without_original_url(
    inspire_app, s3
):
    with requests_mock.Mocker() as mocker:
        mocker.get(
            "http://localhost:5000/api/files/file1.pdf",
            status_code=200,
            content=b"This is a file",
        )

        expected_document_key = "5276effc61dd44a9fe1d5354bf2ad9c4"
        create_s3_bucket(expected_document_key)
        data = {
            "documents": [
                {
                    "source": "arxiv",
                    "key": "key",
                    "url": "/api/files/file1.pdf",
                    "filename": "file1.pdf",
                }
            ]
        }
        record = create_record("lit", data=data)
        expected_documents = [
            {
                "source": "arxiv",
                "key": expected_document_key,
                "url": current_s3_instance.get_public_url(expected_document_key),
                "filename": "file1.pdf",
            }
        ]
        assert current_s3_instance.file_exists(expected_document_key) is True
        assert expected_documents == record["documents"]


@pytest.mark.vcr
def test_adding_deleted_record_with_documents_does_not_add_files(inspire_app, s3):
    expected_document_key = "f276b50c9e6401b5e212785a496efa4e"
    create_s3_bucket(expected_document_key)
    data = {
        "deleted": True,
        "documents": [
            {
                "source": "arxiv",
                "key": "key",
                "url": "http://inspirehep.net/record/863300/files/fermilab-pub-10-255-e.pdf",
                "filename": "file1.pdf",
            }
        ],
    }
    create_record("lit", data=data)
    assert current_s3_instance.file_exists(expected_document_key) is False


@pytest.mark.vcr
def test_update_record_with_documents_and_figures(inspire_app, s3):
    expected_figure_key = "a29b7e90ba08cd1565146fe81ebbecd5"
    expected_document_key = "f276b50c9e6401b5e212785a496efa4e"
    create_s3_bucket(expected_figure_key)
    create_s3_bucket(expected_document_key)
    record = create_record("lit")
    data = dict(record)
    data.update(
        {
            "documents": [
                {
                    "source": "arxiv",
                    "key": "arXiv:nucl-th_9310031.pdf",
                    "url": "http://inspirehep.net/record/863300/files/fermilab-pub-10-255-e.pdf",
                    "original_url": "http://original-url.com/2",
                    "filename": "fermilab.pdf",
                }
            ],
            "figures": [
                {
                    "url": "https://inspirehep.net/record/1759380/files/channelxi3.png",
                    "key": "key",
                    "original_url": "http://original-url.com/3",
                    "filename": "channel.png",
                }
            ],
        }
    )
    record.update(data)
    expected_documents = [
        {
            "source": "arxiv",
            "key": expected_document_key,
            "url": current_s3_instance.get_public_url(expected_document_key),
            "original_url": "http://original-url.com/2",
            "filename": "fermilab.pdf",
        }
    ]
    expected_figures = [
        {
            "key": expected_figure_key,
            "url": current_s3_instance.get_public_url(expected_figure_key),
            "filename": "channel.png",
            "original_url": "http://original-url.com/3",
        }
    ]
    assert record["figures"] == expected_figures
    assert record["documents"] == expected_documents
    assert current_s3_instance.file_exists(expected_figure_key) is True
    assert current_s3_instance.file_exists(expected_document_key) is True
    metadata_document = current_s3_instance.get_file_metadata(expected_document_key)
    assert metadata_document["ContentDisposition"] == 'inline; filename="fermilab.pdf"'
    assert metadata_document["ContentType"] == "application/pdf"
    metadata_figure = current_s3_instance.get_file_metadata(expected_figure_key)
    assert metadata_figure["ContentDisposition"] == 'inline; filename="channel.png"'
    assert metadata_figure["ContentType"] == "image/png"


@pytest.mark.vcr
def test_update_record_remove_documents_and_figures(inspire_app, s3):
    expected_figure_key = "a29b7e90ba08cd1565146fe81ebbecd5"
    expected_document_key = "f276b50c9e6401b5e212785a496efa4e"
    create_s3_bucket(expected_figure_key)
    create_s3_bucket(expected_document_key)
    data = {
        "documents": [
            {
                "source": "arxiv",
                "key": "arXiv:nucl-th_9310031.pdf",
                "url": "http://inspirehep.net/record/863300/files/fermilab-pub-10-255-e.pdf",
                "original_url": "http://original-url.com/2",
                "filename": "fermilab.pdf",
            }
        ],
        "figures": [
            {
                "url": "https://inspirehep.net/record/1759380/files/channelxi3.png",
                "key": "key",
                "original_url": "http://original-url.com/3",
                "filename": "channel.png",
            }
        ],
    }
    record = create_record("lit", data)
    data = dict(record)
    del data["documents"]
    del data["figures"]
    record.update(data)

    assert "figures" not in record
    assert "documents" not in record


@pytest.mark.vcr
def test_update_record_add_more_documents(inspire_app, s3):
    expected_document_key = "b88e6b880b32d8ed06b9b740cfb6eb2a"
    expected_updated_document_key = "f276b50c9e6401b5e212785a496efa4e"
    create_s3_bucket(expected_document_key)
    create_s3_bucket(expected_updated_document_key)
    data = {
        "documents": [
            {
                "source": "arxiv",
                "key": "arXiv:nucl-th_9310031.pdf",
                "url": "http://old.inspirehep.net/record/212819/files/slac-pub-3557.pdf?version=1",
                "original_url": "http://original-url.com/2",
                "filename": "myfile.pdf",
            }
        ]
    }
    record = create_record("lit", data)
    data = dict(record)
    data_with_added_document = {
        "documents": [
            {
                "source": "arxiv",
                "key": "arXiv:nucl-th_9310031.pdf",
                "url": "http://old.inspirehep.net/record/212819/files/slac-pub-3557.pdf?version=1",
                "original_url": "http://original-url.com/2",
                "filename": "myfile.pdf",
            },
            {
                "source": "arxiv",
                "key": "key",
                "url": "http://old.inspirehep.net/record/863300/files/fermilab-pub-10-255-e.pdf",
                "original_url": "http://original-url.com/2",
                "filename": "fermilab.pdf",
            },
        ]
    }
    data.update(data_with_added_document)
    record.update(data)
    expected_document_old = {
        "source": "arxiv",
        "key": expected_document_key,
        "url": current_s3_instance.get_public_url(expected_document_key),
        "original_url": "http://original-url.com/2",
        "filename": "myfile.pdf",
    }
    expected_document_new = {
        "source": "arxiv",
        "key": expected_updated_document_key,
        "url": current_s3_instance.get_public_url(expected_updated_document_key),
        "original_url": "http://original-url.com/2",
        "filename": "fermilab.pdf",
    }
    assert expected_document_old in record["documents"]
    assert expected_document_new in record["documents"]
    assert current_s3_instance.file_exists(expected_updated_document_key) is True
    assert current_s3_instance.file_exists(expected_document_key) is True
    metadata_document = current_s3_instance.get_file_metadata(
        expected_updated_document_key
    )
    assert metadata_document["ContentDisposition"] == 'inline; filename="fermilab.pdf"'
    assert metadata_document["ContentType"] == "application/pdf"


@pytest.mark.vcr
def test_not_adding_unsupported_files(inspire_app, s3):
    expected_document_key = "b98fd32e5ba4fa4e1c4bb547c66734a8"
    create_s3_bucket(expected_document_key)
    data_html = {
        "documents": [
            {
                "source": "arxiv",
                "key": "arXiv:nucl-th_9310031.pdf",
                "url": "https://inspirehep.net/literature/863300",
                "original_url": "http://original-url.com/1",
                "filename": "fermilab.pdf",
            }
        ],
    }
    data_js = {
        "documents": [
            {
                "source": "arxiv",
                "key": "arXiv:nucl-th_9310031.pdf",
                "url": "https://inspirehep.net/config.js",
                "original_url": "http://original-url.com/2",
                "filename": "fermilab.pdf",
            }
        ],
    }
    data_pdf = {
        "documents": [
            {
                "source": "PoS",
                "key": "PoS:ICHEP2020_903.pdf",
                "url": "https://inspirehep.net/files/b98fd32e5ba4fa4e1c4bb547c66734a8",
                "original_url": "http://original-url.com/4",
                "filename": "PoS(ICHEP2020)903.pdf",
            }
        ],
    }
    expected_documents = [
        {
            "source": "PoS",
            "key": expected_document_key,
            "url": current_s3_instance.get_public_url(expected_document_key),
            "original_url": "http://original-url.com/4",
            "filename": "PoS(ICHEP2020)903.pdf",
        },
    ]
    with pytest.raises(UnsupportedFileError):
        create_record("lit", data_html)
    with pytest.raises(UnsupportedFileError):
        create_record("lit", data_js)
    record = create_record("lit", data_pdf)
    assert expected_documents == record["documents"]


def test_literature_updates_refs_to_known_conferences(inspire_app):
    con1 = create_record("con", {"opening_date": "2013-01-01"})
    con2 = create_record("con", {"opening_date": "2020-12-12"})

    lit_data = {"publication_info": [{"cnum": con1["cnum"]}, {"cnum": con2["cnum"]}]}

    expected_publication_info = [
        {
            "cnum": con1["cnum"],
            "conference_record": {
                "$ref": (
                    f"http://localhost:5000/api/conferences/{con1['control_number']}"
                )
            },
        },
        {
            "cnum": con2["cnum"],
            "conference_record": {
                "$ref": (
                    f"http://localhost:5000/api/conferences/{con2['control_number']}"
                )
            },
        },
    ]
    lit = create_record("lit", data=lit_data)

    assert expected_publication_info == lit["publication_info"]


def test_literature_updates_refs_to_known_and_unknown_conference(inspire_app):
    con = create_record("con", {"opening_date": "2013-01-01"})

    lit_data = {"publication_info": [{"cnum": con["cnum"]}, {"cnum": "C99-11-11.111"}]}

    expected_publication_info = [
        {
            "cnum": con["cnum"],
            "conference_record": {
                "$ref": f"http://localhost:5000/api/conferences/{con['control_number']}"
            },
        },
        {"cnum": "C99-11-11.111"},
    ]
    lit = create_record("lit", data=lit_data)

    assert expected_publication_info == lit["publication_info"]


def test_literature_updates_refs_to_known_and_unknown_conference_when_ref_already_exists(
    inspire_app,
):
    con = create_record("con", {"opening_date": "2013-01-01"})

    lit_data = {
        "publication_info": [
            {
                "cnum": con["cnum"],
                "conference_record": {
                    "$ref": "http://localhost:5000/api/conferences/123"
                },
            },
            {
                "cnum": "C99-11-11.111",
                "conference_record": {
                    "$ref": "http://localhost:5000/api/conferences/123"
                },
            },
        ]
    }

    expected_publication_info = [
        {
            "cnum": con["cnum"],
            "conference_record": {
                "$ref": f"http://localhost:5000/api/conferences/{con['control_number']}"
            },
        },
        {
            "cnum": "C99-11-11.111",
            "conference_record": {"$ref": "http://localhost:5000/api/conferences/123"},
        },
    ]
    lit = create_record("lit", data=lit_data)

    assert expected_publication_info == lit["publication_info"]


def test_do_not_add_files_which_are_already_on_s3(inspire_app, s3):
    data = {
        "documents": [
            {
                "filename": "1905.03764.pdf",
                "key": "some_document_key_on_s3",
                "original_url": "http://inspire-afs-web.cern.ch/var/data/files/g188/3771224/content.pdf%3B2",
                "source": "arxiv",
                "url": "http://localhost:5000/files/some_document_key_on_s3",
            }
        ],
        "figures": [
            {
                "caption": "some caption",
                "filename": "Global_noH3_EW_couplings_flat.png",
                "key": "some_figure_key_on_s3",
                "original_url": "http://inspire-afs-web.cern.ch/var/data/files/g188/3771220/content.png%3B2",
                "source": "arxiv",
                "url": "http://localhost:5000/files/some_figure_key_on_s3",
            }
        ],
    }
    with mock.patch.object(
        current_s3_instance, "replace_file_metadata"
    ) as mocked_s3_replace_metadata:
        record = create_record("lit", data=data)
        mocked_s3_replace_metadata.assert_not_called()
    expected_documents = [
        {
            "filename": "1905.03764.pdf",
            "key": "some_document_key_on_s3",
            "original_url": "http://inspire-afs-web.cern.ch/var/data/files/g188/3771224/content.pdf%3B2",
            "source": "arxiv",
            "url": "http://localhost:5000/files/some_document_key_on_s3",
        }
    ]
    expected_figures = [
        {
            "caption": "some caption",
            "filename": "Global_noH3_EW_couplings_flat.png",
            "key": "some_figure_key_on_s3",
            "original_url": "http://inspire-afs-web.cern.ch/var/data/files/g188/3771220/content.png%3B2",
            "source": "arxiv",
            "url": "http://localhost:5000/files/some_figure_key_on_s3",
        }
    ]
    assert record["figures"] == expected_figures
    assert record["documents"] == expected_documents


def test_files_metadata_is_replaced_when_replacing_metadata_is_enabled(
    inspire_app, s3, override_config
):
    expected_figure_key = "cb071d80d1a54f21c8867a038f6a6c66"
    expected_document_key = "fdc3bdefb79cec8eb8211d2499e04704"
    create_s3_bucket(expected_figure_key)
    create_s3_bucket(expected_document_key)
    data = {
        "documents": [
            {
                "source": "arxiv",
                "key": "arXiv:nucl-th_9310031.pdf",
                "url": "http://original-url.com/2",
                "filename": "fermilab.pdf",
            }
        ],
        "figures": [{"url": "http://original-url.com/3", "key": "channel.png"}],
    }

    figure_content = b"figure"
    document_content = b"document"
    with requests_mock.Mocker() as mocker:
        mocker.get(
            "http://original-url.com/2", status_code=200, content=document_content
        )
        mocker.get("http://original-url.com/3", status_code=200, content=figure_content)
        mocker.get(
            current_s3_instance.get_public_url(expected_document_key),
            status_code=200,
            content=document_content,
        )
        mocker.get(
            current_s3_instance.get_public_url(expected_figure_key),
            status_code=200,
            content=figure_content,
        )

        record = create_record("lit", data=data)

        record_data = dict(record)
        files_count = 2
        with (
            override_config(**{"UPDATE_S3_FILES_METADATA": True}),
            mock.patch.object(
                current_s3_instance, "replace_file_metadata"
            ) as mocked_s3_replace_metadata,
        ):
            record.update(record_data)
            assert mocked_s3_replace_metadata.call_count == files_count


def test_adding_files_with_public_file_url_but_wrong_key(inspire_app, s3):
    expected_figure_key = "cb071d80d1a54f21c8867a038f6a6c66"
    expected_document_key = "fdc3bdefb79cec8eb8211d2499e04704"
    create_s3_bucket(expected_figure_key)
    create_s3_bucket(expected_document_key)
    data = {
        "documents": [
            {
                "url": current_s3_instance.get_public_url(expected_document_key),
                "source": "arxiv",
                "key": "arXiv:nucl-th_9310031.pdf",
                "original_url": "http://original-url.com/2",
            }
        ],
        "figures": [
            {
                "url": current_s3_instance.get_public_url(expected_figure_key),
                "original_url": "http://original-url.com/3",
                "key": "channel.png",
            }
        ],
    }

    expected_documents = [
        {
            "url": current_s3_instance.get_public_url(expected_document_key),
            "source": "arxiv",
            "filename": "arXiv:nucl-th_9310031.pdf",
            "original_url": "http://original-url.com/2",
            "key": expected_document_key,
        }
    ]

    expected_figures = [
        {
            "url": current_s3_instance.get_public_url(expected_figure_key),
            "original_url": "http://original-url.com/3",
            "filename": "channel.png",
            "key": expected_figure_key,
        }
    ]

    figure_content = b"figure"
    document_content = b"document"
    with requests_mock.Mocker() as mocker:
        mocker.get(
            current_s3_instance.get_public_url(expected_document_key),
            status_code=200,
            content=document_content,
        )
        mocker.get(
            current_s3_instance.get_public_url(expected_figure_key),
            status_code=200,
            content=figure_content,
        )

        record = create_record("lit", data=data)

        assert record["figures"] == expected_figures
        assert record["documents"] == expected_documents


def test_creating_record_updates_entries_in_authors_records_table(inspire_app):
    author_1 = create_record("aut")
    author_2 = create_record("aut")
    expected_authors_entries_count = 4
    expected_table_entries = [
        (str(author_1["control_number"]), "recid"),
        (str(author_2["control_number"]), "recid"),
        ("collaboration_1", "collaboration"),
        ("collaboration_2", "collaboration"),
    ]
    data = {
        "authors": [
            {"full_name": author_1["name"]["value"], "record": author_1["self"]},
            {"full_name": author_2["name"]["value"], "record": author_2["self"]},
        ],
        "collaborations": [{"value": "collaboration_1"}, {"value": "collaboration_2"}],
    }

    record = create_record("lit", data=data)

    authors_records_entries = RecordsAuthors.query.filter_by(record_id=record.id).all()
    assert len(authors_records_entries) == expected_authors_entries_count
    table_entries = [
        (entry.author_id, entry.id_type) for entry in authors_records_entries
    ]
    assert sorted(table_entries) == sorted(expected_table_entries)


def test_updating_record_updates_entries_in_authors_records_table(inspire_app):
    expected_authors_entries_count = 3
    author_1 = create_record("aut")
    author_2 = create_record("aut")
    author_3 = create_record("aut")
    data = {
        "authors": [
            {"full_name": author_1["name"]["value"], "record": author_1["self"]},
            {"full_name": author_2["name"]["value"], "record": author_2["self"]},
        ],
        "collaborations": [{"value": "collaboration_1"}],
    }

    record = create_record("lit", data=data)

    assert (
        RecordsAuthors.query.filter_by(record_id=record.id).count()
        == expected_authors_entries_count
    )
    data = dict(record)
    data.update(
        {
            "authors": [
                {"full_name": author_1["name"]["value"], "record": author_1["self"]},
            ]
        }
    )
    expected_authors_entries_count = 2
    record.update(data)

    assert (
        RecordsAuthors.query.filter_by(record_id=record.id).count()
        == expected_authors_entries_count
    )

    data = dict(record)
    data.update(
        {
            "authors": [
                {"full_name": author_1["name"]["value"], "record": author_1["self"]},
                {"full_name": author_2["name"]["value"], "record": author_2["self"]},
                {"full_name": author_3["name"]["value"], "record": author_3["self"]},
            ],
            "collaborations": [
                {"value": "collaboration_1"},
                {"value": "collaboration_2"},
            ],
        }
    )
    expected_authors_entries_count = 5
    record.update(data)
    assert (
        RecordsAuthors.query.filter_by(record_id=record.id).count()
        == expected_authors_entries_count
    )


def test_not_literature_collection_do_not_create_entries_in_authors_records_table(
    inspire_app,
):
    data = {
        "_collections": ["ZEUS Internal Notes"],
        "authors": [
            {
                "full_name": "Kathryn Janeway",
                "ids": [{"value": "K.Janeway.1", "schema": "INSPIRE BAI"}],
            }
        ],
    }

    expected_authors_entries_count = 0

    record = create_record("lit", data=data)

    assert (
        RecordsAuthors.query.filter_by(record_id=record.id).count()
        == expected_authors_entries_count
    )


def test_deleted_record_do_not_create_entries_in_authors_records_table(inspire_app):
    data = {
        "authors": [
            {
                "full_name": "Kathryn Janeway",
                "ids": [{"value": "K.Janeway.1", "schema": "INSPIRE BAI"}],
            }
        ],
        "deleted": True,
    }

    expected_authors_entries_count = 0

    record = create_record("lit", data=data)

    assert (
        RecordsAuthors.query.filter_by(record_id=record.id).count()
        == expected_authors_entries_count
    )


def test_deleting_record_removes_entries_in_authors_records_table(inspire_app):
    data = {
        "authors": [
            {
                "full_name": "Kathryn Janeway",
                "ids": [{"value": "K.Janeway.1", "schema": "INSPIRE BAI"}],
            }
        ]
    }

    expected_authors_entries_count = 1

    record = create_record("lit", data=data)

    assert (
        RecordsAuthors.query.filter_by(record_id=record.id).count()
        == expected_authors_entries_count
    )

    record.delete()
    expected_authors_entries_count = 0
    assert (
        RecordsAuthors.query.filter_by(record_id=record.id).count()
        == expected_authors_entries_count
    )


def test_hard_deleting_record_removes_entries_in_authors_records_table(inspire_app):
    data = {
        "authors": [
            {
                "full_name": "Kathryn Janeway",
                "ids": [{"value": "K.Janeway.1", "schema": "INSPIRE BAI"}],
            }
        ]
    }

    expected_authors_entries_count = 1

    record = create_record("lit", data=data)

    assert (
        RecordsAuthors.query.filter_by(record_id=record.id).count()
        == expected_authors_entries_count
    )

    record.hard_delete()
    expected_authors_entries_count = 0
    assert (
        RecordsAuthors.query.filter_by(record_id=record.id).count()
        == expected_authors_entries_count
    )


def test_self_citations_on_authors_calculated_on_record_creation(inspire_app):
    data_authors = {
        "authors": [
            {
                "full_name": "Jean-Luc Picard",
                "ids": [{"schema": "INSPIRE BAI", "value": "Jean.L.Picard.1"}],
            }
        ]
    }
    rec1 = create_record("lit", data=data_authors)
    rec2 = create_record(
        "lit", data=data_authors, literature_citations=[rec1["control_number"]]
    )
    rec3 = create_record(
        "lit", literature_citations=[rec1["control_number"], rec2["control_number"]]
    )

    assert rec1.citation_count == 2
    assert rec1.citation_count_without_self_citations == 1

    assert rec2.citation_count == 1
    assert rec2.citation_count_without_self_citations == 1

    assert rec3.citation_count == 0
    assert rec3.citation_count_without_self_citations == 0


def test_mixed_self_citations_on_authors_calculated_on_record_creation(inspire_app):
    author_1 = {
        "full_name": "James T Kirk",
        "ids": [{"schema": "INSPIRE BAI", "value": "James.T.Kirk.1"}],
    }
    author_2 = {
        "full_name": "Jean-Luc Picard",
        "ids": [{"schema": "INSPIRE BAI", "value": "Jean.L.Picard.1"}],
    }
    author_3 = {
        "full_name": "Kathryn Janeway",
        "ids": [{"schema": "INSPIRE BAI", "value": "K.Janeway.1"}],
    }

    data_authors_1 = {"authors": [author_1]}

    data_authors_2 = {"authors": [author_1, author_2]}

    data_authors_3 = {"authors": [author_2, author_3]}
    rec1 = create_record("lit", data=data_authors_1)
    rec2 = create_record(
        "lit", data=data_authors_2, literature_citations=[rec1["control_number"]]
    )
    rec3 = create_record(
        "lit",
        data=data_authors_3,
        literature_citations=[rec1["control_number"], rec2["control_number"]],
    )

    assert rec1.citation_count == 2
    assert rec1.citation_count_without_self_citations == 1

    assert rec2.citation_count == 1
    assert rec2.citation_count_without_self_citations == 0

    assert rec3.citation_count == 0
    assert rec3.citation_count_without_self_citations == 0


def test_self_citations_on_authors_calculated_on_record_update(inspire_app):
    data_authors = {
        "authors": [
            {
                "full_name": "Jean-Luc Picard",
                "ids": [{"schema": "INSPIRE BAI", "value": "Jean.L.Picard.1"}],
            }
        ]
    }
    rec1 = create_record("lit", data=data_authors)
    rec2 = create_record(
        "lit", data=data_authors, literature_citations=[rec1["control_number"]]
    )
    rec3 = create_record(
        "lit", literature_citations=[rec1["control_number"], rec2["control_number"]]
    )

    assert rec1.citation_count == 2
    assert rec1.citation_count_without_self_citations == 1

    assert rec2.citation_count == 1
    assert rec2.citation_count_without_self_citations == 1

    assert rec3.citation_count == 0
    assert rec3.citation_count_without_self_citations == 0

    rec3_data = dict(rec3)
    rec3_data["authors"] = rec1["authors"]
    rec3.update(rec3_data)

    assert rec1.citation_count == 2
    assert rec1.citation_count_without_self_citations == 0

    assert rec2.citation_count == 1
    assert rec2.citation_count_without_self_citations == 0

    assert rec3.citation_count == 0
    assert rec3.citation_count_without_self_citations == 0


def test_self_citations_on_authors_calculated_on_other_record_update(inspire_app):
    author_1 = {
        "full_name": "James T Kirk",
        "ids": [{"schema": "INSPIRE BAI", "value": "James.T.Kirk.1"}],
    }

    author_2 = {
        "full_name": "Jean-Luc Picard",
        "ids": [{"schema": "INSPIRE BAI", "value": "Jean.L.Picard.1"}],
    }
    data_authors = {"authors": [author_1]}
    rec1 = create_record("lit", data=data_authors)
    rec2 = create_record(
        "lit", data=data_authors, literature_citations=[rec1["control_number"]]
    )

    assert rec1.citation_count == 1
    assert rec1.citation_count_without_self_citations == 0

    assert rec2.citation_count == 0
    assert rec2.citation_count_without_self_citations == 0

    rec1_data = dict(rec1)
    rec1_data["authors"] = [author_2]
    rec1.update(rec1_data)

    assert rec1.citation_count == 1
    assert rec1.citation_count_without_self_citations == 1

    assert rec2.citation_count == 0
    assert rec2.citation_count_without_self_citations == 0


def test_self_citations_on_collaborations_calculated_on_record_creation(inspire_app):
    data_collaborations = {"collaborations": [{"value": "COL1"}]}
    rec1 = create_record("lit", data=data_collaborations)
    rec2 = create_record(
        "lit", data=data_collaborations, literature_citations=[rec1["control_number"]]
    )
    rec3 = create_record(
        "lit", literature_citations=[rec1["control_number"], rec2["control_number"]]
    )

    assert rec1.citation_count == 2
    assert rec1.citation_count_without_self_citations == 1

    assert rec2.citation_count == 1
    assert rec2.citation_count_without_self_citations == 1

    assert rec3.citation_count == 0
    assert rec3.citation_count_without_self_citations == 0


def test_mixed_self_citations_on_collaborations_calculated_on_record_creation(
    inspire_app,
):
    collaboration_1 = {"value": "COL1"}
    collaboration_2 = {"value": "COL2"}
    collaboration_3 = {"value": "COL3"}

    data_collaborations_1 = {"collaborations": [collaboration_1]}

    data_collaborations_2 = {"collaborations": [collaboration_1, collaboration_2]}

    data_collaborations_3 = {"collaborations": [collaboration_2, collaboration_3]}
    rec1 = create_record("lit", data=data_collaborations_1)
    rec2 = create_record(
        "lit", data=data_collaborations_2, literature_citations=[rec1["control_number"]]
    )
    rec3 = create_record(
        "lit",
        data=data_collaborations_3,
        literature_citations=[rec1["control_number"], rec2["control_number"]],
    )

    assert rec1.citation_count == 2
    assert rec1.citation_count_without_self_citations == 1

    assert rec2.citation_count == 1
    assert rec2.citation_count_without_self_citations == 0

    assert rec3.citation_count == 0
    assert rec3.citation_count_without_self_citations == 0


def test_self_citations_on_collaborations_calculated_on_record_update(inspire_app):
    data_collaborations = {"collaborations": [{"value": "COL1"}]}
    rec1 = create_record("lit", data=data_collaborations)
    rec2 = create_record(
        "lit", data=data_collaborations, literature_citations=[rec1["control_number"]]
    )
    rec3 = create_record(
        "lit", literature_citations=[rec1["control_number"], rec2["control_number"]]
    )

    assert rec1.citation_count == 2
    assert rec1.citation_count_without_self_citations == 1

    assert rec2.citation_count == 1
    assert rec2.citation_count_without_self_citations == 1

    assert rec3.citation_count == 0
    assert rec3.citation_count_without_self_citations == 0

    rec3_data = dict(rec3)
    rec3_data["collaborations"] = rec1["collaborations"]
    rec3.update(rec3_data)

    assert rec1.citation_count == 2
    assert rec1.citation_count_without_self_citations == 0

    assert rec2.citation_count == 1
    assert rec2.citation_count_without_self_citations == 0

    assert rec3.citation_count == 0
    assert rec3.citation_count_without_self_citations == 0


def test_self_citations_on_collaborations_calculated_on_other_record_update(
    inspire_app,
):
    collaboration_1 = {"value": "COL1"}
    collaboration_2 = {"value": "COL2"}
    data_collaborations = {"collaborations": [collaboration_1]}
    rec1 = create_record("lit", data=data_collaborations)
    rec2 = create_record(
        "lit", data=data_collaborations, literature_citations=[rec1["control_number"]]
    )

    assert rec1.citation_count == 1
    assert rec1.citation_count_without_self_citations == 0

    assert rec2.citation_count == 0
    assert rec2.citation_count_without_self_citations == 0

    rec1_data = dict(rec1)
    rec1_data["collaborations"] = [collaboration_2]
    rec1.update(rec1_data)

    assert rec1.citation_count == 1
    assert rec1.citation_count_without_self_citations == 1

    assert rec2.citation_count == 0
    assert rec2.citation_count_without_self_citations == 0


def test_arxiv_url_also_supports_format_alias_latex(inspire_app):
    expected_latex_us_type = "application/vnd+inspire.latex.us+x-latex"
    expected_latex_eu_type = "application/vnd+inspire.latex.eu+x-latex"

    data = {
        "arxiv_eprints": [
            {"value": "1607.06746", "categories": ["hep-th"]},
            {"categories": ["hep-ph"], "value": "hep-ph/9709356"},
        ]
    }
    create_record("lit", data)

    with inspire_app.test_client() as client:
        url = "/api/arxiv/hep-ph/9709356"
        response_latex_us = client.get(f"{url}?format=latex-us")
        response_latex_eu = client.get(f"{url}?format=latex-eu")

    assert response_latex_us.status_code == 200
    assert response_latex_us.content_type == expected_latex_us_type

    assert response_latex_eu.status_code == 200
    assert response_latex_eu.content_type == expected_latex_eu_type


def test_arxiv_url_also_supports_format_alias_bibtex(inspire_app):
    expected_bibtex_type = "application/x-bibtex"

    data = {
        "arxiv_eprints": [
            {"value": "1607.06746", "categories": ["hep-th"]},
            {"categories": ["hep-ph"], "value": "hep-ph/9709356"},
        ]
    }
    create_record("lit", data)

    with inspire_app.test_client() as client:
        url = "/api/arxiv/hep-ph/9709356"
        response_bibtex = client.get(f"{url}?format=bibtex")

    assert response_bibtex.status_code == 200
    assert response_bibtex.content_type == expected_bibtex_type


def test_arxiv_url_also_supports_format_alias_json(inspire_app):
    expected_bibtex_type = "application/json"

    data = {
        "arxiv_eprints": [
            {"value": "1607.06746", "categories": ["hep-th"]},
            {"categories": ["hep-ph"], "value": "hep-ph/9709356"},
        ]
    }
    create_record("lit", data)

    with inspire_app.test_client() as client:
        url = "/api/arxiv/hep-ph/9709356"
        response_json = client.get(f"{url}?format=json")

    assert response_json.status_code == 200
    assert response_json.content_type == expected_bibtex_type


def test_arxiv_url_also_supports_format_alias_cv(inspire_app):
    expected_cv_type = "text/vnd+inspire.html+html; charset=utf-8"

    data = {
        "arxiv_eprints": [
            {"value": "1607.06746", "categories": ["hep-th"]},
            {"categories": ["hep-ph"], "value": "hep-ph/9709356"},
        ]
    }
    create_record("lit", data)

    with inspire_app.test_client() as client:
        url = "/api/arxiv/hep-ph/9709356"
        response_cv = client.get(f"{url}?format=cv")

    assert response_cv.status_code == 200
    assert response_cv.content_type == expected_cv_type


def test_cv_format_regression(inspire_app):
    expected_cv_type = "text/vnd+inspire.html+html; charset=utf-8"

    data = {
        "titles": [{"title": "Test"}],
        "arxiv_eprints": [
            {"value": "1607.06746", "categories": ["hep-th"]},
        ],
        "authors": [
            {
                "ids": [{"schema": "INSPIRE BAI", "value": "Joshua.Isaacson.1"}],
                "full_name": "Test, test",
            }
        ],
    }
    lit_record = create_record("lit", data)

    with inspire_app.test_client() as client:
        url = "api/literature?format=cv&q=a%20Joshua.Isaacson.1"
        response_cv = client.get(
            url, headers={"Accept": "text/html,application/xhtml+xml,application/xml"}
        )

    assert response_cv.status_code == 200
    response_data = response_cv.data.decode()
    assert str(lit_record["control_number"]) in response_data
    assert response_cv.content_type == expected_cv_type


def test_literature_get_modified_authors_after_create(inspire_app):
    data = {
        "authors": [
            {
                "full_name": "Brian Gross",
                "ids": [
                    {"schema": "INSPIRE ID", "value": "INSPIRE-00304313"},
                    {"schema": "INSPIRE BAI", "value": "J.M.Maldacena.1"},
                ],
                "emails": ["test@test.com"],
            }
        ]
    }
    data = faker.record("lit", with_control_number=True, data=data)
    record = LiteratureRecord.create(data)

    assert len(list(record.get_modified_authors())) == 1


def test_literature_get_modified_authors_after_uuid_update(inspire_app):
    data = {
        "authors": [
            {
                "full_name": "Brian Gross",
                "ids": [
                    {"schema": "INSPIRE ID", "value": "INSPIRE-00304313"},
                    {"schema": "INSPIRE BAI", "value": "J.M.Maldacena.1"},
                ],
                "emails": ["test@test.com"],
            },
            {
                "full_name": "Donald Matthews",
                "ids": [{"schema": "INSPIRE BAI", "value": "H.Khalfoun.1"}],
                "emails": ["test1@test.pl", "test1.1@test.pl"],
            },
        ]
    }
    data = faker.record("lit", with_control_number=True, data=data)

    record = LiteratureRecord.create(data)

    data.update(
        {
            "authors": [
                {
                    "full_name": "Brian Gross",
                    "ids": [{"schema": "INSPIRE BAI", "value": "B.Gross.1"}],
                    "emails": ["test@test.com"],
                    "uuid": "ec485f53-0d75-403a-a11c-e2a6d45dd328",
                },
                {
                    "full_name": "Donald Matthews",
                    "ids": [{"schema": "INSPIRE BAI", "value": "D.Matthews.1"}],
                    "emails": ["test1@test.pl", "test1.1@test.pl"],
                    "uuid": "ec485f53-0d75-403a-a11c-e2a6d45dd327",
                },
            ]
        }
    )

    record.update(data)
    assert len(list(record.get_modified_authors())) == 2


def test_literature_get_modified_authors_after_metadata_update(inspire_app):
    data = {
        "authors": [
            {
                "full_name": "Brian Gross",
                "ids": [
                    {"schema": "INSPIRE ID", "value": "INSPIRE-00304313"},
                    {"schema": "INSPIRE BAI", "value": "J.M.Maldacena.1"},
                ],
                "emails": ["test@test.com"],
            }
        ]
    }
    data = faker.record("lit", with_control_number=True, data=data)
    record = LiteratureRecord.create(data)

    author = record.get("authors")[0]
    author["emails"] = ["test@test.com", "test2@test.com"]
    record.update(dict(record))

    assert len(list(record.get_modified_authors())) == 1


@pytest.mark.vcr
def test_import_article_with_unknown_type_should_import_as_article(inspire_app):
    doi = "10.31234/osf.io/4ms5a"
    record = import_article(doi)

    assert record["document_type"] == ["article"]


@pytest.mark.vcr
def test_index_fulltext_document_s3(inspire_app, s3):
    metadata = {"foo": "bar"}
    create_s3_bucket(KEY)
    create_s3_file(
        current_s3_instance.get_bucket_for_file_key(KEY),
        KEY,
        "this is my data",
        metadata,
    )
    doi = "10.31234/osf.io/4ms5a"
    record = import_article(doi)
    data = {
        "documents": [
            {
                "fulltext": True,
                "hidden": False,
                "key": KEY,
                "filename": "2105.15193.pdf",
                "url": "https://arxiv.org/pdf/2105.15193.pdf",
            }
        ]
    }
    record_data = faker.record("lit", with_control_number=True, data=data)
    record = LiteratureRecord.create(record_data)
    serialized_data = record.serialize_for_es_with_fulltext()
    assert "text" in serialized_data["documents"][0]


@pytest.mark.vcr
def test_index_fulltext_with_not_existing_doc_handle_exception(
    inspire_app, s3, override_config
):
    metadata = {"foo": "bar"}
    key_for_non_existing_doc = "12323123"
    create_s3_bucket(KEY)
    create_s3_bucket(key_for_non_existing_doc)
    create_s3_file(
        current_s3_instance.get_bucket_for_file_key(KEY),
        KEY,
        "this is my data",
        metadata,
    )
    doi = "10.31234/osf.io/4ms5a"
    record = import_article(doi)
    data = {
        "documents": [
            {
                "fulltext": True,
                "hidden": False,
                "key": KEY,
                "filename": "2105.15193.pdf",
                "url": "https://arxiv.org/pdf/2105.15193.pdf",
            }
        ]
    }
    record_data = faker.record("lit", with_control_number=True, data=data)
    record = LiteratureRecord.create(record_data)
    with override_config(FEATURE_FLAG_ENABLE_FILES=False):
        record["documents"].append(
            {
                "source": "arxiv",
                "fulltext": True,
                "key": key_for_non_existing_doc,
                "filename": "2105.15198.pdf",
                "url": "http://www.africau.edu/images/default/sample.pdf",
            }
        )
        record.update(dict(record))
        serialized_data = record.serialize_for_es_with_fulltext()
        assert "text" in serialized_data["documents"][0]
        assert "text" not in serialized_data["documents"][1]


@pytest.mark.vcr
def test_get_documents_for_fulltext_works_for_arxiv(inspire_app, s3):
    metadata = {"foo": "bar"}
    create_s3_bucket(KEY)
    create_s3_file(
        current_s3_instance.get_bucket_for_file_key(KEY),
        KEY,
        "this is my data",
        metadata,
    )
    doi = "10.31234/osf.io/4ms5a"
    record = import_article(doi)
    data = {
        "documents": [
            {
                "source": "arxiv",
                "fulltext": True,
                "key": KEY,
                "filename": "2105.15193.pdf",
                "url": "https://arxiv.org/pdf/2105.15193.pdf",
            }
        ]
    }
    record_data = faker.record("lit", with_control_number=True, data=data)
    record = LiteratureRecord.create(record_data)
    serialized_data = record.serialize_for_es_with_fulltext()
    assert "text" in serialized_data["documents"][0]


@pytest.mark.vcr
def test_add_record_with_scanned_documents(inspire_app, s3):
    expected_document_key = "8d2fc6d280b1385302910fd5162eaad2"
    create_s3_bucket(expected_document_key)
    data = {
        "documents": [
            {
                "source": "arxiv",
                "key": "scansmpl.pdf",
                "url": "http://solutions.weblite.ca/pdfocrx/scansmpl.pdf",
                "original_url": "http://original-url.com/2",
                "filename": "fermilab.pdf",
            }
        ]
    }
    record = create_record("lit", data=data)
    expected_documents = [
        {
            "source": "arxiv",
            "key": expected_document_key,
            "url": current_s3_instance.get_public_url(expected_document_key),
            "original_url": "http://original-url.com/2",
            "filename": "fermilab.pdf",
            "fulltext": False,
        }
    ]
    assert record["documents"] == expected_documents


@pytest.mark.vcr
@mock.patch("inspirehep.records.api.literature.is_document_scanned")
def test_add_record_with_fulltext_documents_ommit_scanned_check(
    mock_is_scanned, inspire_app, s3
):
    expected_document_key = "8d2fc6d280b1385302910fd5162eaad2"
    create_s3_bucket(expected_document_key)
    data = {
        "documents": [
            {
                "source": "arxiv",
                "key": "scansmpl.pdf",
                "url": "http://solutions.weblite.ca/pdfocrx/scansmpl.pdf",
                "original_url": "http://original-url.com/2",
                "filename": "fermilab.pdf",
                "fulltext": True,
            }
        ]
    }
    create_record("lit", data=data)

    assert not mock_is_scanned.called
