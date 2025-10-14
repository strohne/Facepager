# How to build Facepager
## Windows 10

Setup Facepager to run in your environment using venv, see src/readme.md

Install software
- Install NSIS (https://sourceforge.net/projects/nsis/)
- Install pyinstaller and pywin32:
  ```
  pip install pyinstaller
  pip install pywin32
  ```

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


## macOS Tahoe (v26.0.1)

Setup Facepager to run with venv, see src/readme.md.

Install software:

- Activate venv. Make sure to use the right version of pip (`venv/bin/pip`) by checking the version:
  ```
  source venv/bin/activate
  pip -V
  ```
- Install pyinstaller and upx (optional):
  ```
  pip install pyinstaller
  brew install upx
  ```
- Install Xcode

The following steps can alternatively be executed with build/osx/build.pyinstaller.command.
Double click build.pyinstaller.command in Finder or execute in terminal.

- Copy Facepager.spec to src folder. Before you proceed, please, duplicate Facepager.default.spec and rename it to Facepager.spec. Note that it contains the argument `codesign_identity = 'PUT_HASH_OF_HASH_OF_INSTALLER_ID_HERE'` and has `upx = True` in both Analysis and EXE sections. If you do not have upx installed, set `upx = False` in both sections.
If you do not plan to codesign your build, simply remove the argument. See [bpteague's PyInstaller recipe for codesigning an OSX .app bundle](https://gist.github.com/bpteague/750906b9a02094e7389427d308ba1002) for reference on how to obtain the hash key as well as how to store an Apple Developer certificate in `notarytool`.
  ```
  cd src
  cp ../build/osx/Facepager.spec .
  ```

- Remove old build files:
  ```
  rm -rf build
  rm -rf dist
  ```

- Run pyinstaller from src directory. Note that Facepager.spec contains settings to
  ```
  pyinstaller Facepager.spec
  ```

- [Only if you are codesigning the app] Codesign app and make sure signature is valid:
  ```
  codesign -vv --strict Facepager.app
  ```

- Check if Facepager starts and fix errors:
  ```
  open ./dist/Facepager.app
  ```

### Packaging and notarization

- Apple only notarizes `.pkg`, `.dmg`, and `.zip` files. Hence we must compress our build before submitting. To do so, run:
  ```
  ditto -c -k --sequesterRsrc --keepParent Facepager.app Facepager.zip
  ```
- Notarize the zip file:
  ```
  xcrun notarytool submit Facepager.app --keychain-profile fpcodesign22 --wait
  ```
- Staple the notarization ticket to the app and verify that the notarization was successful:
  ```
  xcrun stapler staple Facepager.app
  spctl -a -v Facepager.app
  ```

- Now we can create the final installer package. Run the following command from the project's root directory:
  ```
  productbuild --identifier "com.strohne.facepager.pkg" \
    --sign "PUT_HASH_OF_HASH_OF_INSTALLER_ID_HERE" \
    --timestamp \
    --root src/dist/Facepager.app /Applications/Facepager.app \
    Facepager_Setup_4_7_0.mac.pkg
  ```

- Notarize the installer package and, again, staple the notarization ticket to the package and verify that the notarization was successful:
  ```
  xcrun notarytool submit Facepager_Setup_4_7_0.mac.pkg --keychain-profile fpcodesign22 --wait
  xcrun stapler staple Facepager_Setup_4_7_0.mac.pkg
  spctl -a -vv -t install Facepager_Setup_4_7_0.mac.pkg
  pkgutil --check-signature Facepager_Setup_4_7_0.mac.pkg
  ```

See for further information:
- https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution#Notarize-your-preexisting-software
- https://developer.apple.com/documentation/security/customizing-the-notarization-workflow#Upload-your-app-to-the-notarization-service.

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

- Create a git tag on the command line with `git tag -a v4.7.0 -m "Version 4.7.0"`
- Upload the tag to GitHib with `git push origin v4.7.0`
- For major releases draft a new release on GitHub, for minor releases edit the last release.
- Enter the tag into the corresponding field, edit release notes, upload binary files.
