import urlparse
import urllib
from mimetypes import guess_all_extensions
from datetime import datetime
import re
import os
import sys
import time
from collections import OrderedDict
import threading

from PySide.QtWebKit import QWebView, QWebPage
from PySide.QtGui import QMessageBox
from PySide.QtCore import QUrl

import requests
from requests.exceptions import *
from rauth import OAuth1Service
from requests_oauthlib import OAuth2Session

import dateutil.parser

from paramedit import *

from utilities import *
from credentials import *


class ApiTab(QWidget):
    """
    Generic API Tab Class
        - handles URL-Substitutions
        - saves current Settings
    """

    streamingData = Signal(list, list, list)

    def __init__(self, mainWindow=None, name="NoName"):
        QWidget.__init__(self, mainWindow)
        self.timeout = None
        self.mainWindow = mainWindow
        self.name = name
        self.connected = False
        self.lastrequest = None
        self.speed = None
        self.loadDocs()
        self.lock_session = threading.Lock()

    def idtostr(self, val):
        """
         Return the Node-ID as a string
        """
        return unicode(val).encode("utf-8")

    def parseURL(self, url):
        """
        Parse any url and return the query-strings and base bath
        """
        url = url.split('?', 1)
        path = url[0]
        query = url[1] if len(url) > 1 else ''
        query = urlparse.parse_qsl(query)
        query = OrderedDict((k, v) for k, v in query)

        return path, query

    def parsePlaceholders(self,pattern,nodedata,paramdata={}):
        if not pattern:
            return pattern

        matches = re.findall(ur"<([^>]*)>", pattern)
        for match in matches:
            if match in paramdata:
                value = paramdata[match]
            elif match == 'None':
                value = ''
            elif match == 'Object ID':
                value = unicode(nodedata['objectid'])
            else:
                value = getDictValue(nodedata['response'], match)

            pattern = pattern.replace('<' + match + '>', value)

        return pattern

    def getURL(self, urlpath, params, nodedata):
        """
        Replaces the Facepager placeholders ("<",">" of the inside the query-Parameter
        by the Object-ID or any other Facepager-Placeholder
        Example: http://www.facebook.com/<Object-ID>/friends
        """
        urlpath, urlparams = self.parseURL(urlpath)

        #Replace placeholders in params and collect template params
        templateparams = {}
        for name in params:
            #Filter empty params
            if (name == '<None>') or (params[name] == '<None>') or (name == ''):
                continue

            # Set the value for the ObjectID or any other placeholder-param
            if params[name] == '<Object ID>':
                value = unicode(nodedata['objectid'])
            else:
                match = re.match(ur"^<(.*)>$", unicode(params[name]))
                if match:
                    value = getDictValue(nodedata['response'], match.group(1))
                else:
                    value = params[name]

            #check for template params
            match = re.match(ur"^<(.*)>$", unicode(name))
            if match:
                templateparams[match.group(1)] = value
            else:
                urlparams[name] = unicode(value).encode("utf-8")

        #Replace placeholders in urlpath
        urlpath = self.parsePlaceholders(urlpath, nodedata, templateparams)

        return urlpath, urlparams


    def getOptions(self, purpose='fetch'): #purpose = 'fetch'|'settings'|'preset'
        return {}

    def setOptions(self, options):
        if options.has_key('client_id'):
            self.clientIdEdit.setText(options.get('client_id',''))
        if 'access_token' in options:
            self.tokenEdit.setText(options.get('access_token', ''))
        if 'access_token_secret' in options:
            self.tokensecretEdit.setText(options.get('access_token_secret', ''))
        if options.has_key('consumer_key'):
            self.consumerKeyEdit.setText(options.get('consumer_key',''))
        if options.has_key('consumer_secret'):
            self.consumerSecretEdit.setText(options.get('consumer_secret',''))

    def saveSettings(self):
        self.mainWindow.settings.beginGroup("ApiModule_" + self.name)
        options = self.getOptions('settings')

        for key in options.keys():
            self.mainWindow.settings.setValue(key, options[key])
        self.mainWindow.settings.endGroup()

    def loadSettings(self):
        self.mainWindow.settings.beginGroup("ApiModule_" + self.name)

        options = {}
        for key in self.mainWindow.settings.allKeys():
            options[key] = self.mainWindow.settings.value(key)
        self.mainWindow.settings.endGroup()
        self.setOptions(options)

    @Slot(str)
    def logMessage(self,message):
        self.mainWindow.logmessage(message)

    def loadDocs(self):
        '''
        Loads and prepares documentation
        '''

        try:
            folder = os.path.join(getResourceFolder(),'docs')
            filename = u"{0}.json".format(self.__class__.__name__)

            with open(os.path.join(folder, filename),"r") as docfile:
                if docfile:
                    self.apidoc = json.load(docfile)
                else:
                    self.apidoc = None
        except:
            self.apidoc = None

    def initInputs(self,basepath = None):
        '''
        Create base path edit, resource edit and param edit
        Set resource according to the APIdocs, if any docs are available
        '''

        self.mainLayout = QFormLayout()
        self.mainLayout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        self.mainLayout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.mainLayout.setLabelAlignment(Qt.AlignLeft)
        self.setLayout(self.mainLayout)

        #Base path
        self.basepathEdit = QComboBox(self)
        if not basepath is None:
            self.basepathEdit.insertItems(0, [basepath])
        self.basepathEdit.setEditable(True)
        self.mainLayout.addRow("Base path", self.basepathEdit)

        #Resource
        self.resourceEdit = QComboBox(self)
        self.mainLayout.addRow("Resource", self.resourceEdit)

        if self.apidoc:
            #Insert one item for every endpoint
            for endpoint in reversed(self.apidoc):
                #store url as item text
                self.resourceEdit.insertItem(0, endpoint["path"])
                #store doc as tooltip
                self.resourceEdit.setItemData(0, endpoint["doc"], Qt.ToolTipRole)
                #store params-dict for later use in onChangedRelation
                self.resourceEdit.setItemData(0, endpoint.get("params",[]), Qt.UserRole)

        self.resourceEdit.setEditable(True)

        #Parameters
        self.paramEdit = QParamEdit(self)
        self.mainLayout.addRow("Parameters", self.paramEdit)
        self.resourceEdit.currentIndexChanged.connect(self.onchangedRelation)
        self.onchangedRelation()


    @Slot()
    def onchangedRelation(self,index=0):
        '''
        Handles the automated parameter suggestion for the current
        selected API relation/endpoint
        '''
        #retrieve param-dict stored in initInputs-method
        params = self.resourceEdit.itemData(index,Qt.UserRole)

        #Set name options and build value dict
        values = {}
        nameoptions = []
        if params:
            for param in params:
                if param["required"]==True:
                    nameoptions.append(param)
                    values[param["name"]] = param["default"]
                else:
                    nameoptions.insert(0,param)
        nameoptions.insert(0,{})
        self.paramEdit.setNameOptions(nameoptions)

        #Set value options
        self.paramEdit.setValueOptions([{'name':'',
                                         'doc':"No Value"},
                                         {'name':'<Object ID>',
                                          'doc':"The value in the Object ID-column of the datatree."}])

        #Set values
        self.paramEdit.setParams(values)

    @Slot()
    def onChangedParam(self,index=0):
        pass

    def initSession(self):
        with self.lock_session:
            if not hasattr(self, "session"):
                self.session = requests.Session()
        return self.session

    def request(self, path, args=None, headers=None, method="get", jsonify=True):
        """
        Start a new threadsafe session and request
        """

        #Throttle speed
        if (self.speed is not None) and (self.lastrequest is not None):
            pause = ((60 * 1000) / float(self.speed)) - self.lastrequest.msecsTo(QDateTime.currentDateTime())
            while (self.connected) and (pause > 0):
                time.sleep(0.1)
                pause = ((60 * 1000) / float(self.speed)) - self.lastrequest.msecsTo(QDateTime.currentDateTime())

        self.lastrequest = QDateTime.currentDateTime()

        session = self.initSession()
        if (not session):
            raise Exception("No session available.")

        try:
            maxretries = 3
            while True:
                try:
                    if method == "post":  #headers is not None
                        response = session.post(path, params=args, headers=headers, timeout=self.timeout, verify=False)
                    else:
                        response = session.get(path, params=args,headers=headers, timeout=self.timeout, verify=False)
                except (HTTPError, ConnectionError), e:
                    maxretries -= 1
                    if maxretries > 0:
                        time.sleep(0.1)
                        self.logMessage(u"Automatic retry: Request Error: {0}".format(e.message))
                    else:
                        raise e
                else:
                    break

        except (HTTPError, ConnectionError), e:
            raise Exception(u"Request Error: {0}".format(e.message))
        else:
            if jsonify == True:
                if not response.json():
                    raise Exception("Request Format Error: No JSON data!")

                else:
                    status = 'fetched' if response.ok else 'error'
                    status = status + ' (' + str(response.status_code) + ')'
                    return response.json(), dict(response.headers.items()), status
            else:
                return response

    def disconnectSocket(self):
        """Used to disconnect when canceling requests"""
        self.connected = False


    @Slot()
    def doLogin(self, query=False, caption='', url=''):
        """
        Create a SSL-capable WebView for the login-process
        Uses a Custom QT-Webpage Implementation
        Supply a getToken-Slot to fetch the API-Token
        """

        self.doQuery = query
        window = QMainWindow(self.mainWindow)
        window.resize(800, 800)
        window.setWindowTitle(caption)

        #create WebView with Facebook log-Dialog, OpenSSL needed
        self.login_webview = QWebView(window)
        window.setCentralWidget(self.login_webview )

        # Use the custom- WebPage class
        webpage = QWebPageCustom(self)
        webpage.logmessage.connect(self.logMessage)
        self.login_webview.setPage(webpage);

        #Connect to the getToken-method
        self.login_webview.urlChanged.connect(self.getToken)
        webpage.urlNotFound.connect(self.getToken) #catch redirects to localhost or nonexistent uris

        # Connect to the loadFinished-Slot for an error message
        self.login_webview.loadFinished.connect(self.loadFinished)

        self.login_webview.load(QUrl(url))
        #self.login_webview.resize(window.size())
        self.login_webview.show()

        window.show()

    @Slot()
    def loadFinished(self, success):
        if (not success):
            self.logMessage('Error loading web page')


    def download(self, path, args=None, headers=None, foldername=None, filename=None, fileext=None):
        """
        Download files ...
        Uses the request-method without converting to json
        (argument jsonify==True)
        """

        def makefilename(foldername=None, filename=None, fileext=None,appendtime = False):  # Create file name
            url_filename, url_fileext = os.path.splitext(os.path.basename(path))
            if fileext is None:
                fileext = url_fileext
            if not filename:
                filename = url_filename

            filename = re.sub(ur'[^a-zA-Z0-9_.-]+', '', filename)
            fileext = re.sub(ur'[^a-zA-Z0-9_.-]+', '', fileext)

            filetime = time.strftime("%Y-%m-%d-%H-%M-%S")
            filenumber = 0

            while True:
                newfilename = filename[:100]
                if appendtime:
                    newfilename += '.' + filetime
                if filenumber > 0:
                    newfilename += '-' + str(filenumber)

                newfilename += str(fileext)
                fullfilename = os.path.join(foldername,newfilename)

                if (os.path.isfile(fullfilename)):
                    filenumber = filenumber + 1
                else:
                    break

            return fullfilename

        try:
            response = self.request(path, args, headers, jsonify=False)

            # Handle the response of the generic, non-json-returning response
            if response.status_code == 200:
                if fileext is None:
                    guessed_ext = guess_all_extensions(response.headers["content-type"])
                    fileext = guessed_ext[-1] if len(guessed_ext) > 0 else None

                fullfilename = makefilename(foldername, filename, fileext)
                with open(fullfilename, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                data = {'filename': os.path.basename(fullfilename), 'filepath': fullfilename, 'sourcepath': path,'sourcequery': args}
                status = 'downloaded' + ' (' + str(response.status_code) + ')'
            else:
                try:
                    data = {'sourcepath': path, 'sourcequery': args,'response':response.json()}
                except:
                    data = {'sourcepath': path, 'sourcequery': args,'response':response.text}

                status = 'error' + ' (' + str(response.status_code) + ')'
        except Exception, e:
            raise Exception(u"Download Error: {0}".format(e.message))
        else:
            return data, dict(response.headers), status

    def selectFolder(self):
        datadir = self.mainWindow.settings.value('lastpath', os.path.expanduser('~'))
        self.folderEdit.setText(
            QFileDialog.getExistingDirectory(self, 'Select Download Folder', datadir, QFileDialog.ShowDirsOnly))

class FacebookTab(ApiTab):
    def __init__(self, mainWindow=None, loadSettings=True):
        super(FacebookTab, self).__init__(mainWindow, "Facebook")

        # Query Box
        self.initInputs(credentials['facebook']['basepath'])

        # Pages Box
        self.pagesEdit = QSpinBox(self)
        self.pagesEdit.setMinimum(1)
        self.pagesEdit.setMaximum(50000)

        # Login-Boxes
        self.tokenEdit = QLineEdit()
        self.tokenEdit.setEchoMode(QLineEdit.Password)
        self.loginButton = QPushButton(" Login to Facebook ", self)
        self.loginButton.clicked.connect(self.doLogin)

        self.clientIdEdit = QLineEdit()
        self.clientIdEdit.setEchoMode(QLineEdit.Password)
        self.scopeEdit = QLineEdit()

        # Construct Login-Layout
        loginlayout = QHBoxLayout()
        loginlayout.addWidget(self.tokenEdit)
        loginlayout.addWidget(self.loginButton)


        applayout = QHBoxLayout()
        applayout.addWidget(self.clientIdEdit)
        applayout.addWidget(QLabel("Scope"))
        applayout.addWidget(self.scopeEdit)


        # Add to main-Layout
        self.mainLayout.addRow("Maximum pages", self.pagesEdit)
        self.mainLayout.addRow("Client Id", applayout)
        self.mainLayout.addRow("Access Token", loginlayout)

        if loadSettings:
            self.loadSettings()


    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {'resource': self.resourceEdit.currentText(),
                   'pages': self.pagesEdit.value(),
                   'params': self.paramEdit.getParams()}

        options['scope'] = self.scopeEdit.text()
        options['basepath'] = self.basepathEdit.currentText()
        #options['folder'] = self.folderEdit.text()

        # options for request
        if purpose != 'preset':
            options['querytype'] = self.name + ':' + self.resourceEdit.currentText()
            options['access_token'] = self.tokenEdit.text()
            options['client_id'] = self.clientIdEdit.text()


        # options for data handling
        if purpose == 'fetch':
            options['objectid'] = 'id'
            options['nodedata'] = 'data' if ('/' in options['resource']) or (options['resource'] == 'search') else None

        return options

    def setOptions(self, options):
        #define default values
        if options.get('basepath','') == '':
            options['basepath'] = credentials['facebook']['basepath']

        #set values
        self.resourceEdit.setEditText(options.get('resource', '<Object ID>'))
        self.pagesEdit.setValue(int(options.get('pages', 1)))

        self.basepathEdit.setEditText(options.get('basepath'))
        self.scopeEdit.setText(options.get('scope'))
        self.paramEdit.setParams(options.get('params', {}))

        # set Access-tokens,use generic method from APITab
        super(FacebookTab, self).setOptions(options)

    def fetchData(self, nodedata, options=None, callback=None, logCallback=None):
    # Preconditions
        if options['access_token'] == '':
            raise Exception('Access token is missing, login please!')
        self.connected = True
        self.speed = options.get('speed',None)

        # Abort condition for time based pagination
        since = options['params'].get('since', False)
        if (since != False):
            since = dateutil.parser.parse(since, yearfirst=True, dayfirst=False)
            since = int((since - datetime(1970, 1, 1)).total_seconds())

        # Abort condition: maximum page count
        for page in range(0, options.get('pages', 1)):
        # build url
            if not ('url' in options):
                urlpath = options["basepath"] + options['resource']
                urlparams = {}

#                 if options['resource'] == 'search':
#                     urlparams['q'] = self.idtostr(nodedata['objectid'])
#                     urlparams['type'] = 'page'
#                 elif options['resource'] == '<Object ID>':
#                     urlparams['metadata'] = '1'
#
#                 elif '<Object ID>/' in options['resource']:
#                     urlparams['limit'] = '100'

                urlparams.update(options['params'])

                urlpath, urlparams = self.getURL(urlpath, urlparams, nodedata)
                urlparams["access_token"] = options['access_token']
            else:
                urlpath = options['url']
                urlparams = options['params']

            if options['logrequests']:
                logCallback(u"Fetching data for {0} from {1}".format(nodedata['objectid'],
                                                                                   urlpath + "?" + urllib.urlencode(
                                                                                       urlparams)))

            # data
            options['querytime'] = str(datetime.now())
            data, headers, status = self.request(urlpath, urlparams,jsonify=True)

            if (status != "fetched (200)"):
                msg = getDictValue(data,"error.message")
                code = getDictValue(data,"error.code")
                logCallback(u"Error '{0}' for {1} with message {2}.".format(status, nodedata['objectid'],msg))

                #see https://developers.facebook.com/docs/graph-api/using-graph-api
                if (code in [4,17,341]) and (status == "error (400)"):
                    status = "rate limit (400)"

            options['querystatus'] = status
            callback(data, options, headers)

            # paging
            if hasDictValue(data, 'paging.next'):
                url, params = self.parseURL(getDictValue(data, 'paging.next', False))

                # abort time based pagination
                until = params.get('until', False)
                if (since != False) and (until != False) and (int(until) < int(since)):
                    break

                options['params'] = params
                options['url'] = url
            else:
                break

            if not self.connected:
                break


    @Slot()
    def doLogin(self, query=False, caption="Facebook Login Page",url=""):
        #use credentials from input if provided
        facebookclientid = self.clientIdEdit.text() if self.clientIdEdit.text() != "" else credentials['facebook']['client_id']
        scope= self.scopeEdit.text() if self.scopeEdit.text() != "" else credentials['facebook']['scope']
        url = credentials['facebook']['auth_uri'] +"?client_id=" + facebookclientid + "&redirect_uri="+credentials['facebook']['redirect_uri']+"&response_type=token&scope="+scope+"&display=popup"

        super(FacebookTab, self).doLogin(query, caption, url)

    @Slot(QUrl)
    def getToken(self,url):
        if url.toString().startswith(credentials['facebook']['redirect_uri']):
            url = urlparse.parse_qs(url.toString())
            token = url.get(credentials['facebook']['redirect_uri']+"#access_token",[''])

            self.tokenEdit.setText(token[0])
            self.login_webview.parent().close()


class TwitterTab(ApiTab):
    def __init__(self, mainWindow=None, loadSettings=True):
        super(TwitterTab, self).__init__(mainWindow, "Twitter")


        # Query and Parameter Box
        self.initInputs(credentials['twitter']['basepath'])

        # Pages-Box
        self.pagesEdit = QSpinBox(self)
        self.pagesEdit.setMinimum(1)
        self.pagesEdit.setMaximum(50000)

        # LogIn Box
        self.tokenEdit = QLineEdit()
        self.tokenEdit.setEchoMode(QLineEdit.Password)
        self.tokensecretEdit = QLineEdit()
        self.tokensecretEdit.setEchoMode(QLineEdit.Password)
        self.loginButton = QPushButton(" Login to Twitter ", self)
        self.loginButton.clicked.connect(self.doLogin)
        self.consumerKeyEdit = QLineEdit()
        self.consumerKeyEdit.setEchoMode(QLineEdit.Password)
        self.consumerSecretEdit = QLineEdit()
        self.consumerSecretEdit.setEchoMode(QLineEdit.Password)


        # Construct login layout
        credentialslayout = QHBoxLayout()
        credentialslayout.addWidget(self.consumerKeyEdit)
        credentialslayout.addWidget(QLabel("Consumer Secret"))
        credentialslayout.addWidget(self.consumerSecretEdit)

        loginlayout = QHBoxLayout()
        loginlayout.addWidget(self.tokenEdit)
        loginlayout.addWidget(QLabel("Access Token Secret"))
        loginlayout.addWidget(self.tokensecretEdit)
        loginlayout.addWidget(self.loginButton)

        # Construct main-Layout
        self.mainLayout.addRow("Maximum pages", self.pagesEdit)
        self.mainLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.mainLayout.addRow("Consumer Key", credentialslayout)
        self.mainLayout.addRow("Access Token", loginlayout)

        if loadSettings:
            self.loadSettings()

        # Twitter OAUTH consumer key and secret should be defined in credentials.py
        self.oauthdata = {}
        self.twitter = OAuth1Service(
            consumer_key=credentials['twitter']['consumer_key'],
            consumer_secret=credentials['twitter']['consumer_secret'],
            name='twitter',
            access_token_url=credentials['twitter']['access_token_url'],
            authorize_url=credentials['twitter']['authorize_url'],
            request_token_url=credentials['twitter']['request_token_url'],
            base_url=credentials['twitter']['basepath'])


    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {'basepath' : self.basepathEdit.currentText(),
                   'resource': self.resourceEdit.currentText(),
                   'params': self.paramEdit.getParams(),
                   'pages': self.pagesEdit.value()}

        # options for request
        if purpose != 'preset':
            options['querytype'] = self.name + ':' + self.resourceEdit.currentText()
            options['access_token'] = self.tokenEdit.text()
            options['access_token_secret'] = self.tokensecretEdit.text()
            options['consumer_key'] = self.consumerKeyEdit.text()
            options['consumer_secret'] = self.consumerSecretEdit.text()

        # options for data handling
        if purpose == 'fetch':
            #options['basepath'] =  "https://api.twitter.com/1.1/"
            options['objectid'] = 'id'

            if options["resource"] == 'search/tweets':
                options['nodedata'] = 'statuses'
            elif options["resource"] == 'followers/list':
                options['nodedata'] = 'users'
            elif options["resource"] == 'followers/ids':
                options['nodedata'] = 'ids'
            elif options["resource"] == 'friends/list':
                options['nodedata'] = 'users'
            else:
                options['nodedata'] = None

        return options


    def setOptions(self, options):
        self.resourceEdit.setEditText(options.get('resource', 'search/tweets'))
        self.basepathEdit.setEditText(options.get('basepath', credentials['twitter']['basepath']))
        self.paramEdit.setParams(options.get('params', {'q': '<Object ID>'}))
        self.pagesEdit.setValue(int(options.get('pages', 1)))

        # set Access-tokens,use generic method from APITab
        super(TwitterTab, self).setOptions(options)

    def initSession(self):
        if hasattr(self, "session"):
            return self.session

        elif (self.tokenEdit.text() != '') and (self.tokensecretEdit.text() != ''):
            self.twitter.consumer_key = self.consumerKeyEdit.text() if self.consumerKeyEdit.text() != "" else credentials['twitter']['consumer_key']
            self.twitter.consumer_secret = self.consumerSecretEdit.text() if self.consumerSecretEdit.text() != "" else credentials['twitter']['consumer_secret']
            self.twitter.base_url = self.basepathEdit.currentText() if self.basepathEdit.currentText() != "" else credentials['twitter']['basepath']

            self.session = self.twitter.get_session((self.tokenEdit.text(), self.tokensecretEdit.text()))
            return self.session

        else:
            raise Exception("No access, login please!")


    def fetchData(self, nodedata, options=None, callback=None,logCallback=None):
        self.connected = True
        self.speed = options.get('speed',None)

        for page in range(0, options.get('pages', 1)):
            if not ('url' in options):
                urlpath = options["basepath"] + options["resource"] + ".json"
                urlpath, urlparams = self.getURL(urlpath, options["params"], nodedata)
            else:
                urlpath = options['url']
                urlparams = options["params"]

            if options['logrequests']:
                logCallback(u"Fetching data for {0} from {1}".format(nodedata['objectid'],
                                                                               urlpath + "?" + urllib.urlencode(
                                                                                   urlparams)))

            # data
            data, headers, status = self.request(urlpath, urlparams,jsonify=True)
            options['querytime'] = str(datetime.now())
            options['querystatus'] = status

            callback(data, options, headers)

            paging = False
            if isinstance(data,dict) and hasDictValue(data, "next_cursor_str") and (data["next_cursor_str"] != "0"):
                paging = True
                options['params']['cursor'] = data["next_cursor_str"]

            # paging with next-results; Note: Do not rely on the search_metadata information, sometimes the next_results param is missing, this is a known bug
            elif isinstance(data,dict) and hasDictValue(data, "search_metadata.next_results"):
                paging = True
                url, params = self.parseURL(getDictValue(data, "search_metadata.next_results", False))
                options['url'] = urlpath
                options['params'] = params

            # manual paging with max-id
            # if there are still statuses in the response, use the last ID-1 for further pagination
            elif isinstance(data,list) and (len(data) > 0):
                options['params']['max_id'] = int(data[-1]["id"])-1
                paging = True

#             elif isinstance(data,dict) and hasDictValue(data, options['nodedata']+".*.id"):
#                 newnodes = getDictValue(data,options['nodedata'],False)
#                 if (type(newnodes) is list) and (len(newnodes) > 0):
#                     options['params']['max_id'] = int(newnodes[-1]['id'])-1
#                     paging = True

            if not paging:
                break

            if not self.connected:
                break

    @Slot()
    def doLogin(self, query=False, caption="Twitter Login Page", url=""):
        try:
            self.twitter.consumer_key = self.consumerKeyEdit.text() if self.consumerKeyEdit.text() != "" else credentials['twitter']['consumer_key']
            self.twitter.consumer_secret = self.consumerSecretEdit.text() if self.consumerSecretEdit.text() != "" else credentials['twitter']['consumer_secret']

            self.oauthdata.pop('oauth_verifier', None)
            self.oauthdata['requesttoken'], self.oauthdata['requesttoken_secret'] = self.twitter.get_request_token(
                verify=False)

            # calls the doLogin-method of the parent
            super(TwitterTab, self).doLogin(query, caption, self.twitter.get_authorize_url(self.oauthdata['requesttoken']))
        except Exception as e:
            QMessageBox.critical(self, "Login canceled",
                                            u"Login canceled. Check you Consumer Key and Consumer Secret. Error Message: {0}".format(e.message),
                                            QMessageBox.StandardButton.Ok)




    @Slot()
    def getToken(self):
        url = urlparse.parse_qs(self.login_webview.url().toString())
        if "oauth_verifier" in url:
            token = url["oauth_verifier"]
            if token:
                self.oauthdata['oauth_verifier'] = token[0]
                self.session = self.twitter.get_auth_session(self.oauthdata['requesttoken'],
                                                             self.oauthdata['requesttoken_secret'], method="POST",
                                                             data={'oauth_verifier': self.oauthdata['oauth_verifier']},
                                                             verify=False)

                self.tokenEdit.setText(self.session.access_token)
                self.tokensecretEdit.setText(self.session.access_token_secret)

                self.login_webview.parent().close()


class TwitterStreamingTab(ApiTab):
    def __init__(self, mainWindow=None, loadSettings=True):
        super(TwitterStreamingTab, self).__init__(mainWindow, "Twitter Streaming")

        # Query Box
        self.initInputs(credentials['twitter_streaming']['basepath'])

        # Construct Log-In elements
        self.tokenEdit = QLineEdit()
        self.tokenEdit.setEchoMode(QLineEdit.Password)
        self.tokensecretEdit = QLineEdit()
        self.tokensecretEdit.setEchoMode(QLineEdit.Password)
        self.loginButton = QPushButton(" Login to Twitter ", self)
        self.loginButton.clicked.connect(self.doLogin)
        self.consumerKeyEdit = QLineEdit()
        self.consumerKeyEdit.setEchoMode(QLineEdit.Password)
        self.consumerSecretEdit = QLineEdit()
        self.consumerSecretEdit.setEchoMode(QLineEdit.Password)

        # Construct login-Layout
        loginlayout = QHBoxLayout()

        loginlayout.addWidget(self.tokenEdit)
        loginlayout.addWidget(QLabel("Access Token Secret"))
        loginlayout.addWidget(self.tokensecretEdit)
        loginlayout.addWidget(self.loginButton)

        credentialslayout = QHBoxLayout()
        credentialslayout.addWidget(self.consumerKeyEdit)
        credentialslayout.addWidget(QLabel("Consumer Secret"))
        credentialslayout.addWidget(self.consumerSecretEdit)


        # Add to main-Layout
        self.mainLayout.addRow("Consumer Key", credentialslayout)
        self.mainLayout.addRow("Access Token", loginlayout)

        if loadSettings:
            self.loadSettings()

        # Twitter OAUTH consumer key and secret should be defined in credentials.py
        self.oauthdata = {}
        self.twitter = OAuth1Service(
            consumer_key=credentials['twitter']['consumer_key'],
            consumer_secret=credentials['twitter']['consumer_secret'],
            name='twitterstreaming',
            access_token_url=credentials['twitter']['access_token_url'],
            authorize_url=credentials['twitter']['authorize_url'],
            request_token_url=credentials['twitter']['request_token_url'],
            base_url='https://stream.twitter.com/1.1/')
        self.timeout = 60
        self.connected = False


    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {'basepath': self.basepathEdit.currentText(),
                   'resource': self.resourceEdit.currentText(),
                   'params': self.paramEdit.getParams()}
        # options for request

        if purpose != 'preset':
            options['querytype'] = self.name + ':' + self.resourceEdit.currentText()
            options['access_token'] = self.tokenEdit.text()
            options['access_token_secret'] = self.tokensecretEdit.text()
            options['consumer_key'] = self.consumerKeyEdit.text()
            options['consumer_secret'] = self.consumerSecretEdit.text()


        # options for data handling
        if purpose == 'fetch':
            options['objectid'] = 'id'
            if options["resource"] == 'search/tweets':
                options['nodedata'] = 'statuses'
            elif options["resource"] == 'followers/list':
                options['nodedata'] = 'users'
            elif options["resource"] == 'friends/list':
                options['nodedata'] = 'users'
            else:
                options['nodedata'] = None

        return options

    def setOptions(self, options):
        self.basepathEdit.setEditText(options.get('basepath', credentials['twitter_streaming']['basepath']))
        self.resourceEdit.setEditText(options.get('resource', 'statuses/filter'))
        self.paramEdit.setParams(options.get('params', {'track': '<Object ID>'}))

        # set Access-tokens,use generic method from APITab
        super(TwitterStreamingTab, self).setOptions(options)

    def initSession(self):
        if hasattr(self, "session"):
            return self.session

        elif (self.tokenEdit.text() != '') and (self.tokensecretEdit.text() != ''):
            self.twitter.consumer_key = self.consumerKeyEdit.text() if self.consumerKeyEdit.text() != "" else credentials['twitter']['consumer_key']
            self.twitter.consumer_secret = self.consumerSecretEdit.text() if self.consumerSecretEdit.text() != "" else credentials['twitter']['consumer_secret']
            self.session = self.twitter.get_session((self.tokenEdit.text(), self.tokensecretEdit.text()))
            return self.session

        else:
            raise Exception("No access, login please!")

    def request(self, path, args=None, headers=None):
        self.connected = True
        self.retry_counter=0
        self.last_reconnect=QDateTime.currentDateTime()
        try:
            self.initSession()

            def _send():
                self.last_reconnect = QDateTime.currentDateTime()
                while self.connected:
                    try:
                        if headers is not None:
                            response = self.session.post(path, params=args,
                                                         headers=headers,
                                                         timeout=self.timeout,
                                                         verify=False,
                                                         stream=True)
                        else:
                            response = self.session.get(path, params=args, timeout=self.timeout,
                                                        verify=False, stream=True)

                    except requests.exceptions.Timeout:
                        raise Exception('Request timed out.')
                    else:
                        if response.status_code != 200:
                            if self.retry_counter<=5:
                                self.logMessage("Reconnecting in 3 Seconds: " + str(response.status_code) + ". Message: "+response.content)
                                time.sleep(3)
                                if self.last_reconnect.secsTo(QDateTime.currentDateTime())>120:
                                    self.retry_counter = 0
                                    _send()
                                else:
                                    self.retry_counter+=1
                                    _send()
                            else:
                                self.connected = False
                                raise Exception("Request Error: " + str(response.status_code) + ". Message: "+response.content)
                        print "good response"
                        return response


            while self.connected:
                self.response = _send()
                if self.response:
                    for line in self.response.iter_lines():
                        if not self.connected:
                            break
                        if line:
                            try:
                                data = json.loads(line)
                            except ValueError:  # pragma: no cover
                                raise Exception("Unable to decode response, not valid JSON")
                            else:
                                yield data
                else:
                    break
            self.response.close()

        except AttributeError:
            #This exception is thrown when canceling the connection
            #Only re-raise if not manually canceled
            if self.connected:
                raise
        finally:
            self.connected = False

    def disconnectSocket(self):
        """Used to hardly disconnect the streaming client"""
        self.connected = False
        self.response.raw._fp.close()
        #self.response.close()

    def fetchData(self, nodedata, options=None, callback=None,logCallback=None):
        if not ('url' in options):
            urlpath = options["basepath"] + options["resource"] + ".json"
            urlpath, urlparams = self.getURL(urlpath, options["params"], nodedata)
        else:
            urlpath = options['url']
            urlparams = options["params"]

        if options['logrequests']:
            logCallback(u"Fetching data for {0} from {1}".format(nodedata['objectid'], urlpath + "?" + urllib.urlencode(urlparams)))

        # data
        headers = None
        for data in self.request(path=urlpath, args=urlparams):
            # data
            options['querytime'] = str(datetime.now())
            options['querystatus'] = 'stream'

            callback(data, options, headers, streamingTab=True)


    @Slot()
    def doLogin(self, query=False, caption="Twitter Login Page", url=""):
        self.twitter.consumer_key = self.consumerKeyEdit.text() if self.consumerKeyEdit.text() != "" else credentials['twitter']['consumer_key']
        self.twitter.consumer_secret = self.consumerSecretEdit.text() if self.consumerSecretEdit.text() != "" else credentials['twitter']['consumer_secret']

        self.oauthdata.pop('oauth_verifier', None)
        self.oauthdata['requesttoken'], self.oauthdata['requesttoken_secret'] = self.twitter.get_request_token(
            verify=False)

        super(TwitterStreamingTab, self).doLogin(query, caption,
                                                 self.twitter.get_authorize_url(self.oauthdata['requesttoken']))


    @Slot()
    def getToken(self):
        url = urlparse.parse_qs(self.login_webview.url().toString())
        if 'oauth_verifier' in url:
            token = url['oauth_verifier']
            if token:
                self.oauthdata['oauth_verifier'] = token[0]
                self.session = self.twitter.get_auth_session(self.oauthdata['requesttoken'],
                                                             self.oauthdata['requesttoken_secret'], method='POST',
                                                             data={'oauth_verifier': self.oauthdata['oauth_verifier']},
                                                             verify=False)

                self.tokenEdit.setText(self.session.access_token)
                self.tokensecretEdit.setText(self.session.access_token_secret)

                self.login_webview.parent().close()

class YoutubeTab(ApiTab):
    def __init__(self, mainWindow=None, loadSettings=True):
        super(YoutubeTab, self).__init__(mainWindow, "YouTube")

        self.initInputs(credentials['youtube']['basepath'])

        # Pages Box
        self.pagesEdit = QSpinBox(self)
        self.pagesEdit.setMinimum(1)
        self.pagesEdit.setMaximum(50000)

        # Login-Boxes
        self.tokenEdit = QLineEdit()
        self.tokenEdit.setEchoMode(QLineEdit.Password)
        self.loginButton = QPushButton(" Login to Google ", self)
        self.loginButton.clicked.connect(self.doLogin)

        self.clientIdEdit = QLineEdit()
        self.clientIdEdit.setEchoMode(QLineEdit.Password)
        self.clientSecretEdit = QLineEdit()
        self.clientSecretEdit.setEchoMode(QLineEdit.Password)

        self.scopeEdit = QLineEdit()

        # Construct Login-Layout
        loginlayout = QHBoxLayout()
        loginlayout.addWidget(self.tokenEdit)
        loginlayout.addWidget(self.loginButton)


        applayout = QHBoxLayout()
        applayout.addWidget(self.clientIdEdit)
        applayout.addWidget(QLabel("Client Secret"))
        applayout.addWidget(self.clientSecretEdit)
        applayout.addWidget(QLabel("Scope"))
        applayout.addWidget(self.scopeEdit)


        # Add to main-Layout
        self.mainLayout.addRow("Maximum pages", self.pagesEdit)
        self.mainLayout.addRow("Client Id", applayout)
        self.mainLayout.addRow("Access Token", loginlayout)

        if loadSettings:
            self.loadSettings()


    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {'resource': self.resourceEdit.currentText(),
                   'pages': self.pagesEdit.value(),
                   'params': self.paramEdit.getParams()}

        options['scope'] = self.scopeEdit.text()
        options['basepath'] = self.basepathEdit.currentText()

        # options for request
        if purpose != 'preset':
            options['querytype'] = self.name + ':' + self.resourceEdit.currentText()
            options['access_token'] = self.tokenEdit.text()
            options['client_id'] = self.clientIdEdit.text()
            options['client_secret'] = self.clientSecretEdit.text()


        # options for data handling
        if purpose == 'fetch':
            options['objectid'] = 'id.videoId'
            options['nodedata'] = 'items'

        return options

    def setOptions(self, options):
        #define default values
        if options.get('basepath','') == '':
            options['basepath'] = credentials['youtube']['basepath']

        #set values
        self.resourceEdit.setEditText(options.get('resource', 'videos'))
        self.pagesEdit.setValue(int(options.get('pages', 1)))

        self.basepathEdit.setEditText(options.get('basepath'))
        self.scopeEdit.setText(options.get('scope'))
        self.paramEdit.setParams(options.get('params', {}))

        # set Access-tokens,use generic method from APITab
        super(YoutubeTab, self).setOptions(options)

    def fetchData(self, nodedata, options=None, callback=None, logCallback=None):
    # Preconditions
        if options['access_token'] == '':
            raise Exception('Access token is missing, login please!')
        self.connected = True
        self.speed = options.get('speed',None)

        # Abort condition: maximum page count
        for page in range(0, options.get('pages', 1)):
        # build url
            if not ('url' in options):
                urlpath = options["basepath"] + options['resource']
                urlparams = {}
                urlparams.update(options['params'])

                urlpath, urlparams = self.getURL(urlpath, urlparams, nodedata)
                urlparams["access_token"] = options['access_token']
            else:
                urlpath = options['url']
                urlparams = options['params']

            if options['logrequests']:
                logCallback(u"Fetching data for {0} from {1}".format(nodedata['objectid'],
                                                                                   urlpath + "?" + urllib.urlencode(
                                                                                       urlparams)))

            # data
            options['querytime'] = str(datetime.now())
            data, headers, status = self.request(urlpath, urlparams,jsonify=True)
            options['querystatus'] = status

            callback(data, options, headers)

            # paging
            if isinstance(data,dict) and hasDictValue(data, "nextPageToken"):
                options['params']['pageToken'] = data["nextPageToken"]
            else:
                break

            if not self.connected:
                break


    @Slot()
    def doLogin(self, query=False, caption="YouTube Login Page",url=""):
        #use credentials from input if provided
        client_id = self.clientIdEdit.text() if self.clientIdEdit.text() != "" else credentials['youtube']['client_id']
        scope = [self.scopeEdit.text()] if self.scopeEdit.text() != "" else credentials['youtube']['scope']
        redirect_uri = credentials['youtube']['redirect_uri']

        self.session = OAuth2Session(client_id, redirect_uri=redirect_uri,scope=scope)
        url = credentials['youtube']['auth_uri'] + "?client_id=" + client_id + "&redirect_uri="+redirect_uri+"&response_type=code" + "&scope="+" ".join(scope)

        super(YoutubeTab, self).doLogin(query, caption, url)

    @Slot(QUrl)
    def getToken(self,url):
        if url.toString().startswith(credentials['youtube']['redirect_uri']):
            try:
                client_secret = self.clientSecretEdit.text() if self.clientSecretEdit.text() != "" else credentials['youtube']['client_secret']
                token = self.session.fetch_token(credentials['youtube']['token_uri'],
                        authorization_response=str(url.toString()),
                        client_secret=client_secret)

                self.tokenEdit.setText(token['access_token'])
            finally:
                self.login_webview.parent().close()


class GenericTab(ApiTab):
    # Youtube:
    # URL prefix: https://gdata.youtube.com/feeds/api/videos?alt=json&v=2&q=
    # URL field: <Object ID>
    # URL suffix:
    # -Extract: data.feed.entry
    # -ObjectId: id.$t

    def __init__(self, mainWindow=None, loadSettings=True):
        super(GenericTab, self).__init__(mainWindow, "Generic")

        #Basic inputs
        self.initInputs()

        #Headers
        self.headerEdit = QParamEdit(self)
        self.mainLayout.addRow("Headers", self.headerEdit)

        #Extract option
        self.extractEdit = QComboBox(self)
        self.extractEdit.setEditable(True)
        self.mainLayout.addRow("Key to extract", self.extractEdit)

        self.objectidEdit = QComboBox(self)
        self.objectidEdit.setEditable(True)
        self.mainLayout.addRow("Key for Object ID", self.objectidEdit)

        if loadSettings:
            self.loadSettings()

        self.timeout = 30

    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {}

        #options for request
        options['basepath'] = self.basepathEdit.currentText()
        options['resource'] = self.resourceEdit.currentText()
        options['params'] = self.paramEdit.getParams()
        options['headers'] = self.headerEdit.getParams()

        if purpose != 'preset':
            options['querytype'] = self.name + ':'+options['basepath']+options['resource']

        #options for data handling
        options['nodedata'] = self.extractEdit.currentText() if self.extractEdit.currentText() != "" else None
        options['objectid'] = self.objectidEdit.currentText() if self.objectidEdit.currentText() != "" else None

        return options

    def setOptions(self, options):
        self.basepathEdit.setEditText(options.get('basepath', ''))
        self.resourceEdit.setEditText(options.get('resource', ''))
        self.paramEdit.setParams(options.get('params', {}))
        self.headerEdit.setParams(options.get('headers', {}))

        self.extractEdit.setEditText(options.get('nodedata', ''))
        self.objectidEdit.setEditText(options.get('objectid', ''))

    def fetchData(self, nodedata, options=None, callback=None,logCallback=None):
        self.connected = True
        self.speed = options.get('speed',None)

        urlpath = options["basepath"] + options['resource']
        urlparams = {}
        urlparams.update(options['params'])

        requestheaders = {}
        requestheaders.update(options['headers'])


        urlpath, urlparams = self.getURL(urlpath,urlparams, nodedata)
        if options['logrequests']:
                logCallback(u"Fetching data for {0} from {1}".format(nodedata['objectid'], urlpath + "?" + urllib.urlencode(urlparams)))

        #data
        data, headers, status = self.request(urlpath, urlparams,requestheaders,jsonify=True)
        options['querytime'] = str(datetime.now())
        options['querystatus'] = status

        callback(data, options, headers)


class FilesTab(ApiTab):
    def __init__(self, mainWindow=None, loadSettings=True):
        super(FilesTab, self).__init__(mainWindow, "Files")

        #Basic inputs
        self.initInputs('<url>')

        #Headers
        self.headerEdit = QParamEdit(self)
        self.mainLayout.addRow("Headers", self.headerEdit)

        #Download folder
        folderlayout = QHBoxLayout()
        self.folderEdit = QLineEdit()
        folderlayout.addWidget(self.folderEdit)

        self.folderButton = QPushButton("...", self)
        self.folderButton.clicked.connect(self.selectFolder)
        folderlayout.addWidget(self.folderButton)

        self.mainLayout.addRow("Folder", folderlayout)

        #filename
        self.filenameEdit = QComboBox(self)
        self.filenameEdit.insertItems(0, ['<None>'])
        self.filenameEdit.setEditable(True)
        self.mainLayout.addRow("Custom filename", self.filenameEdit)

        #fileext
        self.fileextEdit = QComboBox(self)
        self.fileextEdit.insertItems(0, ['<None>'])
        self.fileextEdit.setEditable(True)
        self.mainLayout.addRow("Custom file extension", self.fileextEdit)

        if loadSettings:
            self.loadSettings()

        self.timeout = 30

    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {}
        options['basepath'] = self.basepathEdit.currentText()
        options['resource'] = self.resourceEdit.currentText()
        options['params'] = self.paramEdit.getParams()
        options['headers'] = self.headerEdit.getParams()

        if purpose != 'preset':
            options['querytype'] = self.name + ':'+options['basepath']+options['resource']

        options['folder'] = self.folderEdit.text()
        options['filename'] = self.filenameEdit.currentText()
        options['fileext'] = self.fileextEdit.currentText()
        options['nodedata'] = None
        options['objectid'] = 'filename'

        return options

    def setOptions(self, options):
        self.basepathEdit.setEditText(options.get('basepath', '<url>'))
        self.resourceEdit.setEditText(options.get('resource', ''))
        self.paramEdit.setParams(options.get('params', {}))
        self.headerEdit.setParams(options.get('headers', {}))

        self.folderEdit.setText(options.get('folder', ''))
        self.filenameEdit.setEditText(options.get('filename', '<None>'))
        self.fileextEdit.setEditText(options.get('fileext', '<None>'))

    def fetchData(self, nodedata, options=None, callback=None,logCallback=None):
        self.connected = True
        self.speed = options.get('speed',None)

        foldername = options.get('folder', None)
        if (foldername is None) or (not os.path.isdir(foldername)):
            raise Exception("Folder does not exists, select download folder, please!")
        filename = options.get('filename', None)
        filename = self.parsePlaceholders(filename,nodedata)

        fileext = options.get('fileext', None)

        if fileext is not None and fileext == '<None>':
            fileext = None
        elif fileext is not None and fileext != '':
            fileext = self.parsePlaceholders(fileext,nodedata)

        urlpath = options["basepath"] + options['resource']
        urlparams = {}
        urlparams.update(options['params'])

        urlpath, urlparams = self.getURL(urlpath,urlparams, nodedata)




        requestheaders = {}
        requestheaders.update(options['headers'])

        if options['logrequests']:
            logCallback(u"Downloading file for {0} from {1}".format(nodedata['objectid'],
                                                                              urlpath + "?" + urllib.urlencode(
                                                                                  urlparams)))

        data, headers, status = self.download(urlpath, urlparams, requestheaders, foldername,filename,fileext)
        options['querytime'] = str(datetime.now())
        options['querystatus'] = status

        callback(data, options, headers)


class QWebPageCustom(QWebPage):
    logmessage = Signal(str)
    urlNotFound = Signal(QUrl)

    def __init__(self, *args, **kwargs):
        super(QWebPageCustom, self).__init__(*args, **kwargs)
        self.networkAccessManager().sslErrors.connect(self.onSslErrors)

    def supportsExtension(self, extension):
        if extension == QWebPage.ErrorPageExtension:
            return True
        else:
            return False

    def extension(self, extension, option=0, output=0):
        if extension != QWebPage.ErrorPageExtension: return False

        if option.domain == QWebPage.QtNetwork:
            #msg = "Network error (" + str(option.error) + "): " + option.errorString
            #self.logmessage.emit(msg)
            self.urlNotFound.emit(option.url)

        elif option.domain == QWebPage.Http:
            msg = "HTTP error (" + str(option.error) + "): " + option.errorString
            self.logmessage.emit(msg)

        elif option.domain == QWebPage.WebKit:
            msg = "WebKit error (" + str(option.error) + "): " + option.errorString
            self.logmessage.emit(msg)
        else:
            msg = option.errorString
            self.logmessage.emit(msg)

        return True

    def onSslErrors(self, reply, errors):
        url = unicode(reply.url().toString())
        reply.ignoreSslErrors()
        self.logmessage.emit("SSL certificate error ignored: %s (Warning: Your connection might be insecure!)" % url)
