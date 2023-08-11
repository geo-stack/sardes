# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/geo-stack/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
#
# Copyright (c) 2017 Spyder Project Contributors
# https://github.com/spyder-ide/spyder
#
# Some parts of this file is a derivative work of the Spyder project.
# Licensed under the terms of the MIT License.
#
# Copyright (C) 2013 The IPython Development Team
# https://github.com/ipython/ipython
#
# Some parts of this file is a derivative work of the IPython project.
# Licensed under the terms of the BSD License.
# -----------------------------------------------------------------------------
from __future__ import annotations

# ---- Standard imports
import re
from packaging.version import Version

# ---- Third party imports
from qtpy.QtCore import QObject, Qt, QThread, Signal
from qtpy.QtWidgets import QApplication, QMessageBox, QCheckBox
import requests

# ---- Local imports
from sardes import (
    __version__, __releases_url__, __releases_api__,
    __namever__, __project_url__)
from sardes.config.icons import (
    get_icon, get_standard_iconsize, get_standard_icon)
from sardes.config.locale import _
from sardes.config.main import CONF


class UpdatesManager(QObject):
    """
    Self contained manager that checks if updates are available on GitHub
    and displays the ressults in a message box.
    """

    def __init__(self, parent=None):
        super().__init__()

        self.dialog_updates = UpdatesDialog(parent)
        self._startup_check = False

        self.thread_updates = QThread()

        self.worker_updates = WorkerUpdates()
        self.worker_updates.moveToThread(self.thread_updates)
        self.worker_updates.sig_releases_fetched.connect(
            self._receive_updates_check)

        self.thread_updates.started.connect(self.worker_updates.start)

    def start_updates_check(self, startup_check: bool = False):
        """Check if updates are available."""
        self._startup_check = startup_check
        self.thread_updates.start()

    def _receive_updates_check(self, releases: list[str], error: str):
        """Receive results from an update check."""
        self.thread_updates.quit()

        update_available, latest_release = check_update_available(
            __version__, releases)
        muted_updates = CONF.get('main', 'muted_updates', [])

        if self._startup_check:
            if update_available is False:
                return
            for release in muted_updates:
                if check_version(latest_release, release, '=='):
                    return

        if error is not None:
            msg = error
            icon = get_standard_icon('SP_MessageBoxWarning')
        else:
            if update_available:
                icon = get_icon('update_blue')
                msg = _(
                    "<p><b>Sardes {} is available!</b></p>"
                    "<p>This new version can be downloaded from our "
                    "<a href={}>Releases</a> page.</p>"
                    ).format(latest_release, __releases_url__)
            else:
                icon = get_icon('commit_changes')
                url_m = __project_url__ + "/milestones"
                url_t = __project_url__ + "/issues"
                msg = _(
                    "<p><b>{} is up to date</b></p>"
                    "<p>Further information about Sardes releases are "
                    "available on our <a href={}>Releases</a> page.</p>"
                    "<p>The roadmap of the Sardes project can be consulted "
                    "on our <a href={}>Milestones</a> page.</p>"
                    "<p>Please help Sardes by reporting bugs or proposing "
                    "new features on our <a href={}>Issues Tracker</a>.</p>"
                    ).format(__namever__, __releases_url__, url_m, url_t)

        if self._startup_check:
            # Add some space between text and checkbox.
            msg += "<br>"
        self.dialog_updates.chkbox.setVisible(self._startup_check)

        self.dialog_updates.setText(msg)
        self.dialog_updates.setIconPixmap(
            icon.pixmap(get_standard_iconsize('messagebox')))
        self.dialog_updates.exec_()

        if self.dialog_updates.chkbox.isChecked():
            muted_updates.append(latest_release)
            muted_updates = list(set(muted_updates))
            CONF.set('main', 'muted_updates', muted_updates)


class UpdatesDialog(QMessageBox):
    """
    Dialog to display update checks.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(_('Updates'))
        self.setWindowIcon(get_icon('master'))
        self.setMinimumSize(800, 700)

        self.setWindowFlags(
            Qt.Window | Qt.CustomizeWindowHint | Qt.WindowCloseButtonHint)

        self.chkbox = QCheckBox(_("Do not show this message again."))
        self.setCheckBox(self.chkbox)

        self.setStandardButtons(QMessageBox.Ok)
        self.setDefaultButton(QMessageBox.Ok)


class WorkerUpdates(QObject):
    """
    Worker that fetch available releases using the Github API.
    """
    sig_releases_fetched = Signal(object, object)

    def start(self):
        """Main method of the WorkerUpdates worker."""
        releases, error = fetch_available_releases(__releases_api__)
        self.sig_releases_fetched.emit(releases, error)


def fetch_available_releases(url: str) -> (list[str], str):
    """Retrieve the list of released versions available on GitHub."""
    error = None
    releases = []

    try:
        page = requests.get(__releases_api__)
        data = page.json()
        releases = [item['tag_name'][1:] for item in data]
    except requests.exceptions.HTTPError:
        error = _(
            "Unable to retrieve information because of an http error.")
    except requests.exceptions.ConnectionError:
        error = _(
            "Unable to connect to the internet. Make "
            "sure that your connection is working properly.")
    except requests.exceptions.Timeout:
        error = _(
            "Unable to retrieve information because the "
            "connection timed out.")
    except Exception:
        error = _(
            "Unable to check for updates because of "
            "an unexpected error.")

    return releases, error


def check_update_available(version: str, releases: list[str]) -> (bool, str):
    """
    Checks if there is an update available.

    It takes as parameters the current version of Sardes and a list of
    valid cleaned releases in chronological order (what github api returns
    by default). Example: ['2.3.4', '2.3.3' ...]

    Copyright (c) Spyder Project Contributors
    Licensed under the terms of the MIT License
    """
    if len(releases) == 0:
        return False, None

    if is_stable_version(version):
        # Remove non stable versions from the list.
        releases = [r for r in releases if is_stable_version(r)]

    latest_release = str(max([Version(r) for r in releases]))
    return check_version(version, latest_release, '<'), latest_release


def check_version(actver: str, version: str, cmp_op: str):
    """
    Check version string of an active module against a required version.

    If dev/prerelease tags result in TypeError for string-number comparison,
    it is assumed that the dependency is satisfied. Users on dev branches are
    responsible for keeping their own packages up to date.

    Copyright (C) 2013 The IPython Development Team
    Licensed under the terms of the BSD License
    """
    if isinstance(version, tuple):
        version = '.'.join([str(i) for i in version])

    try:
        if cmp_op == '>':
            return Version(actver) > Version(version)
        elif cmp_op == '>=':
            return Version(actver) >= Version(version)
        elif cmp_op == '==':
            return Version(actver) == Version(version)
        elif cmp_op == '<':
            return Version(actver) < Version(version)
        elif cmp_op == '<=':
            return Version(actver) <= Version(version)
        else:
            return False
    except TypeError:
        return True


def is_stable_version(version):
    """
    Returns wheter this is a stable version or not. A stable version has no
    letters in the final component, but only numbers.

    Stable version example: 1.2, 1.3.4, 1.0.5
    Not stable version: 1.2alpha, 1.3.4beta, 0.1.0rc1, 3.0.0dev

    Copyright (c) 2017 Spyder Project Contributors
    Licensed under the terms of the MIT License
    """
    if not isinstance(version, tuple):
        version = version.split('.')
    last_part = version[-1]

    if not re.search('[a-zA-Z]', last_part):
        return True
    else:
        return False


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    updates_manager = UpdatesManager()
    updates_manager.start_updates_check(startup_check=False)
    sys.exit(app.exec_())
