# How to build Facepager
## Windows 10

Setup Facepager to run in your environment using venv, see src/readme.md

Install software
- Install NSIS (https://sourceforge.net/projects/nsis/)
- Install pyinstaller and pywin32:  
  `$ pip install pyinstaller`  
  `$ pip install pywin32`  

- Run build/windows/build.bat

- Rename resulting installer file

__Hints for solving errors:__

- Create the build from scr-directory in folder-mode and with console option:  

  pyinstaller --log-level=WARN --name "Facepager" --console --add-binary "../build/windows/PySide2;PySide2" --icon "../icons/icon_facepager.ico" Facepager.py  
	 
  If everthing works, replace option "--console" with "--windowed" and create new spec file by replacing pyinstaller with pyi-makespec:  
  
  pyi-makespec --log-level=WARN --name "Facepager" --windowed --add-data "ssl;ssl" --add-binary "../build/windows/PySide2;PySide2" --icon "../icons/icon_facepager.ico" Facepager.py  
  
 - Copy the following folders and files to dist folder (or any other missing files):
	PySide2/resources  
	PySide2/translations  
	PySide2/QtWebEngineProcess.exe  
	PySide2/qt.conf	

- See https://pyinstaller.readthedocs.io
- See https://justcode.nimbco.com/PyInstaller-with-Qt5-WebEngineView-using-PySide2/ for PySide2 issues

    
## macOS High Sierra

Setup Facepager to run with venv, see src/readme.md. 

Install software:
- Go to the src folder of Facepager and activate venv. Make sure to use the right version of pip (`pyenv/bin/pip`) by checking the version.  
  $ source ../pyenv/bin/activate  
  $ pip -V
  
- Install pyinstaller  and upx (optional)
  $ pip install pyinstaller  
  $ brew install upx  

The following steps can alternatively be executed with build/osx/build.pyinstaller.command. 
Double click build.pyinstaller.command in Finder or execute in terminal.

- Copy Facepager.spec to src folder:  
  $ cp ../build/osx/Facepager.spec Facepager.spec

- Fix pyinstaller problem with PySide2 (copy hooks folder to src folder):  
  $ cp -r ../build/osx/hooks hooks

- Remove old build files:  
  $ rm -rf build  
  $ rm -rf dist  

- Run pyinstaller:  
  $ pyinstaller --windowed --noconfirm --upx-dir=/usr/local/bin/ Facepager.spec  

- Check if Facepager starts and fix errors:  
  $ ./dist/Facepager/Facepager

- Create package  
  $ cd dist  
  $ zip -r Facepager.app.zip Facepager.app  
  $ cp Facepager.app.zip ../../build/osx/Facepager_4.app.zip  


## Code signing and packaging

See https://gist.github.com/txoof/0636835d3cc65245c6288b2374799c43

### Get certificates
- Create an Apple Developer Account
- Login to your account and create two certificates (Account -> Identifiers & Profiles): 1. Installer outside AppStore, 2. Application outside AppStore. Download the certificates and install them in the login KeyChain

### Sign the app
- Unpack the Facepager.zip or directly use the dist folder 
- Fix PySide folder structure, see https://github.com/pyinstaller/pyinstaller/wiki/Recipe-OSX-Code-Signing-Qt. 
  sudo pip3 install macholib  
  python3 fix_app_qt_folder_names_for_codesign.py Facepager.app

- Create the entitlements.plist anlegen, see https://gist.github.com/txoof/0636835d3cc65245c6288b2374799c43
- Find the developer hashes:  
  security find-identity -p basic -v
- Codesign with the application hash:  
  codesign --deep --force --options=runtime --entitlements ./entitlements.plist --sign "C5675C9047BC5F500D88849509790AEEBCB99534" --timestamp ./Facepager.app

### Create package


productbuild --identifier "com.strohne.facepager.pkg" --sign "AC630C1E0415944E2C2DCDE3210ADC5C8F20A02E" --timestamp --root ./Facepager.app /Applications/Facepager.app Facepager.pkg


## Notarize
**Not working yet.**
You need altoll which comes with Xcode. Alternatively, download "Transporter.app" from the app store. You will find altos in /Applications/Transporter.app/Contents/Frameworks/ContentDeliveryServices.framework/Versions/A/Frameworks/AppStoreService.framework/Versions/A/Support/altool

(To find a file: sudo find /Applications -name altool -print)

Create a password item in KeyChain, name it Developer-altool and set the app specific password

xcrun /Applications/Transporter.app/Contents/Frameworks/ContentDeliveryServices.framework/Versions/A/Frameworks/AppStoreService.framework/Versions/A/Support/altool --notarize-app --primary-bundle-id "com.strohne.facepager" --username="jakob.juenger@uni-muenster.de" --password "@keychain:Developer-altool" --file ./Facepager.pkg --verbose



__Hints for solving errors:__

- Remove all system wide installations of PySide2: "PyInstaller will pick a system installation of PySide2 or Shiboken2 instead of your virtualenv version without notice, if it exists" (https://doc.qt.io/qtforpython/deployment-pyinstaller.html).
  Make sure to uninstall with pip as well as pip3: 
  $ pip uninstall pyside2 shiboken2 -y  
  $ pip3 uninstall pyside2 shiboken2 -y  

- PyInstaller may not be up to date with PySide2. At the time of this writing the following worked: https://justcode.nimbco.com/PyInstaller-with-Qt5-WebEngineView-using-PySide2/  
  In src/hooks you find a manually adjusted hook. This hook was adapted from the default PyQt-hook of pyinstaller (replace PyQt with PySide2).
  In Facepager.py you find a hack to get QtWebEngineProcess working. 
  Maybe in the meantime it works without these hacks. Then remove.

-  When using pyenv: "You would need to specify PYTHON_CONFIGURE_OPTS="--enable-shared" when building a Python version for PyInstaller" (https://github.com/pyinstaller/pyinstaller/wiki/FAQ)

- Grant execute permissions to build.pyinstallercommand by typing in terminal:  
  $chmod a+rwx build.pyinstaller.command

- If dyld-error comes up (check and adjust path if necessary):  
  $ export DYLD_LIBRARY_PATH=/usr/local/lib/python3.7/site-packages/PySide2

- Create the build from scr-directory in folder-mode:  

	pyinstaller --log-level=WARN --name "Facepager" --console --add-data "docs:docs" --add-data "ssl:ssl" --noupx --icon "icon.icns" Facepager.py  

	If everthing works, replace option "--console" with "--windowed" and create new spec file by replacing pyinstaller with pyi-makespec.

- To show hidden files execute in terminal, then Alt+RightClick Finder and choose "Relaunch"  
  $ defaults write com.apple.finder AppleShowAllFiles YES

- To edit files install text editor, e.g. sublime text		

## Ubuntu 18.04.1 LTS

__Notice: this does not work yet, needs further testing__

Setup Facepager to run in your environment, see src/readme.md.  
When using venv make sure to use `bin/pip` instead of `pip` in the following steps.  

- Install software  
  `$ pip install pyinstaller`
  `$ sudo apt-get install python3-dev` 

__Hints for solving errors:__

- See https://pyinstaller.readthedocs.io

- Create the build from scr-directory in folder-mode and with console option:

   pyinstaller --log-level=WARN --name "Facepager" --console --add-data "docs:docs" --add-data "ssl:ssl" --icon "../icons/icon_facepager.ico" Facepager.py
	 
  If everthing works, replace option "--console" with "--windowed" and create new spec file by replacing pyinstaller with pyi-makespec:
  
   pyi-makespec --log-level=WARN --name "Facepager" --windowed --add-data "docs;docs" --add-data "ssl;ssl" --add-binary "../build/windows/PySide2;PySide2" --icon "../icons/icon_facepager.ico" Facepager.py

- Manually copy PySide2 folder into dist folder 
	
# Version numbers

If drafting a new version adjust version numbers in:  
- src/Facepager.py

# SSL
SSL certificates come from the certifi package included in the requests library. Update before building:
`pip install certifi --upgrade`


# How to deploy builds

_Don't forget to adjust the tag name and message below_

- Create a git tag on the command line with `git tag -a v4.6.1 -m "Version 4.6.1"`
- Upload the tag to GitHib with `git push origin v4.6.1`
- For major releases draft a new release on GitHub, for minor releases edit the last release.
- Enter the tag into the corresponding field, edit release notes, upload binary files.
