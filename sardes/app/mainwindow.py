# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import platform
import sys

# ---- Third party imports
from qtpy.QtCore import QPoint, QSize, Qt, QUrl
from qtpy.QtGui import QDesktopServices
from qtpy.QtWidgets import (QApplication, QActionGroup, QMainWindow, QMenu,
                            QMessageBox, QSizePolicy, QToolButton, QWidget)

# ---- Local imports
from sardes import __namever__, __project_url__
from sardes.config.icons import get_icon
from sardes.config.gui import (get_iconsize, get_window_settings,
                               set_window_settings)
from sardes.config.locale import (_, get_available_translations, get_lang_conf,
                                  LANGUAGE_CODES, set_lang_conf)
from sardes.database.manager import DatabaseConnectionManager
from sardes.widgets.databaseconnector import DatabaseConnectionWidget
from sardes.widgets.locationtable import LocationTableView
from sardes.utils.qthelpers import create_action, create_toolbutton

from multiprocessing import freeze_support
freeze_support()

GITHUB_ISSUES_URL = __project_url__ + "/issues"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._window_normal_size = [self.size()] * 2
        self._window_normal_pos = [self.pos()] * 2

        self.setWindowIcon(get_icon('master'))
        self.setWindowTitle(__namever__)
        if platform.system() == 'Windows':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                __namever__)

        # Toolbars
        self.visible_toolbars = []
        self.toolbarslist = []

        # Setup the database connection manager.
        self.db_connection_manager = DatabaseConnectionManager()

        # Setup the database connection widget.
        self.db_connection_widget = DatabaseConnectionWidget(
            self.db_connection_manager, self)
        self.db_connection_widget.hide()

        # Setup the database locations view table.
        self.location_view = LocationTableView(
            self.db_connection_manager, self)

        self.setup()

    def setup(self):
        """Setup the main window"""
        self.setCentralWidget(self.location_view)
        self.create_topright_corner_toolbar()

        self.set_window_settings(*get_window_settings())

    # ---- Toolbar setup
    def create_topright_corner_toolbar(self):
        """
        Create and add a toolbar to the top right corner of this
        application.
        """
        self.topright_corner_toolbar = self.create_toolbar(
            "Options toolbar", "option_toolbar")
        self.topright_corner_toolbar.setMovable(False)

        # Add a spacer item.
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.topright_corner_toolbar.addWidget(spacer)

        # Add the database connection manager button.
        self.database_button = create_toolbutton(
            self, triggered=self.db_connection_widget.show,
            text=_("Database connection"),
            tip=_("Open a dialog window to manage the "
                  "connection to the database."),
            shortcut='Ctrl+Shift+D')
        self.setup_database_button_icon()
        self.db_connection_manager.sig_database_connection_changed.connect(
            self.setup_database_button_icon)
        self.topright_corner_toolbar.addWidget(self.database_button)

        # Add the tools and options button.
        self.options_button = self.create_options_button()
        self.topright_corner_toolbar.addWidget(self.options_button)

    def create_options_button(self):
        """Create and return the options button of this application."""
        options_button = create_toolbutton(
            self, icon='tooloptions',
            text=_("Tools and options"),
            tip=_("Open the tools and options menu."),
            shortcut='Ctrl+Shift+T')
        options_button.setStyleSheet(
            "QToolButton::menu-indicator{image: none;}")
        options_button.setPopupMode(QToolButton.InstantPopup)

        # Create the tools and options menu.
        options_menu = self.create_options_menu()
        options_button.setMenu(options_menu)

        return options_button

    def create_options_menu(self):
        """Create and return the options menu of this application."""
        options_menu = QMenu(self)

        lang_menu = self.create_lang_menu()

        preferences_action = create_action(
            self, _('Preferences...'), icon='preferences',
            shortcut='Ctrl+Shift+P', context=Qt.ApplicationShortcut
            )
        report_action = create_action(
            self, _('Report an issue...'), icon='bug',
            shortcut='Ctrl+Shift+R', context=Qt.ApplicationShortcut,
            triggered=lambda: QDesktopServices.openUrl(QUrl(GITHUB_ISSUES_URL))
            )
        about_action = create_action(
            self, _('About Sardes...'), icon='information',
            shortcut='Ctrl+Shift+I', context=Qt.ApplicationShortcut
            )
        exit_action = create_action(
            self, _('Exit'), icon='exit', triggered=self.close,
            shortcut='Ctrl+Shift+Q', context=Qt.ApplicationShortcut
            )
        for item in [lang_menu, preferences_action, None, report_action,
                     about_action, exit_action]:
            if item is None:
                options_menu.addSeparator()
            elif isinstance(item, QMenu):
                options_menu.addMenu(item)
            else:
                options_menu.addAction(item)

        return options_menu

    def create_lang_menu(self):
        """Create and return the languages menu of this application."""
        lang_conf = get_lang_conf()

        self.lang_menu = QMenu(_('Languages'), self)
        self.lang_menu.setIcon(get_icon('languages'))

        action_group = QActionGroup(self)
        for lang in get_available_translations():
            lang_action = create_action(
                action_group, LANGUAGE_CODES[lang], icon='lang_' + lang,
                toggled=lambda _, lang=lang: self.set_language(lang))
            self.lang_menu.addAction(lang_action)
            if lang == lang_conf:
                lang_action.setChecked(True)
        return self.lang_menu

    def create_toolbar(self, title, object_name, iconsize=None):
        """Create and return a toolbar with title and object_name."""
        toolbar = self.addToolBar(title)
        toolbar.setObjectName(object_name)
        iconsize = get_iconsize() if iconsize is None else iconsize
        toolbar.setIconSize(QSize(iconsize, iconsize))
        self.toolbarslist.append(toolbar)
        return toolbar

    def setup_database_button_icon(self):
        """
        Set the icon of the database button to show whether a database is
        currently connected or not.
        """
        db_icon = ('database_connected' if
                   self.db_connection_manager.is_connected()
                   else 'database_disconnected')
        self.database_button.setIcon(get_icon(db_icon))

    def set_language(self, lang):
        """
        Set the language to be used by this application for its labels,
        menu, messages, etc.
        """
        if lang != get_lang_conf():
            set_lang_conf(lang)
            QMessageBox.information(
                self,
                _("Language change"),
                _("The language has been set to <i>{}</i>. Restart Sardes to "
                  "apply this change.").format(LANGUAGE_CODES[lang]))

    # ---- Main window settings
    def get_window_settings(self):
        """Return current window settings."""
        is_maximized = self.isMaximized()

        # NOTE: The isMaximized() method does not work as expected when used
        # in the resizeEvent() and moveEvent() that are caused by the window
        # maximization. It seems as if the state returned by isMaximized()
        # is set AFTER the resizeEvent() and moveEvent() were executed.
        # See this Qt bug https://bugreports.qt.io/browse/QTBUG-30085
        # for more information.
        # As a workaround, we store the last and second to last value of
        # the window size and position in the resizeEvent() and moveEvent()
        # regardless of the state of the window. We check for the
        # isMaximized() state here instead and return the right values
        # for the normal window size and position accordingly.
        index = 0 if is_maximized else 1
        window_size = (self._window_normal_size[index].width(),
                       self._window_normal_size[index].height())
        window_position = (self._window_normal_pos[index].x(),
                           self._window_normal_pos[index].y())
        return (window_size, window_position, is_maximized)

    def set_window_settings(self, window_size, window_position, is_maximized):
        """Set window settings"""
        self._window_normal_size = [QSize(*window_size)] * 2
        self._window_normal_pos = [QPoint(*window_position)] * 2

        self.resize(*window_size)
        self.move(*window_position)

        self.setWindowState(Qt.WindowNoState)
        if is_maximized:
            self.setWindowState(self.windowState() ^ Qt.WindowMaximized)
        self.setAttribute(Qt.WA_Resized, True)
        # NOTE: Setting the Qt.WA_Resized attribute to True is required or
        # else the size of the wigdet will not be updated correctly when
        # restoring the window from a maximized state and the layout won't
        # be expanded correctly to the full size of the widget.

    # ---- Main window events
    def closeEvent(self, event):
        """Reimplement Qt closeEvent."""
        set_window_settings(*self.get_window_settings())
        event.accept()

    def resizeEvent(self, event):
        """Reimplement Qt method."""
        if self.size() != self._window_normal_size[1]:
            self._window_normal_size[0] = self._window_normal_size[1]
            self._window_normal_size[1] = self.size()
        super().resizeEvent(event)

    def moveEvent(self, event):
        """Reimplement Qt method."""
        if self.pos() != self._window_normal_pos[1]:
            self._window_normal_pos[0] = self._window_normal_pos[1]
            self._window_normal_pos[1] = self.pos()
        super().moveEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())
