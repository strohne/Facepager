![Logo](https://raw.github.com/strohne/Facepager/master/icons/icon_facepager.png)

Facepager was made for fetching public available data from YouTube, Twitter and other websites on the basis of APIs and webscraping. All data is stored in a SQLite database and may be exported to csv. 

### Installer

Installation packages for each version are available on the [releases page](https://github.com/strohne/Facepager/releases). Database files may be incompatible between versions.

- **Windows**: Download and execute the latest exe-installer from the [releases page](https://github.com/strohne/Facepager/releases). If Windows complains about an unknown publisher and refuses to launch the app click "More info" and start anyway.
- **Mac OS X**: Download and install the latest package from the [releases page](https://github.com/strohne/Facepager/releases). Your computer will complain that it can't install the package. Ctrl+Click on the installer icon to bypass the complaint, see https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unidentified-developer-mh40616/mac for further information.  
  Older versions of Facepager were distributed in zip files and not code signed. Download and unzip the file from the releases page, drag & drop the app to your "Applications" folder. Next, you need to disable the download flag. Open the terminal, go to the folder where Facepager is stored (e.g. `cd /Applications`) and use `xattr -cr Facepager.app` to remove the download flag. Then open the app using ctrl-click.

- **Linux**: There is no binary release, see [src/readme.md](https://github.com/strohne/Facepager/blob/master/src/readme.md) for steps to run under linux.

If you want to run from source, see [src/readme.md](https://github.com/strohne/Facepager/blob/master/src/readme.md).

### Getting help

Try the help button built into Facepager or directly go to the [Wiki](https://github.com/strohne/Facepager/wiki). There you find everything to [get you started](https://github.com/strohne/Facepager/wiki/Getting-Started). Further, you will find some [Tutorials on YouTube](https://www.youtube.com/channel/UCiIbKv5b5rz-6LPTLQgVGug).

You can get help regarding specific problems in the [Facepager Usergroup on Facebook](https://www.facebook.com/groups/136224396995428/). If you want to be informed about updates please follow the [Facebook Page](https://www.facebook.com/facepagerpage).


### Citation

[Jünger, Jakob](https://www.uni-muenster.de/Kowi/personen/jakob-juenger.html) / [Keyling, Till](http://tillkeyling.com/) (2019). Facepager. An application for automated data retrieval on the web. Source code and releases available at https://github.com/strohne/Facepager/.

### Licence


MIT License

Copyright (c) 2019 Jakob Jünger and Till Keyling

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

