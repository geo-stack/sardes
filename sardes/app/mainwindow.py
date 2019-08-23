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

print('Starting SARDES...')
# ---- Setup the main Qt application.
import sys
from qtpy.QtWidgets import QApplication
app = QApplication(sys.argv)

# ---- Setup the splash screen.
from sardes.widgets.splash import SplashScreen
from sardes.config.locale import _
splash = SplashScreen()


# ---- Standard imports
splash.showMessage(_("Importing standard Python modules..."))
import os
import os.path as osp
import platform
import sys
import importlib

# ---- Third party imports
splash.showMessage(_("Importing third party Python modules..."))
from qtpy.QtCore import Qt, QUrl, Slot
from qtpy.QtGui import QDesktopServices
from qtpy.QtWidgets import (QApplication, QActionGroup, QMainWindow, QMenu,
                            QMessageBox, QSizePolicy, QToolButton, QWidget)

# ---- Local imports
splash.showMessage(_("Importing local Python modules..."))
from sardes import __namever__, __project_url__
from sardes.config.main import CONF
from sardes.config.icons import get_icon
from sardes.config.locale import (get_available_translations, get_lang_conf,
                                  LANGUAGE_CODES, set_lang_conf)
from sardes.config.main import CONFIG_DIR
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.utils.qthelpers import (
    create_action, create_mainwindow_toolbar, create_toolbutton,
    qbytearray_to_hexstate, hexstate_to_qbytearray)

from multiprocessing import freeze_support
freeze_support()

GITHUB_ISSUES_URL = __project_url__ + "/issues"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(get_icon('master'))
        self.setWindowTitle(__namever__)
        if platform.system() == 'Windows':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                __namever__)

        # Toolbars and plugins
        self.visible_toolbars = []
        self.toolbars = []
        self.thirdparty_plugins = []
        self.internal_plugins = []

        # Setup the database connection manager.
        splash.showMessage(_("Setting up the database connection manager..."))
        self.db_connection_manager = DatabaseConnectionManager()

        self.setup()

    def setup(self):
        """Setup the main window"""
        self._setup_options_menu_toolbar()
        self._restore_window_geometry()
        self.setup_internal_plugins()
        self.setup_thirdparty_plugins()
        # Note: The window state must be restored after the setup of this
        #       mainwindow plugins and toolbars.
        self._restore_window_state()

    def setup_internal_plugins(self):
        """Setup Sardes internal plugins."""
        # NOTE: We must import each internal plugin explicitely here or else
        # we would have to add each of them as hidden import to the pyinstaller
        # spec file for them to be packaged as part of the Sardes binary.

        # Observation Wells plugin.
        from sardes.plugins.obs_wells_explorer import SARDES_PLUGIN_CLASS
        splash.showMessage(_("Loading the {} plugin...")
                           .format(SARDES_PLUGIN_CLASS.get_plugin_title()))
        plugin = SARDES_PLUGIN_CLASS(self)
        plugin.register_plugin()
        self.internal_plugins.append(plugin)

        # Database plugin.
        from sardes.plugins.databases import SARDES_PLUGIN_CLASS
        splash.showMessage(_("Loading the {} plugin...")
                           .format(SARDES_PLUGIN_CLASS.get_plugin_title()))
        self.databases_plugin = SARDES_PLUGIN_CLASS(self)
        self.databases_plugin.register_plugin()
        self.internal_plugins.append(self.databases_plugin)

    def setup_thirdparty_plugins(self):
        """Setup Sardes third party plugins."""
        installed_thirdparty_plugins = []

        user_plugin_path = osp.join(CONFIG_DIR, 'plugins')
        if not osp.isdir(user_plugin_path):
            os.makedirs(user_plugin_path)

        for module_name in installed_thirdparty_plugins:
            if module_name not in sys.modules:
                try:
                    module_spec = importlib.machinery.PathFinder.find_spec(
                        module_name, [user_plugin_path])
                    if module_spec:
                        module = module_spec.loader.load_module()
                        sys.modules[module_name] = module
                        splash.showMessage(
                            _("Loading the {} plugin...").format(
                                module.SARDES_PLUGIN_CLASS.get_plugin_title()))
                        plugin = module.SARDES_PLUGIN_CLASS(self)
                        plugin.register_plugin()
                        self.thirdparty_plugins.append(plugin)
                except Exception as error:
                    print("{}: {}".format(module_name, str(error)))
            else:
                raise Warning(
                    "{}: This module is already loaded.".format(module_name))

    # ---- Toolbar setup
    @Slot(bool)
    def toggle_lock_dockwidgets_and_toolbars(self, checked):
        """
        Lock or unlock this mainwindow dockwidgets and toolbars.
        """
        for plugin in self.internal_plugins + self.thirdparty_plugins:
            plugin.lock_pane_and_toolbar(checked)
        for toolbar in self.toolbars:
            toolbar.setMovable(not checked)

    # ---- Setup options button and menu
    def _setup_options_menu_toolbar(self):
        """
        Setup a the options menu toolbutton (hamburger menu) and add it
        to a toolbar.
        """
        self.options_menu_toolbar = create_mainwindow_toolbar(
            "Options toolbar")

        # Add a stretcher item.
        stretcher = QWidget()
        stretcher.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.options_menu_toolbar.addWidget(stretcher)

        # Add the tools and options button.
        self.options_menu_button = self._create_options_menu_button()
        self.options_menu_toolbar.addWidget(self.options_menu_button)

        self.toolbars.append(self.options_menu_toolbar)
        self.addToolBar(self.options_menu_toolbar)

    def _create_options_menu_button(self):
        """Create and return the options button of this application."""
        options_menu_button = create_toolbutton(
            self, icon='tooloptions',
            text=_("Tools and options"),
            tip=_("Open the tools and options menu."),
            shortcut='Ctrl+Shift+T')
        options_menu_button.setStyleSheet(
            "QToolButton::menu-indicator{image: none;}")
        options_menu_button.setPopupMode(QToolButton.InstantPopup)

        # Create the tools and options menu.
        options_menu_button.setMenu(self._create_options_menu())

        return options_menu_button

    def _create_options_menu(self):
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

        self.toolbars_menu = QMenu(_("Toolbars"), self)
        self.toolbars_menu.setIcon(get_icon('toolbars'))

        self.lock_dockwidgets_and_toolbars_action = create_action(
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

        # Add the actions and menus to the options menu.
        options_menu_items = [
            self.lang_menu, preferences_action, None, self.panes_menu,
            self.toolbars_menu, self.lock_dockwidgets_and_toolbars_action,
            None, report_action, about_action, exit_action
            ]
        for item in options_menu_items:
            if item is None:
                options_menu.addSeparator()
            elif isinstance(item, QMenu):
                options_menu.addMenu(item)
            else:
                options_menu.addAction(item)

        return options_menu

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
    def _restore_window_geometry(self):
        """
        Restore the geometry of this mainwindow from the value saved
        in the config.
        """
        hexstate = CONF.get('main', 'window/geometry', None)
        if hexstate:
            hexstate = hexstate_to_qbytearray(hexstate)
            self.restoreGeometry(hexstate)
        else:
            from sardes.config.gui import INIT_MAINWINDOW_SIZE
            self.resize(*INIT_MAINWINDOW_SIZE)

    def _save_window_geometry(self):
        """
        Save the geometry of this mainwindow to the config.
        """
        hexstate = qbytearray_to_hexstate(self.saveGeometry())
        CONF.set('main', 'window/geometry', hexstate)

    def _restore_window_state(self):
        """
        Restore the state of this mainwindow’s toolbars and dockwidgets from
        the value saved in the config.
        """
        hexstate = CONF.get('main', 'window/state', None)
        if hexstate:
            hexstate = hexstate_to_qbytearray(hexstate)
            self.restoreState(hexstate)
        self.lock_dockwidgets_and_toolbars_action.setChecked(
            CONF.get('main', 'panes_and_toolbars_locked'))

    def _save_window_state(self):
        """
        Save the state of this mainwindow’s toolbars and dockwidgets to
        the config.
        """
        hexstate = qbytearray_to_hexstate(self.saveState())
        CONF.set('main', 'window/state', hexstate)
        CONF.set('main', 'panes_and_toolbars_locked',
                 self.lock_dockwidgets_and_toolbars_action.isChecked())

    # ---- Qt method override/extension
    def show(self):
        """Extend Qt show to connect to database automatically."""
        super().show()

        # Connect to database if options is True.
        # NOTE: This must be done after all internal and thirdparty plugins
        # have been registered in case they are connected to the database
        # manager connection signals.
        if self.databases_plugin.get_option('auto_connect_to_database'):
            self.db_connection_manager.connect_to_db(
                self.databases_plugin.connect_to_database())

    def closeEvent(self, event):
        """Reimplement Qt closeEvent."""
        self._save_window_geometry()
        self._save_window_state()

        # Close all internal and thirdparty plugins.
        for plugin in self.internal_plugins + self.thirdparty_plugins:
            plugin.close_plugin()

        event.accept()

    def createPopupMenu(self):
        """
        Override Qt method to remove the options menu toolbar from the
        popup menu so that it remains always visible.
        """
        filteredMenu = super().createPopupMenu()
        filteredMenu.removeAction(self.options_menu_toolbar.toggleViewAction())
        return filteredMenu


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
    main = MainWindow()
    splash.finish(main)
    main.show()
    sys.exit(app.exec_())
