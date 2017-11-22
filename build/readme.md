# How to build Facepager
## Windows

Setup Facepager to run in your environment, see src/readme.txt

Install NSIS

Adjust paths and version numbers in
- src/setup_windows.py
- Facepager_Setupscript.nsi
- build.bat

Run build.bat

## OS X El Capitan

Setup Facepager to run in your environment, see src/readme.txt

Adjust paths and version numbers in
- src/setup_osx.py
- build.command

Grant execute permissions to build.command by typing in terminal:
  $chmod a+rwx build.command

To show hidden files execute in terminal, then Alt+RightClick Finder and choose "Relaunch"
    $defaults write com.apple.finder AppleShowAllFiles YES

To edit files install text editor, e.g. sublime text	
Run build.command by double clicking in Finder or in terminal
