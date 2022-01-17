# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Local imports
from sardes.config.locale import _


class SardesTableEditError(object):
    """
    Basic functionality for Sardes data edit error.
    """

    def error_iloc(self, tableview):
        raise NotImplementedError

    def error_message(self, tableview):
        raise NotImplementedError


class NotNullTableEditError(SardesTableEditError):
    def __init__(self, index, column):
        self.index = index
        self.column = column

    def error_iloc(self, tableview):
        row = tableview.model()._proxy_dataf_index.get_loc(self.index)
        col = tableview.model().columns().index(self.column)
        return row, col

    def error_message(self, tableview):
        row = tableview.model()._proxy_dataf_index.get_loc(self.index) + 1
        column = tableview.model().column_at(self.column.name)
        return _(
            '<p>The value in column <b>{}</b> and <b>row {}</b> '
            'cannot be Null.</p>'
            ).format(column.header, row)


class UniqueTableEditError(SardesTableEditError):
    def __init__(self, index, column):
        self.index = index
        self.column = column

    def error_iloc(self, tableview):
        row = tableview.model()._proxy_dataf_index.get_loc(self.index)
        col = tableview.model().columns().index(self.column)
        return row, col

    def error_message(self, tableview):
        row = tableview.model()._proxy_dataf_index.get_loc(self.index) + 1
        column_subset = [tableview.model().column_at(col) for
                         col in self.column.unique_subset]

        if not len(column_subset):
            return _(
                "<p>The value in column <b>{column}</b> and "
                "<b>row {row}</b> violates unique constraint.</p>"
                "<p>Please use a value that does not already exist.</p>"
                ).format(row=row, column=self.column.header)
        elif len(column_subset) == 1:
            return _(
                "<p>On <b>row {}</b>, the combination of values in "
                "columns <b>{}</b> and <b>{}</b> violates unique "
                "constraint.</p>"
                "<p>Please use a combination of values that does not "
                "already exist.</p>"
                ).format(row, self.column.header, column_subset[0].header)
        else:
            colstr = "<b>{}</b>".format(self.column.header)
            for column in column_subset[:-1]:
                colstr += ", <b>{}</b>".format(column.header)
            colstr += _(", and")
            colstr += " <b>{}</b>".format(column_subset[-1].header)
            return _(
                "<p>On <b>row {}</b>, the combination of values in "
                "columns {} violates unique constraint.</p>"
                "<p>Please use a combination of values that does not "
                "already exist.</p>"
                ).format(row, colstr)


class ForeignTableEditError(SardesTableEditError):
    def __init__(self, parent_index, foreign_column, foreign_table_model):
        self.parent_index = parent_index
        self.foreign_column = foreign_column
        self.foreign_table_model = foreign_table_model

    def error_iloc(self, tableview):
        row = tableview.model()._proxy_dataf_index.get_loc(self.parent_index)
        col = 0
        return row, col

    def error_message(self, tableview):
        row = (tableview.model()._proxy_dataf_index
               .get_loc(self.parent_index) + 1)
        return _(
            "<p>Deleting the item on <b>row {row}</b> violates foreign key "
            "constraint on column <b>{foreign_column}</b> of table "
            "<b>{foreign_table}</b>.</p>"
            "<p>Please first delete all rows still referencing this "
            "item in table <b>{foreign_table}</b>.</p>"
            ).format(row=row,
                     foreign_column=self.foreign_column.header,
                     foreign_table=self.foreign_table_model.title())


class ForeignReadingsConstraintError(SardesTableEditError):
    def __init__(self, parent_index):
        self.parent_index = parent_index

    def error_iloc(self, tableview):
        row = tableview.model()._proxy_dataf_index.get_loc(self.parent_index)
        col = 0
        return row, col

    def error_message(self, tableview):
        row = (tableview.model()._proxy_dataf_index
               .get_loc(self.parent_index) + 1)
        station_name = tableview.model()._datat.data.loc[
            self.parent_index]['obs_well_id']
        return _(
            "<p>Station <b>{station_name}</b> on <b>row {row}</b> "
            "cannot be deleted because there is still readings data "
            "related to that station in the database.</p>"
            "<p>Please first delete all readings data related to "
            "station <b>{station_name}</b>."
            ).format(row=row, station_name=station_name)
