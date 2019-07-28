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
from qtpy.QtCore import QSize
from qtpy.QtGui import QIcon
import qtawesome as qta

# ---- Local imports
from sardes import __rootdir__
from sardes.config.gui import ICON_COLOR, GREEN, RED

DIRNAME = os.path.join(__rootdir__, 'ressources', 'icons')
LOCAL_ICONS = {
    'master': 'sardes'}

FA_ICONS = {
    'bug': [
        ('mdi.bug',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
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
    'database_connected': [
        ('mdi.database-check',),
        {'color': GREEN, 'scale_factor': 1.3}],
    'database_disconnected': [
        ('mdi.database',),
        {'color': RED, 'scale_factor': 1.3}],
    'failed': [
        ('mdi.alert-circle-outline',),
        {'color': RED, 'scale_factor': 1.3}],
    'exit': [
        ('fa.power-off',),
        {'color': ICON_COLOR}],
    'languages': [
        ('mdi.web',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'lang_en': [
        ('mdi.alpha-e', 'mdi.alpha-n'),
        {'options': [{'scale_factor': 1.65,
                      'offset': (-0.25, 0),
                      'color': ICON_COLOR},
                     {'scale_factor': 1.65,
                      'offset': (0.25, 0),
                      'color': ICON_COLOR}]}],
    'lang_fr': [
        ('mdi.alpha-f', 'mdi.alpha-r'),
        {'options': [{'scale_factor': 1.65,
                      'offset': (-0.25, 0),
                      'color': ICON_COLOR},
                     {'scale_factor': 1.65,
                      'offset': (0.25, 0),
                      'color': ICON_COLOR}]}],
    'information': [
        ('mdi.information-outline',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'panes': [
        ('mdi.view-grid',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'preferences': [
        ('mdi.settings',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'succes': [
        ('mdi.check-circle-outline',),
        {'color': GREEN, 'scale_factor': 1.3}],
    'tooloptions': [
        ('fa.bars',),
        {'color': ICON_COLOR}],
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
