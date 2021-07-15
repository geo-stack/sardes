# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the system capture manager.
"""

# ---- Standard imports
import os
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest

# ---- Local imports
from sardes.widgets.dialogs import ExceptDialog
from sardes.app.capture import SysCaptureManager


# =============================================================================
# ---- Tests for SysCaptureManager
# =============================================================================
def test_handle_except(qtbot, mocker):
    """
    Test that internal errors are shown as expected in a dialog.
    """
    sys_capture_manager = SysCaptureManager()

    exceptdialog_exec_patcher = mocker.patch.object(ExceptDialog, 'exec_')
    assert exceptdialog_exec_patcher.call_count == 0
    sys_capture_manager.except_hook.sig_except_caught.emit(
        'some_formatted_except_traceback')
    assert exceptdialog_exec_patcher.call_count == 1


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
