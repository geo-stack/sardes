# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the SardesConsole.
"""
# ---- Standard imports
import os
import os.path as osp
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QFileDialog


# ---- Local imports
from sardes.widgets.console import SardesConsole


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def sardes_console(qtbot):
    sardes_console = SardesConsole()
    qtbot.addWidget(sardes_console)
    sardes_console.show()
    qtbot.waitExposed(sardes_console)
    return sardes_console


# =============================================================================
# ---- Tests
# =============================================================================
def test_sardes_console_write(sardes_console):
    """
    Test that writing to the sardes console works as expected.
    """
    assert sardes_console.plain_text() == ''
    strings = ["First line\n", "Second line\n", "Third line\n"]
    for string in strings:
        sardes_console.write(string)

    expected_text = ''.join(strings)
    assert sardes_console.plain_text() == expected_text


def test_sardes_console_save_and_copy(sardes_console, qtbot, mocker, tmp_path):
    """
    Test that saving the content of the sardes console in a file or copying
    it to the clipboard works as expected.
    """
    string = "First line\nSecond line\nThird line\n"
    sardes_console.write(string)

    # Assert the copy to clipboard functionality is working as expected.
    qtbot.mouseClick(sardes_console.copy_btn, Qt.LeftButton)
    assert QApplication.clipboard().text() == string

    # Assert the copy to file functionality is working as expected.
    selectedfilename = osp.join(tmp_path, 'sardeslogfile')
    selectedfilter = "Text File (*.txt)"
    mocker.patch.object(QFileDialog, 'getSaveFileName',
                        return_value=(selectedfilename, selectedfilter))

    assert not osp.exists(selectedfilename + '.txt')
    qtbot.mouseClick(sardes_console.saveas_btn, Qt.LeftButton)
    assert osp.exists(selectedfilename + '.txt')
    with open(selectedfilename + '.txt') as f:
        assert f.read() == string


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw', '-s'])
