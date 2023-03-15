# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
import os.path as osp
import datetime
from math import floor, ceil

# ---- Third party library imports
import matplotlib.dates as mdates
from matplotlib.transforms import ScaledTranslation
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.patches import Rectangle
from matplotlib.ticker import MultipleLocator
from PIL import Image
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QFileDialog, QMessageBox

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.config.locale import _
from sardes.config.main import CONF
from sardes.config.ospath import (
    get_select_file_dialog_dir, set_select_file_dialog_dir,
    get_documents_logo_filename)
from sardes.api.tools import SardesTool


class HydrographTool(SardesTool):
    """
    A tool to produce hydrograph figures for publishing reading data.
    """
    NAMEFILTERS = ';;'.join(['Portable Document Format (*.pdf)',
                             'Scalable Vector Graphics (*.svg)',
                             'Portable Network Graphics (*.png)',
                             'JPEG (*.jpg)'
                             ])

    def __init__(self, parent):
        super().__init__(
            parent,
            name='plot_hydrograph_tool',
            text=_("Create Hydrograph"),
            icon='image',
            tip=_("Create a publication ready graph of the water level data.")
            )

    # ---- SardesTool API
    def update(self):
        pass

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
        obs_well_id = self.table.model()._obs_well_data['obs_well_id']
        if filename is None:
            filename = osp.join(
                get_select_file_dialog_dir(),
                _('graph_{}.pdf').format(obs_well_id))

        filename, filefilter = QFileDialog.getSaveFileName(
            self.table, _("Save Hydrograph"), filename, self.NAMEFILTERS)
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
        last_repere_data = (
            self.table.model()._repere_data
            .sort_values(by=['end_date'], ascending=[True])
            .iloc[-1])
        ground_altitude = (
            last_repere_data['top_casing_alt'] -
            last_repere_data['casing_length'])
        is_alt_geodesic = last_repere_data['is_alt_geodesic']
        hydrograph = HydrographCanvas(
            self.table.get_formatted_data(),
            self.table.model()._obs_well_data,
            ground_altitude, is_alt_geodesic,
            fontname=CONF.get('documents_settings', 'graph_font'))
        try:
            hydrograph.figure.savefig(filename, dpi=300)
        except PermissionError:
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()
            QMessageBox.warning(
                self.table,
                _('File in Use'),
                _("The save file operation cannot be completed because the "
                  "file is in use by another application or user."),
                QMessageBox.Ok)
            self.select_save_file(filename)
        else:
            QApplication.restoreOverrideCursor()
            QApplication.processEvents()


class HydrographCanvas(FigureCanvasAgg):
    def __init__(self, data, obs_well_data, ground_altitude, is_alt_geodesic,
                 fontname='Arial'):
        fwidth = 11
        fheight = 8.5
        margin_width = 0.5
        fig = Figure(figsize=(fwidth, fheight), facecolor='white', dpi=300)
        super().__init__(fig)

        # data = data.set_index('datetime', drop=True)

        line_color = '#1f77b4'
        grid_color = '0.65'

        ax = self.figure.add_axes([0, 0, 1, 1], frameon=True)
        ax.set_ylabel(
            _("Water level altitude (m MSL)"), fontsize=23, labelpad=20,
            fontname=fontname)
        ax.grid(axis='both', ls='-', color=grid_color, which='major')
        ax.tick_params(axis='both', direction='out', length=5,
                       pad=10, color=grid_color)
        ax.tick_params(axis='both', direction='out', color=grid_color,
                       which='minor')
        for spine in ax.spines.values():
            spine.set_edgecolor(grid_color)

        # Plot data acquired with an automated logger.
        data_sonde_id = data[data['sonde_id'].notnull()].copy()
        data_sonde_id['timediff'] = (
            data_sonde_id['datetime'].diff() > datetime.timedelta(1))
        data_sonde_id['timediff'] = data_sonde_id['timediff'].cumsum()
        for group in data_sonde_id.groupby('timediff'):
            ax.plot(group[1]['datetime'],
                    group[1][DataType.WaterLevel],
                    color=line_color)

        # Plot data for which we do not have a sonde id.

        # For these data, we use different rules to plot the data acquired
        # before 2000 then after. Data acquired after 2000 were most likely
        # acquired with a logger, but the information was not entered
        # in the database.
        data_nosonde_id = data[data['sonde_id'].isnull()].copy()

        data_av_2000 = (
            data_nosonde_id
            [data_nosonde_id['datetime'] < datetime.datetime(2000, 1, 1)]
            .copy())
        data_av_2000['timediff'] = (
            data_av_2000['datetime'].diff() > datetime.timedelta(365))
        data_av_2000['timediff'] = data_av_2000['timediff'].cumsum()
        for group in data_av_2000.groupby('timediff'):
            ax.plot(group[1]['datetime'],
                    group[1][DataType.WaterLevel],
                    color=line_color)

        data_af_2000 = (
            data_nosonde_id
            [data_nosonde_id['datetime'] >= datetime.datetime(2000, 1, 1)]
            .copy())
        data_af_2000['timediff'] = (
            data_af_2000['datetime'].diff() > datetime.timedelta(1))
        data_af_2000['timediff'] = data_af_2000['timediff'].cumsum()
        for group in data_af_2000.groupby('timediff'):
            ax.plot(group[1]['datetime'],
                    group[1][DataType.WaterLevel],
                    color=line_color)

        # Setup the the range and ticks of the xaxis.
        if not data.empty:
            ymin = data[DataType.WaterLevel].min()
            ymax = data[DataType.WaterLevel].max()
            ymin = ymin - (ymax - ymin) * 0.025
            ymax = ymax + (ymax - ymin) * 0.025

            yscales = [0.05, 0.1, 0.2, 0.25, 0.5, 0.75, 1, 2, 5, 10]
            yscales_minor = {
                0.05: 0.01, 0.1: 0.02, 0.2: 0.05, 0.25: 0.05,
                0.5: 0.1, 0.75: 0.15, 1: 0.2, 2: 0.5, 5: 1, 10: 2}
            for yscale in yscales:
                if (ymax - ymin) / yscale <= 12:
                    break
            yscale_minor = yscales_minor[yscale]
            ymin = yscale * floor(ymin / yscale)
            ymax = yscale * ceil(ymax / yscale)
        else:
            ymin = 0
            ymax = 1
            yscale = 0.1
            yscale_minor = 0.02
        ax.yaxis.set_major_locator(MultipleLocator(yscale))
        ax.yaxis.set_minor_locator(MultipleLocator(yscale_minor))

        # Setup the the range and ticks of the yaxis.
        if not data.empty:
            year_min = data['datetime'].min().year
            year_max = data['datetime'].max().year + 1
        else:
            year_min = datetime.datetime.now().year
            year_max = year_min + 1
        year_span = year_max - year_min

        if year_span <= 15:
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_minor_locator(mdates.MonthLocator([4, 7, 10]))
            xmin = datetime.datetime(year_min, 1, 1)
            xmax = datetime.datetime(year_max, 1, 1)
        elif year_span <= 30:
            ax.xaxis.set_major_locator(mdates.YearLocator(2))
            ax.xaxis.set_minor_locator(mdates.MonthLocator(7))
            xmin = datetime.datetime(2 * floor(year_min / 2), 1, 1)
            xmax = datetime.datetime(2 * ceil(year_max / 2), 1, 1)
        else:
            ax.xaxis.set_major_locator(mdates.YearLocator(5))
            ax.xaxis.set_minor_locator(mdates.YearLocator())
            xmin = datetime.datetime(5 * floor(year_min / 5), 1, 1)
            xmax = datetime.datetime(5 * ceil(year_max / 5), 1, 1)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.axis(ymax=ymax, ymin=ymin, xmin=xmin, xmax=xmax)
        self.draw()

        # Set the tick labels font properties.

        # Note that 'ticklabels' cannot be set without setting 'ticks' first
        # or else a warning is shown every time. See cgq-qgc/sardes#556.
        ax.set_xticks(ax.get_xticks())
        ax.set_xticklabels(
            ax.get_xticklabels(), fontname=fontname, fontsize=16)

        ax.set_yticks(ax.get_yticks())
        ax.set_yticklabels(
            ax.get_yticklabels(), fontname=fontname, fontsize=16)

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
        offset = ScaledTranslation(0, -margin_width, fig.dpi_scale_trans)
        fig_title = ax.text(
            0.5, 1,
            _('Municipality: {}\nStation: {}').format(
                obs_well_data['municipality'], obs_well_data['obs_well_id']),
            ha='center', va='top', fontsize=20,
            fontweight='bold', fontname=fontname, linespacing=1.5,
            transform=fig.transFigure + offset)

        # Add the company logo.
        logo_height = int(0.7 * fig.dpi)
        logo_y0 = margin_width * fig.dpi

        logo_filename = get_documents_logo_filename()
        bbox_xaxis_bottom = ax.xaxis.get_ticklabel_extents(renderer)[0]
        if logo_filename is not None:
            img = Image.open(logo_filename)
            img_width, img_height = img.size
            logo_width = int(img_width / img_height * logo_height)
            img = img.resize((logo_width, logo_height), Image.LANCZOS)

            logo_x0 = fig.bbox.width - margin_width * fig.dpi - logo_width
            fig.figimage(img, logo_x0, logo_y0, alpha=1, zorder=0,
                         url='http://www.environnement.gouv.qc.ca/')
        else:
            logo_width = 0
            logo_x0 = fig.bbox.width - margin_width * fig.dpi

        # Add a blue delimitation line.
        rect1_height = 6 / 72 * fig.dpi / fig.bbox.height
        rect1_y0 = (logo_height + logo_y0) / fig.bbox.height - rect1_height
        rect1_x0 = margin_width / fwidth
        if logo_filename is not None:
            rect1_width = (
                (logo_x0 - 12/72 * fig.dpi) / fig.bbox.width - rect1_x0)
        else:
            rect1_width = (logo_x0 / fig.bbox.width) - rect1_x0
        rect1 = Rectangle(
            (rect1_x0, rect1_y0), rect1_width, rect1_height, fc=line_color,
            ec=line_color, clip_on=False, zorder=0, transform=fig.transFigure)
        ax.add_patch(rect1)

        # Add the creation date., copyright notice and url.
        now = datetime.datetime.now()
        offset = ScaledTranslation(0, -8/72, fig.dpi_scale_trans)
        created_on_text = ax.text(
            margin_width / fwidth,
            rect1.get_window_extent(renderer).y0 / fig.bbox.height,
            _("Created on {}").format(now.strftime('%Y-%m-%d')),
            va='top', fontname=fontname, transform=fig.transFigure + offset
            )
        next_ypos = created_on_text.get_window_extent(renderer).y0

        # Add the author's name.
        authors_name = CONF.get('documents_settings', 'authors_name', '')
        if authors_name:
            offset = ScaledTranslation(0/72, -4/72, fig.dpi_scale_trans)
            authors_name_text = ax.text(
                margin_width / fwidth, next_ypos / fig.bbox.height,
                authors_name, va='top', fontname=fontname,
                transform=fig.transFigure+offset
                )
            next_ypos = authors_name_text.get_window_extent(renderer).y0

        # Add the site url.
        site_url = CONF.get('documents_settings', 'site_url', '')
        if site_url:
            offset = ScaledTranslation(0/72, -4/72, fig.dpi_scale_trans)
            site_url_text = ax.text(
                margin_width / fwidth, next_ypos / fig.bbox.height,
                site_url, url=site_url, fontname=fontname, fontstyle='italic',
                va='top', color='blue', transform=fig.transFigure+offset)

        # Setup the top and bottom margin.
        self.draw()
        bbox_title = fig_title.get_window_extent(renderer)
        bbox_xaxis_bottom = ax.xaxis.get_ticklabel_extents(renderer)[0]

        title_pad = 18/72 * fig.dpi
        logo_pad = 36/72 * fig.dpi
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
            _('Geodesic') if is_alt_geodesic else _('Approximate'))
        alt_text = _("Ground altitude: {:0.2f} m MSL ({})").format(
            ground_altitude, geodesic_text)
        alt_text_y0 = bbox_xaxis_bottom.y0 / fig.bbox.height
        alt_text_x0 = bbox_yaxis_left.x0 / fig.bbox.width
        offset = ScaledTranslation(0, -8/72, fig.dpi_scale_trans)
        ax.text(
            alt_text_x0, alt_text_y0, alt_text, ha='left', va='top',
            fontsize=10, fontname=fontname,
            transform=fig.transFigure + offset)

        self.draw()


# %%

if __name__ == '__main__':
    from sardes.database.accessors import DatabaseAccessorSardesLite
    from sardes.utils.data_operations import format_reading_data
    from matplotlib.backends.backend_pdf import PdfPages

    dbaccessor = DatabaseAccessorSardesLite(
        'D:/Desktop/rsesq_prod_21072020_v1.db')

    obs_wells_data = dbaccessor.get('observation_wells_data')
    repere_data = dbaccessor.get('repere_data')

    with PdfPages('D:/hydrographs_example.pdf') as pdf:
        count = 0
        for sampling_feature_uuid in obs_wells_data.index:
            readings = dbaccessor.get_timeseries_for_obs_well(
                sampling_feature_uuid, DataType.WaterLevel)
            repere_data_for_well = (
                repere_data
                [repere_data['sampling_feature_uuid'] ==
                 sampling_feature_uuid]
                .iloc[0])
            obswell_data = obs_wells_data.loc[sampling_feature_uuid]
            print(obswell_data['obs_well_id'],
                  '- {} of {}'.format(count + 1, len(obs_wells_data)))
            if readings.empty:
                continue

            hydrograph = HydrographCanvas(
                format_reading_data(
                    readings, repere_data_for_well['top_casing_alt']),
                obswell_data,
                repere_data_for_well)
            pdf.savefig(hydrograph.figure)
            count += 1

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
