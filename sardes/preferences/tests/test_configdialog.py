# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the ConfDialog class.
"""
# ---- Third party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget

# ---- Local imports
from sardes.preferences import ConfDialog, ConfPage


# =============================================================================
# ---- Fixtures
# =============================================================================
class ConfPageTest(ConfPage):

    def __init__(self, name, label, iconname, conf):
        self.conf = conf
        self.value = None
        super().__init__(name, label, iconname)

    def setup_page(self):
        pass

    def set_value(self, value):
        self.value = value
        self.sig_settings_changed.emit()

    def get_settings(self):
        return {self.name(): self.value}

    def get_settings_from_conf(self):
        return {self.name(): self.conf[self.name()]}

    def load_settings_from_conf(self):
        self.value = self.conf[self.name()]

    def save_settings_to_conf(self):
        self.conf[self.name()] = self.value


@pytest.fixture
def conf(qtbot):
    """
    A fixture to imitate Sardes conf system.
    """
    return {'confpagetest1': 3, 'confpagetest2': 4}


@pytest.fixture
def configdialog(qtbot, conf):
    configdialog = ConfDialog(main=QWidget())
    qtbot.addWidget(configdialog)
    configdialog.show()

    configdialog.add_confpage(ConfPageTest(
        'confpagetest1', 'ConfPageTest1', 'information', conf))
    configdialog.add_confpage(ConfPageTest(
        'confpagetest2', 'ConfPageTest2', 'information', conf))

    assert not configdialog.apply_button.isEnabled()
    assert conf == {'confpagetest1': 3, 'confpagetest2': 4}
    assert configdialog.count() == 2

    return configdialog


# =============================================================================
# ---- Tests for the ConfDialog
# =============================================================================
def test_settings_changed(configdialog, conf, qtbot):
    """
    Test that the interface is updated as expected when the settings are
    changed in one or more configuration pages.
    """
    confpage1 = configdialog.get_confpage('confpagetest1')

    # Change the value of the first page.
    confpage1.set_value(5)

    assert conf == {'confpagetest1': 3, 'confpagetest2': 4}
    assert confpage1.is_modified()
    assert configdialog.apply_button.isEnabled()

    # Revert the value of the first page to its original value.
    confpage1.set_value(3)

    assert conf == {'confpagetest1': 3, 'confpagetest2': 4}
    assert confpage1.is_modified() is False
    assert not configdialog.apply_button.isEnabled()


def test_apply_setting_changes(configdialog, conf, qtbot):
    """
    Test that applying setting changes is working as expected.
    """
    confpage1 = configdialog.get_confpage('confpagetest1')
    confpage2 = configdialog.get_confpage('confpagetest2')

    # Change the value of the first and second page.
    confpage1.set_value(34)
    confpage2.set_value(25)

    assert conf == {'confpagetest1': 3, 'confpagetest2': 4}
    assert confpage1.is_modified()
    assert confpage2.is_modified()
    assert configdialog.apply_button.isEnabled()

    # Apply the changes.

    # Note that the OK button applies the changes and also close the
    # configurations dialog.
    qtbot.mouseClick(configdialog.ok_button, Qt.LeftButton)
    assert conf == {'confpagetest1': 34, 'confpagetest2': 25}
    assert confpage1.is_modified() is False
    assert confpage2.is_modified() is False
    assert not configdialog.apply_button.isEnabled()


def test_cancel_setting_changes(configdialog, conf, qtbot):
    """
    Test that cancelling setting changes is working as expected.
    """
    confpage1 = configdialog.get_confpage('confpagetest1')
    confpage2 = configdialog.get_confpage('confpagetest2')

    # Change the value of the first and second page.
    confpage1.set_value(34)
    confpage2.set_value(25)

    assert conf == {'confpagetest1': 3, 'confpagetest2': 4}
    assert confpage1.is_modified()
    assert confpage2.is_modified()
    assert configdialog.apply_button.isEnabled()

    # Cancel the changes.
    qtbot.mouseClick(configdialog.cancel_button, Qt.LeftButton)
    assert conf == {'confpagetest1': 3, 'confpagetest2': 4}
    assert confpage1.is_modified() is False
    assert confpage2.is_modified() is False
    assert not configdialog.apply_button.isEnabled()


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
