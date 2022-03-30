# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the figures.py module.
"""

# ---- Standard library imports
import os.path as osp

# ---- Third party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

# ---- Local imports
from sardes.api.figures import (
    SardesFigureWidget, SardesFigureCanvas, QMessageBox, QFileDialog)


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def figwidget(qtbot):
    figure = Figure()
    canvas = FigureCanvasAgg(figure)
    ax = figure.add_axes([0.1, 0.1, 0.8, 0.8], frameon=True)
    ax.plot([1, 2, 3], [1, 2, 3], '.')

    figcanvas = SardesFigureCanvas(figure)
    figwidget = SardesFigureWidget(figcanvas)

    qtbot.addWidget(figwidget)
    figwidget.show()
    qtbot.waitExposed(figwidget)

    return figwidget


# =============================================================================
# ---- Tests
# =============================================================================
def test_copy_figure_to_clipboard(figwidget, qtbot):
    """
    Test that copying the timeseries plot to the clipboard is working as
    expected.
    """
    QApplication.clipboard().clear()
    assert QApplication.clipboard().image().isNull()
    qtbot.mouseClick(figwidget.copy_to_clipboard_btn, Qt.LeftButton)
    assert not QApplication.clipboard().image().isNull()


def test_save_figure_to_file_error(figwidget, mocker, qtbot, tmp_path):
    """
    Test that permission errors when trying to save figures to file are
    handled as expected.
    """
    # The file type doesn't really matter to assess that permission errors are
    # catched and handled properly.
    fext, ffilter = next(iter((SardesFigureCanvas.NAMEFILTERS.items())))

    # We omit the file extension on purpose in order to test that it is
    # added as expected afterward.
    fpath = osp.join(tmp_path, 'test_figure')

    # We expect the file dialog to be called 2 times during this test.
    qfdialog_patcher = mocker.patch.object(
        QFileDialog,
        'getSaveFileName',
        side_effect=[(fpath, ffilter), (None, None)]
        )

    # We patch the message box that is shown when an operation to save
    # a figure to file fails.
    qmsgbox_patcher = mocker.patch.object(
        QMessageBox, 'warning', return_value=QMessageBox.Ok)

    # We patch 'figure.savefig' method to simulate a PermissionError when
    # it is called.
    savefig_patcher = mocker.patch.object(
        figwidget.canvas.figure, 'savefig', side_effect=PermissionError)

    # When the 'save_figure_btn' is clicked, the qt file dialog is called
    # a first time and returns two valid fpath and ffilter values.
    #
    # A PermissionError is then triggered when trying to save the figure and
    # a warning message box is shown.
    #
    # Another qt file dialog is then automatically opened, asking the
    # user to select another file location to save the figure. The file dialog
    # then returns 'None' values, which simulate the user action of
    # cancelling the saving operation.

    qtbot.mouseClick(figwidget.save_figure_btn, Qt.LeftButton)
    assert savefig_patcher.call_count == 1
    assert qfdialog_patcher.call_count == 2
    assert qmsgbox_patcher.call_count == 1
    assert not osp.exists(fpath + fext)


@pytest.mark.parametrize(
    'fext, ffilter', list(SardesFigureCanvas.NAMEFILTERS.items()))
def test_save_figure_to_file(figwidget, mocker, qtbot, tmp_path,
                             fext, ffilter):
    """
    Test that saving a figure to file is working as expected.
    """
    # We omit the file extension on purpose in order to test that it is
    # added as expected afterward.
    fpath = osp.join(tmp_path, 'test_figure')

    qfdialog_patcher = mocker.patch.object(
        QFileDialog,
        'getSaveFileName',
        return_value=(fpath, ffilter)
        )

    qtbot.mouseClick(figwidget.save_figure_btn, Qt.LeftButton)
    assert qfdialog_patcher.call_count == 1
    assert osp.exists(fpath + fext)


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
