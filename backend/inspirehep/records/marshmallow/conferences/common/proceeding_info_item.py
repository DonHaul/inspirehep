#
# Copyright (C) 2019 CERN.
#
# inspirehep is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.
from inspirehep.records.marshmallow.literature.common import PublicationInfoItemSchemaV1
from marshmallow import Schema, fields


class ProceedingInfoItemSchemaV1(Schema):
    publication_info = fields.Nested(PublicationInfoItemSchemaV1, many=True)
    control_number = fields.Raw()
