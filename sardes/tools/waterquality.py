# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
A tool to export hydrogeochemical data in Excel format.
"""

from __future__ import annotations

# ---- Standard library imports
import os
import os.path as osp
from io import BytesIO
import tempfile

# ---- Third party imports
import pandas as pd
from PIL import Image
from qtpy.QtCore import Signal
from xlsxwriter.exceptions import FileCreateError
import xlsxwriter

# ---- Local imports
from sardes.config.main import TEMP_DIR
from sardes.config.locale import _
from sardes.config.main import CONF
from sardes.config.ospath import get_documents_logo_filename
from sardes.api.tools import SardesTool


class WaterQualityReportTool(SardesTool):
    """
    A tool to format and save hydrogeochemical data to an Excel workbook.

    This tool is meant to be installed in the 'ObsWellsTableWidget'.
    """
    NAMEFILTERS = "Excel Workbook (*.xlsx)"

    sig_report_shown = Signal(object)

    def __init__(self, table):
        super().__init__(
            table,
            name='save_hg_data_to_file',
            text=_("Water Quality Report"),
            icon='water_quality',
            tip=_("Show the water quality report for the selected "
                  "monitoring station.")
            )

    # ---- SardesTool API
    def update(self):
        pass

    def __triggered__(self):
        self._handle_show_report_request()

    def __on_current_changed__(self, index):
        sta_data = self.table.get_current_obs_well_data()
        if sta_data is None:
            self.setEnabled(False)
            return

        _hg_surveys = self.table.model().libraries['hg_surveys']
        sta_hg_surveys = _hg_surveys[
            _hg_surveys['sampling_feature_uuid'] == sta_data.name]
        if len(sta_hg_surveys) == 0:
            self.setEnabled(False)
            return

        self.setEnabled(True)

    # ---- Handlers and Callbacks
    def _handle_show_report_request(self):
        """
        Open a file dialog to allow the user to select a location
        where to save the Excel file.

        Parameters
        ----------
        filename : str
            The absolute path of the default filename that will be set in
            the file dialog.
        """
        sta_data = self.table.get_current_obs_well_data()
        if sta_data is None:
            return

        hg_surveys = self.table.model().libraries['hg_surveys']
        sta_hg_surveys = hg_surveys[
            hg_surveys['sampling_feature_uuid'] == sta_data.name]
        if len(sta_hg_surveys) == 0:
            return

        if self.table.model().db_connection_manager is None:
            return

        self.table.model().db_connection_manager.get_water_quality_data(
            sta_data.name, callback=self._open_report_in_external)

    def _open_report_in_external(self, water_quality_data):
        """
        Create and open the water quality report in an external application
        that is chosen by the OS.
        """
        if water_quality_data.empty:
            return

        # Sort data by their index.
        water_quality_data = water_quality_data.sort_index(
            ascending=True,
            axis=0,
            inplace=False,
            key=lambda index: index.str.lower().str.normalize('NFKD')
            )

        station_name = water_quality_data.attrs['station_data']['obs_well_id']
        temp_path = tempfile.mkdtemp(dir=TEMP_DIR)
        temp_filename = osp.join(
            temp_path, _("water_quality_{}.xlsx").format(station_name)
            )

        last_repere_data = (
            water_quality_data.attrs['station_repere_data']
            .sort_values(by=['end_date'], ascending=[True])
            .iloc[-1])
        ground_altitude = (
            last_repere_data['top_casing_alt'] -
            last_repere_data['casing_length'])
        is_alt_geodesic = last_repere_data['is_alt_geodesic']

        _save_hg_data_to_xlsx(
            temp_filename,
            _('Water Quality'),
            water_quality_data,
            water_quality_data.attrs['station_data'],
            ground_altitude,
            is_alt_geodesic,
            logo_filename=get_documents_logo_filename(),
            font_name=CONF.get('documents_settings', 'xlsx_font')
            )
        os.startfile(temp_filename)

        self.sig_report_shown.emit(
            water_quality_data.attrs['station_data'].name)


def _save_hg_data_to_xlsx(
        filename: str, sheetname: str, water_quality_data: pd.DataFrame,
        station_data: pd.DataFrame, ground_altitude: float,
        is_alt_geodesic: bool, logo_filename: str = None,
        font_name: str = 'Calibri'):
    """
    Save hydrogeochemical data in an excel workbook using the specified
    filename and sheetname.

    https://xlsxwriter.readthedocs.io/format.html
    """
    startrow = 1
    startcol = 1

    if not filename.endswith('.xlsx'):
        filename += '.xlsx'

    hg_datetimes = water_quality_data.columns.get_level_values(0)

    # workbook = writer.book
    workbook = xlsxwriter.Workbook(filename)
    worksheet = workbook.add_worksheet(sheetname)

    # Write the numerical data to the file.
    water_quality_data = water_quality_data.reset_index()
    water_quality_data = water_quality_data.fillna(value=' ')

    values = water_quality_data.values
    nrow, ncol = values.shape
    for row in range(nrow):
        fmt_kwargs = {
            'font_name': font_name, 'font_size': 11, 'valign': 'bottom'}

        if row == nrow - 1:
            fmt_kwargs['bottom'] = 1

        for col in range(ncol):
            if col == 0:
                fmt_kwargs['align'] = 'left'
                fmt_kwargs['left'] = 1
                fmt_kwargs['right'] = 1
            elif col % 2 == 1:
                fmt_kwargs['align'] = 'right'
                fmt_kwargs['left'] = 1
                fmt_kwargs['right'] = 0
            else:
                fmt_kwargs['align'] = 'left'
                fmt_kwargs['left'] = 0
                fmt_kwargs['right'] = 1
            worksheet.write(
                startrow + 8 + row, startcol + col, values[row, col],
                workbook.add_format(fmt_kwargs)
                )

    # Setup the columns format and width.
    values_format = workbook.add_format({
        'font_name': font_name, 'align': 'right'})
    units_format = workbook.add_format({
        'font_name': font_name, 'align': 'left'})
    worksheet.set_column(0, 0, 1.3)
    worksheet.set_column(startcol, startcol, 36.75)
    for i, val in enumerate(hg_datetimes):
        if i % 2 == 0:
            column_format = values_format
        else:
            column_format = units_format
        worksheet.set_column(
            startcol + i + 1, startcol + i + 1, 16.5, column_format)

    # Write the data header.
    worksheet.write(
        startrow + 6, startcol,
        _('Sampling Date'),
        workbook.add_format({
            'font_name': font_name, 'font_size': 11,
            'align': 'center', 'valign': 'bottom', 'bold': True,
            'top': 1, 'left': 1, 'right': 1})
        )
    worksheet.write(
        startrow + 7, startcol,
        _('Parameter'),
        workbook.add_format({
            'font_name': font_name, 'font_size': 11,
            'align': 'center', 'valign': 'bottom', 'bold': True,
            'bottom': 1, 'left': 1, 'right': 1})
        )
    for i, val in enumerate(hg_datetimes):
        if i % 2 == 0:
            worksheet.merge_range(
                startrow + 6, startcol + i + 1, startrow + 6, startcol + i + 2,
                val,
                workbook.add_format({
                    'num_format': 'yyyy-mm-dd', 'font_name': font_name,
                    'font_size': 11, 'align': 'center', 'valign': 'bottom',
                    'bold': True, 'top': 1, 'left': 1, 'right': 1})
                )
            worksheet.write(
                startrow + 7, startcol + i + 1,
                _('Value'),
                workbook.add_format({
                    'font_name': font_name, 'font_size': 11,
                    'align': 'center', 'valign': 'bottom', 'bold': True,
                    'bottom': 1, 'left': 1})
                )
        else:
            worksheet.write(
                startrow + 7, startcol + i + 1,
                _('Units'),
                workbook.add_format({
                    'font_name': font_name, 'font_size': 11,
                    'align': 'center', 'valign': 'bottom', 'bold': True,
                    'bottom': 1, 'right': 1})
                )

    # Setup the height of the rows.
    worksheet.set_default_row(15)
    header_row_height = 22
    worksheet.set_row(0, 9.75)
    worksheet.set_row(startrow, header_row_height)
    worksheet.set_row(startrow + 1, header_row_height)
    worksheet.set_row(startrow + 2, header_row_height)
    worksheet.set_row(startrow + 3, header_row_height)
    worksheet.set_row(startrow + 4, header_row_height)

    # Write the file header.
    # https://xlsxwriter.readthedocs.io/example_pandas_header_format.html

    # ---- Write Municipality
    worksheet.write(
        startrow, startcol, _('Municipality:'),
        workbook.add_format({'font_name': font_name, 'font_size': 12,
                             'bold': True, 'top': 6, 'left': 6,
                             'align': 'right', 'valign': 'vcenter'}))
    worksheet.merge_range(
        startrow, startcol + 1, startrow, startcol + 2,
        station_data['municipality'],
        workbook.add_format({'font_name': font_name, 'font_size': 12,
                             'bold': True, 'top': 6, 'right': 6,
                             'align': 'center', 'valign': 'vcenter'}))

    # ---- Write Station number
    worksheet.write(
        startrow + 1, startcol, _('Station number:'),
        workbook.add_format({'font_name': font_name, 'font_size': 12,
                             'bold': True, 'left': 6,
                             'align': 'right', 'valign': 'vcenter'}))
    worksheet.merge_range(
        startrow + 1, startcol + 1, startrow + 1, startcol + 2,
        station_data['obs_well_id'],
        workbook.add_format({'font_name': font_name, 'font_size': 12,
                             'bold': True, 'right': 6,
                             'align': 'center', 'valign': 'vcenter'}))

    # ---- Write Latitude (degrees)
    worksheet.write(
        startrow + 2, startcol, _('Latitude (degrees):'),
        workbook.add_format({
            'font_name': font_name, 'font_size': 12, 'bold': True, 'left': 6,
            'align': 'right', 'valign': 'vcenter'}))
    if pd.notnull(station_data['latitude']):
        try:
            latitude = float(station_data['latitude'])
        except (ValueError, TypeError):
            latitude = ''
    else:
        latitude = ''
    worksheet.merge_range(
        startrow + 2, startcol + 1, startrow + 2, startcol + 2,
        latitude,
        workbook.add_format({
            'font_name': font_name, 'font_size': 12, 'bold': True, 'right': 6,
            'num_format': '0.0000', 'align': 'center', 'valign': 'vcenter'}))

    # ---- Write Longitude (degrees)
    worksheet.write(
        startrow + 3, startcol, _('Longitude (degrees):'),
        workbook.add_format({
            'font_name': font_name, 'font_size': 12, 'bold': True, 'left': 6,
            'align': 'right', 'valign': 'vcenter'}))
    if pd.notnull(station_data['longitude']):
        try:
            longitude = float(station_data['longitude'])
        except (ValueError, TypeError):
            longitude = ''
    else:
        longitude = ''
    worksheet.merge_range(
        startrow + 3, startcol + 1, startrow + 3, startcol + 2, longitude,
        workbook.add_format({
            'font_name': font_name, 'font_size': 12, 'bold': True, 'right': 6,
            'num_format': '0.0000', 'align': 'center', 'valign': 'vcenter'}))

    # ---- Write Ground Altitude (degrees)
    worksheet.write(
        startrow + 4, startcol, _('Ground altitude (m MSL):'),
        workbook.add_format({'font_name': font_name, 'font_size': 12,
                             'bold': True, 'bottom': 6, 'left': 6,
                             'align': 'right', 'valign': 'vcenter'}))
    if ground_altitude is not None:
        alt_value = "{:0.2f} ({})".format(
            ground_altitude,
            _('Geodesic') if is_alt_geodesic else _('Approximate'))
    else:
        alt_value = _('Not Available')
    worksheet.merge_range(
        startrow + 4, startcol + 1, startrow + 4, startcol + 2,
        alt_value,
        workbook.add_format({'font_name': font_name, 'font_size': 12,
                             'bold': True, 'bottom': 6, 'right': 6,
                             'align': 'center', 'valign': 'vcenter'}))

    # ---- Add the logo.
    if logo_filename is not None:
        img = Image.open(logo_filename)

        width, height = img.size
        img_scale = min(250 / width, 125 / height)

        # Fill transparent background if any.
        # https://github.com/python-pillow/Pillow/issues/2609#issuecomment-313922483
        if img.mode in ('RGBA', 'LA'):
            background = Image.new(img.mode[:-1], img.size, (250, 250, 250))
            background.paste(img, img.split()[-1])
            img = background

        image_data = BytesIO()
        img.convert('RGB').save(image_data, 'JPEG', quality=100)

        worksheet.insert_image(
            startrow, startcol + 3, 'logo.jpg',
            options={'x_scale': img_scale, 'y_scale': img_scale,
                     'image_data': image_data,
                     'x_offset': 10, 'y_offset': 3}
            )

    try:
        workbook.close()
    except FileCreateError:
        raise PermissionError
