# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""Qt utilities"""

# ---- Standard imports
from math import pi
import sys

# ---- Third party imports
from qtpy.QtCore import QByteArray, QSize, Qt
from qtpy.QtWidgets import QAction, QSizePolicy, QToolBar, QToolButton

# ---- Local imports
from sardes.config.icons import get_icon
from sardes.widgets.waitingspinner import WaitingSpinner


def create_action(parent, text, shortcut=None, icon=None, tip=None,
                  toggled=None, triggered=None, data=None, menurole=None,
                  context=Qt.WindowShortcut):
    """Create and return a QAction with the provided settings."""
    action = QAction(text, parent)
    if triggered is not None:
        action.triggered.connect(triggered)
    if toggled is not None:
        action.toggled.connect(toggled)
        action.setCheckable(True)
    if icon is not None:
        icon = get_icon(icon) if isinstance(icon, str) else icon
        action.setIcon(icon)
    if tip is not None:
        action.setToolTip(tip)
        action.setStatusTip(tip)
    if data is not None:
        action.setData(data)
    if menurole is not None:
        action.setMenuRole(menurole)
    if shortcut is not None:
        action.setShortcut(shortcut)
    action.setShortcutContext(context)

    return action


def create_toolbar_separator():
    """Create and return a toolbar separator widget."""
    separator = QToolBar()
    separator.addSeparator()
    separator.setStyleSheet(
        "QToolBar {border: 0px; background: transparent}")
    policy = separator.sizePolicy()
    policy.setVerticalPolicy(QSizePolicy.Expanding)
    separator.setSizePolicy(policy)
    return separator


def create_toolbutton(parent, text=None, shortcut=None, icon=None, tip=None,
                      toggled=None, triggered=None,
                      autoraise=True, text_beside_icon=False, iconsize=None):
    """Create a QToolButton with the provided settings."""
    button = QToolButton(parent)
    if text is not None:
        button.setText(text)
    if icon is not None:
        icon = get_icon(icon) if isinstance(icon, str) else icon
        button.setIcon(icon)
    if text is not None or tip is not None:
        ttip = ("<p style='white-space:pre'><b>{} ({})</b></p>"
                "<p>{}</p>").format(text or '', shortcut or '', tip or '')
        button.setToolTip(ttip)
    if text_beside_icon:
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    button.setAutoRaise(autoraise)
    if triggered is not None:
        button.clicked.connect(triggered)
    if toggled is not None:
        button.toggled.connect(toggled)
        button.setCheckable(True)
    if shortcut is not None:
        button.setShortcut(shortcut)
    if iconsize is not None:
        button.setIconSize(QSize(iconsize, iconsize))
    return button


def create_waitspinner(size=32, n=11, parent=None):
    """
    Create a wait spinner with the specified size built with n circling dots.
    """
    dot_padding = 1

    # To calculate the size of the dots, we need to solve the following
    # system of two equations in two variables.
    # (1) middle_circumference = pi * (size - dot_size)
    # (2) middle_circumference = n * (dot_size + dot_padding)
    dot_size = (pi * size - n * dot_padding) / (n + pi)
    inner_radius = (size - 2 * dot_size) / 2

    spinner = WaitingSpinner(parent, centerOnParent=False)
    spinner.setTrailSizeDecreasing(True)
    spinner.setNumberOfLines(n)
    spinner.setLineLength(dot_size)
    spinner.setLineWidth(dot_size)
    spinner.setInnerRadius(inner_radius)
    spinner.setColor(Qt.black)

    return spinner


def qbytearray_to_hexstate(qba):
    """Convert QByteArray object to a str hexstate."""
    return str(bytes(qba.toHex().data()).decode())


def hexstate_to_qbytearray(hexstate):
    """Convert a str hexstate to a QByteArray object."""
    return QByteArray().fromHex(str(hexstate).encode('utf-8'))
