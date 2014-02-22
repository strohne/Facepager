import urlparse
import urllib
from mimetypes import guess_all_extensions
from datetime import datetime
import re
import os
import time
from collections import OrderedDict
import threading

from PySide.QtWebKit import QWebView, QWebPage
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
        self.loadDocs()
        self.lock_session = threading.Lock()

    def idtostr(self, val):
        """
         Return the Node-ID as a Non-Unicode string
        """
        try:
            return str(val)
        except UnicodeEncodeError:
            return val.encode('utf-8')

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
            if (name == '<None>') or (params[name] == '<None>') or (name == '') or (params[name] == ''):
                continue
            
            # Set the value for the ObjectID or any other placeholder-param
            if params[name] == '<Object ID>':
                value = self.idtostr(nodedata['objectid'])
            else:
                match = re.match("^<(.*)>$", str(params[name]))
                if match:
                    value = getDictValue(nodedata['response'], match.group(1))
                else:
                    value = params[name]

            #check for template params
            match = re.match("^<(.*)>$", str(name))
            if match:
                templateparams[match.group(1)] = value
            else:
                urlparams[name] = value

        #Replace placeholders in urlpath
        matches = re.findall("<([^>]*)>", urlpath)
        for match in matches:
            if match in templateparams:
                value = templateparams[match]
            elif match == 'Object ID':
                value = self.idtostr(nodedata['objectid'])
            else:
                value = getDictValue(nodedata['response'], match)
            urlpath = urlpath.replace('<' + match + '>', value)
            
        return urlpath, urlparams


    def getOptions(self, purpose='fetch'): #purpose = 'fetch'|'settings'|'preset'
        return {}

    def setOptions(self, options):
        if 'access_token' in options:
            self.tokenEdit.setText(options.get('access_token', ''))
        if 'access_token_secret' in options:
            self.tokensecretEdit.setText(options.get('access_token_secret', ''))

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
            with open("docs/{}.json".format(self.__class__.__name__),"r") as docfile:
                if docfile:
                    self.apidoc = []
                    rawdoc = json.load(docfile)
                    
                    #Filter out everything besides get requests
                    rawdoc = [endpoint for endpoint in rawdoc["application"]["endpoints"][0]["resources"] if endpoint["method"]["name"]=="GET"]
                    
                    for endpoint in rawdoc:
                        #Prepare path
                        pathname = endpoint["path"].split(".json")[0].lstrip("/").replace('{','<').replace('}','>')                        
                        
                        #Prepare documentation
                        docstring = "<p>"+endpoint["method"]["doc"]["content"]+"</p>"                        
                        
                        #Prepare params
                        params = []
                        for param in endpoint["method"].get("params",[]):
                            paramreq = param.get("required",False)
                            paramname = param["name"]
                            if param.get("style","query") == "template":
                                paramname = '<'+paramname+'>'
                                paramdefault = '<Object ID>'
                            else:
                                paramdefault = ''
                                    
                            paramdoc = "<p>{0}</p>".format(param.get("doc",{}).get("content","No description found").encode("utf8"))
                            if paramreq:
                                paramdoc = "<font color='#FF0000'>{0}</font><b>[Mandatory Parameter]</b>".format(paramdoc)
                            
                            params.append({'name':paramname,
                                           'doc':paramdoc,
                                           'required':paramreq,
                                           'default':paramdefault
                                           })
                         
                        #Append data  
                        self.apidoc.append({'path': pathname,
                                            'doc': docstring,
                                            'params':params
                                            })

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
            self.relationEdit.activated.connect(self.onchangedRelation)
            self.onchangedRelation()

    @Slot()
    def onchangedRelation(self,index=0):
        '''
        Handles the automated paramter suggestion for the current
        selected API Relation/Endpoint
        '''        
        #retrieve param-dict stored in setRelations-method
        params = self.relationEdit.itemData(index,Qt.UserRole)
        
        #Set name options nd build value dict
        values = {}
        nameoptions = []
        if params:
            for param in params:
                if param["required"]==True:
                    nameoptions.append([param["name"],param["doc"],True])
                    values[param["name"]] = param["default"]
                else:
                    nameoptions.insert(0,[param["name"],param["doc"]])        
        nameoptions.insert(0,((None,None,None)))
        self.paramEdit.setNameOptions(nameoptions)

        #Set value options
        # todo:  (V.3.5) Are there default values inside the JSON? If yes, they should be suggested
        self.paramEdit.setValueOptions([('',"No Value"),('<Object ID>',"The value in the Object ID-column of the datatree.")])

        #Set values
        self.paramEdit.setParams(values) 
        
    def initSession(self):
        with self.lock_session:
            if not hasattr(self, "session"):
                self.session = requests.Session()
        return self.session

    def request(self, path, args=None, headers=None, jsonify=True):
        """
        Start a new threadsafe session and request
        """

        session = self.initSession()
        if (not session):
            raise Exception("No session available.")

        try:
            if headers is not None:
                response = session.post(path, params=args, headers=headers, timeout=self.timeout, verify=False)
            else:
                response = session.get(path, params=args, timeout=self.timeout, verify=False)
        except (HTTPError, ConnectionError), e:
            raise Exception("Request Error: {0}".format(e.message))
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

    def disconnect(self):
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
        window.resize(1200, 800)
        window.setWindowTitle(caption)

        #create WebView with Facebook log-Dialog, OpenSSL needed        
        self.login_webview = QWebView(window)

        # Use the custom- WebPage class
        webpage = QWebPageCustom(self)
        webpage.logmessage.connect(self.mainWindow.logmessage)
        self.login_webview.setPage(webpage);

        #Connect to the getToken-method
        self.login_webview.urlChanged.connect(self.getToken)

        # Connect to the loadFinished-Slot for an error message
        self.login_webview.loadFinished.connect(self.loadFinished)

        self.login_webview.load(QUrl(url))
        self.login_webview.resize(window.size())
        self.login_webview.show()

        window.show()

    @Slot()
    def loadFinished(self, success):
        if (not success):
            self.mainWindow.logmessage('Error loading web page')


class FacebookTab(ApiTab):
    def __init__(self, mainWindow=None, loadSettings=True):
        super(FacebookTab, self).__init__(mainWindow, "Facebook")

        # Query Box
        self.setRelations()

        # Pages Box
        self.pagesEdit = QSpinBox(self)
        self.pagesEdit.setMinimum(1)
        self.pagesEdit.setMaximum(500)

        # Login-Boxes
        self.tokenEdit = QLineEdit()
        self.tokenEdit.setEchoMode(QLineEdit.Password)
        self.loginButton = QPushButton(" Login to Facebook ", self)
        self.loginButton.clicked.connect(self.doLogin)

        # Construct Login-Layout
        loginlayout = QHBoxLayout()
        loginlayout.addWidget(self.tokenEdit)
        loginlayout.addWidget(self.loginButton)

        # Construct main-Layout
        mainLayout = QFormLayout()
        mainLayout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        mainLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        mainLayout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        mainLayout.setLabelAlignment(Qt.AlignLeft)
        mainLayout.addRow("Resource", self.relationEdit)
        mainLayout.addRow("Parameters", self.paramEdit)
        mainLayout.addRow("Maximum pages", self.pagesEdit)
        mainLayout.addRow("Access Token", loginlayout)
        self.setLayout(mainLayout)

        if loadSettings:
            self.loadSettings()


    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {'relation': self.relationEdit.currentText(), 'pages': self.pagesEdit.value(),
                   'params': self.paramEdit.getParams()}

        # options for request
        if purpose != 'preset':
            options['querytype'] = self.name + ':' + self.relationEdit.currentText()
            options['accesstoken'] = self.tokenEdit.text()

        # options for data handling
        if purpose == 'fetch':
            options['objectid'] = 'id'
            options['nodedata'] = 'data' if ('/' in options['relation']) or (options['relation'] == 'search') else None

        return options

    def setOptions(self, options):
        self.relationEdit.setEditText(options.get('relation', 'object'))
        self.pagesEdit.setValue(int(options.get('pages', 1)))
        self.paramEdit.setParams(options.get('params', {}))
        if options.has_key('accesstoken'):
            self.tokenEdit.setText(options.get('accesstoken',''))

    def fetchData(self, nodedata, options=None, callback=None):
    # Preconditions
        if options['accesstoken'] == '':
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
                urlpath = "https://graph.facebook.com/" + options['relation']
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
                urlparams["access_token"] = options['accesstoken']
            else:
                urlpath = options['url']
                urlparams = options['params']

            self.mainWindow.logmessage("Fetching data for {0} from {1}".format(nodedata['objectid'],
                                                                               urlpath + "?" + urllib.urlencode(
                                                                                   urlparams)))

            # data
            options['querytime'] = str(datetime.now())
            data, headers, status = self.request(urlpath, urlparams)
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
    def doLogin(self, query=False, caption="Facebook Login Page",
                url="https://www.facebook.com/dialog/oauth?client_id=" + FACEBOOK_CLIENT_ID + "&redirect_uri=https://www.facebook.com/connect/login_success.html&response_type=token&scope=user_groups"):
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

        # Query and Parameter Box
        self.setRelations()

        # Pages-Box
        self.pagesEdit = QSpinBox(self)
        self.pagesEdit.setMinimum(1)
        self.pagesEdit.setMaximum(500)

        # LogIn Box
        self.tokenEdit = QLineEdit()
        self.tokenEdit.setEchoMode(QLineEdit.Password)
        self.tokensecretEdit = QLineEdit()
        self.tokensecretEdit.setEchoMode(QLineEdit.Password)
        self.loginButton = QPushButton(" Login to Twitter ", self)
        self.loginButton.clicked.connect(self.doLogin)

        # Construct login layout
        loginlayout = QHBoxLayout()
        loginlayout.addWidget(self.tokenEdit)
        loginlayout.addWidget(QLabel("Access Token Secret"))
        loginlayout.addWidget(self.tokensecretEdit)
        loginlayout.addWidget(self.loginButton)

        # Construct main-Layout
        mainLayout = QFormLayout()
        mainLayout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        mainLayout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        mainLayout.setLabelAlignment(Qt.AlignLeft)
        mainLayout.addRow("Resource", self.relationEdit)
        mainLayout.addRow("Parameters", self.paramEdit)
        mainLayout.addRow("Maximum pages", self.pagesEdit)
        mainLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        mainLayout.addRow("Access Token", loginlayout)
        self.setLayout(mainLayout)
        if loadSettings:
            self.loadSettings()

        # Twitter OAUTH consumer key and secret should be defined in credentials.py
        self.oauthdata = {}
        self.twitter = OAuth1Service(
            consumer_key=TWITTER_CONSUMER_KEY,
            consumer_secret=TWITTER_CONSUMER_SECRET,
            name='twitter',
            access_token_url='https://api.twitter.com/oauth/access_token',
            authorize_url='https://api.twitter.com/oauth/authorize',
            request_token_url='https://api.twitter.com/oauth/request_token',
            base_url='https://api.twitter.com/1.1/')

        


    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {'query': self.relationEdit.currentText(), 'params': self.paramEdit.getParams(),
                   'pages': self.pagesEdit.value()}

        # options for request
        if purpose != 'preset':
            options['querytype'] = self.name + ':' + self.relationEdit.currentText()
            options['access_token'] = self.tokenEdit.text()
            options['access_token_secret'] = self.tokensecretEdit.text()

        # options for data handling
        if purpose == 'fetch':
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
        self.paramEdit.setParams(options.get('params', {'q': '<Object ID>'}))
        self.pagesEdit.setValue(int(options.get('pages', 1)))
        # set Access-tokens,use generic method from APITab
        super(TwitterTab, self).setOptions(options)

    def initSession(self):
        if hasattr(self, "session"):
            return self.session

        elif (self.tokenEdit.text() != '') and (self.tokensecretEdit.text() != ''):
            self.session = self.twitter.get_session((self.tokenEdit.text(), self.tokensecretEdit.text()))
            return self.session

        else:
            raise Exception("No access, login please!")


    def fetchData(self, nodedata, options=None, callback=None):
        self.connected = True
        for page in range(0, options.get('pages', 1)):
            if not ('url' in options):
                urlpath = "https://api.twitter.com/1.1/" + options["query"] + ".json"
                urlpath, urlparams = self.getURL(urlpath, options["params"], nodedata)
            else:
                urlpath = options['url']
                urlparams = options["params"]

            self.mainWindow.logmessage("Fetching data for {0} from {1}".format(nodedata['objectid'],
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



            # paging-search
            paging = False
            if hasDictValue(data, "search_metadata.next_results"):
                paging = True
                url, params = self.parseURL(getDictValue(data, "search_metadata.next_results", False))
                options['url'] = urlpath
                options['params'] = params

            # paging timeline
            else:
                ids = [item['id'] for item in data if 'id' in item] if isinstance(data, list) else []
                if ids:
                    paging = True
                    options['params']['max_id'] = min(ids) - 1

            if not paging:
                break

            if not self.connected:
                break

    @Slot()
    def doLogin(self, query=False, caption="Twitter Login Page", url=""):

        self.oauthdata.pop('oauth_verifier', None)
        self.oauthdata['requesttoken'], self.oauthdata['requesttoken_secret'] = self.twitter.get_request_token(
            verify=False)

        # calls the doLogin-method of the parent
        super(TwitterTab, self).doLogin(query, caption, self.twitter.get_authorize_url(self.oauthdata['requesttoken']))


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

        # Construct login-Layout
        loginlayout = QHBoxLayout()

        loginlayout.addWidget(self.tokenEdit)
        loginlayout.addWidget(QLabel("Access Token Secret"))
        loginlayout.addWidget(self.tokensecretEdit)
        loginlayout.addWidget(self.loginButton)

        # Construct main-Layout
        mainLayout = QFormLayout()
        mainLayout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        mainLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        mainLayout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        mainLayout.setLabelAlignment(Qt.AlignLeft)
        mainLayout.addRow("Resource", self.relationEdit)
        mainLayout.addRow("Parameters", self.paramEdit)
        mainLayout.addRow("Access Token", loginlayout)
        if loadSettings:
            self.loadSettings()
        self.setLayout(mainLayout)

        # Twitter OAUTH consumer key and secret should be defined in credentials.py
        self.oauthdata = {}
        self.twitter = OAuth1Service(
            consumer_key=TWITTER_CONSUMER_KEY,
            consumer_secret=TWITTER_CONSUMER_SECRET,
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

        # options for data handling
        if purpose == 'fetch':
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
                                print self.retry_counter
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

    def disconnect(self):
        """Used to hardly disconnect the streaming client"""
        self.connected = False
        self.response.raw._fp.close()
        #self.response.close()

    def fetchData(self, nodedata, options=None, callback=None):
        if not ('url' in options):
            urlpath = "https://stream.twitter.com/1.1/" + options["query"] + ".json"
            urlpath, urlparams = self.getURL(urlpath, options["params"], nodedata)
        else:
            urlpath = options['url']
            urlparams = options["params"]

        self.mainWindow.logmessage(
            "Fetching data for {0} from {1}".format(nodedata['objectid'], urlpath + "?" + urllib.urlencode(urlparams)))
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
        #self.paramEdit.setNameOptions(['<None>', '<:id>', 'q'])
        #self.paramEdit.setValueOptions(['<None>', '<Object ID>'])
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
            "Fetching data for {0} from {1}".format(nodedata['objectid'], urlpath + "?" + urllib.urlencode(urlparams)))

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

        self.setLayout(mainLayout)
        if loadSettings: self.loadSettings()

    def download(self, path, args=None, headers=None, foldername=None):
        """
        Download files ...
        Uses the request-method without converting to json
        (argument jsonify==True)
        """

        def makefilename(extbymime=None):  # Create file name
            filename, fileext = os.path.splitext(os.path.basename(path))
            filetime = time.strftime("%Y-%m-%d-%H-%M-%S")
            filenumber = 1
            if extbymime:
                fileext = extbymime

            while True:
                fullfilename = os.path.join(foldername,
                                            filename + '-' + filetime + '-' + str(filenumber) + str(fileext))
                if (os.path.isfile(fullfilename)):
                    filenumber = filenumber + 1
                else:
                    break
            return fullfilename

        response = self.request(path, args, headers, jsonify=False)

        # Handle the response of the generic, non-json-returning response
        if response.status_code == 200:
            guessed_ext = guess_all_extensions(response.headers["content-type"])
            guessed_ext = guessed_ext[-1] if len(guessed_ext) > 0 else None

            fullfilename = makefilename(guessed_ext)
            with open(fullfilename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            data = {'filename': os.path.basename(fullfilename), 'targetpath': fullfilename, 'sourcepath': path,
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


    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {}

        if purpose != 'preset':
            options['querytype'] = self.name

        options['urlpath'] = self.urlpathEdit.currentText()
        options['folder'] = self.folderEdit.text()
        options['nodedata'] = None
        options['objectid'] = 'filename'

        return options

    def setOptions(self, options):
        self.urlpathEdit.setEditText(options.get('urlpath', '<url>'))
        self.folderEdit.setText(options.get('folder', ''))

    def fetchData(self, nodedata, options=None, callback=None):
        self.connected = True
        foldername = options.get('folder', None)
        if (foldername is None) or (not os.path.isdir(foldername)):
            raise Exception("Folder does not exists, select download folder, please!")

        urlpath, urlparams = self.getURL(options["urlpath"], {}, nodedata)

        self.mainWindow.logmessage("Downloading file for {0} from {1}".format(nodedata['objectid'],
                                                                              urlpath + "?" + urllib.urlencode(
                                                                                  urlparams)))

        data, headers, status = self.download(urlpath, urlparams, None, foldername)
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
