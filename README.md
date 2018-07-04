![Logo](https://raw.github.com/strohne/Facepager/master/icons/icon_facepager.png)

Facepager was made for fetching public available data from Facebook, Twitter and other JSON-based API. 
All data is stored in a SQLite database and may be exported to csv. 

### Installer

Installation packages for each versions are available on the [releases page](https://github.com/strohne/Facepager/releases). Database files may be incompatible between versions.

- Windows: Download and execute the latest installer from the [releases page](https://github.com/strohne/Facepager/releases).
- Mac OS X: Unzipp the file from the [releases page](https://github.com/strohne/Facepager/releases), drag & drop the App to your "Applications" folder. When a warning about the the source pop's up you should allow the installation of non-app-store applications (go to "System Preferrences>Security & Privacy" and check "Anywhere"). If you do not want to change your security settings permanently, you may open the Facepager by CTRL+Click on the icon (each time on startup).
- Linux: There is no binary release, see src/readme.txt for steps to run under linux.

### Getting help

Try the [help button](http://strohne.github.io/Facepager/) built into Facepager or directly go to the [Wiki](https://github.com/strohne/Facepager/wiki). There you find everything to get you started.

You can get help regarding specific problems in the [Facepager Usergroup on Facebook](https://www.facebook.com/groups/136224396995428/). If you want to be informed about updates please follow the [Facebook Page](https://www.facebook.com/groups/136224396995428/).


### Getting started

1.	**Create a database**: click `New Database` in the Menu Bar](https://github.com/strohne/Facepager/wiki/Layout#menu-bar).
2.	**Login to Facebook**: In the Facebook tab of the [Query Setup](https://github.com/strohne/Facepager/wiki/Layout#query-setup) click on `Login to Facebook` to get a valid access token. Notice: the [Access Token](https://github.com/strohne/Facepager/wiki/OpenAuthorization-and-Access-Token) is like a password to Facebook. Since it may be printed in the status log and saved in the application settings don't give anyone untrusted access to your computer or to the status log.
3.	**Add nodes**: Add Facebook IDs by clicking `Add Nodes` in the Menu Bar. Enter the last part of a Facebook page, e.g. enter "Uni.Greifswald.de" for the page "https://www.facebook.com/Uni.Greifswald.de" or enter "TheAcademy" for the page "https://www.facebook.com/TheAcademy". 
4.	**Setup query**: Type `https://graph.facebook.com/v3/` into the Base path field of the Query Setup. Type `<Object ID>` into the Resource field.	Delete any Parameters. Then add just one parameter: the term `fields` goes into the left side, the term `name,category,fan_count,birthday` goes into the right side. See https://developers.facebook.com/docs/graph-api/reference/page/ for other fields if you like.
7.	**Fetch data**: select one or more nodes in the [Nodes View](https://github.com/strohne/Facepager/wiki/Layout#nodes-view) and click `Fetch data`. Look at the Status Log (make sure "Log all requests" was enabled) to see how the URL is assembled from your settings.
8.	**Inspect data**: Expand your node or click `Expand nodes` in the Menu Bar to open all nodes. Select one of the new child nodes. The raw data is shown in the [Data View](https://github.com/strohne/Facepager/wiki/Layout#data-view) to the right.
9.	**Setup columns**: Click `Clear Column Setup` below the "Custom Table Columns" area. Change the Column Setup according to your needs by adding keys found in the raw data into the "Custom Table Columns" area. You can use `Add Column` after you clicked on the specific key or just use `Add All Columns`. Don't forget to click `Apply Column Setup` in the [Column Setup](https://github.com/strohne/Facepager/wiki/Layout#column-setup) to add them in the Nodes View. If the columns don't show up make sure to scroll right or to resize the columns (click between the headers).
10. **Export data**: Click [`Export Data`](https://github.com/strohne/Facepager/wiki/Export-Data) to get a CSV file. Notice the options in the export mode field of the export dialog. You can open CSV files with Excel oder any statistics software you like.
	
10. For further information, click the "help" button and try the default presets.



### Citation

[Jünger, Jakob](https://ipk.uni-greifswald.de/kommunikationswissenschaft/dr-jakob-juenger/) / [Keyling, Till](http://tillkeyling.com/) (2017). Facepager. An application for generic data retrieval through APIs. Source code and releases available at https://github.com/strohne/Facepager/.

### Licence


MIT License

Copyright (c) 2017 Jakob Jünger and Till Keyling

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

