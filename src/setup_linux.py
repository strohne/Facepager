import sys
from cx_Freeze import setup, Executable

includes = ["sqlite3","dateutil","atexit","PySide.QtNetwork"]
includefiles = ['presets/','docs/']

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {'includes':includes,"packages": ["sqlalchemy","sqlalchemy.dialects.sqlite","zlib","dateutil"], 'include_files':includefiles}

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(  name = "Facepager",
        version = "3.6",
        description = "Facebook Page Crawler",
        options = {"build_exe": build_exe_options},
        executables = [Executable("Facepager.py", base=base, copyDependentFiles = True)])
