#on command line: python setup.py build

import sys
from cx_Freeze import setup, Executable

exe = Executable(
        script="Facepager.py",
        base="Win32GUI",
        icon="../icons/icon_facepager.ico",
        copyDependentFiles = True,
        targetDir="build",
        compress=True,
        appendScriptToExe=True,
        appendScriptToLibrary=False
        )

includes = ["sqlite3","dateutil","atexit","PySide.QtNetwork"]
includefiles = ['docs/','ssl/']


buildoptions = {
  'includes':includes,
  "packages":["sqlalchemy","sqlalchemy.dialects.sqlite","zlib","dateutil","requests","requests_oauthlib"],
  'excludes' : ["collections.abc"],
  'include_files':includefiles
}

setup(
        name = "Facepager 3",
        version = "3.10",
        description = "Facepager was made for fetching public available data from Facebook, Twitter and other JSON-based APIs.",
        options = {'build_exe': buildoptions},
        executables = [exe]
        )


