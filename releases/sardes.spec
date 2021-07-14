# -*- mode: python -*-
import shutil
import subprocess
import os
from sardes import __version__
from sardes.utils.fileio import delete_folder_recursively

block_cipher = None

added_files = [('../sardes/ressources/icons/*.png', 'ressources/icons'),
               ('../sardes/ressources/icons/*.svg', 'ressources/icons'),
               ('../sardes/ressources/sardes_splash.png', 'ressources'),
               ('../sardes/ressources/sardes_banner.png', 'ressources'),
               ('../sardes/locale/fr/LC_MESSAGES/*.mo', 'locale/fr/LC_MESSAGES')]
a = Analysis(['../sardes/app/mainwindow.py'],
             pathex=['C:\\Program Files (x86)\\Windows Kits\\10\\Redist\\ucrt\\DLLs\\x64'],
             binaries=[('C:\\Windows\\System32\\vcruntime140_1.dll', '.')],
             datas=added_files ,
             hiddenimports=[
                 'win32timezone', 'sqlalchemy.ext.baked', 'PIL.BmpImagePlugin',
                 'PIL.Jpeg2KImagePlugin', 'PIL.JpegImagePlugin',
                 'PIL.PngImagePlugin', 'PIL.TiffImagePlugin',
                 'PIL.WmfImagePlugin', 'pkg_resources.py2_warn'
                 ],
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
          console=False,
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
