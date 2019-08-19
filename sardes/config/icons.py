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
    'checklist': [
        ('mdi.format-list-checkbox',),
        {'color': ICON_COLOR, 'scale_factor': 1.1}],
    'clear_selected_data': [
        ('mdi.close-box-outline',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
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
    'eye_on': [
        ('mdi.eye',),
        {'color': ICON_COLOR, 'scale_factor': 1.1}],
    'eye_off': [
        ('mdi.eye-off',),
        {'color': ICON_COLOR, 'scale_factor': 1.1}],
    'delete_data': [
        ('mdi.delete-forever',),
        {'color': ICON_COLOR, 'scale_factor': 1.4}],
    'commit_changes': [
        ('mdi.check-circle-outline',),
        {'color': GREEN, 'scale_factor': 1.3}],
    'database_connect': [
        ('mdi.power-plug',),
        {'color': GREEN, 'scale_factor': 1.3}],
    'database_disconnect': [
        ('mdi.power-plug-off',),
        {'color': RED, 'scale_factor': 1.3}],
    'failed': [
        ('mdi.alert-circle-outline',),
        {'color': RED, 'scale_factor': 1.3}],
    'home': [
        ('mdi.home',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
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
    'pan': [
        ('mdi.pan',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'panes': [
        ('mdi.view-grid',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'preferences': [
        ('mdi.settings',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'drag_select': [
        ('mdi.shape-square-plus',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'hspan_select': [
        ('mdi.arrow-expand-horizontal',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'vspan_select': [
        ('mdi.arrow-expand-vertical',),
        {'color': ICON_COLOR, 'scale_factor': 1.1,
         'hflip': True}],
    'save': [
        ('fa.save',),
        {'color': ICON_COLOR}],
    'show_plot': [
        ('mdi.chart-line',),
        {'color': ICON_COLOR}],
    'succes': [
        ('mdi.check-circle-outline',),
        {'color': GREEN, 'scale_factor': 1.3}],
    'tooloptions': [
        ('fa.bars',),
        {'color': ICON_COLOR}],
    'toolbars': [
        ('mdi.wrench',),
        {'color': ICON_COLOR}],
    'warning': [
        ('mdi.alert-circle-outline',),
        {'color': RED, 'scale_factor': 1.3}],
    'zoom_to_rect': [
        ('mdi.magnify-plus-cursor',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
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
