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