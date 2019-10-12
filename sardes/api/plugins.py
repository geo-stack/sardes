# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Third party imports
from appconfigs.user import NoDefault
from qtpy.QtCore import QObject, Qt, Slot
from qtpy.QtWidgets import QDockWidget, QGridLayout, QWidget

# ---- Local imports
from sardes.config.main import CONF


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

        self.setup_plugin()
        self.pane_widget = self.create_pane_widget()
        self.mainwindow_toolbars = self.create_mainwindow_toolbars()

        self._toggle_dockwidget_view_shortcut = None
        self._toggle_dockwidget_view_action = None

    def main_option_actions(self):
        return []

    # ---- Public methods
    def get_option(self, option, default=NoDefault):
        """
        Get an option from Sardes configuration file.

        Parameters
        ----------
        option: str
            Name of the option to get its value from.

        Returns
        -------
        bool, int, str, tuple, list, dict
            Value associated with `option`.
        """
        return CONF.get(self.CONF_SECTION, option, default)

    def set_option(self, option, value):
        """
        Set an option in Sardes configuration file.

        Parameters
        ----------
        option: str
            Name of the option (e.g. 'case_sensitive')
        value: bool, int, str, tuple, list, dict
            Value to save in configuration file, passed as a Python
            object.

        Notes
        -----
        * CONF_SECTION needs to be defined for this to work.
        """
        CONF.set(self.CONF_SECTION, option, value)

    def lock_pane_and_toolbar(self, state):
        """
        Lock or unlock this plugin dockwidget and mainwindow toolbars.
        """
        if self.dockwidget is not None:
            self.dockwidget.setFloating(
                not state and self.dockwidget.isFloating())
            self.dockwidget.setFeatures(
                QDockWidget.NoDockWidgetFeatures |
                QDockWidget.DockWidgetClosable if state else
                QDockWidget.AllDockWidgetFeatures)
            self.dockwidget.setTitleBarWidget(QWidget() if state else None)
        for toolbar in self.mainwindow_toolbars:
            toolbar.setMovable(not state)

    # ---- Private internal methods
    def _setup_dockwidget(self):
        if self.main is not None and self.pane_widget is not None:
            self.dockwidget = QDockWidget()
            self.dockwidget.setObjectName(
                self.__class__.__name__ + "_dw")

            # Encapsulate the pane widget in another widget to control the
            # size of the contents margins.
            self._pane_margins_widget = QWidget()
            layout = QGridLayout(self._pane_margins_widget)
            layout.addWidget(self.pane_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            self.dockwidget.setWidget(self._pane_margins_widget)

            self.dockwidget.setWindowTitle(self.get_plugin_title())

            # Add the dockwidget to the mainwindow.
            self.main.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)

            # Add a toggle view action for this plugin's dockwidget to the
            # panes menu of the mainwindow's options menu.
            self.main.panes_menu.addAction(self.dockwidget.toggleViewAction())

    def _setup_mainwindow_toolbars(self):
        for toolbar in self.mainwindow_toolbars:
            self.main.insertToolBar(self.main.options_menu_toolbar, toolbar)

            # Add a toggle view action for this toolbar to the
            # toolbars menu of the mainwindow's options menu.
            self.main.toolbars_menu.addAction(toolbar.toggleViewAction())

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

    @classmethod
    def get_plugin_title(cls):
        """
        Get plugin's title.

        Returns
        -------
        str
            Name of the plugin.
        """
        raise NotImplementedError

    def setup_plugin(self):
        pass

    def create_mainwindow_toolbars(self):
        return []

    def create_pane_widget(self):
        return None

    def register_plugin(self):
        """
        Register this plugin in Sardes's mainwindow and connect it to other
        plugins.
        """
        self._setup_dockwidget()
        self._setup_mainwindow_toolbars()

    def close_plugin(self):
        """
        Close this plugin panewidget and dockwidget if they exist.
        """
        if self.pane_widget:
            self.pane_widget.close()
        if self.dockwidget:
            self.dockwidget.close()
