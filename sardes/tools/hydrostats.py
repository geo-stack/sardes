# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
from datetime import datetime
from calendar import monthrange
import datetime as dt
import io
import os.path as osp

# ---- Third party imports
import matplotlib as mpl
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.transforms as transforms
from matplotlib.transforms import ScaledTranslation
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure
from qtpy.QtCore import Qt
from qtpy.QtGui import QImage
from qtpy.QtWidgets import (
    QApplication, QComboBox, QGridLayout, QLabel, QMainWindow, QWidget,
    QFileDialog)

# ---- Local imports
from sardes.config.gui import get_iconsize
from sardes.api.timeseries import DataType
from sardes.config.locale import _
from sardes.config.ospath import (
    get_select_file_dialog_dir, set_select_file_dialog_dir)
from sardes.api.tools import SardesTool
from sardes.utils.qthelpers import (
    create_toolbutton, create_mainwindow_toolbar)

MONTHS = np.array([
    _('Jan'), _('Feb'), _('Mar'), _('Apr'), _('May'), _('Jun'),
    _('Jul'), _('Aug'), _('Sep'), _('Oct'), _('Nov'), _('Dec')])


class SatisticalHydrographTool(SardesTool):
    """
    A tool to produce statistical hydrograph from piezometric timeseries.
    """

    def __init__(self, table):
        super().__init__(
            table,
            name='statistical_hydrograph_tool',
            text=_("Statistical Hydrograph"),
            icon='show_barplot',
            tip=_("Show the statistical hydrograph for this record.")
            )

    # ---- SardesTool API
    def __update_toolwidget__(self, toolwidget):
        toolwidget.set_data(self.table.get_formatted_data())
        toolwidget.set_obswell_data(self.table.model()._obs_well_data)

    def __create_toolwidget__(self):
        return SatisticalHydrographWidget()

    def __title__(self):
        obs_well_data = self.table.model()._obs_well_data
        window_title = '{}'.format(obs_well_data['obs_well_id'])
        if obs_well_data['common_name']:
            window_title += ' - {}'.format(obs_well_data['common_name'])
        if obs_well_data['municipality']:
            window_title += ' ({})'.format(obs_well_data['municipality'])
        return window_title


class SatisticalHydrographWidget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__()
        self.obs_well_id = None
        self.canvas = SatisticalHydrographCanvas()
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setCentralWidget(self.canvas)
        self.setup_toolbar()

    def year(self):
        """
        Return the year for which the statistical hydrograph
        needs to be plotted.
        """
        return (
            None if not self.year_cbox.count() else
            int(self.year_cbox.currentText()))

    def month(self):
        """
        Return the integer value of the month for which the
        statistical hydrograph needs to be plotted.
        """
        return (
            None if not self.month_cbox.count() else
            self.month_cbox.currentIndex() + 1)

    def set_obswell_data(self, obswell_data):
        """Set the observation well data."""
        self.obs_well_id = obswell_data['obs_well_id']

    def set_data(self, wlevels):
        """
        Set the data of the figure and update the gui.

        Parameters
        ----------
        wlevels : Series
            A pandas timeseries containing formatted water level data in
            meters above mean sea level.
        """
        try:
            wlevels = (
                wlevels[[DataType.WaterLevel, 'datetime']]
                .set_index('datetime', drop=True))
        except KeyError:
            pass

        self.year_cbox.blockSignals(True)
        self.month_cbox.blockSignals(True)
        curyear = self.year_cbox.currentText()
        curmonth_idx = self.month_cbox.currentIndex()
        self.year_cbox.clear()
        self.month_cbox.clear()
        if not wlevels.empty:
            years = np.unique(wlevels.index.year).astype('str').tolist()
            self.year_cbox.addItems(years)
            if curyear in years:
                self.year_cbox.setCurrentIndex(years.index(curyear))
            else:
                self.year_cbox.setCurrentIndex(len(years) - 1)
            self.month_cbox.addItems(MONTHS.tolist())
            if curmonth_idx == -1:
                self.month_cbox.setCurrentIndex(11)
            else:
                self.month_cbox.setCurrentIndex(curmonth_idx)
        self.year_cbox.blockSignals(False)
        self.month_cbox.blockSignals(False)

        self.canvas.set_data(wlevels, self.year(), self.month())
        self._update_buttons_state()

    def setup_toolbar(self):
        """Setup the toolbar of this widget."""
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

        self.save_multipdf_statistical_graphs_btn = create_toolbutton(
            self, icon='file_multi_pages',
            text=_("Multi Pages PDF"),
            tip=_("Create a multi-page pdf file containing the statistical "
                  "hydrographs (one per page) for each year where data "
                  "are available."),
            triggered=self._select_multipdf_statistical_graphs_filename,
            iconsize=get_iconsize())
        toolbar.addWidget(self.save_multipdf_statistical_graphs_btn)

        # Add navigation and animation tools
        toolbar.addSeparator()

        self.move_backward_btn = create_toolbutton(
            self, icon='file_previous',
            text=_("Move Backward"),
            tip=_("Move the x-axis of the statistical hydrograph "
                  "one month backward."),
            triggered=self.move_backward,
            iconsize=get_iconsize())
        toolbar.addWidget(self.move_backward_btn)

        self.move_forward_btn = create_toolbutton(
            self, icon='file_next',
            text=_("Move Forward"),
            tip=_("Move the x-axis of the statistical hydrograph "
                  "one month forward."),
            triggered=self.move_forward,
            iconsize=get_iconsize())
        toolbar.addWidget(self.move_forward_btn)

        year_labl = QLabel(_('Year:'))
        self.year_cbox = QComboBox()
        self.year_cbox.currentIndexChanged.connect(
            self._handle_current_yearmonth_changed)

        year_widget = QWidget()
        year_layout = QGridLayout(year_widget)
        year_layout.setContentsMargins(5, 0, 0, 0)
        year_layout.addWidget(year_labl, 0, 0)
        year_layout.addWidget(self.year_cbox, 0, 1)
        toolbar.addWidget(year_widget)

        # Setup the month widget.
        month_labl = QLabel(_('Month:'))
        self.month_cbox = QComboBox()
        self.month_cbox.addItems(MONTHS.tolist())
        self.month_cbox.setCurrentIndex(11)
        self.month_cbox.currentIndexChanged.connect(
            self._handle_current_yearmonth_changed)

        month_widget = QWidget()
        month_layout = QGridLayout(month_widget)
        month_layout.setContentsMargins(5, 0, 0, 0)
        month_layout.addWidget(month_labl, 0, 0)
        month_layout.addWidget(self.month_cbox, 0, 1)
        toolbar.addWidget(month_widget)

        self._update_buttons_state()

    def _update_buttons_state(self):
        """Update the enable state of the buttons."""
        year_index = self.year_cbox.currentIndex()
        year_count = self.year_cbox.count()
        month_index = self.month_cbox.currentIndex()
        month_count = self.month_cbox.count()
        if year_count and month_count:
            self.save_multipdf_statistical_graphs_btn.setEnabled(True)
            self.move_forward_btn.setEnabled(True)
            self.move_backward_btn.setEnabled(True)
            if month_index == month_count - 1 and year_index == year_count - 1:
                self.move_forward_btn.setEnabled(False)
            if month_index == 0 and year_index == 0:
                self.move_backward_btn.setEnabled(False)
        else:
            self.save_multipdf_statistical_graphs_btn.setEnabled(False)
            self.move_forward_btn.setEnabled(False)
            self.move_backward_btn.setEnabled(False)

    def _select_multipdf_statistical_graphs_filename(self):
        """
        Show a file dialog to allow the user to select a filename where to
        save the multipage pdf containing the statistical hydrogaphs.
        """
        namefilters = 'Portable Document Format (*.pdf)'
        dirname = get_select_file_dialog_dir()
        filename = "statistical_graphs_{}_(2007-2010).pdf".format(
            self.obs_well_id)
        filename, filefilter = QFileDialog.getSaveFileName(
            self,
            _("Save Multi Statistical Graphs"),
            osp.join(dirname, filename),
            namefilters)
        if filename:
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            filename = osp.abspath(filename)
            set_select_file_dialog_dir(osp.dirname(filename))

            QApplication.setOverrideCursor(Qt.WaitCursor)
            self.canvas.save_multipdf_statistical_graphs(filename)
            QApplication.restoreOverrideCursor()

    def _handle_current_yearmonth_changed(self):
        """
        Handle when the user changed the month or the year for which the
        statistical hydrograph needs to be plotted.
        """
        self.canvas.set_year(self.year(), update=False)
        self.canvas.set_month(self.month(), update=True)
        self._update_buttons_state()

    def move_forward(self):
        """
        Move the x-axis of the statistical hydrograph one month forward.
        """
        if self.year_cbox.count() == 0:
            return

        year_cur_idx = self.year_cbox.currentIndex()
        month_cur_idx = self.month_cbox.currentIndex()
        if month_cur_idx == self.month_cbox.count() - 1:
            if year_cur_idx == self.year_cbox.count() - 1:
                return
            else:
                year_cur_idx += 1
                month_cur_idx = 0
        else:
            month_cur_idx += 1

        # We block the signals of the combo boxes to avoid unecessary
        # updates of the figure canvas.
        self.year_cbox.blockSignals(True)
        self.month_cbox.blockSignals(True)
        self.year_cbox.setCurrentIndex(year_cur_idx)
        self.month_cbox.setCurrentIndex(month_cur_idx)
        self.year_cbox.blockSignals(False)
        self.month_cbox.blockSignals(False)

        self._handle_current_yearmonth_changed()

    def move_backward(self):
        """
        Move the x-axis of the statistical hydrograph one month backward.
        """
        if self.year_cbox.count() == 0:
            return

        year_cur_idx = self.year_cbox.currentIndex()
        month_cur_idx = self.month_cbox.currentIndex()
        if month_cur_idx == 0:
            if year_cur_idx == 0:
                return
            else:
                month_cur_idx = self.month_cbox.count() - 1
                year_cur_idx += -1
        else:
            month_cur_idx += -1

        # We block the signals of the combo boxes to avoid unecessary
        # updates of the figure canvas.
        self.year_cbox.blockSignals(True)
        self.month_cbox.blockSignals(True)
        self.year_cbox.setCurrentIndex(year_cur_idx)
        self.month_cbox.setCurrentIndex(month_cur_idx)
        self.year_cbox.blockSignals(False)
        self.month_cbox.blockSignals(False)

        self._handle_current_yearmonth_changed()


class SatisticalHydrographCanvas(FigureCanvasQTAgg):
    """
    A matplotlib canvas where the figure is drawn.
    """

    def __init__(self, figsize=(8, 6)):
        figure = SatisticalHydrographFigure(figsize=figsize, facecolor='white')
        super().__init__(figure)
        self.wlevels = None
        self.year = None
        self.month = 1
        self.pool = 'min_max_median'

        # Setup a matplotlib navigation toolbar, but hide it.
        toolbar = NavigationToolbar2QT(self, self)
        toolbar.hide()

    def copy_to_clipboard(self):
        """Put a copy of the figure on the clipboard."""
        buf = io.BytesIO()
        self.figure.savefig(buf)
        QApplication.clipboard().setImage(QImage.fromData(buf.getvalue()))
        buf.close()

    def save_multipdf_statistical_graphs(self, filename):
        """
        Create a multipage pdf file containing the statistical hydrographs
        (one per page) for each year where data are available.
        """
        years = np.unique(self.wlevels.index.year).tolist()
        with PdfPages(filename) as pdf:
            for year in years:
                self.figure.plot_statistical_hydrograph(
                    self.wlevels, year, 12, self.pool)
                pdf.savefig(self.figure)

        # Restore figure initial state.
        self._update_figure()

    def set_pool(self, pool):
        """
        Set the pooling mode to use when calculating monthly
        percentile values.
        """
        self.pool = pool
        self._update_figure()

    def set_data(self, wlevels, year, month):
        """
        Set the data of the statistical hydrograph.

        Parameters
        ----------
        wlevels : Series
            A pandas timeseries containing formatted water level data in
            meters above mean sea level.
        year : int
            The year for which the statistical hydrograph needs to be plotted.
        month : int
            An integer value corresponding to the month for which the
            statistical hydrograph needs to be plotted, where 1 corresponds
            to January and 12 to december.
        """
        self.year = year
        self.month = month
        self.wlevels = wlevels
        self._update_figure()

    def set_year(self, year, update=True):
        """Set the year for which the statistical hydrograph is plotted."""
        self.year = year
        if update:
            self._update_figure()

    def set_month(self, month, update=True):
        """Set the month for which the statistical hydrograph is plotted."""
        self.month = month
        if update:
            self._update_figure()

    def _update_figure(self):
        """Update the statistical hydrograph."""
        self.figure.plot_statistical_hydrograph(
            self.wlevels, self.year, self.month, self.pool)


class SatisticalHydrographFigure(Figure):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.set_tight_layout(True)
        self.xlabelpad = 10
        self.ylabelpad = 10
        self.monthlabels = []
        self.ncountlabels = []
        self.leghandles = []
        self.leglabels = []
        self.percentile_bars = {}
        self.percentile_qpairs = [
            (100, 90), (90, 75), (75, 25), (25, 10), (10, 0)]
        self.percentile_labels = {
            (100, 90): '>90',
            (90, 75): '76-90',
            (75, 25): '25-75',
            (25, 10): '10-24',
            (10, 0): '<10'}
        self.percentile_rbg = {
            (100, 90): "#ccebc5",
            (90, 75): "#a8ddb5",
            (75, 25): "#7bccc4",
            (25, 10): "#4eb3d3",
            (10, 0): "#2b8cbe"}

        self.setup_axes()
        self.setup_artists()
        self.setup_legend()

    def setup_axes(self):
        """Setup the main axes and the axes to hold the legend."""
        # Setup the axes to hold the data.
        ax = self.add_axes([0, 0, 1, 1], zorder=1)
        ax.set_facecolor('1')
        ax.grid(axis='y', color='0.65', linestyle='-', linewidth=0.5,
                dashes=[10, 3])
        ax.set_axisbelow(True)
        ax.tick_params(axis='x', which='both', length=3)
        ax.tick_params(axis='y', which='both', length=0)

        ax.set_xticks(np.arange(-0.5, 11.51))
        ax.set_xticklabels([])

        # Setup the axes to hold the legend.
        ax2 = self.add_axes([0, 0, 1, 1], facecolor=None)
        ax2.axis('off')
        ax2.set_xticks([])
        ax2.set_yticks([])
        for spine in ax2.spines.values():
            spine.set_visible(False)

    def setup_artists(self):
        """Setup the matplotlib artists that are used to plot the data."""
        ax = self.axes[0]

        # Setup the artist to plot the current water level values.
        self.cur_wlvl_plot = ax.plot(
            [], [], '.', color='red', ms=3.5)[0]

        # Setup the artist to plot the historical median water level values.
        self.med_wlvl_plot = ax.plot(np.arange(12), [1] * 12, '^k')[0]

        # Setup the artists to plot the percentile bars.
        for i, pair in enumerate(self.percentile_qpairs):
            self.percentile_bars[pair] = ax.bar(
                np.arange(12), [1] * 12, width=0.9, bottom=[0] * 12,
                color=self.percentile_rbg[pair], edgecolor='black',
                linewidth=0.5
                )

        # Setup the artists that holds the xaxis tick labels.
        self.monthlabels = []
        self.ncountlabels = []
        blended_trans = transforms.blended_transform_factory(
            ax.transData, ax.transAxes)
        for x in range(12):
            scaled_trans = transforms.ScaledTranslation(
                0, -5/72, self.dpi_scale_trans)
            self.monthlabels.append(ax.text(
                x, 0, '', ha='center', va='top', fontsize=12,
                transform=blended_trans + scaled_trans
                ))
            scaled_trans = transforms.ScaledTranslation(
                0, -18/72, self.dpi_scale_trans)
            self.ncountlabels.append(ax.text(
                x, 0, '', ha='center', va='top', fontsize=9,
                transform=blended_trans + scaled_trans))

    def tight_layout(self, *args, **kargs):
        """
        Override matplotlib method to setup the margins of the axes.
        """
        if len(self.axes) == 0:
            return
        try:
            # This is required when saving the figure in some format like
            # pdf and svg.
            renderer = self.canvas.get_renderer()
        except AttributeError:
            # With more recent version of matplotlib we need to use 'draw_idle'
            # instead of 'draw'.
            # see cgq-qgc/sardes#553.
            self.canvas.draw_idle()
            return

        figborderpad = 15 / 72 * self.dpi
        figbbox = self.bbox
        ax = self.axes[0]
        axbbox = ax.bbox

        bbox_xaxis_bottom, bbox_xaxis_top = (
            ax.xaxis.get_ticklabel_extents(renderer))
        bbox_yaxis_left, bbox_yaxis_right = (
            ax.yaxis.get_ticklabel_extents(renderer))

        bbox_yaxis_label = ax.yaxis.label.get_window_extent(renderer)
        bbox_xaxis_label = ax.xaxis.label.get_window_extent(renderer)

        # Calculate left margin width.
        yaxis_width = axbbox.x0 - bbox_yaxis_left.x0
        ylabel_width = bbox_yaxis_label.width + self.ylabelpad
        left_margin = (
            yaxis_width + ylabel_width + figborderpad
            ) / figbbox.width

        # Calculate right margin width.
        xaxis_width = max(
            bbox_xaxis_bottom.x1 - axbbox.x1,
            bbox_xaxis_top.x1 - axbbox.x1,
            0)
        right_margin = (xaxis_width + figborderpad) / figbbox.width

        # Calculate bottom margin height.
        xlabel_y0 = min(
            [bbox_xaxis_bottom.y0] +
            [lab.get_window_extent(renderer).y0 for lab in self.ncountlabels])
        xaxis_height = axbbox.y0 - xlabel_y0
        xlabel_height = bbox_xaxis_label.height + self.xlabelpad
        bottom_margin = (
            xaxis_height + xlabel_height + figborderpad
            ) / figbbox.height

        # Calculate top margin height.
        leg_y1 = max(
            [axbbox.y1] +
            [hdl.get_window_extent(renderer).y1 for hdl in self.leghandles])
        legend_height = leg_y1 - axbbox.y1
        top_margin = (
            figborderpad + legend_height
            ) / figbbox.height

        ax.set_position([
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

    def plot_statistical_hydrograph(self, wlevels, curyear, lastmonth,
                                    pool='min_max_median'):
        # Organize month order and define first and last datetime value
        # for the current data.
        ax = self.axes[0]
        if wlevels is None:
            wlevels = pd.DataFrame(
                [],
                columns=['datetime', DataType.WaterLevel])
            wlevels['datetime'] = pd.to_datetime(wlevels['datetime'])
            wlevels = wlevels.set_index('datetime', drop=True)
        lastmonth = 12 if lastmonth is None else lastmonth
        if curyear is None:
            curyear = datetime.now().year
        wlevels = wlevels.dropna()

        if lastmonth == 12:
            year_lbl = '{} {:d}'.format(_("Year"), curyear)
            mth_idx = np.arange(12)
            dtstart = dt.datetime(curyear, 1, 1)
            dtend = dt.datetime(curyear, 12, 31)
        else:
            year_lbl = _("Years {:d}-{:d}").format(curyear - 1, curyear)
            mth_idx = np.hstack(
                (np.arange(lastmonth, 12), np.arange(0, lastmonth)))
            dtstart = dt.datetime(curyear - 1, mth_idx[0] + 1, 1)
            dtend = dt.datetime(
                curyear,
                mth_idx[-1] + 1,
                monthrange(curyear, mth_idx[-1] + 1)[-1])

        # Generate the percentiles.
        q = list(set(
            [50] +
            [item for sublist in self.percentile_qpairs for item in sublist]
            ))
        percentiles, nyear = compute_monthly_percentiles(
            wlevels, q, pool=pool)
        percentiles = percentiles.iloc[mth_idx]
        nyear = nyear[mth_idx]

        # Update the percentile bars and median plot.
        for qpair in self.percentile_qpairs:
            container = self.percentile_bars[qpair]
            for i, bar in enumerate(container.patches):
                ytop = percentiles.iloc[i][qpair[0]]
                ybot = percentiles.iloc[i][qpair[1]]
                bar.set_y(ybot)
                bar.set_height(ytop - ybot)
        self.med_wlvl_plot.set_ydata(percentiles[50])

        # Plot the current water level data series.
        cur_wlevels = wlevels[
            (wlevels.index >= dtstart) & (wlevels.index <= dtend)]

        # datetime.timestamp() returns a POSIX timestamp. However, naive
        # datetime instances are assumed to represent local time.
        # This is different from numpy.datetime64 that are always stored and
        # considered as tz-naive dates.

        # Therefore, we need to supply tzinfo=timezone.utc to our datetime
        # instances before using their timestamp value in calculations
        # involving numpy.datetime64 values.
        # https://docs.python.org/3/library/datetime.html#datetime.datetime.timestamp
        cur_time_min = dtstart.replace(tzinfo=dt.timezone.utc).timestamp()
        cur_time_max = dtend.replace(tzinfo=dt.timezone.utc).timestamp()
        if len(cur_wlevels):
            # We normalize the time data to the range of the xaxis.
            cur_rel_time = (
                cur_wlevels.index.values.astype('datetime64[s]').astype(float))
            cur_rel_time = (
                (cur_rel_time - cur_time_min) / (cur_time_max - cur_time_min))
            cur_rel_time = cur_rel_time * 12 - 0.5
        else:
            cur_rel_time = []
        self.cur_wlvl_plot.set_data(cur_rel_time, cur_wlevels.values)

        # Set xaxis and yaxis label.
        ax.set_xlabel(year_lbl, fontsize=16, labelpad=30)
        ax.set_ylabel(_("Water level altitude (m MSL)"),
                      fontsize=16, labelpad=10)

        # Axe limits and ticks.
        yvals = np.nan_to_num(
            percentiles.values.flatten().tolist() +
            cur_wlevels.values.flatten().tolist())
        ymin = min(yvals)
        ymax = max(yvals)
        yrange = max(ymax - ymin, 0.01)
        yoffset = 0.1 / self.get_figwidth() * yrange
        ax.axis([-0.75, 11.75, ymin - yoffset, ymax + yoffset])

        for i, (m, n) in enumerate(zip(MONTHS[mth_idx], nyear)):
            self.monthlabels[i].set_text(m)
            self.ncountlabels[i].set_text('(%d)' % n)

        self.canvas.draw()

    def setup_legend(self):
        """
        Setup a custom legend for this graph.

        We to do this because we want the text to be placed below each
        legend handle.
        """
        ax = self.axes[0]
        ax2 = self.axes[1]
        ax2.clear()
        self.leghandles = []
        self.leglabels = []

        handlelength = 0.4
        handleheight = 0.15
        labelspacing = 0.3
        borderaxespad = 5
        fontsize = 10
        handletextpad = 5

        trans_text = (
            self.dpi_scale_trans +
            ScaledTranslation(0, 1, ax.transAxes) +
            ScaledTranslation(0, borderaxespad/72, self.dpi_scale_trans)
            )
        trans_patch = (
            self.dpi_scale_trans +
            ScaledTranslation(0, 1, ax.transAxes) +
            ScaledTranslation(0, (borderaxespad + fontsize + handletextpad)/72,
                              self.dpi_scale_trans))

        # Create the legend handles for the percentile ranges.
        for i, qpair in enumerate(reversed(self.percentile_qpairs)):
            patch = mpl.patches.Rectangle(
                (handlelength * i + labelspacing * i, 0),
                handlelength, handleheight,
                fc=self.percentile_rbg[qpair], ec='black', lw=0.5,
                transform=trans_patch)
            self.leghandles.append(patch)
            ax2.add_patch(patch)
            ax2.text(handlelength * (i + 1/2) + labelspacing * i, 0,
                     self.percentile_labels[qpair],
                     ha='center', va='bottom', fontsize=fontsize,
                     transform=trans_text)

        i += 1
        # Create the legend handle for the median.
        self.leghandles.append(ax2.plot(
            [handlelength * (i + 1/2) + labelspacing * i],
            [handleheight / 2],
            marker='^', color='black', ms=10, ls='',
            transform=trans_patch
            )[0])
        ax2.text(handlelength * (i + 1/2) + labelspacing * i, 0, _('Median'),
                 ha='center', va='bottom', fontsize=fontsize,
                 transform=trans_text)
        i += 1
        # Create the legend handle for the measurements.
        self.leghandles.append(ax2.plot(
            [handlelength * (i + 1/2) + labelspacing * i],
            [handleheight / 2],
            marker='.', color='red', ms=10, ls='', mew=2,
            transform=trans_patch
            )[0])
        ax2.text(handlelength * (i + 1/2) + labelspacing * i, 0, _('Measures'),
                 ha='center', va='bottom', fontsize=fontsize,
                 transform=trans_text)

        self.canvas.draw()


def compute_monthly_percentiles(tseries, q, pool='all'):
    """
    Parameters
    ----------
    tseries: array_like
        Pandas time series.
    q: array_like
        Percentile or sequence of percentiles to compute, which must
        be between 0 and 100 inclusive.
    pool: str
        The method used to compute the monthly percentiles.

    Returns
    -------
    percentiles : DataFrame
        A pandas dataframe containing the computed monthly percentiles, where
        the indexes are the months and the columns the q values. The number
        of year of data used to compute each monthly value is also provided
        in the column named 'nyear'
    """
    nyear = np.array([0] * 12)
    percentiles = pd.DataFrame(
        data=np.nan,
        index=np.arange(1, 13),
        columns=q)
    percentiles.index.name = 'month'
    if tseries.empty:
        return percentiles, nyear

    # Pool the data for each month separately.
    monthly_data_pools = [[]] * 12
    if pool == 'all':
        # When pool is 'all', we use all the data available to compute the
        # monthly statistics.
        for i in range(12):
            data = tseries.loc[tseries.index.month == i + 1]
            if not data.empty:
                monthly_data_pools[i] = data.values
                nyear[i] = len(np.unique(data.index.year))
    else:
        group = tseries.groupby([tseries.index.year, tseries.index.month])
        if pool == 'min_max_median':
            # When pool is 'min_max_median', we compute the montly
            # statistics from the minimum, maximum and median value of
            # of each month of each year.
            monthly_stats = pd.concat(
                [group.min(), group.median(), group.max()], axis=1)
        elif pool == 'median':
            # When pool is 'median', we compute the montly statistics
            # from the median value of each month of each year.
            monthly_stats = group.median()
        elif pool == 'mean':
            # When pool is 'mean', we compute the montly statistics
            # from the mean value of each month of each year.
            monthly_stats = group.mean()
        for i in range(12):
            data = (monthly_stats
                    [monthly_stats.index.get_level_values(1) == i + 1])
            monthly_data_pools[i] = data.values.flatten()
            nyear[i] = len(data)

    for i in range(12):
        month = i + 1
        if len(monthly_data_pools[i]):
            percentiles.loc[month] = np.percentile(monthly_data_pools[i], q)
    percentiles = percentiles.round(5)

    return percentiles, nyear


if __name__ == "__main__":
    import sys
    from sardes.utils.qthelpers import create_application
    from sardes.database.accessors import DatabaseAccessorSardesLite
    from sardes.utils.data_operations import format_reading_data

    app = create_application()

    database = "D:/Desktop/rsesq_prod_06-07-2021.db"
    accessor = DatabaseAccessorSardesLite(database)

    sampling_feature_uuid = (
        accessor._get_sampling_feature_uuid_from_name('01070001'))
    readings_data = accessor.get_timeseries_for_obs_well(
        sampling_feature_uuid, [DataType.WaterLevel])

    repere_data = accessor.get('repere_data')
    repere_data = (
        repere_data
        [repere_data['sampling_feature_uuid'] == sampling_feature_uuid]
        .copy())

    obswell_data = accessor.get('observation_wells_data').loc[
        sampling_feature_uuid]

    formatted_data = format_reading_data(readings_data, repere_data)

    wlevels = (formatted_data[[DataType.WaterLevel, 'datetime']]
               .set_index('datetime', drop=True))
    percentiles, nyear = compute_monthly_percentiles(
        wlevels,
        q=[100, 90, 75, 50, 25, 10, 0],
        pool='min_max_median')
    print(percentiles)

    widget = SatisticalHydrographWidget()
    widget.set_data(formatted_data)
    widget.set_obswell_data(obswell_data)
    widget.show()

    sys.exit(app.exec_())
