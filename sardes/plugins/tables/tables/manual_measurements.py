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
    A tool to append the content on the clipboard to the manual measurements
    table.
    """

    def __init__(self, parent):
        super().__init__(
            parent,
            name='import_from_clipboard',
            text=_('Import from Clipboard'),
            icon='import_clipboard',
            tip=_('Add content on the Clipboard to this table.')
            )

    def __triggered__(self):
        new_data = pd.read_clipboard(sep='\t', dtype='str', header=None)

        table_visible_columns = self.parent.tableview.visible_columns()

        data_columns_mapper = self.parent.model()._data_columns_mapper
        table_visible_labels = [
            data_columns_mapper[column].lower().replace(' ', '')
            for column in table_visible_columns]

        new_data_columns = []
        for i in range(len(new_data.columns)):
            new_data_i = new_data.iat[0, i].lower().replace(' ', '')
            if new_data_i in table_visible_columns:
                new_data_columns.append(new_data_i)
            elif new_data_i in table_visible_labels:
                index = table_visible_labels.index(new_data_i)
                new_data_columns.append(table_visible_columns[index])
            else:
                new_data_columns = (
                    table_visible_columns[:len(new_data.columns)])
                break
        else:
            # This means that the headers were correctly provided in
            # the copied data. We then need to drop the first row of the data.
            new_data.drop(new_data.index[0], axis='index', inplace=True)
        new_data.columns = new_data_columns

        warning_messages = []
        for column in new_data.columns:
            if column in 'datetime':
                try:
                    new_data['datetime'] = pd.to_datetime(
                        new_data['datetime'], format="%Y-%m-%d %H:%M:%S")
                except ValueError:
                    warning_messages.append(_(
                        "Some date time data did not match the prescribed "
                        "<i>yyyy-mm-dd hh:mm:ss</i> format"))
                    new_data['datetime'] = pd.to_datetime(
                        new_data['datetime'],
                        format="%Y-%m-%d %H:%M:%S",
                        errors='coerce')
            elif column == 'value':
                try:
                    new_data['value'] = pd.to_numeric(new_data['value'])
                except ValueError:
                    warning_messages.append(_(
                        "Some water level manual measurement data could not "
                        "be converted to numerical value"))
                    new_data['value'] = pd.to_numeric(
                        new_data['value'], errors='coerce')
            elif column == 'sampling_feature_uuid':
                isnull1 = new_data['sampling_feature_uuid'].isnull()
                try:
                    obs_wells = (
                        self.parent.model().libraries['observation_wells_data']
                        )
                    obs_wells_dict = (
                        obs_wells['obs_well_id']
                        [obs_wells['obs_well_id'].isin(
                            new_data['sampling_feature_uuid'])]
                        .drop_duplicates()
                        .reset_index()
                        .set_index('obs_well_id')
                        .to_dict()['sampling_feature_uuid']
                        )
                    new_data['sampling_feature_uuid'] = (
                        new_data['sampling_feature_uuid']
                        .map(obs_wells_dict.get)
                        )
                except KeyError:
                    pass
                else:
                    isnull2 = new_data['sampling_feature_uuid'].isnull()
                    if sum(isnull1 != isnull2):
                        warning_messages.append(_(
                            "Some well ID data did not match any well "
                            "in the database"))
        values = new_data.to_dict(orient='records')

        if values != [{'sampling_feature_uuid': None}]:
            self.parent.tableview._append_row(values)
            if len(warning_messages):
                formatted_message = _(
                    "The following error(s) occurred while adding the "
                    "content on the Clipboard to this table:")
                formatted_message += (
                    '<ul style="margin-left:-30px"><li>{}.</li></ul>'.format(
                        ';</li><li>'.join(warning_messages)))
                self.parent.show_message(
                    title=_("Import from Clipboard warning"),
                    message=formatted_message,
                    func='warning')
        else:
            # This means that the Clipboard doesn't contain any valid data
            # to add to this table.
            self.parent.show_message(
                title=_("Import from Clipboard warning"),
                message=_("The Clipboard does not contain any valid data "
                          "to add to this table."),
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
