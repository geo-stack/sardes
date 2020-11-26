# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------


# ---- Standard library imports

import os
import os.path as osp
from io import BytesIO

# ---- Third party imports
import pandas as pd
from PIL import Image
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QFileDialog, QMessageBox
from xlsxwriter.exceptions import FileCreateError

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.config.locale import _
from sardes.config.main import CONF
from sardes.config.ospath import (
    get_select_file_dialog_dir, set_select_file_dialog_dir,
    get_documents_logo_filename)
from sardes.api.tools import SardesTool


class SaveReadingsToExcelTool(SardesTool):
    """
    A tool to format and save readings data to an Excel workbook.
    """
    NAMEFILTERS = "Excel Workbook (*.xlsx)"

    def __init__(self, parent):
        super().__init__(
            parent,
            name='save_readings_to_file',
            text=_("Create XLSX Document"),
            icon='file_excel',
            tip=_('Save daily readings data in an Excel document.')
            )

    # ---- SardesTool API
    def __triggered__(self):
        self.select_save_file(filename=None)

    # ---- Public API
    def select_save_file(self, filename=None):
        """
        Open a file dialog to allow the user to select a location
        where to save the Excel file.

        Parameters
        ----------
        filename : str
            The absolute path of the default filename that will be set in
            the file dialog.
        """
        obs_well_id = self.parent.model()._obs_well_data['obs_well_id']
        if filename is None:
            filename = osp.join(
                get_select_file_dialog_dir(),
                'readings_{}.xlsx'.format(obs_well_id))

        filename, filefilter = QFileDialog.getSaveFileName(
            self.parent, _("Save File"), filename, self.NAMEFILTERS)
        if filename:
            filename = osp.abspath(filename)
            set_select_file_dialog_dir(osp.dirname(filename))
            if not filename.endswith('.xlsx'):
                filename += '.xlsx'
            self.save_readings_to_file(filename)

    def save_readings_to_file(self, filename):
        """
        Save the resampled and formatted readings data of this tool's
        parent table in an excel workbook.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            last_repere_data = (
                self.parent.model()._repere_data
                .sort_values(by=['end_date'], ascending=[True])
                .iloc[-1])
            ground_altitude = (
                last_repere_data['top_casing_alt'] -
                last_repere_data['casing_length'])
            is_alt_geodesic = last_repere_data['is_alt_geodesic']
            _save_reading_data_to_xlsx(
                filename, _('Piezometry'),
                self.parent.get_formatted_data(),
                self.parent.model()._obs_well_data,
                ground_altitude,
                is_alt_geodesic,
                get_documents_logo_filename())
        except PermissionError:
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()
            QMessageBox.warning(
                self.parent,
                _('File in Use'),
                _("The save file operation cannot be completed because the "
                  "file is in use by another application or user."),
                QMessageBox.Ok)
            self.select_save_file(filename)
        else:
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()


def _save_reading_data_to_xlsx(filename, sheetname, formatted_data,
                               obs_well_data, ground_altitude,
                               is_alt_geodesic, company_logo_filename=None):
    """
    Save data in an excel workbook using the specified filename and sheetname.

    https://xlsxwriter.readthedocs.io/format.html
    """
    if not filename.endswith('.xlsx'):
        filename += '.xlsx'

    # Rename the columns of the dataset.
    formatted_data = formatted_data[
        ['datetime', DataType.WaterLevel, DataType.WaterTemp]]
    formatted_data.columns = [
        _("Date of reading"),
        _("Water level altitude (m MSL)"),
        _("Water temperature (°C)")]

    # Write the data to the file.
    # https://xlsxwriter.readthedocs.io/example_pandas_datetime.html
    writer = pd.ExcelWriter(
        filename, engine='xlsxwriter',
        datetime_format='yyyy-mm-dd', date_format='yyyy-mm-dd')
    formatted_data.to_excel(
        writer, sheet_name=sheetname, startrow=5, header=False, index=False)

    workbook = writer.book
    worksheet = writer.sheets[sheetname]

    # Setup the columns format.
    # Note that for date and datetime, the format needs to be specified
    # in the writer directly.
    # https://xlsxwriter.readthedocs.io/example_pandas_column_formats.html
    # https://github.com/python-excel/xlwt/blob/master/examples/num_formats.py
    date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
    num_format = workbook.add_format({'num_format': '0.00'})
    worksheet.set_column('A:A', 25, date_format)
    worksheet.set_column('B:B', 34, num_format)
    worksheet.set_column('C:C', 34, num_format)

    # Write the data header.
    data_header_style = workbook.add_format({
        'font_name': 'Calibri', 'font_size': 11,
        'align': 'right', 'valign': 'bottom'})
    for i, column in enumerate(formatted_data.columns):
        worksheet.write(4, i, column, data_header_style)

    # Write the file header.
    worksheet.set_default_row(15)
    worksheet.set_row(0, 30)
    worksheet.set_row(1, 30)
    worksheet.set_row(2, 30)

    # https://xlsxwriter.readthedocs.io/example_pandas_header_format.html
    worksheet.write(
        0, 1, _('Municipality:'),
        workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12,
                             'bold': True, 'top': 6, 'left': 6,
                             'align': 'right', 'valign': 'vcenter'}))
    worksheet.write(
        0, 2, obs_well_data['municipality'],
        workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12,
                             'bold': True, 'top': 6, 'right': 6,
                             'align': 'center', 'valign': 'vcenter'}))
    worksheet.write(
        1, 1, _('Piezometer number:'),
        workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12,
                             'bold': True, 'left': 6,
                             'align': 'right', 'valign': 'vcenter'}))
    worksheet.write(
        1, 2, obs_well_data['obs_well_id'],
        workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12,
                             'bold': True, 'right': 6,
                             'align': 'center', 'valign': 'vcenter'}))
    worksheet.write(
        2, 1, _('Ground altitude (m MSL):'),
        workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12,
                             'bold': True, 'bottom': 6, 'left': 6,
                             'align': 'right', 'valign': 'vcenter'}))

    if ground_altitude is not None:
        alt_value = "{:0.2f} ({})".format(
            ground_altitude,
            _('Geodesic') if is_alt_geodesic else _('Approximated'))
    else:
        alt_value = _('Not Available')
    worksheet.write(
        2, 2, alt_value,
        workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12,
                             'bold': True, 'bottom': 6, 'right': 6,
                             'align': 'center', 'valign': 'vcenter'}))

    # Add the corporate logo to the file.
    if company_logo_filename is not None:
        img = Image.open(company_logo_filename)

        width, height = img.size
        img_scale = min(170 / width, 125 / height)

        # Fill transparent background if any.
        # https://github.com/python-pillow/Pillow/issues/2609#issuecomment-313922483
        if img.mode in ('RGBA', 'LA'):
            background = Image.new(img.mode[:-1], img.size, (250, 250, 250))
            background.paste(img, img.split()[-1])
            img = background

        image_data = BytesIO()
        img.convert('RGB').save(image_data, 'JPEG', quality=100)

        worksheet.insert_image(
            0, 0, 'logo.jpg',
            options={'x_scale': img_scale, 'y_scale': img_scale,
                     'image_data': image_data,
                     'x_offset': 3, 'y_offset': 3}
            )

    try:
        writer.save()
    except FileCreateError:
        raise PermissionError
