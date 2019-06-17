# -*- mode: python -*-
import shutil
import subprocess
import os
from sardes import __version__
from sardes.utils.fileio import delete_folder_recursively

block_cipher = None

added_files = [('../sardes/ressources/icons/*.png',
                '../sardes/ressources/icons/*.svg',
                'ressources/icons')]

a = Analysis(['../sardes/app/mainwindow.py'],
             pathex=['C:\\Program Files (x86)\\Windows Kits\\10\\Redist\\ucrt\\DLLs\\x64'],
             binaries=[],
             datas=added_files ,
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
          console=True,
          icon='sardes.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='Sardes')

# Prepare the binary folder.
shutil.copyfile("../LICENSE", "dist/LICENSE")
if os.environ.get('AZURE'):
    output_dirname = os.environ.get('SARDES_OUTPUT_DIRNAME')
else:
    output_dirname = 'sardes'+__version__+'_win_amd64'
delete_folder_recursively(output_dirname, delroot=True)
os.rename('dist', output_dirname)
