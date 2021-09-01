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
class DateEditDelegate(SardesItemDelegate):
    """
    A delegate to edit a date.
    """

    def create_editor(self, parent):
        editor = QDateEdit(parent)
        editor.setCalendarPopup(True)
        editor.setDisplayFormat("yyyy-MM-dd")
        return editor


class DateTimeDelegate(SardesItemDelegate):
    """
    A delegate to edit a datetime.
    """

    def __init__(self, model_view, display_format=None, is_required=False):
        super() .__init__(model_view, is_required=is_required)
        self.display_format = ("yyyy-MM-dd hh:mm:ss" if display_format is None
                               else display_format)

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

    def validate_edits(self):
        return self.validate_unique_constaint()


class IntEditDelegate(SardesItemDelegate):
    """
    A delegate to edit an integer value in a spin box.
    """

    def __init__(self, model_view, bottom=None, top=None,
                 unique_constraint=False):
        super() .__init__(model_view, unique_constraint=unique_constraint)
        self._bottom = bottom
        self._top = top

    # ---- SardesItemDelegate API
    def create_editor(self, parent):
        editor = QSpinBox(parent)
        if self._bottom is not None:
            editor.setMinimum(int(self._bottom))
        if self._top is not None:
            editor.setMaximum(int(self._top))
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

    def __init__(self, model_view, decimals=0, bottom=None, top=None,
                 unique_constraint=False, is_required=False):
        super() .__init__(model_view, unique_constraint=unique_constraint,
                          is_required=is_required)
        self._bottom = bottom
        self._top = top
        self._decimals = decimals

    # ---- SardesItemDelegate API
    def create_editor(self, parent):
        if self._decimals == 0:
            editor = QSpinBox(parent)
        else:
            editor = QDoubleSpinBox(parent)
            editor.setDecimals(self._decimals)
        if self._bottom is not None:
            editor.setMinimum(self._bottom)
        if self._top is not None:
            editor.setMaximum(self._top)
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


# =============================================================================
# ---- Complex Delegates
# =============================================================================
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


class SondeModelEditDelegate(SardesItemDelegate):
    """
    A delegate to select the brand of a sonde from a predefined list.
    """

    def create_editor(self, parent):
        editor = QComboBox(parent)

        # Populate the combobox with the available brand in the library.
        sonde_models_lib = self.model().libraries['sonde_models_lib']
        sonde_models_lib = sonde_models_lib.sort_values(
            'sonde_brand_model', axis=0, ascending=True)
        for index, values in sonde_models_lib.iterrows():
            editor.addItem(values['sonde_brand_model'], userData=index)
        return editor


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
            sondes_data['sonde_brand_model_serial'] = (
                sondes_data[['sonde_brand_model', 'sonde_serial_no']]
                .apply(lambda x: ' - '.join(x), axis=1))
            sondes_data = sondes_data.sort_values(
                'sonde_brand_model_serial', axis=0, ascending=True)
            for index, values in sondes_data.iterrows():
                editor.addItem(
                    values['sonde_brand_model_serial'], userData=index)
        return editor
