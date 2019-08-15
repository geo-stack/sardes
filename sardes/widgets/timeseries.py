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
from qtpy.QtCore import Qt, QEvent, QSize, Slot
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import (
    QAbstractButton, QActionGroup, QApplication, QMainWindow, QMenu,
    QSizePolicy, QStyle, QStyleOptionToolButton, QStylePainter, QToolButton)

# ---- Local imports
from sardes.config.locale import _
from sardes.config.icons import get_icon
from sardes.config.gui import get_iconsize
from sardes.utils.qthelpers import (
    center_widget_to_another, create_mainwindow_toolbar, create_toolbutton,
    create_action)


class TimeSeriesAxes(MplAxes):
    # https://matplotlib.org/3.1.1/api/axes_api.html

    def __init__(self, tseries_figure, ylabel=None, where='left'):
        super().__init__(tseries_figure,
                         tseries_figure.base_axes.get_position(),
                         facecolor=None,
                         frameon=False,
                         sharex=tseries_figure.base_axes)
        self.figure.add_tseries_axes(self)

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
        self.xaxis.set_visible(False)
        self.patch.set_visible(False)
        self.tick_params(labelsize=self.figure.canvas.font().pointSize())

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
            self.plot(tseries.data, color=tseries.color, clip_on=True))
        self._mpl_artist_handles['selected_data'][tseries.id], = (
            self.plot(tseries.get_selected_data(), '.', color='orange',
                      clip_on=True))
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
        self.base_axes = self.add_subplot(1, 1, 1)
        self.base_axes.set_zorder(0)
        self.base_axes.set_yticks([])
        self.base_axes.tick_params(labelsize=self.canvas.font().pointSize(),
                                   left=False, right=False,
                                   labelleft=False, labelright=False)
        self.base_axes.set_visible(False)
        self.canvas.draw()

    def add_tseries_axes(self, tseries_axes):
        self.base_axes.set_visible(True)
        self.tseries_axes_list.append(tseries_axes)
        self.add_axes(tseries_axes)

    def set_current_tseries_axes(self, current_tseries_axes):
        self.sca(current_tseries_axes)
        for tseries_axes in self.tseries_axes_list:
            tseries_axes.set_zorder(
                self.CURRENT_AXE_ZORDER if
                tseries_axes == current_tseries_axes else
                self.SEC_AXE_ZORDER)
            tseries_axes.set_navigate(tseries_axes == current_tseries_axes)
            tseries_axes._draw_selected_data()

    def set_size_inches(self, *args, **kargs):
        super().set_size_inches(*args, **kargs)
        self.tight_layout()

    def clear_selected_data(self):
        "Clear the selected data for the currently selected axe."
        current_axe = self.gca()
        try:
            current_axe.clear_selected_data()
        except AttributeError:
            pass

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
            bottom_margin = 0.5 / fheight
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
        figure.setup_base_axes()

        self.waterlevels = None

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

    def create_axe(self, ylabel='', where='left'):
        # Create the new axe from the base axe so that they share the same
        # xaxis.
        axe = TimeSeriesAxes(self.figure, ylabel, where)
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
        self._pan_axes_is_active = toggle
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


class LeftTextAlignedToolButton(QToolButton):

    def __init__(self, icon, iconsize, parent=None):
        super().__init__(parent)
        self.setIcon(get_icon(icon))
        self.setIconSize(QSize(iconsize, iconsize))
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        self.setMenu(QMenu(self))
        self.setPopupMode(self.InstantPopup)
        self.menu().installEventFilter(self)

        policy = self.sizePolicy()
        policy.setVerticalPolicy(QSizePolicy.Expanding)
        self.setSizePolicy(policy)

        self._action_group = QActionGroup(self)

    def eventFilter(self, widget, event):
        if event.type() == QEvent.MouseButtonRelease and widget == self.menu():
            clicked_action = widget.actionAt(event.pos())
            if clicked_action is not None:
                clicked_action.setChecked(True)
                self.menu().close()
                event.accept()
        return super().eventFilter(widget, event)

    def action_group(self):
        return self._action_group

    def checked_action(self):
        return self._action_group.checkedAction()

    def wheelEvent(self, event):
        checked_action = self.checked_action()
        actions = self.menu().actions()
        for index, action in enumerate(actions):
            if action == checked_action:
                break
        if event.angleDelta().y() < 0:
            index = index - 1 if index > 0 else (len(actions) - 1)
        else:
            index = index + 1 if index < (len(actions) - 1) else 0
        actions[index].setChecked(True)
        return super().wheelEvent(event)

    def paintEvent(self, event):
        """
        Override Qt method to align the icon and text to the left.
        """
        sp = QStylePainter(self)
        opt = QStyleOptionToolButton()
        self.initStyleOption(opt)

        # Draw background.
        opt.text = ''
        opt.icon = QIcon()
        sp.drawComplexControl(QStyle.CC_ToolButton, opt)

        # Draw icon.
        sp.drawItemPixmap(opt.rect,
                          Qt.AlignLeft | Qt.AlignVCenter,
                          self.icon().pixmap(self.iconSize()))

        # # Draw text.
        # palette = QPalette()
        # if not self.checked_action().data().get_visible():
        #     palette.setColor(palette.ButtonText, QColor(200, 200, 200))
        # self.setPalette(palette)

        opt.rect.translate(self.iconSize().width() + 3, 0)
        sp.drawItemText(opt.rect,
                        Qt.AlignLeft | Qt.AlignVCenter,
                        self.palette(),
                        True,
                        self.text())


class SemiExclusiveButtonGroup(object):

    def __init__(self):
        super().__init__()
        self.buttons = []
        self._last_toggled_button = None
        self._is_enabled = True

    def add_button(self, button):
        self.buttons.append(button)
        button.toggled.connect(
            lambda checked: self._handle_button_toggled(button, checked))

    def set_enabled(self, state):
        self._is_enabled = state
        for button in self.buttons:
            button.setEnabled(state)

    def toggle_off(self):
        for button in self.buttons:
            button.setChecked(False)

    def restore_last_toggled(self):
        if self._last_toggled_button is not None and self._is_enabled:
            self._last_toggled_button.setChecked(True)

    @Slot(QAbstractButton, bool)
    def _handle_button_toggled(self, toggled_button, checked):
        if checked is True:
            self._last_toggled_button = toggled_button
            for button in self.buttons:
                if button != toggled_button:
                    button.setChecked(False)


class TimeSeriesPlotViewer(QMainWindow):

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
            tip=_('Select data by clicking with the mouse and dragging'
                  ' the cursor vertically over a given span of the data on'
                  ' the graph.'),
            toggled=self._handle_axe_visibility_changed,
            iconsize=get_iconsize())
        axis_toolbar.addWidget(self.visible_axes_button)

        # Current axe selection.
        self.current_axe_button = LeftTextAlignedToolButton(
            'checklist', get_iconsize(), self)
        axis_toolbar.addWidget(self.current_axe_button)

    def create_axe(self, name, where='left'):
        axe = self.canvas.create_axe(name, where)

        # Add axe to selection menu.
        # Note that checking the action will cause the corresponding axe
        # to become current.
        action = create_action(
            self.current_axe_button.action_group(),
            name,
            toggled=self._handle_selected_axe_changed,
            data=axe)
        self.current_axe_button.menu().addAction(action)
        action.setChecked(True)

        return axe

    def _handle_selected_axe_changed(self, toggle):
        checked_action = self.current_axe_button.checked_action()
        if checked_action:
            self.current_axe_button.setText(checked_action.text())
            selected_axe = checked_action.data()
            selected_axe.set_current()
            self.visible_axes_button.setChecked(not selected_axe.get_visible())

    def _handle_axe_visibility_changed(self, toggle):
        checked_action = self.current_axe_button.checked_action()
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
        self._update_selected_axe_cbox_colors()

    def _update_selected_axe_cbox_colors(self):
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
