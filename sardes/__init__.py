# -*- coding: utf-8 -*-

"""
Sardes License Agreement (GNU-GPLv3)
--------------------------------------

Copyright (c) INRS
https://github.com/cgq-qgc/sardes

Sardes is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>
"""

import os
import sys


version_info = (0, 13, 1)
__version__ = '.'.join(map(str, version_info))
__appname__ = 'Sardes'
__namever__ = __appname__ + " " + __version__
__date__ = '05/04/2023'
__project_url__ = "https://github.com/cgq-qgc/sardes"
__releases_url__ = __project_url__ + "/releases"
__issues_url__ = __project_url__ + "/issues"
__releases_api__ = "https://api.github.com/repos/cgq-qgc/sardes/releases"


def get_versions(reporev=True):
    """
    Get version information for components used by Sardes

    This function is derived from code that was borrowed from the Spyder
    project, licensed under the terms of the MIT license.
    https://github.com/spyder-ide
    """
    import sys
    import platform

    import qtpy
    import qtpy.QtCore

    # To avoid a crash with Mac app
    if not sys.platform == 'darwin':
        system = platform.system()
    else:
        system = 'Darwin'

    return {
        'version': __version__,
        'python': platform.python_version(),
        'bitness': 64 if sys.maxsize > 2**32 else 32,
        'qt': qtpy.QtCore.__version__,
        'qt_api': qtpy.API_NAME,
        'qt_api_ver': qtpy.PYQT_VERSION,
        'system': system,
        'release': platform.release()}


def is_frozen():
    """
    Return whether the application is running from a frozen exe or if it
    is running from the Python source files.

    See: https://stackoverflow.com/a/42615559/4481445
    """
    return getattr(sys, 'frozen', False)


if is_frozen():
    __rootdir__ = sys._MEIPASS
else:
    __rootdir__ = os.path.dirname(os.path.realpath(__file__))
