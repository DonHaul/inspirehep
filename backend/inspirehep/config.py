#
# Copyright (C) 2019 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Default configuration for inspirehep.

You overwrite and set instance-specific configuration by either:

- Configuration file: ``<virtualenv prefix>/var/instance/inspirehep.cfg``
- Environment variables: ``APP_<variable name>``
"""

import orjson
import pkg_resources

from inspirehep.search.serializers import ORJSONSerializerES
from inspirehep.serializers import serialize_json_for_sqlalchemy
from inspirehep.utils import include_table_check

# INSPIRE configuration
# =====================

# Feature flags
# =============
FEATURE_FLAG_ENABLE_BAI_PROVIDER = False
FEATURE_FLAG_ENABLE_BAI_CREATION = False
FEATURE_FLAG_ENABLE_FILES = False
FEATURE_FLAG_ENABLE_ORCID_PUSH = False
FEATURE_FLAG_ENABLE_SEND_TO_BACKOFFICE = False
FEATURE_FLAG_ENABLE_LITERATURE_DATA_LINKS = False
# Only push to ORCIDs that match this regex.
# Examples:
#   any ORCID -> ".*"
#   none -> "^$"
#   some ORCIDs -> "^(0000-0002-7638-5686|0000-0002-7638-5687)$"
FEATURE_FLAG_ORCID_PUSH_WHITELIST_REGEX = ".*"
FEATURE_FLAG_ENABLE_AUTHOR_DISAMBIGUATION = False
FEATURE_FLAG_ENABLE_FULLTEXT = False
FEATURE_FLAG_ENABLE_HAL_PUSH = False

# Web services and APIs
# =====================
AUTHENTICATION_TOKEN = "CHANGE_ME"
INSPIRE_NEXT_URL = "http://localhost:5000"
LEGACY_BASE_URL = "https://old.inspirehep.net"
LEGACY_RECORD_URL_PATTERN = "http://inspirehep.net/record/{recid}"
INSPIRE_BACKOFFICE_URL = "https://backoffice.dev.inspirebeta.net"
AUTHENTICATION_TOKEN_BACKOFFICE = "CHANGE_ME"
MAX_API_RESULTS = 10000
REST_MIMETYPE_QUERY_ARG_NAME = "format"

# Helpers
# =======
PID_TYPES_TO_ENDPOINTS = {
    "lit": "literature",
    "aut": "authors",
    "job": "jobs",
    "jou": "journals",
    "exp": "experiments",
    "con": "conferences",
    "dat": "data",
    "ins": "institutions",
    "sem": "seminars",
}
SCHEMA_TO_PID_TYPES = {
    "hep": "lit",
    "authors": "aut",
    "jobs": "job",
    "journals": "jou",
    "experiments": "exp",
    "conferences": "con",
    "data": "dat",
    "institutions": "ins",
    "seminars": "sem",
}
PID_TYPE_TO_INDEX = {
    "lit": "records-hep",
    "aut": "records-authors",
    "job": "records-jobs",
    "jou": "records-journals",
    "exp": "records-experiments",
    "con": "records-conferences",
    "dat": "records-data",
    "ins": "records-institutions",
    "sem": "records-seminars",
}
# Add here new collections as we release them in labs
COLLECTION_EQUIVALENCE = {
    "HEP": "literature",
    "HepNames": "authors",
    "Conferences": "conferences",
    "Jobs": "jobs",
    "Institutions": "institutions",
    "Experiments": "experiments",
}

NON_PRIVATE_LITERATURE_COLLECTIONS = {
    "Literature",
    "CDF Notes",
    "CDS Hidden",
    "D0 Preliminary Notes",
    "Fermilab",
    "HAL Hidden",
    "LArSoft Notes",
    "SLAC",
    "ZEUS Preliminary Notes",
}

COLLECTION_ROLES_TO_COLLECTION_NAMES = {
    "hep-hidden-read": "HEP Hidden",
    "hep-hidden-read-write": "HEP Hidden",
}

# Invenio and 3rd party
# =====================

# Rate limiting
# =============
#: Storage for ratelimiter.
RATELIMIT_ENABLED = False

# Email configuration
# ===================
#: Email address for support.
SUPPORT_EMAIL = "info@inspirehep.net"
#: Disable email sending by default.
MAIL_SUPPRESS_SEND = True

# Accounts
# ========
#: Email address used as sender of account registration emails.
SECURITY_EMAIL_SENDER = SUPPORT_EMAIL
#: Email subject for account registration emails.
SECURITY_EMAIL_SUBJECT_REGISTER = "Welcome to inspirehep!"
#: Redis session storage URL.
ACCOUNTS_SESSION_REDIS_URL = "redis://localhost:6379/1"

# Sessions
# ========
#: Pickle session protocol. This is needed because inspire-next uses python 2.
SESSION_PICKLE_PROTOCOL = 2

# Celery configuration
# ====================
BROKER_URL = "amqp://guest:guest@localhost:5672/"
#: URL of message broker for Celery (default is RabbitMQ).
CELERY_BROKER_URL = "amqp://guest:guest@localhost:5672/"
#: URL of backend for result storage (default is Redis).
CELERY_RESULT_BACKEND = "redis://localhost:6379/2"
#: Scheduled tasks configuration (aka cronjobs).
CELERY_BEAT_SCHEDULE = {
    #'indexer': {
    #    'task': 'invenio_indexer.tasks.process_bulk_queue',
    #    'schedule': timedelta(minutes=5),
    # },
    #'accounts': {
    #    'task': 'invenio_accounts.tasks.clean_session_table',
    #    'schedule': timedelta(minutes=60),
    # },
}
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True


class Annotator:
    def annotate(self, task):
        if task.acks_late:
            # avoid failing tasks when worker gets killed
            return {"reject_on_worker_lost": True}


CELERY_TASK_ANNOTATIONS = [Annotator()]

# Database
# ========
#: Database URI including user and password
SQLALCHEMY_DATABASE_URI = (
    "postgresql+psycopg2://postgres:postgres@localhost:5432/inspirehep"
)

SQLALCHEMY_ENGINE_OPTIONS = {
    "json_deserializer": orjson.loads,
    "json_serializer": serialize_json_for_sqlalchemy,
}

# JSONSchemas
# ===========
#: Hostname used in URLs for local JSONSchemas.
JSONSCHEMAS_HOST = "localhost:8000"

# Flask configuration
# ===================
# See details on
# http://flask.pocoo.org/docs/0.12/config/#builtin-configuration-values
SECRET_KEY = "CHANGE_ME"
#: Secret key - each installation (dev, production, ...) needs a separate key.
#: It should be changed before deploying.
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MiB
#: Max upload size for form data via application/mulitpart-formdata.
SESSION_COOKIE_SECURE = False
#: Sets cookie with the secure flag by default
DEBUG = True
SERVER_NAME = "localhost:8000"

# Debug
# =====
# Flask-DebugToolbar is by default enabled when the application is running in
# debug mode. More configuration options are available at
# https://flask-debugtoolbar.readthedocs.io/en/latest/#configuration

#: Switches off incept of redirects by Flask-DebugToolbar.
DEBUG_TB_INTERCEPT_REDIRECTS = False

# Pidstore
# ========
PIDSTORE_RECID_FIELD = "control_number"
PIDSTORE_APP_LOGGER_HANDLERS = False

# Invenio-App
# ===========
APP_HEALTH_BLUEPRINT_ENABLED = False
APP_ENABLE_SECURE_HEADERS = False

# Indexer
# =======
INDEXER_DEFAULT_INDEX = "records-hep"
INDEXER_DEFAULT_DOC_TYPE = "_doc"
INDEXER_BULK_REQUEST_TIMEOUT = 1200
FULLLTEXT_INDEXER_REQUEST_TIMEOUT = 90
INDEXER_REPLACE_REFS = False
SEARCH_INDEX_PREFIX = None
SEARCH_CLIENT_CONFIG = {"serializer": ORJSONSerializerES()}

# Alembic
# =======
ALEMBIC_CONTEXT = {
    "version_table": "inspirehep_alembic_version",
    "include_object": include_table_check,
}

ALEMBIC_SKIP_TABLES = [
    "alembic_version",
    "crawler_job",
    "crawler_workflows_object",
    "files_bucket",
    "files_buckettags",
    "files_files",
    "files_location",
    "files_multipartobject",
    "files_multipartobject_part",
    "files_object",
    "files_objecttags",
    "records_buckets",
    "oaiharvester_configs",
    "transaction",
    "workflows_audit_logging",
    "workflows_buckets",
    "workflows_object",
    "workflows_pending_record",
    "workflows_workflow",
]

SEARCH_MAX_RECURSION_LIMIT = 5000

# Refextract
# Path to where journal kb file is stored from `inspirehep.modules.refextract.tasks.create_journal_kb_file`
# On production, if you enable celery beat change this path to point to a shared space.
REFEXTRACT_JOURNAL_KB_PATH = pkg_resources.resource_filename(
    "refextract", "references/kbs/journal-titles.kb"
)

BATCHUPLOADER_WEB_ROBOT_TOKEN = "CHANGE_ME"

# Editor
EDITOR_LOCK_EXPIRATION_TIME = 2 * 60

SUBJECT_MISSING_VALUE = "Unknown"

# fulltext
ES_FULLTEXT_PIPELINE_NAME = "file_content"
ES_FULLTEXT_MAX_BULK_CHUNK_SIZE = 500 * 1014 * 1024  # 500 MiB

# refextract
REFEXTRACT_SERVICE_URL = "https://example:5000"

# cache
CACHE_TYPE = "RedisCache"
