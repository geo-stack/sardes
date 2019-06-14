# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# ----------------------------------------------------------------------------


# ---- Standard imports
import os
import os.path as osp

# ---- Third party imports
from qtpy.QtCore import QSize, Qt
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QToolButton
import qtawesome as qta

# ---- Local imports
from sardes import __rootdir__
from sardes.config.gui import ICON_COLOR, GREEN, RED

DIRNAME = os.path.join(__rootdir__, 'ressources', 'icons_png')
LOCAL_ICONS = {}

FA_ICONS = {
    'close_all': [
        ('fa.close', 'fa.close', 'fa.close'),
        {'options': [{'scale_factor': 0.6,
                      'offset': (0.3, -0.3),
                      'color': ICON_COLOR},
                     {'scale_factor': 0.6,
                      'offset': (-0.3, -0.3),
                      'color': ICON_COLOR},
                     {'scale_factor': 0.6,
                      'offset': (0.3, 0.3),
                      'color': ICON_COLOR}]}],
    'erase_data': [
        ('mdi.eraser',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'delete_data': [
        ('mdi.delete-forever',),
        {'color': ICON_COLOR, 'scale_factor': 1.4}],
    'commit_changes': [
        ('mdi.check-circle-outline',),
        {'color': GREEN, 'scale_factor': 1.3}],
    'failed': [
        ('mdi.alert-circle-outline',),
        {'color': RED, 'scale_factor': 1.3}],
    'succes': [
        ('mdi.check-circle-outline',),
        {'color': GREEN, 'scale_factor': 1.3}],
    'warning': [
        ('mdi.alert-circle-outline',),
        {'color': RED, 'scale_factor': 1.3}],
    }

ICON_SIZES = {'large': (32, 32),
              'normal': (28, 28),
              'small': (20, 20)}


def get_icon(name):
    """Return a QIcon from a specified icon name."""
    if name in FA_ICONS:
        args, kwargs = FA_ICONS[name]
        return qta.icon(*args, **kwargs)
    elif name in LOCAL_ICONS:
        return QIcon(osp.join(DIRNAME, LOCAL_ICONS[name]))
    else:
        return QIcon()


def get_iconsize(size):
    return QSize(*ICON_SIZES[size])
