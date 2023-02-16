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
import os.path as osp
from unittest.mock import Mock
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest

# ---- Local imports
from sardes.database.accessors import DatabaseAccessorSardesLite
from sardes.database.accessors.tests.conftest import *
from sardes.plugins.tables import SARDES_PLUGIN_CLASS as TABLE_PLUGIN_CLASS
from sardes.plugins.librairies import SARDES_PLUGIN_CLASS as LIB_PLUGIN_CLASS
from sardes.plugins.readings import SARDES_PLUGIN_CLASS as READ_PLUGIN_CLASS
from sardes.app.mainwindow import MainWindowBase


@pytest.fixture
def dbaccessor(tmp_path, database_filler):
    dbaccessor = DatabaseAccessorSardesLite(
        osp.join(tmp_path, 'sqlite_database_test.db'))
    dbaccessor.init_database()
    database_filler(dbaccessor)

    return dbaccessor


@pytest.fixture
def mainwindow(qtbot, dbaccessor):
    class MainWindowMock(MainWindowBase):
        def __init__(self):
            self.view_timeseries_data = Mock()
            super().__init__()

        def setup_internal_plugins(self):
            self.tables_plugin = TABLE_PLUGIN_CLASS(self)
            self.tables_plugin.register_plugin()
            self.internal_plugins.append(self.tables_plugin)

            self.librairies_plugin = LIB_PLUGIN_CLASS(self)
            self.librairies_plugin.register_plugin()
            self.internal_plugins.append(self.librairies_plugin)

            self.readings_plugin = READ_PLUGIN_CLASS(self)
            self.readings_plugin.register_plugin()
            self.internal_plugins.append(self.readings_plugin)

            # Tabify dockwidget.
            self.tabifyDockWidget(
                self.tables_plugin.dockwidget(),
                self.readings_plugin.dockwidget())
            self.tabifyDockWidget(
                self.readings_plugin.dockwidget(),
                self.librairies_plugin.dockwidget())

    mainwindow = MainWindowMock()
    mainwindow.show()
    qtbot.waitExposed(mainwindow)

    dbconnmanager = mainwindow.db_connection_manager
    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(dbaccessor)
    assert dbconnmanager.is_connected()

    # We set the option to 'confirm before saving' to False to avoid
    # showing the associated message when saving table edits.
    dbconnmanager.set_confirm_before_saving_edits(False)

    yield mainwindow

    # We need to wait for the mainwindow to close properly to avoid
    # runtime errors on the c++ side.
    with qtbot.waitSignal(mainwindow.sig_about_to_close):
        mainwindow.close()


@pytest.fixture
def dbconnmanager(mainwindow):
    yield mainwindow.db_connection_manager
    # We use 'yield' instead of 'return' here sinde the 'db_connection_manager'
    # will be destroyed in the 'mainwindow' fixture.
