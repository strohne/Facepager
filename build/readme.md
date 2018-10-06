# How to build Facepager
## Windows

Setup Facepager to run in your environment, see src/readme.txt

Install NSIS

Adjust paths and version numbers in
- src/setup_windows.py
- Facepager_Setupscript.nsi
- build.bat

Run build.bat

## OS X El Capitan and High Sierra

Setup Facepager to run in your environment, see src/readme.txt

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

Previously, Facepager was built using py2app. Here are the old instructions:

Adjust paths and version numbers in
- src/setup_osx.py
- build.command

Run build.command by double clicking in Finder or in terminal

Hints for solving errors:
- Test  alias mode:
	python setup_osx.py py2app -A
- After running py2app run the built from command line or double click, e.g. from
  ~/Documents/GitHub/Facepager/dist/Facepager.app/Contents/MacOS/Facepager
- Run in interactive mode and open debugger, see
  https://stackoverflow.com/questions/16131500/py2app-error-in-find-needed-modules-typeerror-nonetype-object-has-no-attribu

  $ python -i setup.py py2app
  $ from pdb import pm; pm()
  
  "Type up and hit enter - you are now a frame higher in the stack - you can type list to see where in the source code the current frame is positioned, and args to see the arguments passed to the current frame (usually a function or method). You can also run python commands to inspect the current state, and run pp var to pretty-print that variable."



# How to deploy builds

_Don't forget to adjust the tag name and message below_

- Create a git tag on the command line with `git tag -a v3.9.2 -m 'Version 3.9.2'`
- Upload the tag to GitHib with `git push origin v3.9.2`
- For major releases draft a new release on GitHub, for minor releases edit the last release.
- Enter the tag into the corresponding field, edit release notes, upload binary files.