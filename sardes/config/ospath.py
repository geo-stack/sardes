# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import os
import os.path as osp

# ---- Third party imports
from appconfigs.base import get_home_dir

# ---- Local imports
from sardes.config.main import CONF, CONFIG_DIR


def get_select_file_dialog_dir():
    """"
    Return the directory that should be displayed by default
    in file dialogs.
    """
    directory = CONF.get('main', 'select_file_dialog_dir', get_home_dir())
    directory = directory if osp.exists(directory) else get_home_dir()
    return directory


def set_select_file_dialog_dir(directory):
    """"
    Save in the user configs the directory that should be displayed
    by default in file dialogs.
    """
    if directory is not None and osp.exists(directory):
        CONF.set('main', 'select_file_dialog_dir', directory)


def get_company_logo_filename():
    """
    Return the absolute file path to the company logo image.
    """
    for file in os.listdir(CONFIG_DIR):
        root, ext = osp.splitext(file)
        if root == 'company_logo':
            return osp.join(CONFIG_DIR, file)
