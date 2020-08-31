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
from appconfigs.base import get_home_dir
import pandas as pd
from PIL import Image
from xlsxwriter.exceptions import FileCreateError

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.config.locale import _
from sardes.config.main import CONF, CONFIG_DIR
from sardes.api.tools import SardesTool
from sardes.utils.fileio import SafeFileSaver


class SaveReadingsToExcelTool(SardesTool):
    """
    A tool to format and save readings data to an Excel workbook.
    """
    NAMEFILTERS = ["Excel Workbook (*.xlsx)"]

    def __init__(self, parent):
        super().__init__(
            parent,
            name='save_readings_to_file',
            text=_("Create XLSX Document"),
            icon='file_excel',
            tip=_('Save daily readings data in an Excel document.')
            )
        self.file_saver = SafeFileSaver(
            parent=parent, name_filters=self.NAMEFILTERS, title=_("Save File"))

    # ---- SardesTool API
    def __triggered__(self):
        obs_well_id = self.parent.model()._obs_well_data['obs_well_id']
        savedir = CONF.get('main', 'savedir', get_home_dir())
        filename = osp.join(
            savedir, 'readings_{}.xlsx'.format(obs_well_id))
        self.file_saver.savefile(self.save_readings_to_file, filename)
        if self.file_saver.savedir != savedir:
            CONF.set('main', 'savedir', self.file_saver.savedir)

    def save_readings_to_file(self, filename, selectedfilter):
        """
        Resample daily, format and save the readings data of this tool's
        parent table in an excel workbook.
        """
        _save_reading_data_to_xlsx(
            filename, _('Piezometry'),
            self.parent.model().dataf,
            self.parent.model()._obs_well_data,
            self.parent.model()._repere_data,
            self.get_company_logo_filename())

    def get_company_logo_filename(self):
        """
        Return the absolute file path of the image to use a a company logo
        in the excel files.
        """
        for file in os.listdir(CONFIG_DIR):
            root, ext = osp.splitext(file)
            if root == 'company_logo':
                return osp.join(CONFIG_DIR, file)


def _format_reading_data(dataf, repere_data):
    """
    Resample readings data on a daily basis and format it so that
    it can be saved in an Excel workbook.
    """
    data = (
        dataf
        .dropna(subset=[DataType.WaterLevel])
        .groupby('install_depth').resample('D', on='datetime').first()
        .dropna(subset=[DataType.WaterLevel])
        .droplevel(0, axis=0).drop('datetime', axis=1)
        .reset_index(drop=False)
        .sort_values(by=['datetime', 'install_depth'], ascending=[True, True])
        .drop_duplicates(subset='datetime', keep='first')
        .reset_index(drop=True)
        )
    data = data[['datetime', DataType.WaterLevel, DataType.WaterTemp]]

    # Convert water level in altitude.
    if not repere_data.empty:
        top_casing_alt = repere_data['top_casing_alt']
        data[DataType.WaterLevel] = (
            top_casing_alt - data[DataType.WaterLevel])

    # Rename columns.
    data.columns = [_("Date of reading"),
                    _("Water level altitude (m)"),
                    _("Water temperature (°C)")
                    ]
    return data


def _save_reading_data_to_xlsx(filename, sheetname, data, obs_well_data,
                               repere_data, company_logo_filename=None):
    """
    Save data in an excel workbook using the specified filename and sheetname.

    https://xlsxwriter.readthedocs.io/format.html
    """
    if not filename.endswith('.xlsx'):
        filename += '.xlsx'

    # Write the data to the file.
    # https://xlsxwriter.readthedocs.io/example_pandas_datetime.html
    writer = pd.ExcelWriter(
        filename, engine='xlsxwriter',
        datetime_format='yyyy-mm-dd', date_format='yyyy-mm-dd')
    data = _format_reading_data(data, repere_data)
    data.to_excel(
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
    worksheet.set_column('B:B', 25, num_format)
    worksheet.set_column('C:C', 34, num_format)

    # Write the data header.
    data_header_style = workbook.add_format({
        'font_name': 'Calibri', 'font_size': 11,
        'align': 'right', 'valign': 'bottom'})
    for i, column in enumerate(data.columns):
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
        2, 1, _('Ground elevation (m):'),
        workbook.add_format({'font_name': 'Times New Roman', 'font_size': 12,
                             'bold': True, 'bottom': 6, 'left': 6,
                             'align': 'right', 'valign': 'vcenter'}))

    if not repere_data.empty:
        alt_value = "{:0.2f} ({})".format(
            repere_data['top_casing_alt'] - repere_data['casing_length'],
            _('Geodesic') if repere_data['is_alt_geodesic'] else
            _('Approximated')
            )
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
                     'image_data': image_data}
            )

    try:
        writer.save()
    except FileCreateError:
        raise PermissionError
