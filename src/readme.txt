#
#  General notes
#

Facepager is developed for Python 2.7

Facepager depends on the following packages:

PySide: Download from https://qt-project.org/wiki/Category:LanguageBindings::PySide::Downloads (Licence: LGPL)
SQLAlchemy: pip install SQLAlchemy (Licence: MIT)
dateutil: pip install python-dateutil (PSF License)
requests: pip install requests (Apache2 License)
rauth: pip install rauth (MIT licence)
numpy and pandas: pip install numpy pandas

Facepager needs some secret keys to connect to Facebook and Twitter.
See credentials.py.readme for further details.


########
#
#  Steps to run under linux
#  (tested under ubuntu vivid x64, thx to crsqq / Christoph Martin) 
#
########


git clone https://github.com/strohne/Facepager
cd Facepager

sudo apt-get install build-essential git cmake libqt4-dev libphonon-dev python2.7-dev libxml2-dev libxslt1-dev qtmobility-dev python-virtualenv

virtualenv facepager_env
. facepager_env/bin/activate

pip install SQLAlchemy python-dateutil requests rauth wheel
cd src/

#you may want to change the download link to the most recent version
wget https://pypi.python.org/packages/source/P/PySide/PySide-1.2.2.tar.gz
extract PySide-1.2.2.tar.gz 
cd PySide-1.2.2/


python2.7 setup.py bdist_wheel --qmake=/usr/bin/qmake-qt4

../pacepager_env/bin/pip2.7 install dist/PySide-1.2.2-cp27-none-linux_x86_64.whl 

#add your credentials
cp credentials.py.readme credentials.py
python Facepager.py 


#######
#
#  Steps to run under Windows Subsystem for Linux (Windows 10)
#
#  Commands to run in bash are marked with $ sign 
#
########

#
# 1. Prepare bash
#

	# Install WSL, see https://msdn.microsoft.com/de-de/commandline/wsl/install_guide
	# Install Xming X Server to run graphical apps, see https://askubuntu.com/questions/823352/windows-10-bash-cannot-connect-to-display and  http://www.pcworld.com/article/3055403/windows/windows-10s-bash-shell-can-run-graphical-linux-applications-with-this-trick.html
	# Start bash: windows key, type "bash"
	# Enable QuickEdit-Mode, this way you can copy&paste commands from this file to the terminal by mouse right click: click on Ubunutu icon in topleft corner of terminal window, click "Properties", "Options", "QuickEdit-Mode"; for further information see http://stackoverflow.com/questions/38832230/copy-paste-in-bash-on-ubuntu-on-windows
	# Create a directory to work in, directories under /mnt/ will be shared between windows and linux, e.g.

	$ mkdir /mnt/c/FacepagerLinux
	$ cd /mnt/c/FacepagerLinux

#
# 2. Install dependencies and setup Python environment
#

	$ sudo apt-get install build-essential git cmake libqt4-dev libphonon-dev python2.7-dev libxml2-dev libxslt1-dev qtmobility-dev python-virtualenv

	$ virtualenv facepager_env
	$ . facepager_env/bin/activate
	$ pip install SQLAlchemy python-dateutil requests rauth wheel

	# The following commands take a long time, press return if terminal seems to hang
	$ pip install pyside
	$ pip install numpy pandas

#
# 3. Install and run Facepager
#

	$ cd /mnt/c/FacepagerLinux
	$ git clone https://github.com/strohne/Facepager
	$ cd Facepager/src
	$ cp credentials.py.readme credentials.py

	# Don't forget to manually add your credentials in credentials.py

	#Activate x server
	$ export DISPLAY=:0

	#Run Facepager
	$ python Facepager.py 



#######
#
#   Steps to run under OSX El Capitan in VMWare
#
#	tested in virtual machine with VMware Workstation 12 Player under windows 10
#   see http://techsviewer.com/how-to-install-mac-os-x-el-capitan-on-vmware-on-pc/
#
#######


0. Install OSX in virtual machine
Follow the steps in http://techsviewer.com/how-to-install-mac-os-x-el-capitan-on-vmware-on-pc/
Edit virtual machine, in Network Adapter section set network connection to "Bridged" instead of "NAT"


1.Prepare system
1.1 Install python 2.7 from python.org. This gives you a Python folder under Applications, containing the Python Launcher
[1.2 Maybe optional: update PIP by running get-pip.py (see http://pyside.readthedocs.io/en/latest/installing/macosx.html)]
1.3 Install homebrew, type in terminal:
	
	/usr/bin/ruby/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

	
2.Install packages

2.1 Install PySide, type in terminal:		

	brew install qt
	brew install PySide	
	
	[Check the output, replace USERNAME by your username in the following command]
	
	mkdir -p /Users/USERNAME/Library/Python/2.7/lib/python/site-packages
	echo 'import site; site.addsitedir("/usr/local/lib/python2.7/site-packages")' >> /Users/USERNAME/Library/Python/2.7/lib/python/site-packages/homebrew.pth
	
2.2. Install other packages, type in terminal:

	pip install SQLAlchemy
	pip install python-dateutil
	pip install requests
	pip install rauth
	pip install pandas
	

3. Install Facepager

    - Download from github or clone (https://github.com/strohne/Facepager.git)
    
	- To clone via https open terminal and run the following commands:
	  (could fail in virtual machine, workaround is to install GitHub Desktop? better way: bridge network in vwware player instead of nat)
	  (adjust folder name if neccessary)
	  
	    $ cd Documents
	    $ git clone https://github.com/strohne/Facepager.git
  	  
	  
    - Create credentials.py (see above)

4. Launch Facepager.py (with python launcher, not in terminal)
