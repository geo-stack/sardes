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


# %%

mpl.rc('font', **{'family': 'sans-serif', 'sans-serif': ['Calibri']})

sid = '04017011'
data = reader.get_station_data(sid)
elev = reader[sid]['Elevation']
lat = reader[sid]['Latitude']
lon = reader[sid]['Longitude']
name = reader[sid]['Name']
# data = data.resample('D').asfreq()

fig = plt.figure(dpi=300)
renderer = fig.canvas.get_renderer()
fheight, fwidth = 8.5, 11
fig.set_size_inches(fwidth, fheight)
margin_width = 0.5

ax = fig.add_axes([0, 0, 1, 1], frameon=False)
line_color = '#1f77b4'

data_av_2000 = data[data.index < datetime.datetime(2000, 1, 1)]
l2, = ax.plot(data_av_2000['Water Level (masl)'], color=line_color)

data_af_2000 = data[data.index >= datetime.datetime(2000, 1, 1)]
ax.plot(data_af_2000['Water Level (masl)'], color=line_color)

ax.set_ylabel("Altitude du niveau d'eau (m)", fontsize=23, labelpad=20)
ax.grid(axis='both', ls='-', color='0.65')
ax.tick_params(axis='both', direction='out', labelsize=16, length=3, pad=10,
               color='0.65')

# Set axis range.
ax.set_yticks(np.arange(41, 46.1, 0.5))
ax.axis(ymax=46, ymin=41,
        xmin=datetime.datetime(1970, 1, 1),
        xmax=datetime.datetime(2020, 1, 1))

# Add the logo.
img = Image.open(
    osp.join(__rootdir__, 'ressources', 'Logo_MELCC_unauthorized.png'))
img_width, img_height = img.size
logo_height = int(0.7 * fig.dpi)
logo_width = int(img_width / img_height * logo_height)
img = img.resize((logo_width, logo_height), Image.ANTIALIAS)

bbox_bott, _ = ax.xaxis.get_ticklabel_extents(renderer)
logo_x0 = fig.bbox.width - img.size[0] - margin_width * fig.dpi
logo_y0 = margin_width * fig.dpi
fimg = fig.figimage(img, logo_x0, logo_y0, alpha=1, zorder=0,
                    url='http://www.environnement.gouv.qc.ca/')

# Add a blue delimitation line.
fig.canvas.draw()
rect1_height = 25 / fig.bbox.height
rect1_y0 = (img.size[1] + logo_y0)/fig.bbox.height - rect1_height
rect1_x0 = margin_width / fwidth
rect1_width = (logo_x0 - 50) / fig.bbox.width - rect1_x0
rect1 = Rectangle((rect1_x0, rect1_y0), rect1_width, rect1_height,
                  fc=line_color, ec=line_color,
                  transform=fig.transFigure, clip_on=False, zorder=0)
ax.add_patch(rect1)

# Add the date, copyright notice and url.
fig.canvas.draw()
locale.setlocale(category=locale.LC_ALL, locale="fr_FR") 
now = datetime.datetime.now()

text_x0 = margin_width / fwidth
offset = ScaledTranslation(0, -8/72, fig.dpi_scale_trans)
text = ax.text(text_x0, rect1.get_window_extent(renderer).y0/fig.bbox.height,
               "Créé le {}".format(now.strftime('%#d %B %Y')),
               va='top', transform=fig.transFigure+offset)  

offset = ScaledTranslation(0/72, -4/72, fig.dpi_scale_trans)
text = ax.text(text_x0, text.get_window_extent(renderer).y0/fig.bbox.height,
               "© Gouvernement du Québec - {}".format(now.year),
               va='top', transform=fig.transFigure+offset)

ax.text(text_x0, text.get_window_extent(renderer).y0/fig.bbox.height,
        "http://www.environnement.gouv.qc.ca/eau/piezo/index.htm",
        va='top', transform=fig.transFigure+offset,
        url="http://www.environnement.gouv.qc.ca/eau/piezo/index.htm",
        color='blue')

# Setup the left and right margins.
fig.canvas.draw()
xaxis_bbox_bott, _ = ax.xaxis.get_ticklabel_extents(renderer)
yaxis_label_bbox = ax.yaxis.label.get_window_extent(renderer)
lm = margin_width/fwidth + (ax.bbox.x0 - yaxis_label_bbox.x0)/fig.bbox.width
rm = margin_width/fwidth + (xaxis_bbox_bott.x1 - ax.bbox.x1)/fig.bbox.width
ax.set_position([lm, 0, 1-lm-rm, 1])

# Add the figure title.
fig.canvas.draw()
offset = ScaledTranslation(0, -margin_width, fig.dpi_scale_trans)
fig_title = ax.text(
    0.5, 1,
    'Hydrogramme du piézomètre No. {}\nMunicipalité de {}'.format(sid, name),
    ha='center', va='top', fontsize=20, fontweight='bold', linespacing=1.5,
    transform=fig.transFigure + offset, color=line_color)

# Add the piezometer information.
fig.canvas.draw()
yaxis_label_x0 = ax.yaxis.label.get_window_extent(renderer).x0
yaxis_bbox_left, _ = ax.yaxis.get_ticklabel_extents(renderer)
xaxis_bbox_bott, _ = ax.xaxis.get_ticklabel_extents(renderer)
offset_top = ScaledTranslation(0, -12/72, fig.dpi_scale_trans)
linespacing = ScaledTranslation(0, -6/72, fig.dpi_scale_trans)

info_top_left = ax.text(
   ax.bbox.x0/fig.bbox.width,
   fig_title.get_window_extent(renderer).y0/fig.bbox.height,
   "Latitude : {}\u00B0".format(lat),
   ha='left', va='top', fontsize=14, fontweight='bold',
   transform=fig.transFigure+offset_top)
    
info_bot_left = ax.text(
   ax.bbox.x0/fig.bbox.width,
   info_top_left.get_window_extent(renderer).y0/fig.bbox.height,
   "Longitude : {}\u00B0".format(lon),
   ha='left', va='top', fontsize=14, fontweight='bold',
   transform=fig.transFigure+linespacing)

info_top_center = ax.text(
    (ax.bbox.x1 + ax.bbox.x0)/2/fig.bbox.width,
    fig_title.get_window_extent(renderer).y0/fig.bbox.height,
    'Nappe : {}'.format(reader[sid]['Nappe']),
    ha='center', va='top', fontsize=14, fontweight='bold',
    transform=fig.transFigure+offset_top)

info_bot_center = ax.text(
    info_top_center.get_window_extent(renderer).x0/fig.bbox.width,
    info_top_center.get_window_extent(renderer).y0/fig.bbox.height,
    'Influencé : {}'.format(reader[sid]['Influenced']),
    ha='left', va='top', fontsize=14, fontweight='bold',
    transform=fig.transFigure+linespacing)

info_top_right = ax.text(
    ax.bbox.x1/fig.bbox.width,
    fig_title.get_window_extent(renderer).y0/fig.bbox.height,
    "Altitude du sol : {} m".format(elev),
    ha='right', va='top', fontsize=14, fontweight='bold',
    transform=fig.transFigure+offset_top)

info_bot_right = ax.text(
    info_top_right.get_window_extent(renderer).x0/fig.bbox.width,
    info_top_right.get_window_extent(renderer).y0/fig.bbox.height,
    "Aquifère : Roc",
    ha='left', va='top', fontsize=14, fontweight='bold',
    transform=fig.transFigure+linespacing)

# Setup the top and bottom margin.
fig.canvas.draw()
xaxis_bbox_bott, _ = ax.xaxis.get_ticklabel_extents(renderer)
sepline_bbox = rect1.get_window_extent(renderer)

tm = 1 - (info_bot_center.get_window_extent(renderer).y0 -
          12/72 * fig.dpi)/fig.bbox.height
bm = (sepline_bbox.y1 +
      ax.bbox.y0 - xaxis_bbox_bott.y0 +
      12/72 * fig.dpi
      )/fig.bbox.height
ax.set_position([lm, bm, 1-lm-rm, 1-bm-tm])

fig.savefig(osp.join(__rootdir__, 'ressources', 'test.pdf'))
fig.savefig(osp.join(__rootdir__, 'ressources', 'test.svg'))
