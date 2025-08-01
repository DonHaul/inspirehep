#
# Copyright (C) 2019 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE module that adds more fun to the platform."""

import copy
from copy import deepcopy

import mock
import pytest
from helpers.providers.faker import faker
from helpers.utils import create_record
from inspirehep.records.api.authors import AuthorsRecord
from inspirehep.records.api.journals import JournalsRecord
from inspirehep.records.api.literature import LiteratureRecord
from inspirehep.records.models import (
    DataLiterature,
    ExperimentLiterature,
    InstitutionLiterature,
    JournalLiterature,
    RecordsAuthors,
    StudentsAdvisors,
)


@pytest.fixture
def journal_data():
    journal_data = {
        "_collections": ["Journals"],
        "journal_title": {"title": "Test"},
        "$schema": "https://inspirehep.net/schemas/records/journals.json",
        "short_title": "Test",
    }
    return journal_data


def test_records_links_correctly_with_conference(inspire_app):
    conference = create_record("con")
    conference_control_number = conference["control_number"]
    ref = f"http://localhost:8000/api/conferences/{conference_control_number}"
    conf_paper_data = {
        "publication_info": [{"conference_record": {"$ref": ref}}],
        "document_type": ["conference paper"],
    }

    proceedings_data = {
        "publication_info": [{"conference_record": {"$ref": ref}}],
        "document_type": ["proceedings"],
    }

    rec_without_correct_type_data = {
        "publication_info": [{"conference_record": {"$ref": ref}}]
    }
    conf_paper_record = create_record("lit", conf_paper_data)
    proceedings_record = create_record("lit", proceedings_data)
    rec_without_correct_type = create_record("lit", rec_without_correct_type_data)

    documents = conference.model.conference_documents
    conf_docs_uuids = [document.literature_uuid for document in documents]
    assert len(documents) == 2
    assert proceedings_record.id in conf_docs_uuids
    assert conf_paper_record.id in conf_docs_uuids
    assert rec_without_correct_type.id not in conf_docs_uuids


def test_creating_lit_record_with_linked_institutions_populates_institution_relation_table(
    inspire_app,
):
    author_institution = create_record("ins")
    author_institution_ref = (
        f"http://localhost:8000/api/institutions/{author_institution['control_number']}"
    )

    thesis_institution = create_record("ins")
    thesis_institution_ref = (
        f"http://localhost:8000/api/institutions/{thesis_institution['control_number']}"
    )

    record_aff_institution = create_record("ins")
    record_aff_institution_ref = f"http://localhost:8000/api/institutions/{record_aff_institution['control_number']}"

    rec_data = {
        "authors": [
            {
                "full_name": "John Doe",
                "affiliations": [
                    {"value": "Institution", "record": {"$ref": author_institution_ref}}
                ],
            }
        ],
        "thesis_info": {"institutions": [{"record": {"$ref": thesis_institution_ref}}]},
        "record_affiliations": [
            {"record": {"$ref": record_aff_institution_ref}, "value": "Institution"}
        ],
    }

    rec = create_record("lit", rec_data)
    assert InstitutionLiterature.query.filter_by(literature_uuid=rec.id).count() == 3


def test_creating_lit_record_with_institution_linked_more_than_once(inspire_app):
    institution = create_record("ins")
    institution_ref = (
        f"http://localhost:8000/api/institutions/{institution['control_number']}"
    )

    rec_data = {
        "thesis_info": {"institutions": [{"record": {"$ref": institution_ref}}]},
        "record_affiliations": [
            {"record": {"$ref": institution_ref}, "value": "Institution"}
        ],
    }

    rec = create_record("lit", rec_data)
    assert InstitutionLiterature.query.filter_by(literature_uuid=rec.id).count() == 1


def test_updating_record_updates_institution_relations(inspire_app):
    institution_1 = create_record("ins")
    institution_1_control_number = institution_1["control_number"]
    ref_1 = f"http://localhost:8000/api/institutions/{institution_1_control_number}"

    institution_2 = create_record("ins")
    institution_2_control_number = institution_2["control_number"]
    ref_2 = f"http://localhost:8000/api/institutions/{institution_2_control_number}"
    rec_data = {
        "authors": [
            {
                "full_name": "John Doe",
                "affiliations": [{"value": "Institution", "record": {"$ref": ref_1}}],
            }
        ]
    }

    rec = create_record("lit", rec_data)

    rec_data = deepcopy(dict(rec))
    rec_data.update(
        {
            "authors": [{"full_name": "John Doe"}],
            "record_affiliations": [
                {"record": {"$ref": ref_2}, "value": "Institution"}
            ],
        }
    )
    rec.update(rec_data)

    institution_1_papers = institution_1.model.institution_papers
    institution_2_papers = institution_2.model.institution_papers
    lit_record_institutions = rec.model.institutions

    assert len(institution_1_papers) == 0
    assert len(institution_2_papers) == 1
    assert len(lit_record_institutions) == 1
    assert lit_record_institutions[0].institution_uuid == institution_2.id


def test_record_with_institutions_adds_only_linked_ones_in_institution_lit_table(
    inspire_app,
):
    ref = "http://localhost:8000/api/institutions/1234"
    rec_data = {
        "authors": [
            {
                "full_name": "John Doe",
                "affiliations": [{"value": "Institution", "record": {"$ref": ref}}],
            }
        ]
    }
    rec = create_record("lit", rec_data)

    assert len(rec.model.institutions) == 0


def test_record_with_institutions_doesnt_add_deleted_institutions_in_institution_lit_table(
    inspire_app,
):
    institution = create_record("ins")
    institution_control_number = institution["control_number"]
    ref = f"http://localhost:8000/api/institutions/{institution_control_number}"
    institution.delete()
    rec_data = {
        "authors": [
            {
                "full_name": "John Doe",
                "affiliations": [{"value": "Institution", "record": {"$ref": ref}}],
            }
        ]
    }

    rec = create_record("lit", rec_data)
    assert len(rec.model.institutions) == 0


def test_deleted_record_deletes_relations_in_institution_literature_table(inspire_app):
    institution = create_record("ins")
    institution_control_number = institution["control_number"]
    ref = f"http://localhost:8000/api/institutions/{institution_control_number}"

    rec_data = {
        "authors": [
            {
                "full_name": "John Doe",
                "affiliations": [{"value": "Institution", "record": {"$ref": ref}}],
            }
        ]
    }

    rec = create_record("lit", rec_data)
    assert InstitutionLiterature.query.filter_by(literature_uuid=rec.id).count() == 1
    rec.delete()

    assert InstitutionLiterature.query.filter_by(literature_uuid=rec.id).count() == 0


def test_hard_delete_record_deletes_relations_in_institution_literature_table(
    inspire_app,
):
    institution = create_record("ins")
    institution_control_number = institution["control_number"]
    ref = f"http://localhost:8000/api/institutions/{institution_control_number}"

    rec_data = {
        "authors": [
            {
                "full_name": "John Doe",
                "affiliations": [{"value": "Institution", "record": {"$ref": ref}}],
            }
        ]
    }

    rec = create_record("lit", rec_data)
    assert InstitutionLiterature.query.filter_by(literature_uuid=rec.id).count() == 1
    rec.hard_delete()

    assert InstitutionLiterature.query.filter_by(literature_uuid=rec.id).count() == 0


@mock.patch.object(LiteratureRecord, "update_institution_relations")
def test_institution_literature_table_is_not_updated_when_feature_flag_is_disabled(
    update_function_mock, inspire_app
):
    institution = create_record("ins")
    institution_control_number = institution["control_number"]
    ref = f"http://localhost:8000/api/institutions/{institution_control_number}"

    data = {
        "authors": [
            {
                "full_name": "John Doe",
                "affiliations": [{"value": "Institution", "record": {"$ref": ref}}],
            }
        ]
    }
    record_data = faker.record("lit", data)
    LiteratureRecord.create(record_data, disable_relations_update=True)
    update_function_mock.assert_not_called()

    LiteratureRecord.create(record_data, disable_relations_update=False)
    update_function_mock.assert_called()


def test_record_links_when_correct_type_is_not_first_document_type_conference(
    inspire_app,
):
    conference = create_record("con")
    conference_control_number = conference["control_number"]
    ref = f"http://localhost:8000/api/conferences/{conference_control_number}"
    conf_paper_data = {
        "publication_info": [{"conference_record": {"$ref": ref}}],
        "document_type": ["article", "conference paper"],
    }

    proceedings_data = {
        "publication_info": [{"conference_record": {"$ref": ref}}],
        "document_type": ["book", "proceedings", "thesis"],
    }

    rec_without_correct_type_data = {
        "publication_info": [{"conference_record": {"$ref": ref}}],
        "document_type": ["book", "thesis", "article"],
    }
    conf_paper_record = create_record("lit", conf_paper_data)
    proceedings_record = create_record("lit", proceedings_data)
    rec_without_correct_type = create_record("lit", rec_without_correct_type_data)

    documents = conference.model.conference_documents
    conf_docs_uuids = [document.literature_uuid for document in documents]
    assert len(documents) == 2
    assert proceedings_record.id in conf_docs_uuids
    assert conf_paper_record.id in conf_docs_uuids
    assert rec_without_correct_type.id not in conf_docs_uuids


def test_record_updates_correctly_conference_link(inspire_app):
    conference_1 = create_record("con")
    conference_1_control_number = conference_1["control_number"]
    ref_1 = f"http://localhost:8000/api/conferences/{conference_1_control_number}"

    conference_2 = create_record("con")
    conference_2_control_number = conference_2["control_number"]
    ref_2 = f"http://localhost:8000/api/conferences/{conference_2_control_number}"
    rec_data = {
        "publication_info": [{"conference_record": {"$ref": ref_1}}],
        "document_type": ["conference paper"],
    }

    rec = create_record("lit", rec_data)

    rec_data = deepcopy(dict(rec))
    rec_data["publication_info"][0]["conference_record"]["$ref"] = ref_2
    rec.update(rec_data)

    documents_from_conference_1 = conference_1.model.conference_documents
    documents_from_conference_2 = conference_2.model.conference_documents
    conferences_from_record = rec.model.conferences

    assert len(documents_from_conference_1) == 0
    assert len(documents_from_conference_2) == 1
    assert len(conferences_from_record) == 1
    assert conferences_from_record[0].conference_uuid == conference_2.id


def test_record_links_only_existing_conference(inspire_app):
    rec_data = {
        "publication_info": [
            {
                "conference_record": {
                    "$ref": "http://localhost:8000/api/conferences/9999"
                }
            }
        ],
        "document_type": ["conference paper"],
    }
    rec = create_record("lit", rec_data)

    assert len(rec.model.conferences) == 0


def test_conference_paper_doesnt_link_deleted_conference(inspire_app):
    conference = create_record("con")
    conference_control_number = conference["control_number"]
    ref = f"http://localhost:8000/api/conferences/{conference_control_number}"

    conference.delete()

    rec_data = {
        "publication_info": [{"conference_record": {"$ref": ref}}],
        "document_type": ["conference paper"],
    }
    rec = create_record("lit", rec_data)

    assert len(rec.model.conferences) == 0


def test_delete_literature_clears_entries_in_conference_literature_table(inspire_app):
    conference = create_record("con")
    conference_control_number = conference["control_number"]
    ref = f"http://localhost:8000/api/conferences/{conference_control_number}"

    rec_data = {
        "publication_info": [{"conference_record": {"$ref": ref}}],
        "document_type": ["conference paper"],
    }
    rec = create_record("lit", rec_data)

    rec.delete()

    assert len(conference.model.conference_documents) == 0


def test_hard_delete_literature_clears_entries_in_conference_literature_table(
    inspire_app,
):
    conference = create_record("con")
    conference_control_number = conference["control_number"]
    ref = f"http://localhost:8000/api/conferences/{conference_control_number}"

    rec_data = {
        "publication_info": [{"conference_record": {"$ref": ref}}],
        "document_type": ["conference paper"],
    }
    rec = create_record("lit", rec_data)

    rec.hard_delete()

    assert len(conference.model.conference_documents) == 0


@mock.patch.object(LiteratureRecord, "update_conference_paper_and_proccedings")
def test_disable_conference_update_feature_flag_disabled(
    update_function_mock, inspire_app
):
    conference = create_record("con")
    conference_control_number = conference["control_number"]
    ref = f"http://localhost:8000/api/conferences/{conference_control_number}"

    conference.delete()

    data = {
        "publication_info": [{"conference_record": {"$ref": ref}}],
        "document_type": ["conference paper"],
    }

    record_data = faker.record("lit", data)

    LiteratureRecord.create(record_data, disable_relations_update=True)
    update_function_mock.assert_not_called()

    LiteratureRecord.create(record_data, disable_relations_update=False)
    update_function_mock.assert_called()


def test_self_citations_in_detail_view_not_logged_user(inspire_app):
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
    create_record(
        "lit",
        data=data_authors_3,
        literature_citations=[rec1["control_number"], rec2["control_number"]],
    )

    expected_citations = 2
    expected_non_self_citations = 1

    headers = {"Accept": "application/vnd+inspire.record.ui+json"}
    with inspire_app.test_client() as client:
        response = client.get(f"/literature/{rec1['control_number']}", headers=headers)

    assert response.status_code == 200
    assert response.json["metadata"]["citation_count"] == expected_citations
    assert (
        response.json["metadata"]["citation_count_without_self_citations"]
        == expected_non_self_citations
    )


def test_creating_lit_record_with_linked_experiment_populates_experiment_relation_table(
    inspire_app,
):
    experiment = create_record("exp")
    experiment_control_number = experiment["control_number"]
    exp_ref = f"http://localhost:8000/api/experiments/{experiment_control_number}"

    data = {
        "accelerator_experiments": [
            {"legacy_name": "LIGO", "record": {"$ref": exp_ref}}
        ]
    }
    rec = create_record("lit", data)
    assert ExperimentLiterature.query.filter_by(literature_uuid=rec.id).count() == 1


def test_updating_record_updates_experiment_relations(inspire_app):
    experiment = create_record("exp")
    experiment_control_number = experiment["control_number"]
    exp_ref_1 = f"http://localhost:8000/api/experiments/{experiment_control_number}"

    experiment_2 = create_record("exp")
    experiment_control_number_2 = experiment_2["control_number"]
    exp_ref_2 = f"http://localhost:8000/api/experiments/{experiment_control_number_2}"
    data = {
        "accelerator_experiments": [
            {"legacy_name": "LIGO", "record": {"$ref": exp_ref_1}}
        ]
    }
    rec = create_record("lit", data)

    rec_data = deepcopy(dict(rec))
    rec_data.update(
        {
            "accelerator_experiments": [
                {"legacy_name": "LIGO", "record": {"$ref": exp_ref_2}}
            ]
        }
    )
    rec.update(rec_data)

    experiment_papers = experiment.model.experiment_papers
    experiment_2_papers = experiment_2.model.experiment_papers
    lit_record_experiments = rec.model.experiments

    assert len(experiment_papers) == 0
    assert len(experiment_2_papers) == 1
    assert len(lit_record_experiments) == 1
    assert lit_record_experiments[0].experiment_uuid == experiment_2.id


def test_record_with_experiment_adds_only_linked_ones_in_experiment_lit_table(
    inspire_app,
):
    ref = "http://localhost:8000/api/experiments/1234"
    rec_data = {
        "accelerator_experiments": [{"legacy_name": "LIGO", "record": {"$ref": ref}}]
    }
    rec = create_record("lit", rec_data)

    assert len(rec.model.experiments) == 0


def test_record_with_experiment_doesnt_add_deleted_experiment_in_experiment_lit_table(
    inspire_app,
):
    experiment = create_record("exp")
    experiment_control_number = experiment["control_number"]
    ref = f"http://localhost:8000/api/experiments/{experiment_control_number}"
    experiment.delete()
    rec_data = {
        "accelerator_experiments": [{"legacy_name": "LIGO", "record": {"$ref": ref}}]
    }
    rec = create_record("lit", rec_data)
    assert len(rec.model.experiments) == 0


def test_deleted_record_deletes_relations_in_experiment_literature_table(inspire_app):
    experiment = create_record("exp")
    experiment_control_number = experiment["control_number"]
    ref = f"http://localhost:8000/api/experiments/{experiment_control_number}"

    rec_data = {
        "accelerator_experiments": [{"legacy_name": "LIGO", "record": {"$ref": ref}}]
    }

    rec = create_record("lit", rec_data)
    assert ExperimentLiterature.query.filter_by(literature_uuid=rec.id).count() == 1
    rec.delete()

    assert ExperimentLiterature.query.filter_by(literature_uuid=rec.id).count() == 0


def test_hard_delete_record_deletes_relations_in_experiment_literature_table(
    inspire_app,
):
    experiment = create_record("exp")
    experiment_control_number = experiment["control_number"]
    ref = f"http://localhost:8000/api/experiments/{experiment_control_number}"

    rec_data = {
        "accelerator_experiments": [{"legacy_name": "LIGO", "record": {"$ref": ref}}]
    }

    rec = create_record("lit", rec_data)
    assert ExperimentLiterature.query.filter_by(literature_uuid=rec.id).count() == 1
    rec.hard_delete()

    assert ExperimentLiterature.query.filter_by(literature_uuid=rec.id).count() == 0


@mock.patch.object(LiteratureRecord, "update_experiment_relations")
def test_experiment_literature_table_is_not_updated_when_feature_flag_is_disabled(
    update_function_mock, inspire_app
):
    institution = create_record("exp")
    institution_control_number = institution["control_number"]
    ref = f"http://localhost:8000/api/experiments/{institution_control_number}"

    data = {
        "accelerator_experiments": [{"legacy_name": "LIGO", "record": {"$ref": ref}}]
    }
    record_data = faker.record("lit", data, with_control_number=False)
    LiteratureRecord.create(record_data, disable_relations_update=True)
    update_function_mock.assert_not_called()

    LiteratureRecord.create(record_data, disable_relations_update=False)
    update_function_mock.assert_called()


def test_redirected_records_are_not_counted_into_citations(inspire_app):
    record_1 = create_record("lit")  # Cited record

    record_redirected = create_record(
        "lit", literature_citations=[record_1["control_number"]]
    )  # This one cites and then will be redirected
    record_2 = create_record(
        "lit",
        literature_citations=[record_1["control_number"]],
        data={"deleted_records": [record_redirected["self"]]},
    )  # This one redirects and also cites

    record_redirected_2 = create_record(
        "lit", literature_citations=[record_1["control_number"]]
    )  # This one cites and will be redirected
    create_record(
        "lit", data={"deleted_records": [record_redirected_2["self"]]}
    )  # This one redirects but not cites.

    # At the end we should have record_1 cited by record_2 only.

    record_1_from_db = LiteratureRecord.get_record_by_pid_value(
        record_1["control_number"]
    )
    assert record_1_from_db.citation_count == 1
    assert record_1_from_db.model.citations[0].citer_id == record_2.id


@pytest.mark.xfail(reason="For now this won't be supported.")
def test_citation_of_redirected_record_is_counted_correctly(inspire_app):
    record_redirected = create_record("lit")  # Cited record

    record_1 = create_record(
        "lit", literature_citations=[record_redirected["control_number"]]
    )  # This one cites

    record_2 = create_record(
        "lit", data={"deleted_records": [record_redirected["self"]]}
    )  # This one redirects cited record to itself

    # At the end we should have record_2 cited by record_1 (indirectly as record_1  was citing redirected record)

    record_2_from_db = LiteratureRecord.get_record_by_pid_value(
        record_2["control_number"]
    )
    assert record_2_from_db.citation_count == 1
    assert record_2_from_db.model.citations[0].citer_id == record_1.id


def test_create_author_with_advisors_updates_students_advisors_table(inspire_app):
    advisor = create_record("aut")
    advisor_2 = create_record("aut")
    student = create_record(
        "aut",
        data={
            "advisors": [
                {
                    "name": advisor["name"]["value"],
                    "record": advisor["self"],
                    "degree_type": "phd",
                },
                {
                    "name": advisor_2["name"]["value"],
                    "record": advisor_2["self"],
                    "degree_type": "other",
                },
            ]
        },
    )

    all_advisors = StudentsAdvisors.query.filter_by(student_id=student.id).all()
    assert len(all_advisors) == 2
    assert all_advisors[0].advisor_id == advisor.id
    assert all_advisors[0].degree_type == "phd"

    assert all_advisors[1].advisor_id == advisor_2.id
    assert all_advisors[1].degree_type == "other"


def test_create_author_with_same_advisor_for_multiple_degrees_updates_students_advisors_table(
    inspire_app,
):
    advisor = create_record("aut")
    student = create_record(
        "aut",
        data={
            "advisors": [
                {
                    "name": advisor["name"]["value"],
                    "record": advisor["self"],
                    "degree_type": "master",
                },
                {
                    "name": advisor["name"]["value"],
                    "record": advisor["self"],
                    "degree_type": "phd",
                },
            ]
        },
    )

    all_advisors = StudentsAdvisors.query.filter_by(student_id=student.id).all()
    assert len(all_advisors) == 2
    assert all_advisors[0].advisor_id == advisor.id
    assert all_advisors[0].degree_type == "master"

    assert all_advisors[1].advisor_id == advisor.id
    assert all_advisors[1].degree_type == "phd"


def test_update_author_with_advisors_updates_students_advisors_table(inspire_app):
    advisor = create_record("aut")
    advisor_2 = create_record("aut")
    student = create_record(
        "aut",
        data={
            "advisors": [
                {
                    "name": advisor["name"]["value"],
                    "record": advisor["self"],
                    "degree_type": "phd",
                }
            ]
        },
    )

    all_advisors = StudentsAdvisors.query.filter_by(student_id=student.id).all()
    assert len(all_advisors) == 1
    assert all_advisors[0].advisor_id == advisor.id
    assert all_advisors[0].degree_type == "phd"

    student["advisors"].append(
        {
            "name": advisor_2["name"]["value"],
            "record": advisor_2["self"],
            "degree_type": "other",
        }
    )
    student.update(dict(student))

    all_advisors = StudentsAdvisors.query.filter_by(student_id=student.id).all()
    assert len(all_advisors) == 2
    assert all_advisors[1].advisor_id == advisor_2.id
    assert all_advisors[1].degree_type == "other"


def test_delete_advisor_doesnt_clear_entries_in_students_advisors_table(inspire_app):
    advisor = create_record("aut")
    student = create_record(
        "aut",
        data={
            "advisors": [
                {
                    "name": advisor["name"]["value"],
                    "record": advisor["self"],
                    "degree_type": "phd",
                }
            ]
        },
    )

    assert StudentsAdvisors.query.filter_by(student_id=student.id).count() == 1

    advisor.delete()

    assert StudentsAdvisors.query.filter_by(student_id=student.id).count() == 1


def test_delete_student_clears_entries_in_students_advisors_table(inspire_app):
    advisor = create_record("aut")
    student = create_record(
        "aut",
        data={
            "advisors": [
                {
                    "name": advisor["name"]["value"],
                    "record": advisor["self"],
                    "degree_type": "phd",
                }
            ]
        },
    )

    assert StudentsAdvisors.query.filter_by(student_id=student.id).count() == 1

    student.delete()

    assert StudentsAdvisors.query.filter_by(student_id=student.id).count() == 0


def test_hard_delete_student_clears_entries_in_students_advisors_table(
    inspire_app,
):
    advisor = create_record("aut")
    student = create_record(
        "aut",
        data={
            "advisors": [
                {
                    "name": advisor["name"]["value"],
                    "record": advisor["self"],
                    "degree_type": "phd",
                }
            ]
        },
    )

    assert StudentsAdvisors.query.filter_by(student_id=student.id).count() == 1

    student.hard_delete()

    assert StudentsAdvisors.query.filter_by(student_id=student.id).count() == 0


def test_hard_delete_advisor_clears_entries_in_students_advisors_table(
    inspire_app,
):
    advisor = create_record("aut")
    student = create_record(
        "aut",
        data={
            "advisors": [
                {
                    "name": advisor["name"]["value"],
                    "record": advisor["self"],
                    "degree_type": "phd",
                }
            ]
        },
    )

    assert StudentsAdvisors.query.filter_by(student_id=student.id).count() == 1

    advisor.hard_delete()

    assert StudentsAdvisors.query.filter_by(student_id=student.id).count() == 0


def test_journal_literature_table_is_populated_when_lit_record_added(inspire_app):
    journal_rec = create_record("jou")
    rec = create_record(
        "lit", data={"publication_info": [{"journal_record": journal_rec["self"]}]}
    )
    assert JournalLiterature.query.filter_by(literature_uuid=rec.id).count() == 1


def test_journal_literature_table_is_populated_when_multiple_lit_records_added(
    inspire_app, journal_data
):
    journal_rec = JournalsRecord(data=journal_data).create(journal_data)
    journal_data_2 = copy.deepcopy(journal_data)
    journal_data_2["journal_title"] = {"title": "Another Test"}
    journal_rec_2 = JournalsRecord(data=journal_data_2).create(journal_data_2)
    data = {
        "_collections": ["Literature"],
        "document_type": ["article"],
        "$schema": "https://inspirehep.net/schemas/records/hep.json",
        "titles": [{"title": "A test"}],
        "publication_info": [{"journal_record": journal_rec["self"]}],
    }
    data_2 = {
        "_collections": ["Literature"],
        "document_type": ["article"],
        "$schema": "https://inspirehep.net/schemas/records/hep.json",
        "titles": [{"title": "A test 2"}],
        "publication_info": [{"journal_record": journal_rec_2["self"]}],
    }
    rec = LiteratureRecord(data=data).create(data)
    rec_2 = LiteratureRecord(data=data_2).create(data_2)
    assert JournalLiterature.query.count() == 2
    assert JournalLiterature.query.filter_by(literature_uuid=rec.id).count() == 1
    assert JournalLiterature.query.filter_by(literature_uuid=rec_2.id).count() == 1


def test_journal_literature_table_is_updated_when_literature_record_modified(
    inspire_app, journal_data
):
    journal_rec = JournalsRecord(data=journal_data).create(journal_data)
    data = {
        "_collections": ["Literature"],
        "document_type": ["article"],
        "$schema": "https://inspirehep.net/schemas/records/hep.json",
        "titles": [{"title": "A test"}],
    }
    rec = LiteratureRecord(data=data).create(data)
    assert JournalLiterature.query.filter_by(literature_uuid=rec.id).count() == 0
    rec["publication_info"] = [{"journal_record": journal_rec["self"]}]
    rec.update(dict(rec))
    assert JournalLiterature.query.filter_by(literature_uuid=rec.id).count() == 1


def test_journal_literature_table_is_updated_when_journal_record_ref_deleted_from_literature(
    inspire_app, journal_data
):
    journal_rec = JournalsRecord(data=journal_data).create(journal_data)
    data = {
        "_collections": ["Literature"],
        "document_type": ["article"],
        "$schema": "https://inspirehep.net/schemas/records/hep.json",
        "titles": [{"title": "A test"}],
        "publication_info": [{"journal_record": journal_rec["self"]}],
    }
    rec = LiteratureRecord(data=data).create(data)
    assert JournalLiterature.query.filter_by(literature_uuid=rec.id).count() == 1
    del rec["publication_info"]
    rec.update(dict(rec))
    assert JournalLiterature.query.filter_by(literature_uuid=rec.id).count() == 0


def test_journal_literature_is_cleaned_after_deleting_lit_record(
    inspire_app, journal_data
):
    journal_rec = JournalsRecord(data=journal_data).create(journal_data)
    data = {
        "_collections": ["Literature"],
        "document_type": ["article"],
        "$schema": "https://inspirehep.net/schemas/records/hep.json",
        "titles": [{"title": "A test"}],
        "publication_info": [{"journal_record": journal_rec["self"]}],
    }
    rec = LiteratureRecord(data=data).create(data)
    assert JournalLiterature.query.filter_by(literature_uuid=rec.id).count() == 1
    rec.delete()
    assert JournalLiterature.query.filter_by(journal_uuid=journal_rec.id).count() == 0


def test_journal_literature_is_cleaned_after_hard_delete_lit_record(
    inspire_app, journal_data
):
    journal_rec = JournalsRecord(data=journal_data).create(journal_data)
    data = {
        "_collections": ["Literature"],
        "document_type": ["article"],
        "$schema": "https://inspirehep.net/schemas/records/hep.json",
        "titles": [{"title": "A test"}],
        "publication_info": [{"journal_record": journal_rec["self"]}],
    }
    rec = LiteratureRecord(data=data).create(data)
    assert JournalLiterature.query.filter_by(literature_uuid=rec.id).count() == 1
    rec.hard_delete()
    assert JournalLiterature.query.filter_by(journal_uuid=journal_rec.id).count() == 0


def test_new_enum_value_in_records_literature_is_populated(inspire_app):
    author_data = faker.record(
        "aut",
        data={
            "ids": [
                {"value": "H.Kuipers.1", "schema": "INSPIRE BAI"},
                {"value": "HEPNAMES-221945", "schema": "SPIRES"},
            ]
        },
    )
    author = AuthorsRecord(data=author_data).create(data=author_data)
    data = faker.record(
        "lit",
        {
            "authors": [
                {
                    "record": author["self"],
                    "full_name": author["name"]["value"],
                    "ids": author["ids"],
                }
            ]
        },
    )
    LiteratureRecord(data=data).create(data=data)
    results = RecordsAuthors.query.all()
    assert len(results) == 1
    assert results[0].id_type == "recid"
    assert results[0].author_id == str(author["control_number"])


def test_creating_data_record_with_linked_literature_populates_relation_table(
    inspire_app,
):
    record_literature = create_record("lit")
    control_number_literature = record_literature["control_number"]

    data = {
        "literature": [
            {
                "record": {
                    "$ref": f"http://localhost:8000/api/literature/{control_number_literature}"
                }
            }
        ]
    }
    record_data = create_record("dat", data)
    assert DataLiterature.query.filter_by(data_uuid=record_data.id).count() == 1


def test_data_updating_record_updates_literature_relation_table(inspire_app):
    record_literature = create_record("lit")
    control_number_literature = record_literature["control_number"]

    record_literature_2 = create_record("lit")
    control_number_literature_2 = record_literature_2["control_number"]

    data = {
        "literature": [
            {
                "record": {
                    "$ref": f"http://localhost:8000/api/literature/{control_number_literature}"
                }
            }
        ]
    }
    record_data = create_record("dat", data)
    assert DataLiterature.query.filter_by(data_uuid=record_data.id).count() == 1

    record_data["literature"].append(
        {
            "record": {
                "$ref": f"http://localhost:8000/api/literature/{control_number_literature_2}"
            }
        }
    )

    record_data.update(dict(record_data))
    assert DataLiterature.query.filter_by(data_uuid=record_data.id).count() == 2


def test_data_literature_relation_cleanup_after_delete(
    inspire_app,
):
    record_literature = create_record("lit")
    control_number_literature = record_literature["control_number"]

    data = {
        "literature": [
            {
                "record": {
                    "$ref": f"http://localhost:8000/api/literature/{control_number_literature}"
                }
            }
        ]
    }
    record_data = create_record("dat", data)
    assert DataLiterature.query.filter_by(data_uuid=record_data.id).count() == 1

    record_data.hard_delete()
    assert DataLiterature.query.filter_by(data_uuid=record_data.id).count() == 0
