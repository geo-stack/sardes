# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""Installation script """

import setuptools
from setuptools import setup
from sardes import __version__, __project_url__
import csv


DESCRIPTION = "Suivi, analyse et représentation de données d’eau souterraine."

with open('requirements.txt', 'r') as csvfile:
    INSTALL_REQUIRES = list(csv.reader(csvfile))
INSTALL_REQUIRES = [item for sublist in INSTALL_REQUIRES for item in sublist]

with open('requirements-dev.txt', 'r') as csvfile:
    DEV_INSTALL_REQUIRES = list(csv.reader(csvfile))
DEV_INSTALL_REQUIRES = [
    item for sublist in DEV_INSTALL_REQUIRES for item in sublist]

EXTRAS_REQUIRE = {
    'dev': DEV_INSTALL_REQUIRES,
    'build': ['pyinstaller==4.9', 'tornado']
    }

PACKAGE_DATA = {
    'sardes': ['ressources/icons/*.png',
               'ressources/icons/*.svg',
               'ressources/sardes_splash.png',
               'ressources/sardes_banner.png',
               'locale/fr/LC_MESSAGES/*.mo']
    }


setup(name='sardes',
      version=__version__,
      description=DESCRIPTION,
      license='MIT',
      author='Jean-Sébastien Gosselin',
      author_email='jean-sebastien.gosselin@outlook.ca',
      url=__project_url__,
      ext_modules=[],
      packages=setuptools.find_packages(),
      package_data=PACKAGE_DATA,
      include_package_data=True,
      install_requires=INSTALL_REQUIRES,
      extras_require=EXTRAS_REQUIRE,
      classifiers=["Programming Language :: Python :: 3",
                   "License :: OSI Approved :: MIT License",
                   "Operating System :: OS Independent"],
      )
