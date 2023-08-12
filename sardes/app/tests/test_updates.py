# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © GWHAT Project Contributors
# https://github.com/jnsebgosselin/gwhat
#
# This file is part of GWHAT (Ground-Water Hydrograph Analysis Toolbox).
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import os
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third parties imports
import pytest
from qtpy.QtCore import QTimer

# ---- Local imports
from sardes.app.updates import UpdatesManager, QMessageBox
from sardes.config.main import CONF


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def updates_manager(qtbot):
    CONF.reset_to_defaults()
    updates_manager = UpdatesManager()

    updates_manager.dialog.setModal(False)
    assert updates_manager.dialog.isVisible() is False

    return updates_manager


# =============================================================================
# ---- Tests
# =============================================================================
def test_update_available(updates_manager, qtbot, mocker):
    """
    Assert that the worker to check for updates on the GitHub API is
    working as expected when an update is available.

    Note that since we are forcing the current version to a not stable version,
    the '1.1.0rc2  update should be proposed to the user.
    """
    mocker.patch('sardes.app.updates.__version__', '1.1.0rc1')
    mocker.patch(
        'sardes.app.updates.fetch_available_releases',
        return_value=(['0.9.0', '1.1.0rc2', '1.0.0'], None)
        )

    def handle_dialog(on_startup: bool):
        assert updates_manager.dialog.isVisible() is True
        assert updates_manager.dialog.chkbox.isVisible() == on_startup
        assert 'Sardes 1.1.0rc2 is available!' in updates_manager.dialog.text()
        updates_manager.dialog.close()

    with qtbot.waitSignal(updates_manager.worker.sig_releases_fetched):
        QTimer.singleShot(300, lambda: handle_dialog(on_startup=False))
        updates_manager.start_updates_check()

    # Test that this is working also as expected during STARTUP and mute
    # the message on next startups.
    with qtbot.waitSignal(updates_manager.worker.sig_releases_fetched):
        updates_manager.dialog.chkbox.setChecked(True)
        QTimer.singleShot(300, lambda: handle_dialog(on_startup=True))
        updates_manager.start_updates_check(startup_check=True)

    # Assert the update is muted as expected.
    with qtbot.waitSignal(updates_manager.worker.sig_releases_fetched):
        updates_manager.start_updates_check(startup_check=True)
    assert updates_manager.dialog.isVisible() is False


def test_no_update_available(updates_manager, qtbot, mocker):
    """
    Assert that the worker to check for updates on the GitHub API is
    working as expected when no update is available.
    """
    mocker.patch('sardes.app.updates.__version__', '1.1.0')
    mocker.patch(
        'sardes.app.updates.fetch_available_releases',
        return_value=(['0.9.0', '1.1.0rc2', '1.0.0'], None)
        )

    # Note that since the current version is stable, the '1.1.0rc2 update
    # should not be proposed to the user.



#     assert updates_manager.dialog.isVisible() is True
#     assert updates_manager.dialog.chkbox.isVisible() is False
#     assert 'is up to date' in updates_manager.dialog.text()
#     updates_manager.dialog.close()

#     # Assert the updates manager is working as expected when an update
#     # is available.


#     mocker.patch('sardes.app.updates.__version__', '1.1.0rc1')

#     with qtbot.waitSignal(updates_manager.worker.sig_releases_fetched):
#         updates_manager.start_updates_check()


#     # Assert the updates manager is working as expected when there is
#     # an error.
#     fetch_patcher.return_value = (['0.9.0', '1.1.0rc2', '1.0.0'], 'Some error')

#     with qtbot.waitSignal(updates_manager.worker.sig_releases_fetched):
#         updates_manager.start_updates_check()

#     assert updates_manager.dialog.isVisible() is True
#     assert updates_manager.dialog.chkbox.isVisible() is False
#     assert 'Some error' in updates_manager.dialog.text()
#     updates_manager.dialog.close()


# def test_updates_manager_startup(updates_manager, qtbot, mocker):
#     """
#     Assert that the worker to check for updates on the GitHub API is
#     working as expected when on Sardes startup.
#     """
#     mocker.patch('sardes.app.updates.__version__', '1.0.0')

#     # Assert the updates manager is working as expected when up-to-date.
#     fetch_patcher = mocker.patch(
#         'sardes.app.updates.fetch_available_releases',
#         return_value=(['0.9.0', '1.0.0'], None)
#         )

#     with qtbot.waitSignal(updates_manager.worker.sig_releases_fetched):
#         updates_manager.start_updates_check(startup_check=True)

#     assert updates_manager.dialog.isVisible() is False

#     # Assert the updates manager is working as expected when an error occured.
#     fetch_patcher.return_value = (['0.9.0', '1.0.0'], 'Some error')

#     with qtbot.waitSignal(updates_manager.worker.sig_releases_fetched):
#         updates_manager.start_updates_check(startup_check=True)

#     assert updates_manager.dialog.isVisible() is False

#     # Assert the updates manager is working as expected when an update
#     # is available.
#     fetch_patcher.return_value = (['0.9.0', '1.1.0', '1.0.0'], None)




if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
