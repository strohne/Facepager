from cx_Freeze import setup, Executable



includes = ["sqlite3","facebook","xlwt","dateutil"]



setup(
        name = "Facepager",
        version = "1.1",
        description = "The Facebook Page Crawler",
        options = {'build_exe': {'includes':includes,"packages":["sqlalchemy","sqlalchemy.dialects.sqlite","zlib","dateutil"],}},
        executables = [Executable(script="Facepager.py",base="Win32GUI",icon="icon_facepager.ico",copyDependentFiles = True)])
