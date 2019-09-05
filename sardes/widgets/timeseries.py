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

# ---- Third party imports
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
from matplotlib.figure import Figure as MplFigure
from matplotlib.axes import Axes as MplAxes
from matplotlib.widgets import RectangleSelector, SpanSelector
from matplotlib.dates import num2date
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import QAction, QApplication, QMainWindow
from pandas.plotting import register_matplotlib_converters

# ---- Local imports
from sardes.config.locale import _
from sardes.config.icons import get_icon
from sardes.config.gui import get_iconsize
from sardes.utils.qthelpers import (
    center_widget_to_another, create_mainwindow_toolbar, create_toolbutton)
from sardes.widgets.buttons import DropdownToolButton, SemiExclusiveButtonGroup


register_matplotlib_converters()


class TimeSeriesAxes(MplAxes):
    """
    A matplotlib Axes object where one or more timeseries of the same
    quantity can be plotted at the same time.
    """
    # https://matplotlib.org/3.1.1/api/axes_api.html

    def __init__(self, tseries_figure, tseries_group, where=None):
        super().__init__(tseries_figure,
                         tseries_figure.base_axes.get_position(),
                         facecolor=None,
                         frameon=False,
                         sharex=tseries_figure.base_axes)
        self.figure.add_tseries_axes(self)
        # Note that this axe is created so that its xaxis is shared with
        # the base axe of the figure.

        # Init class attributes.
        self._rect_selector = None
        self._hspan_selector = None
        self._vspan_selector = None
        self._mpl_artist_handles = {
            'data': {},
            'selected_data': {}}

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

    # ---- Timeseries
    def set_timeseries_group(self, tseries_group):
        """
        Set the namespace of the timeseries group for this axe, setup the
        label of the yaxis and plot the data.
        """
        self.tseries_group = tseries_group

        # Setup the ylabel of the axe.
        ylabel = tseries_group.prop_name
        if tseries_group.prop_units:
            ylabel += ' ({})'.format(tseries_group.prop_units)
        self.set_ylabel(ylabel, labelpad=10)

        # Add each timeseries of the monitored property object to this axe.
        for tseries in self.tseries_group:
            self._add_timeseries(tseries)

        self.figure.canvas.draw()

    def _add_timeseries(self, tseries):
        """
        Plot the data of the timeseries and init selected data artist.
        """
        self._mpl_artist_handles['data'][tseries.id], = (
            self.plot(tseries.data, color=tseries.color, clip_on=True))
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
        self.set_tight_layout(False)
        self._last_fsize = (self.bbox_inches.width, self.bbox_inches.height)

        self.base_axes = None
        self.tseries_axes_list = []

    def setup_base_axes(self):
        """
        Setup a base axes with which all other axes will share their xaxis.
        """
        self.base_axes = self.add_subplot(1, 1, 1)
        self.base_axes.set_zorder(0)
        self.base_axes.set_yticks([])
        self.base_axes.tick_params(labelsize=self.canvas.font().pointSize(),
                                   left=False, right=False,
                                   labelleft=False, labelright=False)
        self.base_axes.set_visible(False)
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

    def tight_layout(self, *args, **kargs):
        """
        Override matplotlib method to setup the margins of the axes
        to fixes dimension in inches. This allows to increase greatly the
        performance of the drawing.
        """
        current_fsize = (self.bbox_inches.width, self.bbox_inches.height)
        if (self._last_fsize != current_fsize or kargs.get('force', False)):
            self._last_fsize = current_fsize
            fheight = self.get_figheight()
            fwidth = self.get_figwidth()

            left_margin = 1 / fwidth
            right_margin = 1 / fwidth
            bottom_margin = 0.5 / fheight
            top_margin = 0.2 / fheight

            x0 = left_margin
            y0 = bottom_margin
            w = 1 - (left_margin + right_margin)
            h = 1 - (bottom_margin + top_margin)

            for axe in self.axes:
                axe.set_position([x0, y0, w, h])


class TimeSeriesCanvas(FigureCanvasQTAgg):
    """
    A matplotlib canvas where the figure is drawn.
    """

    def __init__(self, figure):
        super().__init__(figure)
        figure.setup_base_axes()

        # Setup a matplotlib navigation toolbar, but hide it.
        toolbar = NavigationToolbar2QT(self, self)
        toolbar.hide()

    def get_default_filename(self):
        """
        Return a string, which includes extension, suitable for use as
        a default filename.
        """
        default_basename = self.get_window_title() or 'image'
        default_basename = default_basename.replace(' ', '_')
        default_filetype = self.get_default_filetype()
        default_filename = default_basename + '.' + default_filetype
        return default_filename

    def create_axe(self, tseries_group, where):
        """
        Create a new axe to plot the timeseries data of a given monitored
        property and add it to this canvas' figure.
        """
        axe = TimeSeriesAxes(self.figure, tseries_group, where)
        return axe

    # ---- Navigation and Selection tools
    def home(self):
        """Reset the orgininal view of this canvas' figure."""
        self.toolbar.home()
        self.figure.tight_layout(force=True)

    def zoom_to_rect(self, toggle):
        """Toggle zooming in the canvas."""
        if toggle is True:
            if self.toolbar._active != 'ZOOM':
                self.toolbar.zoom()
        else:
            if self.toolbar._active == 'ZOOM':
                self.toolbar.zoom()

    def pan_axes(self, toggle):
        """Toggle axe panning in the canvas."""
        if toggle is True:
            if self.toolbar._active != 'PAN':
                self.toolbar.pan()
        else:
            if self.toolbar._active == 'PAN':
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


class TimeSeriesPlotViewer(QMainWindow):
    """
    A widget to plot, explore and manipulate interactively timeseries data.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window)
        self.setMinimumSize(350, 350)

        self.figure = TimeSeriesFigure(facecolor='white')
        self.canvas = TimeSeriesCanvas(self.figure)

        self.setCentralWidget(self.canvas)
        self._setup_toolbar()

    def _setup_toolbar(self):
        """Setup the main toolbar of this time series viewer."""
        # ---- Navigate data.
        toolbar = create_mainwindow_toolbar("TimeSeries toolbar")
        self.addToolBar(toolbar)

        self._navig_and_select_buttongroup = SemiExclusiveButtonGroup()

        self.home_button = create_toolbutton(
            self, icon='home',
            text=_("Home"),
            tip=_('Reset original view'),
            shortcut='Ctrl+Home',
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
            tip=_('Zoom to rectangle'),
            shortcut='Ctrl+Z',
            toggled=self.canvas.zoom_to_rect,
            iconsize=get_iconsize())
        toolbar.addWidget(self.zoom_to_rect_button)
        self._navig_and_select_buttongroup.add_button(self.zoom_to_rect_button)

        # ---- Select and transform data.
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
            text=_("Clear"),
            tip=_('Clear all selected data'),
            triggered=self.canvas.figure.clear_selected_data,
            iconsize=get_iconsize())
        toolbar.addWidget(self.clear_selected_data_button)

        # ---- Save figure and data.
        toolbar.addSeparator()

        self.save_figure_button = create_toolbutton(
            self, icon='save',
            text=_("Save"),
            tip=_('Save the figure to a file'),
            shortcut='Ctrl+S',
            triggered=self.canvas.toolbar.save_figure,
            iconsize=get_iconsize())
        toolbar.addWidget(self.save_figure_button)

        # ---- Timeseries selection.
        axis_toolbar = create_mainwindow_toolbar("Axis toolbar")
        self.addToolBarBreak(Qt.TopToolBarArea)
        self.addToolBar(axis_toolbar)

        # Axes visibility.
        self.visible_axes_button = create_toolbutton(
            self, icon='eye_on',
            text=_("Toggle axe visibility"),
            tip=_('Toggle currently selected axe visibility.'),
            toggled=self._handle_axe_visibility_changed,
            iconsize=get_iconsize())
        axis_toolbar.addWidget(self.visible_axes_button)

        # Current axe selection.
        self.current_axe_button = DropdownToolButton(
            'checklist', get_iconsize(), self)
        self.current_axe_button.sig_checked_action_changed.connect(
            self._handle_selected_axe_changed)
        axis_toolbar.addWidget(self.current_axe_button)

    def create_axe(self, tseries_group, where=None):
        """
        Create and add a new axe to the figure where to plot the data
        contained in the timeseries group.
        """
        axe = self.canvas.create_axe(tseries_group, where)

        # Add axe to selection menu.
        # Note that this will make the corresponding axe to become current.
        self.current_axe_button.create_action(tseries_group.prop_name,
                                              data=axe)
        return axe

    @Slot(QAction)
    def _handle_selected_axe_changed(self, checked_action):
        """
        Handle when the current axe is changed by the user.
        """
        selected_axe = checked_action.data()
        selected_axe.set_current()
        self.visible_axes_button.setChecked(not selected_axe.get_visible())

    def _handle_axe_visibility_changed(self, toggle):
        """
        Toggle on or off the visibility of the current matplotlib axe and
        enable or disable items in the gui accordingly.
        """
        checked_action = self.current_axe_button.checked_action()
        if checked_action is not None:
            selected_axe = checked_action.data()
            selected_axe.set_visible(not toggle)
            self.visible_axes_button.setIcon(
                get_icon('eye_on' if not toggle else 'eye_off'))

            # Update the navigation and selection tools state.
            self._navig_and_select_buttongroup.set_enabled(not toggle)
            if toggle is True:
                self._navig_and_select_buttongroup.toggle_off()
            else:
                self._navig_and_select_buttongroup.restore_last_toggled()
            self.canvas.draw()
            self.current_axe_button.repaint()
            self._update_selected_axe_cbox_state()

    def _update_selected_axe_cbox_state(self):
        """
        Enable or disable the actions of the current axe button's menu
        depending on the visibility of their corresponding matplotlib axe.
        """
        menu = self.current_axe_button.menu()
        for index, action in enumerate(menu.actions()):
            action.setEnabled(action.data().get_visible())

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