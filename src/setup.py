from cx_Freeze import setup, Executable



includes = ["sqlite3","facebook"]



setup(
        name = "Facepager",
        version = "0.1",
        description = "The Facebook Page Crawler",
        options = {'build_exe': {'includes':includes,"packages":["sqlalchemy","sqlalchemy.dialects.sqlite","zlib"],}},
        executables = [Executable(script="Facepager.py",base="Win32GUI",copyDependentFiles = True)])