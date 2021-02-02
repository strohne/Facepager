# General notes

Facepager 4 is developed for Python 3.7 (64 bit) and PySide2 (Qt5)

Facepager depends on the following packages:

- PySide2: pip install PySide2==5.15.2 (Licence LGPLv3/GPLv2)
- SQLAlchemy: pip install SQLAlchemy (Licence: MIT)
- dateutil: pip install python-dateutil (PSF License)
- requests: pip install requests (Apache2 License)
- requests_oauthlib: pip install requests_oauthlib (ISC License, equivalent to the BSD 2-Clause and MIT licenses)
- requests[security]: pip install -U requests[security]==2.7.0
- requests[socks]: pip install -U requests[socks]
- requests-toolbelt pip install requests-toolbelt (Licence: Apache 2.0)
- rauth: pip install rauth (MIT licence)
- numpy and pandas: pip install numpy pandas (licensed under BSD and 3-clause BSD license) 
- lxml: pip install lxml (BSD licence)
- xmljson pip install xmljson (MIT licence)
- cchardet: pip install cchardet (GPL, LGPL, MPL 1.1)
- json
- cssselect
- datetime
- pyjsparser: pip install pyjsparser (MIT)
- tldextract

Facepager needs some secret keys to connect to Facebook, Twitter and YouTube. You can provide the credentials in the user interface or in an credential file. See credentials.py.readme for further details. 

The right version of PySide2 matters. Not every version includes the WebEngineWidgets module. For example, there is no version working out of the box for Windows 32bit.

# Steps to runder under Windows 10

Install Python3 64bit: https://www.python.org/downloads/windows/
Make sure python.exe are in the path. See https://docs.python.org/3/using/windows.html#using-on-windows for further details.

Open the command line in a directory of your choice and execute the comments indicated by the $ sign

- Clone Facepager  
  $ git clone https://github.com/strohne/Facepager  
  $ cd Facepager

- Setup Python environment  
  $ python -m venv pyenv  
  $ pyenv\Scripts\activate.bat  
  
  $ pip install SQLAlchemy python-dateutil requests_oauthlib requests-toolbelt rauth lxml xmljson numpy pandas cchardet pyjsparser tldextract cssselect  
  $ pip install PySide2==5.15.2

- Start Facepager  
  $ cd src  
  $ python Facepager.py  

# Steps to runder under macOS High Sierra

Open terminal in a directory of your choice and execute the commands indicated by the $ sign.

- Clone Facepager  
   $ git clone https://github.com/strohne/Facepager  
   $ cd Facepager  

- Setup Python environment  
  $ python3 -m venv pyenv  
  $ source pyenv/bin/activate  
  
  $ pip install SQLAlchemy python-dateutil requests_oauthlib requests-toolbelt rauth lxml xmljson numpy pandas cchardet pyjsparser tldextract cssselect  
  $ pip install PySide2==5.15.2 

- Start Facepager  
  $ cd src  
  $ python Facepager.py  

# Steps to runder under Ubuntu 18.04.1 LTS

Open terminal in a directory of your choice and execute the commands indicated by the $ sign.

- Install additional software:  
   $ sudo apt install git  
   $ sudo apt-get install python3-venv  

- Clone Facepager  
   $ git clone https://github.com/strohne/Facepager  
   $ cd Facepager  

- Setup Python environment  
  $ python3 -m venv pyenv  
  $ source pyenv/bin/activate  
  
  $ pip3 install SQLAlchemy python-dateutil requests_oauthlib requests-toolbelt rauth lxml xmljson numpy pandas cchardet pyjsparser tldextract cssselect   
  $ pip3 install PySide2==5.15.2

- Start Facepager  
  $ cd src  
  $ python3 Facepager.py  
  
Remember: you can provide default credentials for Facebook, Twitter and YouTube in the credentials.py. See credentials.py.readme for further details.
