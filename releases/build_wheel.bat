cd ..
call .venv\Scripts\activate.bat
python setup.py --quiet sdist bdist_wheel
pause
