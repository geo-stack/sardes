# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard imports
import gettext
import os
import os.path as osp

# ---- Local imports
from sardes import __rootdir__
from sardes.config.main import CONF

_ = gettext.gettext


LOCALE_PATH = osp.join(__rootdir__, 'locale')
DEFAULT_LANGUAGE = 'en'

# This needs to be updated every time a new language is added to spyder, and is
# used by the Preferences configuration to populate the Language QComboBox
LANGUAGE_CODES = {'en': 'English',
                  'fr': 'Français'}

# Disabled languages (because their translations are outdated)
DISABLED_LANGUAGES = []


def get_available_translations():
    """
    Return a list of available translations for Sardes based on the content
    found in the locale folder.
    """
    listdir = os.listdir(LOCALE_PATH)

    langs = [d for d in listdir if osp.isdir(osp.join(LOCALE_PATH, d))]
    langs = [DEFAULT_LANGUAGE] + langs

    # Remove disabled languages
    langs = list(set(langs) - set(DISABLED_LANGUAGES))

    return sorted(langs)


def get_lang_conf():
    """
    Get and return from the user config file the language that should be used
    in the gui .
    """
    lang = CONF.get('main', 'language')

    # Save language again if it's been disabled.
    if lang in DISABLED_LANGUAGES:
        lang = DEFAULT_LANGUAGE
        set_lang_conf(lang)
    return lang


def set_lang_conf(lang):
    """
    Save in the user config file the language that should be used in the gui.
    """
    lang = CONF.set('main', 'language', lang)


def get_translation():
    """Return translation callback for module *modname*"""
    lang = get_lang_conf()
    import gettext
    try:
        translation = gettext.translation(
            'sardes', LOCALE_PATH, languages=[lang])
        return translation.gettext
    except Exception:
        return lambda x: x


# Translation callback
_ = get_translation()
