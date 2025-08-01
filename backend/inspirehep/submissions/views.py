#
# Copyright (C) 2019 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

import datetime

import orjson
import requests
import structlog
from flask import Blueprint, abort, current_app, request, url_for
from flask.views import MethodView
from flask_login import current_user
from inspire_schemas.builders import JobBuilder
from inspire_utils.record import get_value
from invenio_db import db
from invenio_pidstore.errors import PIDDoesNotExistError
from jsonschema import SchemaError, ValidationError
from requests.exceptions import RequestException

from inspirehep.accounts.api import (
    can_user_edit_author_record,
    can_user_edit_record,
    get_current_user_orcid,
    is_superuser_or_cataloger_logged_in,
)
from inspirehep.accounts.decorators import login_required_with_roles
from inspirehep.accounts.roles import Roles
from inspirehep.mailing.api.conferences import send_conference_confirmation_email
from inspirehep.mailing.api.seminars import send_seminar_confirmation_email
from inspirehep.records.api import (
    AuthorsRecord,
    ExperimentsRecord,
    InstitutionsRecord,
    JobsRecord,
    JournalsRecord,
    SeminarsRecord,
)
from inspirehep.records.api.conferences import ConferencesRecord
from inspirehep.serializers import jsonify
from inspirehep.submissions.errors import (
    RESTDataError,
    WorkflowConflictError,
    WorkflowStartError,
)
from inspirehep.submissions.loaders import author_v1 as author_loader_v1
from inspirehep.submissions.loaders import conference_v1 as conference_loader_v1
from inspirehep.submissions.loaders import experiment_v1 as experiment_loader_v1
from inspirehep.submissions.loaders import institution_v1 as institution_loader_v1
from inspirehep.submissions.loaders import job_v1 as job_loader_v1
from inspirehep.submissions.loaders import journal_v1 as journal_loader_v1
from inspirehep.submissions.loaders import literature_v1 as literature_loader_v1
from inspirehep.submissions.loaders import seminar_v1 as seminar_loader_v1
from inspirehep.submissions.serializers import author_v1, job_v1
from inspirehep.submissions.serializers import seminar_v1 as seminar_serializer_v1
from inspirehep.submissions.tasks import async_create_ticket_with_template
from inspirehep.submissions.utils import has_30_days_passed_after_deadline
from inspirehep.utils import get_inspirehep_url

blueprint = Blueprint("inspirehep_submissions", __name__, url_prefix="/submissions")

LOGGER = structlog.getLogger()


def get_updated_record_data(record, update_form_data, optional_field_names):
    record_data = dict(record)

    # delete optional fields if they are removed in the form data
    for field in optional_field_names:
        if field not in update_form_data and field in record_data:
            del record_data[field]
    # overwrite record data with form data
    record_data.update(update_form_data)
    return record_data


class BaseSubmissionsResource(MethodView):
    decorators = [login_required_with_roles()]

    def load_data_from_request(self):
        return request.get_json()

    def send_post_request_to_workflows(
        self, url, endpoint, data, token, bearer_keyword="Bearer"
    ):
        """Sends a post request to the backoffice/next

        :param string endpoint: endpoint
        :param object data: payload
        :raises WorkflowStartError: error during workflow creation
        :return: response content
        """

        LOGGER.info("Sending post request to workflows", url=url, endpoint=endpoint)
        headers = {
            "content-type": "application/json",
            "Authorization": f"{bearer_keyword} {token}",
        }
        response = requests.post(
            f"{url}{endpoint}",
            data=orjson.dumps(data),
            headers=headers,
        )
        try:
            response.raise_for_status()
        except RequestException as e:
            LOGGER.exception(
                "Error during workflow creation.",
                response=response.text,
                data=data,
                url=url,
                endpoint=endpoint,
                bearer_keyword=bearer_keyword,
            )
            match response.status_code:
                case 409:
                    raise WorkflowConflictError from e
                case _:
                    raise WorkflowStartError from e

        LOGGER.info("Workflow creation successful", response=response.text)
        return response.json()

    def get_acquisition_source(self):
        acquisition_source = dict(
            email=current_user.email,
            datetime=datetime.datetime.utcnow().isoformat(),
            method="submitter",
            source="submitter",
            internal_uid=int(current_user.get_id()),
        )

        orcid = self.get_user_orcid()
        if orcid:
            acquisition_source["orcid"] = orcid
        return acquisition_source

    # TODO: remove this and directly use `get_current_user_orcid`
    def get_user_orcid(self):
        return get_current_user_orcid()


class AuthorSubmissionsResource(BaseSubmissionsResource):
    def get(self, pid_value):
        try:
            record = AuthorsRecord.get_record_by_pid_value(pid_value)

            if not can_user_edit_author_record(record):
                return (
                    jsonify({"message": "You are not allowed to edit this author"}),
                    403,
                )
        except PIDDoesNotExistError:
            abort(404)
        serialized_record = author_v1.dump(record)
        return jsonify({"data": serialized_record})

    def post(self):
        data = self.load_data_from_request()
        return self.start_workflow_for_submission(data, "AUTHOR_CREATE")

    def put(self, pid_value):
        try:
            record = AuthorsRecord.get_record_by_pid_value(pid_value)
            # check if we need to check the orcid in the acquisition source or the one in ids
            if not can_user_edit_author_record(record):
                return (
                    jsonify({"message": "You are not allowed to edit this author"}),
                    403,
                )
        except PIDDoesNotExistError:
            abort(404)
        data = self.load_data_from_request()
        self.update_author_record(data, record)
        db.session.commit()

        self.start_workflow_for_submission(record, "AUTHOR_UPDATE")

        return jsonify({"pid_value": record["control_number"]})

    def update_author_record(self, update_data, record):
        optional_fields = [
            "email_addresses",
            "public_notes",
            "urls",
            "positions",
            "project_membership",
            "arxiv_categories",
            "advisors",
        ]

        if "_private_notes" in update_data and "_private_notes" in record:
            record["_private_notes"].extend(update_data["_private_notes"])
            del update_data["_private_notes"]

        record_ids = record.get("ids", [])
        record_ids_schemas = set(get_value(record, "ids.schema", []))
        for id_dict in update_data.get("ids", []):
            if (id_dict["schema"] not in record_ids_schemas) or (
                id_dict["schema"] == "ORCID" and id_dict not in record_ids
            ):
                record["ids"].append(id_dict)
            elif id_dict["schema"] != "ORCID":
                for record_id in record_ids:
                    if record_id["schema"] == id_dict["schema"]:
                        record_id["value"] = id_dict["value"]
            update_data.pop("ids", None)

        updated_record_data = get_updated_record_data(
            record, update_data, optional_fields
        )
        record.update(updated_record_data)

    def load_data_from_request(self):
        return author_loader_v1()

    def start_workflow_for_submission(self, record, workflow_type):
        """Sends workflow payload to the backoffice.

        :param object record: dict with workflow model variables set
        :param str workflow_type: distinguish between UPDATE and CREATE
        :return object: inspire next response
        """
        record["acquisition_source"] = self.get_acquisition_source()
        payload = {"data": record, "workflow_type": workflow_type}

        LOGGER.info("Sending author submission to backoffice", data=payload)
        return self.send_post_request_to_workflows(
            current_app.config["INSPIRE_BACKOFFICE_URL"],
            "/api/workflows/authors/",
            payload,
            current_app.config["AUTHENTICATION_TOKEN_BACKOFFICE"],
            bearer_keyword="Token",
        )

    def create_ticket(self, record, rt_template):
        control_number = record["control_number"]
        author_name = record["name"]["value"]

        hep_url = get_inspirehep_url()
        author_url = f"{hep_url}/authors/{control_number}"
        author_form_url = f"{hep_url}/submissions/authors/{control_number}"
        # need to add author editor url?

        rt_queue = "Author updates"

        requestor = current_user.email
        rt_template_context = {
            "author_url": author_url,
            "author_form_url": author_form_url,
            "hep_url": hep_url,
        }
        async_create_ticket_with_template.delay(
            rt_queue,
            requestor,
            rt_template,
            rt_template_context,
            f"Your update to author {author_name} on INSPIRE",
            control_number,
        )


class ConferenceSubmissionsResource(BaseSubmissionsResource):
    def post(self):
        """Adds new conference record"""

        data = self.load_data_from_request()

        record = ConferencesRecord.create(data)
        db.session.commit()
        if not is_superuser_or_cataloger_logged_in():
            self.create_ticket(record, "snow/new_conference.html")
            send_conference_confirmation_email(current_user.email, record)
        return (
            jsonify(
                {"pid_value": record["control_number"], "cnum": record.get("cnum")}
            ),
            201,
        )

    def load_data_from_request(self):
        return conference_loader_v1()

    def create_ticket(self, record, rt_template):
        control_number = record["control_number"]

        INSPIREHEP_URL = get_inspirehep_url()
        CONFERENCE_DETAILS = f"{INSPIREHEP_URL}/conferences/{control_number}"
        CONFERENCE_EDIT = f"{INSPIREHEP_URL}/submissions/conferences/{control_number}"

        rt_queue = "Conferences"

        requestor = current_user.email
        rt_template_context = {
            "conference_url": CONFERENCE_DETAILS,
            "conference_url_edit": CONFERENCE_EDIT,
            "hep_url": INSPIREHEP_URL,
        }
        async_create_ticket_with_template.delay(
            rt_queue,
            requestor,
            rt_template,
            rt_template_context,
            f"New Conference Submission {control_number}.",
            control_number,
        )


class ExperimentSubmissionsResource(BaseSubmissionsResource):
    decorators = [login_required_with_roles([Roles.cataloger.value])]

    def load_data_from_request(self):
        return experiment_loader_v1()

    def post(self):
        """Adds new experiment record"""

        data = self.load_data_from_request()
        record = ExperimentsRecord(data=data).create(data)
        db.session.commit()
        return (jsonify({"control_number": record["control_number"]}), 201)


class SeminarSubmissionsResource(BaseSubmissionsResource):
    def post(self):
        """Adds new conference record"""

        data = self.load_data_from_request()
        data["acquisition_source"] = self.get_acquisition_source()
        record = SeminarsRecord.create(data)
        db.session.commit()

        if not is_superuser_or_cataloger_logged_in():
            self.create_ticket(record, "snow/new_seminar.html")
            send_seminar_confirmation_email(current_user.email, record)

        return (jsonify({"pid_value": record["control_number"]}), 201)

    def get(self, pid_value):
        try:
            record = SeminarsRecord.get_record_by_pid_value(pid_value)
        except PIDDoesNotExistError:
            abort(404)

        serialized_record = seminar_serializer_v1.dump(record)

        return jsonify({"data": serialized_record})

    def put(self, pid_value):
        try:
            record = SeminarsRecord.get_record_by_pid_value(pid_value)
            if not can_user_edit_record(record):
                return (
                    jsonify({"message": "You are not allowed to edit this seminar"}),
                    403,
                )
        except PIDDoesNotExistError:
            abort(404)
        data = self.load_data_from_request()
        updated_record_data = self.get_updated_record_data(data, record)
        record.update(updated_record_data)
        db.session.commit()

        if not is_superuser_or_cataloger_logged_in():
            self.create_ticket(record, "snow/update_seminar.html")

        return jsonify({"pid_value": record["control_number"]})

    def get_updated_record_data(self, update_data, record):
        optional_fields = [
            "address",
            "series",
            "contact_details",
            "urls",
            "join_urls",
            "abstract",
            "keywords",
            "public_notes",
        ]

        return get_updated_record_data(record, update_data, optional_fields)

    def create_ticket(self, record, rt_template):
        control_number = record["control_number"]

        hep_url = get_inspirehep_url()
        seminar_url = f"{hep_url}/seminars/{control_number}"
        seminar_edit_url = f"{hep_url}/submissions/seminars/{control_number}"

        rt_queue = "Seminars"

        requestor = current_user.email
        rt_template_context = {
            "seminar_url": seminar_url,
            "seminar_edit_url": seminar_edit_url,
            "hep_url": hep_url,
        }
        async_create_ticket_with_template.delay(
            rt_queue,
            requestor,
            rt_template,
            rt_template_context,
            f"New Seminar Submission {control_number}.",
            control_number,
        )

    def load_data_from_request(self):
        return seminar_loader_v1()


class LiteratureSubmissionResource(BaseSubmissionsResource):
    def post(self):
        return self.start_workflow_for_submission()

    def load_data_from_request(self):
        return literature_loader_v1()

    def start_workflow_for_submission(self, control_number=None):
        submission_data = self.load_data_from_request()
        # FIXME: we get the request data twice
        request_submission_data = request.get_json()["data"]
        form_data = {
            "url": request_submission_data.get("pdf_link"),
            "references": request_submission_data.get("references"),
        }
        submission_data["acquisition_source"] = self.get_acquisition_source()
        payload = {"data": submission_data, "form_data": form_data}

        return self.send_post_request_to_workflows(
            current_app.config["INSPIRE_NEXT_URL"],
            "/workflows/literature",
            payload,
            current_app.config["AUTHENTICATION_TOKEN"],
        )


class JobSubmissionsResource(BaseSubmissionsResource):
    data_loader_from_request = job_loader_v1

    user_allowed_status_changes = {
        "pending": ["pending"],
        "open": ["open", "closed"],
        "closed": ["open", "closed"],
    }

    def get(self, pid_value):
        try:
            pid, _ = pid_value.data
            record = JobsRecord.get_record_by_pid_value(pid.pid_value)
        except PIDDoesNotExistError:
            abort(404)

        serialized_record = job_v1.dump(record)
        deadline = serialized_record.get("deadline_date")

        can_modify_status = (
            is_superuser_or_cataloger_logged_in()
            or not has_30_days_passed_after_deadline(deadline)
        )
        return jsonify(
            {
                "data": serialized_record,
                "meta": {"can_modify_status": can_modify_status},
            }
        )

    def post(self):
        """Adds new job record"""
        data = self.load_data_from_request()
        builder = self.get_builder_with_new_record(data)
        data = self.get_valid_record_data_from_builder(builder)
        record = JobsRecord.create(data)
        db.session.commit()
        self.create_ticket(record, "snow/new_job.html")
        return jsonify({"pid_value": record["control_number"]}), 201

    def put(self, pid_value):
        """Updates existing record in db"""
        data = self.load_data_from_request()

        try:
            pid, _ = pid_value.data
            record = JobsRecord.get_record_by_pid_value(pid.pid_value)
            if not self.user_can_edit(record):
                return (
                    jsonify(
                        {"message": "You are not allowed to edit this Job opening"}
                    ),
                    403,
                )
        except PIDDoesNotExistError:
            abort(404)

        self.raise_if_user_can_not_modify_status(data, record)

        builder = self.get_builder_with_updated_record(data, record)
        data = self.get_valid_record_data_from_builder(builder)
        record.update(data)
        db.session.commit()

        if not is_superuser_or_cataloger_logged_in():
            self.create_ticket(record, "snow/update_job.html")

        return jsonify({"pid_value": record["control_number"]})

    def load_data_from_request(self):
        return job_loader_v1()

    def raise_if_user_can_not_modify_status(self, data, existing_record):
        if is_superuser_or_cataloger_logged_in():
            return

        old_status = existing_record.get("status", "pending")
        new_status = data.get("status", old_status)
        deadline = data.get("deadline_date")

        has_status_changed = new_status != old_status
        is_change_to_new_status_allowed = (
            new_status in self.user_allowed_status_changes[old_status]
        )
        can_change_status = (
            is_change_to_new_status_allowed
            and not has_30_days_passed_after_deadline(deadline)
        )

        if has_status_changed and not can_change_status:
            raise RESTDataError(
                f"Only curator can change status from '{old_status}' to '{new_status}'."
            )

    def get_builder_with_new_record(self, data):
        if "$schema" not in data:
            data["$schema"] = url_for(
                "invenio_jsonschemas.get_schema",
                schema_path="records/jobs.json",
                _external=True,
            )
        if not is_superuser_or_cataloger_logged_in():
            data["status"] = "pending"

        builder = JobBuilder(record=data)
        if "acquisition_source" not in builder.record:
            acquisition_source = self.get_acquisition_source()
            builder.add_acquisition_source(**acquisition_source)
        return builder

    def get_builder_with_updated_record(self, data, record):
        optional_fields = [
            "external_job_identifier",
            "accelerator_experiments",
            "urls",
            "contact_details",
            "reference_letters",
        ]

        record_data = get_updated_record_data(record, data, optional_fields)
        builder = JobBuilder(record=record_data)
        return builder

    def get_valid_record_data_from_builder(self, builder):
        try:
            builder.validate_record()
        except ValidationError as e:
            LOGGER.exception("Cannot process job submission")
            raise RESTDataError(e.args[0]) from e
        except SchemaError as e:
            LOGGER.exception("Schema is broken")
            abort(500, str(e))
        data = builder.record
        return data

    def user_can_edit(self, record):
        if is_superuser_or_cataloger_logged_in():
            return True

        orcid = get_value(record, "acquisition_source.orcid")
        if orcid:
            return orcid == self.get_user_orcid()
        return False

    def create_ticket(self, record, rt_template):
        control_number = record["control_number"]

        INSPIREHEP_URL = get_inspirehep_url()
        JOB_DETAILS = f"{INSPIREHEP_URL}/jobs/{control_number}"
        JOB_EDIT = f"{INSPIREHEP_URL}/submissions/jobs/{control_number}"

        rt_queue = "Jobs"
        requestor = record["acquisition_source"]["email"] or record[
            "acquisition_source"
        ].get("name", "UNKNOWN")
        rt_template_context = {
            "job_url": JOB_DETAILS,
            "job_url_edit": JOB_EDIT,
            "hep_url": INSPIREHEP_URL,
        }
        async_create_ticket_with_template.delay(
            rt_queue,
            requestor,
            rt_template,
            rt_template_context,
            f"Job {control_number} has been submitted to the Jobs database",
            control_number,
        )


class InstitutionSubmissionsResource(BaseSubmissionsResource):
    decorators = [login_required_with_roles([Roles.cataloger.value])]

    def load_data_from_request(self):
        return institution_loader_v1()

    def post(self):
        """Adds new Institution"""

        data = self.load_data_from_request()
        record = InstitutionsRecord(data=data).create(data)
        db.session.commit()

        return jsonify({"control_number": record["control_number"]}), 201


class JournalSubmissionsResource(BaseSubmissionsResource):
    decorators = [login_required_with_roles([Roles.cataloger.value])]

    def load_data_from_request(self):
        return journal_loader_v1()

    def post(self):
        data = self.load_data_from_request()
        record = JournalsRecord(data=data).create(data)
        db.session.commit()

        return jsonify({"control_number": record["control_number"]}), 201


author_submissions_view = AuthorSubmissionsResource.as_view("author_submissions_view")
blueprint.add_url_rule("/authors", view_func=author_submissions_view)
blueprint.add_url_rule("/authors/<int:pid_value>", view_func=author_submissions_view)

literature_submission_view = LiteratureSubmissionResource.as_view(
    "literature_submissions_view"
)
blueprint.add_url_rule("/literature", view_func=literature_submission_view)

job_submission_view = JobSubmissionsResource.as_view("job_submission_view")
blueprint.add_url_rule("/jobs", view_func=job_submission_view)
blueprint.add_url_rule(
    '/jobs/<pid(job,record_class="inspirehep.records.api.JobsRecord"):pid_value>',
    view_func=job_submission_view,
)

seminar_submission_view = SeminarSubmissionsResource.as_view("seminar_submission_view")
blueprint.add_url_rule("/seminars", view_func=seminar_submission_view)
blueprint.add_url_rule("/seminars/<int:pid_value>", view_func=seminar_submission_view)

experiment_submission_view = ExperimentSubmissionsResource.as_view(
    "experiment_submission_view"
)
blueprint.add_url_rule("/experiments", view_func=experiment_submission_view)

conference_submission_view = ConferenceSubmissionsResource.as_view(
    "conference_submissions_view"
)
blueprint.add_url_rule("/conferences", view_func=conference_submission_view)

institution_submission_view = InstitutionSubmissionsResource.as_view(
    "institution_submission_view"
)
blueprint.add_url_rule("/institutions", view_func=institution_submission_view)

journal_submission_view = JournalSubmissionsResource.as_view("journal_submission_view")
blueprint.add_url_rule("/journals", view_func=journal_submission_view)
