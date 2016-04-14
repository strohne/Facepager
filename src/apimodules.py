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
import requests
from requests.exceptions import *
from rauth import OAuth1Service
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
        if options.has_key('twitter_consumer_secret'):
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

    def loadDocs(self):
        '''
        Loads and prepares documentation
        '''

        try:
            if getattr(sys, 'frozen', False):
                folder = os.path.join(os.path.dirname(sys.executable),'docs')
            elif __file__:
                folder = os.path.join(os.path.dirname(__file__),'docs')

            filename = u"{0}.json".format(self.__class__.__name__)

            with open(os.path.join(folder, filename),"r") as docfile:
                if docfile:
                    self.apidoc = json.load(docfile)
                else:
                    self.apidoc = None
        except:
            self.apidoc = None

    def setRelations(self,params=True):
        '''
        Create relations box and paramedit
        Set the relations according to the APIdocs, if any docs are available
        '''

        self.relationEdit = QComboBox(self)
        if self.apidoc:
            #Insert one item for every endpoint
            for endpoint in reversed(self.apidoc):
                #store url as item text
                self.relationEdit.insertItem(0, endpoint["path"])
                #store doc as tooltip
                self.relationEdit.setItemData(0, endpoint["doc"], Qt.ToolTipRole)
                #store params-dict for later use in onChangedRelation
                self.relationEdit.setItemData(0, endpoint.get("params",[]), Qt.UserRole)

        self.relationEdit.setEditable(True)
        if params:
            self.paramEdit = QParamEdit(self)
            # changed to currentIndexChanged for recognition of changes made by the tool itself
            self.relationEdit.currentIndexChanged.connect(self.onchangedRelation)
            self.onchangedRelation()

    @Slot()
    def onchangedRelation(self,index=0):
        '''
        Handles the automated paramter suggestion for the current
        selected API Relation/Endpoint
        '''
        #retrieve param-dict stored in setRelations-method
        params = self.relationEdit.itemData(index,Qt.UserRole)

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

    def request(self, path, args=None, headers=None, jsonify=True,speed=None):
        """
        Start a new threadsafe session and request
        """

        #Throttle speed
        if (speed is not None) and (self.lastrequest is not None):
            pause = ((60 * 1000) / float(speed)) - self.lastrequest.msecsTo(QDateTime.currentDateTime())
            while (self.connected) and (pause > 0):
                time.sleep(0.1)
                pause = ((60 * 1000) / float(speed)) - self.lastrequest.msecsTo(QDateTime.currentDateTime())

        self.lastrequest = QDateTime.currentDateTime()

        session = self.initSession()
        if (not session):
            raise Exception("No session available.")

        try:
            maxretries = 3
            while True:
                try:
                    if headers is not None:
                        response = session.post(path, params=args, headers=headers, timeout=self.timeout, verify=False)
                    else:
                        response = session.get(path, params=args, timeout=self.timeout, verify=False)
                except (HTTPError, ConnectionError), e:
                    maxretries -= 1
                    if maxretries > 0:
                        sleep(0.1)
                        self.mainWindow.logmessage(u"Automatic retry: Request Error: {0}".format(e.message))
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
        webpage.logmessage.connect(self.mainWindow.logmessage)
        self.login_webview.setPage(webpage);

        #Connect to the getToken-method
        self.login_webview.urlChanged.connect(self.getToken)

        # Connect to the loadFinished-Slot for an error message
        self.login_webview.loadFinished.connect(self.loadFinished)

        self.login_webview.load(QUrl(url))
        #self.login_webview.resize(window.size())
        self.login_webview.show()

        window.show()

    @Slot()
    def loadFinished(self, success):
        if (not success):
            self.mainWindow.logmessage('Error loading web page')


    def download(self, path, args=None, headers=None, foldername=None, filename=None, fileext=None):
        """
        Download files ...
        Uses the request-method without converting to json
        (argument jsonify==True)
        """

        def makefilename(foldername=None, filename=None, fileext=None,appendtime = False):  # Create file name
            url_filename, url_fileext = os.path.splitext(os.path.basename(path))
            if not fileext:
                fileext = url_fileext
            if not filename:
                filename = url_filename

            filename = re.sub(ur'[^a-zA-Z0-9_.-]+', '', filename)
            fileext = re.sub(ur'[^a-zA-Z0-9_.-]+', '', fileext)

            filetime = time.strftime("%Y-%m-%d-%H-%M-%S")
            filenumber = 1

            while True:
                if appendtime:
                    fullfilename = os.path.join(foldername,
                                                filename[:100] + '.' + filetime + '-' + str(filenumber) + str(fileext))
                else:
                    fullfilename = os.path.join(foldername,
                                                filename[:100] + '.' + str(filenumber) + str(fileext))

                if (os.path.isfile(fullfilename)):
                    filenumber = filenumber + 1
                else:
                    break
            return fullfilename

        response = self.request(path, args, headers, jsonify=False)

        # Handle the response of the generic, non-json-returning response
        if response.status_code == 200:
            if not fileext:
                guessed_ext = guess_all_extensions(response.headers["content-type"])
                fileext = guessed_ext[-1] if len(guessed_ext) > 0 else None

            fullfilename = makefilename(foldername, filename, fileext)
            with open(fullfilename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            data = {'filename': os.path.basename(fullfilename), 'filepath': fullfilename, 'sourcepath': path,
                    'sourcequery': args}
            status = 'downloaded' + ' (' + str(response.status_code) + ')'
        else:
            data = {'sourcepath': path, 'sourcequery': args}
            status = 'error' + ' (' + str(response.status_code) + ')'

        return data, dict(response.headers), status

    def selectFolder(self):
        datadir = self.mainWindow.settings.value('lastpath', os.path.expanduser('~'))
        self.folderEdit.setText(
            QFileDialog.getExistingDirectory(self, 'Select Download Folder', datadir, QFileDialog.ShowDirsOnly))

class FacebookTab(ApiTab):
    def __init__(self, mainWindow=None, loadSettings=True):
        super(FacebookTab, self).__init__(mainWindow, "Facebook")

        #Base path
        #URL prefix
        self.basepathEdit = QComboBox(self)
        self.basepathEdit.insertItems(0, ['https://graph.facebook.com/v2.2/'])
        self.basepathEdit.setEditable(True)



        # Query Box
        self.setRelations()

#         #Download folder
#         folderlayout = QHBoxLayout()
#
#         self.folderEdit = QLineEdit()
#         folderlayout.addWidget(self.folderEdit)
#
#         self.folderButton = QPushButton("...", self)
#         self.folderButton.clicked.connect(self.selectFolder)
#         folderlayout.addWidget(self.folderButton)




        # Pages Box
        self.pagesEdit = QSpinBox(self)
        self.pagesEdit.setMinimum(1)
        self.pagesEdit.setMaximum(50000)




        #self.basepathEdit = QLineEdit()

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


        # Construct main-Layout
        mainLayout = QFormLayout()
        mainLayout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        mainLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        mainLayout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        mainLayout.setLabelAlignment(Qt.AlignLeft)
        mainLayout.addRow("Base path", self.basepathEdit)
        mainLayout.addRow("Resource", self.relationEdit)
        mainLayout.addRow("Parameters", self.paramEdit)
        #mainLayout.addRow("Download folder", folderlayout)
        mainLayout.addRow("Maximum pages", self.pagesEdit)

        mainLayout.addRow("Client Id", applayout)
        mainLayout.addRow("Access Token", loginlayout)

        self.setLayout(mainLayout)

        if loadSettings:
            self.loadSettings()


    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {'relation': self.relationEdit.currentText(), 'pages': self.pagesEdit.value(),
                   'params': self.paramEdit.getParams()}

        options['scope'] = self.scopeEdit.text()
        options['basepath'] = self.basepathEdit.currentText()
        #options['folder'] = self.folderEdit.text()

        # options for request
        if purpose != 'preset':
            options['querytype'] = self.name + ':' + self.relationEdit.currentText()
            options['access_token'] = self.tokenEdit.text()
            options['client_id'] = self.clientIdEdit.text()


        # options for data handling
        if purpose == 'fetch':
            options['objectid'] = 'id'
            options['nodedata'] = 'data' if ('/' in options['relation']) or (options['relation'] == 'search') else None

        return options

    def setOptions(self, options):
        #define default values
        if options.get('basepath','') == '':
            options['basepath']= "https://graph.facebook.com/v2.2/"
        if options.get('scope','') == '':
            options['scope']= "user_groups"

        #set values
        self.relationEdit.setEditText(options.get('relation', '<page>'))
        self.pagesEdit.setValue(int(options.get('pages', 1)))

        self.basepathEdit.setEditText(options.get('basepath'))
        self.scopeEdit.setText(options.get('scope'))
        self.paramEdit.setParams(options.get('params', {}))

        # set Access-tokens,use generic method from APITab
        super(FacebookTab, self).setOptions(options)

    def fetchData(self, nodedata, options=None, callback=None):
    # Preconditions
        if options['access_token'] == '':
            raise Exception('Access token is missing, login please!')
        self.connected = True

        # Abort condition for time based pagination
        since = options['params'].get('since', False)
        if (since != False):
            since = dateutil.parser.parse(since, yearfirst=True, dayfirst=False)
            since = int((since - datetime(1970, 1, 1)).total_seconds())

        # Abort condition: maximum page count
        for page in range(0, options.get('pages', 1)):
        # build url
            if not ('url' in options):
                urlpath = options["basepath"] + options['relation']
                urlparams = {}

                if options['relation'] == 'search':
                    urlparams['q'] = self.idtostr(nodedata['objectid'])
                    urlparams['type'] = 'page'

                elif options['relation'] == '<Object ID>':
                    urlparams['metadata'] = '1'

                elif '<Object ID>/' in options['relation']:
                    urlparams['limit'] = '100'

                urlparams.update(options['params'])

                urlpath, urlparams = self.getURL(urlpath, urlparams, nodedata)
                urlparams["access_token"] = options['access_token']
            else:
                urlpath = options['url']
                urlparams = options['params']

            self.mainWindow.logmessage(u"Fetching data for {0} from {1}".format(nodedata['objectid'],
                                                                               urlpath + "?" + urllib.urlencode(
                                                                                   urlparams)))

            # data
            options['querytime'] = str(datetime.now())
            data, headers, status = self.request(urlpath, urlparams,None,True,options.get('speed',None) )
            options['querystatus'] = status

            if callback is None:
                self.streamingData.emit(data, options, headers)
            else:
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
        facebookclientid = self.clientIdEdit.text() if self.clientIdEdit.text() != "" else credentials['facebook_client_id']
        scope= self.scopeEdit.text()
        url = "https://www.facebook.com/dialog/oauth?client_id=" + facebookclientid + "&redirect_uri=https://www.facebook.com/connect/login_success.html&response_type=token&scope="+scope+"&display=popup"

        # Facebook client id should be defined in credentials.py
        super(FacebookTab, self).doLogin(query, caption, url)

    @Slot()
    def getToken(self):
        url = urlparse.parse_qs(self.login_webview.url().toString())
        if "https://www.facebook.com/connect/login_success.html#access_token" in url:
            token = url["https://www.facebook.com/connect/login_success.html#access_token"]
            if token:
                self.tokenEdit.setText(token[0])
                self.login_webview.parent().close()


class TwitterTab(ApiTab):
    def __init__(self, mainWindow=None, loadSettings=True):
        super(TwitterTab, self).__init__(mainWindow, "Twitter")

        #Base path
        #URL prefix
        self.basepathEdit = QComboBox(self)
        self.basepathEdit.insertItems(0, ['https://api.twitter.com/1.1/'])
        self.basepathEdit.setEditable(True)


        # Query and Parameter Box
        self.setRelations()

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
        loginlayout = QHBoxLayout()
        loginlayout.addWidget(self.tokenEdit)
        loginlayout.addWidget(QLabel("Access Token Secret"))
        loginlayout.addWidget(self.tokensecretEdit)
        loginlayout.addWidget(self.loginButton)

        credentialslayout = QHBoxLayout()
        credentialslayout.addWidget(self.consumerKeyEdit)
        credentialslayout.addWidget(QLabel("Consumer Secret"))
        credentialslayout.addWidget(self.consumerSecretEdit)


        # Construct main-Layout
        mainLayout = QFormLayout()
        mainLayout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        mainLayout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        mainLayout.setLabelAlignment(Qt.AlignLeft)
        mainLayout.addRow("Base path", self.basepathEdit)
        mainLayout.addRow("Resource", self.relationEdit)
        mainLayout.addRow("Parameters", self.paramEdit)
        mainLayout.addRow("Maximum pages", self.pagesEdit)
        mainLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        mainLayout.addRow("Access Token", loginlayout)
        mainLayout.addRow("Consumer Key", credentialslayout)
        self.setLayout(mainLayout)
        if loadSettings:
            self.loadSettings()

        # Twitter OAUTH consumer key and secret should be defined in credentials.py
        self.oauthdata = {}
        self.twitter = OAuth1Service(
            consumer_key=credentials['twitter_consumer_key'],
            consumer_secret=credentials['twitter_consumer_secret'],
            name='twitter',
            access_token_url='https://api.twitter.com/oauth/access_token',
            authorize_url='https://api.twitter.com/oauth/authorize',
            request_token_url='https://api.twitter.com/oauth/request_token',
            base_url='https://api.twitter.com/1.1/')


    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {'basepath' : self.basepathEdit.currentText(),'query': self.relationEdit.currentText(), 'params': self.paramEdit.getParams(),
                   'pages': self.pagesEdit.value()}

        # options for request
        if purpose != 'preset':
            options['querytype'] = self.name + ':' + self.relationEdit.currentText()
            options['access_token'] = self.tokenEdit.text()
            options['access_token_secret'] = self.tokensecretEdit.text()
            options['consumer_key'] = self.consumerKeyEdit.text()
            options['consumer_secret'] = self.consumerSecretEdit.text()

        # options for data handling
        if purpose == 'fetch':
            #options['basepath'] =  "https://api.twitter.com/1.1/"
            options['objectid'] = 'id'

            if options["query"] == 'search/tweets':
                options['nodedata'] = 'statuses'
            elif options["query"] == 'followers/list':
                options['nodedata'] = 'users'
            elif options["query"] == 'friends/list':
                options['nodedata'] = 'users'
            else:
                options['nodedata'] = None

        return options


    def setOptions(self, options):
        self.relationEdit.setEditText(options.get('query', 'search/tweets'))
        self.basepathEdit.setEditText(options.get('basepath', 'https://api.twitter.com/1.1/'))
        self.paramEdit.setParams(options.get('params', {'q': '<Object ID>'}))
        self.pagesEdit.setValue(int(options.get('pages', 1)))

        # set Access-tokens,use generic method from APITab
        super(TwitterTab, self).setOptions(options)

    def initSession(self):
        if hasattr(self, "session"):
            return self.session

        elif (self.tokenEdit.text() != '') and (self.tokensecretEdit.text() != ''):
            self.twitter.consumer_key = self.consumerKeyEdit.text() if self.consumerKeyEdit.text() != "" else credentials['twitter_consumer_key']
            self.twitter.consumer_secret = self.consumerSecretEdit.text() if self.consumerSecretEdit.text() != "" else credentials['twitter_consumer_secret']
            self.twitter.base_url = self.basepathEdit.currentText() if self.basepathEdit.currentText() != "" else 'https://api.twitter.com/1.1/'

            self.session = self.twitter.get_session((self.tokenEdit.text(), self.tokensecretEdit.text()))
            return self.session

        else:
            raise Exception("No access, login please!")


    def fetchData(self, nodedata, options=None, callback=None):
        self.connected = True
        for page in range(0, options.get('pages', 1)):
            if not ('url' in options):
                urlpath = options["basepath"] + options["query"] + ".json"
                urlpath, urlparams = self.getURL(urlpath, options["params"], nodedata)
            else:
                urlpath = options['url']
                urlparams = options["params"]

            self.mainWindow.logmessage(u"Fetching data for {0} from {1}".format(nodedata['objectid'],
                                                                               urlpath + "?" + urllib.urlencode(
                                                                                   urlparams)))

            # data
            data, headers, status = self.request(urlpath, urlparams)
            options['querytime'] = str(datetime.now())
            options['querystatus'] = status

            if callback is None:
                self.streamingData.emit(data, options, headers)
            else:
                callback(data, options, headers)

            # paging with next-results; Note: Do not rely on the search_metadata information, sometimes the next_results param is missing, this is a known bug
            paging = False
            if isinstance(data,dict) and hasDictValue(data, "search_metadata.next_results"):
                paging = True
                url, params = self.parseURL(getDictValue(data, "search_metadata.next_results", False))
                options['url'] = urlpath
                options['params'] = params

            # manual paging with max-id
            # if there are still statuses in the response, use the last ID-1 for further pagination
            elif isinstance(data,list) and (len(data) > 0):
                options['params']['max_id'] = int(data[-1]["id"])-1
                paging = True

            if not paging:
                break

            if not self.connected:
                break

    @Slot()
    def doLogin(self, query=False, caption="Twitter Login Page", url=""):
        try:
            self.twitter.consumer_key = self.consumerKeyEdit.text() if self.consumerKeyEdit.text() != "" else credentials['twitter_consumer_key']
            self.twitter.consumer_secret = self.consumerSecretEdit.text() if self.consumerSecretEdit.text() != "" else credentials['twitter_consumer_secret']

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
        self.setRelations()

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


        # Construct main-Layout
        mainLayout = QFormLayout()
        mainLayout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        mainLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        mainLayout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        mainLayout.setLabelAlignment(Qt.AlignLeft)
        mainLayout.addRow("Resource", self.relationEdit)
        mainLayout.addRow("Parameters", self.paramEdit)
        mainLayout.addRow("Access Token", loginlayout)
        mainLayout.addRow("Consumer Key", credentialslayout)
        if loadSettings:
            self.loadSettings()
        self.setLayout(mainLayout)

        # Twitter OAUTH consumer key and secret should be defined in credentials.py
        self.oauthdata = {}
        self.twitter = OAuth1Service(
            consumer_key=credentials['twitter_consumer_key'],
            consumer_secret=credentials['twitter_consumer_secret'],
            name='twitterstreaming',
            access_token_url='https://api.twitter.com/oauth/access_token',
            authorize_url='https://api.twitter.com/oauth/authorize',
            request_token_url='https://api.twitter.com/oauth/request_token',
            base_url='https://stream.twitter.com/1.1/')
        self.timeout = 60
        self.connected = False


    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {'query': self.relationEdit.currentText(), 'params': self.paramEdit.getParams()}
        # options for request

        if purpose != 'preset':
            options['querytype'] = self.name + ':' + self.relationEdit.currentText()
            options['access_token'] = self.tokenEdit.text()
            options['access_token_secret'] = self.tokensecretEdit.text()
            options['consumer_key'] = self.consumerKeyEdit.text()
            options['consumer_secret'] = self.consumerSecretEdit.text()


        # options for data handling
        if purpose == 'fetch':
            options['basepath'] =  "https://stream.twitter.com/1.1/"

            options['objectid'] = 'id'

            if options["query"] == 'search/tweets':
                options['nodedata'] = 'statuses'
            elif options["query"] == 'followers/list':
                options['nodedata'] = 'users'
            elif options["query"] == 'friends/list':
                options['nodedata'] = 'users'
            else:
                options['nodedata'] = None

        return options

    def setOptions(self, options):
        self.relationEdit.setEditText(options.get('query', 'statuses/filter'))
        self.paramEdit.setParams(options.get('params', {'track': '<Object ID>'}))

        # set Access-tokens,use generic method from APITab
        super(TwitterStreamingTab, self).setOptions(options)

    def initSession(self):
        if hasattr(self, "session"):
            return self.session

        elif (self.tokenEdit.text() != '') and (self.tokensecretEdit.text() != ''):
            self.twitter.consumer_key = self.consumerKeyEdit.text() if self.consumerKeyEdit.text() != "" else credentials['twitter_consumer_key']
            self.twitter.consumer_secret = self.consumerSecretEdit.text() if self.consumerSecretEdit.text() != "" else credentials['twitter_consumer_secret']
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
                                self.mainWindow.logmessage("Reconnecting in 3 Seconds: " + str(response.status_code) + ". Message: "+response.content)
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

    def fetchData(self, nodedata, options=None, callback=None):
        if not ('url' in options):
            urlpath = options["basepath"] + options["query"] + ".json"
            urlpath, urlparams = self.getURL(urlpath, options["params"], nodedata)
        else:
            urlpath = options['url']
            urlparams = options["params"]

        self.mainWindow.logmessage(
            u"Fetching data for {0} from {1}".format(nodedata['objectid'], urlpath + "?" + urllib.urlencode(urlparams)))
        # data
        headers = None
        for data in self.request(path=urlpath, args=urlparams):
            # data
            options['querytime'] = str(datetime.now())
            options['querystatus'] = 'stream'

            if callback is None:
                self.streamingData.emit(data, options, headers)
            else:
                callback(data, options, headers, streamingTab=True)


    @Slot()
    def doLogin(self, query=False, caption="Twitter Login Page", url=""):
        self.twitter.consumer_key = self.consumerKeyEdit.text() if self.consumerKeyEdit.text() != "" else credentials['twitter_consumer_key']
        self.twitter.consumer_secret = self.consumerSecretEdit.text() if self.consumerSecretEdit.text() != "" else credentials['twitter_consumer_secret']

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


class GenericTab(ApiTab):
    # Youtube:
    # URL prefix: https://gdata.youtube.com/feeds/api/videos?alt=json&v=2&q=
    # URL field: <Object ID>
    # URL suffix:
    # -Extract: data.feed.entry
    # -ObjectId: id.$t

    def __init__(self, mainWindow=None, loadSettings=True):
        super(GenericTab, self).__init__(mainWindow, "Generic")
        mainLayout = QFormLayout()
        mainLayout.setRowWrapPolicy(QFormLayout.DontWrapRows);
        mainLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow);
        mainLayout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop);
        mainLayout.setLabelAlignment(Qt.AlignLeft);

        #URL prefix
        self.urlpathEdit = QComboBox(self)
        self.urlpathEdit.insertItems(0, ['https://api.twitter.com/1/statuses/user_timeline.json'])
        self.urlpathEdit.insertItems(0, ['https://gdata.youtube.com/feeds/api/videos'])

        self.urlpathEdit.setEditable(True)
        mainLayout.addRow("URL path", self.urlpathEdit)

        #Parameter
        self.paramEdit = QParamEdit(self)
        self.paramEdit.setNameOptions([{'name':''}])
        self.paramEdit.setValueOptions([{'name':'',
                                         'doc':"No Value"},
                                         {'name':'<Object ID>',
                                          'doc':"The value in the Object ID-column of the datatree."}])
        mainLayout.addRow("Parameters", self.paramEdit)

        #Extract option
        self.extractEdit = QComboBox(self)
        #self.extractEdit.insertItems(0,['data'])
        self.extractEdit.insertItems(0, ['matches'])
        self.extractEdit.insertItems(0, ['feed.entry'])

        self.extractEdit.setEditable(True)
        mainLayout.addRow("Key to extract", self.extractEdit)

        self.objectidEdit = QComboBox(self)
        self.objectidEdit.insertItems(0, ['id.$t'])
        self.objectidEdit.setEditable(True)
        mainLayout.addRow("Key for ObjectID", self.objectidEdit)

        self.setLayout(mainLayout)
        if loadSettings:
            self.loadSettings()

    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {}

        #options for request
        if purpose != 'preset':
            options['querytype'] = self.name

        options['urlpath'] = self.urlpathEdit.currentText()
        options['params'] = self.paramEdit.getParams()

        #options for data handling
        options['nodedata'] = self.extractEdit.currentText() if self.extractEdit.currentText() != "" else None
        options['objectid'] = self.objectidEdit.currentText() if self.objectidEdit.currentText() != "" else None

        return options

    def setOptions(self, options):
        self.urlpathEdit.setEditText(options.get('urlpath', 'https://gdata.youtube.com/feeds/api/videos'))
        self.paramEdit.setParams(options.get('params', {'q': '<Object ID>', 'alt': 'json', 'v': '2'}))
        self.extractEdit.setEditText(options.get('nodedata', 'feed.entry'))
        self.objectidEdit.setEditText(options.get('objectid', 'media$group.yt$videoid.$t'))


    def fetchData(self, nodedata, options=None, callback=None):
        self.connected = True
        urlpath, urlparams = self.getURL(options["urlpath"], options["params"], nodedata)
        self.mainWindow.logmessage(
            u"Fetching data for {0} from {1}".format(nodedata['objectid'], urlpath + "?" + urllib.urlencode(urlparams)))

        #data
        data, headers, status = self.request(urlpath, urlparams)
        options['querytime'] = str(datetime.now())
        options['querystatus'] = status

        if callback is None:
            self.streamingData.emit(data, options, headers)
        else:
            callback(data, options, headers)


class FilesTab(ApiTab):
    def __init__(self, mainWindow=None, loadSettings=True):
        super(FilesTab, self).__init__(mainWindow, "Files")
        mainLayout = QFormLayout()
        mainLayout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        mainLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        mainLayout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        mainLayout.setLabelAlignment(Qt.AlignLeft)

        #URL field
        self.urlpathEdit = QComboBox(self)
        self.urlpathEdit.insertItems(0, ['<url>'])
        self.urlpathEdit.setEditable(True)
        mainLayout.addRow("URL path", self.urlpathEdit)

        #Download folder
        folderlayout = QHBoxLayout()

        self.folderEdit = QLineEdit()
        folderlayout.addWidget(self.folderEdit)

        self.folderButton = QPushButton("...", self)
        self.folderButton.clicked.connect(self.selectFolder)
        folderlayout.addWidget(self.folderButton)

        mainLayout.addRow("Folder", folderlayout)

        #filename
        self.filenameEdit = QComboBox(self)
        self.filenameEdit.insertItems(0, ['<None>'])
        self.filenameEdit.setEditable(True)
        mainLayout.addRow("Custom filename", self.filenameEdit)

        #fileext
        self.fileextEdit = QComboBox(self)
        self.fileextEdit.insertItems(0, ['<None>'])
        self.fileextEdit.setEditable(True)
        mainLayout.addRow("Custom file extension", self.fileextEdit)

        self.setLayout(mainLayout)
        if loadSettings: self.loadSettings()



    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {}

        if purpose != 'preset':
            options['querytype'] = self.name

        options['urlpath'] = self.urlpathEdit.currentText()
        options['folder'] = self.folderEdit.text()
        options['filename'] = self.filenameEdit.currentText()
        options['fileext'] = self.fileextEdit.currentText()
        options['nodedata'] = None
        options['objectid'] = 'filename'

        return options

    def setOptions(self, options):
        self.urlpathEdit.setEditText(options.get('urlpath', '<url>'))
        self.folderEdit.setText(options.get('folder', ''))
        self.filenameEdit.setEditText(options.get('filename', '<None>'))
        self.fileextEdit.setEditText(options.get('fileext', '<None>'))

    def fetchData(self, nodedata, options=None, callback=None):
        self.connected = True
        foldername = options.get('folder', None)
        if (foldername is None) or (not os.path.isdir(foldername)):
            raise Exception("Folder does not exists, select download folder, please!")
        filename = options.get('filename', None)
        fileext = options.get('fileext', None)

        urlpath, urlparams = self.getURL(options["urlpath"], {}, nodedata)
        filename = self.parsePlaceholders(filename,nodedata)
        fileext = self.parsePlaceholders(fileext,nodedata)

        self.mainWindow.logmessage(u"Downloading file for {0} from {1}".format(nodedata['objectid'],
                                                                              urlpath + "?" + urllib.urlencode(
                                                                                  urlparams)))

        data, headers, status = self.download(urlpath, urlparams, None, foldername,filename,fileext)
        options['querytime'] = str(datetime.now())
        options['querystatus'] = status
        if callback is None:
            self.streamingData.emit(data, options, headers)
        else:
            callback(data, options, headers)


class QWebPageCustom(QWebPage):
    logmessage = Signal(str)

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
            msg = "Network error (" + str(option.error) + "): " + option.errorString

        elif option.domain == QWebPage.Http:
            msg = "HTTP error (" + str(option.error) + "): " + option.errorString

        elif option.domain == QWebPage.WebKit:
            msg = "WebKit error (" + str(option.error) + "): " + option.errorString
        else:
            msg = option.errorString

        self.logmessage.emit(msg)

        return True

    def onSslErrors(self, reply, errors):
        url = unicode(reply.url().toString())
        reply.ignoreSslErrors()
        self.logmessage.emit("SSL certificate error ignored: %s (Warning: Your connection might be insecure!)" % url)
