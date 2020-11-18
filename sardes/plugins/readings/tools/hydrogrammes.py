# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
import sys
import os.path as osp
import datetime
import locale
from math import floor, ceil

# ---- Third party library imports
import matplotlib as mpl
import matplotlib.dates as mdates
from matplotlib.transforms import ScaledTranslation
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
from PIL import Image
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QFileDialog, QMessageBox
import numpy as np

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.config.locale import _
from sardes.config.ospath import (
    get_select_file_dialog_dir, set_select_file_dialog_dir,
    get_company_logo_filename)
from sardes import __rootdir__
from sardes.api.tools import SardesTool

mpl.rc('font', **{'family': 'sans-serif', 'sans-serif': ['Calibri']})


class HydrographTool(SardesTool):
    """
    A tool to produce hydrograph figures for publishing from reading data.
    """
    NAMEFILTERS = ';;'.join(['Portable Document Format (*.pdf)',
                             'Scalable Vector Graphics (*.svg)',
                             'Portable Network Graphics (*.png)'
                             'JPEG (*.jpg)'
                             ])

    def __init__(self, parent):
        super().__init__(
            parent,
            name='plot_hydrograph_tool',
            text=_("Show Hydrograph"),
            icon='image',
            tip=_("Create a publication ready graph of the water level data.")
            )

    def __triggered__(self):
        self.select_save_file()

    # ---- Public API
    def select_save_file(self, filename=None):
        """
        Open a file dialog to allow the user to select a location and a
        file type to save the hydrograph.

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
                'graph_{}.pdf'.format(obs_well_id))

        filename, filefilter = QFileDialog.getSaveFileName(
            self.parent, _("Save Hydrograph"), filename, self.NAMEFILTERS)
        if filename:
            fext = filefilter[-5:-1]
            if not filename.endswith(fext):
                filename += fext
            filename = osp.abspath(filename)
            set_select_file_dialog_dir(osp.dirname(filename))
            self.save_hydrograph_to_file(filename)

    def save_hydrograph_to_file(self, filename):
        """
        Plot and save the resampled and formatted readings data of this tool's
        parent table to pdf, svg, png or jpg file.
        """
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            hydrograph = HydrographCanvas(
                self.parent.get_formatted_data(),
                self.parent.model()._obs_well_data)
            hydrograph.figure.savefig(filename, dpi=300)
            pass
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


class HydrographCanvas(FigureCanvasQTAgg):
    def __init__(self, data, obs_well_data, repere_data):
        fwidth = 11
        fheight = 8.5
        margin_width = 0.5
        fig = Figure(figsize=(fwidth, fheight), facecolor='white', dpi=300)
        super().__init__(fig)

        # data = data.set_index('datetime', drop=True)

        line_color = '#1f77b4'
        grid_color = '0.65'

        ax = self.figure.add_axes([0, 0, 1, 1], frameon=True)
        ax.set_ylabel("Water level altitude (m)", fontsize=23, labelpad=20)
        ax.grid(axis='both', ls='-', color=grid_color, which='major')
        ax.tick_params(axis='both', direction='out', labelsize=16, length=3,
                       pad=10, color=grid_color)
        ax.tick_params(axis='both', direction='out', color=grid_color,
                       which='minor')
        for spine in ax.spines.values():
            spine.set_edgecolor(grid_color)

        # Plot the data for the period preceding the use of electronic probes.
        data1 = data[data['sonde_id'].isnull()].copy()
        data1['timediff'] = data1['datetime'].diff() > datetime.timedelta(365)
        data1['timediff'] = data1['timediff'].cumsum().copy()
        for group in data1.groupby('timediff'):
            ax.plot(group[1]['datetime'],
                    group[1][DataType.WaterLevel],
                    color=line_color)

        # Plot the data from automated logger.
        data2 = data[data['sonde_id'].notnull()].copy()
        data2['timediff'] = data2['datetime'].diff() > datetime.timedelta(1)
        data2['timediff'] = data2['timediff'].cumsum()
        for group in data2.groupby('timediff'):
            ax.plot(group[1]['datetime'],
                    group[1][DataType.WaterLevel],
                    color=line_color)

        # Setup the the axis range and ticks.
        ymin = data[DataType.WaterLevel].min()
        ymax = data[DataType.WaterLevel].max()

        year_min = data['datetime'].min().year
        year_max = data['datetime'].max().year + 1
        year_span = year_max - year_min
        if year_span <= 15:
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_minor_locator(mdates.MonthLocator())
            xmin = datetime.datetime(year_min, 1, 1)
            xmax = datetime.datetime(year_max, 1, 1)
        elif year_span <= 30:
            ax.xaxis.set_major_locator(mdates.YearLocator(2))
            ax.xaxis.set_minor_locator(mdates.MonthLocator(3))
            xmin = datetime.datetime(2 * floor(year_min / 2), 1, 1)
            xmax = datetime.datetime(2 * ceil(year_max / 2), 1, 1)
        else:
            ax.xaxis.set_major_locator(mdates.YearLocator(5))
            ax.xaxis.set_minor_locator(mdates.YearLocator())
            xmin = datetime.datetime(5 * floor(year_min / 5), 1, 1)
            xmax = datetime.datetime(5 * ceil(year_max / 5), 1, 1)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.axis(ymax=ymax * 1.025, ymin=ymin * 0.975, xmin=xmin, xmax=xmax)

        # Setup the left and right margins.
        self.draw()
        renderer = self.get_renderer()
        bbox_xaxis_bottom = ax.xaxis.get_ticklabel_extents(renderer)[0]
        bbox_yaxis_label = ax.yaxis.label.get_window_extent(renderer)
        left_margin = (
            margin_width / fwidth +
            (ax.bbox.x0 - bbox_yaxis_label.x0) / fig.bbox.width)
        right_margin = (
            margin_width / fwidth +
            max(((bbox_xaxis_bottom.x1 - ax.bbox.x1) / fig.bbox.width), 0)
            )
        ax.set_position([left_margin, 0, 1 - left_margin - right_margin, 1])

        # Add the figure title.
        self.draw()
        title_text = _(
            'Municipality: {}\nObservation Well: {}'
            ).format(obs_well_data['municipality'],
                     obs_well_data['obs_well_id'])
        offset = ScaledTranslation(0, -margin_width, fig.dpi_scale_trans)
        fig_title = ax.text(
            0.5, 1, title_text, ha='center', va='top', fontsize=20,
            fontweight='bold', linespacing=1.5,
            transform=fig.transFigure + offset)

        # Add the logo.
        img = Image.open(get_company_logo_filename())
        img_width, img_height = img.size
        logo_height = int(0.7 * fig.dpi)
        logo_width = int(img_width / img_height * logo_height)
        img = img.resize((logo_width, logo_height), Image.LANCZOS)

        bbox_xaxis_bottom = ax.xaxis.get_ticklabel_extents(renderer)[0]
        logo_x0 = max(ax.bbox.x1, bbox_xaxis_bottom.x1) - logo_width
        logo_y0 = margin_width * fig.dpi
        fig.figimage(img, logo_x0, logo_y0, alpha=1, zorder=0,
                     url='http://www.environnement.gouv.qc.ca/')

        # Add a blue delimitation line.
        rect1_height = 6 / 72 * fig.dpi / fig.bbox.height
        rect1_y0 = (logo_height + logo_y0) / fig.bbox.height - rect1_height
        rect1_x0 = margin_width / fwidth
        rect1_width = (logo_x0 - 12/72 * fig.dpi) / fig.bbox.width - rect1_x0
        rect1 = Rectangle((rect1_x0, rect1_y0), rect1_width, rect1_height,
                          fc=line_color, ec=line_color,
                          transform=fig.transFigure, clip_on=False, zorder=0)
        ax.add_patch(rect1)

        # Add the date, copyright notice and url.
        now = datetime.datetime.now()
        offset = ScaledTranslation(0, -8/72, fig.dpi_scale_trans)
        created_on_text = ax.text(
            margin_width / fwidth,
            rect1.get_window_extent(renderer).y0 / fig.bbox.height,
            _("Created on {}").format(now.strftime('%d/%m/%y')),
            va='top', transform=fig.transFigure + offset
            )
        offset = ScaledTranslation(0/72, -4/72, fig.dpi_scale_trans)
        copyright_text = ax.text(
            margin_width / fwidth,
            created_on_text.get_window_extent(renderer).y0 / fig.bbox.height,
            "© Gouvernement du Québec - {}".format(now.year),
            va='top', transform=fig.transFigure+offset
            )
        url_text = ax.text(
            margin_width / fwidth,
            copyright_text.get_window_extent(renderer).y0 / fig.bbox.height,
            "http://www.environnement.gouv.qc.ca/eau/piezo/index.htm",
            va='top', transform=fig.transFigure+offset,
            url="http://www.environnement.gouv.qc.ca/eau/piezo/index.htm",
            color='blue')

        # Setup the top and bottom margin.
        self.draw()
        bbox_title = fig_title.get_window_extent(renderer)
        bbox_xaxis_bottom = ax.xaxis.get_ticklabel_extents(renderer)[0]

        title_pad = 18 / 72 * fig.dpi
        logo_pad = 36 / 72 * fig.dpi
        top_margin = (
            margin_width / fheight +
            (bbox_title.height + title_pad) / fig.bbox.height
            )
        bottom_margin = (
            margin_width / fheight +
            (logo_height + logo_pad) / fig.bbox.height +
            (ax.bbox.y0 - bbox_xaxis_bottom.y0) / fig.bbox.height
            )
        ax.set_position([left_margin, bottom_margin,
                         1 - left_margin - right_margin,
                         1 - bottom_margin - top_margin])

        # Add altitude information.
        bbox_xaxis_bottom = ax.xaxis.get_ticklabel_extents(renderer)[0]
        bbox_yaxis_left = ax.yaxis.get_ticklabel_extents(renderer)[0]
        geodesic_text = (
            _('Geodesic') if repere_data['is_alt_geodesic'] else
            _('Approximated'))
        alt_text = _("Ground elevation: {:0.1f} m ({})").format(
            repere_data['top_casing_alt'], geodesic_text)
        alt_text_y0 = bbox_xaxis_bottom.y0 / fig.bbox.height
        alt_text_x0 = bbox_yaxis_left.x0 / fig.bbox.width
        offset = ScaledTranslation(0, -8/72, fig.dpi_scale_trans)
        ax.text(
            alt_text_x0, alt_text_y0, alt_text, ha='left', va='top',
            fontsize=10, transform=fig.transFigure + offset)

        self.draw()


# %%

def test_hydrograph():
    dbaccessor = DatabaseAccessorSardesLite(
        'D:/Desktop/rsesq_prod_21072020_v1.db')
    dbmanager = DatabaseConnectionManager()

    dbmanager.connect_to_db(dbaccessor)
    sampling_feature_uuid = (
        dbaccessor._get_sampling_feature_uuid_from_name('01070002'))
    readings = dbmanager.get_timeseries_for_obs_well(
        sampling_feature_uuid,
        [DataType.WaterLevel, DataType.WaterTemp],
        callback=None,
        postpone_exec=False, main_thread=True)

    obs_wells_data = dbaccessor.get_observation_wells_data().loc[
        sampling_feature_uuid]

    repere_data = dbaccessor.get_repere_data()
    repere_data = (
        repere_data
        [repere_data['sampling_feature_uuid'] == sampling_feature_uuid]
        .iloc[0]
        )

    hydrograph = HydrographCanvas(
        format_reading_data(readings, repere_data['top_casing_alt']),
        obs_wells_data,
        repere_data)
    hydrograph.figure.savefig('D:/hydrograph_test2.pdf')

    dbmanager.close()


if __name__ == '__main__':
    from sardes.database.accessors import DatabaseAccessorSardesLite
    from sardes.database.database_manager import DatabaseConnectionManager
    from sardes.utils.data_operations import format_reading_data
    test_hydrograph()


# # Add the piezometer information.
# fig.canvas.draw()
# yaxis_label_x0 = ax.yaxis.label.get_window_extent(renderer).x0
# yaxis_bbox_left, _ = ax.yaxis.get_ticklabel_extents(renderer)
# xaxis_bbox_bott, _ = ax.xaxis.get_ticklabel_extents(renderer)
# offset_top = ScaledTranslation(0, -12/72, fig.dpi_scale_trans)
# linespacing = ScaledTranslation(0, -6/72, fig.dpi_scale_trans)

# info_top_left = ax.text(
#    ax.bbox.x0/fig.bbox.width,
#    fig_title.get_window_extent(renderer).y0/fig.bbox.height,
#    "Latitude : {}\u00B0".format(lat),
#    ha='left', va='top', fontsize=14, fontweight='bold',
#    transform=fig.transFigure+offset_top)
    
# info_bot_left = ax.text(
#    ax.bbox.x0/fig.bbox.width,
#    info_top_left.get_window_extent(renderer).y0/fig.bbox.height,
#    "Longitude : {}\u00B0".format(lon),
#    ha='left', va='top', fontsize=14, fontweight='bold',
#    transform=fig.transFigure+linespacing)

# info_top_center = ax.text(
#     (ax.bbox.x1 + ax.bbox.x0)/2/fig.bbox.width,
#     fig_title.get_window_extent(renderer).y0/fig.bbox.height,
#     'Nappe : {}'.format(reader[sid]['Nappe']),
#     ha='center', va='top', fontsize=14, fontweight='bold',
#     transform=fig.transFigure+offset_top)

# info_bot_center = ax.text(
#     info_top_center.get_window_extent(renderer).x0/fig.bbox.width,
#     info_top_center.get_window_extent(renderer).y0/fig.bbox.height,
#     'Influencé : {}'.format(reader[sid]['Influenced']),
#     ha='left', va='top', fontsize=14, fontweight='bold',
#     transform=fig.transFigure+linespacing)

# info_top_right = ax.text(
#     ax.bbox.x1/fig.bbox.width,
#     fig_title.get_window_extent(renderer).y0/fig.bbox.height,
#     "Altitude du sol : {} m".format(elev),
#     ha='right', va='top', fontsize=14, fontweight='bold',
#     transform=fig.transFigure+offset_top)

# info_bot_right = ax.text(
#     info_top_right.get_window_extent(renderer).x0/fig.bbox.width,
#     info_top_right.get_window_extent(renderer).y0/fig.bbox.height,
#     "Aquifère : Roc",
#     ha='left', va='top', fontsize=14, fontweight='bold',
#     transform=fig.transFigure+linespacing)
