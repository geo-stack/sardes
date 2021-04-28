# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import os

# ---- Third party imports
from appconfigs.user import NoDefault
from qtpy.QtCore import QObject, Qt, Slot, QPoint, Signal
from qtpy.QtWidgets import (QDockWidget, QGridLayout, QWidget, QFrame,
                            QStyle, QApplication, QLabel)

# ---- Local imports
from sardes.config.icons import get_icon
from sardes.config.main import CONF
from sardes.utils.qthelpers import (
    create_action, qbytearray_to_hexstate,
    hexstate_to_qbytearray, create_toolbutton)


class DockWidgetTitleBar(QWidget):
    """
    A custom title bar widget for the SardesDockWindow.
    """

    def __init__(self, plugin, parent=None):
        super().__init__(parent)

        style = QApplication.instance().style()
        title_label = QLabel(plugin.get_plugin_title())

        # https://code.qt.io/cgit/qt/qtbase.git/tree/src/widgets/widgets/qdockwidget.cpp
        # Dock Widget title buttons on Windows where historically limited
        # to size 10 (from small icon size 16) since only a 10x10 XPM was
        # provided. Adding larger pixmaps to the icons thus caused the icons
        # to grow; limit this to qpiScaled(10) here.
        if os.name == 'nt':
            iconsize = style.pixelMetric(QStyle.PM_SmallIconSize)
            iconsize = min(10 * self.logicalDpiX() / 96, iconsize)

        self.close_btn = create_toolbutton(
            self,
            icon=style.standardIcon(QStyle.SP_TitleBarCloseButton),
            iconsize=iconsize
            )
        self.close_btn.setFocusPolicy(Qt.NoFocus)

        self.undock_btn = create_toolbutton(
            self,
            icon=style.standardIcon(QStyle.SP_TitleBarNormalButton),
            iconsize=iconsize
            )
        self.undock_btn.setFocusPolicy(Qt.NoFocus)

        # Setup title banner.
        banner = QFrame()
        banner.setLineWidth(1)
        banner.setMidLineWidth(0)
        banner.setFrameStyle(banner.Box | banner.Plain)

        banner.setObjectName('titlebarbanner')
        banner.setAutoFillBackground(True)
        c1, c2 = 220, 190
        banner.setStyleSheet((
            "QFrame#titlebarbanner{"
            "background-color: rgb(%d, %d, %d);"
            "border: 1px solid rgb(%d, %d, %d);"
            "}" % (c1, c1, c1, c2, c2, c2)))

        height = style.pixelMetric(QStyle.PM_TitleBarHeight)
        margin = 2 * style.pixelMetric(
            QStyle.PM_DockWidgetTitleMargin)
        banner.setFixedHeight(height - margin)

        banner_layout = QGridLayout(banner)
        banner_layout.setSpacing(0)
        banner_layout.setContentsMargins(4, 1, 0, 0)
        banner_layout.addWidget(title_label, 0, 0)
        banner_layout.setColumnStretch(0, 1)
        banner_layout.addWidget(self.undock_btn, 0, 1)
        banner_layout.addWidget(self.close_btn, 0, 2)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 1, 0, 2)
        layout.addWidget(banner)


class SardesDockWindow(QFrame):
    """
    A frame that can display the content of a Sardes plugin pane either
    encased in a dockwidget docked in the main window or as a
    separate full fledged independent window when undocked.
    """
    sig_docked_changed = Signal(bool)
    sig_docked = Signal()
    sig_undocked = Signal()
    sig_view_toggled = Signal(bool)

    def __init__(self, widget, plugin, undocked_geometry, is_docked,
                 is_locked=True):
        super().__init__()
        self.plugin = plugin
        self.widget = widget
        self.dock_btn = None

        self._focused_widget = None
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
            toggled=self.toggle_view)

        layout = QGridLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.addWidget(self.widget, 0, 0)

        self._setup_dockwidget()
        self.setWindowTitle(plugin.get_plugin_title())
        self.setWindowIcon(plugin.get_plugin_icon())

        self.sig_docked.connect(lambda: self.sig_docked_changed.emit(True))
        self.sig_undocked.connect(lambda: self.sig_docked_changed.emit(False))

    # ---- Private API
    def _setup_dockwidget(self):
        """
        Setup the dockwidget used to encased this dockwindow in the
        mainwindow.
        """
        self.dockwidget = QDockWidget()
        self.dockwidget.setAllowedAreas(Qt.LeftDockWidgetArea)
        self.dockwidget.setObjectName(self.plugin.__class__.__name__ + "_dw")

        self.dockwidget_titlebar = DockWidgetTitleBar(
            self.plugin, self.dockwidget)
        self.dockwidget_titlebar.close_btn.clicked.connect(
            lambda: self.toggle_view(False))
        self.dockwidget_titlebar.undock_btn.clicked.connect(self.undock)

        if self._is_docked is True:
            self.dockwidget.setWidget(self)
        self.set_locked(self._is_locked)

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
        self._focused_widget = self.focusWidget()
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
            cp = parent.mapToGlobal(QPoint(wp // 2, hp // 2))
            qr.moveCenter(cp)
            self.move(qr.topLeft())
        self.show()
        self.activateWindow()
        self.raise_()
        if self._focused_widget is not None:
            self._focused_widget.setFocus()
        self.sig_undocked.emit()

    def dock(self):
        """
        Encase this dockwindow in a dockwidget and dock it in the mainwindow.
        """
        self._focused_widget = self.focusWidget()
        self._is_docked = True
        if not self.is_docked() and self.is_visible():
            self._undocked_geometry = self.saveGeometry()
        self.dockwidget.setWidget(self)
        self.setWindowFlags(Qt.Widget)
        self.dockwidget.show()
        self.dockwidget.activateWindow()
        self.dockwidget.raise_()
        if self._focused_widget is not None:
            self._focused_widget.setFocus()
        self.sig_docked.emit()

    def toggle_view(self, toggle):
        """
        Toggle the visibility of this dockwindow on or off.

        Parameters
        ----------
        toggle: bool
            Whether this dockwindow is visible or not in the main application.
        """

        self._toggle_view_action.blockSignals(True)
        self._toggle_view_action.setChecked(toggle)
        self._toggle_view_action.blockSignals(False)

        if toggle and self._is_docked:
            self.dockwidget.show()
            self.dockwidget.raise_()
            self.show()
        elif toggle and not self._is_docked:
            self.show()
            self.raise_()
        elif not toggle and self._is_docked:
            self.dockwidget.hide()
            self.hide()
        elif not toggle and not self._is_docked:
            self.hide()
        self.sig_view_toggled.emit(toggle)

    def set_locked(self, locked):
        """
        If locked, hide the title bar and make the dockwidget if this
        dockwindow un-movable and un-closable.
        """
        self._is_locked = locked
        self.setFeatures(
            QDockWidget.NoDockWidgetFeatures if locked else
            QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable
            )
        self.dockwidget.setTitleBarWidget(
            QWidget() if locked else self.dockwidget_titlebar)

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
        if not self._is_docked:
            self.dock()
        event.ignore()

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
            self.set_option('is_visible', self.dockwindow.is_visible())

    def switch_to_plugin(self):
        """"Switch to this plugin."""
        if self.dockwindow.is_docked():
            self.dockwindow.dockwidget.show()
            self.dockwindow.dockwidget.activateWindow()
            self.dockwindow.dockwidget.raise_()
        else:
            # If window is minimised, restore it.
            if self.dockwindow.windowState() == Qt.WindowMinimized:
                self.dockwindow.setWindowState(Qt.WindowNoState)
            self.dockwindow.show()
            self.dockwindow.activateWindow()
            self.dockwindow.raise_()

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
            self.dockwindow.sig_view_toggled.connect(
                self.on_pane_view_toggled)
            self.dockwindow.sig_docked.connect(self.on_docked)
            self.dockwindow.sig_undocked.connect(self.on_undocked)
            if self.dockwindow.is_docked():
                self.on_docked()
            else:
                self.on_undocked()

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
            self.dockwindow.undock()

    def close_plugin(self):
        """
        Close this plugin dockwindow if it exists.
        """
        if self.dockwindow is not None:
            self.save_geometry_and_state()
            self.dockwindow.close()

    @Slot()
    def on_docked(self):
        """
        A slot called when the dockwindow is docked in the mainwindow.
        """
        pass

    @Slot()
    def on_undocked(self):
        """
        A slot called when the dockwindow is detached in the mainwindow.
        """
        pass

    @Slot(bool)
    def on_pane_view_toggled(self, toggled):
        """
        A slot called when the dockwindow is hidden or shown.
        """
        pass
