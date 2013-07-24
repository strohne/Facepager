from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtWebKit import QWebView, QWebPage
import urlparse
import requests
from requests.exceptions import *
from datetime import datetime, timedelta
from components import *
from rauth import OAuth1Service
from utilities import *
import re
import json



def loadTabs(mainWindow=None):                    
    mainWindow.RequestTabs.addTab(FacebookTab(mainWindow),"Facebook")
    mainWindow.RequestTabs.addTab(TwitterTab(mainWindow),"Twitter")
    mainWindow.RequestTabs.addTab(GenericTab(mainWindow),"Generic")    
    
class ApiTab(QWidget):
    def __init__(self, mainWindow=None,name="NoName",loadSettings=True):
        QWidget.__init__(self, mainWindow)
        self.timeout=None
        self.mainWindow=mainWindow
        self.name=name

    def idtostr(self,val):
        try:
            return str(val)
        except UnicodeEncodeError as e:
            return val.encode('utf-8')     

    def getvalue(self,key,nodedata):
        if key == '<Object ID>':        
          return self.idtostr(nodedata['objectid'])
        else:
            match = re.match("^<(.*)>$",key)
            if match:                 
                 return getDictValue(nodedata['response'],match.group(1))
            else:  
                return key
        
    def getOptions(self,purpose='fetch'): #purpose = 'fetch'|'settings'|'preset'
        return {}
    
    def setOptions(self,options):
        pass
    
    def saveSettings(self):
        self.mainWindow.settings.beginGroup("ApiModule_"+self.name)
        options=self.getOptions('settings')

        for key in options.keys():        
            self.mainWindow.settings.setValue(key,options[key])
        self.mainWindow.settings.endGroup()
                                          
    def loadSettings(self):
        #self.setOptions({})       
        #return (False) 
        self.mainWindow.settings.beginGroup("ApiModule_"+self.name)
        options={}
        for key in self.mainWindow.settings.allKeys():        
            options[key] = self.mainWindow.settings.value(key)
        self.mainWindow.settings.endGroup()
        
        self.setOptions(options)                                    

    def initSession(self):
        if not hasattr(self,"session"):
            self.session = requests.Session()
        return self.session

                
    def request(self, path, args=None,headers=None):
        session = self.initSession()            
        if (not session): raise Exception("No session available.")        
                
        try:
            if headers != None:
                response = session.post(path,params=args,headers=headers,timeout=self.timeout,verify=False)
            else:
                response = session.get(path,params=args,timeout=self.timeout,verify=False)
        except (HTTPError,ConnectionError),e: 
            raise Exception("Request Error: {0}".format(e.message))
        else:
            if not response.ok:
                raise Exception("Request Status Error: {0}".format(response.reason))
            elif not response.json():
                raise Exception("Request Format Error: No JSON data!")
                
            else:    
                return response.json()     

    @Slot()
    def doLogin(self,query=False,caption='',url=''):
        self.doQuery=query
        window = QMainWindow(self.mainWindow)
        window.resize(1200,800)
        window.setWindowTitle(caption)
        
        #create WebView with Facebook log-Dialog, OpenSSL needed        
        self.login_webview=QWebView(window)
        
        webpage = QWebPageCustom(self)
        webpage.logmessage.connect(self.mainWindow.logmessage)   
        self.login_webview.setPage(webpage);
        self.login_webview.urlChanged.connect(self.getToken)
        self.login_webview.loadFinished.connect(self.loadFinished)
        
        self.login_webview.load(QUrl(url))
        self.login_webview.resize(window.size())
        self.login_webview.show()
        
        window.show()
            
    @Slot()            
    def loadFinished(self,success):
        if (not success): self.mainWindow.logmessage('Error loading web page')    
        
class FacebookTab(ApiTab):

    def __init__(self, mainWindow=None,loadSettings=True):
        super(FacebookTab,self).__init__(mainWindow,"Facebook")

        mainLayout = QFormLayout()
                
        #-Query Type
        self.relationEdit=QComboBox(self)
        self.relationEdit.insertItems(0,['<self>','<search>','feed','posts','comments','likes','global_brand_children','groups','insights','members','picture','docs','noreply','invited','attending','maybe','declined','videos','accounts','achievements','activities','albums','books','checkins','events','family','friendlists','friends','games','home','interests','links','locations','movies','music','notes','photos','questions','scores','statuses','subscribedto','tagged','television'])        
        self.relationEdit.setEditable(True)
        mainLayout.addRow("Query",self.relationEdit)

        #-Since
        self.sinceEdit=QDateEdit(self)
        self.sinceEdit.setDate(datetime.today()-timedelta( days=7))
        mainLayout.addRow("Since",self.sinceEdit)
        

        #-Until
        self.untilEdit=QDateEdit(self)
        self.untilEdit.setDate(datetime.today())
        mainLayout.addRow("Until",self.untilEdit)
        
        #-Offset
        self.offsetEdit=QSpinBox(self)
        self.offsetEdit.setMaximum(500)
        self.offsetEdit.setMinimum(0)
        self.offsetEdit.setValue(0)
        mainLayout.addRow("Offset",self.offsetEdit)

        #-Limit
        self.limitEdit=QSpinBox(self)
        self.limitEdit.setMaximum(1000)
        self.limitEdit.setMinimum(1)
        self.limitEdit.setValue(50)
        mainLayout.addRow("Limit",self.limitEdit)

        #-Log in
        loginlayout=QHBoxLayout()
        
        self.tokenEdit=QLineEdit()
        self.tokenEdit.setEchoMode(QLineEdit.Password)
        loginlayout.addWidget(self.tokenEdit)

        self.loginButton=QPushButton(" Login to Facebook ", self)
        self.loginButton.clicked.connect(self.doLogin)
        loginlayout.addWidget(self.loginButton)
        
        mainLayout.addRow("Access Token",loginlayout)
                
        self.setLayout(mainLayout)
        if loadSettings: self.loadSettings()
        
    def getOptions(self,purpose='fetch'): #purpose = 'fetch'|'settings'|'preset'     
        options={}                
        
        #options for request                
        options['relation']=self.relationEdit.currentText()
        options['since']=self.sinceEdit.date().toString("yyyy-MM-dd")
        options['until']=self.untilEdit.date().toString("yyyy-MM-dd")
        options['offset']=self.offsetEdit.value()
        options['limit']=self.limitEdit.value()
        
        if purpose != 'preset':
            options['querytype']=self.name+':'+self.relationEdit.currentText()
            options['accesstoken']= self.tokenEdit.text() # self.accesstoken # None #"109906609107292|_3rxWMZ_v1UoRroMVkbGKs_ammI"
                
        #options for data handling
        if purpose == 'fetch':
            options['objectid']='id'            
            options['nodedata']=None if (options['relation']=='<self>') else 'data'
               
        return options        

    def setOptions(self,options):         
        self.relationEdit.setEditText(options.get('relation','<self>'))        
        if options.has_key('since'): self.sinceEdit.setDate(datetime.strptime(options['since'],"%Y-%m-%d"))
        if options.has_key('until'): self.untilEdit.setDate(datetime.strptime(options['until'],"%Y-%m-%d"))
        self.offsetEdit.setValue(int(options.get('offset',0)))
        self.limitEdit.setValue(int(options.get('limit',50)))
        if options.has_key('accesstoken'): self.tokenEdit.setText(options.get('accesstoken','')) 


    def fetchData(self,nodedata,options=None):          
        if (options==None): options = self.getOptions()
        if (options['accesstoken'] == ""): raise Exception("Access token is missing, login please!")

        if nodedata['objectid']==None:
            raise Exception("Empty object id")
            
        #build url        
        if options['relation']=='<self>':
            urlpath=self.idtostr(nodedata['objectid'])
            urlparams={'metadata':'1'}

        elif options['relation']=='<search>':
            urlpath='search'
            urlparams={'q':self.idtostr(nodedata['objectid']),'type':'page'}
        
        else:
            urlpath=self.idtostr(nodedata['objectid'])+'/'+options['relation']            
            urlparams= { key: options[key] for key in ['limit','offset','since','until'] }                   
                
        urlparams["access_token"] =   options['accesstoken']         
        urlpath = "https://graph.facebook.com/" + urlpath
        
        self.mainWindow.logmessage("Fetching data for "+nodedata['objectid']+" from "+urlpath+" with params "+json.dumps(urlparams))
        return self.request(urlpath,urlparams)          


    @Slot()
    def doLogin(self,query=False,caption="Facebook Login Page",url="https://www.facebook.com/dialog/oauth?client_id=109906609107292&redirect_uri=https://www.facebook.com/connect/login_success.html&response_type=token&scope=user_groups"):
        super(FacebookTab,self).doLogin(query,caption,url)
        
    @Slot()
    def getToken(self):
        url = urlparse.parse_qs(self.login_webview.url().toString())
        if url.has_key("https://www.facebook.com/connect/login_success.html#access_token"):
            token=url["https://www.facebook.com/connect/login_success.html#access_token"]
            if token:
                self.tokenEdit.setText(token[0])
                self.login_webview.parent().close()
                #if (self.doQuery == True): self.mainWindow.actions.queryNodes()
           


        


class TwitterTab(ApiTab):

    def __init__(self, mainWindow=None,loadSettings=True):
        super(TwitterTab,self).__init__(mainWindow,"Twitter")

        mainLayout = QFormLayout()
                
        #-Query Type
        self.relationEdit=QComboBox(self)
        
        self.relationEdit.insertItems(0,['users/show','users/search'])      
        self.relationEdit.insertItems(0,['followers/list','friends/list'])        
        self.relationEdit.insertItems(0,['statuses/show/:id','statuses/retweets/:id'])
        self.relationEdit.insertItems(0,['statuses/user_timeline'])                       
        self.relationEdit.insertItems(0,['search/tweets'])
        
        self.relationEdit.setEditable(True)
        mainLayout.addRow("Resource",self.relationEdit)
        
        #Twitter OAUTH consumer key and secret (should be kept secret on github
        #in the future!!)        
        self.oauthdata = {
             'consumer_key':'BXczKRXJpd8VSogbEA',
             'consumer_secret':'beanc6H8c1Q27NpH26OMX3URDS9nyrbiyUGKQJS8M8'             
        }
        
        #see the overcomplicated OAuth1 Handshake here https://github.com/litl/rauth
        self.twitter = OAuth1Service(
                            consumer_key=self.oauthdata['consumer_key'],
                            consumer_secret=self.oauthdata['consumer_secret'],
                            name='twitter',
                            access_token_url='https://api.twitter.com/oauth/access_token',
                            authorize_url='https://api.twitter.com/oauth/authorize',
                            request_token_url='https://api.twitter.com/oauth/request_token',
                            base_url='https://api.twitter.com/1.1/')


         
        #Parameter
        self.paramEdit = QParamEdit(self)
        self.paramEdit.setNameOptions(['<None>','<:id>','q','screen_name','user_id']) #'count','until'
        self.paramEdit.setValueOptions(['<None>','<Object ID>'])
        
        mainLayout.addRow("Parameters",self.paramEdit)
 
        #-Log in
        loginlayout=QHBoxLayout()
        
        self.tokenEdit=QLineEdit()
        self.tokenEdit.setEchoMode(QLineEdit.Password)
        loginlayout.addWidget(self.tokenEdit)
        
        loginlayout.addWidget(QLabel("Access Token Secret"))

        self.tokensecretEdit=QLineEdit()
        self.tokensecretEdit.setEchoMode(QLineEdit.Password)
        loginlayout.addWidget(self.tokensecretEdit)

        self.loginButton=QPushButton(" Login to Twitter ", self)
        self.loginButton.clicked.connect(self.doLogin)
        loginlayout.addWidget(self.loginButton)
        
        mainLayout.addRow("Access Token",loginlayout)

                 
        self.setLayout(mainLayout)
        if loadSettings: self.loadSettings()
  
              
    def getOptions(self,purpose='fetch'): #purpose = 'fetch'|'settings'|'preset'      
        options={}
        
        #options for request 
        options['query'] = self.relationEdit.currentText()        
        options['params']=self.paramEdit.getParams()
        
        if purpose != 'preset':
            options['querytype']=self.name+':'+self.relationEdit.currentText()
            options['access_token'] = self.tokenEdit.text() 
            options['access_token_secret'] = self.tokensecretEdit.text()
                
        #options for data handling
        if purpose == 'fetch':                 
            options['objectid']='id'
            
            if (options["query"] == 'search/tweets'):
                options['nodedata']='statuses'
            elif (options["query"] == 'followers/list'):
                options['nodedata']='users'
            elif (options["query"] == 'friends/list'):
                options['nodedata']='users'
            else:
                options['nodedata']=None    
                        
        return options


    def setOptions(self,options):         
        self.relationEdit.setEditText(options.get('query','search/tweets'))        
        self.paramEdit.setParams(options.get('params',{'q':'<Object ID'}))
        if options.has_key('access_token'): self.tokenEdit.setText(options.get('access_token',''))
        if options.has_key('access_token_secret'): self.tokensecretEdit.setText(options.get('access_token_secret',''))
        
    def initSession(self):
        if hasattr(self,"session"):
            return self.session
                
        elif (self.tokenEdit.text() != '') and (self.tokensecretEdit.text() != ''):                  
            self.session=self.twitter.get_session((self.tokenEdit.text(), self.tokensecretEdit.text()))
            return self.session
                    
        else:
            #self.doLogin(True)
            raise Exception("No access, login please!")

    
    def fetchData(self,nodedata,options=None):
        if (options==None): options = self.getOptions()
        
        #Resource
        urlpath = "https://api.twitter.com/1.1/"+options["query"]+".json"
        
        #Params
        urlparams = {}                                
        for name in options["params"]:
            if (name == '<None>') | (name == ''): continue
            if (options["params"][name] == '<None>') | (options["params"][name] == ''): continue
                        
            value = self.getvalue(options["params"][name],nodedata)             
             
            if name == '<:id>':
              urlpath = urlpath.replace(':id',value)                                        
            else:
              urlparams[name] = value
                

        self.mainWindow.logmessage("Fetching data for {0} from {1} with params \
                {2}".format(nodedata['objectid'],urlpath,urlparams))                    
 
        return self.request(urlpath,urlparams)
    
    @Slot()
    def doLogin(self,query=False,caption="Twitter Login Page",url=""):

        self.oauthdata.pop('oauth_verifier',None)
        self.oauthdata['requesttoken'],self.oauthdata['requesttoken_secret']=self.twitter.get_request_token(verify=False)
        
        super(TwitterTab,self).doLogin(query,caption,self.twitter.get_authorize_url(self.oauthdata['requesttoken']))


    @Slot()
    def getToken(self):
        url = urlparse.parse_qs(self.login_webview.url().toString())
        if "oauth_verifier" in url:
            token=url["oauth_verifier"]
            if token:
                self.oauthdata['oauth_verifier'] = token[0]
                self.session=self.twitter.get_auth_session(self.oauthdata['requesttoken'],
                                            self.oauthdata['requesttoken_secret'],method="POST",
                                            data={'oauth_verifier':self.oauthdata['oauth_verifier']},verify=False)
                
                              
                self.tokenEdit.setText(self.session.access_token)
                self.tokensecretEdit.setText(self.session.access_token_secret)              
                
                self.login_webview.parent().close()
                #if (self.doQuery == True): self.mainWindow.actions.queryNodes()


class GenericTab(ApiTab):

    #Youtube: 
    #URL prefix: https://gdata.youtube.com/feeds/api/videos?alt=json&v=2&q=
    #URL field: <Object ID>
    #URL suffix: 
    #-Extract: data.feed.entry
    #-ObjectId: id.$t

    def __init__(self, mainWindow=None,loadSettings=True):
        super(GenericTab,self).__init__(mainWindow,"Generic")
        mainLayout = QFormLayout()
                
        #URL prefix 
        self.prefixEdit=QComboBox(self)        
        self.prefixEdit.insertItems(0,['https://api.twitter.com/1/statuses/user_timeline.json?screen_name='])
        self.prefixEdit.insertItems(0,['https://gdata.youtube.com/feeds/api/videos?alt=json&v=2&q='])
                       
        self.prefixEdit.setEditable(True)
        mainLayout.addRow("URL prefix",self.prefixEdit)

        #URL field 
        self.fieldEdit=QComboBox(self)
        self.fieldEdit.insertItems(0,['<Object ID>','<None>'])       
        self.fieldEdit.setEditable(True)        
        mainLayout.addRow("URL field",self.fieldEdit)
        
        #URL suffix 
        self.suffixEdit=QComboBox(self)
        self.suffixEdit.insertItems(0,[''])       
        self.suffixEdit.setEditable(True)        
        mainLayout.addRow("URL suffix",self.suffixEdit)
        

        #Extract option 
        self.extractEdit=QComboBox(self)
        #self.extractEdit.insertItems(0,['data'])
        self.extractEdit.insertItems(0,['matches'])      
        self.extractEdit.insertItems(0,['feed.entry'])        
                 
        self.extractEdit.setEditable(True)
        mainLayout.addRow("Key to extract",self.extractEdit)

        self.objectidEdit=QComboBox(self)
        self.objectidEdit.insertItems(0,['id.$t'])              
        self.objectidEdit.setEditable(True)
        mainLayout.addRow("Key for ObjectID",self.objectidEdit)


        self.setLayout(mainLayout)
        if loadSettings: self.loadSettings()
        
    def getOptions(self,purpose='fetch'): #purpose = 'fetch'|'settings'|'preset'      
        options={}
        
        #options for request 
        options['querytype']='generic'
        options['prefix']=self.prefixEdit.currentText()
        options['suffix']=self.suffixEdit.currentText()
        options['urlfield']=self.fieldEdit.currentText()
                
        #options for data handling
        options['nodedata']=self.extractEdit.currentText() if self.extractEdit.currentText() != "" else None
        options['objectid']=self.objectidEdit.currentText() if self.objectidEdit.currentText() != "" else None                                     
        
        return options  

    def setOptions(self,options):         
        self.prefixEdit.setEditText(options.get('prefix','https://gdata.youtube.com/feeds/api/videos?alt=json&v=2&q='))        
        self.fieldEdit.setEditText(options.get('urlfield','<Object ID>'))
        self.suffixEdit.setEditText(options.get('suffix',''))
        self.extractEdit.setEditText(options.get('nodedata','data.feed.entry'))
        self.objectidEdit.setEditText(options.get('objectid','id.$t'))
        
        
    def fetchData(self,nodedata,options=None):
        if (options==None): options = self.getOptions()
    
        if(options['urlfield']=='<Object ID>'): 
            queryterm=self.idtostr(nodedata['objectid'])
        elif((options['urlfield']=='<None>') | (options['urlfield']=='')):
            queryterm=''
        else:    
            queryterm=nodedata[options['urlfield']]
                        
                 
        urlpath = options["prefix"]+queryterm+options["suffix"]        
        
        self.mainWindow.logmessage("Fetching data for "+self.idtostr(nodedata['objectid'])+" from "+urlpath)    
        return self.request(urlpath)       



class QWebPageCustom(QWebPage):
    
    logmessage = Signal(str)
    
    def supportsExtension(self,extension): 
        if (extension == QWebPage.ErrorPageExtension):
            return True
        else:
            return False
    
    def extension(self,extension,option=0,output=0):
        if (extension != QWebPage.ErrorPageExtension): return False
         
        if (option.domain == QWebPage.QtNetwork):
            msg = "Network error ("+ str(option.error)+"): "+option.errorString
                   
        elif (option.domain == QWebPage.Http):
            msg = "HTTP error ("+ str(option.error)+"): "+option.errorString
            
        elif(option.domain == QWebPage.WebKit):
            msg = "WebKit error ("+ str(option.error)+"): "+option.errorString    
        else:
            msg = option.errorString
                
        print(option.url)
        print(msg)
        
        self.logmessage.emit(msg)
                
        return False;        

