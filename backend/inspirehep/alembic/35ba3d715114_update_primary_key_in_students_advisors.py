#
# This file is part of Invenio.
# Copyright (C) 2016-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""update primary key in students advisors
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "35ba3d715114"
down_revision = "0ae62076ae0c"
branch_labels = ()
depends_on = None


def upgrade():
    """Upgrade database."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint("pk_students_advisors", "students_advisors", type_="primary")
    op.add_column(
        "students_advisors",
        sa.Column(
            "id", sa.Integer(), nullable=False, primary_key=True, autoincrement=True
        ),
    )
    op.create_primary_key("pk_students_advisors", "students_advisors", ["id"])


def downgrade():
    """Downgrade database."""
    op.drop_column("students_advisors", "id")
    op.create_primary_key(
        "pk_students_advisors", "students_advisors", ["advisor_id", "student_id"]
    )