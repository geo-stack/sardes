# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Thid party imports
import pandas as pd

# ---- Local imports
from sardes.api.tablemodels import SardesTableModel
from sardes.config.locale import _
from sardes.widgets.tableviews import (
    SardesTableWidget, TextEditDelegate, NotEditableDelegate, DateTimeDelegate,
    NumEditDelegate)
from sardes.plugins.tables.tables.delegates import ObsWellIdEditDelegate
from sardes.api.tools import SardesTool


class ImportFromClipboardTool(SardesTool):
    """
    A tool to append the Clipboard contents to the manual measurements table.
    """

    def __init__(self, parent):
        super().__init__(
            parent,
            name='import_from_clipboard',
            text=_('Import from Clipboard'),
            icon='import_clipboard',
            tip=_('Add the Clipboard contents to this table.')
            )

    def __triggered__(self):
        new_data = pd.read_clipboard(sep='\t', dtype='str', header=None)
        if new_data.empty:
            self.parent.show_message(
                title=_("Import from Clipboard warning"),
                message=_("Nothing was added to the table because the "
                          "Clipboard was empty."),
                func='warning')
            return

        table_visible_columns = self.parent.tableview.visible_columns()
        if len(new_data.columns) > len(table_visible_columns):
            self.parent.show_message(
                title=_("Import from Clipboard warning"),
                message=_("The Clipboard contents cannot be added to "
                          "the table because the number of columns of the "
                          "copied data is too large."),
                func='warning')
            return

        data_columns_mapper = self.parent.model()._data_columns_mapper
        table_visible_labels = [
            data_columns_mapper[column].lower().replace(' ', '')
            for column in table_visible_columns]

        new_data_columns = []
        for i in range(len(new_data.columns)):
            print(str(new_data.iat[0, i]))
            new_data_i = (
                '' if pd.isnull(new_data.iat[0, i]) else new_data.iat[0, i]
                ).lower().replace(' ', '')
            if new_data_i in table_visible_columns:
                new_data_columns.append(new_data_i)
            elif new_data_i in table_visible_labels:
                index = table_visible_labels.index(new_data_i)
                new_data_columns.append(table_visible_columns[index])
            else:
                break
        if len(new_data.columns) == len(set(new_data_columns)):
            # This means that the headers were correctly provided in
            # the copied data. We then need to drop the first row of the data.
            new_data.drop(new_data.index[0], axis='index', inplace=True)
        else:
            # This means that there was a problem reading the columns name or
            # that the columns names were not provided with the imported data.
            new_data_columns = table_visible_columns[:len(new_data.columns)]
        new_data.columns = new_data_columns

        warning_messages = []
        for column in new_data.columns:
            delegate = self.parent.tableview.itemDelegateForColumn(
                self.parent.model().columns.index(column))
            new_data[column], warning_message = delegate.format_data(
                new_data[column])
            if warning_message is not None:
                warning_messages.append(warning_message)

        formatted_message = None
        if new_data.isnull().values.flatten().all():
            formatted_message = _(
                "Nothing was added to the table because the Clipboard "
                "did not contain any valid data.")
            if new_data.size > 1 and len(warning_messages):
                formatted_message += "<br><br>"
                formatted_message += _(
                    "The following error(s) occurred while trying to add the "
                    "Clipboard contents to this table:")
                formatted_message += (
                    '<ul style="margin-left:-30px"><li>{}.</li></ul>'.format(
                        ';</li><li>'.join(warning_messages)))
        else:
            values = new_data.to_dict(orient='records')
            self.parent.tableview._append_row(values)
            if len(warning_messages):
                formatted_message = _(
                    "The following error(s) occurred while adding the "
                    "Clipboard contents to this table:")
                formatted_message += (
                    '<ul style="margin-left:-30px"><li>{}.</li></ul>'.format(
                        ';</li><li>'.join(warning_messages)))
        if formatted_message is not None:
            self.parent.show_message(
                title=_("Import from Clipboard warning"),
                message=formatted_message,
                func='warning')


class ManualMeasurementsTableModel(SardesTableModel):
    """
    A table model to display the list of manual groundwater level measurements
    made in the observation wells of the monitoring network.
    """

    def create_delegate_for_column(self, view, column):
        """
        Create the item delegate that the view need to use when editing the
        data of this model for the specified column. If None is returned,
        the items of the column will not be editable.
        """
        if column == 'sampling_feature_uuid':
            return ObsWellIdEditDelegate(view)
        elif column == 'datetime':
            return DateTimeDelegate(view, display_format="yyyy-MM-dd hh:mm")
        elif column == 'value':
            return NumEditDelegate(view, decimals=3, bottom=-99999, top=99999)
        elif column == 'notes':
            return TextEditDelegate(view)
        else:
            return NotEditableDelegate(view)

    # ---- Visual Data
    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.
        """
        try:
            obs_wells_data = self.libraries['observation_wells_data']
            visual_dataf['sampling_feature_uuid'] = (
                visual_dataf['sampling_feature_uuid']
                .map(obs_wells_data['obs_well_id'].to_dict().get)
                )
        except KeyError:
            pass
        visual_dataf['datetime'] = (visual_dataf['datetime']
                                    .dt.strftime('%Y-%m-%d %H:%M'))
        return visual_dataf


class ManualMeasurementsTableWidget(SardesTableWidget):
    def __init__(self, *args, **kargs):
        table_model = ManualMeasurementsTableModel(
            table_title=_('Manual Measurements'),
            table_id='table_manual_measurements',
            data_columns_mapper=[
                ('sampling_feature_uuid', _('Well ID')),
                ('datetime', _('Date/Time')),
                ('value', _('Water Level')),
                ('notes', _('Notes'))]
            )
        super().__init__(table_model, *args, **kargs)

        # Add the tool to import data from the clipboard.
        self.install_tool(
            ImportFromClipboardTool(self), after='copy_to_clipboard')
