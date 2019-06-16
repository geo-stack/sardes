# -*- mode: python -*-
import shutil
import subprocess
import os
from sardes import __version__
from sardes.utils.fileio import delete_folder_recursively

block_cipher = None

a = Analysis(['../sardes/app/mainwindow.py'],
             pathex=['C:\\Program Files (x86)\\Windows Kits\\10\\Redist\\ucrt\\DLLs\\x64'],
             binaries=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=['PySide', 'PyQt4'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='sardes',
          debug=False,
          strip=False,
          upx=True,
          console=True)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='Sardes')

# Prepare the binary folder.
shutil.copyfile("../LICENSE", "dist/LICENSE")
output_dirname = 'sardes'+__version__+'_win_amd64'
delete_folder_recursively(output_dirname, delroot=True)
os.rename('dist', output_dirname)
os.environ['SARDES_DIRNAME'] = output_dirname
