# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
import pandas as pd
from qtpy.QtWidgets import (
    QComboBox, QDateEdit, QDateTimeEdit, QTextEdit, QSpinBox, QLineEdit,
    QDoubleSpinBox)

# ---- Local imports
from sardes.config.locale import _
from sardes.api.tabledelegates import SardesItemDelegate


# =============================================================================
# ---- Simple Delegates
# =============================================================================
class NotEditableDelegate(SardesItemDelegate):
    """
    A delegate used to indicate that the items in the associated
    column are not editable.
    """

    def __init__(self, model_view, table_column):
        super().__init__(model_view, table_column)

    def createEditor(self, *args, **kargs):
        return None

    def setEditorData(self, *args, **kargs):
        pass

    def setModelData(self, *args, **kargs):
        pass

    # ---- SardesItemDelegate API
    def get_editor_data(self, *args, **kargs):
        pass

    def set_editor_data(self, *args, **kargs):
        pass

    def format_data(self, data):
        data.values[:] = None
        return data, None


class DateTimeDelegate(SardesItemDelegate):
    """
    A delegate to edit a datetime.
    """

    def __init__(self, model_view, table_column, display_format: str = None):
        super() .__init__(model_view, table_column)
        self.display_format = ("yyyy-MM-dd hh:mm:ss" if display_format is None
                               else display_format)
        self.strftime_format = (
            self.display_format
            .replace('yyyy', '%Y')
            .replace('MM', '%m')
            .replace('dd', '%d')
            .replace('hh', '%H')
            .replace('mm', '%M')
            .replace('ss', '%S')
            )

    # ---- SardesItemDelegate API
    def create_editor(self, parent):
        editor = QDateTimeEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat(self.display_format)
        return editor

    def format_data(self, data):
        fmt = "%Y-%m-%d %H:%M:%S"
        try:
            formatted_data = pd.to_datetime(data, format=fmt)
            warning_message = None
        except ValueError:
            formatted_data = pd.to_datetime(data, format=fmt, errors='coerce')
            warning_message = _(
                "Some {} data did not match the prescribed "
                "<i>yyyy-mm-dd hh:mm:ss</i> format"
                ).format(self.model().column_header_at(data.name))
        return formatted_data, warning_message

    def logical_to_visual_data(self, visual_dataf):
        if self.strftime_format is not None:
            try:
                visual_dataf[self.table_column.name] = (
                    visual_dataf[self.table_column.name].dt.strftime(
                        self.strftime_format))
            except AttributeError as e:
                print((
                    'WARNING: Failed to format datetime values on '
                    'column "{}" of table "{}" because of the following '
                    'error :\n{}'
                    ).format(self.table_column, self.model().name(), e))


class TextEditDelegate(SardesItemDelegate):
    """
    A delegate to edit very long strings that can span over multiple lines.
    """

    def create_editor(self, parent):
        return QTextEdit(parent)


class StringEditDelegate(SardesItemDelegate):
    """
    A delegate to edit a 250 characters strings.
    """
    MAX_LENGTH = 250

    def create_editor(self, parent):
        editor = QLineEdit(parent)
        editor.setMaxLength(self.MAX_LENGTH)
        return editor


class IntEditDelegate(SardesItemDelegate):
    """
    A delegate to edit an integer value in a spin box.
    """

    def __init__(self, model_view, table_column, minimum=None, maximum=None):
        super() .__init__(model_view, table_column)
        self._minimum = minimum
        self._maximum = maximum

    # ---- SardesItemDelegate API
    def create_editor(self, parent):
        editor = QSpinBox(parent)
        if self._minimum is not None:
            editor.setMinimum(int(self._minimum))
        if self._maximum is not None:
            editor.setMaximum(int(self._maximum))
        return editor

    def format_data(self, data):
        try:
            formatted_data = pd.to_numeric(data)
            warning_message = None
        except ValueError:
            formatted_data = pd.to_numeric(data, errors='coerce')
            warning_message = _(
                "Some {} data could not be converted to integer value"
                ).format(self.model().column_header_at(data.name))
        # We need to round the data before casting them as Int64DType to
        # avoid "TypeError: cannot safely cast non-equivalent float64 to int64"
        # when the data contains float numbers.
        formatted_data = formatted_data.round().astype(pd.Int64Dtype())
        return formatted_data, warning_message


class NumEditDelegate(SardesItemDelegate):
    """
    A delegate to edit a float or a float value in a spin box.
    """

    def __init__(self, model_view, table_column, decimals=0, minimum=None,
                 maximum=None):
        super() .__init__(model_view, table_column)
        self._minimum = minimum
        self._maximum = maximum
        self._decimals = decimals

    # ---- SardesItemDelegate API
    def create_editor(self, parent):
        if self._decimals == 0:
            editor = QSpinBox(parent)
        else:
            editor = QDoubleSpinBox(parent)
            editor.setDecimals(self._decimals)
        if self._minimum is not None:
            editor.setMinimum(self._minimum)
        if self._maximum is not None:
            editor.setMaximum(self._maximum)
        return editor

    def format_data(self, data):
        try:
            formatted_data = pd.to_numeric(data).astype(float)
            warning_message = None
        except ValueError:
            formatted_data = pd.to_numeric(data, errors='coerce').astype(float)
            warning_message = _(
                "Some {} data could not be converted to numerical value"
                ).format(self.model().column_header_at(data.name))
        return formatted_data, warning_message


class BoolEditDelegate(SardesItemDelegate):
    """
    A delegate to edit a boolean value with a combobox.
    """

    # ---- SardesItemDelegate API
    def create_editor(self, parent):
        editor = QComboBox(parent)
        editor.addItem(_('Yes'), userData=True)
        editor.addItem(_('No'), userData=False)
        return editor

    def format_data(self, data):
        isnull1 = data.isnull()
        bool_map_dict = {
            _('Yes').lower(): True, 'yes': True, 'true': True, '1': True,
            _('No').lower(): False, 'no': False, 'false': False, '0': False}
        formatted_data = data.str.lower().str.strip().map(bool_map_dict.get)
        isnull2 = formatted_data.isnull()
        if sum(isnull1 != isnull2):
            warning_message = _(
                "Some {} data could notbe converted to boolean value."
                ).format(self.model().column_header_at(data.name))
        else:
            warning_message = None
        return formatted_data, warning_message

    def logical_to_visual_data(self, visual_dataf):
        visual_dataf[self.table_column.name] = (
            visual_dataf[self.table_column.name]
            .map({True: _('Yes'), False: _('No')}.get)
            )


class TriStateEditDelegate(SardesItemDelegate):
    """
    A delegate where you can chose between three states: No, Yes, and NA.
    """

    def create_editor(self, parent):
        editor = QComboBox(parent)
        editor.addItem(_('No'), userData=0)
        editor.addItem(_('Yes'), userData=1)
        editor.addItem(_('NA'), userData=2)
        return editor

    def logical_to_visual_data(self, visual_dataf):
        visual_dataf[self.table_column.name] = (
            visual_dataf[self.table_column.name]
            .map({1: _('Yes'), 0: _('No'), 2: _('NA')}.get)
            )


# =============================================================================
# ---- Complex Delegates
# =============================================================================
class GenericLibSelectDelegate(SardesItemDelegate):
    """
    A generic delegate to select an item from a library.
    """

    def __init__(self, model_view, table_column,
                 lib_name: str, lib_column_name: str):
        super() .__init__(model_view, table_column)
        self.lib_name = lib_name
        self.lib_column_name = lib_column_name

    def create_editor(self, parent):
        editor = QComboBox(parent)

        # Populate the combobox with the available brand in the library.
        lib = self.model().libraries[self.lib_name]
        lib = lib.sort_values(self.lib_column_name, axis=0, ascending=True)
        for index, values in lib.iterrows():
            editor.addItem(values[self.lib_column_name], userData=index)
        return editor

    def logical_to_visual_data(self, visual_dataf):
        try:
            lib = self.model().libraries[self.lib_name]
            visual_dataf[self.table_column.name] = (
                visual_dataf[self.table_column.name]
                .map(lib[self.lib_column_name].to_dict().get)
                )
        except KeyError:
            pass


class ObsWellIdEditDelegate(SardesItemDelegate):
    """
    A delegate to select an observation well from the list of existing well
    in the database.
    """

    # ---- SardesItemDelegate API
    def create_editor(self, parent):
        editor = QComboBox(parent)

        # Populate the combobox with the existing observation wells.
        obs_well_data = (self.model().libraries['observation_wells_data']
                         .sort_values('obs_well_id', axis=0, ascending=True))
        for index, values in obs_well_data.iterrows():
            editor.addItem(values['obs_well_id'], userData=index)

        return editor

    def format_data(self, data):
        isnull1 = data.isnull()
        try:
            obs_wells = (
                self.model().libraries['observation_wells_data'])
            obs_wells_dict = (
                obs_wells['obs_well_id']
                [obs_wells['obs_well_id'].isin(data)]
                .drop_duplicates()
                .reset_index()
                .set_index('obs_well_id')
                .to_dict()['sampling_feature_uuid'])
        except KeyError:
            obs_wells_dict = {}
        else:
            formatted_data = data.map(obs_wells_dict.get)
            isnull2 = formatted_data.isnull()
            if sum(isnull1 != isnull2):
                warning_message = _(
                    "Some {} data did not match any well in the database"
                    ).format(self.model().column_header_at(data.name))
            else:
                warning_message = None
        return formatted_data, warning_message

    def logical_to_visual_data(self, visual_dataf):
        try:
            obs_wells_data = self.model().libraries['observation_wells_data']
            visual_dataf[self.table_column.name] = (
                visual_dataf[self.table_column.name]
                .map(obs_wells_data['obs_well_id'].to_dict().get)
                )
        except KeyError:
            pass


class SondesSelectionDelegate(SardesItemDelegate):
    """
    A delegate to select a level or baro logger from the inventory.
    """

    def create_editor(self, parent):
        editor = QComboBox(parent)

        # Populate the combobox with the existing sondes.
        try:
            sondes_data = self.model().libraries['sondes_data']
            sonde_models_lib = self.model().libraries['sonde_models_lib']
        except KeyError:
            pass
        else:
            sondes_data['sonde_brand_model'] = sonde_models_lib.loc[
                sondes_data['sonde_model_id']]['sonde_brand_model'].values

            mask = sondes_data['sonde_serial_no'].notnull()
            sondes_data['sonde_brand_model_serial'] = sondes_data[
                'sonde_brand_model']
            sondes_data.loc[mask, 'sonde_brand_model_serial'] = (
                sondes_data['sonde_serial_no'] +
                ' - ' +
                sondes_data['sonde_brand_model'])

            sondes_data = sondes_data.sort_values(
                'sonde_brand_model_serial', axis=0, ascending=True)
            for index, values in sondes_data.iterrows():
                editor.addItem(
                    values['sonde_brand_model_serial'], userData=index)
        return editor

    def logical_to_visual_data(self, visual_dataf):
        """
        Transform logical data to visual data.
        """
        try:
            sondes_data = self.model().libraries['sondes_data']
            sonde_models_lib = self.model().libraries['sonde_models_lib']

            sondes_data['sonde_brand_model'] = sonde_models_lib.loc[
                sondes_data['sonde_model_id']]['sonde_brand_model'].values

            mask = sondes_data['sonde_serial_no'].notnull()
            sondes_data['sonde_brand_model_serial'] = sondes_data[
                'sonde_brand_model']
            sondes_data.loc[mask, 'sonde_brand_model_serial'] = (
                sondes_data['sonde_serial_no'] +
                ' - ' +
                sondes_data['sonde_brand_model'])

            visual_dataf['sonde_uuid'] = (
                visual_dataf['sonde_uuid']
                .map(sondes_data['sonde_brand_model_serial'].to_dict().get)
                )
        except KeyError:
            pass


class HGSurveyEditDelegate(SardesItemDelegate):
    """
    A delegate to select an hydrogeochemical survey.
    """

    def create_editor(self, parent):
        editor = QComboBox(parent)

        try:
            hg_surveys = self.model().libraries['hg_surveys']
            obswell_data = self.model().libraries['observation_wells_data']
        except KeyError:
            pass
        else:
            hg_surveys['obs_well_id'] = obswell_data.loc[
                hg_surveys['sampling_feature_uuid']
                ]['obs_well_id'].values
            hg_surveys['survey_well_datetime'] = (
                hg_surveys['obs_well_id'] +
                ' - ' +
                hg_surveys['hg_survey_datetime'].dt.strftime("%Y-%m-%d %H:%M")
                )
            hg_surveys = hg_surveys.sort_values(
                'survey_well_datetime', axis=0, ascending=True)
            for index, values in hg_surveys.iterrows():
                editor.addItem(values['survey_well_datetime'], userData=index)
        return editor

    def logical_to_visual_data(self, visual_dataf):
        try:
            hg_surveys = self.model().libraries['hg_surveys']
            obswell_data = self.model().libraries['observation_wells_data']

            hg_surveys['obs_well_id'] = obswell_data.loc[
                hg_surveys['sampling_feature_uuid']
                ]['obs_well_id'].values
            hg_surveys['survey_well_datetime'] = (
                hg_surveys['obs_well_id'] +
                ' - ' +
                hg_surveys['hg_survey_datetime'].dt.strftime("%Y-%m-%d %H:%M")
                )

            visual_dataf['hg_survey_id'] = (
                visual_dataf['hg_survey_id']
                .map(hg_surveys['survey_well_datetime'].to_dict().get)
                )
        except KeyError:
            pass
