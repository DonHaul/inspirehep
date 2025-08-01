#
# Copyright (C) 2021 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.


from inspirehep.records.api import AuthorsRecord
from inspirehep.records.api.conferences import ConferencesRecord
from inspirehep.records.api.literature import LiteratureRecord


def get_references_to_update(record):
    uuids_to_reindex = set()
    if isinstance(record, LiteratureRecord):
        uuids_to_reindex |= record.get_linked_papers_if_reference_changed()
        uuids_to_reindex |= record.get_linked_datas_if_authors_changed()
        uuids_to_reindex |= record.get_all_connected_records_uuids_of_modified_authors()
        uuids_to_reindex |= (
            record.get_all_connected_records_uuids_of_modified_collaborations()
        )
    if isinstance(record, AuthorsRecord):
        uuids_to_reindex |= (
            record.get_linked_author_records_uuids_if_author_changed_name()
        )
        uuids_to_reindex |= record.get_linked_advisors_when_name_changes()
        uuids_to_reindex |= record.get_linked_author_paper_uuids_if_author_changed_bai()

    if isinstance(record, ConferencesRecord):
        uuids_to_reindex |= (
            record.get_linked_literature_record_uuids_if_conference_title_changed()
        )
    return uuids_to_reindex
