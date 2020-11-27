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
import os
import os.path as osp
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
from qtpy.QtCore import Qt

# ---- Local imports
from sardes import __rootdir__
from sardes.widgets.logoselector import LogoSelector, QFileDialog

DOCUMENTS_LOGO_FILENAME = osp.join(
    __rootdir__, 'ressources', 'icons', 'sardes.png')


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def logoselector(qtbot):
    logoselector = LogoSelector()
    qtbot.addWidget(logoselector)
    logoselector.show()

    assert logoselector.filename is None
    return logoselector


# =============================================================================
# ---- Tests for the LogoSelector
# =============================================================================
def test_browse_logo(logoselector, mocker, qtbot):
    """Test that browsing and selecting a new logo is working as expected."""
    mocker.patch.object(
        QFileDialog, 'getOpenFileName',
        return_value=(DOCUMENTS_LOGO_FILENAME, logoselector.FILEFILTER))

    with qtbot.waitSignal(logoselector.sig_logo_changed):
        qtbot.mouseClick(logoselector.browse_logo_button, Qt.LeftButton)
    assert logoselector.filename == DOCUMENTS_LOGO_FILENAME


def test_remove_logo(logoselector, qtbot):
    """Test that removing the current logo is working as expected."""
    with qtbot.waitSignal(logoselector.sig_logo_changed):
        logoselector.load_image(DOCUMENTS_LOGO_FILENAME)
    assert logoselector.filename == DOCUMENTS_LOGO_FILENAME

    with qtbot.waitSignal(logoselector.sig_logo_changed):
        qtbot.mouseClick(logoselector.remove_logo_button, Qt.LeftButton)
    assert logoselector.filename is None


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw', '-s'])
