# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

import subprocess
import sys
import os.path as osp

# Run pygettext.py.
python_dir = osp.dirname(osp.abspath(sys.executable))
pygettext_path = osp.join(python_dir, 'Tools', 'i18n', 'pygettext.py')

sardes_dir = osp.dirname(osp.dirname(osp.abspath(__file__)))
pot_filepath = osp.join(sardes_dir, 'sardes', 'locale', 'sardes')

output = subprocess.run(
    ["python", pygettext_path, '-d', pot_filepath, sardes_dir],
    capture_output=True
    )
print(output)

# Make sure the pot file is encoded in utf-8.
with open(pot_filepath + '.pot', 'r') as potfile:
    text = potfile.read()
text = text.replace('charset=cp1252', 'charset=utf-8')
with open(pot_filepath + '.pot', 'w', encoding='utf-8') as potfile:
    potfile.write(text)
