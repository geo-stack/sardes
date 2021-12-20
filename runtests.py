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
    args = ['-x', 'sardes', '-v', '-rw', '--durations=10',
            '--cov=sardes', '-o', 'junit_family=xunit2']
    if os.environ.get('Azure', None) is not None:
        args.append('--no-coverage-upload')
    errno = pytest.main(args)
    if errno != 0:
        raise SystemExit(errno)


if __name__ == '__main__':
    main()
