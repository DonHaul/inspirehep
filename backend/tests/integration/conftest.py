#
# Copyright (C) 2019 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""INSPIRE module that adds more fun to the platform."""

from contextlib import contextmanager
from functools import partial

import boto3
import mock
import pytest
from click.testing import CliRunner
from flask import current_app
from flask.cli import ScriptInfo
from helpers.cleanups import db_cleanup, es_cleanup
from helpers.factories.models.base import BaseFactory
from helpers.factories.models.pidstore import PersistentIdentifierFactory
from helpers.factories.models.records import RecordMetadataFactory
from inspirehep.cli import cli as inspire_cli
from inspirehep.factory import create_app as inspire_create_app
from inspirehep.files.api.s3 import S3
from invenio_cache import current_cache
from moto import mock_s3
from redis import StrictRedis


@pytest.fixture(scope="module")
def _instance_path():
    """Override pytest-invenio fixture creating a temp dir."""
    return


@pytest.fixture(scope="module")
def app_config(app_config):
    # add extra global config if you would like to customize the config
    # for a specific test you can change create fixture per-directory
    # using ``conftest.py`` or per-file.
    app_config["DEBUG"] = False
    app_config["JSONSCHEMAS_HOST"] = "localhost:5000"
    app_config["SERVER_NAME"] = "localhost:5000"
    app_config["SEARCH_INDEX_PREFIX"] = "test-integration-"
    app_config["SQLALCHEMY_DATABASE_URI"] = (
        "postgresql+psycopg2://postgres:postgres@localhost/test-inspirehep"
    )
    app_config["FILES_MAX_UPLOAD_THREADS"] = 1
    return app_config


@pytest.fixture
def enable_files(inspire_app, override_config):
    with override_config(FEATURE_FLAG_ENABLE_FILES=True):
        yield inspire_app


@pytest.fixture
def disable_files(inspire_app, override_config):
    with override_config(FEATURE_FLAG_ENABLE_FILES=False):
        yield inspire_app


@pytest.fixture
def enable_hal_push(inspire_app, override_config):
    with override_config(FEATURE_FLAG_ENABLE_HAL_PUSH=True):
        yield inspire_app


@pytest.fixture
def disable_hal_push(inspire_app, override_config):
    with override_config(FEATURE_FLAG_ENABLE_HAL_PUSH=False):
        yield inspire_app


@pytest.fixture(scope="module")
def create_app():
    return inspire_create_app


@pytest.fixture(scope="module")
def database(appctx):
    """Setup database."""
    from invenio_db import db as db_

    db_cleanup(db_)
    yield db_
    db_.session.remove()


@pytest.fixture
def db_(database):
    """Creates a new database session for a test.
    Scope: function
    You must use this fixture if your test connects to the database. The
    fixture will set a save point and rollback all changes performed during
    the test (this is much faster than recreating the entire database).
    """
    import sqlalchemy as sa

    connection = database.engine.connect()
    transaction = connection.begin()

    options = dict(bind=connection, binds={})
    session = database.create_scoped_session(options=options)

    session.begin_nested()

    # FIXME: attach session to all factories
    # https://github.com/pytest-dev/pytest-factoryboy/issues/11#issuecomment-130521820
    BaseFactory._meta.sqlalchemy_session = session
    RecordMetadataFactory._meta.sqlalchemy_session = session
    PersistentIdentifierFactory._meta.sqlalchemy_session = session
    # `session` is actually a scoped_session. For the `after_transaction_end`
    # event, we need a session instance to listen for, hence the `session()`
    # call.

    @sa.event.listens_for(session(), "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not trans._parent.nested:
            session.expire_all()
            session.begin_nested()

    old_session = database.session
    database.session = session

    yield database
    session.remove()
    transaction.rollback()
    connection.close()
    database.session = old_session


@pytest.fixture
def db(db_):
    return db_


@pytest.fixture
def es_clear(es):
    es_cleanup(es)
    return es


@pytest.fixture
def cli(inspire_app):
    """Click CLI runner inside the Flask application."""
    runner = CliRunner()
    obj = ScriptInfo(create_app=lambda: inspire_app)
    runner.invoke = partial(runner.invoke, inspire_cli, obj=obj)
    return runner


@pytest.fixture
def redis(inspire_app):
    redis_url = inspire_app.config.get("CACHE_REDIS_URL")
    redis = StrictRedis.from_url(redis_url, decode_responses=True)
    redis.flushall()
    yield redis
    redis.flushall()
    redis.close()


@pytest.fixture
def inspire_app(base_app, db, es_clear, vcr_config):
    # Make sure the API app has the same config
    base_app.wsgi_app.mounts["/api"].config.update(base_app.config)
    return base_app


@pytest.fixture
def override_config(inspire_app):
    @contextmanager
    def _override_config(**kwargs):
        """Override Flask's current app configuration.

        Note: it's a CONTEXT MANAGER.from

        Example:

            with override_config(
                MY_FEATURE_FLAG_ACTIVE=True,
                MY_USERNAME='username',
            ):
                ...
        """
        with (
            mock.patch.dict(inspire_app.config, kwargs),
            mock.patch.dict(inspire_app.wsgi_app.mounts["/api"].config, kwargs),
        ):
            yield

    return _override_config


@pytest.fixture
def s3(inspire_app, enable_files):
    mock = mock_s3()
    mock.start()
    client = boto3.client("s3")
    resource = boto3.resource("s3")
    s3 = S3(client, resource)

    class MockedInspireS3:
        s3_instance = s3

    real_inspirehep_s3 = inspire_app.extensions["inspirehep-s3"]
    inspire_app.extensions["inspirehep-s3"] = MockedInspireS3

    yield s3
    mock.stop()
    inspire_app.extensions["inspirehep-s3"] = real_inspirehep_s3


@pytest.fixture
def _mocked_inspire_snow(mocker):
    # If SNOW_AUTH_URL (and SNOW_CLIENT_ID, SNOW_CLIENT_SECRET) is set, we dont need to mock the token
    if not current_app.config.get("SNOW_AUTH_URL"):
        mocker.patch(
            "inspirehep.snow.api.InspireSnow.headers",
            new_callable=mocker.PropertyMock,
            return_value={
                "Authorization": "Bearer abcd",
                "Content-Type": "application/json",
            },
        )
        mocker.patch("inspirehep.snow.api.InspireSnow.get_token", return_value="abcd")


@pytest.fixture
def _teardown_cache():
    yield
    current_cache.delete("snow_users")
    current_cache.delete("snow_functional_categories")
