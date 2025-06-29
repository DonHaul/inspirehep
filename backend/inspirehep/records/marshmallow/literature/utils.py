#
# Copyright (C) 2019 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

import re

from pylatexenc.latexencode import (
    RULE_DICT,
    UnicodeToLatexConversionRule,
    UnicodeToLatexEncoder,
)

from inspirehep.records.api import InspireRecord

# The regex selects math delimited by ``$...$`` or ``\(...\)``
# where the delimiters are not escaped
MATH_EXPRESSION_REGEX = re.compile(r"((?<!\\)\$.*?(?<!\\)\$|(?<!\\)\\\(.*?(?<!\\)\\\))")


def get_pages(data):
    pub_info = InspireRecord.get_value(data, "publication_info")
    page_start_list = []
    page_end_list = []

    if pub_info:
        for entry in pub_info:
            if "parent_record" in entry:
                page_start_list.append(entry.get("page_start", None))
                page_end_list.append(entry.get("page_end", None))

    return {"page_start": page_start_list, "page_end": page_end_list}


def get_parent_records(data):
    record = InspireRecord(data)
    linked_pids_order = [
        pid
        for _, pid in record.get_linked_pids_from_field(
            "publication_info.parent_record"
        )
    ]
    book_records = list(
        InspireRecord.get_linked_records_from_dict_field(
            data, "publication_info.parent_record"
        )
    )

    return sorted(
        book_records,
        key=lambda rec: linked_pids_order.index(str(rec["control_number"])),
    )


def get_parent_record(data):
    if data.get("doc_type") == "inproceedings":
        conference_records = InspireRecord.get_linked_records_from_dict_field(
            data, "publication_info.conference_record"
        )
        conference_record = next(conference_records, {})
        return conference_record

    book_records = InspireRecord.get_linked_records_from_dict_field(
        data, "publication_info.parent_record"
    )
    return next(book_records, {})


def latex_encode(text, contains_math=False):
    """Encode a string for use in a LaTeX format.

    Args:
        contains_math (bool): when True, math environments delimited by $...$
        or \\(...\\) are preserved to avoid double escaping. Note that $$...$$
        is not handled.
    """
    if text is None:
        return None

    conversion_rules = [
        UnicodeToLatexConversionRule(RULE_DICT, {ord("{"): "{", ord("}"): "}"}),
        "defaults",
    ]

    encode = UnicodeToLatexEncoder(
        replacement_latex_protection="braces-almost-all",
        conversion_rules=conversion_rules,
    ).unicode_to_latex

    if not (contains_math and ("$" in text or r"\(" in text)):
        return encode(text)

    parts = MATH_EXPRESSION_REGEX.split(text)
    encoded_text = "".join(
        encode(part) if i % 2 == 0 else part for i, part in enumerate(parts)
    )

    return encoded_text


def get_authors_without_emails(data):
    updated_authors = []
    authors = data.get("authors", [])
    for author in authors:
        if "emails" in author:
            del author["emails"]
        updated_authors.append(author)
    return updated_authors
