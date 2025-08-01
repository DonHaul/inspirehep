#
# Copyright (C) 2019 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

from copy import deepcopy
from datetime import datetime, timedelta

import orjson
import pytest
import requests_mock
from flask import current_app, url_for
from freezegun import freeze_time
from helpers.utils import (
    create_record,
    create_record_factory,
    create_user,
    create_user_and_token,
)
from inspire_utils.query import ordered
from inspire_utils.record import get_value
from inspirehep.accounts.roles import Roles
from inspirehep.records.api import (
    AuthorsRecord,
    ExperimentsRecord,
    InstitutionsRecord,
    JobsRecord,
    JournalsRecord,
    SeminarsRecord,
)
from inspirehep.records.api.conferences import ConferencesRecord
from invenio_accounts.testutils import login_user_via_session
from mock import patch

FRANK_CASTLE_ORCID = "0000-0002-6152-062X"


def test_author_submit_requires_authentication(inspire_app):
    with inspire_app.test_client() as client:
        response = client.post(
            "/submissions/authors",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "given_name": "John",
                        "display_name": "John Doe",
                        "status": "active",
                    }
                }
            ),
        )
    assert response.status_code == 401


def test_author_update_requires_authentication(inspire_app):
    with inspire_app.test_client() as client:
        response = client.put(
            "/submissions/authors/123",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "given_name": "John",
                        "display_name": "John Doe",
                        "status": "active",
                    }
                }
            ),
        )
    assert response.status_code == 401


def test_author_get_requires_authentication(inspire_app):
    with inspire_app.test_client() as client:
        response = client.get(
            "/submissions/authors/123", content_type="application/json"
        )
    assert response.status_code == 401


@freeze_time("2019-06-17")
def test_new_author_submit(inspire_app, requests_mock):
    data = {
        "given_name": "John",
        "display_name": "John Doe",
        "status": "active",
    }
    requests_mock.post(
        f"{current_app.config['INSPIRE_BACKOFFICE_URL']}/api/workflows/authors/",
        json={"data": data, "workflow_type": "AUTHOR_CREATE"},
    )
    user_and_token = create_user_and_token()
    headers = {"Authorization": "BEARER " + user_and_token.access_token}
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user_and_token.user.email)
        response = client.post(
            "/submissions/authors",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
            headers=headers,
        )

    assert response.status_code == 200
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    post_data = history.json()
    assert "Authorization" in history.headers
    assert (
        f"Token {current_app.config['AUTHENTICATION_TOKEN']}"
        == history.headers["Authorization"]
    )
    assert (
        history.url
        == f"{current_app.config['INSPIRE_BACKOFFICE_URL']}/api/workflows/authors/"
    )
    expected_data = {
        "data": {
            "_collections": ["Authors"],
            "acquisition_source": {
                "email": user_and_token.user.email,
                "method": "submitter",
                "source": "submitter",
                "internal_uid": user_and_token.user.id,
                "datetime": "2019-06-17T00:00:00",
            },
            "name": {"value": "John", "preferred_name": "John Doe"},
            "status": "active",
        },
        "workflow_type": "AUTHOR_CREATE",
    }
    assert expected_data == post_data


def test_new_author_submit_with_workflows_error(inspire_app, requests_mock):
    requests_mock.post(
        f"{current_app.config['INSPIRE_BACKOFFICE_URL']}/api/workflows/authors/",
        status_code=500,
    )
    token = create_user_and_token()
    headers = {"Authorization": "BEARER " + token.access_token}
    with inspire_app.test_client() as client:
        response = client.post(
            "/submissions/authors",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "given_name": "John",
                        "display_name": "John Doe",
                        "status": "active",
                    }
                }
            ),
            headers=headers,
        )
    assert response.status_code == 503


def test_new_author_submit_with_conflict_error(
    inspire_app,
    requests_mock,
):
    requests_mock.post(
        f"{current_app.config['INSPIRE_BACKOFFICE_URL']}/api/workflows/authors/",
        status_code=409,
        json={"error": "Author already exists"},
    )

    token = create_user_and_token()
    headers = {"Authorization": "BEARER " + token.access_token}
    with inspire_app.test_client() as client:
        response = client.post(
            "/submissions/authors",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "given_name": "John",
                        "display_name": "John Doe",
                        "status": "active",
                    }
                }
            ),
            headers=headers,
        )
    assert response.status_code == 409


def test_new_author_submit_works_with_session_login(inspire_app, requests_mock):
    requests_mock.post(
        f"{current_app.config['INSPIRE_BACKOFFICE_URL']}/api/workflows/authors/",
        json={"id": "1e309a22-07d6-46e3-8814-1e0d796f7b42"},
    )
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/authors",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "given_name": "John",
                        "display_name": "John Doe",
                        "status": "active",
                    }
                }
            ),
        )
    assert response.status_code == 200


def test_get_author_update_data_fails_if_user_does_not_own_author_profile(inspire_app):
    user = create_user()

    rec = create_record_factory("aut")

    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.get(
            f"/submissions/authors/{rec.data['control_number']}",
            headers={"Accept": "application/json"},
        )

    assert response.status_code == 403


def test_get_author_update_data_of_same_author(inspire_app):
    orcid = "0000-0001-5109-3700"
    user = create_user(orcid=orcid)

    author_data = {
        "name": {"value": "John", "preferred_name": "John Doe"},
        "ids": [{"schema": "ORCID", "value": orcid}],
        "email_addresses": [
            {"value": "public@john.ch"},
            {"value": "private@john.ch", "hidden": True},
        ],
        "status": "active",
    }
    rec = create_record_factory("aut", data=author_data)

    expected_data = {
        "data": {
            "given_name": "John",
            "display_name": "John Doe",
            "status": "active",
            "orcid": orcid,
            "emails": [
                {"value": "public@john.ch"},
                {"value": "private@john.ch", "hidden": True},
            ],
        }
    }

    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.get(
            f"/submissions/authors/{rec.data['control_number']}",
            headers={"Accept": "application/json"},
        )
    response_data = orjson.loads(response.data)

    assert response_data == expected_data


def test_get_author_update_data_not_found(inspire_app):
    user = create_user()

    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.get(
            "/submissions/authors/1993", headers={"Accept": "application/json"}
        )

    assert response.status_code == 404


def test_get_author_update_data_requires_auth(inspire_app):
    with inspire_app.test_client() as client:
        response = client.get(
            "/submissions/authors/1993", headers={"Accept": "application/json"}
        )

    assert response.status_code == 401


@freeze_time("2019-06-17")
def test_update_author(inspire_app):
    orcid = "0000-0001-5109-3700"
    user = create_user(orcid=orcid)
    author_data = {
        "name": {"value": "John"},
        "ids": [
            {"schema": "ORCID", "value": orcid},
            {"value": "M.T.Hansen.1", "schema": "INSPIRE BAI"},
            {"value": "HEPNAMES-1114565", "schema": "SPIRES"},
            {"value": "http://linkedin.com", "schema": "LINKEDIN"},
        ],
        "status": "active",
        "urls": [{"value": "https://wrong-url"}],
        "_private_notes": [{"value": "A private note"}],
    }
    rec = create_record("aut", data=author_data)

    with inspire_app.test_client() as client, requests_mock.Mocker() as request_mock:
        login_user_via_session(client, email=user.email)
        request_mock.post(
            f"{current_app.config['INSPIRE_BACKOFFICE_URL']}/api/workflows/authors/",
            json={},
            status_code=200,
        )
        response = client.put(
            f"/submissions/authors/{rec['control_number']}",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "given_name": "John, Updated",
                        "display_name": "Updated",
                        "orcid": orcid,
                        "linkedin": "test",
                        "status": "active",
                        "comments": "A new private note",
                    }
                }
            ),
        )
    assert response.status_code == 200

    expected_data = {
        "_collections": ["Authors"],
        "self": {"$ref": f"http://localhost:5000/api/authors/{rec['control_number']}"},
        "$schema": "http://localhost:5000/schemas/records/authors.json",
        "control_number": rec["control_number"],
        "name": {"preferred_name": "Updated", "value": "John, Updated"},
        "status": "active",
        "ids": [
            {"schema": "ORCID", "value": orcid},
            {"schema": "INSPIRE BAI", "value": "M.T.Hansen.1"},
            {"schema": "SPIRES", "value": "HEPNAMES-1114565"},
            {"value": "test", "schema": "LINKEDIN"},
        ],
        "_private_notes": [
            {"value": "A private note"},
            {"value": "A new private note"},
        ],
    }

    updated_author = AuthorsRecord.get_record_by_pid_value(rec["control_number"])

    assert expected_data == updated_author


@freeze_time("2019-06-17")
def test_update_author_with_new_orcid(inspire_app):
    orcid = "0000-0001-5109-3700"
    user = create_user(orcid=orcid)
    author_data = {
        "name": {"value": "John"},
        "ids": [
            {"schema": "ORCID", "value": orcid},
            {"value": "HEPNAMES-1114565", "schema": "SPIRES"},
        ],
        "status": "active",
        "urls": [{"value": "https://wrong-url"}],
    }
    rec = create_record("aut", data=author_data)

    with inspire_app.test_client() as client, requests_mock.Mocker() as request_mock:
        login_user_via_session(client, email=user.email)

        request_mock.post(
            f"{current_app.config['INSPIRE_BACKOFFICE_URL']}/api/workflows/authors/",
            json={},
            status_code=200,
        )
        response = client.put(
            f"/submissions/authors/{rec['control_number']}",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "given_name": "John, Updated",
                        "display_name": "Updated",
                        "orcid": "0000-0001-8829-5461",
                        "status": "active",
                        "linkedin": "http://linkedin.com",
                        "bai": "M.T.Hansen.1",
                    }
                }
            ),
        )
    assert response.status_code == 200

    expected_data = {
        "_collections": ["Authors"],
        "self": {"$ref": f"http://localhost:5000/api/authors/{rec['control_number']}"},
        "$schema": "http://localhost:5000/schemas/records/authors.json",
        "control_number": rec["control_number"],
        "name": {"preferred_name": "Updated", "value": "John, Updated"},
        "status": "active",
        "ids": [
            {"schema": "ORCID", "value": "0000-0001-8829-5461"},
            {"schema": "INSPIRE BAI", "value": "M.T.Hansen.1"},
            {"schema": "ORCID", "value": orcid},
            {"schema": "SPIRES", "value": "HEPNAMES-1114565"},
            {"schema": "LINKEDIN", "value": "http://linkedin.com"},
        ],
    }
    updated_author = AuthorsRecord.get_record_by_pid_value(rec["control_number"])
    assert ordered(expected_data) == ordered(updated_author)


@freeze_time("2019-06-17")
def test_update_author_with_extra_data(inspire_app):
    orcid = "0000-0001-5109-3700"
    user = create_user(orcid=orcid)
    author_data = {
        "name": {"value": "John"},
        "ids": [{"schema": "ORCID", "value": orcid}],
        "status": "active",
        "urls": [{"value": "https://wrong-url"}],
    }
    rec = create_record("aut", data=author_data)

    with inspire_app.test_client() as client, requests_mock.Mocker() as request_mock:
        login_user_via_session(client, email=user.email)

        request_mock.post(
            f"{current_app.config['INSPIRE_BACKOFFICE_URL']}/api/workflows/authors/",
            json={},
            status_code=200,
        )
        response = client.put(
            f"/submissions/authors/{rec['control_number']}",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "given_name": "John, Updated",
                        "display_name": "Updated",
                        "linkedin": "http://linkedin.com",
                        "bai": "M.T.Hansen.1",
                    }
                }
            ),
        )
    assert response.status_code == 200

    expected_data = {
        "_collections": ["Authors"],
        "self": {"$ref": f"http://localhost:5000/api/authors/{rec['control_number']}"},
        "$schema": "http://localhost:5000/schemas/records/authors.json",
        "control_number": rec["control_number"],
        "name": {"preferred_name": "Updated", "value": "John, Updated"},
        "status": "active",
        "ids": [
            {"schema": "INSPIRE BAI", "value": "M.T.Hansen.1"},
            {"schema": "LINKEDIN", "value": "http://linkedin.com"},
            {"schema": "ORCID", "value": orcid},
        ],
    }
    updated_author = AuthorsRecord.get_record_by_pid_value(rec["control_number"])
    assert ordered(expected_data) == ordered(updated_author)


@freeze_time("2019-06-17")
def test_update_author_with_new_bai(inspire_app):
    orcid = "0000-0001-5109-3700"
    user = create_user(orcid=orcid)
    author_data = {
        "name": {"value": "John"},
        "ids": [
            {"schema": "ORCID", "value": orcid},
            {"value": "M.T.Hansen.2", "schema": "INSPIRE BAI"},
        ],
        "status": "active",
        "urls": [{"value": "https://wrong-url"}],
    }
    rec = create_record("aut", data=author_data)

    with inspire_app.test_client() as client, requests_mock.Mocker() as request_mock:
        login_user_via_session(client, email=user.email)
        request_mock.post(
            f"{current_app.config['INSPIRE_BACKOFFICE_URL']}/api/workflows/authors/",
            json={},
            status_code=200,
        )
        response = client.put(
            f"/submissions/authors/{rec['control_number']}",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "given_name": "John, Updated",
                        "display_name": "Updated",
                        "linkedin": "http://linkedin.com",
                        "orcid": orcid,
                        "bai": "M.T.Hansen.1",
                    }
                }
            ),
        )
    assert response.status_code == 200

    expected_data = {
        "_collections": ["Authors"],
        "self": {"$ref": f"http://localhost:5000/api/authors/{rec['control_number']}"},
        "$schema": "http://localhost:5000/schemas/records/authors.json",
        "control_number": rec["control_number"],
        "name": {"preferred_name": "Updated", "value": "John, Updated"},
        "status": "active",
        "ids": [
            {"schema": "ORCID", "value": orcid},
            {"schema": "INSPIRE BAI", "value": "M.T.Hansen.1"},
            {"schema": "LINKEDIN", "value": "http://linkedin.com"},
        ],
    }
    updated_author = AuthorsRecord.get_record_by_pid_value(rec["control_number"])
    assert expected_data == updated_author


@freeze_time("2019-06-17")
def test_update_author_creates_new_workflow(inspire_app, override_config):
    orcid = "0000-0001-5109-3700"
    user = create_user(orcid=orcid)
    author_data = {
        "name": {"value": "John"},
        "ids": [
            {"schema": "ORCID", "value": orcid},
            {"schema": "LINKEDIN", "value": "test_account"},
        ],
        "status": "active",
        "urls": [{"value": "https://wrong-url"}],
    }

    rec = create_record("aut", data=author_data)

    with inspire_app.test_client() as client, requests_mock.Mocker() as request_mock:
        login_user_via_session(client, email=user.email)

        expected_next_request = {
            "data": {
                "$schema": "http://localhost:5000/schemas/records/authors.json",
                "_collections": ["Authors"],
                "acquisition_source": {
                    "datetime": "2019-06-17T00:00:00",
                    "email": user.email,
                    "internal_uid": user.id,
                    "method": "submitter",
                    "orcid": "0000-0001-5109-3700",
                    "source": "submitter",
                },
                "control_number": rec["control_number"],
                "ids": [
                    {"schema": "ORCID", "value": "0000-0001-5109-3700"},
                    {"schema": "LINKEDIN", "value": "test_account"},
                    {"schema": "TWITTER", "value": "test_account"},
                ],
                "name": {"preferred_name": "Updated", "value": "John, Updated"},
                "self": {
                    "$ref": f"http://localhost:5000/api/authors/{rec['control_number']}"
                },
                "status": "active",
                "urls": [{"value": "http://test1.com"}, {"value": "http://test2.com"}],
            },
            "workflow_type": "AUTHOR_UPDATE",
        }

        request_mock.post(
            f"{current_app.config['INSPIRE_BACKOFFICE_URL']}/api/workflows/authors/",
            json={},
            status_code=200,
        )
        response = client.put(
            f"/submissions/authors/{rec['control_number']}",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "given_name": "John, Updated",
                        "display_name": "Updated",
                        "orcid": orcid,
                        "status": "active",
                        "linkedin": "test_account",
                        "twitter": "test_account",
                        "websites": ["http://test1.com", "http://test2.com"],
                    }
                }
            ),
        )
        assert request_mock.request_history[0].json() == expected_next_request
    assert response.status_code == 200


@freeze_time("2019-06-17")
def test_new_literature_submit_no_merge(inspire_app, requests_mock):
    requests_mock.post(
        f"{current_app.config['INSPIRE_NEXT_URL']}/workflows/literature",
        json={"workflow_object_id": 30},
    )
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/literature",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "arxiv_id": "1701.00006",
                        "arxiv_categories": ["hep-th"],
                        "preprint_date": "2019-10-15",
                        "document_type": "article",
                        "authors": [{"full_name": "Urhan, Harun"}],
                        "title": "Discovery of cool stuff",
                        "subjects": ["Other"],
                        "pdf_link": "https://cern.ch/coolstuff.pdf",
                        "references": "[1] Dude",
                        "additional_link": "https://cern.ch/other_stuff.pdf",
                    }
                }
            ),
        )
    assert response.status_code == 200
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    post_data = history.json()
    assert "Authorization" in history.headers
    assert (
        f"Bearer {current_app.config['AUTHENTICATION_TOKEN']}"
        == history.headers["Authorization"]
    )
    assert (
        history.url == f"{current_app.config['INSPIRE_NEXT_URL']}/workflows/literature"
    )
    expected_data = {
        "data": {
            "_collections": ["Literature"],
            "acquisition_source": {
                "email": user.email,
                "internal_uid": user.id,
                "method": "submitter",
                "source": "submitter",
                "datetime": "2019-06-17T00:00:00",
            },
            "preprint_date": "2019-10-15",
            "arxiv_eprints": [{"categories": ["hep-th"], "value": "1701.00006"}],
            "authors": [{"full_name": "Urhan, Harun"}],
            "citeable": True,
            "curated": False,
            "document_type": ["article"],
            "inspire_categories": [{"term": "Other"}],
            "titles": [{"source": "submitter", "title": "Discovery of cool stuff"}],
            "urls": [
                {"value": "https://cern.ch/coolstuff.pdf"},
                {"value": "https://cern.ch/other_stuff.pdf"},
            ],
        },
        "form_data": {"references": "[1] Dude", "url": "https://cern.ch/coolstuff.pdf"},
    }
    assert post_data == expected_data


@freeze_time("2019-06-17")
def test_new_literature_submit_arxiv_urls(inspire_app, requests_mock):
    requests_mock.post(
        f"{current_app.config['INSPIRE_NEXT_URL']}/workflows/literature",
        json={"workflow_object_id": 30},
    )
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/literature",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "arxiv_id": "1701.00006",
                        "arxiv_categories": ["hep-th"],
                        "preprint_date": "2019-10-15",
                        "document_type": "article",
                        "authors": [{"full_name": "Urhan, Harun"}],
                        "title": "Discovery of cool stuff",
                        "subjects": ["Other"],
                        "pdf_link": "https://arxiv.org/coolstuff.pdf",
                        "references": "[1] Dude",
                        "additional_link": "https://arxiv.org/other_stuff.pdf",
                    }
                }
            ),
        )
    assert response.status_code == 200
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    post_data = history.json()
    assert "Authorization" in history.headers
    assert (
        f"Bearer {current_app.config['AUTHENTICATION_TOKEN']}"
        == history.headers["Authorization"]
    )
    assert (
        history.url == f"{current_app.config['INSPIRE_NEXT_URL']}/workflows/literature"
    )
    expected_data = {
        "data": {
            "_collections": ["Literature"],
            "acquisition_source": {
                "email": user.email,
                "internal_uid": user.id,
                "method": "submitter",
                "source": "submitter",
                "datetime": "2019-06-17T00:00:00",
            },
            "preprint_date": "2019-10-15",
            "arxiv_eprints": [{"categories": ["hep-th"], "value": "1701.00006"}],
            "authors": [{"full_name": "Urhan, Harun"}],
            "citeable": True,
            "curated": False,
            "document_type": ["article"],
            "inspire_categories": [{"term": "Other"}],
            "titles": [{"source": "submitter", "title": "Discovery of cool stuff"}],
        },
        "form_data": {
            "references": "[1] Dude",
            "url": "https://arxiv.org/coolstuff.pdf",
        },
    }
    assert post_data == expected_data


def test_new_literature_submit_works_with_session_login(inspire_app, requests_mock):
    requests_mock.post(
        f"{current_app.config['INSPIRE_NEXT_URL']}/workflows/literature",
        json={"workflow_object_id": 30},
    )
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/literature",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "document_type": "article",
                        "authors": [{"full_name": "Urhan, Harun"}],
                        "title": "Discovery of cool stuff",
                        "subjects": ["Other"],
                    }
                }
            ),
        )
    assert response.status_code == 200


def test_new_literature_submit_requires_authentication(inspire_app):
    with inspire_app.test_client() as client:
        response = client.post(
            "/submissions/literature",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "document_type": "article",
                        "authors": [{"full_name": "Urhan, Harun"}],
                        "title": "Discovery of cool stuff",
                        "subjects": ["Other"],
                    }
                }
            ),
        )
    assert response.status_code == 401


def test_new_literature_submit_with_workflows_api_error(inspire_app, requests_mock):
    requests_mock.post(
        f"{current_app.config['INSPIRE_NEXT_URL']}/workflows/literature",
        status_code=500,
    )

    token = create_user_and_token()
    headers = {"Authorization": "BEARER " + token.access_token}
    with inspire_app.test_client() as client:
        response = client.post(
            "/submissions/literature",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "document_type": "article",
                        "authors": [{"full_name": "Urhan, Harun"}],
                        "title": "Discovery of cool stuff",
                        "subjects": ["Other"],
                    }
                }
            ),
            headers=headers,
        )
    assert response.status_code == 503


def test_new_literature_submit_with_private_notes(inspire_app, requests_mock):
    requests_mock.post(
        f"{current_app.config['INSPIRE_NEXT_URL']}/workflows/literature",
        json={"workflow_object_id": 30},
    )
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/literature",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "arxiv_id": "1701.00006",
                        "arxiv_categories": ["hep-th"],
                        "preprint_date": "2019-10-15",
                        "document_type": "article",
                        "authors": [{"full_name": "Urhan, Harun"}],
                        "title": "Discovery of cool stuff",
                        "subjects": ["Other"],
                        "pdf_link": "https://arxiv.org/coolstuff.pdf",
                        "references": "[1] Dude",
                        "additional_link": "https://arxiv.org/other_stuff.pdf",
                        "comments": "comment will be here",
                        "proceedings_info": "Proceeding info will be here",
                        "conference_info": "conference info in very important topic",
                    }
                }
            ),
        )
    assert response.status_code == 200

    history = requests_mock.request_history[0]
    post_data = history.json()
    assert "Authorization" in history.headers
    assert (
        f"Bearer {current_app.config['AUTHENTICATION_TOKEN']}"
        == history.headers["Authorization"]
    )
    assert (
        history.url == f"{current_app.config['INSPIRE_NEXT_URL']}/workflows/literature"
    )

    expected_data = [
        {"value": "comment will be here", "source": "submitter"},
        {"value": "Proceeding info will be here", "source": "submitter"},
        {"value": "conference info in very important topic", "source": "submitter"},
    ]

    assert post_data["data"]["_private_notes"] == expected_data


def test_new_literature_submit_with_private_notes_and_conference_record(
    inspire_app, requests_mock
):
    requests_mock.post(
        f"{current_app.config['INSPIRE_NEXT_URL']}/workflows/literature",
        json={"workflow_object_id": 30},
    )
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/literature",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "arxiv_id": "1701.00006",
                        "arxiv_categories": ["hep-th"],
                        "preprint_date": "2019-10-15",
                        "document_type": "article",
                        "authors": [{"full_name": "Urhan, Harun"}],
                        "title": "Discovery of cool stuff",
                        "subjects": ["Other"],
                        "pdf_link": "https://arxiv.org/coolstuff.pdf",
                        "references": "[1] Dude",
                        "additional_link": "https://arxiv.org/other_stuff.pdf",
                        "conference_record": "a conference record",
                        "comments": "comment will be here",
                        "proceedings_info": "Proceeding info will be here",
                        "conference_info": "conference info in very important topic",
                    }
                }
            ),
        )
    assert response.status_code == 200

    history = requests_mock.request_history[0]
    post_data = history.json()
    assert "Authorization" in history.headers
    assert (
        f"Bearer {current_app.config['AUTHENTICATION_TOKEN']}"
        == history.headers["Authorization"]
    )
    assert (
        history.url == f"{current_app.config['INSPIRE_NEXT_URL']}/workflows/literature"
    )

    expected_data = [
        {"value": "comment will be here", "source": "submitter"},
        {"value": "Proceeding info will be here", "source": "submitter"},
    ]

    assert post_data["data"]["_private_notes"] == expected_data


def test_new_literature_submit_with_conference_cnum(inspire_app, requests_mock):
    requests_mock.post(
        f"{current_app.config['INSPIRE_NEXT_URL']}/workflows/literature",
        json={"workflow_object_id": 30},
    )
    user = create_user()
    conference = create_record("con", data={"cnum": "C21-03-18.1"})
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/literature",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "arxiv_id": "1701.00006",
                        "arxiv_categories": ["hep-th"],
                        "preprint_date": "2019-10-15",
                        "document_type": "article",
                        "authors": [{"full_name": "Urhan, Harun"}],
                        "title": "Discovery of cool stuff",
                        "subjects": ["Other"],
                        "pdf_link": "https://arxiv.org/coolstuff.pdf",
                        "references": "[1] Dude",
                        "additional_link": "https://arxiv.org/other_stuff.pdf",
                        "comments": "comment will be here",
                        "proceedings_info": "Proceeding info will be here",
                        "conference_info": "conference info in very important topic",
                        "conference_record": conference["self"],
                    }
                }
            ),
        )
    assert response.status_code == 200

    history = requests_mock.request_history[0]
    post_data = history.json()

    expected_publication_info = [
        {"cnum": conference["cnum"], "conference_record": conference["self"]}
    ]

    assert post_data["data"]["publication_info"] == expected_publication_info


def test_new_literature_submit_with_wrong_conference(inspire_app, requests_mock):
    requests_mock.post(
        f"{current_app.config['INSPIRE_NEXT_URL']}/workflows/literature",
        json={"workflow_object_id": 30},
    )
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/literature",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "arxiv_id": "1701.00006",
                        "arxiv_categories": ["hep-th"],
                        "preprint_date": "2019-10-15",
                        "document_type": "article",
                        "authors": [{"full_name": "Urhan, Harun"}],
                        "title": "Discovery of cool stuff",
                        "subjects": ["Other"],
                        "pdf_link": "https://arxiv.org/coolstuff.pdf",
                        "references": "[1] Dude",
                        "additional_link": "https://arxiv.org/other_stuff.pdf",
                        "comments": "comment will be here",
                        "proceedings_info": "Proceeding info will be here",
                        "conference_info": "conference info in very important topic",
                        "conference_record": {
                            "$ref": "http://localhost:5000/api/conferences/12345"
                        },
                    }
                }
            ),
        )
    assert response.status_code == 200

    history = requests_mock.request_history[0]
    post_data = history.json()

    expected_publication_info = [
        {"conference_record": {"$ref": "http://localhost:5000/api/conferences/12345"}}
    ]

    assert post_data["data"]["publication_info"] == expected_publication_info


def test_new_literature_submit_with_conference_without_cnum(inspire_app, requests_mock):
    requests_mock.post(
        f"{current_app.config['INSPIRE_NEXT_URL']}/workflows/literature",
        json={"workflow_object_id": 30},
    )
    user = create_user()
    conference = create_record("con")
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/literature",
            content_type="application/json",
            data=orjson.dumps(
                {
                    "data": {
                        "arxiv_id": "1701.00006",
                        "arxiv_categories": ["hep-th"],
                        "preprint_date": "2019-10-15",
                        "document_type": "article",
                        "authors": [{"full_name": "Urhan, Harun"}],
                        "title": "Discovery of cool stuff",
                        "subjects": ["Other"],
                        "pdf_link": "https://arxiv.org/coolstuff.pdf",
                        "references": "[1] Dude",
                        "additional_link": "https://arxiv.org/other_stuff.pdf",
                        "comments": "comment will be here",
                        "proceedings_info": "Proceeding info will be here",
                        "conference_info": "conference info in very important topic",
                        "conference_record": conference["self"],
                    }
                }
            ),
        )
    assert response.status_code == 200

    history = requests_mock.request_history[0]
    post_data = history.json()

    expected_publication_info = [{"conference_record": conference["self"]}]

    assert post_data["data"]["publication_info"] == expected_publication_info


DEFAULT_EXAMPLE_JOB_DATA = {
    "deadline_date": "2030-01-01",
    "description": "description",
    "field_of_interest": ["q-bio"],
    "reference_letter_contact": {},
    "regions": ["Europe"],
    "status": "pending",
    "title": "Some title",
    "external_job_identifier": "",
}


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_job_submit_requires_authentication(ticket_mock, inspire_app):
    with inspire_app.test_client() as client:
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps(DEFAULT_EXAMPLE_JOB_DATA),
        )
    assert response.status_code == 401


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_job_update_requires_authentication(ticket_mock, inspire_app):
    with inspire_app.test_client() as client:
        response = client.post(
            "/submissions/jobs/1234",
            content_type="application/json",
            data=orjson.dumps(DEFAULT_EXAMPLE_JOB_DATA),
        )

    assert response.status_code == 401


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_job_get_requires_authentication(ticket_mock, inspire_app):
    with inspire_app.test_client() as client:
        response = client.get("/submissions/jobs/123", content_type="application/json")
    assert response.status_code == 401


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_new_job_submit_by_user(create_ticket_mock, inspire_app):
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": DEFAULT_EXAMPLE_JOB_DATA}),
        )
    assert response.status_code == 201

    job_id = orjson.loads(response.data)["pid_value"]
    job_data = JobsRecord.get_record_by_pid_value(job_id)

    assert job_data["status"] == "pending"
    create_ticket_mock.delay.assert_called_once()


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_new_job_submit_by_cataloger(ticket_mock, inspire_app):
    user = create_user(role=Roles.cataloger.value)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)

        post_data = {**DEFAULT_EXAMPLE_JOB_DATA, "status": "open"}
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": post_data}),
        )
    assert response.status_code == 201

    job_id = orjson.loads(response.data)["pid_value"]
    job_data = JobsRecord.get_record_by_pid_value(job_id)

    assert job_data["status"] == "open"


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_new_job_submit_with_wrong_field_value(ticket_mock, inspire_app):
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        data = {**DEFAULT_EXAMPLE_JOB_DATA, "deadline_date": "some value"}
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
    assert response.status_code == 400


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_new_job_submit_with_wrong_status_value(ticket_mock, inspire_app):
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        data = {**DEFAULT_EXAMPLE_JOB_DATA, "status": "closed"}
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
        assert response.status_code == 201
        pid_value = response.json["pid_value"]
        record_url = url_for(
            "inspirehep_submissions.job_submission_view", pid_value=pid_value
        )
        record = client.get(record_url).json["data"]
    assert record["status"] == "pending"


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_update_job(create_ticket_mock, inspire_app):
    user = create_user(orcid=FRANK_CASTLE_ORCID)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)

        data = {**DEFAULT_EXAMPLE_JOB_DATA}
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )

        assert response.status_code == 201

        create_ticket_mock.reset_mock()

        pid_value = response.json["pid_value"]
        record_url = url_for(
            "inspirehep_submissions.job_submission_view", pid_value=pid_value
        )
        data["title"] = "New test title"
        response2 = client.put(
            record_url,
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )

        assert response2.status_code == 200
        record = client.get(record_url).json["data"]
        assert record["title"] == "New test title"
        create_ticket_mock.delay.assert_called_once()


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_update_job_status_from_pending_not_curator(ticket_mock, inspire_app):
    user = create_user(orcid=FRANK_CASTLE_ORCID)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)

        data = {**DEFAULT_EXAMPLE_JOB_DATA}
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )

        assert response.status_code == 201

        pid_value = response.json["pid_value"]
        record_url = url_for(
            "inspirehep_submissions.job_submission_view", pid_value=pid_value
        )
        data["status"] = "open"
        response2 = client.put(
            record_url,
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )

        assert response2.status_code == 400
        record = client.get(record_url).json["data"]
        assert record["status"] == "pending"


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_update_job_status_from_pending_curator(create_ticket_mock, inspire_app):
    user = create_user(orcid=FRANK_CASTLE_ORCID)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)

        data = {**DEFAULT_EXAMPLE_JOB_DATA}
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )

    assert response.status_code == 201

    create_ticket_mock.reset_mock()

    pid_value = response.json["pid_value"]

    curator = create_user(role="cataloger")
    with inspire_app.test_client() as client:
        record_url = url_for(
            "inspirehep_submissions.job_submission_view", pid_value=pid_value
        )
        login_user_via_session(client, email=curator.email)

        data["status"] = "open"
        response2 = client.put(
            record_url,
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )

        assert response2.status_code == 200
        record = client.get(record_url).json["data"]
    assert record["status"] == "open"
    create_ticket_mock.delay.assert_not_called()


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_update_job_data_from_different_user(ticket_mock, inspire_app):
    user = create_user(orcid=FRANK_CASTLE_ORCID)
    user2 = create_user(orcid="0000-0001-5109-3700")
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        data = {**DEFAULT_EXAMPLE_JOB_DATA}
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
    assert response.status_code == 201
    pid_value = response.json["pid_value"]
    record_url = url_for(
        "inspirehep_submissions.job_submission_view", pid_value=pid_value
    )
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user2.email)
        data["title"] = "Title2"
        response2 = client.put(
            record_url,
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
    assert response2.status_code == 403


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_update_job_status_from_open(ticket_mock, inspire_app):
    user = create_user(orcid=FRANK_CASTLE_ORCID)
    curator = create_user(role="cataloger")
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        data = {**DEFAULT_EXAMPLE_JOB_DATA}
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
        assert response.status_code == 201
        pid_value = response.json["pid_value"]
        record_url = url_for(
            "inspirehep_submissions.job_submission_view", pid_value=pid_value
        )
        #  Login as curator to update job status

        login_user_via_session(client, email=curator.email)
        data["status"] = "open"
        response2 = client.put(
            record_url,
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
        assert response2.status_code == 200
        #  Login as user again to update job from open to closed
        login_user_via_session(client, email=user.email)
        data["status"] = "closed"
        response3 = client.put(
            record_url,
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )

        assert response3.status_code == 200
        record = client.get(record_url).json["data"]
    assert record["status"] == "closed"


@freeze_time("2019-01-31")
def test_job_update_data_30_days_after_deadline(inspire_app):
    user = create_user(orcid=FRANK_CASTLE_ORCID)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)

        data = {**DEFAULT_EXAMPLE_JOB_DATA, "deadline_date": "2019-01-01"}
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
        assert response.status_code == 201
        pid_value = response.json["pid_value"]
        record_url = url_for(
            "inspirehep_submissions.job_submission_view", pid_value=pid_value
        )

        response = client.get(record_url).json
        assert not response["meta"]["can_modify_status"]


@freeze_time("2019-01-31")
def test_job_update_data_30_days_after_deadline_with_cataloger(inspire_app):
    cataloger = create_user(role="cataloger")
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=cataloger.email)

        data = {**DEFAULT_EXAMPLE_JOB_DATA, "deadline_date": "2019-01-01"}
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
        assert response.status_code == 201
        pid_value = response.json["pid_value"]
        record_url = url_for(
            "inspirehep_submissions.job_submission_view", pid_value=pid_value
        )

        response = client.get(record_url).json
        assert response["meta"]["can_modify_status"]


@freeze_time("2019-01-31")
def test_job_update_data_less_than_30_days_after_deadline(inspire_app):
    user = create_user(orcid=FRANK_CASTLE_ORCID)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)

        data = {**DEFAULT_EXAMPLE_JOB_DATA, "deadline_date": "2019-01-02"}
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
        assert response.status_code == 201
        pid_value = response.json["pid_value"]
        record_url = url_for(
            "inspirehep_submissions.job_submission_view", pid_value=pid_value
        )

        response = client.get(record_url).json
        assert response["meta"]["can_modify_status"]


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_update_job_from_closed_less_than_30_days_after_deadline_by_user(
    ticket_mock, inspire_app
):
    user = create_user(orcid=FRANK_CASTLE_ORCID)
    curator = create_user(role="cataloger")
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        data = {**DEFAULT_EXAMPLE_JOB_DATA}
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
        assert response.status_code == 201
        pid_value = response.json["pid_value"]
        record_url = url_for(
            "inspirehep_submissions.job_submission_view", pid_value=pid_value
        )
        #  Login as curator to update job status
        login_user_via_session(client, email=curator.email)
        data["status"] = "closed"
        data["deadline_date"] = (datetime.now() - timedelta(1)).strftime(
            "%Y-%m-%d"
        )  # yesterday
        response2 = client.put(
            record_url,
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
        assert response2.status_code == 200
        #  Login as user again to update job title
        login_user_via_session(client, email=user.email)
        data["title"] = "Another Title"
        response3 = client.put(
            record_url,
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )

        assert response3.status_code == 200
        record = client.get(record_url).json["data"]
        assert record["title"] == "Another Title"


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_update_job_status_update_more_than_30_days_after_deadline_by_user(
    ticket_mock, inspire_app
):
    user = create_user(orcid=FRANK_CASTLE_ORCID)
    curator = create_user(role="cataloger")
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        data = {**DEFAULT_EXAMPLE_JOB_DATA}
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
        assert response.status_code == 201
        pid_value = response.json["pid_value"]
        record_url = url_for(
            "inspirehep_submissions.job_submission_view", pid_value=pid_value
        )
        #  Login as curator to update job status
        login_user_via_session(client, email=curator.email)
        data["status"] = "closed"
        data["deadline_date"] = "2020-01-01"
        response2 = client.put(
            record_url,
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
        assert response2.status_code == 200
        #  Login as user again to update job title
        login_user_via_session(client, email=user.email)
        data["status"] = "open"
        response3 = client.put(
            record_url,
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )

        assert response3.status_code == 400
        record = client.get(record_url).json["data"]
        assert record["status"] == "closed"


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_update_job_remove_not_compulsory_fields(ticket_mock, inspire_app):
    user = create_user(orcid=FRANK_CASTLE_ORCID)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        data = {
            **DEFAULT_EXAMPLE_JOB_DATA,
            "external_job_identifier": "IDENTIFIER",
            "experiments": [
                {
                    "legacy_name": "some legacy_name",
                    "record": {"$ref": "http://api/experiments/1234"},
                }
            ],
            "url": "http://something.com",
            "contacts": [
                {"name": "Some name", "email": "some@email.com"},
                {"name": "some other name"},
            ],
            "reference_letters": [
                "email@some.ch",
                "http://url.com",
                "something@somewhere.kk",
            ],
        }
        response = client.post(
            "/submissions/jobs",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
        pid_value = response.json["pid_value"]
        record_url = url_for(
            "inspirehep_submissions.job_submission_view", pid_value=pid_value
        )
        data = {**DEFAULT_EXAMPLE_JOB_DATA}
        response2 = client.put(
            record_url,
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )

        assert response2.status_code == 200
        response3 = client.get(record_url, content_type="application/json")
    assert response3.status_code == 200
    assert "external_job_identifier" not in response3.json["data"]
    assert "experiments" not in response3.json["data"]
    assert "url" not in response3.json["data"]
    assert "contacts" not in response3.json["data"]
    assert "reference_letters" not in response3.json["data"]


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_regression_update_job_without_acquisition_source_doesnt_give_500(
    ticket_mock, inspire_app
):
    data = {
        "status": "open",
        "_collections": ["Jobs"],
        "deadline_date": "2019-12-31",
        "description": "nice job",
        "position": "junior",
        "regions": ["Europe"],
    }
    rec = create_record("job", data=data)
    pid_value = rec["control_number"]
    job_record = JobsRecord.get_record_by_pid_value(pid_value)

    assert "acquisition_source" not in job_record

    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        data["title"] = "New Title"
        record_url = url_for(
            "inspirehep_submissions.job_submission_view", pid_value=pid_value
        )

        response = client.put(
            record_url,
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
    assert response.status_code == 403


CONFERENCE_FORM_DATA = {
    "name": "College on Computational Physics",
    "subtitle": "the best conference ever",
    "description": "lorem ipsum",
    "dates": ["1993-05-17", "1993-05-20"],
    "addresses": [{"city": "Trieste", "country": "Italy"}],
    "series_name": "ICFA Seminar on Future Perspectives in High-Energy Physics",
    "series_number": 11,
    "contacts": [
        {"email": "somebody@email.com", "name": "somebody"},
        {"email": "somebodyelse@email.com"},
    ],
    "field_of_interest": ["Accelerators"],
    "acronyms": ["foo", "bar"],
    "websites": ["http://somebody.example.com"],
    "additional_info": "UPDATED",
    "keywords": ["black hole: mass"],
}


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_new_user_conference_submission_full_form_is_in_db_and_es_and_has_all_fields_correct(
    ticket_mock, inspire_app
):
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/conferences",
            content_type="application/json",
            data=orjson.dumps({"data": CONFERENCE_FORM_DATA}),
        )
    assert response.status_code == 201

    payload = orjson.loads(response.data)
    conference_id = payload["pid_value"]
    conference_cnum = payload["cnum"]

    conference_rec = ConferencesRecord.get_record_by_pid_value(conference_id)
    assert conference_cnum == conference_rec["cnum"]
    assert get_value(conference_rec, "titles[0].title") == CONFERENCE_FORM_DATA["name"]
    assert (
        get_value(conference_rec, "titles[0].subtitle")
        == CONFERENCE_FORM_DATA["subtitle"]
    )
    assert (
        get_value(conference_rec, "short_description.value")
        == CONFERENCE_FORM_DATA["description"]
    )
    assert get_value(conference_rec, "opening_date") == CONFERENCE_FORM_DATA["dates"][0]
    assert get_value(conference_rec, "closing_date") == CONFERENCE_FORM_DATA["dates"][1]
    assert (
        get_value(conference_rec, "series[0].name")
        == CONFERENCE_FORM_DATA["series_name"]
    )
    assert (
        get_value(conference_rec, "series[0].number")
        == CONFERENCE_FORM_DATA["series_number"]
    )
    assert (
        get_value(conference_rec, "contact_details[0].email")
        == CONFERENCE_FORM_DATA["contacts"][0]["email"]
    )
    assert (
        get_value(conference_rec, "contact_details[0].name")
        == CONFERENCE_FORM_DATA["contacts"][0]["name"]
    )
    assert (
        get_value(conference_rec, "contact_details[1].email")
        == CONFERENCE_FORM_DATA["contacts"][1]["email"]
    )
    assert get_value(conference_rec, "acronyms") == CONFERENCE_FORM_DATA["acronyms"]
    assert (
        get_value(conference_rec, "urls[0].value")
        == CONFERENCE_FORM_DATA["websites"][0]
    )
    assert (
        get_value(conference_rec, "inspire_categories[0].term")
        == CONFERENCE_FORM_DATA["field_of_interest"][0]
    )
    assert (
        get_value(conference_rec, "public_notes[0].value")
        == CONFERENCE_FORM_DATA["additional_info"]
    )
    assert (
        get_value(conference_rec, "keywords[0].value")
        == CONFERENCE_FORM_DATA["keywords"][0]
    )
    assert get_value(conference_rec, "addresses[0].country_code") == "IT"
    assert (
        get_value(conference_rec, "addresses[0].cities[0]")
        == CONFERENCE_FORM_DATA["addresses"][0]["city"]
    )
    ticket_mock.delay.assert_called_once()


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_new_user_conference_submission_missing_dates_has_no_cnum(
    ticket_mock, inspire_app
):
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)

        form_data = deepcopy(CONFERENCE_FORM_DATA)
        form_data.pop("dates")

        response = client.post(
            "/submissions/conferences",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )

    payload = orjson.loads(response.data)
    conference_id = payload["pid_value"]
    conference_cnum = payload["cnum"]
    conference_record = ConferencesRecord.get_record_by_pid_value(conference_id)

    assert response.status_code == 201
    assert conference_cnum is None
    assert "cnum" not in conference_record

    ticket_mock.delay.assert_called_once()


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_non_logged_in_user_tries_to_submit(ticket_mock, inspire_app):
    form_data = deepcopy(CONFERENCE_FORM_DATA)
    with inspire_app.test_client() as client:
        response = client.post(
            "/submissions/conferences",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )

    assert response.status_code == 401

    ticket_mock.delay.assert_not_called()


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_rt_ticket_when_cataloger_submits_conference(ticket_mock, inspire_app):
    user = create_user(role=Roles.cataloger.value)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        form_data = deepcopy(CONFERENCE_FORM_DATA)
        response = client.post(
            "/submissions/conferences",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )

    assert response.status_code == 201
    ticket_mock.delay.assert_not_called()


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_rt_ticket_when_superuser_submits_conference(ticket_mock, inspire_app):
    user = create_user(role=Roles.superuser.value)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        form_data = deepcopy(CONFERENCE_FORM_DATA)
        response = client.post(
            "/submissions/conferences",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )

    assert response.status_code == 201
    ticket_mock.delay.assert_not_called()


@patch("inspirehep.submissions.views.send_conference_confirmation_email")
def test_confirmation_email_not_sent_when_user_is_superuser(
    mock_send_confirmation_email, inspire_app
):
    user = create_user(role=Roles.superuser.value)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        form_data = deepcopy(CONFERENCE_FORM_DATA)
        response = client.post(
            "/submissions/conferences",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )

    assert response.status_code == 201
    mock_send_confirmation_email.assert_not_called()


@patch("inspirehep.submissions.views.send_conference_confirmation_email")
def test_confirmation_email_not_sent_when_user_is_cataloger(
    mock_send_confirmation_email, inspire_app
):
    user = create_user(role=Roles.cataloger.value)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        form_data = deepcopy(CONFERENCE_FORM_DATA)
        response = client.post(
            "/submissions/conferences",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )

    assert response.status_code == 201
    mock_send_confirmation_email.assert_not_called()


@patch("inspirehep.submissions.views.send_conference_confirmation_email")
def test_confirmation_email_sent_for_regular_user(
    mock_send_confirmation_email, inspire_app
):
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        form_data = deepcopy(CONFERENCE_FORM_DATA)
        response = client.post(
            "/submissions/conferences",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )

    conference_rec = ConferencesRecord.get_record_by_pid_value(
        response.json["pid_value"]
    )
    assert response.status_code == 201
    mock_send_confirmation_email.assert_called_once_with(user.email, conference_rec)


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_conference_raise_loader_error(ticket_mock, inspire_app):
    DATA = deepcopy(CONFERENCE_FORM_DATA)
    DATA["addresses"][0]["country"] = "Graham City"
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/conferences",
            content_type="application/json",
            data=orjson.dumps({"data": DATA}),
        )
    assert response.status_code == 400


REQUIRED_SEMINAR_RECORD_DATA = {
    "title": {"title": "The Cool Seminar"},
    "inspire_categories": [{"term": "Accelerators"}],
    "speakers": [{"name": "Urhan, Ahmet"}],
    "end_datetime": "2020-05-06T12:30:00.000000",
    "start_datetime": "2020-05-06T06:30:00.000000",
    "timezone": "Europe/Zurich",
}
SEMINAR_RECORD_DATA = {
    "title": {"title": "The Cool Seminar"},
    "public_notes": [{"value": "A public note"}],
    "series": [{"name": "A seminar serie", "number": 1}],
    "captioned": True,
    "contact_details": [
        {
            "curated_relation": False,
            "email": "contact1@example",
            "name": "Contact 1",
            "record": {"$ref": "http://api/authors/1"},
        },
        {"email": "contact2@example"},
    ],
    "inspire_categories": [{"term": "Accelerators"}, {"term": "Math and Math Physics"}],
    "address": {"cities": ["Geneva"], "country_code": "CH"},
    "speakers": [
        {"name": "Urhan, Ahmet", "record": {"$ref": "http://api/authors/12"}},
        {
            "name": "Urhan, Harun",
            "affiliations": [
                {"value": "CERN", "record": {"$ref": "http://api/institutions/12"}}
            ],
            "record": {"$ref": "http://api/authors/2"},
        },
    ],
    "join_urls": [
        {"description": "primary", "value": "http://example.com/join/1"},
        {"value": "http://example.com/join/2"},
    ],
    "material_urls": [
        {"description": "slides", "value": "http://example.com/slides"},
        {"value": "http://example.com/pdf"},
    ],
    "end_datetime": "2020-05-06T12:30:00.000000",
    "start_datetime": "2020-05-06T06:30:00.000000",
    "timezone": "Europe/Zurich",
}

REQUIRED_SEMINAR_FORM_DATA = {
    "name": "The Cool Seminar",
    "timezone": "Europe/Zurich",
    "dates": ["2020-05-06 08:30 AM", "2020-05-06 02:30 PM"],
    "speakers": [{"name": "Urhan, Ahmet"}],
    "field_of_interest": ["Accelerators"],
}
SEMINAR_FORM_DATA = {
    "name": "The Cool Seminar",
    "timezone": "Europe/Zurich",
    "dates": ["2020-05-06 08:30 AM", "2020-05-06 02:30 PM"],
    "captioned": True,
    "join_urls": SEMINAR_RECORD_DATA["join_urls"],
    "material_urls": SEMINAR_RECORD_DATA["material_urls"],
    "speakers": [
        {"name": "Urhan, Ahmet", "record": {"$ref": "http://api/authors/12"}},
        {
            "name": "Urhan, Harun",
            "affiliation": "CERN",
            "affiliation_record": {"$ref": "http://api/institutions/12"},
            "record": {"$ref": "http://api/authors/2"},
        },
    ],
    "address": {"city": "Geneva", "country": "Switzerland"},
    "field_of_interest": ["Accelerators", "Math and Math Physics"],
    "contacts": SEMINAR_RECORD_DATA["contact_details"],
    "series_name": "A seminar serie",
    "series_number": 1,
    "additional_info": "A public note",
}


@pytest.mark.parametrize(
    ("form_data", "record_data"),
    [
        (SEMINAR_FORM_DATA, SEMINAR_RECORD_DATA),
        (REQUIRED_SEMINAR_FORM_DATA, REQUIRED_SEMINAR_RECORD_DATA),
    ],
)
def test_get_seminar_update_data(form_data, record_data, inspire_app):
    user = create_user()

    record_data = deepcopy(record_data)
    record_data["literature_records"] = [
        {"record": {"$ref": "http://localhost:5000/api/literature/123"}}
    ]
    seminar_data = {**record_data}
    rec = create_record_factory("sem", data=seminar_data)
    form_data = deepcopy(form_data)
    form_data["literature_records"] = ["123"]
    expected_data = {"data": form_data}
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.get(
            f"/submissions/seminars/{rec.data['control_number']}",
            headers={"Accept": "application/json"},
        )
    response_data = orjson.loads(response.data)

    assert response_data == expected_data


def test_get_seminar_update_data_not_found(inspire_app):
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)

        response = client.get(
            "/submissions/seminars/1993", headers={"Accept": "application/json"}
        )

    assert response.status_code == 404


def test_get_seminar_update_data_requires_auth(inspire_app):
    with inspire_app.test_client() as client:
        response = client.get(
            "/submissions/seminars/1993", headers={"Accept": "application/json"}
        )

    assert response.status_code == 401


@pytest.mark.parametrize(
    ("form_data", "expected_record_data"),
    [
        (deepcopy(SEMINAR_FORM_DATA), SEMINAR_RECORD_DATA),
        (deepcopy(REQUIRED_SEMINAR_FORM_DATA), REQUIRED_SEMINAR_RECORD_DATA),
    ],
)
@patch("inspirehep.submissions.views.send_seminar_confirmation_email")
@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_new_seminar_submission(
    create_ticket_mock,
    send_confirmation_mock,
    form_data,
    expected_record_data,
    inspire_app,
):
    orcid = "0000-0001-5109-3700"
    user = create_user(orcid=orcid)

    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/seminars",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )

    assert response.status_code == 201

    payload = orjson.loads(response.data)
    seminar_id = payload["pid_value"]
    seminar_record = SeminarsRecord.get_record_by_pid_value(seminar_id)
    seminar_record_data = {
        key: value
        for (key, value) in seminar_record.items()
        if key in SEMINAR_RECORD_DATA
    }
    assert seminar_record_data == expected_record_data
    assert get_value(seminar_record, "acquisition_source.orcid") == orcid

    create_ticket_mock.delay.assert_called_once()
    send_confirmation_mock.assert_called_once_with(user.email, seminar_record)


@patch("inspirehep.submissions.views.send_seminar_confirmation_email")
@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_new_seminar_submission_with_cataloger_login(
    create_ticket_mock, send_confirmation_mock, inspire_app
):
    orcid = "0000-0001-5109-3700"
    cataloger = create_user(role=Roles.cataloger.value, orcid=orcid)

    form_data = deepcopy(SEMINAR_FORM_DATA)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=cataloger.email)
        response = client.post(
            "/submissions/seminars",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )

    assert response.status_code == 201

    payload = orjson.loads(response.data)
    seminar_id = payload["pid_value"]
    seminar_record = SeminarsRecord.get_record_by_pid_value(seminar_id)
    seminar_record_data = {
        key: value
        for (key, value) in seminar_record.items()
        if key in SEMINAR_RECORD_DATA
    }
    assert seminar_record_data == SEMINAR_RECORD_DATA
    assert get_value(seminar_record, "acquisition_source.orcid") == orcid

    create_ticket_mock.delay.assert_not_called()
    send_confirmation_mock.assert_not_called()


@pytest.mark.parametrize(
    ("form_data", "record_data"),
    [
        (SEMINAR_FORM_DATA, SEMINAR_RECORD_DATA),
        (REQUIRED_SEMINAR_FORM_DATA, REQUIRED_SEMINAR_RECORD_DATA),
    ],
)
@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_seminar_update_submission(
    create_ticket_mock, form_data, record_data, inspire_app
):
    orcid = "0000-0001-5109-3700"
    user = create_user(orcid=orcid)

    seminar_data = {
        "acquisition_source": {"orcid": orcid},
        **record_data,
    }
    rec = create_record_factory("sem", data=seminar_data)

    update_form_data = deepcopy({**form_data, "name": "New name"})
    expected_record_data = {**record_data, "title": {"title": "New name"}}

    if "address" in update_form_data:
        # to test deletion
        update_form_data.pop("address")
        expected_record_data.pop("address")

    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.put(
            f"/submissions/seminars/{rec.data['control_number']}",
            content_type="application/json",
            data=orjson.dumps({"data": update_form_data}),
        )
    assert response.status_code == 200

    payload = orjson.loads(response.data)
    seminar_id = payload["pid_value"]
    seminar_record = SeminarsRecord.get_record_by_pid_value(seminar_id)
    seminar_record_data = {
        key: value for (key, value) in seminar_record.items() if key in record_data
    }
    assert seminar_record_data == expected_record_data

    create_ticket_mock.delay.assert_called_once()


@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_seminar_update_submission_with_cataloger_login(
    create_ticket_mock, inspire_app
):
    cataloger = create_user(role=Roles.cataloger.value, orcid="0000-0002-6665-4934")
    orcid = "0000-0001-5109-3700"

    seminar_data = {
        "acquisition_source": {"orcid": orcid},
        **SEMINAR_RECORD_DATA,
    }
    rec = create_record_factory("sem", data=seminar_data)

    form_data = deepcopy({**SEMINAR_FORM_DATA, "name": "New name"})
    form_data.pop("address")

    expected_record_data = {**SEMINAR_RECORD_DATA, "title": {"title": "New name"}}
    expected_record_data.pop("address")
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=cataloger.email)
        response = client.put(
            f"/submissions/seminars/{rec.data['control_number']}",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )
    assert response.status_code == 200

    payload = orjson.loads(response.data)
    seminar_id = payload["pid_value"]
    seminar_record = SeminarsRecord.get_record_by_pid_value(seminar_id)
    seminar_record_data = {
        key: value
        for (key, value) in seminar_record.items()
        if key in SEMINAR_RECORD_DATA
    }
    assert seminar_record_data == expected_record_data
    # cataloger's orcid shouldn't override the original submitter's
    assert get_value(seminar_record, "acquisition_source.orcid") == orcid

    create_ticket_mock.assert_not_called()


def test_seminar_update_submission_without_login(inspire_app):
    seminar_data = {
        "acquisition_source": {"orcid": "0000-0001-5109-3700"},
        **SEMINAR_RECORD_DATA,
    }
    rec = create_record_factory("sem", data=seminar_data)

    form_data = deepcopy({**SEMINAR_FORM_DATA, "name": "New name"})
    with inspire_app.test_client() as client:
        response = client.put(
            f"/submissions/seminars/{rec.data['control_number']}",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )
    assert response.status_code == 401


def test_seminar_update_submission_with_different_user(inspire_app):
    user = create_user()

    seminar_data = {
        "acquisition_source": {"orcid": "0000-0001-5109-3700"},
        **SEMINAR_RECORD_DATA,
    }
    rec = create_record_factory("sem", data=seminar_data)

    form_data = deepcopy({**SEMINAR_FORM_DATA, "name": "New name"})
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.put(
            f"/submissions/seminars/{rec.data['control_number']}",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )
    assert response.status_code == 403


@patch("inspirehep.submissions.views.send_seminar_confirmation_email")
@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_new_seminar_submission_with_valid_lit_record(
    create_ticket_mock, send_confirmation_mock, inspire_app
):
    orcid = "0000-0001-5109-3700"
    user = create_user(orcid=orcid)
    data = deepcopy(REQUIRED_SEMINAR_FORM_DATA)
    lit_record = create_record("lit")
    lit_record_control_number = lit_record["control_number"]
    data["literature_records"] = [lit_record_control_number]
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/seminars",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )

    assert response.status_code == 201

    payload = orjson.loads(response.data)
    seminar_id = payload["pid_value"]
    seminar_record = SeminarsRecord.get_record_by_pid_value(seminar_id)
    assert seminar_record["literature_records"] == [
        {
            "record": {
                "$ref": (
                    f"http://localhost:5000/api/literature/{lit_record_control_number}"
                )
            }
        }
    ]


@patch("inspirehep.submissions.views.send_seminar_confirmation_email")
@patch("inspirehep.submissions.views.async_create_ticket_with_template")
def test_new_seminar_submission_with_invalid_lit_record(
    create_ticket_mock, send_confirmation_mock, inspire_app
):
    orcid = "0000-0001-5109-3700"
    user = create_user(orcid=orcid)
    data = deepcopy(REQUIRED_SEMINAR_FORM_DATA)
    lit_record = create_record("lit")
    data["literature_records"] = [lit_record["control_number"], 666]
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/seminars",
            content_type="application/json",
            data=orjson.dumps({"data": data}),
        )
        assert response.status_code == 400
        assert response.json["message"][0] == "666 is not a valid literature record."


REQUIRED_EXPERIMENT_RECORD_DATA = {
    "$schema": "http://localhost:5000/schemas/records/experiments.json",
    "legacy_name": "CERN-LHC-ATLAS",
    "_collections": ["Experiments"],
    "project_type": ["experiment"],
}
EXPERIMENT_FORM_DATA = {"legacy_name": "CERN-LHC-ATLAS", "project_type": ["experiment"]}


@pytest.mark.parametrize(
    ("form_data", "expected_record_data"),
    [(deepcopy(EXPERIMENT_FORM_DATA), REQUIRED_EXPERIMENT_RECORD_DATA)],
)
def test_new_experiment_submission(form_data, expected_record_data, inspire_app):
    user = create_user(role=Roles.cataloger.value)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/experiments",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )
    assert response.status_code == 201

    payload = orjson.loads(response.data)
    experiment_id = payload["control_number"]
    experiment_record = ExperimentsRecord.get_record_by_pid_value(experiment_id)
    experiment_record_data = {
        key: value
        for (key, value) in experiment_record.items()
        if key in expected_record_data
    }
    assert experiment_record_data == expected_record_data


def test_new_experiment_submission_with_empty_data(
    inspire_app,
):
    form_data = {}
    user = create_user(role=Roles.cataloger.value)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/experiments",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )
    assert response.status_code == 400
    assert response.json["message"][0] == "Experiment is missing a value or values."


def test_new_experiment_submission_with_no_cataloger_role(inspire_app):
    form_data = {}
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/experiments",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )
    assert response.status_code == 403


REQUIRED_INSTITUTION_RECORD_DATA = {
    "$schema": "http://localhost:5000/schemas/records/institutions.json",
    "_collections": ["Institutions"],
    "legacy_ICN": "Humboldt U., Berlin",
    "ICN": ["Humboldt U., Berlin, Inst. Phys."],
}
INSTITUTION_FORM_DATA = {
    "legacy_ICN": "Humboldt U., Berlin",
    "ICN": ["Humboldt U., Berlin, Inst. Phys."],
}


@pytest.mark.parametrize(
    ("form_data", "expected_record_data"),
    [(deepcopy(INSTITUTION_FORM_DATA), REQUIRED_INSTITUTION_RECORD_DATA)],
)
def test_new_institution_submission(form_data, expected_record_data, inspire_app):
    user = create_user(role=Roles.cataloger.value)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/institutions",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )
    assert response.status_code == 201

    payload = orjson.loads(response.data)
    institution_id = payload["control_number"]

    institution_record = InstitutionsRecord.get_record_by_pid_value(institution_id)
    institution_record = {
        key: value
        for (key, value) in institution_record.items()
        if key in expected_record_data
    }

    assert institution_record == expected_record_data


def test_new_institution_submission_with_no_cataloger_role(inspire_app):
    user = create_user()
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/institutions",
            content_type="application/json",
            data=orjson.dumps({"data": {}}),
        )
    assert response.status_code == 403


def test_new_institution_submission_with_empty_data(
    inspire_app,
):
    form_data = {}
    user = create_user(role=Roles.cataloger.value)
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/institutions",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )

    assert response.status_code == 400
    assert response.json["message"][0] == "Institution is missing a value or values."


def test_new_journal_submission(
    inspire_app,
):
    journal_data = {
        "_collections": ["Journals"],
        "$schema": "http://localhost:5000/schemas/records/journals.json",
        "short_title": "RoMP",
        "journal_title": {"title": "Reviews of Modern Physics"},
    }

    form_data = {
        "short_title": "RoMP",
        "journal_title": {"title": "Reviews of Modern Physics"},
    }

    user = create_user(role=Roles.cataloger.value)

    with inspire_app.test_client() as client:
        login_user_via_session(client, email=user.email)
        response = client.post(
            "/submissions/journals",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )

    assert response.status_code == 201

    payload = orjson.loads(response.data)
    journal_id = payload["control_number"]
    journal_record = JournalsRecord.get_record_by_pid_value(journal_id)
    journal_record_data = {
        key: value for (key, value) in journal_record.items() if key in journal_data
    }
    assert journal_record_data == journal_data


def test_new_journal_submission_with_no_cataloger_role(inspire_app):
    form_data = {
        "short_title": "RoMP",
        "journal_title": {"title": "Reviews of Modern Physics"},
    }

    curator = create_user()

    with inspire_app.test_client() as client:
        login_user_via_session(client, email=curator.email)
        response = client.post(
            "/submissions/journals",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )

    assert response.status_code == 403


def test_new_journal_submission_with_empty_data(
    inspire_app,
):
    form_data = {}
    curator = create_user(role="cataloger")
    with inspire_app.test_client() as client:
        login_user_via_session(client, email=curator.email)
        response = client.post(
            "/submissions/journals",
            content_type="application/json",
            data=orjson.dumps({"data": form_data}),
        )
    assert response.status_code == 400
    assert response.json["message"][0] == "Journal is missing short_title"
