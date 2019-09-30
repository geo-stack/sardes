# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
Tests for the qthelpers functions.
"""

# ---- Standard imports
import os
from itertools import product

# ---- Third party imports
import pytest

# ---- Local imports
from sardes.utils.qthelpers import format_tooltip


# =============================================================================
# ---- Tests
# =============================================================================
def test_format_tooltip():
    """Test that tooltip are formatted correctly."""
    texts = ['TEXT', None, '']
    shortcuts = ['S', None, '', 'BADSHORTCUT']
    tips = ['TOOLTIPTEXT', None, '']
    for text, shortcut, tip in product(texts, shortcuts, tips):
        keystr = 'S' if shortcut == 'S' else ''
        if text and keystr and tip:
            expected_ttip = ("<p style='white-space:pre'><b>TEXT (S)</b></p>"
                             "<p>TOOLTIPTEXT</p>")
        elif text and keystr:
            expected_ttip = "<p style='white-space:pre'><b>TEXT (S)</b></p>"
        elif text and tip:
            expected_ttip = ("<p style='white-space:pre'><b>TEXT</b></p>"
                             "<p>TOOLTIPTEXT</p>")
        elif keystr and tip:
            expected_ttip = ("<p style='white-space:pre'><b>(S)</b></p>"
                             "<p>TOOLTIPTEXT</p>")
        elif text:
            expected_ttip = "<p style='white-space:pre'><b>TEXT</b></p>"
        elif keystr:
            expected_ttip = "<p style='white-space:pre'><b>(S)</b></p>"
        elif tip:
            expected_ttip = "<p>TOOLTIPTEXT</p>"
        else:
            expected_ttip = ""

        tooltip = format_tooltip(text=text, shortcuts=shortcut, tip=tip)
        assertion_error = {'text': text, 'shortcut': shortcut, 'tip': tip}

        assert tooltip == expected_ttip, assertion_error


if __name__ == "__main__":
    pytest.main(['-x', os.path.basename(__file__), '-v', '-rw', '-s'])
