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
from sardes.config.gui import ICON_COLOR, GREEN, RED, YELLOW

DIRNAME = os.path.join(__rootdir__, 'ressources', 'icons')
LOCAL_ICONS = {
    'master': 'sardes',
    'sort_clear': 'sort_clear'}

FA_ICONS = {
    'add_row': [
        ('mdi.table-row-plus-after',),
        {'color': ICON_COLOR, 'scale_factor': 1.1}],
    'browse_directory': [
        ('mdi.folder-open',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'browse_files': [
        ('fa5.folder-open',),
        {'color': ICON_COLOR, 'scale_factor': 1}],
    'bug': [
        ('mdi.bug',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'cancel_changes': [
        ('mdi.close-circle-outline',),
        {'color': RED, 'scale_factor': 1.2}],
    'cancel_selection_changes': [
        ('mdi.close-box-outline',),
        {'color': RED, 'scale_factor': 1.2}],
    'checklist': [
        ('mdi.format-list-checkbox',),
        {'color': ICON_COLOR, 'scale_factor': 1.1}],
    'clear_selected_data': [
        ('mdi.close-box-outline',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'close': [
        ('fa.close', 'fa.close', 'fa.close'),
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
    'commit_changes': [
        ('mdi.check-circle-outline',),
        {'color': GREEN, 'scale_factor': 1.2}],
    'copy_clipboard': [
        ('mdi.content-copy',),
        {'color': ICON_COLOR, 'scale_factor': 1}],
    'database_connect': [
        ('mdi.power-plug',),
        {'color': GREEN, 'scale_factor': 1.3}],
    'database_disconnect': [
        ('mdi.power-plug-off',),
        {'color': RED, 'scale_factor': 1.3}],
    'delete_data': [
        ('mdi.delete-forever',),
        {'color': ICON_COLOR, 'scale_factor': 1.4}],
    'drag_select': [
        ('mdi.shape-square-plus',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'edit_database_item': [
        ('mdi.square-edit-outline',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'erase_data': [
        ('mdi.eraser',),
        {'color': ICON_COLOR, 'scale_factor': 1.1}],
    'exit': [
        ('fa.power-off',),
        {'color': ICON_COLOR}],
    'eye_off': [
        ('mdi.eye-off',),
        {'color': ICON_COLOR, 'scale_factor': 1.1}],
    'eye_on': [
        ('mdi.eye',),
        {'color': ICON_COLOR, 'scale_factor': 1.1}],
    'failed': [
        ('mdi.alert-circle-outline',),
        {'color': RED, 'scale_factor': 1.3}],
    'file_download': [
        ('mdi.file-download',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'file_excel': [
        ('mdi.file-excel-outline',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'file_export': [
        ('mdi.file-export-outline',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'file_image': [
        ('mdi.file-image',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'file_import': [
        ('mdi.file-import',),
        {'color': ICON_COLOR, 'scale_factor': 1.1}],
    'file_next': [
        ('mdi.arrow-right-bold',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'fmt_line_weight': [
        ('mdi.format-line-weight',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'fmt_marker_size': [
        ('mdi.circle-medium',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'home': [
        ('mdi.home',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'hspan_select': [
        ('mdi.arrow-expand-horizontal',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'import_clipboard': [
        ('mdi.clipboard-plus-outline',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'information': [
        ('mdi.information-outline',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
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
    'menu_down': [
        ('mdi.menu-down',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'menu_right': [
        ('mdi.menu-right',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'pan': [
        ('mdi.pan',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'panes': [
        ('mdi.widgets',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'pane_dock': [
        ('mdi.open-in-app',),
        {'color': ICON_COLOR}],
    'pane_lock': [
        ('mdi.lock-outline',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'pane_undock': [
        ('mdi.window-restore',),
        {'color': ICON_COLOR, 'scale_factor': 1}],
    'pane_unlock': [
        ('mdi.lock-open-outline',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'preferences': [
        ('mdi.settings',),
        {'color': ICON_COLOR, 'scale_factor': 1.3}],
    'remove_row': [
        ('mdi.table-row-remove',),
        {'color': ICON_COLOR, 'scale_factor': 1.1}],
    'reset_layout': [
        ('fa.undo',),
        {'color': ICON_COLOR, 'scale_factor': 1.1}],
    'save': [
        ('fa.save',),
        {'color': ICON_COLOR}],
    'save_to_db': [
        ('mdi.database-import',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'select_all': [
        ('mdi.select-all',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'select_clear': [
        ('mdi.select-off',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'select_row': [
        ('mdi.arrow-expand-horizontal',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'select_column': [
        ('mdi.arrow-expand-vertical',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'show_barplot': [
        ('mdi.chart-bar-stacked',),
        {'color': ICON_COLOR}],
    'show_data_table': [
        ('mdi.table-search',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'show_plot': [
        ('mdi.chart-line',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'sort_ascending': [
        ('mdi.sort-ascending',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'sort_descending': [
        ('mdi.sort-descending',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'succes': [
        ('mdi.check-circle-outline',),
        {'color': GREEN, 'scale_factor': 1.3}],
    'table': [
        ('mdi.table',),
        {'color': ICON_COLOR, 'scale_factor': 1.2}],
    'table_columns': [
        ('fa.columns',),
        {'color': ICON_COLOR, 'scale_factor': 0.9, 'offset': (0, -0.1)}],
    'toolbars': [
        ('mdi.wrench',),
        {'color': ICON_COLOR}],
    'tooloptions': [
        ('fa.bars',),
        {'color': ICON_COLOR}],
    'undo': [
        ('mdi.undo-variant',),
        {'color': ICON_COLOR}],
    'vspan_select': [
        ('mdi.arrow-expand-vertical',),
        {'color': ICON_COLOR, 'scale_factor': 1.1,
         'hflip': True}],
    'warning': [
        ('mdi.alert-outline',),
        {'color': YELLOW, 'scale_factor': 1.3}],
    'zoom_in': [
        ('mdi.plus-circle-outline',),
        {'color': ICON_COLOR, 'scale_factor': 1.1}],
    'zoom_out': [
        ('mdi.minus-circle-outline',),
        {'color': ICON_COLOR, 'scale_factor': 1.1}],
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
