# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the buttons.py module.
"""

# ---- Standard imports
import os.path as osp

# ---- Third party imports
import pytest
from qtpy.QtGui import QWheelEvent
from qtpy.QtCore import Qt, QSize, QPoint
from qtpy.QtWidgets import QToolBar, QToolButton

# ---- Local imports
from sardes.config.gui import get_iconsize
from sardes.widgets.statusbar import ProcessStatusBar

ACTIONS = ['Action #{}'.format(i) for i in range(3)]


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def pstatusbar(qtbot):
    pstatusbar = ProcessStatusBar()
    qtbot.addWidget(pstatusbar)

    assert pstatusbar.status == pstatusbar.HIDDEN
    assert not pstatusbar._spinner._isSpinning
    assert not pstatusbar._spinner.isVisible()
    for icon in pstatusbar._icons.values():
        assert not icon.isVisible()
    assert pstatusbar._label.text() == ''

    return pstatusbar


# =============================================================================
# ---- Tests for the ProcessStatusBar
# =============================================================================
def test_pstatusbar_showhide(pstatusbar):
    """Test the process status bar show/hide interface."""

    # Show the progress status bar.
    pstatusbar.show(message='test in progess')
    assert pstatusbar.status == pstatusbar.IN_PROGRESS
    assert pstatusbar._spinner._isSpinning
    assert pstatusbar._spinner.isVisible()
    for icon in pstatusbar._icons.values():
        assert not icon.isVisible()
    assert pstatusbar._label.text() == 'test in progess'

    # Hide the progress status bar.
    pstatusbar.hide()
    assert not pstatusbar._spinner._isSpinning
    assert not pstatusbar._spinner.isVisible()
    for icon in pstatusbar._icons.values():
        assert not icon.isVisible()


def test_pstatusbar_fail_success_update(pstatusbar):
    """
    Test the process status bar interface to show icons is working
    as expected.
    """
    # Show the progress status bar.
    pstatusbar.show('test is spinning')
    assert pstatusbar._spinner._isSpinning
    assert pstatusbar._spinner.isVisible()
    assert pstatusbar._label.text() == 'test is spinning'
    for icon in pstatusbar._icons.values():
        assert not icon.isVisible()

    # Show the failed icon and message.
    pstatusbar.show_fail_icon('test fail icon')
    assert pstatusbar.status == pstatusbar.PROCESS_FAILED
    assert not pstatusbar._spinner._isSpinning
    assert not pstatusbar._spinner.isVisible()
    assert pstatusbar._failed_icon.isVisible()
    assert not pstatusbar._success_icon.isVisible()
    assert not pstatusbar._update_icon.isVisible()
    assert pstatusbar._label.text() == 'test fail icon'

    # Show the progress status bar again.
    pstatusbar.show('test is spinning')
    assert pstatusbar._spinner._isSpinning
    assert pstatusbar._spinner.isVisible()
    assert pstatusbar._label.text() == 'test is spinning'
    for icon in pstatusbar._icons.values():
        assert not icon.isVisible()

    # Show the success icon and message.
    pstatusbar.show_sucess_icon('test success icon')
    assert pstatusbar.status == pstatusbar.PROCESS_SUCCEEDED
    assert not pstatusbar._spinner._isSpinning
    assert not pstatusbar._spinner.isVisible()
    assert not pstatusbar._failed_icon.isVisible()
    assert pstatusbar._success_icon.isVisible()
    assert not pstatusbar._update_icon.isVisible()
    assert pstatusbar._label.text() == 'test success icon'

    # Show the progress status bar again.
    pstatusbar.show('test is spinning')
    assert pstatusbar._spinner._isSpinning
    assert pstatusbar._spinner.isVisible()
    assert pstatusbar._label.text() == 'test is spinning'
    for icon in pstatusbar._icons.values():
        assert not icon.isVisible()

    # Show the update icon and message.
    pstatusbar.show_update_icon('test update icon')
    assert pstatusbar.status == pstatusbar.NEED_UPDATE
    assert not pstatusbar._spinner._isSpinning
    assert not pstatusbar._spinner.isVisible()
    assert not pstatusbar._failed_icon.isVisible()
    assert not pstatusbar._success_icon.isVisible()
    assert pstatusbar._update_icon.isVisible()
    assert pstatusbar._label.text() == 'test update icon'


if __name__ == "__main__":
    pytest.main(['-x', osp.basename(__file__), '-v', '-rw'])
