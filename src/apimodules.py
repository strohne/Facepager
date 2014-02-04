from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtWebKit import QWebView, QWebPage
import urlparse
import urllib
import requests
from mimetypes import guess_all_extensions
from requests.exceptions import *
from datetime import datetime, timedelta
from paramedit import *
from rauth import OAuth1Service
from utilities import *
import re
import json
from credentials import *
import os
import time
import dateutil.parser
from collections import OrderedDict
import threading
import Queue


class ApiThread(threading.Thread):
    def __init__(self, input, output, module, pool):
        threading.Thread.__init__(self)
        #self.daemon = True
        self.pool = pool
        self.input = input
        self.output = output
        self.module = module
        self.halt = threading.Event()

    def run(self):
        def streamingData(data, options, headers, streamingTab=False):
            out = {'nodeindex': job['nodeindex'], 'data': data, 'options': options, 'headers': headers}
            if streamingTab:
                out["streamprogress"] = True
            self.output.put(out)

        try:
            while not self.halt.isSet():
                try:
                    time.sleep(0)
                    job = self.input.get()
                    try:
                        if job is None:
                            self.halt.set()
                        else:
                            self.module.fetchData(job['data'], job['options'], streamingData)
                    finally:
                        self.input.task_done()
                        if job is not None:
                            self.output.put({'progress': job.get('number', 0)})
                except Exception as e:
                    self.module.mainWindow.logmessage(e)
        finally:
            self.pool.threadFinished()


class ApiThreadPool():
    def __init__(self, module):
        self.input = Queue.Queue()
        self.output = Queue.Queue(100)
        self.module = module
        self.threads = []
        self.pool_lock = threading.Lock()
        self.threadcount = 0

    def addJob(self, job):
        self.input.put(job)

    def getJob(self):
        try:
            if self.output.empty():
                job = {'waiting': True}
            else:
                job = self.output.get(True, 1)
                self.output.task_done()
        except Queue.Empty as e:
            job = {'waiting': True}
        finally:
            return job

    def processJobs(self):
        with self.pool_lock:
            if self.input.qsize > 50:
                maxthreads = 5
            elif self.input.qsize > 10:
                maxthreads = 2
            else:
                maxthreads = 1

            self.threads = []
            for x in range(maxthreads):
                self.addJob(None)  # sentinel empty job
                thread = ApiThread(self.input, self.output, self.module, self)
                self.threadcount += 1
                self.threads.append(thread)
                thread.start()

    def stopJobs(self):
        for thread in self.threads:
            thread.halt.set()
        self.module.connected = False

    def threadFinished(self):
        with self.pool_lock:
            self.threadcount -= 1
            if (self.threadcount == 0):
                with self.input.mutex:
                    self.input.queue.clear()
                self.output.put(None) #sentinel


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

        #Replace placeholders in urlpath
        matches = re.findall("<([^>]*)>", urlpath)
        for match in matches:
            if match == 'Object ID':
                value = self.idtostr(nodedata['objectid'])
            else:
                value = getDictValue(nodedata['response'], match)
            urlpath = urlpath.replace('<' + match + '>', value)

            #Replace placeholders in params
        urlpath, urlparams = self.parseURL(urlpath)
        for name in params:
            if (name == '<None>') | (name == ''):
                continue
            if (params[name] == '<None>') | (params[name] == ''):
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

            urlparams[name] = value

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
        self.relationEdit = QComboBox(self)
        self.relationEdit.insertItems(0, ['<Object ID>', 'search', '<Object ID>/feed', '<Object ID>/posts',
                                          '<Object ID>/comments', '<Object ID>/likes',
                                          '<Object ID>/global_brand_children', '<Object ID>/groups',
                                          '<Object ID>/insights', '<Object ID>/members', '<Object ID>/picture',
                                          '<Object ID>/docs', '<Object ID>/noreply', '<Object ID>/invited',
                                          '<Object ID>/attending', '<Object ID>/maybe', '<Object ID>/declined',
                                          '<Object ID>/videos', '<Object ID>/accounts', '<Object ID>/achievements',
                                          '<Object ID>/activities', '<Object ID>/albums', '<Object ID>/books',
                                          '<Object ID>/checkins', '<Object ID>/events', '<Object ID>/family',
                                          '<Object ID>/friendlists', '<Object ID>/friends', '<Object ID>/games',
                                          '<Object ID>/home', '<Object ID>/interests', '<Object ID>/links',
                                          '<Object ID>/locations', '<Object ID>/movies', '<Object ID>/music',
                                          '<Object ID>/notes', '<Object ID>/photos', '<Object ID>/questions',
                                          '<Object ID>/scores', '<Object ID>/statuses', '<Object ID>/subscribedto',
                                          '<Object ID>/tagged', '<Object ID>/television'])
        self.relationEdit.setEditable(True)

        # Param Box
        self.paramEdit = QParamEdit(self)
        self.paramEdit.setNameOptions(['<None>', 'since', 'until', 'offset', 'limit', 'type'])
        self.paramEdit.setValueOptions(['<None>', '2013-07-17', 'page'])

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

        # Query Box
        self.relationEdit = QComboBox(self)
        self.relationEdit.insertItems(0, ['search/tweets'])
        self.relationEdit.insertItems(0, ['users/show', 'users/search'])
        self.relationEdit.insertItems(0, ['followers/list', 'friends/list'])
        self.relationEdit.insertItems(0, ['statuses/show/<Object ID>', 'statuses/retweets/<Object ID>'])
        self.relationEdit.insertItems(0, ['statuses/user_timeline'])
        self.relationEdit.setEditable(True)

        # Parameter-Box
        self.paramEdit = QParamEdit(self)
        self.paramEdit.setNameOptions(
            ['<None>', 'q', 'screen_name', 'user_id', 'count', 'result_type'])  # 'count','until'
        self.paramEdit.setValueOptions(['<None>', '<Object ID>'])

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
        self.relationEdit = QComboBox(self)
        self.relationEdit.insertItems(0, ['statuses/sample'])
        self.relationEdit.insertItems(0, ['statuses/filter'])
        self.relationEdit.setEditable(True)

        # Construct Parameter-Edit
        self.paramEdit = QParamEdit(self)

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
        try:
            self.initSession()

            def _send():
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
                        self.on_timeout()
                    else:
                        if response.status_code != 200:
                            self._on_error(response.status_code, response.content)

                        return response

            while self.connected:
                response = _send()

                for line in response.iter_lines():
                    #QApplication.processEvents()
                    if not self.connected:
                        break
                    if line:
                        try:
                            data = json.loads(line)
                            #print data
                        except ValueError:  # pragma: no cover
                            self._on_error(response.status_code, 'Unable to decode response, not valid JSON.')
                        else:
                            yield data
            response.close()

        finally:
            self.connected = False



    def _on_delete(self, data):
        # Hier koennte man delete messages verabeiten
        pass

    def _on_error(self, status_code, data):  # pragma: no cover
        """Called when stream returns non-200 status code
        Feel free to override this to handle your streaming data how you
        want it handled.
        :param status_code: Non-200 status code sent from stream
        :type status_code: int
        :param data: Error message sent from stream
        :type data: dict
        """
        raise Exception("Error, Status Code " + str(status_code))

    def _on_timeout(self):  # pragma: no cover
        """ Called when the request has timed out """
        return

    def _disconnect(self):
        """Used to disconnect the streaming client manually"""
        self.connected = False

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
        self.paramEdit.setNameOptions(['<None>', '<:id>', 'q'])
        self.paramEdit.setValueOptions(['<None>', '<Object ID>'])
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
