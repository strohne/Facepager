from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtWebKit import QWebView, QWebPage
import urlparse
import urllib,urllib2
from datetime import datetime, timedelta
from components import *

# Find a JSON parser
try:
    import simplejson as json
except ImportError:
    try:
        from django.utils import simplejson as json
    except ImportError:
        import json
_parse_json = json.loads



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

    def getOptions(self):
        return {}
    
    def setOptions(self,options):
        pass
    
    def saveSettings(self):
        self.mainWindow.settings.beginGroup("ApiModule_"+self.name)
        options=self.getOptions(True)

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
        
    def request(self, path, args=None,headers={}):
        
        path=path + "?" +urllib.urlencode(args) if args else path
        
        try:
            req = urllib2.Request(path,headers=headers)
            file = urllib2.urlopen(req,timeout=self.timeout)
        except urllib2.HTTPError, e:
            response = _parse_json(e.read())
            raise RequesterError(response)
        except TypeError:
            # Timeout support for Python <2.6
            if self.timeout:
                socket.setdefaulttimeout(self.timeout)
            file = urllib2.urlopen(path, post_data)
        try:
            fileInfo = file.info()
            if fileInfo.maintype == 'text':
                content=file.read()
                
                #f = open('D:/temp/log.txt', 'w')
                #f.write(content)
                #f.close()
                 
                response = _parse_json(content)
            elif fileInfo.maintype == 'image':
                mimetype = fileInfo['content-type']
                response = {
                    "data": file.read(),
                    "mime-type": mimetype,
                    "url": file.url,
                }
            elif fileInfo.maintype == 'application':
                response = {"data": _parse_json(file.read())}                
            else:
                raise RequesterError('Maintype was not text or image')
        finally:
            file.close()
        if response and isinstance(response, dict) and response.get("error"):
            raise RequesterError(response["error"]["type"],
                                response["error"]["message"])
        return response    
        
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
        
    def getOptions(self,persistent=False):      
        options={}                
        
        #options for request        
        options['querytype']=self.name+':'+self.relationEdit.currentText()
        options['relation']=self.relationEdit.currentText()
        options['since']=self.sinceEdit.date().toString("yyyy-MM-dd")
        options['until']=self.untilEdit.date().toString("yyyy-MM-dd")
        options['offset']=self.offsetEdit.value()
        options['limit']=self.limitEdit.value()
        options['accesstoken']= self.tokenEdit.text() # self.accesstoken # None #"109906609107292|_3rxWMZ_v1UoRroMVkbGKs_ammI"
        if (options['accesstoken'] == ""): self.doLogin(True)
        
        #options for data handling
        if not persistent:
            options['objectid']='id'
            
            if (options['relation']=='<self>'):
                options['nodedata']=None
            else:  
                options['nodedata']='data'
               
        return options        

    def setOptions(self,options):         
        self.relationEdit.setEditText(options.get('relation','<self>'))        
        if options.has_key('since'): self.sinceEdit.setDate(datetime.strptime(options['since'],"%Y-%m-%d"))
        if options.has_key('until'): self.untilEdit.setDate(datetime.strptime(options['until'],"%Y-%m-%d"))
        self.offsetEdit.setValue(options.get('offset',0))
        self.limitEdit.setValue(options.get('limit',50))
        self.tokenEdit.setText(options.get('accesstoken','')) 


    def fetchData(self,nodedata,options=None):
        if (options==None): options = self.getOptions()
        if (options['accesstoken'] == ""): raise RequesterError("Access token is missing")

        if nodedata['objectid']==None:
            raise RequesterError("Empty object id")
            
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
    def doLogin(self,query=False):
        self.doQuery=query
        window = QMainWindow(self.mainWindow)
        window.resize(1200,800)
        window.setWindowTitle("Facebook Login Page")
        
        #create WebView with Facebook log-Dialog, OpenSSL needed        
        self.login_webview=QWebView(window)
        
        webpage = QWebPageCustom(self)
        webpage.logmessage.connect(self.mainWindow.logmessage)   
        self.login_webview.setPage(webpage);
        self.login_webview.urlChanged.connect(self.getToken)
        self.login_webview.loadFinished.connect(self.loadFinished)
        
        self.login_webview.load(QUrl("https://www.facebook.com/dialog/oauth?client_id=109906609107292&redirect_uri=https://www.facebook.com/connect/login_success.html&response_type=token&scope=user_groups"))
        self.login_webview.resize(window.size())
        self.login_webview.show()
        
        window.show()

    @Slot()
    def getToken(self):
        url = urlparse.parse_qs(self.login_webview.url().toString())
        if url.has_key("https://www.facebook.com/connect/login_success.html#access_token"):
            token=url["https://www.facebook.com/connect/login_success.html#access_token"]
            if token:
                self.tokenEdit.setText(token[0])
                self.login_webview.parent().close()
                if (self.doQuery == True): self.mainWindow.actions.queryNodes()
           
    @Slot()            
    def loadFinished(self,success):
        if (not success): self.mainWindow.logmessage('Error loading web page')

        


class TwitterTab(ApiTab):

    def __init__(self, mainWindow=None,loadSettings=True):
        super(TwitterTab,self).__init__(mainWindow,"Twitter")

        mainLayout = QFormLayout()
                
        #-Query Type
        self.relationEdit=QComboBox(self)
        
        self.relationEdit.insertItems(0,['users/lookup','users/show''users/search'])      
        self.relationEdit.insertItems(0,['followers/list','followers/ids','friends/list','friends/ids'])        
        self.relationEdit.insertItems(0,['statuses/retweeters/ids','statuses/show/:id','statuses/retweets/:id','statuses/retweets_of_me'])
        self.relationEdit.insertItems(0,['statuses/home_timeline','statuses/mentions_timeline','statuses/user_timeline'])                       
        self.relationEdit.insertItems(0,['search/tweets'])
        
        self.relationEdit.setEditable(True)
        mainLayout.addRow("Resource",self.relationEdit)

         
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

        self.loginButton=QPushButton(" Login to Twitter ", self)
        self.loginButton.clicked.connect(self.doLogin)
        loginlayout.addWidget(self.loginButton)
        
        mainLayout.addRow("Access Token",loginlayout)

                 
        self.setLayout(mainLayout)
        if loadSettings: self.loadSettings()
  
              
    def getOptions(self,persistent=False):      
        options={}
        
        #options for request 
        options['query'] = self.relationEdit.currentText()
        options['querytype']=self.name+':'+self.relationEdit.currentText()
        options['params']=self.paramEdit.getParams()
                
        #options for data handling
        if not persistent:                 
            options['objectid']='id'
            #options['nodedata']='data.results' if (options["query"] == '<search>')  else 'data'                        
            options['nodedata']='data'
        
        return options  

    def setOptions(self,options):         
        self.relationEdit.setEditText(options.get('query','search/tweets'))        
        self.paramEdit.setParams(options.get('params',{'q':'<Object ID'}))
    
    def fetchData(self,nodedata,options=None):
        if (options==None): options = self.getOptions()
        
        #Resource
        urlpath = "https://api.twitter.com/1.1/"+options["query"]+".json"
        
        #Params
        urlparams = {}                                
        for name in options["params"]:
            if (name == '<None>') | (name == ''): continue
            if (options["params"][name] == '<None>') | (options["params"][name] == ''): continue
                        
            value = self.idtostr(nodedata['objectid']) if options["params"][name] == '<Object ID>' else nodedata[options[options["params"][name]]] 
            if name == '<:id>':
              urlpath = urlpath.replace(':id',value)                                        
            else:
              urlparams[name] = value
                
        #Authentication
#        self.oauth={
#            "oauth_consumer_key":"xvz1evFS4wEEPTGEFPHBog",
#            "oauth_nonce":"kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg", 
#            "oauth_signature":"tnnArxj06cWHq44gCs1OSKk%2FjLY%3D", 
#            "oauth_signature_method":"HMAC-SHA1", 
#            "oauth_timestamp":"1318622958", 
#            "oauth_token":"370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb", 
#            "oauth_version":"1.0"
#        }
#        
        auth = 'OAuth ' 
        headers={'Authorization':auth}        
        
        self.mainWindow.logmessage("Fetching data for "+nodedata['objectid']+" from "+urlpath+" with params "+json.dumps(urlparams)+" and headers "+json.dumps(headers))    
        return self.request(urlpath,urlparams,headers)        
    
    
    @Slot()
    def doLogin(self,query=False):
        self.doQuery=query
        window = QMainWindow(self.mainWindow)
        window.resize(1200,800)
        window.setWindowTitle("Facebook Login Page")
        
        #create WebView with Facebook log-Dialog, OpenSSL needed        
        self.login_webview=QWebView(window)
        
        webpage = QWebPageCustom(self)
        webpage.logmessage.connect(self.mainWindow.logmessage)   
        self.login_webview.setPage(webpage);
        self.login_webview.urlChanged.connect(self.getToken)
        self.login_webview.loadFinished.connect(self.loadFinished)
        
        #self.login_webview.load(QUrl("https://www.facebook.com/dialog/oauth?client_id=109906609107292&redirect_uri=https://www.facebook.com/connect/login_success.html&response_type=token&scope=user_groups"))
        self.login_webview.resize(window.size())
        self.login_webview.show()
        
        window.show()

    @Slot()
    def getToken(self):
        url = urlparse.parse_qs(self.login_webview.url().toString())
        if url.has_key("https://www.facebook.com/connect/login_success.html#access_token"):
            token=url["https://www.facebook.com/connect/login_success.html#access_token"]
            if token:
                self.tokenEdit.setText(token[0])
                self.login_webview.parent().close()
                if (self.doQuery == True): self.mainWindow.actions.queryNodes()
           
    @Slot()            
    def loadFinished(self,success):
        if (not success): self.mainWindow.logmessage('Error loading web page')     

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
        self.extractEdit.insertItems(0,['data'])
        self.extractEdit.insertItems(0,['data.matches'])      
        self.extractEdit.insertItems(0,['data.feed.entry'])        
                 
        self.extractEdit.setEditable(True)
        mainLayout.addRow("Key to extract",self.extractEdit)

        self.objectidEdit=QComboBox(self)
        self.objectidEdit.insertItems(0,['id.$t'])              
        self.objectidEdit.setEditable(True)
        mainLayout.addRow("Key for ObjectID",self.objectidEdit)


        self.setLayout(mainLayout)
        if loadSettings: self.loadSettings()
        
    def getOptions(self,persistent=False):      
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



#Notcie: RequesterError und Requester enthalten Code aus facebook-sdk, das unter Apache 2.0 licence steht
class RequesterError(Exception):
    def __init__(self, result):
        #Exception.__init__(self, message)
        #self.type = type
        self.result = result
        try:
            self.type = result["error_code"]
        except:
            self.type = ""

        # OAuth 2.0 Draft 10
        try:
            self.message = result["error_description"]
        except:
            # OAuth 2.0 Draft 00
            try:
                self.message = result["error"]["message"]
            except:
                # REST server style
                try:
                    self.message = result["error_msg"]
                except:
                    self.message = result

        Exception.__init__(self, self.message)
        

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

