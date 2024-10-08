#
# Copyright (C) 2019 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

import orjson
from helpers.utils import create_record, create_user
from inspirehep.accounts.roles import Roles
from invenio_accounts.testutils import login_user_via_session
from marshmallow import utils


def test_conferences_json_without_login(inspire_app, datadir):
    headers = {"Accept": "application/json"}

    data = orjson.loads((datadir / "1185692.json").read_text())

    record = create_record("con", data=data)
    record_control_number = record["control_number"]

    expected_metadata = {
        "$schema": "https://labs.inspirehep.net/schemas/records/conferences.json",
        "addresses": [{"cities": ["Kyoto"], "country": "Japan", "country_code": "JP"}],
        "closing_date": "2012-05-25",
        "cnum": "C12-05-21.5",
        "contact_details": [{"email": "fs4loc@konan-u.ac.jp"}],
        "control_number": record_control_number,
        "deleted": False,
        "inspire_categories": [{"term": "Astrophysics"}],
        "legacy_creation_date": "2012-09-17",
        "legacy_version": "20161101104659.0",
        "opening_date": "2012-05-21",
        "self": {
            "$ref": f"http://localhost:5000/api/conferences/{record_control_number}"
        },
        "series": [{"name": "First Stars", "number": 4}],
        "titles": [
            {"subtitle": "From Hayashi to the Future", "title": "First Stars IV"}
        ],
        "urls": [
            {
                "description": "web page",
                "value": "http://tpweb2.phys.konan-u.ac.jp/~FirstStar4/",
            }
        ],
        "number_of_contributions": 0,
    }
    expected_created = utils.isoformat(record.created)
    expected_updated = utils.isoformat(record.updated)
    with inspire_app.test_client() as client:
        response = client.get(f"/conferences/{record_control_number}", headers=headers)

    response_data = orjson.loads(response.data)
    response_data_metadata = response_data["metadata"]
    response_created = response_data["created"]
    response_updated = response_data["updated"]

    assert expected_metadata == response_data_metadata
    assert expected_created == response_created
    assert expected_updated == response_updated


def test_conferences_json_with_logged_in_cataloger(inspire_app):
    user = create_user(role=Roles.cataloger.value)

    headers = {"Accept": "application/json"}

    data = {
        "$schema": "https://inspire/schemas/records/conferences.json",
        "_collections": ["Conferences"],
        "_private_notes": [{"value": "A private note"}],
        "titles": [{"title": "Great conference for HEP"}],
    }

    record = create_record("con", data=data)
    record_control_number = record["control_number"]

    expected_metadata = {
        "$schema": "https://inspire/schemas/records/conferences.json",
        "_collections": ["Conferences"],
        "_private_notes": [{"value": "A private note"}],
        "control_number": record_control_number,
        "titles": [{"title": "Great conference for HEP"}],
        "number_of_contributions": 0,
        "self": {
            "$ref": f"http://localhost:5000/api/conferences/{record_control_number}"
        },
    }
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.get(f"/conferences/{record_control_number}", headers=headers)

    response_data = orjson.loads(response.data)
    response_data_metadata = response_data["metadata"]

    assert expected_metadata == response_data_metadata


def test_conferences_detail(inspire_app, datadir):
    headers = {"Accept": "application/vnd+inspire.record.ui+json"}

    data = orjson.loads((datadir / "1185692.json").read_text())

    record = create_record("con", data=data)
    record_control_number = record["control_number"]

    expected_metadata = {
        "$schema": "https://labs.inspirehep.net/schemas/records/conferences.json",
        "addresses": [{"cities": ["Kyoto"], "country": "Japan", "country_code": "JP"}],
        "closing_date": "2012-05-25",
        "cnum": "C12-05-21.5",
        "contact_details": [{"email": "fs4loc@konan-u.ac.jp"}],
        "control_number": record_control_number,
        "deleted": False,
        "inspire_categories": [{"term": "Astrophysics"}],
        "legacy_creation_date": "2012-09-17",
        "legacy_version": "20161101104659.0",
        "opening_date": "2012-05-21",
        "self": {
            "$ref": f"http://localhost:5000/api/conferences/{record_control_number}"
        },
        "series": [{"name": "First Stars", "number": 4}],
        "titles": [
            {"subtitle": "From Hayashi to the Future", "title": "First Stars IV"}
        ],
        "urls": [
            {
                "description": "web page",
                "value": "http://tpweb2.phys.konan-u.ac.jp/~FirstStar4/",
            }
        ],
        "number_of_contributions": 0,
    }
    expected_created = utils.isoformat(record.created)
    expected_updated = utils.isoformat(record.updated)
    with inspire_app.test_client() as client:
        response = client.get(f"/conferences/{record_control_number}", headers=headers)

    response_data = orjson.loads(response.data)
    response_data_metadata = response_data["metadata"]
    response_created = response_data["created"]
    response_updated = response_data["updated"]

    assert expected_metadata == response_data_metadata
    assert expected_created == response_created
    assert expected_updated == response_updated


def test_conferences_search_json(inspire_app, datadir):
    headers = {"Accept": "application/vnd+inspire.record.ui+json"}

    data = orjson.loads((datadir / "1185692.json").read_text())

    record = create_record("con", data=data)
    record_control_number = record["control_number"]

    expected_result = {
        "addresses": [{"cities": ["Kyoto"], "country_code": "JP", "country": "Japan"}],
        "number_of_contributions": 0,
        "$schema": "https://labs.inspirehep.net/schemas/records/conferences.json",
        "closing_date": "2012-05-25",
        "cnum": "C12-05-21.5",
        "control_number": record_control_number,
        "deleted": False,
        "inspire_categories": [{"term": "Astrophysics"}],
        "legacy_creation_date": "2012-09-17",
        "legacy_version": "20161101104659.0",
        "opening_date": "2012-05-21",
        "self": {
            "$ref": f"http://localhost:5000/api/conferences/{record_control_number}"
        },
        "series": [{"name": "First Stars", "number": 4}],
        "titles": [
            {"subtitle": "From Hayashi to the Future", "title": "First Stars IV"}
        ],
        "urls": [
            {
                "description": "web page",
                "value": "http://tpweb2.phys.konan-u.ac.jp/~FirstStar4/",
            }
        ],
    }

    expected_created = utils.isoformat(record.created)
    expected_updated = utils.isoformat(record.updated)
    with inspire_app.test_client() as client:
        response = client.get("/conferences", headers=headers)

    response_data_hit = orjson.loads(response.data)["hits"]["hits"][0]

    response_created = response_data_hit["created"]
    response_updated = response_data_hit["updated"]
    response_metadata = response_data_hit["metadata"]

    assert expected_result == response_metadata
    assert expected_created == response_created
    assert expected_updated == response_updated


def test_proceedings_in_detail_page(inspire_app):
    headers = {"Accept": "application/vnd+inspire.record.ui+json"}

    conference = create_record("con")
    conference_control_number = conference["control_number"]
    ref = f"http://localhost:8000/api/conferences/{conference_control_number}"

    rec_data = {
        "publication_info": [{"conference_record": {"$ref": ref}}],
        "document_type": ["proceedings"],
    }
    proceeding = create_record("lit", rec_data)

    rec_data = {
        "publication_info": [{"conference_record": {"$ref": ref}}],
        "document_type": ["conference paper"],
    }
    create_record("lit", rec_data)

    expected_metadata = {
        "number_of_contributions": 1,
        "$schema": "http://localhost:5000/schemas/records/conferences.json",
        "control_number": conference["control_number"],
        "titles": conference["titles"],
        "proceedings": [{"control_number": proceeding["control_number"]}],
        "self": {
            "$ref": f"http://localhost:5000/api/conferences/{conference_control_number}"
        },
    }
    with inspire_app.test_client() as client:
        response = client.get(
            f"/conferences/{conference_control_number}", headers=headers
        )
    response_metadata = response.json["metadata"]
    assert expected_metadata == response_metadata


def test_conferences_detail_links(inspire_app):
    expected_status_code = 200
    record = create_record("con")
    expected_links = {
        "json": (
            f"http://localhost:5000/conferences/{record['control_number']}?format=json"
        )
    }
    with inspire_app.test_client() as client:
        response = client.get(f"/conferences/{record['control_number']}")
    assert response.status_code == expected_status_code
    assert response.json["links"] == expected_links


def test_conferences_detail_json_format(inspire_app):
    expected_status_code = 200
    record = create_record("con")
    expected_content_type = "application/json"
    with inspire_app.test_client() as client:
        response = client.get(f"/conferences/{record['control_number']}?format=json")
    assert response.status_code == expected_status_code
    assert response.content_type == expected_content_type


def test_conferences_json_search_doesnt_return_emails(inspire_app, datadir):
    headers = {"Accept": "application/vnd+inspire.record.ui+json"}

    data = {"contact_details": [{"name": "Test Name", "email": "test@test.com"}]}

    create_record("con", data=data)

    with inspire_app.test_client() as client:
        response = client.get("/conferences", headers=headers)

    response_data_hit = orjson.loads(response.data)["hits"]["hits"][0]
    response_metadata = response_data_hit["metadata"]

    assert "email" not in response_metadata["contact_details"][0]
