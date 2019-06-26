# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

from sardes.config.main import CONF


ICON_COLOR = '#202020'
GREEN = '#00aa00'
RED = '#CC0000'


def get_iconsize():
    return 24


def get_window_settings():
    """
    Get and return the main window normal size, normal position, and maximized
    state flag that were saved in the config file the last time Sardes
    was closed.
    """
    window_size = CONF.get('main', 'window/size')
    window_position = CONF.get('main', 'window/position')
    is_maximized = CONF.get('main', 'window/is_maximized')
    return (window_size, window_position, is_maximized)


def set_window_settings(window_size, window_position, is_maximized):
    """
    Set the specified main window normal size, normal position, and maximized
    state flag in the configuration file.
    """
    CONF.set('main', 'window/size', window_size)
    CONF.set('main', 'window/position', window_position)
    CONF.set('main', 'window/is_maximized', is_maximized)
