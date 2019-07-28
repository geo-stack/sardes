# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
from qtpy.QtCore import QEvent, QObject, Qt, Slot
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import (QGridLayout, QDockWidget, QHBoxLayout,
                            QVBoxLayout, QWidget)

# ---- Local imports
from sardes.config.gui import (get_layout_horizontal_spacing,
                               get_toolbar_item_spacing)
from sardes.utils.qthelpers import create_action, create_toolbar_separator


class SardesPluginBase(QObject):
    """
    Basic functionality for Sardes plugins.

    WARNING: Don't override any methods or attributes present here!
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # This is the plugin parent, which corresponds to the main window.
        self.main = parent
        # This is the dock widget for the plugin, i.e. the pane that's going
        # to be displayed in Sardes main window for this plugin.
        self.dockwidget = None
        self.pane_widget = None

        self._toggle_dockwidget_view_shortcut = None
        self._toggle_dockwidget_view_action = None

    def main_toolbars(self):
        return []

    def main_option_actions(self):
        return []

    def lock_pane_and_toolbar(self, state):
        """
        Lock or unlock this plugin dockwidget and mainwindow toolbars.
        """
        if self.dockwidget is not None:
            self.dockwidget.setFloating(
                not state and self.dockwidget.isFloating())
            self.dockwidget.setFeatures(
                self.dockwidget.NoDockWidgetFeatures if state
                else self.dockwidget.AllDockWidgetFeatures)
            self.dockwidget.setTitleBarWidget(QWidget() if state else None)

    # ---- Public methods
    def _setup_dockwidget(self):
        self.pane_widget = self.get_pane_widget()
        if self.main is not None and self.pane_widget is not None:
            self.dockwidget = QDockWidget()
            self.dockwidget.setObjectName(
                self.__class__.__name__ + "_dw")
            self.dockwidget.setWidget(self.pane_widget)

            self.dockwidget.setWindowTitle(self.get_plugin_title())

            # Add the dockwidget to the mainwindow.
            self.main.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)

            # Add a toggle view action for this plugin's dockwidget to the
            # panes menu of the mainwindow's options menu.
            self._dockwidget_toggle_view_action = (
                self.dockwidget.toggleViewAction())
            self.main.panes_menu.addAction(self._dockwidget_toggle_view_action)

    def _setup_plugin(self):
        """
        Setup Options menu, create toggle action and connect signals.
        """
        pass

    @Slot(bool)
    def _toggle_dockwidget_view(self, checked):
        """
        Toggle dockwidget's visibility when its entry is selected in
        the menu `View > Panes`.

        Parameters
        ----------
        checked: bool
            Is the entry in `View > Panes` checked or not?
        """
        if self.dockwidget is not None:
            if checked:
                self.dockwidget.show()
                self.dockwidget.raise_()
            else:
                self.dockwidget.hide()


class SardesPlugin(SardesPluginBase):
    """
    Sardes plugin class.

    All plugins *must* inherit this class and reimplement its interface.
    """

    # Name of the configuration section that's going to be used to record
    # the plugin's permanent data in Sardes config system (i.e. in sardes.ini)
    # Status: Optional
    CONF_SECTION = None

    # Widget to be used as entry in Sardes Preferences dialog
    # Status: Optional
    CONFIGWIDGET_CLASS = None

    def get_plugin_title(self):
        """
        Get plugin's title.

        Returns
        -------
        str
            Name of the plugin.
        """
        raise NotImplementedError

    def get_pane_widget(self):
        return None

    def register_plugin(self):
        """
        Register this plugin in Sardes's mainwindow and connect it to other
        plugins.
        """
        self._setup_dockwidget()

    def close_plugin(self):
        """
        Close this plugin panewidget and dockwidget if they exist.
        """
        if self.pane_widget:
            self.pane_widget.close()
        if self.dockwidget:
            self.dockwidget.close()


class SardesPaneWidget(QWidget):
    """
    Sardes pane widget class.

    All plugin that need to add a pane to Sardes mainwindow *must* use this
    class to encapsulate their main interface.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._upper_toolbar = None
        self._lower_toolbar = None
        self._main_widget = None

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

    # ---- Setup
    def _setup_upper_toolbar(self):
        self._upper_toolbar = SardesToolbarWidget()
        self.layout().addWidget(self._upper_toolbar, 0, 0)

    def _setup_lower_toolbar(self):
        self._lower_toolbar = SardesToolbarWidget()
        self.layout().addWidget(self._lower_toolbar, 2, 0)

    def _setup_main_widget(self):
        if self._main_widget is not None:
            self.layout().addWidget(self._main_widget, 1, 0)

    # ---- Public methods
    def get_main_widget(self):
        return self._main_widget

    def set_main_widget(self, main_widget):
        self._main_widget = main_widget
        self._setup_main_widget()

    def get_upper_toolbar(self):
        if self._upper_toolbar is None:
            self._setup_upper_toolbar()
        return self._upper_toolbar

    def get_lower_toolbar(self):
        if self._lower_toolbar is None:
            self._setup_lower_toolbar()
        return self._lower_toolbar


class SardesToolbarWidget(QWidget):
    """
    Sardes toolbar widget class.

    All Sardes pane widgets must use this class for their uppermost toolbar.
    """
    CLOSE_COL = 0
    CONTENT_COL = 2
    OPTIONS_COL = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QGridLayout(self)
        self.layout.setHorizontalSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

    # ---- Private methods
    def _add_new_row(self):
        """Add a new row to this toolbar."""
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(get_toolbar_item_spacing())
        row = self.layout.rowCount()
        colspan = 1 if row == 0 else 3
        self.layout.addLayout(row_layout, row, self.CONTENT_COL, 1, colspan)

    def _get_layout_at_row(self, row, require_row=False):
        """
        Return the layout at row.
        """
        layout_at_row = self._get_layout_at_row(row)
        if require_row is True:
            while layout_at_row is None:
                self._add_new_row()
                layout_at_row = self._get_layout_at_row(row)
        return layout_at_row

    # ---- Public methods
    def set_row_visible(self, row, state):
        """
        Set the visibility of all widgets at row to state.
        """
        layout_at_row = self._get_layout_at_row(row)
        if (state and not self.isVisible()) or layout_at_row is None:
            return
        for index in range(layout_at_row.count()):
            try:
                layout_at_row.itemAt(index).widget().setVisible(state)
            except AttributeError:
                pass

    def add_item(self, item, stretch=None, row=0):
        """
        Add a widget, a separator or an empty space to the end of this
        toolbar's row.
        """
        if item is None:
            self.add_separator(row)
        elif isinstance(item, int):
            self.add_spacing(spacing=item, row=row)
        else:
            self.add_widget(item, stretch, row)

    def add_separator(self, row=0):
        """
        Add a separator to the end of this toolbar's row.
        """
        self.add_widget(create_toolbar_separator(), stretch=None, row=row)

    def add_widget(self, widget, stretch=None, row=0):
        """
        Add a widget with an horizontal stretch factor stretch to the end
        of this toolbar's row.
        """
        layout_at_row = self._get_layout_at_row(row, require_row=True)
        layout_at_row.addWidget(widget)
        if stretch is not None:
            layout_at_row.setStretchFactor(widget, stretch)

    def add_stretch(self, stretch, row=0):
        """
        Add a stretchable space with zero minimum size and stretch factor
        stretch to the end of this toolbar's row.
        """
        layout_at_row = self._get_layout_at_row(row, require_row=True)
        layout_at_row.addStretch(stretch)

    def add_spacing(self, spacing, row=0):
        """
        Add a non-stretchable space with size spacing to the end
        of this toolbar's row.
        """
        row_layout = self._get_hboxlayout_at_row(row)
        row_layout.addSpacing(spacing)

    def add_options_button(self, options_button, stretch=1):
        """Add `options_button` to the top right corner of this toolbar."""
        self.layout.setColumnMinimumWidth(
            self.OPTIONS_COL - 1, get_toolbar_item_spacing())
        if stretch is not None:
            self.layout.setColumnStretch(self.OPTIONS_COL - 1, stretch)
        self.layout.addWidget(options_button, 0, self.OPTIONS_COL)

    def add_close_button(self, close_button):
        """Add `close_button` to the top left corner of this toolbar."""
        spacing = get_layout_horizontal_spacing()
        self.layout.setColumnMinimumWidth(self.CLOSE_COL + 1, spacing)
        self.layout.addWidget(close_button, 0, self.CLOSE_COL)

    def set_iconsize(self, iconsize):
        """Set the icon size of the toolbar."""
        pass
    #     set_iconsize_recursively(iconsize, self.layout)
