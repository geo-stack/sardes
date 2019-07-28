# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# It is often said when developing interfaces that you need to fail fast,
# and iterate often. When creating a UI, you will make mistakes. Just keep
# moving forward, and remember to keep your UI out of the way.
# http://blog.teamtreehouse.com/10-user-interface-design-fundamentals

# ---- Standard imports
import os
import os.path as osp
import platform
import sys

# ---- Third party imports
from qtpy.QtCore import QPoint, QSize, Qt, QUrl
from qtpy.QtGui import QDesktopServices
from qtpy.QtWidgets import (QApplication, QActionGroup, QMainWindow, QMenu,
                            QMessageBox, QSizePolicy, QToolButton, QWidget)

# ---- Local imports
from sardes import __namever__, __project_url__, __rootdir__
from sardes.app.plugins import get_sardes_plugin_module_loaders
from sardes.config.main import CONF
from sardes.config.icons import get_icon
from sardes.config.gui import (get_iconsize, get_window_settings,
                               set_window_settings)
from sardes.config.locale import (_, get_available_translations, get_lang_conf,
                                  LANGUAGE_CODES, set_lang_conf)
from sardes.config.main import CONFIG_DIR
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.widgets.database_connection import DatabaseConnectionWidget
from sardes.utils.qthelpers import (
    create_action, create_toolbutton, qbytearray_to_hexstate,
    hexstate_to_qbytearray)

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

        self.setup()

    def setup(self):
        """Setup the main window"""
        self.create_topright_corner_toolbar()
        self.set_window_settings(*get_window_settings())
        self.setup_plugins()
        # Note: The window state must be restored after the setup of this
        #       mainwindow plugins and toolbars.
        self._restore_window_state()

    def setup_plugins(self):
        """Setup sardes internal and third party plugins."""
        installed_user_plugins = []
        blacklisted_internal_plugins = []

        # Setup internal plugin path.
        self.internal_plugins = []
        sardes_plugin_path = osp.join(__rootdir__, 'plugins')
        module_loaders = get_sardes_plugin_module_loaders(sardes_plugin_path)
        for module_name, module_loader in module_loaders.items():
            if (module_name not in blacklisted_internal_plugins and
                    module_name not in sys.modules):
                try:
                    module = module_loader.load_module()
                    sys.modules[module_name] = module
                    plugin = module.SARDES_PLUGIN_CLASS(self)
                    plugin.register_plugin()
                except Exception as error:
                    print("%s: %s" % (module, str(error)))
                else:
                    self.internal_plugins.append(plugin)

        # Setup user plugins.
        self.thirdparty_plugins = []
        user_plugin_path = osp.join(CONFIG_DIR, 'plugins')
        if not osp.isdir(user_plugin_path):
            os.makedirs(user_plugin_path)
        module_loaders = get_sardes_plugin_module_loaders(user_plugin_path)
        for module_name, module_loader in module_loaders.items():
            if (module_name in installed_user_plugins and
                    module_name not in sys.modules):
                try:
                    module = module_loader.load_module()
                    sys.modules[module_name] = module
                    plugin = module.SARDES_PLUGIN_CLASS(self)
                    plugin.register_plugin()
                except Exception as error:
                    print("%s: %s" % (module, str(error)))
                else:
                    self.thirdparty_plugins.append(plugin)

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

    def create_toolbar(self, title, object_name, iconsize=None):
        """Create and return a toolbar with title and object_name."""
        toolbar = self.addToolBar(title)
        toolbar.setObjectName(object_name)
        iconsize = get_iconsize() if iconsize is None else iconsize
        toolbar.setIconSize(QSize(iconsize, iconsize))
        self.toolbarslist.append(toolbar)
        return toolbar

    def toggle_lock_dockwidgets_and_toolbars(self, checked):
        for plugin in self.internal_plugins + self.thirdparty_plugins:
            plugin.lock_pane_and_toolbar(checked)

    # ---- Setup options button and menu
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

        # Create the languages menu.
        self.lang_menu = QMenu(_('Languages'), self)
        self.lang_menu.setIcon(get_icon('languages'))

        lang_conf = get_lang_conf()
        action_group = QActionGroup(self)
        for lang in get_available_translations():
            lang_action = create_action(
                action_group, LANGUAGE_CODES[lang], icon='lang_' + lang,
                toggled=lambda _, lang=lang: self.set_language(lang))
            self.lang_menu.addAction(lang_action)
            if lang == lang_conf:
                lang_action.setChecked(True)

        # Create the preference action to show the preference dialog window.
        preferences_action = create_action(
            self, _('Preferences...'), icon='preferences',
            shortcut='Ctrl+Shift+P', context=Qt.ApplicationShortcut
            )

        # Create the panes and toolbars menus and actions
        self.panes_menu = QMenu(_("Panes"), self)
        self.panes_menu.setIcon(get_icon('panes'))

        lock_dockwidgets_and_toolbars_action = create_action(
            self, _('Lock panes and toolbars'),
            shortcut='Ctrl+Shift+F5', context=Qt.ApplicationShortcut,
            toggled=(lambda checked:
                     self.toggle_lock_dockwidgets_and_toolbars(checked))
            )

        # Create help related actions and menus.
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
        for item in [self.lang_menu, preferences_action, None,
                     self.panes_menu, lock_dockwidgets_and_toolbars_action,
                     None, report_action, about_action, exit_action]:
            if item is None:
                options_menu.addSeparator()
            elif isinstance(item, QMenu):
                options_menu.addMenu(item)
            else:
                options_menu.addAction(item)

        return options_menu

    # ---- Database toolbar and widget setup.
    def setup_database_button_icon(self):
        """
        Set the icon of the database button to show whether a database is
        currently connected or not.
        """
        db_icon = ('database_connected' if
                   self.db_connection_manager.is_connected()
                   else 'database_disconnected')
        self.database_button.setIcon(get_icon(db_icon))

    # ---- Language and other locale settings.
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

    def _restore_window_state(self):
        """
        Restore the state of this mainwindow’s toolbars and dockwidgets from
        the value saved in the config.
        """
        hexstate = CONF.get('main', 'window/state', None)
        if hexstate:
            hexstate = hexstate_to_qbytearray(hexstate)
            self.restoreState(hexstate)

    def _save_window_state(self):
        """
        Save the state of this mainwindow’s toolbars and dockwidgets to
        the config.
        """
        hexstate = qbytearray_to_hexstate(self.saveState())
        CONF.set('main', 'window/state', hexstate)

    # ---- Main window events
    def closeEvent(self, event):
        """Reimplement Qt closeEvent."""
        set_window_settings(*self.get_window_settings())
        self._save_window_state()

        # Close all internal and thirdparty plugins.
        for plugin in self.internal_plugins + self.thirdparty_plugins:
            plugin.close_plugin()

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


def except_hook(cls, exception, traceback):
    """
    Used to override the default sys except hook so that this application
    doesn't automatically exit when an unhandled exception occurs.

    See this StackOverflow answer for more details :
    https://stackoverflow.com/a/33741755/4481445
    """

    sys.__excepthook__(cls, exception, traceback)


if __name__ == '__main__':
    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())
