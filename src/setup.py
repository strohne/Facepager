#on command line: python setup.py build


from cx_Freeze import setup, Executable

includes = ["sqlite3","facebook","xlwt","dateutil"]


exe = Executable(
        script="Facepager.py",
        base="Win32GUI",
        icon="../icons/icon_facepager.ico",
        copyDependentFiles = True,
        targetDir="build"    
        )

setup(
        name = "Facepager",
        version = "2.0",
        description = "The Facebook Page Crawler",
        options = {'build_exe': {'includes':includes,"packages":["sqlalchemy","sqlalchemy.dialects.sqlite","zlib","dateutil"],}},
        executables = [exe]
        )


