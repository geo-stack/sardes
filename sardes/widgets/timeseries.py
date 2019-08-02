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
from matplotlib.widgets import RectangleSelector, SpanSelector
from matplotlib.dates import num2date
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (QAbstractButton, QApplication, QMainWindow)

# ---- Local imports
from sardes.config.locale import _
from sardes.config.gui import get_iconsize
from sardes.utils.qthelpers import (
    center_widget_to_another, create_mainwindow_toolbar, create_toolbutton)
class TimeSeriesAxes(MplAxes):
    # https://matplotlib.org/3.1.1/api/axes_api.html

    def __init__(self, tseries_figure, ylabel=None, where='left'):
        super().__init__(tseries_figure,
                         tseries_figure.base_axes.get_position(),
                         facecolor=None,
                         frameon=False,
                         sharex=tseries_figure.base_axes)
        self.figure.add_tseries_axes(self)
        self.patch.set_visible(False)

        # Init class attributes.
        self.tseries_list = []
        self._rect_selector = None
        self._hspan_selector = None
        self._vspan_selector = None
        self._mpl_artist_handles = {
            'data': {},
            'selected_data': {}}

        # Make sure the xticks and xticks labels are not shown for this
        # axe, because this is provided by the base axe.
        self.tick_params(labelsize=self.figure.canvas.font().pointSize(),
                         top=False, bottom=False,
                         labeltop=False, labelbottom=False)

        # Setup the new axe yaxis position and parameters.
        if where == 'right':
            self.yaxis.tick_right()
            self.yaxis.set_label_position('right')
        else:
            self.yaxis.tick_left()
            self.yaxis.set_label_position('left')
        self.tick_params(labelsize=self.figure.canvas.font().pointSize())

        # Setup the ylabel of the axe.
        if ylabel is not None:
            self.set_ylabel(ylabel, labelpad=10)

        self.figure.tight_layout(force=True)
        self.figure.canvas.draw()

    @property
    def rect_selector(self):
        if self._rect_selector is None:
            # Setup a new data rectangular selector for this axe.
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
        if self._hspan_selector is None:
            # Setup a new data horizontal span selector for this axe
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

    def add_timeseries(self, tseries):
        self.tseries_list.append(tseries)

        # Plot the data of the timeseries and init selected data artist.
        self._mpl_artist_handles['data'][tseries.id], = (
            self.plot(tseries.data, color=tseries.color))
        self._mpl_artist_handles['selected_data'][tseries.id], = (
            self.plot(tseries.get_selected_data(), '.', color='orange'))

        self.figure.canvas.draw()

    def set_current(self):
        self.figure.set_current_tseries_axes(self)

    def clear_selected_data(self):
        for tseries in self.tseries_list:
            tseries.clear_selected_data()
        self._draw_selected_data()

    # ---- Drawing methods
    def _draw_selected_data(self, draw=True):
        for tseries in self.tseries_list:
            if self.figure.gca() != self:
                (self._mpl_artist_handles['selected_data'][tseries.id]
                 .set_visible(False))
            else:

                selected_data = tseries.get_selected_data()
                # Update the selected data plot for the current axe.
                (self._mpl_artist_handles['selected_data'][tseries.id]
                 .set_data(selected_data.index.values, selected_data.values))

        if draw:
            self.figure.canvas.draw()

    # ----Data selection handlers
    def _handle_drag_select_data(self, eclick, erelease):
        """
        Handle when a rectangular area to select data has been selected.
        """
        xmin, xmax, ymin, ymax = self._rect_selector.extents
        for tseries in self.tseries_list:
            tseries.select_data(xrange=(num2date(xmin), num2date(xmax)),
                                yrange=(ymin, ymax))
        self._draw_selected_data()

    def _handle_hspan_select_data(self, xmin, xmax):
        for tseries in self.tseries_list:
            tseries.select_data(xrange=(num2date(xmin), num2date(xmax)))
        self._draw_selected_data()

    def _handle_vspan_select_data(self, ymin, ymax):
        for tseries in self.tseries_list:
            tseries.select_data(yrange=(ymin, ymax))
        self._draw_selected_data()


class TimeSeriesFigure(MplFigure):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.set_tight_layout(True)
        self._last_fsize = (self.bbox_inches.width, self.bbox_inches.height)

    # def set_size_inches(self, *args, **kargs):
    #     super().set_size_inches(*args, **kargs)
    #     self.tight_layout()

    # def set_axe_margins_inches(left, right, top, bottom):
    #     pass

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
            bottom_margin = 0.75 / fheight
            top_margin = 0.2 / fheight

            x0 = left_margin
            y0 = bottom_margin
            w = 1 - (left_margin + right_margin)
            h = 1 - (bottom_margin + top_margin)

            for axe in self.axes:
                axe.set_position([x0, y0, w, h])


class TimeSeriesCanvas(FigureCanvasQTAgg):

    def __init__(self, figure):
        super().__init__(figure)
        self._timeseries = {}
        self._rect_selectors = {}
        self._hspan_selectors = {}
        self._vspan_selectors = {}
        self._mpl_artist_handles = {
            'data': {},
            'selected_data': {}}

        self.waterlevels = None
        self.draw()

        # Setup a matplotlib navigation toolbar, but hide it.
        toolbar = NavigationToolbar2QT(self, self)
        toolbar.hide()

        self._pan_axes_is_active = False
        self._zoom_to_rect_is_active = False
        self._drag_select_data_is_active = False

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

    def add_timeseries(self, timeseries):
        """
        Add a new timeseries to plot on the figure of this canvas.
        """
        # Setup a new axe to plot this timeseries.
        if len(self.figure.axes) == 0:
            axe = self.figure.add_subplot(1, 1, 1)
        else:
            axe = self.figure.axes[0].twinx()
        axe.patch.set_visible(False)
        self.figure.tight_layout(force=True)

        # Plot the data of the timeseries and init selected data artist.
        self._mpl_artist_handles['data'][axe], = (
            axe.plot(timeseries.data))
        self._mpl_artist_handles['selected_data'][axe], = (
            axe.plot(timeseries.get_selected_data(), '.', color='orange'))

        # Setup a new data rectangular selector for this timeseries.
        rect_selector = RectangleSelector(
            axe,
            self._handle_drag_select_data,
            drawtype='box',
            useblit=True,
            button=[1],
            spancoords='data',
            interactive=False,
            rectprops=dict(facecolor='red',
                           edgecolor='black',
                           alpha=0.2,
                           fill=True,
                           linestyle=':')
            )
        rect_selector.set_active(False)

        # Setup a new data horizontal span selector for this timeseries.
        hspan_selector = SpanSelector(
            axe,
            self._handle_hspan_select_data,
            'horizontal',
            useblit=True,
            rectprops=dict(alpha=0.2,
                           facecolor='red',
                           edgecolor='black',
                           linestyle=':')
            )
        hspan_selector.set_active(False)

        # Setup a new data vertical span selector for this timeseries.
        vspan_selector = SpanSelector(
            axe,
            self._handle_vspan_select_data,
            'vertical',
            useblit=True,
            rectprops=dict(alpha=0.2,
                           facecolor='red',
                           edgecolor='black',
                           linestyle=':')
            )
        vspan_selector.set_active(False)

        self.figure.sca(axe)
        self._timeseries[axe] = timeseries
        self._rect_selectors[axe] = rect_selector
        self._hspan_selectors[axe] = hspan_selector
        self._vspan_selectors[axe] = vspan_selector

    def add_waterlevels(self, waterlevels):
        self.add_timeseries(waterlevels)

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
        self._pan_axes_is_active = toggle
        if toggle is True:
            if self.toolbar._active != 'PAN':
                self.toolbar.pan()
        else:
            if self.toolbar._active == 'PAN':
                self.toolbar.pan()

    def drag_select_data(self, toggle):
        """Toggle data mouse drag selection over a rectangle region."""
        if len(self.figure.axes):
            self._rect_selectors[self.figure.gca()].set_active(toggle)

    def hspan_select_data(self, toggle):
        """Toggle data mouse drag selection over an horizontal span."""
        if len(self.figure.axes):
            self._hspan_selectors[self.figure.gca()].set_active(toggle)

    def vspan_select_data(self, toggle):
        """Toggle data mouse drag selection over a vertical span."""
        if len(self.figure.axes):
            self._vspan_selectors[self.figure.gca()].set_active(toggle)

    def clear_selected_data(self):
        "Clear the selected data for all registered timeseries."
        for axe in self.figure.axes:
            self._timeseries[axe].clear_selected_data()
        self._draw_selected_data()

    # ---- Handlers
    def _handle_drag_select_data(self, eclick, erelease):
        """
        Handle when a rectangular area to select data has been selected.
        """
        current_axe = self.figure.gca()
        xmin, xmax, ymin, ymax = self._rect_selectors[current_axe].extents

        timeseries = self._timeseries[current_axe]
        timeseries.select_data(xrange=(num2date(xmin), num2date(xmax)),
                               yrange=(ymin, ymax))

        self._draw_selected_data()

    def _handle_hspan_select_data(self, xmin, xmax):
        current_axe = self.figure.gca()
        timeseries = self._timeseries[current_axe]
        timeseries.select_data(xrange=(num2date(xmin), num2date(xmax)))

        self._draw_selected_data()

    def _handle_vspan_select_data(self, ymin, ymax):
        current_axe = self.figure.gca()
        timeseries = self._timeseries[current_axe]
        timeseries.select_data(yrange=(ymin, ymax))

        self._draw_selected_data()

    # ---- Drawing methods
    def _draw_selected_data(self):
        current_axe = self.figure.gca()
        selected_data = self._timeseries[current_axe].get_selected_data()

        # Hide the selected data artist for all axes but the current one.
        for axe in self.figure.axes:
            self._mpl_artist_handles['selected_data'][axe].set_visible(
                axe == axe)

        # Update the selected data plot for the current axe.
        self._mpl_artist_handles['selected_data'][current_axe].set_data(
            selected_data.index.values, selected_data.values)
        self.draw()


class SemiExclusiveButtonGroup(object):

    def __init__(self):
        super().__init__()
        self.buttons = []

    def add_button(self, button):
        self.buttons.append(button)
        button.toggled.connect(
            lambda checked: self._handle_button_toggled(button, checked))

    @Slot(QAbstractButton, bool)
    def _handle_button_toggled(self, toggled_button, checked):
        if checked is True:
            for button in self.buttons:
                if button != toggled_button:
                    button.setChecked(False)


class TimeSeriesViewer(QMainWindow):

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
        toolbar.setMovable(False)
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
            triggered=self.canvas.clear_selected_data,
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

    def add_waterlevels(self, waterlevels):
        self.canvas.add_waterlevels(waterlevels)
        self.canvas.draw()

    def show(self):
        """
        Extend Qt show method to center this mainwindow to its parent's
        geometry.
        """
        self.resize(850, 500)
        if self.parent():
            self.setAttribute(Qt.WA_DontShowOnScreen, True)
            super().show()
            super().close()
            self.setAttribute(Qt.WA_DontShowOnScreen, False)
            center_widget_to_another(self, self.parent())
        super().show()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    viewer = TimeSeriesViewer()
    viewer.show()

    sys.exit(app.exec_())
