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
import sys
from datetime import datetime
from math import pi
from time import strptime
import platform

# ---- Third party imports
from qtpy.QtGui import QKeySequence
from qtpy.QtCore import QByteArray, QDateTime, QPoint, QSize, Qt
from qtpy.QtWidgets import (QAction, QDateEdit, QSizePolicy, QToolBar,
                            QToolButton, QWidget, QApplication, QStyleFactory)

# ---- Local imports
from sardes.config.gui import (get_iconsize, get_toolbar_item_spacing)
from sardes.config.icons import get_icon
from sardes.widgets.waitingspinner import WaitingSpinner


def center_widget_to_another(widget, other_widget):
    """Center widget position to another widget's geometry."""
    q1 = widget.frameGeometry()
    w2 = other_widget.frameGeometry().width()
    h2 = other_widget.frameGeometry().height()
    c2 = other_widget.mapToGlobal(QPoint(w2 / 2, h2 / 2))
    q1.moveCenter(c2)
    widget.move(q1.topLeft())


def create_application():
    """Create a QApplication instance if it doesn't already exist"""
    qapp = QApplication.instance()
    if qapp is None:
        qapp = QApplication(sys.argv)

        if platform.system() == 'Windows':
            qapp.setStyle(QStyleFactory.create('WindowsVista'))

    return qapp


def create_action(parent, text=None, shortcut=None, icon=None, tip=None,
                  toggled=None, triggered=None, data=None, menurole=None,
                  context=Qt.WindowShortcut, name=None):
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
    if any((text, tip, shortcut)):
        action.setToolTip(format_tooltip(text, tip, shortcut))
    if text:
        action.setStatusTip(format_statustip(text, shortcut))
    if data is not None:
        action.setData(data)
    if menurole is not None:
        action.setMenuRole(menurole)
    if shortcut is not None:
        if isinstance(shortcut, (list, tuple)):
            action.setShortcuts(shortcut)
        else:
            action.setShortcut(shortcut)
    if name is not None:
        action.setObjectName(name)

    action.setShortcutContext(context)

    return action


def create_mainwindow_toolbar(title, iconsize=None, areas=None, spacing=None,
                              movable=False, floatable=False):
    """Create and return a toolbar with title and object_name."""
    toolbar = QToolBar(title)
    toolbar.setObjectName(title.lower().replace(' ', '_'))
    toolbar.setFloatable(floatable)
    toolbar.setMovable(movable)
    toolbar.setAllowedAreas(areas or Qt.TopToolBarArea)
    toolbar.layout().setSpacing(spacing or get_toolbar_item_spacing())
    iconsize = iconsize or get_iconsize()
    toolbar.setIconSize(QSize(iconsize, iconsize))
    return toolbar


def create_toolbar_stretcher():
    """Create a stretcher to be used in a toolbar """
    stretcher = QWidget()
    stretcher.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    return stretcher


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
    if any((text, tip, shortcut)):
        button.setToolTip(format_tooltip(text, tip, shortcut))
    if text_beside_icon:
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    button.setAutoRaise(autoraise)
    if triggered is not None:
        button.clicked.connect(triggered)
    if toggled is not None:
        button.toggled.connect(toggled)
        button.setCheckable(True)
    if shortcut is not None:
        if isinstance(shortcut, (list, tuple)):
            for sc in shortcut:
                button.setShortcut(sc)
        else:
            button.setShortcut(shortcut)
    if iconsize is not None:
        button.setIconSize(QSize(int(iconsize), int(iconsize)))
    return button


def format_statustip(text, shortcuts):
    """
    Format text and shortcut into a single str to be set
    as an action status tip. The status tip is displayed on all status
    bars provided by the action's top-level parent widget.
    """
    keystr = get_shortcuts_native_text(shortcuts)
    if text and keystr:
        stip = "{} ({})".format(text, keystr)
    elif text:
        stip = "{}".format(text)
    else:
        stip = ""
    return stip


def format_tooltip(text, tip, shortcuts):
    """
    Format text, tip and shortcut into a single str to be set
    as a widget's tooltip.
    """
    keystr = get_shortcuts_native_text(shortcuts)
    # We need to replace the unicode characters < and > by their HTML
    # code to avoid problem with the HTML formatting of the tooltip.
    keystr = keystr.replace('<', '&#60;').replace('>', '&#62;')
    ttip = ""
    if text or keystr:
        ttip += "<p style='white-space:pre'><b>"
        if text:
            ttip += "{}".format(text) + (" " if keystr else "")
        if keystr:
            ttip += "({})".format(keystr)
        ttip += "</b></p>"
    if tip:
        ttip += "<p>{}</p>".format(tip or '')
    return ttip


def get_shortcuts_native_text(shortcuts):
    """
    Return the native text of a shortcut or a list of shortcuts.
    """
    if not isinstance(shortcuts, (list, tuple)):
        shortcuts = [shortcuts, ]

    return ', '.join([QKeySequence(sc).toString(QKeySequence.NativeText)
                      for sc in shortcuts])


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


def qdatetime_from_datetime(datetime_object):
    """Convert a datetime to a QDateTime object."""
    return QDateTime(*tuple(datetime_object.timetuple())[:6])


def get_datetime_from_editor(editor):
    """
    Return a datetime object corresponding to the current datetime value of a
    a QDateTimeEdit widget.
    """
    dtime = datetime.strptime(
        editor.dateTime().toString('yyyy-MM-dd hh:mm'), '%Y-%m-%d %H:%M')
    if isinstance(editor, QDateEdit):
        return dtime.date()
    else:
        return dtime


def qdatetime_from_str(str_date_time, datetime_format="%Y-%m-%d %H:%M"):
    """Convert a date time str to a QDateTime object."""
    struct_time = strptime(str_date_time, datetime_format)
    return QDateTime(struct_time.tm_year, struct_time.tm_mon,
                     struct_time.tm_mday, struct_time.tm_hour,
                     struct_time.tm_min)
