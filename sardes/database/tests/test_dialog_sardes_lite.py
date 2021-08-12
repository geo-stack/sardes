# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the DatabaseConnectDialogSardesLite.
"""

# ---- Standard imports
import os.path as osp
from unittest.mock import Mock

# ---- Third party imports
from sqlalchemy.exc import OperationalError
import pytest
from qtpy.QtCore import Qt

# ---- Local imports
from sardes.database.dialogs.dialog_sardes_lite import (
    DatabaseConnectDialogSardesLite, QMessageBox, QFileDialog)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def dbconndialog(qtbot, mocker):
    dbconndialog = DatabaseConnectDialogSardesLite()
    qtbot.addWidget(dbconndialog)
    dbconndialog.show()
    return dbconndialog


# =============================================================================
# ---- Tests for DatabaseConnectionWidget
# =============================================================================
def test_browse_database(dbconndialog, tmp_path, mocker, qtbot):
    """
    Test that browsing and selecting and existing Sardes SQLite database
    is working as expected.
    """
    selectedfilename = osp.join(tmp_path, 'test_browse_sardes_sqlite.db')
    with open(selectedfilename, 'w') as f:
        f.write('test_browse_sardes_sqlite')
    selectedfilter = dbconndialog.FILEFILTER
    mocker.patch.object(QFileDialog, 'getOpenFileName',
                        return_value=(selectedfilename, selectedfilter))

    qtbot.mouseClick(dbconndialog.browse_btn, Qt.LeftButton)
    assert osp.samefile(dbconndialog.dbname_widget.path(), selectedfilename)


def test_create_database(dbconndialog, tmp_path, mocker, qtbot):
    """
    Test that creating a new Sardes SQLite database is working as expected.
    """
    selectedfilename = osp.join(tmp_path, 'test_create_sardes_sqlite.db')
    selectedfilter = dbconndialog.FILEFILTER
    mocker.patch.object(QFileDialog, 'getSaveFileName',
                        return_value=(selectedfilename, selectedfilter))

    qtbot.mouseClick(dbconndialog.create_btn, Qt.LeftButton)
    qtbot.waitUntil(lambda: osp.exists(selectedfilename))
    assert osp.samefile(dbconndialog.dbname_widget.path(), selectedfilename)


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
