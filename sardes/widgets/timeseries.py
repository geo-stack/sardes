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
from collections.abc import Mapping
import datetime
import io

# ---- Third party imports
import matplotlib as mpl
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure as MplFigure
from matplotlib.axes import Axes as MplAxes
from matplotlib.transforms import Bbox
from matplotlib.widgets import RectangleSelector, SpanSelector
from matplotlib.dates import num2date, date2num
import numpy as np
from qtpy.QtCore import (Qt, Slot, QTimer, Signal, QPropertyAnimation)
from qtpy.QtGui import QGuiApplication, QKeySequence, QImage
from qtpy.QtWidgets import (
    QAction, QApplication, QMainWindow, QLabel, QWidget, QGridLayout,
    QGraphicsOpacityEffect)
import pandas as pd
from pandas.plotting import register_matplotlib_converters

# ---- Local imports
from sardes.api.timeseries import DataType
from sardes.config.locale import _
from sardes.config.gui import get_iconsize
from sardes.utils.qthelpers import (
    center_widget_to_another, create_mainwindow_toolbar, create_toolbutton,
    format_tooltip, create_toolbar_stretcher)
from sardes.widgets.buttons import (
    DropdownToolButton, SemiExclusiveButtonGroup, ToggleVisibilityToolButton)
from sardes.widgets.spinboxes import IconSpinBox


register_matplotlib_converters()
MSEC_MIN_OVERLAY_MSG_DISPLAY = 2000

rcParams = mpl.rcParams
YTICKS_LENGTH = rcParams["ytick.major.size"]
YTICKS_PAD = rcParams['ytick.major.pad']
AXIS_LABEL_FS = 12
YAXIS_LABEL_PAD = 10
FIG_PAD = 20


# ---- Data containers
class TimeSeriesGroup(Mapping):
    """
    Sardes time series group class.

    The :class:`TimeSeriesGroup` class provides a container to manage sardes
    :class:`TimeSeries` that belongs to the same data type.

    Parameters
    ----------
    data_type: DataType
        The type of data constituing the time series that are contained in
        this group.
    prop_name: str
        The common human readable name describing the data constituing
        the time series that are contained in this group.
    yaxis_inverted: bool
        A boolean to indicate whether the data should be plotted on an
        inverted y-axis (positive towards bottom).
    """

    def __init__(self, data_type, yaxis_inverted=False):
        self._timeseries = []
        self.data_type = DataType(data_type)
        self.yaxis_inverted = yaxis_inverted

    def __len__(self, key):
        return len(self._tseries)

    def __setitem__(self, key, value):
        return NotImplementedError

    def __getitem__(self, key):
        return NotImplementedError

    def __iter__(self):
        for tseries in self._timeseries:
            yield tseries

    def __str__(self):
        return self.get_merged_timeseries().__str__()

    # ---- Timeseries
    @property
    def timeseries(self):
        """
        Return a list of timeseries associated with this monitored property.
        """
        return self._timeseries

    def add_timeseries(self, tseries):
        """
        Add a new timeseries to this monitored property.
        """
        self._timeseries.append(tseries)

    # ---- Utilities
    def get_merged_timeseries(self):
        """
        Return a pandas dataframe containing the data from all the timeseries
        that were added to this group.
        """
        if len(self.timeseries) >= 1:
            merged_tseries = self.timeseries[0]._data.to_frame()
            merged_tseries.columns = [self.data_type]
            # Add series ID to the dataframe.
            merged_tseries['obs_id'] = self.timeseries[0].id
            # Add sonde ID to the dataframe.
            merged_tseries['sonde_id'] = self.timeseries[0].sonde_id
            # Add datetime to the dataframe.
            merged_tseries['datetime'] = merged_tseries.index
            # Reset index, but preserve the datetime data.
            merged_tseries.reset_index(drop=True, inplace=True)

            # Append or merge the remaining timeseries with the first one.
            for tseries in self.timeseries[1:]:
                tseries_to_append = tseries._data.to_frame()
                tseries_to_append.columns = [self.data_type]
                tseries_to_append['obs_id'] = tseries.id
                tseries_to_append['sonde_id'] = tseries.sonde_id
                tseries_to_append['datetime'] = tseries_to_append.index
                tseries_to_append.reset_index(drop=True, inplace=True)
                merged_tseries = merged_tseries.append(
                    tseries_to_append, ignore_index=True,
                    verify_integrity=True, sort=True)
        elif len(self.timeseries) == 0:
            merged_tseries = pd.DataFrame([])
        return merged_tseries

    # ---- Data selection
    def clear_selected_data(self):
        """
        Clear all selected data in the timeseries of this timeseries group.
        """
        for tseries in self._timeseries:
            tseries.clear_selected_data()

    def select_data(self, *args, **kargs):
        """
        This is a convenience method to select data in the timeseries of this
        group for a given period and range of values.
        """
        for tseries in self._timeseries:
            tseries.select_data(*args, **kargs)


class TimeSeries(Mapping):
    """
    Sardes time series class.

    Attributes
    ----------
    data
        A pandas Series with datetime indexes.
    tseries_id
        A unique ID used to reference this time series between Sardes GUI and
        the database by the database accessor.
    tseries_name: str
        A common human readable name used to reference this time series in the
        GUI and the graphs.
    tseries_units: str
        The units of the data this timeseries is referencing to.
    sonde_id
        An ID used to reference the sonde with which the data of this time
        series were acquired.
    """

    def __init__(self, data, tseries_id, tseries_name=None,
                 tseries_units=None, tseries_color=None,
                 sonde_id=None):
        super().__init__()
        self._data = data
        self.name = tseries_name
        self.id = tseries_id
        self.units = tseries_units
        self.color = tseries_color
        self.sonde_id = sonde_id

        self._undo_stack = []
        self._selected_data_indexes = pd.DatetimeIndex([])

    def __len__(self, key):
        return len(self._data)

    def __setitem__(self, key, value):
        return NotImplementedError

    def __getitem__(self, key):
        return NotImplementedError

    def __iter__(self):
        return NotImplementedError

    def __str__(self):
        return self._data.__str__()

    # ---- Attributes
    @property
    def data(self):
        return self._data

    @property
    def dates(self):
        return self._data.index.values

    @property
    def strftime(self):
        return self._data.index.strftime("%Y-%m-%dT%H:%M:%S").values.tolist()

    # ---- Data Selection
    def select_data(self, xrange=None, yrange=None):
        """
        Select data for a given period and range of values.

        Return a pandas DatetimeIndex containing the datetime indexes
        of the timeseries corresponding to the data in the specified
        period and range of values.

        The resulting datetime indexes are also added to a list of
        already selected indexes, whose corresponding data can be obtained
        with the get_selected_data method.

        Parameters
        ----------
        xrange: tuple of datetime
            A tuple of 2-datetime objects specifying the start and end of
            a period.
        yrange: tuple of float
            A tuple of 2-floats specifying a range of values.

        Returns
        -------
        pandas.DatetimeIndex
            A pandas datetime index corresponding to the data in the
            specified period and range of values.
        """
        if xrange is not None and self._data.index.tzinfo is None:
            # Make sure the datetime objects or the specified period
            # use the same timezone info as that of the timeseries.
            xrange = (xrange[0].replace(tzinfo=self._data.index.tzinfo),
                      xrange[1].replace(tzinfo=self._data.index.tzinfo))

        if xrange and yrange:
            indexes = (
                self._data[(self._data.index >= xrange[0]) &
                           (self._data.index <= xrange[1]) &
                           (self._data >= yrange[0]) &
                           (self._data <= yrange[1])
                           ]).index
        elif xrange:
            indexes = (
                self._data[(self._data.index >= xrange[0]) &
                           (self._data.index <= xrange[1])
                           ]).index
        elif yrange:
            indexes = (
                self._data[(self._data >= yrange[0]) &
                           (self._data <= yrange[1])
                           ]).index
        else:
            indexes = pd.DatetimeIndex([])

        self._selected_data_indexes = (
            self._selected_data_indexes.append(indexes))

        return indexes

    def get_selected_data(self):
        """
        Get the previously selected data of this timeseries.

        Return a pandas Series containing the data of this timeseries that
        were previously selected by the user.
        """
        return self._data.loc[self._selected_data_indexes]

    def clear_selected_data(self):
        """
        Clear the previously selected data of this timeseries.

        Clear the data of this timeseries that were previously selected
        by the user.
        """
        self._selected_data_indexes = pd.DatetimeIndex([])

    # ---- Versionning
    @property
    def has_uncommited_changes(self):
        """"
        Return whether there is uncommited changes to the water level data.
        """
        return bool(len(self._undo_stack))

    def commit(self):
        """Commit the changes made to the water level data to the project."""
        raise NotImplementedError

    def undo(self):
        """Undo the last changes made to the water level data."""
        if self.has_uncommited_changes:
            changes = self._undo_stack.pop(-1)
            self._data[changes.index] = changes

    def clear_all_changes(self):
        """
        Clear all changes that were made to the water level data since the
        last commit.
        """
        while self.has_uncommited_changes:
            self.undo()

    def delete_waterlevels_at(self, indexes):
        """Delete the water level data at the specified indexes."""
        if len(indexes):
            self._add_to_undo_stack(indexes)
            self._data.iloc[indexes] = np.nan

    def _add_to_undo_stack(self, indexes):
        """
        Store the old water level values at the specified indexes in a stack
        before changing or deleting them. This allow to undo or cancel any
        changes made to the water level data before commiting them.
        """
        if len(indexes):
            self._undo_stack.append(self._data.iloc[indexes, 0].copy())


# ---- Plotting devices
class BaseAxes(MplAxes):
    MINDATE = date2num(datetime.datetime(1000, 1, 1))
    MAXDATE = date2num(datetime.datetime(3000, 1, 1))

    def set_xlim(self, left=None, right=None, emit=True, auto=False,
                 *, xmin=None, xmax=None):
        """
        Override _AxesBase method to limit the xaxis to a valid matplotlib
        date range.
        """
        if right is None and np.iterable(left):
            left, right = left
        left = xmin if xmin is not None else left
        right = xmax if xmax is not None else right

        if left is not None:
            if left <= self.MINDATE or left >= self.MAXDATE:
                return super().set_xlim(None, None, emit, auto)
        if right is not None:
            if right <= self.MINDATE or right >= self.MAXDATE:
                return super().set_xlim(None, None, emit, auto)
        return super().set_xlim(left, right, emit, auto)


class TimeSeriesAxes(BaseAxes):
    """
    A matplotlib Axes object where one or more timeseries of the same
    quantity can be plotted at the same time.

    Note that this axe is created so that its xaxis is shared with
    the base axe of the figure.
    """
    # https://matplotlib.org/3.1.1/api/axes_api.html

    def __init__(self, tseries_figure, tseries_group, where=None,
                 linewidth=0.75, markersize=0):
        super().__init__(tseries_figure,
                         tseries_figure.base_axes.get_position(),
                         facecolor=None,
                         frameon=True,
                         sharex=tseries_figure.base_axes)
        for spine in self.spines.values():
            spine.set_visible(False)

        self.figure.add_tseries_axes(self)

        # Plot format options.
        self._linewidth = linewidth
        self._markersize = markersize

        # Init class attributes.
        self._rect_selector = None
        self._hspan_selector = None
        self._vspan_selector = None
        self._mpl_artist_handles = {
            'data': {},
            'selected_data': {},
            'manual_measurements': None}

        # Set and plot the timeseries for this axe.
        self.set_timeseries_group(tseries_group)

        # Make sure the xticks and xticks labels are not shown for this
        # axe, because this is provided by the base axe.
        self.xaxis.set_visible(False)
        self.patch.set_visible(False)
        self.tick_params(labelsize=self.figure.canvas.font().pointSize())

        # Setup the new axe yaxis position and parameters.
        if where is None:
            where = ('left' if len(self.figure.tseries_axes_list) == 1
                     else 'right')
        if where == 'right':
            self.yaxis.tick_right()
            self.yaxis.set_label_position('right')
        else:
            self.yaxis.tick_left()
            self.yaxis.set_label_position('left')
        self.tick_params(labelsize=self.figure.canvas.font().pointSize())

        self.figure.tight_layout(force=True)

    def set_current(self):
        """Set this axe as current."""
        self.figure.set_current_tseries_axes(self)

    # ---- Selectors
    @property
    def rect_selector(self):
        """
        Return a rectangular data selector for this axe.
        """
        if self._rect_selector is None:
            self._rect_selector = RectangleSelector(
                self,
                self._handle_drag_select_data,
                drawtype='box',
                useblit=True,
                button=[1],
                interactive=False,
                rectprops=dict(facecolor='red', edgecolor='black',
                               alpha=0.2, fill=True, linestyle=':')
                )
        return self._rect_selector

    @property
    def hspan_selector(self):
        """
        Return a horizontal span data selector for this axe.
        """
        if self._hspan_selector is None:
            self._hspan_selector = SpanSelector(
                self,
                self._handle_hspan_select_data,
                'horizontal',
                useblit=True,
                rectprops=dict(facecolor='red', edgecolor='black',
                               alpha=0.2, linestyle=':')
                )
        return self._hspan_selector

    @property
    def vspan_selector(self):
        """
        Return a vertical span data selector for this axe.
        """
        if self._vspan_selector is None:
            # Setup a new data vertical span selector for this timeseries.
            self._vspan_selector = SpanSelector(
                self,
                self._handle_vspan_select_data,
                'vertical',
                useblit=True,
                rectprops=dict(facecolor='red', edgecolor='black',
                               alpha=0.2, linestyle=':')
                )
        return self._vspan_selector

    # ---- Manual Measurements
    def set_manual_measurements(self, measurements):
        """
        Set and plot the manual measurements for this axe.
        """
        if self._mpl_artist_handles['manual_measurements'] is None:
            self._mpl_artist_handles['manual_measurements'], = (
                self.plot([], 'o', color='magenta', clip_on=True, ms=5,
                          mfc='none', mec='magenta', mew=1.5))
        self._mpl_artist_handles['manual_measurements'].set_data(
            measurements['datetime'].values, measurements['value'].values)
        self.figure.setup_legend()
        self.figure.canvas.draw()

    # ---- Timeseries
    @property
    def data_type(self):
        """
        Return the DataType of the data that are plotted on this axes.
        """
        return self.tseries_group.data_type

    def set_timeseries_group(self, tseries_group):
        """
        Set the namespace of the timeseries group for this axe, setup the
        label of the yaxis and plot the data.
        """
        self.tseries_group = tseries_group
        data_type = tseries_group.data_type

        # Setup the ylabel of the axe.
        self.set_ylabel(
            '{} ({})'.format(data_type.title, data_type.units),
            labelpad=YAXIS_LABEL_PAD, fontsize=AXIS_LABEL_FS)

        # Add each timeseries of the monitored property object to this axe.
        for tseries in self.tseries_group:
            self._add_timeseries(tseries)

        # Invert yaxis if required by the group.
        if tseries_group.yaxis_inverted:
            self.invert_yaxis()

        self.figure.setup_legend()
        self.figure.canvas.draw()

    def _add_timeseries(self, tseries):
        """
        Plot the data of the timeseries and init selected data artist.
        """
        self._mpl_artist_handles['data'][tseries.id], = (
            self.plot(tseries.data, '.-', color=tseries.color, clip_on=True,
                      ms=self._markersize, lw=self._linewidth))
        self._mpl_artist_handles['selected_data'][tseries.id], = (
            self.plot(tseries.get_selected_data(), '.', color='orange',
                      clip_on=True))

    def clear_selected_data(self):
        """
        Clear all selected data in the timeseries associated with this axe.
        """
        self.tseries_group.clear_selected_data()
        self._draw_selected_data()

    # ---- Drawing methods
    def set_linewidth(self, linewidth):
        """Set the line width for the plots of this axe."""
        self._linewidth = linewidth
        for tseries in self.tseries_group:
            (self._mpl_artist_handles['data'][tseries.id]
             .set_linewidth(linewidth))
        self.figure.setup_legend()
        self.figure.canvas.draw()

    def set_markersize(self, markersize):
        """Set the marker size for the plots of this axe."""
        self._markersize = markersize
        for tseries in self.tseries_group:
            (self._mpl_artist_handles['data'][tseries.id]
             .set_markersize(markersize))
        self.figure.setup_legend()
        self.figure.canvas.draw()

    def _draw_selected_data(self, draw=True):
        """
        If this axe is current, draw the selected data of the timeseries
        associated with this axe.
        """
        for tseries in self.tseries_group:
            handle = self._mpl_artist_handles['selected_data'][tseries.id]
            handle.set_visible(self.figure.gca() == self)
            if self.figure.gca() == self:
                # Update the selected data plot for the current axe.
                selected_data = tseries.get_selected_data()
                handle.set_data(selected_data.index.values,
                                selected_data.values)
        if draw:
            self.figure.canvas.draw()

    # ----Data selection handlers
    def _handle_drag_select_data(self, eclick, erelease):
        """
        Handle when a rectangular area to select data has been selected.
        """
        xmin, xmax, ymin, ymax = self._rect_selector.extents
        self.tseries_group.select_data(xrange=(num2date(xmin), num2date(xmax)),
                                       yrange=(ymin, ymax))
        self._draw_selected_data()

    def _handle_hspan_select_data(self, xmin, xmax):
        """
        Handle when an horizontal span has been selected by the user to
        select data.
        """
        self.tseries_group.select_data(xrange=(num2date(xmin), num2date(xmax)))
        self._draw_selected_data()

    def _handle_vspan_select_data(self, ymin, ymax):
        """
        Handle when a vertical span has been selected by the user to
        select data.
        """
        self.tseries_group.select_data(yrange=(ymin, ymax))
        self._draw_selected_data()

    # ---- Axes public API
    def set_visible(self, *arg, **kargs):
        super().set_visible(*arg, **kargs)
        self.figure.setup_legend()


class TimeSeriesFigure(MplFigure):
    """
    A matplotlib Figure object that hold a base axe and one or more axes to
    plot timeseries data.
    """
    # https://matplotlib.org/3.1.1/api/_as_gen/matplotlib.figure.Figure.html

    CURRENT_AXE_ZORDER = 200
    SEC_AXE_ZORDER = 100

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.set_tight_layout(True)
        self._legend_visible = True

        self.base_axes = None
        self.tseries_axes_list = []

    def setup_base_axes(self):
        """
        Setup a base axes with which all other axes will share their xaxis.
        """
        self.base_axes = BaseAxes(self, [0, 0, 1, 1])
        self.base_axes.set_zorder(0)
        self.base_axes.set_yticks([])
        self.base_axes.tick_params(
            labelsize=self.canvas.font().pointSize(),
            left=False, right=False, labelleft=False, labelright=False)
        self.base_axes.set_visible(False)
        self.add_axes(self.base_axes)
        self.setup_legend()
        self.canvas.draw()

    def add_tseries_axes(self, tseries_axes):
        """
        Add the new axes used to plot timeseries data to this figure.
        """
        self.base_axes.set_visible(True)
        self.tseries_axes_list.append(tseries_axes)
        self.add_axes(tseries_axes)

    def set_current_tseries_axes(self, current_tseries_axes):
        """
        Set the current axe of this figure to that specified in the arguments.
        """
        self.sca(current_tseries_axes)
        for tseries_axes in self.tseries_axes_list:
            tseries_axes.set_zorder(
                self.CURRENT_AXE_ZORDER if
                tseries_axes == current_tseries_axes else
                self.SEC_AXE_ZORDER)
            tseries_axes.set_navigate(tseries_axes == current_tseries_axes)
            tseries_axes._draw_selected_data()

    def set_size_inches(self, *args, **kargs):
        """
        Override matplotlib method to force a call to tight_layout when
        set_size_inches is called. This allow to keep the size of the margins
        fixed when the canvas of this figure is resized.
        """
        super().set_size_inches(*args, **kargs)
        self.tight_layout()

    def clear_selected_data(self):
        "Clear the selected data for the currently selected axe."
        current_axe = self.gca()
        try:
            current_axe.clear_selected_data()
        except AttributeError:
            pass

    def setup_legend(self):
        """Setup the legend of the graph."""
        lg_handles = []
        lg_labels = []
        if self._legend_visible is True:
            for ax in self.tseries_axes_list:
                if not ax.get_visible():
                    continue
                # Add an handle for the timeseries data.
                for handle in ax._mpl_artist_handles['data'].values():
                    lg_handles.append(handle)
                    lg_labels.append(ax.data_type.title)
                    break
                # Add an handle for the manual measurements.
                handle = ax._mpl_artist_handles['manual_measurements']
                if handle is not None:
                    lg_handles.append(handle)
                    lg_labels.append('{} ({})'.format(
                        ax.data_type.title, _('manual')))

        legend = self.base_axes.legend(
            lg_handles, lg_labels, bbox_to_anchor=[0.5, 1],
            loc='lower center', ncol=4, handletextpad=0.5,
            numpoints=1, fontsize=9, frameon=False)
        legend.set_visible(len(legend.legendHandles) > 0)

    def tight_layout(self, *args, **kargs):
        """
        Override matplotlib method to setup the margins of the axes.
        """
        if self.base_axes is None:
            return
        try:
            # This is required when saving the figure in some format like
            # pdf and svg.
            # See cgq-qgc/sardes#313.
            renderer = self.canvas.get_renderer()
        except AttributeError:
            # With more recent version of matplotlib we need to use 'draw_idle'
            # instead of 'draw'.
            # see cgq-qgc/sardes#553.
            self.canvas.draw_idle()
            return

        fheight = self.get_figheight()
        fwidth = self.get_figwidth()
        bottom_margin = 0.5 / fheight

        # We calculate the size of the top margin.
        top_margin = FIG_PAD / 72 / fheight
        legend = self.base_axes.get_legend()
        if legend.get_visible():
            legend_height = legend.get_window_extent(renderer).transformed(
                self.dpi_scale_trans.inverted()).height * 72
            top_margin = np.ceil(
                (legend_height + FIG_PAD) * 10) / 10 / 72 / fheight

        # We calculate the size of the left margin.
        left_margin = FIG_PAD / 72 / fwidth
        if len(self.tseries_axes_list):
            ax = self.tseries_axes_list[0]
            if ax.get_visible():
                ticklabel_width = ax.yaxis.get_ticklabel_extents(
                    renderer)[0].transformed(
                        self.dpi_scale_trans.inverted()).width * 72
                left_margin = np.ceil((
                    FIG_PAD + AXIS_LABEL_FS + YAXIS_LABEL_PAD +
                    ticklabel_width + YTICKS_PAD + YTICKS_LENGTH
                    ) * 10) / 10 / 72 / fwidth

        # We set the position of the other axes and calculate the
        # size of the right margin.
        other_axes = [
            ax for ax in self.tseries_axes_list[1:] if ax.get_visible()]
        right_margin = 0
        for ax in other_axes:
            ax.spines['right'].set_visible(right_margin > 0)
            ax.spines['right'].set_position(('outward', right_margin))
            ticklabel_width = ax.yaxis.get_ticklabel_extents(
                renderer)[1].transformed(
                    self.dpi_scale_trans.inverted()).width * 72
            right_margin += np.ceil((
                YTICKS_LENGTH + YTICKS_PAD + ticklabel_width +
                YAXIS_LABEL_PAD + AXIS_LABEL_FS +
                (FIG_PAD if ax == other_axes[-1] else 20)
                ) * 10) / 10
        right_margin = max(FIG_PAD, right_margin) / 72 / fwidth

        # From the size of the margins, we set the new position of the axes.
        cur_position = self.base_axes.get_position()
        new_position = Bbox.from_bounds(
            left_margin, bottom_margin,
            1 - (left_margin + right_margin), 1 - (bottom_margin + top_margin))
        if np.any(cur_position.get_points() != new_position.get_points()):
            for axe in self.axes:
                axe.set_position(new_position)


class TimeSeriesCanvas(FigureCanvasQTAgg):
    """
    A matplotlib canvas where the figure is drawn.
    """
    sig_show_overlay_message = Signal()
    BASE_ZOOM_SCALE = 1.25

    def __init__(self, figure):
        super().__init__(figure)
        # A pandas series containing the information related to the well
        # in which the data plotted in this canvas were acquired.
        self._obs_well_data = None

        figure.setup_base_axes()

        # Setup a matplotlib navigation toolbar, but hide it.
        toolbar = NavigationToolbar2QT(self, self)
        toolbar.hide()

        self.mpl_connect('scroll_event', self._on_mouse_scroll)

    def create_axe(self, tseries_group, where):
        """
        Create a new axe to plot the timeseries data of a given monitored
        property and add it to this canvas' figure.
        """
        axe = TimeSeriesAxes(self.figure, tseries_group, where)
        return axe

    def copy_to_clipboard(self):
        """Put a copy of the figure on the clipboard."""
        buf = io.BytesIO()
        self.figure.savefig(buf)
        QApplication.clipboard().setImage(QImage.fromData(buf.getvalue()))
        buf.close()

    # ---- Navigation and Selection tools
    def _on_mouse_scroll(self, event):
        """
        Scroll the graph in or out when Ctrl is pressed and the wheel of
        the mouse is scrolled up or down.

        Adapted from https://stackoverflow.com/a/11562898/4481445
        """
        modifiers = QGuiApplication.keyboardModifiers()
        if not bool(modifiers & Qt.ControlModifier):
            self.sig_show_overlay_message.emit()
            return

        if event.button == 'up':
            self.zoom_current_axes(event.xdata, event.ydata, -1)
        elif event.button == 'down':
            self.zoom_current_axes(event.xdata, event.ydata, 1)

    def zoom_in(self):
        """
        Zoom current axes in.
        """
        ax = self.figure.gca()
        self.zoom_current_axes(
            np.mean(ax.get_xlim()), np.mean(ax.get_ylim()), -1)

    def zoom_out(self):
        """
        Zoom current axes out.
        """
        ax = self.figure.gca()
        self.zoom_current_axes(
            np.mean(ax.get_xlim()), np.mean(ax.get_ylim()), 1)

    def zoom_current_axes(self, xdata, ydata, scale_factor):
        """
        Zoome the current axes by the given scale factor around the given
        set of x and y coordinates.
        """
        # push the current view to define home if stack is empty
        if self.toolbar._nav_stack() is None:
            self.toolbar.push_current()

        scale_factor = self.BASE_ZOOM_SCALE**scale_factor

        ax = self.figure.gca()
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()

        left_xrange = xdata - cur_xlim[0]
        right_xrange = cur_xlim[1] - xdata
        top_yrange = cur_ylim[1] - ydata
        bottom_yrange = ydata - cur_ylim[0]

        ax.set_xlim([xdata - left_xrange * scale_factor,
                     xdata + right_xrange * scale_factor])
        ax.set_ylim([ydata - bottom_yrange * scale_factor,
                     ydata + top_yrange * scale_factor])
        self.draw()

    def home(self):
        """Reset the orgininal view of this canvas' figure."""
        self.toolbar.home()
        self.figure.tight_layout(force=True)

    def zoom_to_rect(self, toggle):
        """Toggle zooming in the canvas."""
        if toggle is True:
            if self.toolbar.mode.name != 'ZOOM':
                self.toolbar.zoom()
        else:
            if self.toolbar.mode.name == 'ZOOM':
                self.toolbar.zoom()

    def pan_axes(self, toggle):
        """Toggle axe panning in the canvas."""
        if toggle is True:
            if self.toolbar.mode.name != 'PAN':
                self.toolbar.pan()
        else:
            if self.toolbar.mode.name == 'PAN':
                self.toolbar.pan()

    def drag_select_data(self, toggle):
        """Toggle data mouse drag selection over a rectangle region."""
        for axe in self.figure.tseries_axes_list:
            axe.rect_selector.set_active(toggle)

    def hspan_select_data(self, toggle):
        """Toggle data mouse drag selection over an horizontal span."""
        for axe in self.figure.tseries_axes_list:
            axe.hspan_selector.set_active(toggle)

    def vspan_select_data(self, toggle):
        """Toggle data mouse drag selection over a vertical span."""
        for axe in self.figure.tseries_axes_list:
            axe.vspan_selector.set_active(toggle)

    # ---- FigureCanvasQTAgg API
    def get_default_filename(self):
        """
        Return a string, which includes extension, suitable for use as
        a default filename.
        """
        if self._obs_well_data is None:
            return super().get_default_filename()
        else:
            figname = self._obs_well_data['obs_well_id']
            if self._obs_well_data['common_name']:
                figname += ' - {}'.format(self._obs_well_data['common_name'])
            figname += '.{}'.format(self.get_default_filetype())
            return figname


class TimeSeriesPlotViewer(QMainWindow):
    """
    A widget to plot, explore and manipulate interactively timeseries data.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window)
        self.setMinimumSize(750, 450)

        self.figure = TimeSeriesFigure(facecolor='white')
        self.canvas = TimeSeriesCanvas(self.figure)
        self.canvas.sig_show_overlay_message.connect(
            self._show_canvas_overlay_message)

        self.overlay_msg_widget = self._setup_overlay_msg_widget()

        self.central_widget = QWidget()
        central_widget_layout = QGridLayout(self.central_widget)
        central_widget_layout.setContentsMargins(0, 0, 0, 0)
        central_widget_layout.addWidget(self.canvas, 0, 0)
        central_widget_layout.addWidget(self.overlay_msg_widget, 0, 0)
        self.setCentralWidget(self.central_widget)

        self.toolbars = []
        self._setup_toolbar()
        self._setup_axes_toolbar()

        self.canvas.mpl_connect('motion_notify_event', self._on_mouse_move)
        self.canvas.mpl_connect('axes_leave_event', self._on_axe_leave)
        self.canvas.mpl_connect('figure_leave_event', self._on_axe_leave)

    def _setup_overlay_msg_widget(self):
        """
        Setup a widget that can show a message that is overlying the plot
        area.
        """
        # We cannot only the Ctrl modifier becasue this results in an
        # empty string.
        ctrl_text = QKeySequence('Ctrl+1').toString(
            QKeySequence.NativeText)[:-2]
        overlay_msg = _(
            "Use {} + scroll to zoom the graph").format(ctrl_text)

        msg_background = QWidget()
        msg_background.setObjectName('plot_viewer_msg_background')
        msg_background.setStyleSheet(
            "QWidget#plot_viewer_msg_background {background-color: black;}")
        msg_background.setAutoFillBackground(True)

        self.msq_label = QLabel(overlay_msg)
        self.msq_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.msq_label.setWordWrap(True)
        self.msq_label.setStyleSheet("color:white;")
        font = self.msq_label.font()
        font.setPointSize(16)
        self.msq_label.setFont(font)

        overlay_msg_widget = QWidget()
        msg_layout = QGridLayout(overlay_msg_widget)
        msg_layout.setContentsMargins(0, 0, 0, 0)
        msg_layout.addWidget(msg_background, 0, 0)
        msg_layout.addWidget(self.msq_label, 0, 0)
        overlay_msg_widget.hide()

        opacity_effect = QGraphicsOpacityEffect(msg_background)
        msg_background.setGraphicsEffect(opacity_effect)

        # Setup a gradual opacity effect on the overlay message widget when
        # showing it.
        # Adapted from https://stackoverflow.com/a/14444331/4481445
        self._overlay_msg_widget_show_animation = QPropertyAnimation(
            opacity_effect, b"opacity")
        self._overlay_msg_widget_show_animation.setDuration(100)
        self._overlay_msg_widget_show_animation.setStartValue(0)
        self._overlay_msg_widget_show_animation.setEndValue(0.65)

        self._hide_overlay_msg_timer = QTimer(self)
        self._hide_overlay_msg_timer.setSingleShot(True)
        self._hide_overlay_msg_timer.timeout.connect(overlay_msg_widget.hide)

        return overlay_msg_widget

    def _setup_toolbar(self):
        """Setup the main toolbar of this time series viewer."""
        toolbar = create_mainwindow_toolbar("TimeSeries toolbar")
        self.addToolBar(toolbar)
        self.toolbars.append(toolbar)

        self._navig_and_select_buttongroup = SemiExclusiveButtonGroup()

        # ---- Save figure and data.
        self.save_figure_button = create_toolbutton(
            self, icon='save',
            text=_("Save"),
            tip=_('Save the figure to a file'),
            shortcut='Ctrl+S',
            triggered=self.canvas.toolbar.save_figure,
            iconsize=get_iconsize())
        toolbar.addWidget(self.save_figure_button)

        self.copy_to_clipboard_btn = create_toolbutton(
            self, icon='copy_clipboard',
            text=_("Copy"),
            tip=_("Put a copy of the figure on the Clipboard."),
            triggered=self.canvas.copy_to_clipboard,
            shortcut='Ctrl+C',
            iconsize=get_iconsize())
        toolbar.addWidget(self.copy_to_clipboard_btn)

        toolbar.addSeparator()

        # ---- Navigate data.
        self.home_button = create_toolbutton(
            self, icon='home',
            text=_("Home"),
            tip=_('Reset original view'),
            shortcut='Ctrl+0',
            triggered=self.canvas.home,
            iconsize=get_iconsize())
        toolbar.addWidget(self.home_button)

        self.pane_button = create_toolbutton(
            self, icon='pan',
            text=_("Pan"),
            tip=_('Pan axes with left mouse, zoom with right'),
            shortcut='Ctrl+P',
            toggled=self.canvas.pan_axes,
            iconsize=get_iconsize())
        toolbar.addWidget(self.pane_button)
        self._navig_and_select_buttongroup.add_button(self.pane_button)

        self.zoom_to_rect_button = create_toolbutton(
            self, icon='zoom_to_rect',
            text=_("Zoom"),
            tip=_('Zoom in to rectangle with left mouse, '
                  'zoom out with right.'),
            shortcut='Ctrl+Z',
            toggled=self.canvas.zoom_to_rect,
            iconsize=get_iconsize())
        toolbar.addWidget(self.zoom_to_rect_button)
        self._navig_and_select_buttongroup.add_button(self.zoom_to_rect_button)

        # We cannot only the Ctrl modifier becasue this results in an
        # empty string.
        ctrl_text = QKeySequence('Ctrl+1').toString(
            QKeySequence.NativeText)[:-2]
        self.zoom_out_btn = create_toolbutton(
            self, icon='zoom_out',
            text=_("Zoom out"),
            tip=_('Zoom the graph out. You can also use {}+scroll down to '
                  'zoom the graph out.').format(ctrl_text),
            shortcut=['Ctrl+-'],
            triggered=self.canvas.zoom_out,
            iconsize=get_iconsize())
        toolbar.addWidget(self.zoom_out_btn)

        self.zoom_in_btn = create_toolbutton(
            self, icon='zoom_in',
            text=_("Zoom in"),
            tip=_('Zoom the graph in. You can also use {}+scroll up to '
                  'zoom the graph in.').format(ctrl_text),
            shortcut=['Ctrl++', 'Ctrl+='],
            triggered=self.canvas.zoom_in,
            iconsize=get_iconsize())
        toolbar.addWidget(self.zoom_in_btn)

        # ---- Select and transform data.

        # We are currently hiding these buttons since selecting data doesn't
        # allow users to do anything usefull yet in the timeseries plot viewer,
        # so these buttons are just a source of confusion for the moment. We
        # will add them back later.

        toolbar.addSeparator()

        self.drag_select_data_button = create_toolbutton(
            self, icon='drag_select',
            text=_("Select Data"),
            tip=_('Select data by clicking with the mouse and dragging'
                  ' the cursor over a rectangular region on the graph.'),
            toggled=self.canvas.drag_select_data,
            iconsize=get_iconsize())
        toolbar.addWidget(self.drag_select_data_button)
        self._navig_and_select_buttongroup.add_button(
            self.drag_select_data_button)

        self.hspan_select_data_button = create_toolbutton(
            self, icon='hspan_select',
            text=_("Select Data"),
            tip=_('Select data by clicking with the mouse and dragging'
                  ' the cursor horizontally over a given period on'
                  ' the graph.'),
            toggled=self.canvas.hspan_select_data,
            iconsize=get_iconsize())
        toolbar.addWidget(self.hspan_select_data_button)
        self._navig_and_select_buttongroup.add_button(
            self.hspan_select_data_button)

        self.vspan_select_data_button = create_toolbutton(
            self, icon='vspan_select',
            text=_("Select Data"),
            tip=_('Select data by clicking with the mouse and dragging'
                  ' the cursor vertically over a given span of the data on'
                  ' the graph.'),
            toggled=self.canvas.vspan_select_data,
            iconsize=get_iconsize())
        toolbar.addWidget(self.vspan_select_data_button)
        self._navig_and_select_buttongroup.add_button(
            self.vspan_select_data_button)

        self.clear_selected_data_button = create_toolbutton(
            self, icon='clear_selected_data',
            text=_("Clear Data Selection"),
            tip=_('Clear data selection for the currently selected '
                  'time series.'),
            triggered=self.canvas.figure.clear_selected_data,
            iconsize=get_iconsize())
        toolbar.addWidget(self.clear_selected_data_button)

    def _setup_axes_toolbar(self):
        """
        Setup the toolbar for axes.
        """
        # ---- Timeseries selection.
        self.axes_toolbar = create_mainwindow_toolbar("Axis toolbar")
        self.addToolBar(Qt.BottomToolBarArea, self.axes_toolbar)
        self.toolbars.append(self.axes_toolbar)

        # Axes visibility.
        self.visible_axes_btn = ToggleVisibilityToolButton(get_iconsize())
        self.visible_axes_btn.setToolTip(
            _("Toggle graph element visibility"))
        self.visible_axes_btn.sig_item_clicked.connect(
            self._handle_axe_visibility_changed)
        self.axes_toolbar.addWidget(self.visible_axes_btn)

        # Current axe selection.
        self.current_axe_button = DropdownToolButton(
            None, get_iconsize(),
            parent=self,
            placeholder_text='<{}>'.format(_('Graph is empty')))
        self.current_axe_button.sig_checked_action_changed.connect(
            self._handle_selected_axe_changed)
        self.current_axe_button.setToolTip(format_tooltip(
            _('Graph Element'),
            _('Select a graph element so that you can format it and'
              ' zoom and pan the data.'),
            None))
        self.axes_toolbar.addWidget(self.current_axe_button)

        # ---- Format
        self.axes_toolbar.addSeparator()

        # Line weight format.
        self.fmt_line_weight = IconSpinBox(
            'fmt_line_weight', 0.75, value_range=(0, 99), decimals=2,
            single_step=0.25, suffix=' {}'.format(_('pt')),
            text=_('Line Width'),
            tip=_('Enter a value from 0 pt to 99 pt to change the line width '
                  'of the plot of the currently selected time series.')
            )
        self.fmt_line_weight.sig_value_changed.connect(
            self._handle_linewidth_changed)
        self.axes_toolbar.addWidget(self.fmt_line_weight)

        # Marker size format.
        self.fmt_marker_size = IconSpinBox(
            'fmt_marker_size', 0, value_range=(0, 99), decimals=0,
            single_step=1, suffix=' {}'.format(_('pt')),
            text=_('Marker Size'),
            tip=_('Enter a value from 0 pt to 99 pt to change the marker size '
                  'of the plot of the currently selected time series.')
            )
        self.fmt_marker_size.sig_value_changed.connect(
            self._handle_markersize_changed)
        self.axes_toolbar.addWidget(self.fmt_marker_size)

        # Axe coordinates.
        self.axes_toolbar.addWidget(create_toolbar_stretcher())
        self._axes_coord_sep = self.axes_toolbar.addSeparator()
        self._axes_coord_action = self.axes_toolbar.addWidget(QLabel())

    # ---- Public API
    def set_data(self, dataf, obs_well_data=None):
        """Set the data that need to be displayed in this plot viewer."""
        self.canvas._obs_well_data = obs_well_data
        for data_type in DataType:
            if data_type in dataf.columns:
                tseries_group = TimeSeriesGroup(
                    data_type,
                    yaxis_inverted=(data_type == DataType.WaterLevel)
                    )

                # Split the data in channels.
                for obs_id in dataf['obs_id'].unique():
                    channel_data = dataf[dataf['obs_id'] == obs_id]
                    sonde_id = channel_data['sonde_id'].unique()[0]
                    tseries_group.add_timeseries(TimeSeries(
                        pd.Series(channel_data[data_type].values,
                                  index=channel_data['datetime'].values),
                        tseries_id=obs_id,
                        tseries_name=data_type.title,
                        tseries_units='',
                        tseries_color=data_type.color,
                        sonde_id=sonde_id
                        ))
                self.create_axe(tseries_group)
        self.axes_toolbar.setEnabled(self.current_axe_button.count())

        # We want the water level axe to be the active one by default.
        if self.current_axe_button.count():
            self.set_current_axe(0)

    def update_data(self, dataf, obs_well_data=None):
        """Set the data that need to be displayed in this plot viewer."""
        for axe in reversed(self.figure.tseries_axes_list):
            self.remove_axe(axe)
        self.set_data(dataf, obs_well_data)

    def set_manual_measurements(self, data_type, measurements):
        """
        Set the manual measurements for the axe corresponding to the given
        data type.
        """
        for axe in self.figure.tseries_axes_list:
            if axe.tseries_group.data_type == data_type:
                axe.set_manual_measurements(measurements)

    def create_axe(self, tseries_group, where=None):
        """
        Create and add a new axe to the figure where to plot the data
        contained in the timeseries group.
        """
        axe = self.canvas.create_axe(tseries_group, where)

        # Add axe to selection menu.
        # Note that this will make the corresponding axe to become current.
        self.current_axe_button.create_action(
            tseries_group.data_type.title, data=axe)
        self.axes_toolbar.setEnabled(self.current_axe_button.count())
        self.visible_axes_btn.create_action(tseries_group.data_type.title, axe)

        return axe

    def remove_axe(self, axe):
        """
        Remove the given axe from this timeseries viewer.
        """
        self.figure.tseries_axes_list.remove(axe)
        self.current_axe_button.remove_action(axe)
        self.visible_axes_btn.remove_action(axe)
        axe.remove()
        self.canvas.draw()
        self.axes_toolbar.setEnabled(self.current_axe_button.count())

    def current_axe(self):
        """Return the currently active axe."""
        checked_action = self.current_axe_button.checked_action()
        if checked_action is not None:
            return checked_action.data()
        else:
            return None

    def set_current_axe(self, index):
        """Set the currently active axe."""
        self.current_axe_button.setCheckedAction(index)

    # ---- Private API
    def _on_mouse_move(self, event):
        """
        Handle when the mouse cursor is moved over this viewer's figure.
        """
        xdata, ydata = event.xdata, event.ydata
        if all((xdata, ydata)) and self.current_axe() is not None:
            self._axes_coord_action.defaultWidget().setText(
                '{:0.3f} {}\n{}'.format(
                    ydata,
                    self.current_axe().tseries_group.data_type.units,
                    num2date(xdata).strftime("%Y-%m-%d %H:%M")
                ))
            self._axes_coord_action.setVisible(True)
            self._axes_coord_sep.setVisible(True)
        else:
            self._on_axe_leave()

    def _on_axe_leave(self, event=None):
        """
        Handle when the mouse cursor leaves the current axe of this viewer's
        figure.
        """
        self._axes_coord_action.setVisible(False)
        self._axes_coord_sep.setVisible(False)

    @Slot()
    def _show_canvas_overlay_message(self):
        self._hide_overlay_msg_timer.stop()
        if not self.overlay_msg_widget.isVisible():
            self._overlay_msg_widget_show_animation.start()
            self.overlay_msg_widget.show()
        self._hide_overlay_msg_timer.start(MSEC_MIN_OVERLAY_MSG_DISPLAY)

    @Slot(float)
    def _handle_linewidth_changed(self, value):
        if self.current_axe() is not None:
            self.current_axe().set_linewidth(value)

    @Slot(float)
    def _handle_markersize_changed(self, value):
        if self.current_axe() is not None:
            self.current_axe().set_markersize(value)

    @Slot(QAction)
    def _handle_selected_axe_changed(self, checked_action):
        """
        Handle when the current axe is changed by the user.
        """
        selected_axe = checked_action.data()
        selected_axe.set_current()
        self.fmt_line_weight.setValue(selected_axe._linewidth)
        self.fmt_marker_size.setValue(selected_axe._markersize)

    def _handle_axe_visibility_changed(self, axe, toggle):
        """
        Toggle on or off the visibility of the current matplotlib axe and
        enable or disable items in the gui accordingly.
        """
        axe.set_visible(toggle)
        self.canvas.draw()
        self._update_selected_axe_cbox_state()

    def _update_selected_axe_cbox_state(self):
        """
        Enable or disable the actions of the current axe button's menu
        depending on the visibility of their corresponding matplotlib axe.
        """
        menu = self.current_axe_button.menu()
        for index, action in enumerate(menu.actions()):
            action.setEnabled(action.data().get_visible())

    # ---- Qt Override
    def show(self):
        """
        Extend Qt show method to center this mainwindow to its parent's
        geometry.
        """
        self.resize(1200, 600)
        if self.parent():
            self.setAttribute(Qt.WA_DontShowOnScreen, True)
            super().show()
            super().close()
            self.setAttribute(Qt.WA_DontShowOnScreen, False)
            center_widget_to_another(self, self.parent())
        super().show()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    viewer = TimeSeriesPlotViewer()
    viewer.show()

    sys.exit(app.exec_())
