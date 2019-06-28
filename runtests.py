# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

"""
File for running tests programmatically.
"""

import os
os.environ['SARDES_PYTEST'] = 'True'

import pytest


def main():
    """
    Run pytest tests.
    """
    errno = pytest.main(['-x', 'sardes', '-v', '-rw', '--durations=10',
                         '--cov=sardes', '-s'])
    if errno != 0:
        raise SystemExit(errno)


if __name__ == '__main__':
    main()
