# -*- coding: utf-8 -*-
"""
Created on Wed Oct 25 20:24:09 2017
@author: jsgosselin
"""

# ---- Standard library imports
import os
from calendar import monthrange
import datetime as dt
import io

# ---- Third party imports
import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.transforms as transforms
from matplotlib.transforms import ScaledTranslation
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure
from qtpy.QtCore import Qt
from qtpy.QtGui import QImage
from qtpy.QtWidgets import QMainWindow, QApplication

# ---- Local imports
from sardes.config.gui import get_iconsize
from sardes.api.timeseries import DataType
from sardes.config.locale import _
from sardes.api.tools import SardesTool
from sardes.utils.qthelpers import (
    create_action, create_toolbutton, create_mainwindow_toolbar)


RGB = ["#ccebc5", "#a8ddb5", "#7bccc4", "#4eb3d3", "#2b8cbe"]
MONTHS = np.array(['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun',
                   'Jui', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc'])


class SatisticalHydrographTool(SardesTool):
    def __init__(self, parent):
        super().__init__(
            parent,
            name='statistical_hydrograph_tool',
            text=_("Statistical Hydrograph"),
            icon='show_barplot',
            tip=_("Show the statistical hydrograph for this record.")
            )

    def __init_toolwidget__(self):
        toolwidget = SatisticalHydrographWidget()
        toolwidget.canvas.set_data(
            self.parent.model()
            .dataf[[DataType.WaterLevel, 'datetime']]
            .set_index('datetime', drop=True))
        return toolwidget

    def __title__(self):
        obs_well_data = self.parent.model()._obs_well_data
        window_title = '{}'.format(obs_well_data['obs_well_id'])
        if obs_well_data['common_name']:
            window_title += ' - {}'.format(obs_well_data['common_name'])
        if obs_well_data['municipality']:
            window_title += ' ({})'.format(obs_well_data['municipality'])
        return window_title


class SatisticalHydrographWidget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas = SatisticalHydrographCanvas()
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setCentralWidget(self.canvas)
        self.setup_toolbar()

    def setup_toolbar(self):
        toolbar = create_mainwindow_toolbar("stat hydrograph toolbar")
        self.addToolBar(toolbar)
        self.save_figure_btn = create_toolbutton(
            self, icon='save',
            text=_("Save"),
            tip=_('Save the figure to a file'),
            shortcut='Ctrl+S',
            triggered=self.canvas.toolbar.save_figure,
            iconsize=get_iconsize())
        toolbar.addWidget(self.save_figure_btn)

        self.copy_to_clipboard_btn = create_toolbutton(
            self, icon='copy_clipboard',
            text=_("Copy"),
            tip=_("Put a copy of the figure on the Clipboard."),
            triggered=self.canvas.copy_to_clipboard,
            shortcut='Ctrl+C',
            iconsize=get_iconsize())
        toolbar.addWidget(self.copy_to_clipboard_btn)


class SatisticalHydrographCanvas(FigureCanvasQTAgg):
    """
    A matplotlib canvas where the figure is drawn.
    """
    BASE_ZOOM_SCALE = 1.25

    def __init__(self):
        figure = SatisticalHydrographFigure(figsize=(8, 6), facecolor='white')
        super().__init__(figure)
        self._setup_axes()
        self.wlevels = None
        self._last_month = 12
        self._pool = 'all'
        self._cur_year = 2016

        # Setup a matplotlib navigation toolbar, but hide it.
        toolbar = NavigationToolbar2QT(self, self)
        toolbar.hide()

    def _setup_axes(self):
        # Create the main axe.
        ax = self.figure.add_axes([0, 0, 1, 1], zorder=1)
        ax.set_facecolor('1')
        ax.grid(axis='y', color='0.65', linestyle='-', linewidth=0.5,
                dashes=[10, 3])
        ax.set_axisbelow(True)
        ax.tick_params(axis='x', which='both', length=3)
        ax.tick_params(axis='y', which='both', length=0)

        # Setup yaxis.
        ax.set_ylabel("Niveau d'eau en m sous la surface",
                      fontsize=16, labelpad=10)

        # Setup xaxis.
        ax.set_xticks(np.arange(-0.5, 11.51))
        ax.set_xticklabels([])

    def copy_to_clipboard(self):
        buf = io.BytesIO()
        self.figure.savefig(buf)
        QApplication.clipboard().setImage(QImage.fromData(buf.getvalue()))
        buf.close()

    def set_data(self, wlevels):
        self.wlevels = wlevels
        self._cur_year = np.max(self.wlevels.index.year)
        self.plot_statistical_hydrograph()

    def plot_statistical_hydrograph(self):
        # Organize month order and define first and last datetime value
        # for the current data.
        ax = self.figure.axes[0]
        if self._last_month == 12:
            year_lbl = '{} {:d}'.format(_("Year"), self._cur_year)
            mth_idx = np.arange(12)
            dtstart = dt.datetime(self._cur_year, 1, 1)
            dtend = dt.datetime(self._cur_year, 12, 31)
        else:
            year_lbl = "Years %d-%d" % (self._cur_year - 1, self._cur_year)
            mth_idx = np.arange(self._last_month, 12)
            mth_idx = np.hstack((mth_idx, np.arange(12 - len(mth_idx))))
            dtstart = dt.datetime(self._cur_year - 1, mth_idx[0] + 1, 1)
            dtend = dt.datetime(
                self._cur_year,
                mth_idx[-1] + 1,
                monthrange(self._cur_year, mth_idx[-1] + 1)[-1])

        # Generate the percentiles.
        q = [100, 90, 75, 50, 25, 10, 0]
        percentiles, nyear = compute_monthly_statistics(
            self.wlevels, q, self._pool)

        # Plot the percentiles.
        xpos = np.arange(12)
        idx = [0, 1, 2, 4, 5, 6]
        for i in range(len(idx)-1):
            ax.bar(
                xpos,
                percentiles[mth_idx, idx[i]] - percentiles[mth_idx, idx[i+1]],
                width=0.9, bottom=percentiles[mth_idx, idx[i+1]],
                color=RGB[i], edgecolor='black', linewidth=0.5)
        ax.plot(xpos, percentiles[mth_idx, 3], '^k')

        # Plot the current water level data series.
        cur_wlevels = self.wlevels[
            (self.wlevels.index >= dtstart) & (self.wlevels.index <= dtend)]
        cur_rel_time = cur_wlevels.index.dayofyear.values / 365 * 12 - 0.5
        ax.plot(cur_rel_time, cur_wlevels.values, '.', color='red', ms=3.5)

        # Axe limits.
        ymax = max(np.max(percentiles), np.max(cur_wlevels.values))
        ymin = min(np.min(percentiles), np.min(cur_wlevels.values))
        yrange = ymax - ymin
        yoffset = 0.1 / self.figure.get_figwidth() * yrange
        ax.axis([-0.75, 11.75, ymin-yoffset, ymax+yoffset])
        ax.invert_yaxis()

        # Set xaxis label.
        ax.set_xlabel(year_lbl, fontsize=16, labelpad=30)

        xlabelspos = np.arange(12)
        y = ymax+yoffset
        for m, n, x in zip(MONTHS[mth_idx], nyear[mth_idx], xlabelspos):
            offset = transforms.ScaledTranslation(
                0, -5/72, self.figure.dpi_scale_trans)
            ax.text(x, y, m, ha='center', va='top', fontsize=12,
                    transform=ax.transData+offset)
            offset = transforms.ScaledTranslation(
                0, -18/72, self.figure.dpi_scale_trans)
            ax.text(x, y, '(%d)' % n, ha='center', va='top', fontsize=9,
                    transform=ax.transData+offset)

        self.setup_legend()

    def setup_legend(self):
        """
        Setup a custom legend for this graph.

        We to do this because we want the text to be placed below each
        legend handle.
        """
        ax = self.figure.axes[0]
        ax2 = self.figure.add_axes([0, 0, 1, 1], facecolor=None)
        ax2.axis('off')

        labels = ['<10', '10-24', '25-75', '76-90', '>90',
                  _('Median'), _('Measures')]
        handlelength = 0.4
        handleheight = 0.15
        labelspacing = 0.3
        borderaxespad = 5
        fontsize = 10
        handletextpad = 5

        trans_text = (
            self.figure.dpi_scale_trans +
            ScaledTranslation(0, 1, ax.transAxes) +
            ScaledTranslation(0, borderaxespad/72, self.figure.dpi_scale_trans)
            )
        trans_patch = (
            self.figure.dpi_scale_trans +
            ScaledTranslation(0, 1, ax.transAxes) +
            ScaledTranslation(0, (borderaxespad + fontsize + handletextpad)/72,
                              self.figure.dpi_scale_trans))
        for i in range(5):
            patch = mpl.patches.Rectangle(
                (handlelength * i + labelspacing * i, 0),
                handlelength, handleheight,
                fc=RGB[i], ec='black', lw=0.5, transform=trans_patch)
            ax2.add_patch(patch)
            ax2.text(handlelength * (i + 1/2) + labelspacing * i, 0, labels[i],
                     ha='center', va='bottom', fontsize=fontsize,
                     transform=trans_text)
        i += 1
        ax2.plot([handlelength * (i + 1/2) + labelspacing * i],
                 [handleheight / 2],
                 marker='^', color='black', ms=10, ls='',
                 transform=trans_patch)
        ax2.text(handlelength * (i + 1/2) + labelspacing * i, 0, labels[i],
                 ha='center', va='bottom', fontsize=fontsize,
                 transform=trans_text)
        i += 1
        ax2.plot([handlelength * (i + 1/2) + labelspacing * i],
                 [handleheight / 2],
                 marker='.', color='red', ms=10, ls='', mew=2,
                 transform=trans_patch)
        ax2.text(handlelength * (i + 1/2) + labelspacing * i, 0, labels[i],
                 ha='center', va='bottom', fontsize=fontsize,
                 transform=trans_text)


class SatisticalHydrographFigure(Figure):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.set_tight_layout(True)

    def tight_layout(self, *args, **kargs):
        """
        Override matplotlib method to setup the margins of the axes.
        """
        if len(self.axes):
            fheight = self.get_figheight()
            fwidth = self.get_figwidth()
            left_margin = 0.85 / fwidth
            right_margin = 0.1 / fwidth
            bottom_margin = 0.8 / fheight
            top_margin = 0.5 / fheight
            self.axes[0].set_position([
                left_margin, bottom_margin,
                1 - left_margin - right_margin, 1 - bottom_margin - top_margin
                ])

    def set_size_inches(self, *args, **kargs):
        """
        Override matplotlib method to force a call to tight_layout when
        set_size_inches is called. This allow to keep the size of the margins
        fixed when the canvas of this figure is resized.
        """
        super().set_size_inches(*args, **kargs)
        self.tight_layout()


def compute_monthly_statistics(tseries, q, pool='all'):
    percentiles = []
    nyear = []
    mly_values = []

    if pool == 'all':
        for m in range(1, 13):
            mly_stats = tseries.loc[tseries.index.month == m]
            mly_values.append(mly_stats.values)
            nyear.append(len(np.unique(mly_stats.index.year)))
    else:
        group = tseries.groupby([tseries.index.year, tseries.index.month])
        if pool == 'min_max_median':
            mly_stats = pd.concat(
                [group.min(), group.median(), group.max()], axis=1)
        elif pool == 'median':
            mly_stats = group.median()
        elif pool == 'mean':
            mly_stats = group.mean()
        for m in range(1, 13):
            mly_stats_m = mly_stats[mly_stats.index.get_level_values(1) == m]
            mly_values.append(mly_stats_m.values.flatten())
            nyear.append(len(mly_stats_m))

    percentiles = [np.percentile(v, q) for v in mly_values]
    return np.array(percentiles), np.array(nyear)


# def plot_10yrs_annual_statistical_hydrograph(sid, cur_year, last_month=12,
#                                              filename=None, pool='all'):

#     # Add title: Station name and ID.
#     mpad = mpl.transforms.ScaledTranslation(0, -5/72, fig.dpi_scale_trans)
#     title = "{}\nStation {}".format(stn_name, stn_id)
#     ax2.text(1, 1, title, ha='right', va='top', fontsize=12,
#              transform=ax2.transAxes+mpad)
