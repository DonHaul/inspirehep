#
# Copyright (C) 2019 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.


from marshmallow import fields

from inspirehep.records.marshmallow.base import RecordBaseSchema


class JournalsRawSchema(RecordBaseSchema):
    number_of_papers = fields.Raw()


# Fields that are needed to be indexed but exluded from API responses
FIELDS_TO_EXCLUDE = ["title_suggest"]


class JournalsAdminSchema(JournalsRawSchema):
    class Meta:
        exclude = FIELDS_TO_EXCLUDE


class JournalsPublicSchema(JournalsRawSchema):
    class Meta:
        exclude = FIELDS_TO_EXCLUDE + ["_private_notes", "_collections"]


class JournalsPublicListSchema(JournalsRawSchema):
    class Meta:
        exclude = FIELDS_TO_EXCLUDE + ["_private_notes", "_collections"]
