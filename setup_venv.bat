python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install wheel
python -m pip install -e ../sardes[dev,build]
python -m pip install spyder-kernels==2.2.*
pause
