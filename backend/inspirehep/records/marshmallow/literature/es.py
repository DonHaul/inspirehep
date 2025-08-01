#
# Copyright (C) 2019 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

import base64
from itertools import chain

import orjson
import structlog
from flask import current_app
from inspire_utils.helpers import force_list
from inspire_utils.record import get_value
from invenio_db import db
from invenio_pidstore.models import PersistentIdentifier
from marshmallow import fields, missing, pre_dump

from inspirehep.files.api import current_s3_instance
from inspirehep.oai.utils import is_cds_set, is_cern_arxiv_set
from inspirehep.records.marshmallow.base import ElasticSearchBaseSchema
from inspirehep.records.marshmallow.literature.base import LiteratureRawSchema
from inspirehep.records.marshmallow.literature.common.abstract import AbstractSource
from inspirehep.records.marshmallow.literature.common.author import (
    AuthorsInfoSchemaForES,
    FirstAuthorSchemaV1,
    SupervisorSchema,
)
from inspirehep.records.marshmallow.literature.common.thesis_info import (
    ThesisInfoSchemaForESV1,
)
from inspirehep.records.marshmallow.literature.ui import LiteratureDetailSchema
from inspirehep.records.marshmallow.literature.utils import get_expanded_authors
from inspirehep.records.marshmallow.utils import (
    get_facet_author_name_lit_and_dat,
)
from inspirehep.records.models import RecordCitations, RecordsAuthors

LOGGER = structlog.getLogger()


class LiteratureElasticSearchSchema(ElasticSearchBaseSchema, LiteratureRawSchema):
    """Elasticsearch serialzier"""

    _oai = fields.Method("get_oai", dump_only=True)
    _ui_display = fields.Method("get_ui_display", dump_only=True)
    _expanded_authors_display = fields.Method(
        "get_expanded_authors_display", dump_only=True
    )
    _latex_us_display = fields.Method("get_latex_us_display", dump_only=True)
    _latex_eu_display = fields.Method("get_latex_eu_display", dump_only=True)
    _bibtex_display = fields.Method("get_bibtex_display", dump_only=True)
    _cv_format = fields.Method("get_cv_format", dump_only=True)
    abstracts = fields.Nested(AbstractSource, dump_only=True, many=True)
    author_count = fields.Method("get_author_count")
    authors = fields.Nested(AuthorsInfoSchemaForES, dump_only=True, many=True)
    supervisors = fields.Nested(SupervisorSchema, dump_only=True, many=True)
    first_author = fields.Nested(FirstAuthorSchemaV1, dump_only=True)
    bookautocomplete = fields.Method("get_bookautocomplete")
    earliest_date = fields.Raw(dump_only=True, default=missing)
    facet_inspire_doc_type = fields.Method("get_inspire_document_type")
    facet_author_name = fields.Method("get_facet_author_name")
    journal_title_variants = fields.Method("get_journal_title_variants")
    id_field = fields.Integer(dump_only=True, dump_to="id", attribute="control_number")
    thesis_info = fields.Nested(ThesisInfoSchemaForESV1, dump_only=True)
    referenced_authors_bais = fields.Method(
        "get_referenced_authors_bais", dump_only=True
    )
    primary_arxiv_category = fields.Method("get_primary_arxiv_category", dump_only=True)

    @staticmethod
    def get_referenced_authors_bais(record):
        recids = [
            result.author_id
            for result in db.session.query(RecordsAuthors.author_id)
            .filter(
                RecordsAuthors.id_type == "recid",
                RecordsAuthors.record_id == RecordCitations.cited_id,
                RecordCitations.citer_id == record.id,
            )
            .distinct(RecordsAuthors.author_id)
            .all()
        ]
        if not recids:
            return

        subquery = (
            db.session.query(PersistentIdentifier.object_uuid)
            .filter(
                PersistentIdentifier.pid_value.in_(recids),
                PersistentIdentifier.pid_type == "aut",
            )
            .subquery()
        )
        bais = (
            db.session.query(PersistentIdentifier.pid_value)
            .filter(
                PersistentIdentifier.object_uuid.in_(subquery),
                PersistentIdentifier.pid_provider == "bai",
            )
            .all()
        )
        return [bai[0] for bai in bais]

    def get_ui_display(self, record):
        return orjson.dumps(LiteratureDetailSchema().dump(record).data).decode("utf-8")

    def get_expanded_authors_display(self, record):
        expanded_authors = get_expanded_authors(record)
        return orjson.dumps(expanded_authors).decode("utf-8")

    def get_latex_us_display(self, record):
        from inspirehep.records.serializers.latex import latex_US

        try:
            return latex_US.latex_template().render(
                data=latex_US.dump(record), format=latex_US.format
            )
        except Exception:
            LOGGER.exception("Cannot get latex us display", record=record)
            return " "

    def get_latex_eu_display(self, record):
        from inspirehep.records.serializers.latex import latex_EU

        try:
            return latex_EU.latex_template().render(
                data=latex_EU.dump(record), format=latex_EU.format
            )
        except Exception:
            LOGGER.exception("Cannot get latex eu display", record=record)
            return " "

    def get_bibtex_display(self, record):
        from inspirehep.records.serializers.bibtex import literature_bibtex

        return literature_bibtex.serialize(None, record)

    def get_cv_format(self, record):
        from inspirehep.records.serializers.cv import literature_cv_html

        try:
            return literature_cv_html.serialize_inner(None, record)
        except Exception:
            LOGGER.exception("Cannot get cv format", record=record)
            return " "

    def get_author_count(self, record):
        """Prepares record for ``author_count`` field."""
        authors = record.get("authors", [])
        return len(authors)

    def get_inspire_document_type(self, record):
        """Prepare record for ``facet_inspire_doc_type`` field."""
        result = []

        result.extend(record.get("document_type", []))
        result.extend(record.get("publication_type", []))
        if "refereed" in record and record["refereed"]:
            result.append("published")
        return result

    def get_facet_author_name(self, record):
        return get_facet_author_name_lit_and_dat(record)

    def get_bookautocomplete(self, record):
        """prepare ```bookautocomplete`` field."""
        paths = ["imprints.date", "imprints.publisher", "isbns.value"]

        authors = force_list(record.get_value("authors.full_name", default=[]))
        titles = force_list(record.get_value("titles.title", default=[]))

        input_values = list(
            chain.from_iterable(
                force_list(record.get_value(path, default=[])) for path in paths
            )
        )
        input_values.extend(authors)
        input_values.extend(titles)
        input_values = [el for el in input_values if el]

        return {"input": input_values}

    def get_oai(self, record):
        sets = []
        if is_cds_set(record):
            sets.append(current_app.config["OAI_SET_CDS"])
        if is_cern_arxiv_set(record):
            sets.append(current_app.config["OAI_SET_CERN_ARXIV"])

        if sets:
            return {
                "id": f"oai:inspirehep.net:{record['control_number']}",
                "sets": sets,
                "updated": record.updated,
            }
        return missing

    @staticmethod
    def get_primary_arxiv_category(record):
        arxiv_categories = get_value(record, "arxiv_eprints.categories")
        if not arxiv_categories:
            return missing
        arxiv_primary_categories = {categories[0] for categories in arxiv_categories}
        return list(arxiv_primary_categories)

    @pre_dump
    def separate_authors_and_supervisors_and_populate_first_author(self, data):
        if "authors" in data:
            data["supervisors"] = [
                author
                for author in data["authors"]
                if "supervisor" in author.get("inspire_roles", [])
            ]
            data["authors"] = [
                author
                for author in data["authors"]
                if "supervisor" not in author.get("inspire_roles", [])
            ]
            if data["authors"]:
                data["first_author"] = data["authors"][0]
        return data

    def get_journal_title_variants(self, record):
        publication_infos = record.get("publication_info", [])
        result = set()
        for publication_info in publication_infos:
            journal_title = publication_info.get("journal_title")
            if journal_title:
                result.add(journal_title)
                journal_title_split = journal_title.replace(".", ". ").strip()
                result.add(journal_title_split)
        return list(result)


class LiteratureFulltextElasticSearchSchema(LiteratureElasticSearchSchema):
    """Elasticsearch fulltext serialzier"""

    documents = fields.Method("get_documents_with_fulltext")

    def get_documents_with_fulltext(self, record_data):
        documents = record_data.get("documents", [])
        for document in documents:
            if (
                not document.get("hidden")
                and document.get("filename", "").endswith("pdf")
                and document.get("fulltext")
            ) or (
                document.get("source") == "arxiv"
                and document.get("fulltext") is not False
            ):
                try:
                    key = document["key"]
                    bucket = current_s3_instance.get_bucket_for_file_key(key)
                    file_data = current_s3_instance.client.get_object(
                        Bucket=bucket, Key=key
                    )
                    mimetype = file_data.get("ContentType", "")
                    body = file_data["Body"]
                    if mimetype != "application/pdf":
                        continue
                    encoded_file = base64.b64encode(body.read()).decode("ascii")
                    document["text"] = encoded_file
                except current_s3_instance.client.exceptions.NoSuchKey:
                    LOGGER.error(
                        "File was not found for the given url",
                        document_url=document["url"],
                        record_control_number=record_data["control_number"],
                    )
                    continue
        return documents
