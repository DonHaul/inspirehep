#
# Copyright (C) 2019 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

import orjson
from flask import current_app, request
from inspire_dojson.utils import get_recid_from_ref, get_record_ref
from inspire_utils.date import format_date
from inspire_utils.record import get_value, get_values_for_schema
from marshmallow import fields, missing, pre_dump

from inspirehep.accounts.api import (
    check_permissions_for_private_collection_read_write,
    is_user_logged_in,
)
from inspirehep.assign.utils import can_claim, is_assign_view_enabled
from inspirehep.files.api import current_s3_instance
from inspirehep.records.marshmallow.base import EnvelopeSchema
from inspirehep.records.marshmallow.common import AcceleratorExperimentSchemaV1
from inspirehep.records.marshmallow.common.mixins import (
    CanEditByCollectionPermissionMixin,
)
from inspirehep.records.marshmallow.fields import ListWithLimit, NonHiddenNested
from inspirehep.records.marshmallow.literature.base import LiteraturePublicSchema
from inspirehep.records.marshmallow.literature.common import (
    AuthorSchemaV1,
    CollaborationSchemaV1,
    CollaborationWithSuffixSchemaV1,
    ConferenceInfoItemSchemaV1,
    DOISchemaV1,
    ExternalSystemIdentifierSchemaV1,
    IsbnSchemaV1,
    PublicationInfoItemSchemaV1,
    ThesisInfoSchemaV1,
)
from inspirehep.records.marshmallow.literature.pdg_identifiers_latex import (
    PDG_IDS_TO_LATEX_DESCRIPTION_MAPPING,
)
from inspirehep.records.marshmallow.literature.utils import (
    get_authors_without_emails,
    get_pages,
    get_parent_records,
)
from inspirehep.records.utils import get_literature_earliest_date
from inspirehep.utils import get_inspirehep_url

DATASET_SCHEMA_TO_URL_PREFIX_MAP = {
    "hepdata": "https://www.hepdata.net/record/",
}
DATASET_SCHEMA_TO_DESCRIPTION_MAP = {"hepdata": "HEPData"}


class LiteratureDetailSchema(
    CanEditByCollectionPermissionMixin, LiteraturePublicSchema
):
    """Schema for Literature records to displayed on UI"""

    class Meta:
        exclude = LiteraturePublicSchema.Meta.exclude + [
            "$schema",
            "copyright",
            "citations_by_year",
            "can_edit",
            "citeable",
            "core",
            "curated",
            "editions",
            "energy_ranges",
            "funding_info",
            "legacy_creation_date",
            "legacy_version",
            "publication_type",
            "record_affiliations",
            "refereed",
            "references",
            "withdrawn",
            "first_author",
        ]

    accelerator_experiments = fields.Nested(
        AcceleratorExperimentSchemaV1, dump_only=True, many=True
    )
    authors = ListWithLimit(fields.Nested(AuthorSchemaV1, dump_only=True), limit=10)
    collaborations = fields.List(
        fields.Nested(CollaborationSchemaV1, dump_only=True), attribute="collaborations"
    )
    citation_pdf_urls = fields.Method("get_citation_pdf_urls")
    collaborations_with_suffix = fields.List(
        fields.Nested(CollaborationWithSuffixSchemaV1, dump_only=True),
        attribute="collaborations",
    )
    conference_info = fields.Nested(
        ConferenceInfoItemSchemaV1,
        dump_only=True,
        attribute="publication_info",
        many=True,
    )
    date = fields.Method("get_formatted_earliest_date")
    is_collection_hidden = fields.Method("get_is_collection_hidden")
    dois = fields.Nested(DOISchemaV1, dump_only=True, many=True)
    documents = fields.Method("get_documents_without_fulltext")
    external_system_identifiers = fields.Nested(
        ExternalSystemIdentifierSchemaV1, dump_only=True, many=True
    )
    fulltext_links = fields.Method("get_fulltext_links", dump_only=True)
    isbns = fields.List(fields.Nested(IsbnSchemaV1, dump_only=True))
    linked_books = fields.Method(
        "get_linked_books", dump_only=True, attribute="publication_info"
    )
    number_of_authors = fields.Method("get_number_of_authors")
    number_of_references = fields.Method("get_number_of_references")
    publication_info = NonHiddenNested(
        PublicationInfoItemSchemaV1, dump_only=True, many=True
    )
    thesis_info = fields.Nested(ThesisInfoSchemaV1, dump_only=True)
    dataset_links = fields.Method("get_datasets")
    pdg_keywords = fields.Method("get_pdg_keywords", dump_only=True)
    keywords = fields.Method("get_keywords", dump_only=True)

    def get_is_collection_hidden(self, data):
        collections = data.get("_collections")
        if not collections:
            return missing
        return "Literature" not in collections

    def get_formatted_earliest_date(self, data):
        earliest_date = (
            data.earliest_date
            if hasattr(data, "earliest_date")
            else get_literature_earliest_date(data)
        )
        if earliest_date is None:
            return missing
        return format_date(earliest_date)

    def get_fulltext_links(self, data):
        field_data = []
        fields_to_include = {
            "arxiv_eprints": self.get_arxiv_fulltext_link,
            "external_system_identifiers": self.get_kek_fulltext_link,
            "documents": self.get_internal_fulltext_link,
        }
        for field, process_method in fields_to_include.items():
            for item in data.get(field, []):
                field_data.append(process_method(item))
        return field_data

    def get_kek_fulltext_link(self, data):
        description = "KEK scanned document"
        kek_id = data.get("value")
        if kek_id and data.get("schema", "") == "KEKSCAN":
            return {
                "description": description,
                "value": ExternalSystemIdentifierSchemaV1.get_link_for_kekscan_schema(
                    kek_id
                ),
            }
        return missing

    def get_arxiv_fulltext_link(self, data):
        description = "arXiv"
        arxiv_id = data.get("value")
        if arxiv_id:
            return {
                "description": description,
                "value": f"https://arxiv.org/pdf/{arxiv_id}",
            }
        return missing

    def get_internal_fulltext_link(self, document):
        if not current_app.config.get("FEATURE_FLAG_ENABLE_FILES"):
            return missing
        description = document.get("description") or "fulltext"
        url = document.get("url")
        if url and not self.is_document_hidden(document):
            return {"description": description, "value": url}
        return missing

    def get_number_of_authors(self, data):
        authors = data.get("authors")
        return self.get_len_or_missing(authors)

    def get_number_of_references(self, data):
        number_of_references = data.get("number_of_references")
        if number_of_references is not None:
            return number_of_references

        references = data.get("references")
        return self.get_len_or_missing(references)

    def get_linked_books(self, data):
        parents = get_parent_records(data)
        pages = get_pages(data)

        records = [
            {
                **parent["titles"][0],
                "record": get_record_ref(parent["control_number"], "literature"),
            }
            for parent in parents
            if parent and "titles" in parent and "control_number" in parent
        ]
        merged_list = [
            {"page_start": start, "page_end": end, **record}
            for start, end, record in zip(
                pages["page_start"], pages["page_end"], records, strict=False
            )
        ]

        return merged_list or None

    @staticmethod
    def get_len_or_missing(maybe_none_list):
        if maybe_none_list is None:
            return missing
        return len(maybe_none_list)

    @pre_dump
    def add_ads_links_for_arxiv_papers(self, data):
        arxiv_id = get_value(data, "arxiv_eprints[0].value")

        external_system_ids = get_value(data, "external_system_identifiers", default=[])
        ads_ids = get_values_for_schema(external_system_ids, "ADS")

        if arxiv_id and not ads_ids:
            external_system_ids.append({"schema": "ADS", "value": f"arXiv:{arxiv_id}"})
            data["external_system_identifiers"] = external_system_ids

        return data

    @staticmethod
    def is_document_hidden(document):
        return document.get("hidden", False)

    @staticmethod
    def is_document_local(document):
        return current_s3_instance.is_public_url(document["url"])

    def get_citation_pdf_urls(self, data):
        urls = []
        for document in data.get("documents", []):
            url = document.get("url")
            if (
                url
                and not self.is_document_hidden(document)
                and self.is_document_local(document)
            ):
                urls.append(url)
        return urls or missing

    def get_datasets(self, data):
        if current_app.config.get("FEATURE_FLAG_ENABLE_LITERATURE_DATA_LINKS"):
            return self.get_datasets_from_data_links(data)

        dataset_links = []
        all_links = get_value(data, "external_system_identifiers", [])
        for link in all_links:
            link_schema = link["schema"].lower()
            if link_schema in DATASET_SCHEMA_TO_URL_PREFIX_MAP:
                dataset_url = (
                    DATASET_SCHEMA_TO_URL_PREFIX_MAP[link_schema] + link["value"]
                )
                dataset_description = DATASET_SCHEMA_TO_DESCRIPTION_MAP[link_schema]
                dataset_links.append(
                    {"value": dataset_url, "description": dataset_description}
                )
        return dataset_links or missing

    def get_datasets_from_data_links(self, data):
        inspirehep_url = get_inspirehep_url()
        dataset_links = []
        all_links = get_value(data, "data", [])
        for link in all_links:
            data_control_number = get_recid_from_ref(link.get("record"))
            data_ui_link = f"{inspirehep_url}/data/{data_control_number}"
            dataset_links.append(
                {"value": data_ui_link, "description": data_control_number}
            )
        return dataset_links or missing

    def get_documents_without_fulltext(self, data):
        documents = data.get("documents", [])
        for document in documents:
            if "attachment" in document:
                del document["attachment"]
            if "text" in document:
                del document["text"]
            if "_error" in document:
                del document["_error"]
        return documents

    def get_pdg_keywords(self, data):
        keywords = data.get("keywords", [])
        pdg_keywords = []

        for keyword_entry in keywords:
            if keyword_entry.get("schema") != "PDG":
                continue
            pdg_identifier = keyword_entry["value"]
            pdg_keywords.append(
                {
                    "value": pdg_identifier,
                    "description": PDG_IDS_TO_LATEX_DESCRIPTION_MAPPING[pdg_identifier],
                }
            )

        return pdg_keywords

    def get_keywords(self, data):
        keywords = data.get("keywords", [])
        keywords_without_pdg = []

        for keyword_entry in keywords:
            if keyword_entry.get("schema") != "PDG":
                keywords_without_pdg.append(keyword_entry)

        return keywords_without_pdg


class LiteratureListWrappedSchema(EnvelopeSchema):
    """Special case for SearchUI.

    We index a stringified JSON and we have to transform it to JSON again.
    """

    metadata = fields.Method("get_ui_display", dump_only=True)

    def get_ui_display(self, data):
        try:
            ui_display = orjson.loads(get_value(data, "metadata._ui_display", ""))
            collections = get_value(data, "metadata._collections", "")
            if "fulltext_highlight" in data.get("metadata", {}):
                ui_display["fulltext_highlight"] = data["metadata"][
                    "fulltext_highlight"
                ]
            if is_user_logged_in():
                ui_display["curated_relation"] = get_value(
                    data, "metadata.curated_relation", False
                )
            if (
                is_user_logged_in()
                and check_permissions_for_private_collection_read_write(collections)
            ):
                ui_display["can_edit"] = True
            if ui_display.get("authors"):
                ui_display.update({"authors": get_authors_without_emails(ui_display)})
            if is_assign_view_enabled():
                author_recid = request.values.get("author", type=str).split("_")[0]
                if can_claim(ui_display, author_recid):
                    ui_display["can_claim"] = True
            acquisition_source = ui_display.get("acquisition_source")
            if acquisition_source and "email" in acquisition_source:
                del acquisition_source["email"]
                ui_display.update({"acquisition_source": acquisition_source})
            return ui_display
        except orjson.JSONDecodeError:
            return {}
