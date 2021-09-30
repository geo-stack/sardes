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
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest

# ---- Local imports
from sardes.database.database_manager import DatabaseConnectionManager
from sardes.tables.managers import SardesTableModelsManager
from sardes.database.accessors import DatabaseAccessorSardesLite
from sardes.database.accessors.tests.conftest import *


@pytest.fixture
def dbaccessor(tmp_path, database_filler):
    dbaccessor = DatabaseAccessorSardesLite(
        osp.join(tmp_path, 'sqlite_database_test.db'))
    dbaccessor.init_database()
    database_filler(dbaccessor)

    return dbaccessor


@pytest.fixture
def dbconnmanager(dbaccessor, qtbot):
    dbconnmanager = DatabaseConnectionManager()
    with qtbot.waitSignal(dbconnmanager.sig_database_connected, timeout=3000):
        dbconnmanager.connect_to_db(dbaccessor)
    assert dbconnmanager.is_connected()

    # We set the option to 'confirm before saving' to False to avoid
    # showing the associated message when saving table edits.
    dbconnmanager.set_confirm_before_saving_edits(False)

    return dbconnmanager


@pytest.fixture
def tablesmanager(dbconnmanager):
    tablesmanager = SardesTableModelsManager(dbconnmanager)
    return tablesmanager
