# How to build Facepager
## Windows 10

Setup Facepager to run in your environment, see src/readme.md

Install software
- Install NSIS (https://sourceforge.net/projects/nsis/)
- Install pyinstaller and pywin32:
  `$ pip install pyinstaller`
  `$ pip install pywin32`

Adjust paths and version numbers in
- src/Facepager.py
- Facepager.spec
- Facepager_Setupscript.nsi
- build.bat

Run build.bat


Hints for solving errors:

- See https://pyinstaller.readthedocs.io

- Create the build from scr-directory in folder-mode and with console option:

   pyinstaller --log-level=WARN --name "Facepager" --windowed --add-data "docs;docs" --add-data "ssl;ssl" --add-binary "../build/windows/PySide2;PySide2" --icon "../icons/icon_facepager.ico" Facepager.py
	 
  If everthing works, replace option "--console" with "--windowed" and create new spec file by replacing pyinstaller with pyi-makespec:
  
   pyi-makespec --log-level=WARN --name "Facepager" --windowed --add-data "docs;docs" --add-data "ssl;ssl" --add-binary "../build/windows/PySide2;PySide2" --icon "../icons/icon_facepager.ico" Facepager.py
  
  
 - Copy the following folders and files to dist folder:
	PySide2/resources
	PySide2/translations
	PySide2/QtWebEngineProcess.exe
	PySide2/qt.conf	
		
## OS X El Capitan and High Sierra

Setup Facepager to run in your environment, see src/readme.md

Install pyinstaller:
	$ pip install pyinstaller
	
Install upx (optional)
	$ brew install upx

Adjust paths and version numbers in build.pyinstaller.command

Run build.pyinstaller.command by double clicking in Finder or execute in terminal

[Obsolete: You can set the icon of the unix distributable by right clicking -> get info -> drag icon.icns file to top left corner.]

Hints for solving errors:

- Grant execute permissions to build.pyinstallercommand by typing in terminal:
  $chmod a+rwx build.pyinstaller.command

- If dyld-error comes up (check and adjust path if necessary):
  $ export DYLD_LIBRARY_PATH=/usr/local/lib/python2.7/site-packages/PySide

- Create the build from scr-directory in folder-mode:

	pyinstaller --log-level=WARN  \
	    --name "Facepager" \
	    --windowed \
	    --add-data "docs:docs" \
	    --add-data "ssl:ssl" \
	    --noupx \
	    --icon "icon.icns" \
	    Facepager.py 

	If everthing works create new spec file by replacing pyinstaller with pyi-makespec

- To show hidden files execute in terminal, then Alt+RightClick Finder and choose "Relaunch"
    $defaults write com.apple.finder AppleShowAllFiles YES

- To edit files install text editor, e.g. sublime text		


# How to deploy builds

_Don't forget to adjust the tag name and message below_

- Create a git tag on the command line with `git tag -a v3.9.2 -m 'Version 3.9.2'`
- Upload the tag to GitHib with `git push origin v3.9.2`
- For major releases draft a new release on GitHub, for minor releases edit the last release.
- Enter the tag into the corresponding field, edit release notes, upload binary files.