#
# This file is part of INSPIRE.
# Copyright (C) 2018 CERN.
#
# INSPIRE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# INSPIRE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with INSPIRE. If not, see <http://www.gnu.org/licenses/>.
#
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.

import os

import mock
import orjson
import pkg_resources
import pytest
from inspirehep.records.api import InspireRecord
from inspirehep.records.api.literature import LiteratureRecord
from invenio_db import db
from invenio_oauthclient.models import RemoteAccount, RemoteToken, User, UserIdentity
from invenio_oauthclient.utils import oauth_link_external_id


@pytest.fixture
def user_with_permission(inspire_app):
    _user_data = {
        "orcid": "0000-0001-8829-5461",
        "token": "3d25a708-dae9-48eb-b676-aaaaaaaaaaaa",
        "email": "dummy1@email.com",
        "name": "Franz Kärtner",
        "consumer_key": "0000-0000-0000-0000",
        "allow_push": True,
    }

    create_user(**_user_data)

    yield _user_data

    cleanup_user_record(_user_data)


@pytest.fixture
def two_users_with_permission(inspire_app):
    _user1_data = {
        "orcid": "0000-0001-8829-5461",
        "token": "3d25a708-dae9-48eb-b676-aaaaaaaaaaaa",
        "email": "dummy1@email.com",
        "name": "Franz Kärtner",
        "consumer_key": "0000-0000-0000-0000",
        "allow_push": True,
    }
    _user2_data = {
        "orcid": "0000-0002-2174-4493",
        "token": "3d25a708-dae9-48eb-b676-bbbbbbbbbbbb",
        "email": "dummy2@email.com",
        "name": "Kranz Färtner Son",
        "consumer_key": "0000-0000-0000-0000",
        "allow_push": True,
    }

    create_user(**_user1_data)
    create_user(**_user2_data)

    yield _user1_data, _user2_data

    cleanup_user_record(_user1_data)
    cleanup_user_record(_user2_data)


@pytest.fixture
def user_without_permission(inspire_app):
    _user_data = {
        "orcid": "0000-0001-8829-5461",
        "token": "3d25a708-dae9-48eb-b676-aaaaaaaaaaaa",
        "email": "dummy1@email.com",
        "name": "Franz Kärtner",
        "consumer_key": "0000-0000-0000-0000",
        "allow_push": False,
    }

    create_user(**_user_data)

    yield _user_data

    cleanup_user_record(_user_data)


@pytest.fixture
def user_without_token(inspire_app):
    _user_data = {
        "orcid": "0000-0001-8829-5461",
        "email": "dummy1@email.com",
        "name": "Franz Kärtner",
        "consumer_key": "0000-0000-0000-0000",
        "allow_push": False,
    }

    create_user(**_user_data)

    yield _user_data

    cleanup_user_record(_user_data)


@pytest.fixture
def raw_record(inspire_app):
    data = {
        "$schema": "http://localhost:5000/schemas/records/hep.json",
        "document_type": ["article"],
        "titles": [{"title": "Jessica Jones"}],
        "_collections": ["Literature"],
        "references": [
            {"record": {"$ref": "http://localhost:5000/api/literature/1498589"}}
        ],
    }
    return data


@pytest.fixture
def record(raw_record):
    with mock.patch("inspirehep.orcid.api._send_push_task") as mock_orcid_push:
        mock_orcid_push.return_value = mock_orcid_push
        with mock.patch(
            "inspirehep.orcid.api.get_orcids_for_push",
            return_value=["0000-0001-8829-5461", "0000-0002-2174-4493"],
        ):
            _record = InspireRecord.create(raw_record)

    return _record


@pytest.fixture
def _enable_orcid_push_feature(inspire_app, override_config):
    with override_config(**{"FEATURE_FLAG_ENABLE_ORCID_PUSH": True}):
        yield


def create_user(orcid, email, name, consumer_key, token=None, allow_push=False):
    user = User()
    user.email = email
    with db.session.begin_nested():
        db.session.add(user)

    oauth_link_external_id(user, {"id": orcid, "method": "orcid"})

    if token:
        with db.session.begin_nested():
            db.session.add(
                RemoteToken.create(
                    user_id=user.id,
                    client_id=consumer_key,
                    token=token,
                    secret=None,
                    extra_data={
                        "orcid": orcid,
                        "full_name": name,
                        "allow_push": allow_push,
                    },
                )
            )


def assert_db_has_no_user_record(user_record):
    assert User.query.filter_by(email=user_record["email"]).count() == 0
    assert (
        RemoteAccount.query.join(User)
        .join(UserIdentity)
        .filter(UserIdentity.id == user_record["orcid"])
        .count()
        == 0
    )
    if "token" in user_record:
        assert (
            RemoteToken.query.filter_by(access_token=user_record["token"]).count() == 0
        )

    assert UserIdentity.query.filter_by(id=user_record["orcid"]).count() == 0


def cleanup_user_record(user_record):
    if "token" in user_record:
        RemoteToken.query.filter_by(access_token=user_record["token"]).delete()
    user_id = (
        db.session.query(UserIdentity.id_user)
        .filter(UserIdentity.id == user_record["orcid"])
        .subquery()
    )
    RemoteAccount.query.filter(RemoteAccount.user_id.in_(user_id)).delete(
        synchronize_session="fetch"
    )
    UserIdentity.query.filter_by(id=user_record["orcid"]).delete()
    User.query.filter_by(email=user_record["email"]).delete()
    assert_db_has_no_user_record(user_record)


def assert_db_has_no_author_record(author_recid):
    assert InspireRecord.query.filter_by().count() == 0


@mock.patch("inspirehep.orcid.api._send_push_task")
def test_orcid_push_not_trigger_for_author_records(
    mock_orcid_push_task, user_with_permission
):
    mock_orcid_push_task.assert_not_called()


@mock.patch("inspirehep.orcid.api._send_push_task")
def test_orcid_push_not_triggered_on_create_record_without_allow_push(
    mock_orcid_push_task, inspire_app, raw_record, user_without_permission
):
    with mock.patch(
        "inspirehep.orcid.api.get_orcids_for_push",
        return_value=["0000-0001-8829-5461", "0000-0002-2174-4493"],
    ):
        InspireRecord.create(raw_record)

    mock_orcid_push_task.assert_not_called()


@mock.patch("inspirehep.orcid.api._send_push_task")
def test_orcid_push_not_triggered_on_create_record_without_token(
    mock_orcid_push_task, inspire_app, raw_record, user_without_token
):
    with mock.patch(
        "inspirehep.orcid.api.get_orcids_for_push",
        return_value=["0000-0001-8829-5461", "0000-0002-2174-4493"],
    ):
        InspireRecord.create(raw_record)

    mock_orcid_push_task.assert_not_called()


@mock.patch("inspirehep.orcid.api._send_push_task")
@pytest.mark.usefixtures("_enable_orcid_push_feature")
def test_orcid_push_triggered_on_create_record_with_allow_push(
    mock_orcid_push_task,
    inspire_app,
    raw_record,
    user_with_permission,
    override_config,
):
    with mock.patch(
        "inspirehep.orcid.api.get_orcids_for_push",
        return_value=["0000-0001-8829-5461", "0000-0002-2174-4493"],
    ):
        record = InspireRecord.create(raw_record)
        expected_kwargs = {
            "kwargs": {
                "orcid": user_with_permission["orcid"],
                "rec_id": record["control_number"],
                "oauth_token": user_with_permission["token"],
                "kwargs_to_pusher": {"record_db_version": mock.ANY},
            }
        }
        mock_orcid_push_task.assert_called_once_with(**expected_kwargs)


@mock.patch("inspirehep.orcid.api._send_push_task")
@pytest.mark.usefixtures("_enable_orcid_push_feature")
def test_orcid_push_triggered_on_record_update_with_allow_push(
    mock_orcid_push_task,
    inspire_app,
    record,
    user_with_permission,
):
    expected_kwargs = {
        "kwargs": {
            "orcid": user_with_permission["orcid"],
            "rec_id": record["control_number"],
            "oauth_token": user_with_permission["token"],
            "kwargs_to_pusher": {"record_db_version": mock.ANY},
        }
    }
    with mock.patch(
        "inspirehep.orcid.api.get_orcids_for_push",
        return_value=["0000-0001-8829-5461", "0000-0002-2174-4493"],
    ):
        record.update(dict(record))

    mock_orcid_push_task.assert_called_once_with(**expected_kwargs)


@mock.patch("inspirehep.orcid.api._send_push_task")
@pytest.mark.usefixtures("_enable_orcid_push_feature")
def test_orcid_push_triggered_on_create_record_with_multiple_authors_with_allow_push(
    mock_orcid_push_task,
    inspire_app,
    raw_record,
    two_users_with_permission,
):
    with mock.patch(
        "inspirehep.orcid.api.get_orcids_for_push",
        return_value=["0000-0001-8829-5461", "0000-0002-2174-4493"],
    ):
        record = InspireRecord.create(raw_record)

    expected_kwargs_user1 = {
        "kwargs": {
            "orcid": two_users_with_permission[0]["orcid"],
            "rec_id": record["control_number"],
            "oauth_token": two_users_with_permission[0]["token"],
            "kwargs_to_pusher": {"record_db_version": mock.ANY},
        }
    }
    expected_kwargs_user2 = {
        "kwargs": {
            "orcid": two_users_with_permission[1]["orcid"],
            "rec_id": record["control_number"],
            "oauth_token": two_users_with_permission[1]["token"],
            "kwargs_to_pusher": {"record_db_version": mock.ANY},
        }
    }

    mock_orcid_push_task.assert_any_call(**expected_kwargs_user1)
    mock_orcid_push_task.assert_any_call(**expected_kwargs_user2)
    assert mock_orcid_push_task.call_count == 2


@mock.patch("inspirehep.orcid.api._send_push_task")
def test_orcid_push_not_triggered_on_create_record_no_feat_flag(
    mocked_Task, inspire_app, raw_record, user_with_permission
):
    with mock.patch(
        "inspirehep.orcid.api.get_orcids_for_push",
        return_value=["0000-0001-8829-5461", "0000-0002-2174-4493"],
    ):
        InspireRecord.create(raw_record)

    mocked_Task.assert_not_called()


@pytest.mark.usefixtures("inspire_app")
class TestPushToOrcid:
    @pytest.fixture(autouse=True)
    def _setup(self, inspire_app):
        # record 736770
        record_fixture_path = pkg_resources.resource_filename(
            __name__, os.path.join("fixtures", "736770.json")
        )
        with open(record_fixture_path) as fp:
            data = orjson.loads(fp.read())
        self.record = LiteratureRecord.create(data)

    def test_existing_record(self, override_config):
        recid = self.record["control_number"]
        inspire_record = LiteratureRecord.get_record_by_pid_value(recid)
        with (
            override_config(
                FEATURE_FLAG_ENABLE_ORCID_PUSH=True,
                FEATURE_FLAG_ORCID_PUSH_WHITELIST_REGEX=".*",
                ORCID_APP_CREDENTIALS={"consumer_key": "0000-0001-8607-8906"},
            ),
            mock.patch(
                "inspirehep.orcid.api.push_access_tokens"
            ) as mock_push_access_tokens,
            mock.patch("inspirehep.orcid.api._send_push_task") as mock_send_push_task,
        ):
            mock_push_access_tokens.get_access_tokens.return_value = [
                ("myorcid", "mytoken")
            ]
            inspire_record.update(dict(inspire_record))
            mock_send_push_task.assert_called_once_with(
                kwargs={
                    "orcid": "myorcid",
                    "oauth_token": "mytoken",
                    "kwargs_to_pusher": {
                        "record_db_version": inspire_record.model.version_id
                    },
                    "rec_id": recid,
                }
            )

    def test_new_record(self, override_config):
        record_json = {
            "$schema": "http://localhost:5000/schemas/records/hep.json",
            "document_type": ["article"],
            "titles": [{"title": "Jessica Jones"}],
            "_collections": ["Literature"],
            "references": [
                {"record": {"$ref": "http://localhost:5000/api/literature/1498589"}}
            ],
        }
        inspire_record = InspireRecord.create(record_json)
        with (
            override_config(
                FEATURE_FLAG_ENABLE_ORCID_PUSH=True,
                FEATURE_FLAG_ORCID_PUSH_WHITELIST_REGEX=".*",
                ORCID_APP_CREDENTIALS={"consumer_key": "0000-0001-8607-8906"},
            ),
            mock.patch(
                "inspirehep.orcid.api.push_access_tokens"
            ) as mock_push_access_tokens,
            mock.patch("inspirehep.orcid.api._send_push_task") as mock_send_push_task,
        ):
            mock_push_access_tokens.get_access_tokens.return_value = [
                ("myorcid", "mytoken")
            ]
            inspire_record.update(dict(inspire_record))
            mock_send_push_task.assert_called_once_with(
                kwargs={
                    "orcid": "myorcid",
                    "oauth_token": "mytoken",
                    "kwargs_to_pusher": {
                        "record_db_version": inspire_record.model.version_id
                    },
                    "rec_id": inspire_record["control_number"],
                }
            )
