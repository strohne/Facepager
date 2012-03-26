from cx_Freeze import setup, Executable


includefiles = ['../data']
includes = ["sqlite3","facebook"]



setup(
        name = "Facepager",
        version = "0.1",
        description = "The Facebook Page Crawler",
        options = {'build_exe': {'includes':includes,"packages":["sqlalchemy","sqlalchemy.dialects.sqlite"],'include_files':includefiles}},
        executables = [Executable(script="main.py",copyDependentFiles = True)])