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

# Enforce using dots as decimal separators for the whole application.
from qtpy.QtCore import QLocale
QLocale.setDefault(QLocale(QLocale.C))

# ---- Standard imports
import os
import os.path as osp
import platform
import sys
import traceback
import importlib

# ---- Third party imports
from qtpy.QtCore import Qt, QUrl, Slot, QEvent, Signal, QObject
from qtpy.QtGui import QDesktopServices
from qtpy.QtWidgets import (QApplication, QActionGroup, QMainWindow, QMenu,
                            QMessageBox, QToolButton)

# ---- Local imports
# Note: when possible, move imports of widgets and plugins exactly where they
# are needed in MainWindow to speed up perceived startup time.

from sardes import __namever__, __project_url__, __appname__
from sardes.config.main import CONF, TEMP_DIR
from sardes.config.icons import get_icon
from sardes.config.locale import (
    _, get_available_translations, get_lang_conf,
    LANGUAGE_CODES, set_lang_conf)
from sardes.config.main import CONFIG_DIR
from sardes.widgets.tableviews import RowCountLabel
from sardes.utils.qthelpers import (
    create_action, create_mainwindow_toolbar, create_toolbar_stretcher,
    create_toolbutton, qbytearray_to_hexstate, hexstate_to_qbytearray)
from sardes.utils.fileio import delete_folder_recursively

from multiprocessing import freeze_support
freeze_support()

GITHUB_ISSUES_URL = __project_url__ + "/issues"


class MainWindowBase(QMainWindow):
    sig_about_to_close = Signal()

    def __init__(self, splash=None, sys_capture_manager=None):
        super().__init__()
        self.splash = splash
        self.sys_capture_manager = sys_capture_manager
        self.console = None
        if self.sys_capture_manager is not None:
            # Setup the internal Sardes console.
            from sardes.widgets.console import SardesConsole
            self.console = SardesConsole()
            self.sys_capture_manager.register_stdstream_console(self.console)

        self.setWindowIcon(get_icon('master'))
        self.setWindowTitle(__namever__)
        self.setCentralWidget(None)
        self.setDockNestingEnabled(True)
        if platform.system() == 'Windows':
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                __namever__)

        self._is_closing = None

        # Toolbars and plugins
        self.visible_toolbars = []
        self.toolbars = []
        self.thirdparty_plugins = []
        self.internal_plugins = []
        self._is_panes_and_toolbars_locked = False

        # Setup the database connection manager.
        print("Setting up the database connection manager...")
        from sardes.database.database_manager import DatabaseConnectionManager
        self.set_splash(_("Setting up the database connection manager..."))
        self.db_connection_manager = DatabaseConnectionManager()
        print("Database connection manager set up succesfully.")

        # Setup the table models manager.
        print("Setting up the table models manager...")
        from sardes.tables.managers import SardesTableModelsManager
        self.table_models_manager = SardesTableModelsManager(
            self.db_connection_manager)
        print("Table models manager set up succesfully.")

        self.setup()

    def set_splash(self, message):
        """Set splash message."""
        if self.splash is not None:
            self.splash.showMessage(message)

    # ---- Public API
    def setup_default_layout(self):
        """Setup the default layout for Sardes mainwindow."""
        pass

    def setup_internal_plugins(self):
        """Setup Sardes internal plugins."""
        pass

    # ---- Setup
    def setup(self):
        """Setup the main window"""
        self.installEventFilter(self)
        self.setup_preferences()
        self.setup_options_button()
        self.setup_statusbar()
        self._restore_window_geometry()
        self.setup_internal_plugins()
        self.setup_thirdparty_plugins()

        # Note: The window state must be restored after the setup of the
        # plugins and toolbars.
        self._restore_window_state()

    def setup_preferences(self):
        """Setup Sardes config dialog."""
        from sardes.preferences import ConfDialog, DocumentsSettingsConfPage
        self.confdialog = ConfDialog(self)
        self.confdialog.add_confpage(DocumentsSettingsConfPage())

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
                        self.set_splash(
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

    # ---- Tables
    def register_table(self, table):
        """
        Register a SardesTableView to the mainwindow.
        """
        self.tables_row_count.register_table(table)

    def unregister_table(self, table):
        """
        Un-register a SardesTableView from the mainwindow.
        """
        self.tables_row_count.unregister_table(table)

    # ---- Statusbar
    def setup_statusbar(self):
        """
        Setup the status bar of the mainwindow.
        """
        statusbar = self.statusBar()
        statusbar.setSizeGripEnabled(False)

        # Number of row(s) selected.
        self.tables_row_count = RowCountLabel()
        statusbar.addPermanentWidget(self.tables_row_count)

    # ---- Toolbar setup
    @Slot(bool)
    def toggle_lock_dockwidgets_and_toolbars(self, locked):
        """
        Lock or unlock this mainwindow dockwidgets and toolbars.
        """
        self._is_panes_and_toolbars_locked = locked
        self.lock_dockwidgets_and_toolbars_action.setIcon(
            get_icon('pane_lock' if locked else 'pane_unlock'))
        self.lock_dockwidgets_and_toolbars_action.setText(
            _('Unlock panes and toolbars') if locked else
            _('Lock panes and toolbars'))
        for plugin in self.internal_plugins + self.thirdparty_plugins:
            plugin.lock_pane_and_toolbar(locked)
        for toolbar in self.toolbars:
            toolbar.setMovable(not locked)

    # ---- Setup options button and menu
    def setup_options_button(self):
        """
        Setup a the options menu toolbutton (hamburger menu) and add it
        to a toolbar.
        """
        self.options_menu_toolbar = create_mainwindow_toolbar(
            "Options toolbar")

        # Add a stretcher to the toolbar.
        self.options_menu_toolbar.addWidget(create_toolbar_stretcher())

        # Add the tools and options button.
        self.options_menu_button = create_toolbutton(
            self, icon='tooloptions',
            text=_("Tools and options"),
            tip=_("Open the tools and options menu."),
            shortcut='Ctrl+Shift+T')
        self.options_menu_button.setStyleSheet(
            "QToolButton::menu-indicator{image: none;}")
        self.options_menu_button.setPopupMode(QToolButton.InstantPopup)
        self.options_menu_button.setMenu(self.setup_options_menu())
        self.options_menu_toolbar.addWidget(self.options_menu_button)

        self.toolbars.append(self.options_menu_toolbar)
        self.addToolBar(self.options_menu_toolbar)

    def setup_options_menu(self):
        """Create and return the options menu of this application."""
        class Separator(object):
            # Used for adding a separator to the menu.
            pass

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
            shortcut='Ctrl+Shift+P', context=Qt.ApplicationShortcut,
            triggered=self.confdialog.show
            )

        # Create the panes and toolbars menus and actions
        self.panes_menu = QMenu(_("Panes"), self)
        self.panes_menu.setIcon(get_icon('panes'))

        self.toolbars_menu = QMenu(_("Toolbars"), self)
        self.toolbars_menu.setIcon(get_icon('toolbars'))

        self.lock_dockwidgets_and_toolbars_action = create_action(
            self, _('Lock panes and toolbars'),
            shortcut='Ctrl+Shift+F5', context=Qt.ApplicationShortcut,
            triggered=(
                lambda checked: self.toggle_lock_dockwidgets_and_toolbars(
                    not self._is_panes_and_toolbars_locked))
            )

        self.reset_window_layout_action = create_action(
            self, _('Reset window layout'), icon='reset_layout',
            triggered=self.reset_window_layout)

        # Create help related actions and menus.
        self.console_action = None
        if self.console is not None:
            self.console_action = create_action(
                self, _('Sardes Console...'), icon='console',
                shortcut='Ctrl+Shift+J', context=Qt.ApplicationShortcut,
                triggered=self.console.show
                )
        report_action = create_action(
            self, _('Report an issue...'), icon='bug',
            shortcut='Ctrl+Shift+R', context=Qt.ApplicationShortcut,
            triggered=lambda: QDesktopServices.openUrl(QUrl(GITHUB_ISSUES_URL))
            )
        about_action = create_action(
            self, _('About Sardes...'), icon='information',
            shortcut='Ctrl+Shift+I',
            context=Qt.ApplicationShortcut
            )
        exit_action = create_action(
            self, _('Exit'), icon='exit', triggered=self.close,
            shortcut='Ctrl+Shift+Q', context=Qt.ApplicationShortcut
            )

        # Add the actions and menus to the options menu.
        options_menu_items = [
            self.lang_menu, preferences_action, Separator(),
            self.panes_menu, self.toolbars_menu,
            self.lock_dockwidgets_and_toolbars_action,
            self.reset_window_layout_action, Separator(),
            self.console_action, report_action, about_action, exit_action
            ]
        for item in options_menu_items:
            if isinstance(item, Separator):
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
    @Slot()
    def reset_window_layout(self):
        """
        Reset window layout to default
        """
        answer = QMessageBox.warning(
            self, _("Reset Window Layout"),
            _("Window layout will be reset to default settings.<br><br>"
              "Do you want to continue?"),
            QMessageBox.Yes | QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.setup_default_layout()

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
        # We setup the default layout configuration first.
        self.setup_default_layout()

        # Then we appply saved configuration if it exists.
        hexstate = CONF.get('main', 'window/state', None)
        if hexstate:
            hexstate = hexstate_to_qbytearray(hexstate)
            self.restoreState(hexstate)
        self.toggle_lock_dockwidgets_and_toolbars(
            CONF.get('main', 'panes_and_toolbars_locked'))

    def _save_window_state(self):
        """
        Save the state of this mainwindow’s toolbars and dockwidgets to
        the config.
        """
        hexstate = qbytearray_to_hexstate(self.saveState())
        CONF.set('main', 'window/state', hexstate)
        CONF.set('main', 'panes_and_toolbars_locked',
                 self._is_panes_and_toolbars_locked)

    # ---- Qt method override/extension
    def eventFilter(self, widget, event):
        """
        An event filter to prevent status tips from buttons and menus
        to show in the status bar.
        """
        if event.type() == QEvent.StatusTip:
            return True
        return False

    def show(self):
        """
        Extend Qt method to call show_plugin on each installed plugin.
        """
        super().show()
        for plugin in self.internal_plugins + self.thirdparty_plugins:
            plugin.show_plugin()

    def closeEvent(self, event):
        """Reimplement Qt closeEvent."""
        if self._is_closing is None:
            print('Closing {}...'.format(__appname__))
            QApplication.setOverrideCursor(Qt.WaitCursor)
            self._is_closing = True

            self._save_window_geometry()
            self._save_window_state()

            # Close Sardes console.
            if self.console is not None:
                self.console.close()

            # Close all internal and thirdparty plugins.
            for plugin in self.internal_plugins + self.thirdparty_plugins:
                plugin.close_plugin()

            # Clean temp files.
            print('Cleaning temp files...')
            delete_folder_recursively(TEMP_DIR)
            print('Sucessfully cleaned temp files.')

            # Close the database connection manager.
            self.db_connection_manager.close(
                callback=self._handle_project_manager_closed)
            event.ignore()
        elif self._is_closing is True:
            event.ignore()
        elif self._is_closing is False:
            self.sig_about_to_close.emit()
            event.accept()

    def createPopupMenu(self):
        """
        Override Qt method to remove the options menu toolbar from the
        popup menu so that it remains always visible.
        """
        filteredMenu = super().createPopupMenu()
        filteredMenu.removeAction(self.options_menu_toolbar.toggleViewAction())
        return filteredMenu

    # ---- Handlers
    def _handle_project_manager_closed(self, *args, **kargs):
        """
        Close Sardes after the database manager has been safely closed.
        """
        self._is_closing = False
        self.close()


class MainWindow(MainWindowBase):

    # ---- Plugin interactions
    def view_timeseries_data(self, sampling_feature_uuid):
        """
        Create and show a table to visualize the timeseries data related
        to the given sampling feature uuid.
        """
        self.readings_plugin.view_timeseries_data(sampling_feature_uuid)

    def setup_default_layout(self):
        """
        Setup the default layout for Sardes mainwindow.
        """
        self.setUpdatesEnabled(False)

        # Make sure all plugins are docked and visible.
        self.tables_plugin.dockwindow.dock()
        self.librairies_plugin.dockwindow.dock()
        self.hydrogeochemistry_plugin.dockwindow.dock()
        self.data_import_plugin.dockwindow.dock()
        self.readings_plugin.dockwindow.dock()

        # Split dockwidgets.
        # Note that we use both directions to ensure proper update in case
        # the tables plugin is already in a tabbed docked area. In that case,
        # doing only the horizontal orientation simply adds the other plugin
        # to the tabbed docked area instead of next to it.
        for orientation in [Qt.Vertical, Qt.Horizontal]:
            self.splitDockWidget(
                self.tables_plugin.dockwidget(),
                self.data_import_plugin.dockwidget(),
                orientation)

        # Tabify dockwidget.
        self.tabifyDockWidget(
            self.tables_plugin.dockwidget(),
            self.readings_plugin.dockwidget()
            )
        self.tabifyDockWidget(
            self.readings_plugin.dockwidget(),
            self.librairies_plugin.dockwidget()
            )
        self.tabifyDockWidget(
            self.librairies_plugin.dockwidget(),
            self.hydrogeochemistry_plugin.dockwidget()
            )

        # Resize dockwidgets.
        wf2 = int(500 / self.width() * 100)
        wf1 = 100 - wf2
        dockwidgets = [self.tables_plugin.dockwidget(),
                       self.data_import_plugin.dockwidget()]
        width_fractions = [wf1, wf2]
        self.resizeDocks(dockwidgets, width_fractions, Qt.Horizontal)

        self.tables_plugin.switch_to_plugin()
        self.setUpdatesEnabled(True)

    def setup_internal_plugins(self):
        """Setup Sardes internal plugins."""
        # NOTE: We must import each internal plugin explicitely here or else
        # we would have to add each of them as hidden import to the pyinstaller
        # spec file for them to be packaged as part of the Sardes binary.

        # Tables plugin.
        from sardes.plugins.tables import SARDES_PLUGIN_CLASS
        plugin_title = SARDES_PLUGIN_CLASS.get_plugin_title()
        print("Loading plugin '{}'...".format(plugin_title))
        self.set_splash(_("Loading the {} plugin...").format(plugin_title))
        self.tables_plugin = SARDES_PLUGIN_CLASS(self)
        self.tables_plugin.register_plugin()
        self.internal_plugins.append(self.tables_plugin)
        print("Plugin '{}' loaded successfully".format(plugin_title))

        # Librairies plugin.
        from sardes.plugins.librairies import SARDES_PLUGIN_CLASS
        plugin_title = SARDES_PLUGIN_CLASS.get_plugin_title()
        print("Loading plugin '{}'...".format(plugin_title))
        self.set_splash(_("Loading the {} plugin...").format(plugin_title))
        self.librairies_plugin = SARDES_PLUGIN_CLASS(self)
        self.librairies_plugin.register_plugin()
        self.internal_plugins.append(self.librairies_plugin)
        print("Plugin '{}' loaded successfully".format(plugin_title))

        # Hydrogeochemistry plugin.
        from sardes.plugins.hydrogeochemistry import SARDES_PLUGIN_CLASS
        plugin_title = SARDES_PLUGIN_CLASS.get_plugin_title()
        print("Loading plugin '{}'...".format(plugin_title))
        self.set_splash(_("Loading the {} plugin...").format(plugin_title))
        self.hydrogeochemistry_plugin = SARDES_PLUGIN_CLASS(self)
        self.hydrogeochemistry_plugin.register_plugin()
        self.internal_plugins.append(self.hydrogeochemistry_plugin)
        print("Plugin '{}' loaded successfully".format(plugin_title))

        # Database plugin.
        from sardes.plugins.databases import SARDES_PLUGIN_CLASS
        plugin_title = SARDES_PLUGIN_CLASS.get_plugin_title()
        print("Loading plugin '{}'...".format(plugin_title))
        self.set_splash(_("Loading the {} plugin...").format(plugin_title))
        self.databases_plugin = SARDES_PLUGIN_CLASS(self)
        self.databases_plugin.register_plugin()
        self.internal_plugins.append(self.databases_plugin)
        print("Plugin '{}' loaded successfully".format(plugin_title))

        # Import Data Wizard.
        from sardes.plugins.dataio import SARDES_PLUGIN_CLASS
        plugin_title = SARDES_PLUGIN_CLASS.get_plugin_title()
        print("Loading plugin '{}'...".format(plugin_title))
        self.set_splash(_("Loading the {} plugin...").format(plugin_title))
        self.data_import_plugin = SARDES_PLUGIN_CLASS(self)
        self.data_import_plugin.register_plugin()
        self.internal_plugins.append(self.data_import_plugin)
        print("Plugin '{}' loaded successfully".format(plugin_title))

        # Time Data plugin.
        from sardes.plugins.readings import SARDES_PLUGIN_CLASS
        plugin_title = SARDES_PLUGIN_CLASS.get_plugin_title()
        print("Loading plugin '{}'...".format(plugin_title))
        self.set_splash(_("Loading the {} plugin...").format(plugin_title))
        self.readings_plugin = SARDES_PLUGIN_CLASS(self)
        self.readings_plugin.register_plugin()
        self.internal_plugins.append(self.readings_plugin)
        print("Plugin '{}' loaded successfully".format(plugin_title))

        # Piezometric Network plugin.
        from sardes.plugins.network import SARDES_PLUGIN_CLASS
        plugin_title = SARDES_PLUGIN_CLASS.get_plugin_title()
        print("Loading plugin '{}'...".format(plugin_title))
        self.set_splash(_("Loading the {} plugin...").format(plugin_title))
        self.network_plugin = SARDES_PLUGIN_CLASS(self)
        self.network_plugin.register_plugin()
        self.internal_plugins.append(self.network_plugin)
        print("Plugin '{}' loaded successfully".format(plugin_title))

    def show(self):
        """
        Extend Qt method to call show_plugin on each installed plugin.
        """
        super().show()

        # Connect to database if options is True.
        # NOTE: This must be done after all internal and thirdparty plugins
        # have been registered in case they are connected to the database
        # manager connection signals.
        if self.databases_plugin.get_option('auto_connect_to_database'):
            self.databases_plugin.connect_to_database()


class ExceptHook(QObject):
    """
    A Qt object to caught exceptions and emit a formatted string of the error.
    """
    sig_except_caught = Signal(str)

    def __init__(self):
        super().__init__()
        sys.excepthook = self.excepthook

    def excepthook(self, exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions."""
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        if not issubclass(exc_type, SystemExit):
            log_msg = ''.join(traceback.format_exception(
                exc_type, exc_value, exc_traceback))
            self.sig_except_caught.emit(log_msg)


if __name__ == '__main__':
    from sardes.utils.qthelpers import create_application
    app = create_application()

    from sardes.app.capture import SysCaptureManager
    sys_capture_manager = SysCaptureManager(start_capture=True)

    from sardes.widgets.splash import SplashScreen
    splash = SplashScreen(_("Initializing {}...").format(__namever__))

    print("Initializing MainWindow...")
    main = MainWindow(splash, sys_capture_manager)
    splash.finish(main)
    main.show()
    print("Successfully initialized MainWindow.")

    sys.exit(app.exec_())
