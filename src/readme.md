# General notes

Facepager 4 is developed for Python 3.7 (32 bit) and PySide2 (Qt5)

Facepager depends on the following packages:

- PySide: Download from https://qt-project.org/wiki/Category:LanguageBindings::PySide::Downloads (Licence: LGPL)
- SQLAlchemy: pip install SQLAlchemy (Licence: MIT)
- dateutil: pip install python-dateutil (PSF License)
- requests: pip install requests (Apache2 License)
- requests_oauthlib: pip install requests_oauthlib (ISC License, equivalent to the BSD 2-Clause and MIT licenses)
- requests[security]: pip install -U requests[security]==2.7.0
- requests-toolbelt pip install requests-toolbelt (Licence: Apache 2.0)
- rauth: pip install rauth (MIT licence)
- numpy and pandas: pip install numpy pandas
- lxml: pip install lxml

Facepager needs some secret keys to connect to Facebook and Twitter.
See credentials.py.readme for further details. You can provide the credentials in this file or in the user interface, as you like.

# Steps to runder under Windows 10

$ pip install PySide2
$ pip install numpy pandas


$ git clone https://github.com/strohne/Facepager
$ cd Facepager
$ cp credentials.py.readme credentials.py
$ python Facepager.py 