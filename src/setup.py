#on command line: python setup.py build

import sys
from cx_Freeze import setup, Executable

exe = Executable(
        script="Facepager.py",
        base="Win32GUI",
        icon="../icons/icon_facepager.ico",
        copyDependentFiles = True,
        targetDir="build"
        )

includes = ["sqlite3","facebook","dateutil","atexit","PySide.QtNetwork"]



buildoptions = {
  'includes':includes,
  "packages":["sqlalchemy","sqlalchemy.dialects.sqlite","zlib","dateutil"]
}

setup(
        name = "Facepager 3",
        version = "3.0",
        description = "The Facebook Page Crawler",
        options = {'build_exe': buildoptions},
        executables = [exe]
        )


