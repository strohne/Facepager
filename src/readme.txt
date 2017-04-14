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
pandas and numpy:   pip install numpy,  pip install pandas


Facepager needs some secret keys to connect to Facebook and Twitter.
See credentials.py.readme for further details.


#
#  Steps to run under linux
#  (tested under ubuntu vivid x64, thx to crsqq / Christoph Martin) 
#


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


#
#   Steps to run under OSX El Capitan
#
#	tested in virtual machine under windows 10, see 
#	http://techsviewer.com/how-to-install-mac-os-x-el-capitan-on-vmware-on-pc/
#



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
	
	
3. Create credentials.py (see above)

4. Launch Facepager.py (with python launcher, not in terminal)

	