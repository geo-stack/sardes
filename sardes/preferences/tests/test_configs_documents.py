# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the DocumentsSettingsConfPage class.
"""

# ---- Standard imports
import os
import os.path as osp
os.environ['SARDES_PYTEST'] = 'True'

# ---- Third party imports
import pytest
from qtpy.QtGui import QFont
from qtpy.QtCore import Qt

# ---- Local imports
from sardes import __rootdir__
from sardes.config.main import CONF, CONFIG_DIR
from sardes.preferences.documents import DocumentsSettingsConfPage
from sardes.widgets.logoselector import QFileDialog

DOCUMENTS_LOGO_FILENAME = osp.join(
    __rootdir__, 'ressources', 'icons', 'sardes.png')
CONF_LOGO_FILENAME = osp.join(CONFIG_DIR, 'sardes.png')


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def doc_confpage(qtbot):
    # We reset the configs to defaults to make sure each test are
    # run against a fresh setup.
    CONF.reset_to_defaults()
    if osp.exists(CONF_LOGO_FILENAME):
        os.remove(CONF_LOGO_FILENAME)

    doc_confpage = DocumentsSettingsConfPage()
    qtbot.addWidget(doc_confpage)
    doc_confpage.show()

    expected_documents_settings = {
        'logo_filename': None,
        'site_url': '',
        'authors_name': '',
        'xlsx_font': 'Calibri',
        'graph_font': 'Arial'}
    assert doc_confpage.get_settings() == expected_documents_settings
    assert doc_confpage.is_modified() is False

    return doc_confpage


# =============================================================================
# ---- Tests
# =============================================================================
def test_change_documents_logo(doc_confpage, qtbot, mocker):
    """Test that changing the documents settings is working as expected."""

    # Select a new logo.
    filefilter = doc_confpage.logo_selector.FILEFILTER
    mocker.patch.object(
        QFileDialog, 'getOpenFileName',
        return_value=(DOCUMENTS_LOGO_FILENAME, filefilter))
    with qtbot.waitSignal(doc_confpage.sig_settings_changed):
        doc_confpage.logo_selector.load_image(DOCUMENTS_LOGO_FILENAME)

    assert doc_confpage.is_modified()
    assert (doc_confpage.get_settings()['logo_filename'] ==
            DOCUMENTS_LOGO_FILENAME)
    assert doc_confpage.get_settings_from_conf()['logo_filename'] is None
    assert not osp.exists(CONF_LOGO_FILENAME)

    # Apply the logo change.
    doc_confpage.apply_changes()

    assert not doc_confpage.is_modified()
    assert (doc_confpage.get_settings()['logo_filename'] ==
           CONF_LOGO_FILENAME)
    assert (doc_confpage.get_settings_from_conf()['logo_filename'] ==
            CONF_LOGO_FILENAME)
    assert osp.exists(CONF_LOGO_FILENAME)

    # Remove the logo.
    with qtbot.waitSignal(doc_confpage.sig_settings_changed):
        doc_confpage.logo_selector.load_default_image()

    assert doc_confpage.is_modified()
    assert doc_confpage.get_settings()['logo_filename'] is None
    assert (doc_confpage.get_settings_from_conf()['logo_filename'] ==
            CONF_LOGO_FILENAME)
    assert osp.exists(CONF_LOGO_FILENAME)

    # Apply the removal of the logo.
    doc_confpage.apply_changes()

    assert not doc_confpage.is_modified()
    assert doc_confpage.get_settings()['logo_filename'] is None
    assert doc_confpage.get_settings_from_conf()['logo_filename'] is None
    assert not osp.exists(CONF_LOGO_FILENAME)


def test_change_site_url(doc_confpage, qtbot, mocker):
    """Test that changing the site url is working as expected."""

    # Change the site url.
    expected_site_url = 'https://github.com/cgq-qgc/sardes'
    with qtbot.waitSignal(doc_confpage.sig_settings_changed):
        doc_confpage.site_url_lineedit.setText(expected_site_url)
        qtbot.keyPress(doc_confpage.site_url_lineedit, Qt.Key_Enter)

    assert doc_confpage.is_modified()
    assert doc_confpage.get_settings()['site_url'] == expected_site_url
    assert doc_confpage.get_settings_from_conf()['site_url'] == ''

    # Apply the changes.
    doc_confpage.apply_changes()
    assert not doc_confpage.is_modified()
    assert doc_confpage.get_settings()['site_url'] == expected_site_url
    assert (doc_confpage.get_settings_from_conf()['site_url'] ==
            expected_site_url)


def test_change_author(doc_confpage, qtbot, mocker):
    """Test that changing the author's name is working as expected."""

    # Change the author's name.
    expected_author = 'Jean-Sébastien Gosselin'
    with qtbot.waitSignal(doc_confpage.sig_settings_changed):
        doc_confpage.authors_name_lineedit.setText(expected_author)
        qtbot.keyPress(doc_confpage.authors_name_lineedit, Qt.Key_Enter)

    assert doc_confpage.is_modified()
    assert doc_confpage.get_settings()['authors_name'] == expected_author
    assert doc_confpage.get_settings_from_conf()['authors_name'] == ''

    # Apply the changes.
    doc_confpage.apply_changes()
    assert not doc_confpage.is_modified()
    assert doc_confpage.get_settings()['authors_name'] == expected_author
    assert (doc_confpage.get_settings_from_conf()['authors_name'] ==
            expected_author)


def test_change_fonts(doc_confpage, qtbot, mocker):
    """Test that changing the fonts is working as expected."""
    # Change the xlsx and graph fonts.
    expected_font = 'Courier'

    # Change the xlsx font.
    with qtbot.waitSignal(doc_confpage.sig_settings_changed):
        doc_confpage.xlsx_font_combobox.setCurrentFont(QFont(expected_font))

    assert doc_confpage.is_modified()
    assert doc_confpage.get_settings()['xlsx_font'] == expected_font
    assert doc_confpage.get_settings_from_conf()['xlsx_font'] == 'Calibri'

    # Apply the changes.
    doc_confpage.apply_changes()
    assert not doc_confpage.is_modified()
    assert doc_confpage.get_settings()['xlsx_font'] == expected_font
    assert doc_confpage.get_settings_from_conf()['xlsx_font'] == expected_font

    # Change the graph font.
    with qtbot.waitSignal(doc_confpage.sig_settings_changed):
        doc_confpage.graph_font_combobox.setCurrentFont(QFont(expected_font))

    assert doc_confpage.is_modified()
    assert doc_confpage.get_settings()['graph_font'] == expected_font
    assert doc_confpage.get_settings_from_conf()['graph_font'] == 'Arial'

    # Apply the changes.
    doc_confpage.apply_changes()
    assert not doc_confpage.is_modified()
    assert doc_confpage.get_settings()['graph_font'] == expected_font
    assert doc_confpage.get_settings_from_conf()['graph_font'] == expected_font


if __name__ == "__main__":
    pytest.main(['-x', __file__, '-v', '-rw'])
