#
# Copyright (C) 2019 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

import mock
from helpers.providers.faker import faker
from inspire_schemas.api import load_schema, validate
from inspirehep.records.marshmallow.literature.bibtex import BibTexCommonSchema


def test_get_authors_with_role_author():
    record = {
        "document_type": ["article"],
        "authors": [
            {"full_name": "Kiritsis, Elias", "inspire_roles": ["editor"]},
            {"full_name": "Nitti, Francesco", "inspire_roles": ["author"]},
            {"full_name": "Pimenta, Leandro Silva"},
        ],
    }
    expected = ["Nitti, Francesco", "Pimenta, Leandro Silva"]
    schema = BibTexCommonSchema()
    result = schema.dump(record).data

    assert expected == result["authors_with_role_author"]


def test_get_authors_with_role_encodes_names_properly():
    record = {
        "document_type": ["article"],
        "authors": [{"full_name": "Pimenta, L.S."}, {"full_name": "Smith, John, Jr."}],
    }
    expected = ["Pimenta, L. S.", "Smith, Jr., John"]
    schema = BibTexCommonSchema()
    result = schema.dump(record).data

    assert expected == result["authors_with_role_author"]


def test_get_authors_with_role_editor():
    record = {
        "document_type": ["article"],
        "authors": [
            {"full_name": "Kiritsis, Elias", "inspire_roles": ["editor"]},
            {"full_name": "Nitti, Francesco", "inspire_roles": ["author"]},
        ],
    }
    expected = ["Kiritsis, Elias"]
    schema = BibTexCommonSchema()
    result = schema.dump(record).data

    assert expected == result["authors_with_role_editor"]


def test_get_collaboration():
    record = {
        "document_type": ["article"],
        "collaborations": [{"value": "CMS"}, {"value": "ATLAS"}],
    }
    expected_collaboration = "CMS, ATLAS"
    schema = BibTexCommonSchema()
    result = schema.dump(record).data

    result_collaboration = result["collaboration"]
    assert expected_collaboration == result_collaboration


def test_no_collaboration():
    record = {"document_type": ["article"]}
    expected_collaboration = ""
    schema = BibTexCommonSchema()
    result = schema.dump(record).data

    result_collaboration = result["collaboration"]
    assert expected_collaboration == result_collaboration


def test_bibtex_document_type_misc():
    record = {"document_type": ["misc"]}
    expected = "misc"
    result = BibTexCommonSchema.get_bibtex_document_type(record)
    assert expected == result


def test_bibtex_document_type():
    record = {"document_type": ["thesis"], "thesis_info": {"degree_type": "master"}}
    expected = "mastersthesis"
    result = BibTexCommonSchema.get_bibtex_document_type(record)
    assert expected == result


def test_bibtex_document_type_recognizes_phd_theses():
    schema = load_schema("hep")
    document_type_schema = schema["properties"]["document_type"]
    thesis_info_schema = schema["properties"]["thesis_info"]

    record = {"document_type": ["thesis"], "thesis_info": {"degree_type": "phd"}}
    assert validate(record["document_type"], document_type_schema) is None
    assert validate(record["thesis_info"], thesis_info_schema) is None

    expected = "phdthesis"
    result = BibTexCommonSchema.get_bibtex_document_type(record)

    assert expected == result


def test_bibtex_document_type_recognizes_thesis_as_article():
    record = {
        "document_type": ["thesis"],
        "thesis_info": {"degree_type": "phd"},
        "publication_info": {"journal_title": "JHEP"},
    }
    expected = "article"
    result = BibTexCommonSchema.get_bibtex_document_type(record)
    assert expected == result


def test_bibtex_document_type_reckognize_book_chapter_as_article():
    record = {
        "document_type": ["book chapter"],
        "publication_info": {"journal_title": "JHEP"},
    }
    expected = "article"
    result = BibTexCommonSchema.get_bibtex_document_type(record)
    assert expected == result


def test_bibtex_document_type_handles_missing_thesis_info():
    schema = load_schema("hep")
    subschema = schema["properties"]["document_type"]

    record = {"document_type": ["thesis"]}
    assert validate(record["document_type"], subschema) is None

    expected = "mastersthesis"
    result = BibTexCommonSchema.get_bibtex_document_type(record)

    assert expected == result


def test_bibtex_document_type_prefers_article():
    record = {
        "thesis_info": {"degree_type": "master"},
        "document_type": ["thesis", "article"],
    }
    expected = "article"
    result = BibTexCommonSchema.get_bibtex_document_type(record)
    assert expected == result


def test_get_journal():
    record = {
        "document_type": ["article"],
        "publication_info": [
            {
                "journal_title": "Rhys.Rev.",
                "journal_volume": "12",
                "artid": "1",
                "page_start": "10",
            }
        ],
    }
    expected_journal = "Rhys. Rev."
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_journal = result["journal"]

    assert expected_journal == result_journal


def test_get_volume():
    record = {
        "document_type": ["article"],
        "publication_info": [
            {
                "journal_title": "Rhys.Rev.",
                "journal_volume": "12",
                "artid": "1",
                "page_start": "10",
            }
        ],
    }
    expected_volume = "12"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_volume = result["volume"]

    assert expected_volume == result_volume


def test_get_report_number():
    test_data = {
        "document_type": ["article"],
        "report_numbers": [
            {"value": "CERN-SOME-REPORT"},
            {"value": "CERN-SOME-OTHER-REPORT"},
            {"value": "CERN-HIDDEN", "hidden": True},
        ],
    }
    expected_report_numbers = "CERN-SOME-REPORT, CERN-SOME-OTHER-REPORT"
    schema = BibTexCommonSchema()

    result = schema.dump(test_data).data
    result_report_numbers = result["reportNumber"]

    assert expected_report_numbers == result_report_numbers


def test_get_type():
    test_data = {
        "document_type": ["thesis"],
        "thesis_info": {"degree_type": "bachelor"},
    }
    expected_type = "Bachelor thesis"
    schema = BibTexCommonSchema()

    result = schema.dump(test_data).data
    result_type = result["type"]
    assert expected_type == result_type


def test_get_type_handles_missing_thesis_info():
    schema = load_schema("hep")
    subschema = schema["properties"]["document_type"]

    record = {"document_type": ["thesis"]}
    assert validate(record["document_type"], subschema) is None

    expected_type = "Other thesis"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_type = result["type"]

    assert expected_type == result_type


def test_get_author():
    record = {"document_type": ["article"], "corporate_author": ["Corp A", "Corp B"]}
    expected_author = "{Corp A} and {Corp B}"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_author = result["author"]
    assert expected_author == result_author


def test_note_on_erratum():
    record = {
        "document_type": ["article"],
        "publication_info": [
            {
                "journal_title": "J.Testing",
                "journal_volume": "A",
                "page_start": "12",
                "page_end": "15",
                "year": 2016,
                "material": "erratum",
            },
            {
                "journal_title": "A Title",
                "journal_volume": "B",
                "artid": "987",
                "material": "addendum",
            },
        ],
    }
    expected_note = "[Erratum: J.Testing A, 12--15 (2016), Addendum: A Title B, 987]"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_note = result["note"]
    assert expected_note == result_note


def test_isbn():
    record = {"document_type": ["book"], "isbns": [{"value": "9781108705011"}]}

    expected_isbn = "978-1-108-70501-1"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_isbn = result["isbn"]
    assert expected_isbn == result_isbn


def test_eprint():
    arxiv_value = faker.arxiv()
    record = {"document_type": ["article"], "arxiv_eprints": [{"value": arxiv_value}]}

    expected_eprint = arxiv_value
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_eprint = result["eprint"]
    assert expected_eprint == result_eprint


def test_archive_prefix():
    arxiv_value = faker.arxiv()
    record = {"document_type": ["article"], "arxiv_eprints": [{"value": arxiv_value}]}

    expected_archive_prefix = "arXiv"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_archivePrefix = result["archivePrefix"]
    assert expected_archive_prefix == result_archivePrefix


def test_archive_prefix_empty():
    record = {"document_type": ["article"]}

    expected_archive_prefix = None
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_archivePrefix = result["archivePrefix"]
    assert expected_archive_prefix == result_archivePrefix


def test_get_number():
    record = {
        "document_type": ["article"],
        "publication_info": [
            {
                "journal_title": "Rhys.Rev.",
                "journal_volume": "12",
                "artid": "1",
                "page_start": "10",
                "journal_issue": "12",
            }
        ],
    }
    expected_number = "12"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_number = result["number"]

    assert expected_number == result_number


def test_get_editions():
    record = {"document_type": ["article"], "editions": ["first"]}
    expected_edition = "first"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_edition = result["edition"]

    assert expected_edition == result_edition


def test_get_number_with_different_publication_info_material():
    record = {
        "document_type": ["article"],
        "publication_info": [{"material": "foo", "journal_issue": "12"}],
    }
    expected_number = None
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_number = result["number"]

    assert expected_number == result_number


def test_get_page():
    record = {
        "document_type": ["article"],
        "publication_info": [
            {
                "journal_title": "Rhys.Rev.",
                "journal_volume": "12",
                "artid": "1",
                "page_start": "10",
            }
        ],
    }
    expected_pages = "1"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_pages = result["pages"]

    assert expected_pages == result_pages


def test_get_page_without_journal_title_volume():
    record = {
        "document_type": ["book chapter"],
        "publication_info": [
            {
                "artid": "67567",
                "page_start": "123",
                "parent_record": {
                    "ref": "http://labs.inspirehep.net/api/literature/1642228"
                },
            }
        ],
    }
    expected_pages = "67567"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_pages = result["pages"]

    assert expected_pages == result_pages


def test_get_page_range_without_journal_title_volume():
    record = {
        "document_type": ["book chapter"],
        "publication_info": [
            {
                "page_start": "123",
                "page_end": "151",
                "parent_record": {
                    "ref": "http://labs.inspirehep.net/api/literature/1642228"
                },
            }
        ],
    }
    expected_pages = "123--151"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_pages = result["pages"]

    assert expected_pages == result_pages


@mock.patch(
    "inspirehep.records.marshmallow.literature.bibtex.get_parent_record",
    return_value={"titles": [{"title": "Parent title"}]},
)
def test_get_book_title_with_parent_record(mock_get_linked_records):
    record = {
        "titles": [{"title": "This is the main title"}],
        "document_type": ["book"],
    }
    expected_book_title = "{Parent title}"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_book_title = result["booktitle"]

    assert expected_book_title == result_book_title


@mock.patch(
    "inspirehep.records.marshmallow.literature.bibtex.get_parent_record",
    return_value={},
)
def test_get_book_title_without_parent_record(mock_get_linked_records):
    record = {
        "titles": [{"title": "This is the main title"}],
        "document_type": ["book"],
    }
    expected_book_title = None
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_book_title = result["booktitle"]

    assert expected_book_title == result_book_title


def test_get_series():
    record = {
        "document_type": ["book"],
        "book_series": [{"title": "This is a book title"}],
    }
    expected_series = "This is a book title"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_series = result["series"]

    assert expected_series == result_series


def test_get_publisher():
    record = {"document_type": ["book"], "imprints": [{"publisher": "Elsevier"}]}
    expected_publisher = "Elsevier"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_publisher = result["publisher"]

    assert expected_publisher == result_publisher


def test_get_school():
    record = {
        "document_type": ["thesis"],
        "thesis_info": {"institutions": [{"name": "NTUA"}, {"name": "MIT"}]},
    }
    expected_school = "NTUA, MIT"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_school = result["school"]

    assert expected_school == result_school


def test_get_school_empty():
    record = {"document_type": ["thesis"]}
    expected_school = None
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_school = result["school"]

    assert expected_school == result_school


def test_get_address():
    record = {
        "document_type": ["book"],
        "addresses": [{"cities": ["Tokyo"], "country_code": "JP"}],
    }
    expected_address = "Tokyo, jp"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_address = result["address"]

    assert expected_address == result_address


def test_get_address_with_imprint_place():
    record = {"document_type": ["book"], "imprints": [{"place": "This is a place"}]}
    expected_address = "This is a place"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_address = result["address"]

    assert expected_address == result_address


def test_get_title():
    record = {"document_type": ["article"], "titles": [{"title": "This is a title"}]}
    expected_title = "{This is a title}"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_title = result["title"]

    assert expected_title == result_title


def test_get_title_with_subtitle():
    record = {
        "document_type": ["article"],
        "titles": [{"title": "This is a title", "subtitle": "with a subtitle"}],
    }
    expected_title = "{This is a title}: {with a subtitle}"
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_title = result["title"]

    assert expected_title == result_title


def test_bibtex_document_type_conference_paper_with_journal_title():
    record = {
        "document_type": ["conference paper"],
        "publication_info": [
            {"pubinfo_freetext": "Geneva, Switzerland: CERN (2002) 401 p"},
            {
                "pubinfo_freetext": "Geneva, Switzerland: CERN (2002) 401 p",
                "journal_title": "Nucl.Part.Phys.Proc.",
            },
        ],
    }
    expected = "article"
    result = BibTexCommonSchema.get_bibtex_document_type(record)
    assert expected == result


def test_bibtex_document_type_conference_paper():
    record = {"document_type": ["conference paper"]}
    expected = "inproceedings"
    result = BibTexCommonSchema.get_bibtex_document_type(record)
    assert expected == result


@mock.patch(
    "inspirehep.records.marshmallow.literature.bibtex.get_parent_record",
    create=True,
    return_value={
        "document_type": ["book"],
        "authors": [{"full_name": "Kiritsis, Elias", "inspire_roles": ["editor"]}],
    },
)
def test_get_editor_from_book_parent_record(mock_get_linked_records_from_dict_field):
    record = {"document_type": ["book chapter"]}
    expected_editors = ["Kiritsis, Elias"]
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_editors = result["authors_with_role_editor"]

    assert expected_editors == result_editors


@mock.patch(
    "inspirehep.records.marshmallow.literature.bibtex.get_parent_record",
    create=True,
    return_value={
        "document_type": ["proceedings"],
        "authors": [{"full_name": "Kiritsis, Elias", "inspire_roles": ["editor"]}],
    },
)
def test_get_editor_from_proceedings_parent_record(
    mock_get_linked_records_from_dict_field,
):
    record = {"document_type": ["conference paper"]}
    expected_editors = ["Kiritsis, Elias"]
    schema = BibTexCommonSchema()

    result = schema.dump(record).data
    result_editors = result["authors_with_role_editor"]

    assert expected_editors == result_editors


def test_get_best_publication_info():
    record = {
        "document_type": ["conference paper"],
        "publication_info": [
            {
                "year": 2021,
                "artid": "0001",
                "material": "publication",
                "journal_title": "title-2021",
                "journal_volume": "1",
                "page_start": "1",
            },
            {
                "year": 2019,
                "artid": "0002",
                "material": "publication",
                "journal_title": "title-2019",
                "journal_volume": "2",
                "page_start": "1",
            },
            {
                "year": 2020,
                "artid": "0003",
                "material": "publication",
                "journal_title": "title-2020",
                "journal_volume": "3",
                "page_start": "1",
            },
            {
                "year": 2018,
                "material": "publication",
                "journal_title": "title-2018",
                "journal_volume": "2",
            },
            {
                "artid": "0004",
                "material": "publication",
                "journal_title": "title-2020",
                "journal_volume": "3",
                "page_start": "1",
            },
        ],
    }
    expected = {
        "year": 2019,
        "artid": "0002",
        "material": "publication",
        "journal_title": "title-2019",
        "journal_volume": "2",
        "page_start": "1",
    }
    result = BibTexCommonSchema.get_best_publication_info(record)
    assert expected == result
