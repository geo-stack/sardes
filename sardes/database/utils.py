# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
from sqlalchemy import Column


def map_table_column_names(*sqlalchemy_tables, with_labels=True):
    """
    Create and return a dictionary that maps the name of the attributes in
    each SQLAlchemy tables with the name of the columns of the their
    corresponding table in the database.

    When 'with_labels' is True, the name of the columns are prefix with the
    name of the schema and table in the database.
    """
    columns_map = {}
    for table in sqlalchemy_tables:
        for arg in dir(table):
            column = table.__mapper__.columns.get(arg, None)
            if isinstance(column, Column):
                if with_labels:
                    key = '_'.join(
                        [column.table.schema, column.table.name, column.name])
                else:
                    key = column.name
                columns_map[key] = arg
    return columns_map


def format_sqlobject_repr(sqlobject):
    """
    Return a formatted string for the sql object.
    """
    returned_value = "<" + sqlobject.__class__.__name__ + "("
    for attr in dir(sqlobject):
        if isinstance(sqlobject.__mapper__.columns.get(attr, None), Column):
            returned_value += "{}={} ".format(attr, getattr(sqlobject, attr))
    returned_value += ">"
    return returned_value
