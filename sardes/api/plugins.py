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
from qtpy.QtCore import QObject, Qt, Slot, QPoint
from qtpy.QtGui import QPalette
from qtpy.QtWidgets import (QDockWidget, QGridLayout, QWidget, QFrame,
                            QToolBar, QStyle, QApplication, QStyleOption,
                            QPushButton, QStyleOptionDockWidget,
                            QStylePainter, QStyleOptionFrame, QLabel)

# ---- Local imports
from sardes.api.panes import SardesPaneWidget, SardesDockingButton
from sardes.config.icons import get_icon
from sardes.config.main import CONF
from sardes.utils.qthelpers import (
    create_toolbar_stretcher, create_action, qbytearray_to_hexstate,
    hexstate_to_qbytearray, create_toolbutton)


class SardesDockWindow(QFrame):
    """
    A frame that can display the content of a Sardes plugin pane either
    encased in a dockwidget docked in the main window or as a
    separate full fledged independent window when undocked.
    """

    def __init__(self, widget, plugin, undocked_geometry, is_docked,
                 is_locked=True):
        super().__init__()
        self.plugin = plugin
        self.widget = widget
        self.dock_btn = None

        self._undocked_geometry = undocked_geometry
        self._is_docked = is_docked
        self._is_locked = is_locked
        if is_docked:
            self.setWindowFlags(Qt.Widget)
        else:
            self.setWindowFlags(Qt.Window)
            if undocked_geometry is not None:
                self.restoreGeometry(self._undocked_geometry)

        self._toggle_view_action = create_action(
            self, text=plugin.get_plugin_title(),
            toggled=self._handle_view_action_toggled)

        self._setup_layout()
        self._setup_dockwidget()
        self._setup_widget()
        self.setWindowTitle(plugin.get_plugin_title())
        self.setWindowIcon(plugin.get_plugin_icon())

    # ---- Private API
    def _setup_layout(self):
        """
        Setup the layout of this dockwindow.
        """
        layout = QGridLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)

    def _setup_dockwidget(self):
        """
        Setup the dockwidget used to encased this dockwindow in the
        mainwindow.
        """
        class _DockWidget(QDockWidget):
            def __init__(self, toggle_view_action, *args, **kargs):
                super().__init__(*args, **kargs)
                self._toggle_view_action = toggle_view_action

            def showEvent(self, event):
                """
                Override this QT event to synchronize the toggle view
                action of the dockwindow contained by this dockwidget
                when shown.
                """
                self._toggle_view_action.blockSignals(True)
                self._toggle_view_action.setChecked(True)
                self._toggle_view_action.blockSignals(False)

            def closeEvent(self, event):
                """
                Override this QT event to synchronize the toggle view
                action of the dockwindow contained by this dockwidget
                when closed.
                """
                self._toggle_view_action.blockSignals(True)
                self._toggle_view_action.setChecked(False)
                self._toggle_view_action.blockSignals(False)
                super().closeEvent(event)

        self.dockwidget = _DockWidget(self._toggle_view_action)
        self.dockwidget.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.dockwidget.setObjectName(self.plugin.__class__.__name__ + "_dw")
        if self._is_docked is True:
            self.dockwidget.setWidget(self)
        self.set_locked(self._is_locked)

    def _setup_widget(self):
        """
        Setup the widget that this dockwindow is used to display.
        """
        self.layout().addWidget(self.widget, 0, 0)
        if (isinstance(self.widget, SardesPaneWidget) and
                self.widget._upper_toolbar is not None):
            self.dock_btn = SardesDockingButton(
                self.plugin.get_plugin_title(), self._is_docked)
            self.dock_btn.sig_undock_pane.connect(self.undock)
            self.dock_btn.sig_dock_pane.connect(self.dock)
            self.widget._upper_toolbar.addWidget(create_toolbar_stretcher())
            self.widget._upper_toolbar.addWidget(self.dock_btn)

    @Slot(bool)
    def _handle_view_action_toggled(self, checked):
        """
        Handle when the action to control this dockwindow's visibility
        is toggled on or off in the menu `View > Panes`.

        Parameters
        ----------
        checked: bool
            Is the entry in `View > Panes` checked or not?
        """
        if checked and self._is_docked:
            self.dockwidget.show()
            self.dockwidget.raise_()
            self.show()
        elif checked and not self._is_docked:
            self.show()
            self.raise_()
        elif not checked and self._is_docked:
            self.dockwidget.hide()
            self.hide()
        elif not checked and not self._is_docked:
            self.hide()

    # ---- Public API
    def undocked_geometry(self):
        """
        Return the geometry of this dockwindow when undocked.
        """
        if self._is_docked is False:
            return self.saveGeometry()
        else:
            return self._undocked_geometry

    def is_docked(self):
        """
        Return whether this dockwindow is docked or not.
        """
        return self._is_docked

    def is_visible(self):
        """
        Return whether this dockwindow is visible or not.
        """
        return self.isVisible()

    def undock(self):
        """
        Undock this dockwindow as a full fledged window.
        """
        self._is_docked = False
        self.dockwidget.setVisible(False)
        self.setParent(None)
        self.setWindowFlags(Qt.Window)
        if self._undocked_geometry is not None:
            self.restoreGeometry(self._undocked_geometry)
        else:
            # Since this is the first time this dockwindow is shown undocked,
            # we center its'position programmatically to that
            # of the mainwindow.
            qr = self.frameGeometry()
            parent = self.plugin.main
            wp = parent.frameGeometry().width()
            hp = parent.frameGeometry().height()
            cp = parent.mapToGlobal(QPoint(wp/2, hp/2))
            qr.moveCenter(cp)
            self.move(qr.topLeft())
        self.show()
        self.raise_()

    def dock(self):
        """
        Encase this dockwindow in a dockwidget and dock it in the mainwindow.
        """
        self._undocked_geometry = self.saveGeometry()
        self._is_docked = True
        self.dockwidget.setWidget(self)
        self.setWindowFlags(Qt.Widget)
        self.dockwidget.show()
        self.dockwidget.raise_()

    def set_locked(self, locked):
        """
        If locked, hide the title bar and make the dockwidget if this
        dockwindow un-movable and un-closable.
        """
        self._is_locked = locked
        self.setFeatures(
            QDockWidget.NoDockWidgetFeatures if locked else
            QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        self.dockwidget.setTitleBarWidget(QWidget() if locked else None)

    # ---- Qt Overrides
    def showEvent(self, event):
        """
        Override this QT event to synchronize the toggle view action related
        to this dockwindow when shown.
        """
        self._toggle_view_action.blockSignals(True)
        self._toggle_view_action.setChecked(True)
        self._toggle_view_action.blockSignals(False)

    def closeEvent(self, event):
        """
        Override this QT event to synchronize the toggle view action related
        to this dockwindow when closed.
        """
        self._toggle_view_action.blockSignals(True)
        self._toggle_view_action.setChecked(False)
        self._toggle_view_action.blockSignals(False)
        super().closeEvent(event)

    # ---- QDockWidget mocked API
    def setFeatures(self, *args, **kargs):
        return self.dockwidget.setFeatures(*args, **kargs)

    def setFloating(self, *args, **kargs):
        return self.dockwidget.setFloating(*args, **kargs)

    def setTitleBarWidget(self, *args, **kargs):
        return self.dockwidget.setTitleBarWidget(*args, **kargs)

    def isFloating(self, *args, **kargs):
        return self.dockwidget.isFloating()

    def setWindowTitle(self, title):
        self.dockwidget.setWindowTitle(title)
        return super().setWindowTitle(title)

    def toggleViewAction(self):
        return self._toggle_view_action


class SardesPluginBase(QObject):
    """
    Basic functionality for Sardes plugins.

    WARNING: Don't override any methods or attributes present here unless you
    know what you are doing.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # This is the plugin parent, which corresponds to the main window.
        self.main = parent

        # This is the dock widget for the plugin, i.e. the pane that's going
        # to be displayed in Sardes main window for this plugin.
        self.dockwindow = None

        self.setup_plugin()
        self.pane_widget = self.create_pane_widget()
        self.mainwindow_toolbars = self.create_mainwindow_toolbars()

    def main_option_actions(self):
        return []

    # ---- Public methods
    def dockwidget(self):
        """
        Return the dockwidget of this plugin if any.
        """
        return (self.dockwindow.dockwidget if self.dockwindow
                is not None else None)

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

    def lock_pane_and_toolbar(self, lock):
        """
        Lock or unlock this plugin dockwindow and mainwindow toolbars.
        """
        if self.dockwindow is not None:
            self.dockwindow.set_locked(lock)
        for toolbar in self.mainwindow_toolbars:
            toolbar.setMovable(not lock)

    def save_geometry_and_state(self):
        """
        Save the geometry and state of this plugin's dockwindow to the
        configurations.
        """
        if self.dockwindow is not None:
            undocked_geometry = self.dockwindow.undocked_geometry()
            if undocked_geometry is not None:
                self.set_option(
                    'undocked/geometry',
                    qbytearray_to_hexstate(undocked_geometry))
            self.set_option('is_docked', self.dockwindow._is_docked)

    # ---- Private internal methods
    def _setup_dockwindow(self):
        """
        Setup a dockwindow that is used to show the pane related to
        this plugin, if it exists, either encased in a dockwidget docked
        in the mainwindow or as a full fledged independent window when
        undocked.
        """
        if self.main is not None and self.pane_widget is not None:
            hexstate = self.get_option('undocked/geometry', None)
            undocked_geometry = (
                hexstate_to_qbytearray(hexstate) if hexstate is not
                None else None)

            self.dockwindow = SardesDockWindow(
                widget=self.pane_widget,
                plugin=self,
                undocked_geometry=undocked_geometry,
                is_docked=self.get_option('is_docked', True),
                )

            # Add the dockwidget to the mainwindow.
            self.main.addDockWidget(
                Qt.LeftDockWidgetArea, self.dockwindow.dockwidget)

            # Add a toggle view action for this plugin's dockwidget to the
            # panes menu of the mainwindow's options menu.
            self.main.panes_menu.addAction(self.dockwindow.toggleViewAction())

    def _setup_mainwindow_toolbars(self):
        """
        Setup any toolbar that need to be added to the mainwindow.
        """
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

    @classmethod
    def get_plugin_icon(cls):
        """
        Return the icon to used for this plugin. The default value is the icon
        used for Sardes mainwindow.
        """
        return get_icon('master')

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
        self._setup_dockwindow()
        self._setup_mainwindow_toolbars()
        self.lock_pane_and_toolbar(False)

    def show_plugin(self):
        """
        Show this plugin dockwindow if it exists, is visible and is not docked.

        This method is called by the mainwindow after it is shown.
        """
        is_visible = self.get_option('is_visible', False)
        is_docked = self.get_option('is_docked', True)
        if is_visible and not is_docked:
            self.dockwindow.show()
            self.dockwindow.raise_()

    def close_plugin(self):
        """
        Close this plugin dockwindow if it exists.
        """
        if self.dockwindow is not None:
            self.save_geometry_and_state()
            self.dockwindow.close()
