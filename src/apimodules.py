import urllib.parse
import urllib.request, urllib.error

import secrets
import hashlib, hmac, base64
from mimetypes import guess_all_extensions
from datetime import datetime
from copy import deepcopy
import re
import os, sys, time
import io
from collections import OrderedDict
import threading

from PySide2.QtWebEngineWidgets import QWebEngineView
from PySide2.QtCore import Qt, QUrl

import requests
from requests.exceptions import *
from rauth import OAuth1Service
from requests_oauthlib import OAuth2Session
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from urllib.parse import urlparse, parse_qs, unquote

import webbrowser
import cchardet
import json

if sys.version_info.major < 3:
    from urllib import url2pathname
else:
    from urllib.request import url2pathname

import dateutil.parser

from dialogs.folder import SelectFolderDialog
from dialogs.webdialog import PreLoginWebDialog, BrowserDialog, WebPageCustom
from server import LoginServer
from widgets.paramedit import *
from utilities import *

try:
    from credentials import *
except ImportError:
    credentials = {}

class ApiTab(QScrollArea):
    """
    Generic API Tab Class
        - parse placeholders
        - saves and load current settings
        - init basic inputs
        - handle requests
    """

    streamingData = Signal(list, list, list)

    def __init__(self, mainWindow=None, name="NoName"):
        QScrollArea.__init__(self, mainWindow)
        self.timeout = None
        self.maxsize = 5
        self.mainWindow = mainWindow
        self.loginWindow = None
        self.name = name
        self.connected = False
        self.lastrequest = None
        self.speed = None
        self.lock_session = threading.Lock()
        self.sessions = []

        # Layout       
        self.mainLayout = QFormLayout()
        self.mainLayout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        self.mainLayout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.mainLayout.setLabelAlignment(Qt.AlignLeft)
        self.mainLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)    
        self.mainLayout.setSizeConstraint(QLayout.SetMaximumSize) #QLayout.SetMinimumSize

        # Extra layout
        self.extraLayout = QFormLayout()
        self.extraLayout.setRowWrapPolicy(QFormLayout.DontWrapRows)
        self.extraLayout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.extraLayout.setLabelAlignment(Qt.AlignLeft)
        self.extraLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Container
        pagelayout = QVBoxLayout()
        pagelayout.addLayout(self.mainLayout)
        pagelayout.addStretch(0)
        pagelayout.addLayout(self.extraLayout)

        # For scrolling
        page = QWidget(self)
        page.setLayout(pagelayout)
        self.setWidget(page)
        self.setStyleSheet("QScrollArea {border:0px;background-color:transparent;}")
        page.setAutoFillBackground(False) #import: place after setStyleSheet
        self.setWidgetResizable(True)

        
        # Popup window for auth settings
        self.authWidget = QWidget()

        # Default settings
        try:
            self.defaults = credentials.get(name.lower().replace(' ','_'),{})
        except NameError:
            self.defaults = {}

        # Authorization / use preregistered app
        self.auth_userauthorized = True
        self.auth_preregistered = self.defaults.get('termsurl', '') != ''

    # Called when Facepager stops
    def cleanup(self):
        pass

    def idtostr(self, val):
        """
         Return the Node-ID as a string
        """
        return str(val).encode("utf-8")

    def parseURL(self, url):
        """
        Parse any url and return the query-strings and base bath
        """
        url = url.split('?', 1)
        path = url[0]
        query = url[1] if len(url) > 1 else ''
        query = urllib.parse.parse_qsl(query)
        query = OrderedDict((k, v) for k, v in query)

        return path, query

    def parsePlaceholders(self,pattern,nodedata,paramdata={},options = {}):
        if not pattern:
            return pattern
        elif isinstance(pattern,list):
            return [self.parsePlaceholders(x, nodedata, paramdata, options) for x in pattern]
        else:
            pattern = str(pattern)

        #matches = re.findall(ur"<([^>]*>", pattern)
        #matches = re.findall(ur"(?<!\\)<([^>]*?)(?<!\\)>", pattern)
        #Find placeholders in brackets, ignoring escaped brackets (escape character is backslash)
        matches = re.findall(r"(?<!\\)(?:\\\\)*<([^>]*?(?<!\\)(?:\\\\)*)>", pattern)

        for match in matches:
            name, key, pipeline = parseKey(match)

            if key in paramdata:
                value = str(paramdata[key])
            elif key == 'None':
                value = ''
            elif key == 'Object ID':
                value = {'Object ID':str(nodedata['objectid'])}
                name, value = extractValue(value, match, folder=options.get('folder', ''))
            else:
                name, value = extractValue(nodedata['response'], match, folder=options.get('folder',''))

            if (pattern == '<' + match + '>'):
                pattern = value
                return pattern
            else:                
                #Mask special characters 
                value = value.replace('\\','\\\\')
                value = value.replace('<','\\<')
                value = value.replace('>','\\>')
                
                pattern = pattern.replace('<' + match + '>', value)
               
        pattern = pattern.replace('\\<', '<')
        pattern = pattern.replace('\\>', '>')
        pattern = pattern.replace('\\\\', '\\')

        return pattern

    def getURL(self, urlpath, params, nodedata,options):
        """
        Replaces the Facepager placeholders ("<",">")
        by the Object-ID or any other Facepager-Placeholder
        Example: http://www.facebook.com/<Object-ID>/friends
        """
        urlpath, urlparams = self.parseURL(urlpath)

        # Filter empty params
        params = {name: params[name] for name in params if (name != '') and (name != '<None>') and (params[name] != '<None>')}

        # Collect template parameters (= placeholders)
        templateparams = {}
        for name in params:
            match = re.match(r"^<(.*)>$", str(name))
            if match:
                # Replace placeholders in parameter value
                value = self.parsePlaceholders(params[name], nodedata, {}, options)
                templateparams[match.group(1)] = value

        # Replace placeholders in parameters
        for name in params:
            match = re.match(r"^<(.*)>$", str(name))
            if not match:
                # Replace placeholders in parameter value
                value = self.parsePlaceholders(params[name], nodedata, templateparams, options)
                if isinstance(value,list):
                    urlparams[name] = [str(x) for x in value]
                else:
                    urlparams[name] = str(value)

        # Replace placeholders in urlpath
        urlpath = self.parsePlaceholders(urlpath, nodedata, templateparams)

        return urlpath, urlparams, templateparams

    def getLogURL(self, urlpath, urlparams, options, removesecrets=True):
        url = urlpath

        # Convert to list of tuple to allow duplicated keys
        if urlparams:
            urltuples = dictToTuples(urlparams)
            urltuples = urllib.parse.urlencode(urltuples)
            if removesecrets:
                urltuples = urltuples.replace(options.get('access_token', ''), '')
            url += "?" + urltuples

        return url

    def getPayload(self,payload, params, nodedata,options, logProgress=None):
        #Return nothing
        if (payload is None) or (payload == ''):            
            return None
        
        # Parse JSON and replace placeholders in values
        elif options.get('encoding','<None>') == 'multipart/form-data':
            #payload = json.loads(payload)
            for name in payload:
                value = payload[name]
                
                try:
                    value = json.loads(value)
                except:
                    pass 
                    
                # Files (convert dict to tuple)
                if isinstance(value,dict):                
                   filename = self.parsePlaceholders(value.get('name',''), nodedata, params,options)
                   filedata = self.parsePlaceholders(value.get('data',''), nodedata, params,options)
                   filetype = self.parsePlaceholders(value.get('type',''), nodedata, params,options)                   
                   payload[name] = (filename,filedata,filetype)
                    
                # Strings
                else:
                    value = payload[name]
                    payload[name] = self.parsePlaceholders(value, nodedata, params,options)

            def callback(monitor):
                if logProgress is not None:
                    logProgress({'current': monitor.bytes_read, 'total': monitor.len})

            payload = MultipartEncoder(fields=payload)
            payload = MultipartEncoderMonitor(payload,callback)

            return payload
        
        # Replace placeholders in string and setup progress callback
        else:
            def callback(current, total):
                if logProgress is not None:
                    logProgress({'current': current, 'total': total})

            payload = self.parsePlaceholders(payload, nodedata, params,options)
            payload = BufferReader(payload,callback)
            return payload

    # Gets data from input fields or defaults (never gets credentials from default values!)
    def getSettings(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {}

        defaults = self.getDefaultAndDocOptions()
        #options['module'] = self.name

        #options for request
        try:
            options['basepath'] = self.basepathEdit.currentText().strip()
            options['resource'] = self.resourceEdit.currentText().strip()
            options['params'] = self.paramEdit.getParams()
        except AttributeError:
            pass

        # Extension (for Twitter, deprecated)
        options['extension'] = defaults.get('extension','')
        if (options['extension'] != '') and options['resource'].endswith(options['extension']):
            options['extension'] = ''

        #headers and verbs
        try:
            options['headers'] = self.headerEdit.getParams()
            options['verb'] = self.verbEdit.currentText().strip()            
        except AttributeError:
            pass
        #
        # # Get doc key for lookup of data handling keys
        # doc_resource = options.get('resource', '').strip()
        # if doc_resource == '':
        #     doc_resource = '0'

        #format
        try:
            options['format'] = self.formatEdit.currentText().strip()
        except AttributeError:
            pass

        #payload
        try:
            if options.get('verb','GET') in ['POST','PUT','PATCH']:
                options['encoding'] = self.encodingEdit.currentText().strip()
                
                if options['encoding'] == 'multipart/form-data':
                    options['payload'] = self.multipartEdit.getParams()
                else:
                    options['payload'] = self.payloadEdit.toPlainText()
        except AttributeError:
            pass

        try:
            options['filename'] = self.filenameEdit.currentText()
            options['fileext'] = self.fileextEdit.currentText()
        except AttributeError:
            pass

        #paging
        try:
            options['pages'] = self.pagesEdit.value()
        except AttributeError:
            pass

        try:
            options['paging_type'] = self.pagingTypeEdit.currentText().strip() if self.pagingTypeEdit.currentText() != "" else defaults.get('paging_type', '')
            options['key_paging'] = self.pagingkeyEdit.text() if self.pagingkeyEdit.text() != "" else defaults.get('key_paging',None)
            options['paging_stop'] = self.pagingstopEdit.text() if self.pagingstopEdit.text() != "" else defaults.get('paging_stop',None)
            options['param_paging'] = self.pagingparamEdit.text() if self.pagingparamEdit.text() != "" else defaults.get('param_paging',None)
            options['offset_start'] = self.offsetStartEdit.value()
            options['offset_step'] = self.offsetStepEdit.value()
        except AttributeError:
            options['paging_type'] = defaults.get('paging_type')
            options['key_paging'] = defaults.get('key_paging')
            options['paging_stop'] = defaults.get('paging_stop')
            options['param_paging'] = defaults.get('param_paging')
            options['offset_start'] = 1
            options['offset_step'] = 1

        if options.get('paging_type') == 'url':
            options.pop('paging_stop')
            options.pop('param_paging')
            options.pop('offset_start')
            options.pop('offset_step')
        elif options.get('paging_type') == 'decrease':
            options.pop('offset_start')
            options.pop('offset_step')
            options.pop('paging_stop')
        elif options.get('paging_type') == 'key':
            options.pop('offset_start')
            options.pop('offset_step')
        elif options.get('paging_type') == 'count':
            options.pop('key_paging')
            options.pop('paging_stop')

        #options for data handling
        try:
            options['nodedata'] = self.extractEdit.text() if self.extractEdit.text() != "" else defaults.get('nodedata')
            options['objectid'] = self.objectidEdit.text() if self.objectidEdit.text() != "" else defaults.get('objectid')
        except AttributeError:
            options['nodedata'] = defaults.get('nodedata')
            options['objectid'] = defaults.get('objectid')

        # Scopes
        try:
            options['scope'] = self.scopeEdit.text().strip()
        except AttributeError:
            pass

        try:
            options['proxy'] = self.proxyEdit.text().strip()
        except AttributeError:
            pass


        # Options not saved to preset but to settings
        if purpose != 'preset':
            # query type
            options['querytype'] = self.name + ':' + self.resourceEdit.currentText()            

            # uploadfolder
            try:
                options['folder'] = self.folderEdit.text()
            except AttributeError:
                pass

            # download folder
            try:
                options['downloadfolder'] = self.downloadfolderEdit.text()
            except AttributeError:
                pass

            try:
                options['access_token'] = self.tokenEdit.text()
            except AttributeError:
                pass            

            try:
                options['access_token_secret'] = self.tokensecretEdit.text()
            except AttributeError:
                pass    
                        
            try:
                options['client_id'] = self.clientIdEdit.text()
            except AttributeError:
                pass            

            try:
                options['client_secret'] = self.clientSecretEdit.text()
            except AttributeError:
                pass

        return options

    def updateBasePath(self, options=None):
        if options is None:
            basepath = self.basepathEdit.currentText().strip()
            options = {'basepath' : basepath}
        else:
            basepath = options.get('basepath', '')
            self.basepathEdit.setEditText(basepath)

        index = self.basepathEdit.findText(basepath)
        if index != -1:
            self.basepathEdit.setCurrentIndex(index)

        # Get general doc
        apidoc = self.mainWindow.apiWindow.getApiDoc(self.name, basepath)

        # apidoc = self.basepathEdit.itemData(index, Qt.UserRole)

        # Add endpoints in reverse order
        self.resourceEdit.clear()
        if apidoc and isinstance(apidoc, dict):
            endpoints = apidoc.get("paths", {})
            paths = endpoints.keys()
            for path in list(paths):
                operations = endpoints[path]
                path = path.replace("{", "<").replace("}", ">")

                self.resourceEdit.addItem(path)
                idx = self.resourceEdit.count() - 1
                self.resourceEdit.setItemData(idx, wraptip(getDictValue(operations, "get.summary", "")), Qt.ToolTipRole)

                # store params for later use in onChangedResource
                self.resourceEdit.setItemData(idx, operations, Qt.UserRole)

            self.buttonApiHelp.setVisible(True)
        else:
            self.resourceEdit.insertItem(0, "/<Object ID>")

    def updateResource(self, options=None):
        if options is None:
            resource = self.resourceEdit.currentText().strip()
            options = {'resource' : resource}
        else:
            resource = options.get('resource', '')
            self.resourceEdit.setEditText(resource)

        index = self.resourceEdit.findText(resource)
        if index != -1:
            self.resourceEdit.setCurrentIndex(index)


        operations = self.resourceEdit.itemData(index, Qt.UserRole)
        params = getDictValue(operations, "get.parameters", False) if operations else []

        # Set param names
        self.paramEdit.setNameOptionsAll(params)

    # Populates input fields from loaded options and presets
    # Select boxes are updated by onChangedBasepath and onChangedResource
    # based on the API docs.
    # @settings Dict with options
    def setSettings(self, settings = {}):

        # Base path
        options = self.getDefaultAndDocOptions(settings)
        self.updateBasePath(options)

        # Resource
        options = self.getDefaultAndDocOptions(settings)
        self.updateResource(options)

        # Params and Options
        options = self.getDefaultAndDocOptions(settings)
        self.updateParams(options)
        self.updateOptions(options)

        return options

    def updateParams(self, options):
        self.paramEdit.setParams(options.get('params', ''))

    def updateOptions(self, options):

        # Header and method
        try:
            self.headerEdit.setParams(options.get('headers', {}))
            self.verbEdit.setCurrentIndex(self.verbEdit.findText(options.get('verb', 'GET')))
            self.encodingEdit.setCurrentIndex(self.encodingEdit.findText(options.get('encoding', '<None>')))

            if options.get('encoding', '<None>') == 'multipart/form-data':
                self.multipartEdit.setParams(options.get('payload', {}))
            else:
                self.payloadEdit.setPlainText(options.get('payload', ''))

            self.verbChanged()
        except AttributeError:
            pass

        # Format
        try:
            self.formatEdit.setCurrentIndex(self.formatEdit.findText(options.get('format', 'json')))
        except AttributeError:
            pass

        # Upload folder
        try:
            if 'folder' in options:
                self.folderEdit.setText(options.get('folder'))
        except AttributeError:
            pass

        # Download folder
        try:
            if 'downloadfolder' in options:
                self.downloadfolderEdit.setText(options.get('downloadfolder'))
        except AttributeError:
            pass

        try:
            self.filenameEdit.setEditText(options.get('filename', '<None>'))
            self.fileextEdit.setEditText(options.get('fileext', '<None>'))
        except AttributeError:
            pass

        # Paging
        try:
            self.pagesEdit.setValue(int(options.get('pages', 1)))
        except AttributeError:
            pass

        try:
            self.pagingTypeEdit.setCurrentIndex(
                self.pagingTypeEdit.findText(options.get('paging_type', 'key')))
            self.pagingkeyEdit.setText(options.get('key_paging', ''))
            self.pagingstopEdit.setText(options.get('paging_stop', ''))
            self.pagingparamEdit.setText(options.get('param_paging', ''))
            self.offsetStartEdit.setValue(int(options.get('offset_start', 1)))
            self.offsetStepEdit.setValue(int(options.get('offset_step', 1)))
            self.pagingChanged()
        except AttributeError:
            pass

        # Extract options
        try:
            self.extractEdit.setText(options.get('nodedata'))
            self.objectidEdit.setText(options.get('objectid'))
        except AttributeError:
            pass

        # Scope
        try:
            self.scopeEdit.setText(options.get('scope', ''))
        except AttributeError:
            pass

        # Proxy
        try:
            self.proxyEdit.setText(options.get('proxy', ''))
        except AttributeError:
            pass

        # Credentials
        try:
            if 'access_token' in options:
                self.tokenEdit.setText(options.get('access_token', ''))
            if 'access_token_secret' in options:
                self.tokensecretEdit.setText(options.get('access_token_secret', ''))
            if 'client_id' in options:
                self.clientIdEdit.setText(options.get('client_id', ''))
            if 'client_secret' in options:
                self.clientSecretEdit.setText(options.get('client_secret', ''))

        except AttributeError:
            pass

    def saveSettings(self):
        self.mainWindow.settings.beginGroup("ApiModule_" + self.name)
        options = self.getSettings('settings')

        for key in list(options.keys()):
            self.mainWindow.settings.setValue(key, options[key])
        self.mainWindow.settings.endGroup()

    def loadSettings(self):
        self.mainWindow.settings.beginGroup("ApiModule_" + self.name)

        options = {}
        for key in self.mainWindow.settings.allKeys():
            options[key] = self.mainWindow.settings.value(key)
        self.mainWindow.settings.endGroup()
        self.setSettings(options)

    @Slot(str)
    def logMessage(self,message):
        self.mainWindow.logmessage(message)

    def reloadDoc(self):
        self.saveSettings()
        self.loadDoc()
        self.loadSettings()

    def loadDoc(self):
        '''
        Loads and prepares documentation
        '''

        # Add base paths
        self.basepathEdit.clear()
        urls = self.mainWindow.apiWindow.getApiBasePaths(self.name)
        self.basepathEdit.insertItems(0,urls)

        # TODO: set API Docs as item data

    def showDoc(self):
        '''
        Open window with documentation
        '''
        basepath = self.basepathEdit.currentText().strip()
        path = self.resourceEdit.currentText().strip()
        self.mainWindow.apiWindow.showDoc(self.name, basepath, path)

    def getDefaultAndDocOptions(self, options = {}):
        # Set default options
        defaults = self.defaults.copy()
        defaults.update(self.getDocOptions())
        defaults.update(options)

        return defaults

    def getDocOptions(self):

        # def getFromDoc(self, dockey, defaultkey=None):
        #     dockey = dockey.replace("<", "{").replace(">", "}")
        #     value = getDictValue(self.apidoc, dockey, dump=False, default=None)
        #     if (value is None) and (defaultkey is not None):
        #         value = self.defaults.get(defaultkey)
        #     return value

        # Get general doc
        basepath = self.basepathEdit.currentText().strip()
        apidoc = self.mainWindow.apiWindow.getApiDoc(self.name,basepath)

        # Get response doc
        resourceidx = self.resourceEdit.findText(self.resourceEdit.currentText())
        operations = self.resourceEdit.itemData(resourceidx,Qt.UserRole) if resourceidx != -1 else {}
        schema = getDictValue(operations, "get.responses.200.content.application/json.schema", []) if operations else []

        options = {}

        # Params
        params = getDictValue(operations, "get.parameters", False) if operations else []
        defaultparams = {}
        for param in params:
            # Default values for required params
            if param.get("required", False) or param.get("x-facepager-default", False):
                name = param.get("name", "")
                name = "<" + name + ">" if param.get("in", "query") == "path" else name
                value = param.get("example", "<Object ID>")

                defaultparams[name] = value

        options['params'] = defaultparams

        # Path extension for Twitter (deprecated)
        options['extension'] = getDictValue(apidoc, "servers.0.x-facepager-suffix")

        # Default extract settings
        options['objectid'] = getDictValueOrNone(apidoc, "x-facepager-objectid")
        options['nodedata'] = getDictValueOrNone(apidoc, "x-facepager-extract")

        # Default pagination settings
        pagination = getDictValueOrNone(apidoc, "x-facepager-pagination", dump=False)
        options['paging_type'] = getDictValueOrNone(pagination, 'method')
        options['param_paging'] = getDictValueOrNone(pagination, 'param')
        options['key_paging'] = getDictValueOrNone(pagination, 'key')
        options['paging_stop'] = getDictValueOrNone(pagination, 'stop')

        # Default authorization settings
        authorization = getDictValueOrNone(apidoc, "x-facepager-authorization", dump=False)
        options['auth_type'] = getDictValueOrNone(authorization, 'auth_type')
        options['auth_uri'] = getDictValueOrNone(authorization, 'auth_uri')
        options['auth_tokenuri'] = getDictValueOrNone(authorization, 'token_uri')

        options['auth'] = getDictValueOrNone(authorization, 'auth_method')
        options['auth_tokenname'] = getDictValueOrNone(authorization, 'token_name')


        # Extract options from response reference
        if 'x-facepager-extract' in schema:
            options['nodedata'] = schema.get('x-facepager-extract')

        if 'x-facepager-objectid' in schema:
            options['objectid'] = schema.get('x-facepager-objectid')


        options = {k: v for k, v in options.items() if v is not None}

        return options

    def initInputs(self):
        '''
        Create base path edit, resource edit and param edit
        Set resource according to the APIdocs, if any docs are available
        '''

        #Base path
        self.basepathEdit = QComboBox(self)
        if not self.defaults.get('basepath',None) is None:
            self.basepathEdit.insertItems(0, [self.defaults.get('basepath','')])
        self.basepathEdit.setEditable(True)
        self.mainLayout.addRow("Base path", self.basepathEdit)
        self.basepathEdit.currentIndexChanged.connect(self.onChangedBasepath)

        #Resource
        self.resourceLayout = QHBoxLayout()
        self.actionApiHelp = QAction('Open documentation if available.',self)
        self.actionApiHelp.setText('?')
        self.actionApiHelp.triggered.connect(self.showDoc)
        self.buttonApiHelp =QToolButton(self)
        self.buttonApiHelp.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.buttonApiHelp.setDefaultAction(self.actionApiHelp)
        self.buttonApiHelp.setVisible(False)

        self.resourceEdit = QComboBox(self)
        self.resourceEdit.setEditable(True)

        self.resourceLayout.addWidget(self.resourceEdit)
        self.resourceLayout.addWidget(self.buttonApiHelp)

        self.mainLayout.addRow("Resource", self.resourceLayout)

        #Parameters
        self.paramEdit = QParamEdit(self)
        self.mainLayout.addRow("Parameters", self.paramEdit)
        self.resourceEdit.currentIndexChanged.connect(self.onChangedResource)

    def getFileFolderName(self,options, nodedata):
        # Folder
        foldername = options.get('downloadfolder', None)
        if foldername == '':
            foldername = None

        # File
        filename = options.get('filename', None)
        if (filename is not None) and (filename  == '<None>'):
            filename = None
        else:
            filename = self.parsePlaceholders(filename,nodedata)

        if filename == '':
            filename = None

        # Extension
        fileext = options.get('fileext', None)

        if fileext is not None and fileext == '<None>':
            fileext = None
        elif fileext is not None and fileext != '':
            fileext = self.parsePlaceholders(fileext,nodedata)

        return (foldername,filename,fileext)

    # Upload folder
    def initUploadFolderInput(self):
        self.folderwidget = QWidget()
        folderlayout = QHBoxLayout()
        folderlayout.setContentsMargins(0,0,0,0)
        self.folderwidget.setLayout(folderlayout)

        self.folderEdit = QLineEdit()
        folderlayout.addWidget(self.folderEdit)

        self.folderButton = QPushButton("...", self)
        self.folderButton.clicked.connect(self.selectFolder)
        folderlayout.addWidget(self.folderButton)

        self.mainLayout.addRow("Upload folder", self.folderwidget)

    # Download folder
    def initFileInputs(self):

        self.downloadfolderwidget = QWidget()
        folderlayout = QHBoxLayout()
        folderlayout.setContentsMargins(0,0,0,0)
        self.downloadfolderwidget.setLayout(folderlayout)

        # Folder edit
        self.downloadfolderEdit = QLineEdit()
        self.downloadfolderEdit.setToolTip(wraptip("Select a folder if you want to save the responses to files."))
        folderlayout.addWidget(self.downloadfolderEdit,2)

        # Select folder button
        self.actionDownloadFolder = QAction('...',self)
        self.actionDownloadFolder.setText('..')
        self.actionDownloadFolder.triggered.connect(self.selectDownloadFolder)
        self.downloadfolderButton =QToolButton(self)
        self.downloadfolderButton.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.downloadfolderButton.setDefaultAction(self.actionDownloadFolder)
        folderlayout.addWidget(self.downloadfolderButton,0)

        # filename
        folderlayout.addWidget(QLabel("Filename"),0)
        self.filenameEdit = QComboBox(self)
        self.filenameEdit .setToolTip(wraptip("Set the filename, if you want to save the responses to files. <Object ID> usually is a good choice."))
        self.filenameEdit.insertItems(0, ['<Object ID>','<None>'])
        self.filenameEdit.setEditable(True)
        folderlayout.addWidget(self.filenameEdit,1)


        # fileext
        folderlayout.addWidget(QLabel("Custom file extension"),0)
        self.fileextEdit = QComboBox(self)
        self.fileextEdit  .setToolTip(wraptip("Set the extension of the files, for example .json, .txt or .html. Set to <None> to automatically guess from the response."))
        self.fileextEdit.insertItems(0, ['<None>','.html','.txt'])
        self.fileextEdit.setEditable(True)
        folderlayout.addWidget(self.fileextEdit,1)
        #layout.setStretch(2, 1)

        self.extraLayout.addRow("Download", self.downloadfolderwidget)

    def pagingChanged(self):
        if self.pagingTypeEdit.currentText() == "count":
            self.pagingParamWidget.show()
            self.pagingStepsWidget.show()
            self.pagingKeyWidget.hide()
        elif self.pagingTypeEdit.currentText() == "url":
            self.pagingParamWidget.hide()
            self.pagingStepsWidget.hide()
            self.pagingKeyWidget.show()
        else:
            self.pagingParamWidget.show()
            self.pagingStepsWidget.hide()
            self.pagingKeyWidget.show()

        if self.pagingTypeEdit.count() < 2:
            self.pagingTypeEdit.hide()


    def initPagingInputs(self,keys = False):
        layout= QHBoxLayout()
        
        if keys:
            # Paging type

            self.pagingTypeEdit = QComboBox(self)

            self.pagingTypeEdit.addItem('key')
            self.pagingTypeEdit.addItem('count')
            self.pagingTypeEdit.addItem('url')

            self.pagingTypeEdit.setToolTip(wraptip("Select 'key' if the response contains data about the next page, e.g. page number or offset. Select 'count' if you want to increase the paging param by a fixed amount. Select 'url' if the response contains a complete URL to the next page."))
            self.pagingTypeEdit.currentIndexChanged.connect(self.pagingChanged)
            layout.addWidget(self.pagingTypeEdit)
            layout.setStretch(0, 0)

            # Paging param
            self.pagingParamWidget = QWidget()
            self.pagingParamLayout = QHBoxLayout()
            self.pagingParamLayout .setContentsMargins(0, 0, 0, 0)
            self.pagingParamWidget.setLayout(self.pagingParamLayout)

            self.pagingParamLayout.addWidget(QLabel("Param"))
            self.pagingparamEdit = QLineEdit(self)
            self.pagingparamEdit.setToolTip(wraptip("This parameter will be added to the query if you select key-pagination. The value is extracted by the paging key."))
            self.pagingParamLayout.addWidget(self.pagingparamEdit)
            self.pagingParamLayout.setStretch(0,0)
            self.pagingParamLayout.setStretch(1, 0)

            layout.addWidget(self.pagingParamWidget)
            layout.setStretch(1, 2)

            # Paging key
            self.pagingKeyWidget = QWidget()
            self.pagingKeyLayout = QHBoxLayout()
            self.pagingKeyLayout .setContentsMargins(0, 0, 0, 0)
            self.pagingKeyWidget.setLayout(self.pagingKeyLayout)

            self.pagingKeyLayout.addWidget(QLabel("Paging key"))
            self.pagingkeyEdit = QLineEdit(self)
            self.pagingkeyEdit.setToolTip(wraptip("If the respsonse contains data about the next page, specify the key. The value will be added as paging parameter or used as the URL."))
            self.pagingKeyLayout.addWidget(self.pagingkeyEdit)
            self.pagingKeyLayout.setStretch(0, 0)
            self.pagingKeyLayout.setStretch(1, 1)

            layout.addWidget(self.pagingKeyWidget)
            layout.setStretch(2, 2)

            # Page steps
            self.pagingStepsWidget = QWidget()
            self.pagingStepsLayout = QHBoxLayout()
            self.pagingStepsLayout.setContentsMargins(0, 0, 0, 0)
            self.pagingStepsWidget.setLayout(self.pagingStepsLayout)

            self.pagingStepsLayout.addWidget(QLabel("Start value"))
            self.offsetStartEdit = QSpinBox(self)
            self.offsetStartEdit.setValue(1)
            self.offsetStartEdit.setToolTip(wraptip("First page or offset number, defaults to 1"))
            self.pagingStepsLayout.addWidget(self.offsetStartEdit)
            self.pagingStepsLayout.setStretch(0, 0)
            self.pagingStepsLayout.setStretch(1, 1)

            self.pagingStepsLayout.addWidget(QLabel("Step"))
            self.offsetStepEdit = QSpinBox(self)
            self.offsetStepEdit.setMaximum(10000)
            self.offsetStepEdit.setValue(1)
            self.offsetStepEdit.setToolTip(wraptip("Amount to increase for each page, defaults to 1"))
            self.pagingStepsLayout.addWidget(self.offsetStepEdit)
            self.pagingStepsLayout.setStretch(2, 0)
            self.pagingStepsLayout.setStretch(3, 1)

            layout.addWidget(self.pagingStepsWidget)
            layout.setStretch(3, 1)

            # Stop if
            layout.addWidget(QLabel("Stop key"))
            self.pagingstopEdit = QLineEdit(self)
            self.pagingstopEdit.setToolTip(wraptip("Stops fetching data as soon as the given key is present but empty or false. For example, stops fetching if the value of 'hasNext' ist false, none or an empty list. Usually you can leave the field blank, since fetching will stop anyway when the paging key is empty."))
            layout.addWidget(self.pagingstopEdit)
            layout.setStretch(4, 0)
            layout.setStretch(5, 1)

            #Page count
            layout.addWidget(QLabel("Maximum pages"))
            self.pagesEdit = QSpinBox(self)
            self.pagesEdit.setMinimum(1)
            self.pagesEdit.setMaximum(50000)
            self.pagesEdit.setToolTip(wraptip("Number of maximum pages."))
            layout.addWidget(self.pagesEdit)
            layout.setStretch(6, 0)
            layout.setStretch(7, 0)

            rowcaption = "Paging"

        else:
            #Page count
            self.pagesEdit = QSpinBox(self)
            self.pagesEdit.setMinimum(1)
            self.pagesEdit.setMaximum(50000)
            layout.addWidget(self.pagesEdit)            
            
            rowcaption = "Maximum pages"

        self.extraLayout.addRow(rowcaption, layout)

    def initHeaderInputs(self):
        self.headerEdit = QParamEdit(self)
        self.mainLayout.addRow("Headers", self.headerEdit)


    def initVerbInputs(self):
        # Verb and encoding
        self.verbEdit = QComboBox(self)
        self.verbEdit.addItems(['GET','HEAD','POST','PUT','PATCH','DELETE'])
        self.verbEdit.currentIndexChanged.connect(self.verbChanged)

        self.encodingLabel = QLabel("Encoding")
        self.encodingEdit = QComboBox(self)
        self.encodingEdit.addItems(['<None>','multipart/form-data'])
        self.encodingEdit.currentIndexChanged.connect(self.verbChanged)
        

        layout= QHBoxLayout()
        layout.addWidget(self.verbEdit)
        layout.setStretch(0, 1)
        layout.addWidget(self.encodingLabel)
        layout.addWidget(self.encodingEdit)
        layout.setStretch(2, 1)
        self.mainLayout.addRow("Method", layout)
        
        # Payload
        self.payloadWidget = QWidget()
        self.payloadLayout = QHBoxLayout()
        self.payloadLayout.setContentsMargins(0,0,0,0)
        self.payloadWidget.setLayout(self.payloadLayout)
        
        self.payloadEdit = QPlainTextEdit()
        self.payloadEdit.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.payloadLayout.addWidget(self.payloadEdit)
        self.payloadLayout.setStretch(0, 1);
        
        self.multipartEdit = QParamEdit()
        self.payloadLayout.addWidget(self.multipartEdit)
        self.payloadLayout.setStretch(0, 1);        

        self.payloadLayout.setStretch(2, 1);    
        self.mainLayout.addRow("Payload", self.payloadWidget)

    def verbChanged(self):
        if self.verbEdit.currentText() in ['GET','DELETE','HEAD']:
            self.payloadWidget.hide()
            self.mainLayout.labelForField(self.payloadWidget).hide()
            
            self.encodingEdit.hide()
            self.encodingLabel.hide()                        

            self.folderwidget.hide()
            self.mainLayout.labelForField(self.folderwidget).hide()
        else:
            self.payloadWidget.show()
            self.mainLayout.labelForField(self.payloadWidget).show()

            #Encoding    
            self.encodingEdit.show()
            self.encodingLabel.show()
            
            #Multipart
            if self.encodingEdit.currentText().strip() == 'multipart/form-data':
                self.multipartEdit.show()
                self.payloadEdit.hide()
                
                #self.payloadEdit.setPlainText(json.dumps(self.multipartEdit.getParams(),indent=4,))
            else:
                self.payloadEdit.show()
                self.multipartEdit.hide()
            
            #Folder
            self.folderwidget.show()
            self.mainLayout.labelForField(self.folderwidget).show()                        

    def initResponseInputs(self, format=False):
        layout= QHBoxLayout()

        if not format:
            #Extract
            self.extractEdit = QLineEdit(self)
            layout.addWidget(self.extractEdit)
            layout.setStretch(0, 1)

            layout.addWidget(QLabel("Key for Object ID"))
            self.objectidEdit = QLineEdit(self)
            layout.addWidget(self.objectidEdit)
            layout.setStretch(2, 1)

            #Add layout
            self.extraLayout.addRow("Key to extract", layout)
        else:
            # Format
            self.formatEdit = QComboBox(self)
            self.formatEdit.addItems(['json', 'text', 'links','xml','file'])
            self.formatEdit.setToolTip("<p>JSON: default option, data will be parsed as JSON. </p> \
                                        <p>Text: data will not be parsed and embedded in JSON. </p> \
                                        <p>Links: data will be parsed as xml and links will be extracted (set key to extract to 'links' and key for Object ID to 'url'). </p> \
                                        <p>XML: data will be parsed as XML and converted to JSON. </p> \
                                        <p>File: data will only be downloaded to files, specify download folder and filename.</p>")
            layout.addWidget(self.formatEdit)
            layout.setStretch(0, 0)
            # self.formatEdit.currentIndexChanged.connect(self.formatChanged)

            # Extract
            layout.addWidget(QLabel("Key to extract"))
            self.extractEdit = QLineEdit(self)
            self.extractEdit.setToolTip(wraptip(
                "If your data contains a list of objects, set the key of the list. Every list element will be adeded as a single node. Remaining data will be added as offcut node."))
            layout.addWidget(self.extractEdit)
            layout.setStretch(1, 0)
            layout.setStretch(2, 2)

            layout.addWidget(QLabel("Key for Object ID"))
            self.objectidEdit = QLineEdit(self)
            self.objectidEdit.setToolTip(
                wraptip("If your data contains unique IDs for every node, define the corresponding key."))
            layout.addWidget(self.objectidEdit)
            layout.setStretch(3, 0)
            layout.setStretch(4, 2)

            # Add layout
            self.extraLayout.addRow("Response", layout)

    @Slot()
    def onChangedBasepath(self, index = None):
        '''
        Handles the automated resource suggestion for the
        selected API based on the OpenAPI specification 3.0.0
        '''
        if index is None:
            index = self.basepathEdit.findText(self.basepathEdit.currentText())
            if index != -1:
                self.basepathEdit.setCurrentIndex(index)

        self.updateBasePath()
        self.updateResource()

        defaults = self.getDefaultAndDocOptions()
        self.updateParams(defaults)
        self.updateOptions(defaults)

    @Slot()
    def onChangedResource(self, index = None):
        '''
        Handles the automated parameter suggestion for the
        selected API endpoint based on the OpenAPI specification 3.0.0
        '''

        if index is None:
            index = self.resourceEdit.findText(self.resourceEdit.currentText())
            if index != -1:
                self.resourceEdit.setCurrentIndex(index)

        self.updateResource()

        defaults = self.getDefaultAndDocOptions()
        self.updateParams(defaults)
        self.updateOptions(defaults)


    @Slot()
    def onChangedParam(self,index=0):
        pass

    def getProxies(self, reload=False):
        if not hasattr(self, "proxies") or reload:
            self.proxies = {}
            if hasattr(self, "proxyEdit"):
                self.proxies = self.proxyEdit.text().strip()
                self.proxies = self.proxies.split(";")

        if len(self.proxies) == 0:
            proxy = ""
        elif len(self.proxies) == 1:
            proxy = self.proxies[0]
        else:
            proxy = self.proxies[0]
            self.proxies = self.proxies[1:] + self.proxies[:1]

        if proxy.startswith('http'):
            proxy_http = "http://"+re.sub('^https?://', '', proxy)
            proxy_https = "https://" + re.sub('^https?://', '', proxy)
            return {'http': proxy_http, 'https': proxy_https}
        elif proxy != "":
            return {'http': proxy, 'https': proxy}
        else:
            return {}

        # if not hasattr(self,"proxies") or reload:
        #     try:
        #         filename = os.path.join(os.path.expanduser("~"), 'Facepager','proxies.json')
        #         if os.path.exists(filename):
        #             with open(filename, 'r', encoding='utf-8') as f:
        #                 self.proxies = json.load(f)
        #         else:
        #             self.proxies = {}
        #     except Exception as e:
        #         self.logMessage("Error loading proxies: {}".format(str(e)))
        #         self.proxies = {}
        #
        # return proxy

    def initPagingOptions(self, data, options):

        # only empty if requested
        if options.get('emptyonly', False):
            lastdata = getDictValueOrNone(options, 'lastdata', dump=False)
            if lastdata is not None:
                return None

        # paging by auto count
        if (options.get('paging_type') == "count") and (options.get('param_paging', '') is not None):
            offset = options.get('offset_start', 1)
            options['params'][options.get('param_paging', '')] = offset

        # paging by key (continue previous fetching process based on last fetched child offcut node)
        elif (options.get('paging_type') == "key") and (options.get('key_paging') is not None) and (options.get('param_paging') is not None):
            # Get cursor of last offcut node
            offcut = getDictValueOrNone(options, 'lastdata.response', dump=False)
            cursor = getDictValueOrNone(offcut,options.get('key_paging'))
            stopvalue = not extractValue(offcut,options.get('paging_stop'), dump = False, default = True)[1]

            # Dont't fetch if already finished (=offcut without next cursor)
            if options.get('resume',False) and (offcut is not None) and ((cursor is None) or stopvalue):
                return None

            # Continue / start fetching
            elif (cursor is not None) :
                options['params'][options['param_paging']] = cursor

        # url based paging
        elif (options.get('paging_type') == "url") and (options.get('key_paging') is not None):
            offcut = getDictValueOrNone(options, 'lastdata.response', dump=False)
            url = getDictValueOrNone(offcut,options.get('key_paging'))

            # Dont't fetch if already finished (=offcut without next cursor)
            if options.get('resume',False) and (offcut is not None) and (url is None):
                return None

            if url is not None:
                url, params = self.parseURL(url)
                options['params'] = params
                options['url'] = url

        elif (options.get('paging_type') == "decrease"):
            node= getDictValueOrNone(options, 'lastdata.response', dump=False)
            cursor = getDictValueOrNone(node, options.get('key_paging'))

            if (node is not None):
                if cursor is None:
                    return None

                try:
                    cursor = int(cursor) - 1
                    options['params'][options['param_paging']] = cursor
                except:
                    return None

        # break if "continue pagination" is checked and data already present
        elif options.get('resume',False):
            offcut = getDictValueOrNone(options, 'lastdata.response', dump=False)

            # Dont't fetch if already finished (=offcut)
            if (offcut is not None):
                return None

        return options

    def updatePagingOptions(self, data, options):
        # Stop if result is empty
        if (options['nodedata'] is not None) and not hasValue(data, options['nodedata']):
            return None

        # paging by auto count
        if (options.get('paging_type') == "count") and (options.get('param_paging') is not None):
            offset = options['params'][options['param_paging']]
            offset = offset + options.get('offset_step', 1)
            options['params'][options['param_paging']] = offset

        # paging by key
        elif (options.get('paging_type') == "key") and (options.get('key_paging') is not None) and (
                options.get('param_paging') is not None):
            cursor = getDictValueOrNone(data, options['key_paging'])
            if cursor is None:
                return None

            stopvalue = not extractValue(data, options.get('paging_stop'), dump=False, default=True)[1]
            if stopvalue:
                return None

            options['params'][options['param_paging']] = cursor

        # url based paging
        elif (options.get('paging_type') == "url") and (options.get('key_paging') is not None):
            url = getDictValueOrNone(data, options['key_paging'])
            if url is not None:
                url, params = self.parseURL(url)
                options['params'] = params
                options['url'] = url
            else:
                return None
        elif (options.get('paging_type') == "decrease"):
            # manual paging with max-id
            # if there are still statuses in the response, use the last ID-1 for further pagination

            if isinstance(data, list) and (len(data) > 0):
                node = data[-1]
            else:
                node = data

            cursor = getDictValueOrNone(node, options['key_paging'])
            if cursor is None:
                return None

            try:
                cursor = int(cursor) - 1
                options['params'][options['param_paging']] = cursor
            except:
                return None

        # no pagination
        else:
            return None

        return options

    def buildUrl(self, nodedata, options, logProgress=None):
        if not ('url' in options):
            urlpath = options["basepath"].strip() + options['resource'].strip() + options.get('extension', '')
            urlparams = {}
            urlparams.update(options['params'])
            urlpath, urlparams, templateparams = self.getURL(urlpath, urlparams, nodedata, options)
            requestheaders = options.get('headers', {})

            # Authorization
            if options.get('auth','disable') != 'disable':
                token = options.get('auth_prefix','') + options.get('access_token','')
                if options.get('auth') == 'param':
                    urlparams[options.get('auth_tokenname')] = token
                elif (options.get('auth') == 'header'):
                    requestheaders[options.get('auth_tokenname')] = token

            method = options.get('verb', 'GET')
            payload = self.getPayload(options.get('payload', None), templateparams, nodedata, options, logProgress)
            if isinstance(payload, MultipartEncoder) or isinstance(payload, MultipartEncoderMonitor):
                requestheaders["Content-Type"] = payload.content_type
        else:
            method = options.get('verb', 'GET')
            payload = None
            urlpath = options['url']
            urlparams = options['params']
            requestheaders = {}

        # sign request (for Amazon tab)
        if hasattr(self, "signRequest"):
            requestheaders = self.signRequest(urlpath, urlparams, requestheaders, method, payload, options)

        return method, urlpath, urlparams, payload, requestheaders

    def initSession(self, no=0, renew=False):
        """
        Return existing session or create a new session if necessary
        :param no: Session number
        :return: session
        """
        with self.lock_session:
            while (len(self.sessions) <= no):
                self.sessions.append(None)

            session = self.sessions[no] if not renew else None

            if session is None:
                session = requests.Session()
                session.proxies.update(self.getProxies())

                # Mount new adapters = don't cache connections
                adapter = requests.adapters.HTTPAdapter()
                session.mount('http://', adapter)
                session.mount('https://', adapter)
                session.mount('file://', LocalFileAdapter())

            self.sessions[no] = session

        return session

    def closeSession(self, no=0):
        """
        Close the session
        :param no: number of session
        :return: None
        """
        with self.lock_session:
            if (len(self.sessions) > no) and (self.sessions[no] is not None):
                self.sessions[no].close()
                self.sessions[no] = None

    def request(self, session_no=0, path=None, args=None, headers=None, method="GET", payload=None,foldername=None,
                                                      filename=None, fileext=None, format='json'):
        """
        Start a new threadsafe session and request
        """

        def download(response,foldername=None,filename=None,fileext=None):
            if foldername is not None and filename is not None:
                if fileext is None:
                    contentype = response.headers.get("content-type")
                    if contentype is not None:
                        guessed_ext = guess_all_extensions(contentype)
                        fileext = guessed_ext[-1] if len(guessed_ext) > 0 else None
                    else:
                        fileext = None


                fullfilename = makefilename(path,foldername, filename, fileext)
                file = open(fullfilename, 'wb')
            else:
                fullfilename = None
                file = None

            # requests completely downloads data to memory if not stream=True
            # iter_content, text and content all fall back to the previously downloaded content
            # no need to download into string object a second time

            try:
                content = io.BytesIO()
                try:
                    for chunk in response.iter_content(1024):
                        content.write(chunk)
                        if file is not None:
                            file.write(chunk)


                    out = content.getvalue()
                    encoding = cchardet.detect(out)['encoding']
                    encoding = 'utf-8' if encoding is None else encoding
                    out = out.decode(encoding)

                except Exception as e:
                    out = str(e)
                finally:
                    content.close()
            finally:
                if file is not None:
                    file.close()

            # if file is not None:
            #     try:
            #         for chunk in response.iter_content(1024):
            #             file.write(chunk)
            #     finally:
            #         file.close()


            return (fullfilename, out)

        #Throttle speed
        if (self.speed is not None) and (self.lastrequest is not None):
            pause = ((60 * 1000) / float(self.speed)) - self.lastrequest.msecsTo(QDateTime.currentDateTime())
            while (self.connected) and (pause > 0):
                time.sleep(0.1)
                pause = ((60 * 1000) / float(self.speed)) - self.lastrequest.msecsTo(QDateTime.currentDateTime())

        self.lastrequest = QDateTime.currentDateTime()

        if session_no is None:
            session_no = 0
            self.closeSession(session_no)

        session = self.initSession(session_no)

        try:
            response = None
            try:
                maxretries = 3
                while True:
                    try:
                        if (not session):
                            raise Exception("No session available.")

                        # Use cookie jar instead of header to persist redirects
                        cookies = headers.pop('Cookie', None) if headers is not None else None
                        if cookies is not None:
                            cookies = dict(item.split("=",maxsplit=1) for item in cookies.split(";"))

                        # Send request
                        response = session.request(method,path, params=args, headers=headers, cookies=cookies,
                                                   data=payload, timeout=self.timeout,stream=True,verify=True) # verify=False

                    except (HTTPError, ConnectionError) as e:
                        maxretries -= 1

                        # Try next request with new session
                        if (maxretries > 0) and (self.connected):
                            time.sleep(0.1)
                            session = self.initSession(session_no, True)
                            self.logMessage("Automatic retry: Request Error: {0}".format(str(e)))
                        else:
                            raise e
                    else:
                        break

                if int(response.headers.get('content-length',0)) > (self.maxsize * 1024 * 1024):
                    raise DataTooBigError(f"File is too big, content length is {response.headers['content-length']}.")

                status = 'fetched' if response.ok else 'error'
                status = status + ' (' + str(response.status_code) + ')'
                headers = dict(list(response.headers.items()))

                # Download data
                data = {
                    'content-type': response.headers.get("content-type",""),
                    'sourcepath': path,'sourcequery': args,'finalurl': response.url
                }

                fullfilename, content = download(response, foldername, filename, fileext)

                if fullfilename is not None:
                    data['filename'] = os.path.basename(fullfilename)
                    data['filepath'] = fullfilename

                # Text
                if format == 'text':
                        data['text'] = content  # str(response.text)

                 # Scrape links
                elif format == 'links':
                    try:
                        links, base = extractLinks(content, response.url)
                        data['links'] = links
                        data['base'] = base
                    except Exception as  e:
                        data['error'] = 'Could not extract Links.'
                        data['message'] = str(e)
                        data['response'] = content

                # JSON
                elif format == 'json':
                    try:
                        data = json.loads(content) if content != '' else []
                    except Exception as e:
                        # self.logMessage("No valid JSON data, try to convert XML to JSON ("+str(e)+")")
                        # try:
                        #     data = xmlToJson(response.text)
                        # except:
                        data = {
                            'error': 'Data could not be converted to JSON',
                            'response': content,
                            'exception':str(e)
                        }

                # JSON
                elif format == 'xml':
                    try:
                        data = xmlToJson(content)
                    except Exception as e:
                        data = {
                            'error': 'Data could not be converted to JSON',
                            'response': content,
                            'exception':str(e)
                        }


            except Exception as e:
            #except (DataTooBigError, HTTPError, ReadTimeout, ConnectionError, InvalidURL, MissingSchema) as e:
                status = 'request error'
                data = {'error':str(e)}
                headers = {}

                #raise Exception("Request Error: {0}".format(str(e)))
        finally:
            if response is not None:
                response.close()

            return data, headers, status


    def disconnectSocket(self):
        """Used to hardly disconnect the streaming client"""
        self.connected = False
        while (len(self.sessions) > 0):
            session = self.sessions.pop()
            session.close()

        #self.response.raw._fp.close()
        #self.response.close()

    @Slot()
    def captureData(self, nodedata, options=None, logData=None, logMessage=None, logProgress=None):
        session_no = options.get('threadnumber',0)
        self.connected = True

        # Init pagination
        options = self.initPagingOptions(nodedata, options)
        if options is None:
            return False

        # file settings
        foldername, filename, fileext = self.getFileFolderName(options, nodedata)

        format = options.get('format', 'json')
        if format == 'file':
            if (foldername is None) or (not os.path.isdir(foldername)):
                raise Exception("Folder does not exists, select download folder, please!")

        # build url
        method, urlpath, urlparams, payload, requestheaders = self.buildUrl(nodedata, options, logProgress)

        if not urlpath:
            logMessage("Empty path, node {0} skipped.".format(nodedata['objectid']))
            return False

        if not urlpath.startswith(('https://','http://','file://')):
            logMessage("Http or https missing in path, node {0} skipped.".format(nodedata['objectid']))
            return False

        if options['logrequests']:
            logpath = self.getLogURL(urlpath,urlparams,options)
            logMessage("Capturing data for {0} from {1}".format(nodedata['objectid'], logpath))

        # Show browser
        self.browserWindow = BrowserDialog(self.mainWindow, "Browser", 800, 600)
        self.browserWindow.logMessage.connect(logMessage)
        self.browserWindow.activateCaptureButton(logData)
        url = urlpath + '?' + urllib.parse.urlencode(urlparams)
        self.browserWindow.loadPage(url, requestheaders, options, foldername, filename, fileext)

        # for data, headers, status in self.browserWindow.capturePage(
        #         session_no,urlpath, urlparams, requestheaders, method, payload,
        #         foldername, filename, fileext, format=format, strip):
        #     options['querytime'] = str(datetime.now())
        #     options['querystatus'] = status
        #     logData(data, options, headers)

        return True

    @Slot()
    def loadFinished(self, success):
        if (not success and not self.loginWindow.stopped):
            self.logMessage('Error loading web page')


    def selectFolder(self):
        datadir = self.folderEdit.text()
        datadir = os.path.dirname(self.mainWindow.settings.value('lastpath', '')) if datadir == '' else datadir 
        datadir = os.path.expanduser('~') if datadir == '' else datadir        
        
        dlg = SelectFolderDialog(self, 'Select Upload Folder', datadir)
        if dlg.exec_():
            if dlg.optionNodes.isChecked():
                newnodes = [os.path.basename(f)  for f in dlg.selectedFiles()]
                self.mainWindow.tree.treemodel.addSeedNodes(newnodes)
                folder = os.path.dirname(dlg.selectedFiles()[0])
                self.folderEdit.setText(folder)            
            else:
                folder = dlg.selectedFiles()[0]
                self.folderEdit.setText(folder)

    def selectDownloadFolder(self):
        datadir = self.downloadfolderEdit.text()
        datadir = os.path.dirname(self.mainWindow.settings.value('lastpath', '')) if datadir == '' else datadir
        datadir = os.path.expanduser('~') if datadir == '' else datadir

        dlg = SelectFolderDialog(self, 'Select Download Folder', datadir)
        if dlg.exec_():
            if dlg.optionNodes.isChecked():
                newnodes = [os.path.basename(f) for f in dlg.selectedFiles()]
                self.mainWindow.tree.treemodel.addSeedNodes(newnodes)
                folder = os.path.dirname(dlg.selectedFiles()[0])
                self.downloadfolderEdit.setText(folder)
            else:
                folder = dlg.selectedFiles()[0]
                self.downloadfolderEdit.setText(folder)

    def getGlobalOptions(self):
        # Get global options
        settings = {}
        settings['nodelevel'] = self.mainWindow.levelEdit.value()
        settings['excludetypes'] = self.mainWindow.typesEdit.text()

        settings['threads'] = self.mainWindow.threadsEdit.value()
        settings['speed'] = self.mainWindow.speedEdit.value()
        settings['errors'] = self.mainWindow.errorEdit.value()
        settings['expand'] = self.mainWindow.autoexpandCheckbox.isChecked()
        settings['logrequests'] = self.mainWindow.logCheckbox.isChecked()
        settings['saveheaders'] = self.mainWindow.headersCheckbox.isChecked()
        settings['fulloffcut'] = self.mainWindow.offcutCheckbox.isChecked()
        settings['timeout'] = self.mainWindow.timeoutEdit.value()
        settings['maxsize'] = self.mainWindow.maxsizeEdit.value()
        settings['allnodes'] = self.mainWindow.allnodesCheckbox.isChecked()
        settings['resume'] = self.mainWindow.resumeCheckbox.isChecked()
        settings['emptyonly'] = self.mainWindow.emptyCheckbox.isChecked()

        return settings

    def setGlobalOptions(self, settings):
        value = settings.get('nodelevel', None)  # default None
        if value is not None:
            self.mainWindow.levelEdit.setValue(int(value))

        value = settings.get('excludetypes', None)  # default None
        if value is not None:
            self.mainWindow.typesEdit.setText(str(value))

        value = settings.get('threads', None)  # default None
        if value is not None:
            self.mainWindow.threadsEdit.setValue(int(value))

        value = settings.get('speed')  # default 200
        if value is not None:
            self.mainWindow.speedEdit.setValue(int(value))

        value = settings.get('errors', None)  # default None
        if value is not None:
            self.mainWindow.errorEdit.setValue(int(value))

        value = settings.get('expand', None)  # default None
        if value is not None:
            self.mainWindow.autoexpandCheckbox.setChecked(bool(value))

        value = settings.get('saveheaders', None)  # default None
        if value is not None:
            self.mainWindow.headersCheckbox.setChecked(bool(value))

        value = settings.get('fulloffcut', None)  # default None
        if value is not None:
            self.mainWindow.offcutCheckbox.setChecked(bool(value))

        value = settings.get('timeout')  # default 15
        if value is not None:
            self.mainWindow.timeoutEdit.setValue(int(value))

        value = settings.get('maxsize')  # default 5
        if value is not None:
            self.mainWindow.maxsizeEdit.setValue(int(value))

        value = settings.get('logrequests', None)  # default None
        if value is not None:
            self.mainWindow.logCheckbox.setChecked(bool(value))

        value = settings.get('allnodes', None)  # default None
        if value is not None:
            self.mainWindow.allnodesCheckbox.setChecked(bool(value))

        value = settings.get('resume', None)  # default None
        if value is not None:
            self.mainWindow.resumeCheckbox.setChecked(bool(value))

        value = settings.get('emptyonly', None)  # default None
        if value is not None:
            self.mainWindow.emptyCheckbox.setChecked(bool(value))

class AuthTab(ApiTab):
    """
    Module providing authorization
    - init input fields
    - login windows
    - open authorization support
    """

    # see YoutubeTab for keys in the options-parameter
    def __init__(self, mainWindow=None, name='NoName'):
        super(AuthTab, self).__init__(mainWindow, name)

        self.loginServerInstance = None

        self.defaults['login_buttoncaption'] = " Login "
        self.defaults['login_window_caption'] = "Login Page"
        self.defaults['auth_type'] = "Disable"

    def cleanup(self):
        if self.loginServerInstance is not None:
            self.loginServerInstance.shutdown()

    def initAuthSetupInputs(self):
        authlayout = QFormLayout()
        authlayout.setContentsMargins(0, 0, 0, 0)
        self.authWidget.setLayout(authlayout)

        self.authTypeEdit = QComboBox()
        self.authTypeEdit.addItems(['Disable','API key','OAuth2', 'Cookie', 'OAuth2 Client Credentials'])
        authlayout.addRow("Authentication type", self.authTypeEdit)

        self.authURIEdit = QLineEdit()
        authlayout.addRow("Login URI", self.authURIEdit)

        self.redirectURIEdit = QLineEdit()
        authlayout.addRow("Redirect URI", self.redirectURIEdit)

        self.tokenURIEdit = QLineEdit()
        authlayout.addRow("Token URI", self.tokenURIEdit)

        self.clientIdEdit = QLineEdit()
        self.clientIdEdit.setEchoMode(QLineEdit.Password)
        authlayout.addRow("Client Id", self.clientIdEdit)

        self.clientSecretEdit = QLineEdit()
        self.clientSecretEdit.setEchoMode(QLineEdit.Password)
        authlayout.addRow("Client Secret", self.clientSecretEdit)

        self.scopeEdit = QLineEdit()
        authlayout.addRow("Scopes", self.scopeEdit)

        self.proxyEdit = QLineEdit()
        self.proxyEdit .setToolTip(wraptip("The proxy will be used for fetching data only, not for the login procedure."))
        authlayout.addRow("Proxy", self.proxyEdit)


    @Slot()
    def editAuthSettings(self):
        dialog = QDialog(self,Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        dialog.setWindowTitle("Authentication settings")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout()
        layout.addWidget(self.authWidget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        dialog.setLayout(layout)

        def close():
            dialog.close()

        def apply():
            # Auth type: 'Disable','API key','OAuth2', 'OAuth2 Client Credentials','Cookie'
            try:
                if self.authTypeEdit.currentText() == 'Disable':
                    self.authEdit.setCurrentIndex(self.authEdit.findText('disable'))
                    self.tokenNameEdit.setText('')
                elif self.authTypeEdit.currentText() == 'API key':
                    pass
                elif self.authTypeEdit.currentText() == 'OAuth2':
                    self.authEdit.setCurrentIndex(self.authEdit.findText('header'))
                    self.tokenNameEdit.setText('Authorization')
                elif self.authTypeEdit.currentText() == 'OAuth2 Client Credentials':
                    self.authEdit.setCurrentIndex(self.authEdit.findText('header'))
                    self.tokenNameEdit.setText('Authorization')
                elif self.authTypeEdit.currentText() == 'Cookie':
                    self.authEdit.setCurrentIndex(self.authEdit.findText('header'))
                    self.tokenNameEdit.setText('Cookie')

            except AttributeError:
                pass

            dialog.close()

        #connect the nested functions above to the dialog-buttons
        buttons.accepted.connect(apply)
        buttons.rejected.connect(close)
        dialog.exec_()

    def initLoginInputs(self, toggle=True):
        # token and login button
        loginlayout = QHBoxLayout()

        if toggle:
            self.authEdit = QComboBox(self)
            self.authEdit.addItems(['disable', 'param', 'header'])
            self.authEdit.setToolTip(wraptip(
                "Disable: no authorization. Param: an access_token parameter containing the access token will be added to the query. Header: a header containing the access token will be sent."))
            loginlayout.addWidget(self.authEdit)

            loginlayout.addWidget(QLabel("Name"))
            self.tokenNameEdit = QLineEdit()
            self.tokenNameEdit.setToolTip(wraptip("The name of the access token parameter or the authorization header. If you select an authentication method different from API key (e.g. OAuth2 or Cookie), name the is overriden by the selected method."))
            # If you leave this empty, the default value is 'access_token' for param-method and 'Authorization' for header-method.
            loginlayout.addWidget(self.tokenNameEdit,1)

            rowcaption = "Authorization"
            loginlayout.addWidget(QLabel("Access token"))
        else:
            rowcaption = "Access token"

        self.tokenEdit = QLineEdit()
        self.tokenEdit.setEchoMode(QLineEdit.Password)
        loginlayout.addWidget(self.tokenEdit,2)

        self.authButton = QPushButton('Settings', self)
        self.authButton.clicked.connect(self.editAuthSettings)
        loginlayout.addWidget(self.authButton)

        self.loginButton = QPushButton(self.defaults.get('login_buttoncaption', "Login"), self)
        self.loginButton.setToolTip(wraptip(
            "Sometimes you need to register your own app at the platform of the API provider. Adjust the settings and login,"))
        self.loginButton.clicked.connect(self.doLogin)
        loginlayout.addWidget(self.loginButton)

        #self.mainLayout.addRow(rowcaption, loginwidget)
        self.extraLayout.addRow(rowcaption, loginlayout)

    def getSettings(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = super(AuthTab, self).getSettings(purpose)
        defaults = self.getDefaultAndDocOptions()

        # Auth type
        try:
            options['auth_type'] = self.authTypeEdit.currentText().strip() if self.authTypeEdit.currentText() != "" else defaults.get('auth_type', '')
        except AttributeError:
            options['auth_type'] = defaults.get('auth_type', '')

        # OAUTH URIs
        try:
            options[
                'auth_uri'] = self.authURIEdit.text().strip() if self.authURIEdit.text() != "" else defaults.get(
                'auth_uri', '')
            options[
                'redirect_uri'] = self.redirectURIEdit.text().strip() if self.redirectURIEdit.text() != "" else defaults.get(
                'redirect_uri', '')
            options[
                'token_uri'] = self.tokenURIEdit.text().strip() if self.tokenURIEdit.text() != "" else defaults.get(
                'token_uri', '')
        except AttributeError:
            options['auth_uri'] = defaults.get('auth_uri', '')
            options['redirect_uri'] = defaults.get('redirect_uri', '')
            options['token_uri'] = defaults.get('token_uri', '')

        try:
            options['auth'] = self.authEdit.currentText().strip() \
                if self.authEdit.currentText() != "" \
                else defaults.get('auth', 'disable')

            options['auth_tokenname'] = self.tokenNameEdit.text()

        except AttributeError:
            options.pop('auth_tokenname',None)
            options['auth'] = defaults.get('auth', 'disable')

        # Override authorization settings (token handling)
        # based on authentication settings

        if options.get('auth_type') == 'OAuth2':
            #options['auth'] = 'header'
            options['auth_prefix'] = "Bearer "
            #options['auth_tokenname'] = "Authorization"
        elif options.get('auth_type') == 'OAuth2 Client Credentials':
            #options['auth'] = 'header'
            options['auth_prefix'] = "Bearer "
            #options['auth_tokenname'] = "Authorization"
        elif options.get('auth_type') == 'OAuth1':
            #options['auth'] = 'disable' # managed by Twitter module
            options['auth_prefix'] = ''
            #options['auth_tokenname'] = ''
        elif options.get('auth_type') == 'Cookie':
            #options['auth'] = 'header'
            options['auth_prefix'] = ''
            #options['auth_tokenname'] = 'Cookie'

        if options['auth'] == 'disable':
            options['auth_prefix'] = ''
            options['auth_tokenname'] = ''

        return options


    # Transfer options to GUI
    def setSettings(self, settings = {}):
        settings = super(AuthTab, self).setSettings(settings)

        # Merge options
        options = self.getDefaultAndDocOptions(settings)

        # Legacy types
        if options.get('auth_type') == 'Twitter OAuth1':
            options['auth_type'] = 'OAuth1'
        if options.get('auth_type') == 'Twitter App-only':
            options['auth_type'] = 'OAuth2 Client Credentials'

        # Override defaults
        if options.get('auth_type') == 'OAuth2':
            options['auth'] = 'header'
            options['auth_prefix'] = "Bearer "
            options['auth_tokenname'] = "Authorization"
        elif options.get('auth_type') == 'OAuth2 Client Credentials':
            options['auth'] = 'header'
            options['auth_prefix'] = "Bearer "
            options['auth_tokenname'] = "Authorization"
        elif options.get('auth_type') == 'OAuth1':
            options['auth'] = 'disable'  # managed by Twitter module
            options['auth_prefix'] = ''
            options['auth_tokenname'] = ''
        elif options.get('auth_type') == 'Cookie':
            options['auth'] = 'header'
            options['auth_prefix'] = ''
            options['auth_tokenname'] = 'Cookie'

        try:
            self.authTypeEdit.setCurrentIndex( \
                self.authTypeEdit.findText(options.get('auth_type', 'Disable')))
            self.authURIEdit.setText(options.get('auth_uri'))
            self.redirectURIEdit.setText(options.get('redirect_uri'))
            self.tokenURIEdit.setText(options.get('token_uri'))
        except AttributeError:
            pass

        try:
            self.authEdit.setCurrentIndex(self.authEdit.findText(options.get('auth', 'disable')))
            self.tokenNameEdit.setText(options.get('auth_tokenname'))
        except AttributeError:
            pass

        return options

    def fetchData(self, nodedata, options=None, logData=None, logMessage=None, logProgress=None):
        # Preconditions
        if not self.auth_userauthorized and self.auth_preregistered:
            raise Exception('You are not authorized, login please!')

        session_no = options.get('threadnumber',0)
        self.closeSession(session_no)
        self.connected = True
        self.speed = options.get('speed', None)
        self.timeout = options.get('timeout', 15)
        self.maxsize = options.get('maxsize', 5)

        # Init pagination
        options = self.initPagingOptions(nodedata, options)
        if options is None:
            return False

        # file settings
        foldername, filename, fileext = self.getFileFolderName(options, nodedata)

        format = options.get('format', 'json')
        if format == 'file':
            if (foldername is None) or (not os.path.isdir(foldername)):
                raise Exception("Folder does not exists, select download folder, please!")

        # Abort condition: maximum page count
        for page in range(options.get('currentpage', 0), options.get('pages', 1)):
            # Save page
            options['currentpage'] = page


            # build url
            method, urlpath, urlparams, payload, requestheaders = self.buildUrl(nodedata, options, logProgress)

            if not urlpath:
                logMessage("Empty path, node {0} skipped.".format(nodedata['objectid']))
                return False

            if not urlpath.startswith(('https://','http://','file://')):
                logMessage("Http or https missing in path, node {0} skipped.".format(nodedata['objectid']))
                return False

            if options['logrequests']:
                logpath = self.getLogURL(urlpath,urlparams,options)
                logMessage("Fetching data for {0} from {1}".format(nodedata['objectid'], logpath))

            # data
            options['querytime'] = str(datetime.now())
            data, headers, status = self.request(session_no,urlpath, urlparams, requestheaders, method, payload,
                                                 foldername, filename, fileext, format=format)

            # status handling
            options['querystatus'] = status
            options['ratelimit'] = (status == "error (429)")

            # return data
            logData(data, options, headers)

            # rate limit info
            # if 'x-rate-limit-remaining' in headers:
            #     options['info'] = {'x-rate-limit-remaining': u"{} requests remaining until rate limit".format(headers['x-rate-limit-remaining'])}

            # Progress
            if logProgress is not None:
                logProgress({'page': page + 1})

            # Paging
            options = self.updatePagingOptions(data, options)
            if options is None:
                break

            if not self.connected:
                break

        return True



    @Slot()
    def doLogin(self, session_no = 0):
        """
        Show login window
        :param session_no: the number of the session used for login
        :return:
        """
        self.closeSession(session_no)
        options = self.getSettings()

        if options['auth_type'] == 'OAuth2 Client Credentials':
            self.doTwitterAppLogin(session_no)
        elif options['auth_type'] == 'OAuth1':
            self.doOAuth1Login(session_no)
        elif options['auth_type'] == 'Cookie':
            self.doCookieLogin(session_no)
        elif options['auth_type'] == 'API key':
            QMessageBox.information(self, "Facepager", "Manually enter your API key into the access token field or change the authentication method in the settings.")
        elif options['auth_type'] == 'Disable':
            QMessageBox.information(self, "Login disabled","No authentication method selected. Please choose a method in the settings.", QMessageBox.StandardButton.Ok)
        elif options['auth_type'] == 'OAuth2 External':
            self.doOAuth2ExternalLogin(session_no)
        else:
            self.doOAuth2Login(session_no)

    @Slot()
    def doOAuth1Login(self, session_no = 0):
        try:
            # use credentials from input if provided
            clientid = self.getClientId()
            if clientid is None:
                return False

            service = self.getOAuth1Service()

            self.oauthdata.pop('oauth_verifier', None)
            self.oauthdata['requesttoken'], self.oauthdata[
                'requesttoken_secret'] = service.get_request_token()

            self.showLoginWindow(self.defaults.get('login_window_caption', 'Login'),
                                 service.get_authorize_url(self.oauthdata['requesttoken']),
                                 self.defaults.get('login_window_width', 600),
                                 self.defaults.get('login_window_height', 600)
                                 )
        except Exception as e:
            QMessageBox.critical(self, "Login canceled",
                                 str(e),
                                 QMessageBox.StandardButton.Ok)

    @Slot()
    def doOAuth2Login(self, session_no=0):
        try:
            options = self.getSettings()

            # use credentials from input if provided
            clientid = self.getClientId()
            if clientid is None:
                return False

            scope = self.scopeEdit.text() if self.scopeEdit.text() != "" else self.defaults.get('scope', None)
            loginurl = options.get('auth_uri', '')

            if loginurl == '':
                raise Exception('Login URL is missing, please adjust settings!')

            if clientid == '':
                raise Exception('Client Id is missing, please adjust settings!')

            params = {'client_id': clientid,
                      'redirect_uri': options['redirect_uri'],
                      'response_type': options.get('response_type', 'code')}

            if scope is not None:
                params['scope'] = scope


            #params = '&'.join('%s=%s' % (key, value) for key, value in iter(params.items()))
            #url =  loginurl + "?" + params
            urlpath, urlparams, templateparams = self.getURL(loginurl,params,{},{})
            url = urlpath + '?' + urllib.parse.urlencode(urlparams)

            self.showLoginWindow(self.defaults.get('login_window_caption', 'Login'),
                                 url,
                                 self.defaults.get('login_window_width', 600),
                                 self.defaults.get('login_window_height', 600)
                                 )
        except Exception as e:
            QMessageBox.critical(self, "Login canceled",
                                 str(e),
                                 QMessageBox.StandardButton.Ok)

    @Slot()
    def doOAuth2ExternalLogin(self, session_no=0):
        try:
            options = self.getSettings()

            # use credentials from input if provided
            clientid = self.getClientId()
            if clientid is None:
                return False

            scope = self.scopeEdit.text() if self.scopeEdit.text() != "" else self.defaults.get('scope', None)
            loginurl = options.get('auth_uri', '')

            if loginurl == '':
                raise Exception('Login URL is missing, please adjust settings!')

            if clientid == '':
                raise Exception('Client Id is missing, please adjust settings!')

            self.startLoginServer(0)
            redirect_uri = "http://localhost:"+str(self.loginServerInstance.server_port)

            params = {'client_id': clientid,
                      'redirect_uri': redirect_uri,
                      'response_type': options.get('response_type', 'code')}

            if scope is not None:
                params['scope'] = scope

            params = '&'.join('%s=%s' % (key, value) for key, value in iter(params.items()))
            url = loginurl + "?" + params

            webbrowser.open(url)

        except Exception as e:
            QMessageBox.critical(self, "Login canceled",
                                 str(e),
                                 QMessageBox.StandardButton.Ok)


    @Slot()
    def doCookieLogin(self, session_no=0):
        def newCookie(domain, cookie):
            self.tokenEdit.setText(cookie)
            # print("Domain: "+domain+". Cookie: "+cookie)

        try:
            options = self.getSettings()
            url= options.get('auth_uri', '')

            if url == '':
                raise Exception('Login URL is missing, please adjust settings!')

            self.loginWindow = BrowserDialog(
                self.mainWindow,
                self.defaults.get('login_window_caption', 'Login'),
                self.defaults.get('login_window_width', 600),
                self.defaults.get('login_window_height', 600)
            )

            self.loginWindow.logMessage.connect(self.logMessage)
            self.loginWindow.activateCookieButton(newCookie)
            self.loginWindow.loadPage(url)

        except Exception as e:
            QMessageBox.critical(self, "Login canceled",
                                 str(e),
                                 QMessageBox.StandardButton.Ok)

    @Slot()
    def doTwitterAppLogin(self, session_no=0):
        try:
            # See https://developer.twitter.com/en/docs/basics/authentication/overview/application-only
            self.auth_preregistered = False
            clientid = self.clientIdEdit.text() # no defaults
            if clientid == '':
                raise Exception('Client Id is missing, please adjust settings!')

            clientsecret = self.clientSecretEdit.text() # no defaults
            if clientsecret == '':
                raise Exception('Client Secret is missing, please adjust settings!')

            options = self.getSettings()
            path= options.get('auth_uri', '')
            if path == '':
                raise Exception('Login URL is missing, please adjust settings!')


            basicauth = urllib.parse.quote_plus(clientid) + ':' + urllib.parse.quote_plus(clientsecret)
            basicauth = base64.b64encode(basicauth.encode('utf-8')).decode('utf-8')

            payload = 'grant_type=client_credentials'
            headers = {'Authorization': 'Basic ' + basicauth,
                       'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}

            data, headers, status = self.request(None, path, payload=payload, headers=headers, method="POST")

            token = data.get('access_token', '')
            self.tokenEdit.setText(token)

            try:
                self.tokensecretEdit.setText('')
            except AttributeError:
                pass

            if token != '':
                QMessageBox.information(self, "Login", "Login succeeded, got new access token.",
                                        QMessageBox.StandardButton.Ok)
            else:
                raise Exception("Check your settings, no token could be retrieved.")
        except Exception as e:
            QMessageBox.critical(self, "Login failed",
                                 str(e),
                                 QMessageBox.StandardButton.Ok)


    @Slot()
    def showLoginWindow(self, caption='', url='',width=600,height=600):
        """
        Create a SSL-capable WebView for the login-process
        Uses a Custom QT-Webpage Implementation
        Supply a onLoginWindowChanged-Slot to fetch the API-Token
        """

        self.loginWindow = QMainWindow(self.mainWindow)
        self.loginWindow.setAttribute(Qt.WA_DeleteOnClose)
        self.loginWindow.resize(width, height)
        self.loginWindow.setWindowTitle(caption)
        self.loginWindow.stopped = False
        self.loginWindow.cookie = ''


        #create WebView with Facebook log-Dialog, OpenSSL needed
        self.loginStatus = self.loginWindow.statusBar()
        self.login_webview = QWebEngineView(self.loginWindow)
        self.loginWindow.setCentralWidget(self.login_webview)

        # Use the custom- WebPage class
        webpage = WebPageCustom(self.login_webview)
        webpage.logMessage.connect(self.logMessage)
        self.login_webview.setPage(webpage)

        #Connect to the onLoginWindowChanged-method
        self.login_webview.urlChanged.connect(self.onLoginWindowChanged)
        webpage.urlNotFound.connect(self.onLoginWindowChanged) #catch redirects to localhost or nonexistent uris

        # Connect to the loadFinished-Slot for an error message
        self.login_webview.loadFinished.connect(self.loadFinished)

        self.login_webview.load(QUrl(url))
        self.login_webview.show()
        self.loginWindow.show()

    @Slot()
    def closeLoginWindow(self):
        if self.loginWindow is None:
            return False

        self.loginWindow.stopped = True
        self.login_webview.stop()
        self.loginWindow.close()
        self.loginWindow = None

    @Slot()
    def onLoginWindowChanged(self, url=False):
        options = self.getSettings()

        if options['auth_type'] == 'OAuth2 Client Credentials':
            return False
        elif options['auth_type'] == 'OAuth1':
            url = self.login_webview.url().toString()
            success = self.getOAuth1Token(url)
            if success:
                self.closeLoginWindow()
        else:
            url = url.toString()
            options = self.getSettings()
            if url.startswith(options['redirect_uri']):
                if self.getOAuth2Token(url):
                    self.closeLoginWindow()

    @Slot()
    def startLoginServer(self, port):
        self.stopLoginServer()
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

        self.loginServerInstance = LoginServer(port, self.onLoginServerRedirect)
        self.loginServerThread = threading.Thread(target=self.loginServerInstance.serve_forever)
        self.loginServerThread.start()
        port = self.loginServerInstance.server_port
        self.defaults['redirect_uri'] = 'http://localhost:%d' % port
        self.logMessage('Login server listening at http://localhost:%d.' % port)

    @Slot()
    def stopLoginServer(self):
        if self.loginServerInstance is not None:
            self.loginServerInstance.shutdown()
            self.logMessage('Login server stopped.')
            self.loginServerInstance = None

    def onLoginServerRedirect(self, path):
        options = self.getSettings()
        url = options['redirect_uri'] + path
        if self.getOAuth2Token(url):
            self.stopLoginServer()
            return "https://strohne.github.io/Facepager/oauth_feedback.html"
        else:
            return None

    @Slot()
    def initSession(self, no=0, renew=False):
        """
        Dispatch session initialization to specialized functions
        :param no: session number
        :return: session object
        """
        options = self.getSettings()

        if options.get('auth_type') == 'OAuth1':
            return self.initOAuth1Session(no, renew)
        else:
            return self.initOAuth2Session(no, renew)

    def initOAuth1Session(self,no=0, renew=False):
        """
        Return session or create if necessary
        :param no: session number
        :return: session object
        """

        while (len(self.sessions) <= no):
            self.sessions.append(None)

        session = self.sessions[no] if not renew else None
        if session is None:
            if (self.tokenEdit.text() == '') or (self.tokensecretEdit.text() == ''):
                raise Exception("No access, login please!")

            service = self.getOAuth1Service()
            session = service.get_session((self.tokenEdit.text(), self.tokensecretEdit.text()))

        self.sessions[no] = session
        return session

    def initOAuth2Session(self, no=0, renew=False):
        return super(AuthTab, self).initSession(no, renew)

    def getOAuth1Service(self):
        if not hasattr(self,'oauthdata'):
            self.oauthdata = {}

        service = OAuth1Service(
            consumer_key=self.defaults.get('client_id'),
            consumer_secret=self.defaults.get('client_secret'),
            name='oauth1',
            access_token_url=self.defaults.get('access_token_url'),
            authorize_url=self.defaults.get('authorize_url'),
            request_token_url=self.defaults.get('request_token_url'),
            base_url=self.defaults.get('basepath'))

        # clientid = self.getClientId()
        # if clientid is None:
        #     return None

        service.consumer_key = self.clientIdEdit.text() if self.clientIdEdit.text() != "" else \
            self.defaults['client_id']
        service.consumer_secret = self.clientSecretEdit.text() if self.clientSecretEdit.text() != "" else \
            self.defaults['client_secret']
        service.base_url = self.basepathEdit.currentText().strip() if self.basepathEdit.currentText().strip() != "" else \
            self.defaults['basepath']

        if service.consumer_key == '':
            raise Exception('Consumer key is missing, please adjust settings!')
        if service.consumer_secret == '':
            raise Exception('Consumer secret is missing, please adjust settings!')

        return service


    def getOAuth1Token(self, url):
        success = False
        url = urllib.parse.parse_qs(url)
        if "oauth_verifier" in url:
            token = url["oauth_verifier"]
            if token:
                service = self.getOAuth1Service()
                self.oauthdata['oauth_verifier'] = token[0]

                session = service.get_auth_session(self.oauthdata['requesttoken'],
                                                   self.oauthdata['requesttoken_secret'], method="POST",
                                                   data={'oauth_verifier': self.oauthdata['oauth_verifier']})

                # Get user ID
                if self.auth_preregistered:
                    userid = self.getUserId(session)
                    if userid is None:
                        raise Exception("Could not retrieve user ID. Check settings and try again.")

                    self.authorizeUser(userid)
                    if not self.auth_userauthorized:
                        raise Exception("You are not registered at Facepager.")

                self.tokenEdit.setText(session.access_token)
                self.tokensecretEdit.setText(session.access_token_secret)

                session.close()
                success = True
        return success


    def getOAuth2Token(self, url):
        success = False
        try:
            options = self.getSettings()

            urlparsed = urlparse(url)
            query = parse_qs(urlparsed.query)

            if url.startswith(options['redirect_uri']) and query.get('code') is not None:
                try:
                    clientid = self.clientIdEdit.text() if self.clientIdEdit.text() != "" \
                        else self.defaults.get('client_id', '')
                    clientsecret = self.clientSecretEdit.text() if self.clientSecretEdit.text() != "" \
                        else self.defaults.get('client_secret', '')
                    scope = self.scopeEdit.text() if self.scopeEdit.text() != "" else \
                        self.defaults.get('scope', None)

                    headers = options.get("headers",{})
                    headers = {key.lower(): value for (key, value) in headers.items()}

                    session = OAuth2Session(clientid, redirect_uri=options['redirect_uri'], scope=scope)
                    token = session.fetch_token(
                        options['token_uri'],
                        authorization_response=str(url),
                        client_secret=clientsecret,
                        headers=headers
                    )

                    # Get user ID
                    if self.auth_preregistered:
                        userid = self.getUserId(token.get('access_token',''))
                        if userid is None:
                            raise Exception("Could not retrieve user ID. Check settings and try again.")

                        self.authorizeUser(userid)
                        if not self.auth_userauthorized:
                            raise Exception("You are not registered at Facepager.")

                    self.tokenEdit.setText(token.get('access_token',''))

                    try:
                        self.authEdit.setCurrentIndex(self.authEdit.findText('header'))
                    except AttributeError:
                        pass

                    success = True
                finally:
                    session.close()
            elif url.startswith(options['redirect_uri']) and query.get('error') is not None:
                self.logMessage(f"Login error: {query.get('error')}")

        except Exception as e:
            self.logMessage(e)

        return success

    # Get Client ID
    # return custom client ID if provided
    # otherwise login to Facepager and return preregistered ID
    # or return None if login fails
    def getClientId(self):
        if self.clientIdEdit.text() != "":
            self.auth_preregistered = False
            clientid = self.clientIdEdit.text()
        else:
            self.auth_preregistered = True
            clientid = self.defaults.get('client_id', '')

            if clientid == '':
                raise Exception('Client ID missing, please adjust settings!')

            termsurl = self.defaults.get('termsurl', '')
            if termsurl != '':
                proceedDlg = PreLoginWebDialog(self.mainWindow, "Login to Facepager", termsurl)
                if proceedDlg.show() != QDialog.Accepted:
                    return None

        return clientid

    # Retrieves a user ID from the API that
    # later is hashed for maintaining the
    # anonymized user list. REimplement in the modules.
    def getUserId(self):
        return None

    def authorizeUser(self, userid):
        # User ID
        if userid is None:
            self.auth_userauthorized = False
            return False

        # App salt
        salt = getDictValueOrNone(credentials,'facepager.salt')
        if salt is None:
            self.auth_userauthorized = False
            return False

        # Create token
        usertoken = hashlib.pbkdf2_hmac(
            'sha256',  # The hash digest algorithm for HMAC
            userid.encode("utf-8"),
            salt.encode("utf-8"),
            100000  # It is recommended to use at least 100,000 iterations of SHA-256
        )

        # Check token
        authurl = getDictValueOrNone(credentials, 'facepager.url')
        if authurl is None:
            self.auth_userauthorized = False
            return False

        authurl += '?module='+self.name.lower()+'&usertoken='+usertoken.hex()
        session = self.initOAuth2Session(0, True)
        data, headers, status = self.request(0, authurl)
        self.closeSession(0)
        self.auth_userauthorized = status == 'fetched (200)'

        return self.auth_userauthorized


class GenericTab(AuthTab):
    def __init__(self, mainWindow=None):
        super(GenericTab, self).__init__(mainWindow, "Generic")

        #Defaults
        self.timeout = 60
        self.defaults['basepath'] = '<Object ID>'

        # Standard inputs
        self.initInputs()

        # Header, Verbs
        self.initHeaderInputs()
        self.initVerbInputs()
        self.initUploadFolderInput()

        # Extract input
        self.initPagingInputs(True)
        self.initResponseInputs(True)

        self.initFileInputs()

        # Login inputs
        self.initAuthSetupInputs()
        self.initLoginInputs()

        self.loadDoc()
        self.loadSettings()


    def getSettings(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = super(GenericTab, self).getSettings(purpose)

        if purpose != 'preset':
            options['querytype'] = self.name + ':'+options['basepath']+options['resource']

        return options

    # def onSslErrors(self, reply, errors):
    #     url = str(reply.url().toString())
    #     reply.ignoreSslErrors()
    #     self.logmessage.emit("SSL certificate error ignored: %s (Warning: Your connection might be insecure!)" % url)


class FacebookTab(AuthTab):
    def __init__(self, mainWindow=None):
        super(FacebookTab, self).__init__(mainWindow, "Facebook")

        # Authorization
        self.auth_userauthorized = False

        #Defaults
        self.defaults['auth_type'] = "OAuth2"
        self.defaults['scope'] = '' #user_groups
        self.defaults['basepath'] = 'https://graph.facebook.com/v3.4'
        self.defaults['resource'] = '/<Object ID>'
        self.defaults['auth_uri'] = 'https://www.facebook.com/dialog/oauth'
        self.defaults['redirect_uri'] = 'https://www.facebook.com/connect/login_success.html'

        self.defaults['login_buttoncaption'] = " Login to Facebook "

        # Query Box
        self.initInputs()

        # Pages Box
        self.initPagingInputs()

        self.initAuthSettingsInputs()
        self.initLoginInputs(toggle=False)

        self.loadDoc()
        self.loadSettings()

    def initAuthSettingsInputs(self):
        authlayout = QFormLayout()
        authlayout.setContentsMargins(0,0,0,0)
        self.authWidget.setLayout(authlayout)

        self.pageIdEdit = QLineEdit()
        authlayout.addRow("Page Id", self.pageIdEdit)

        self.clientIdEdit = QLineEdit()
        self.clientIdEdit.setEchoMode(QLineEdit.Password)
        authlayout.addRow("Client Id", self.clientIdEdit)

        self.scopeEdit = QLineEdit()
        authlayout.addRow("Scopes",self.scopeEdit)

    def getSettings(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = super(FacebookTab, self).getSettings(purpose)

        options['auth'] = 'param'
        options['auth_prefix'] = ''
        options['auth_tokenname'] = 'access_token'

        if purpose != 'preset':
            options['pageid'] = self.pageIdEdit.text().strip()

        return options

    def setSettings(self, settings ={}):
        settings = super(FacebookTab, self).setSettings(settings)

        if 'pageid' in settings:
            self.pageIdEdit.setText(settings.get('pageid'))

        return settings

    def fetchData(self, nodedata, options=None, logData=None, logMessage=None, logProgress=None):
        # Preconditions
        if not self.auth_userauthorized and self.auth_preregistered:
            raise Exception('You are not authorized, login please!')

        if options.get('access_token','') == '':
            raise Exception('Access token is missing, login please!')

        self.connected = True
        self.speed = options.get('speed',None)
        self.timeout = options.get('timeout', 15)
        self.maxsize = options.get('maxsize', 5)
        session_no = options.get('threadnumber', 0)

        # Init pagination
        options = self.initPagingOptions(nodedata, options)
        if options is None:
            return False

        # # Abort condition for time based pagination
        # since = options['params'].get('since', False)
        # if (since != False):
        #     since = dateutil.parser.parse(since, yearfirst=True, dayfirst=False)
        #     since = int((since - datetime(1970, 1, 1)).total_seconds())

        # Abort condition: maximum page count
        for page in range(options.get('currentpage', 0), options.get('pages', 1)):
            # Save page
            options['currentpage'] = page

            method, urlpath, urlparams, payload, requestheaders = self.buildUrl(nodedata, options, logProgress)

            if options['logrequests']:
                logpath = self.getLogURL(urlpath, urlparams, options)
                logMessage("Fetching data for {0} from {1}".format(nodedata['objectid'], logpath))

            # data
            options['querytime'] = str(datetime.now())
            data, headers, status = self.request(session_no,urlpath, urlparams)

            options['ratelimit'] = False
            options['querystatus'] = status

            # rate limit info
            if 'x-app-usage' in headers:
                appusage = json.loads(headers['x-app-usage'])
                appusage = appusage.get('call_count', 'Undefined')
                if appusage > 0:
                    options['info'] = {'x-app-usage': "{} percent of app level rate limit reached.".format(appusage)}


            if (status != "fetched (200)"):
                msg = getDictValue(data,"error.message")
                code = getDictValue(data,"error.code")
                logMessage("Error '{0}' for {1} with message {2}.".format(status, nodedata['objectid'], msg))

                # see https://developers.facebook.com/docs/graph-api/using-graph-api
                # see https://developers.facebook.com/docs/graph-api/advanced/rate-limiting/
                if (code in ['4','17','32','613']) and (status in ['error (400)', 'error (403)']):
                    options['ratelimit'] = True
                else:
                    options['ratelimit'] = False

            logData(data, options, headers)
            if logProgress is not None:
                logProgress({'page':page+1})

            # paging
            options = self.updatePagingOptions(data, options)
            if options is None:
                break

            # # abort time based pagination
            # until = params.get('until', False)
            # if (since != False) and (until != False) and (int(until) < int(since)):
            #     break

            if not self.connected:
                break

    @Slot()
    def doLogin(self, session_no = 0):
        try:
            #use credentials from input if provided
            clientid = self.getClientId()
            if clientid is None:
                return False
            scope= self.scopeEdit.text() if self.scopeEdit.text() != "" else self.defaults.get('scope','')
            

            url = self.defaults['auth_uri'] +"?client_id=" + clientid + "&redirect_uri="+self.defaults['redirect_uri']+"&response_type=token&scope="+scope+"&display=popup"
            caption = "Facebook Login Page"
            self.showLoginWindow(caption, url)
        except Exception as e:
            QMessageBox.critical(self, "Login canceled",str(e),QMessageBox.StandardButton.Ok)

    def getUserId(self, token):
        data, headers, status = self.request(
            None, self.basepathEdit.currentText().strip() +
                  '/me?fields=id&access_token=' + token)
        if status != 'fetched (200)':
            return None

        return data.get('id')

    @Slot(QUrl)
    def onLoginWindowChanged(self, url):
        if "#access_token" in url.toString():
            try:
                url = urllib.parse.urlparse(url.toString(),allow_fragments=True)
                fragment = urllib.parse.parse_qs(url.fragment)
                token = fragment.get('access_token').pop()

                # Get user ID
                if self.auth_preregistered:
                    userid = self.getUserId(token)
                    if userid is None:
                        raise Exception("Could not retrieve user ID. Check settings and try again.")

                    self.authorizeUser(userid)
                    if not self.auth_userauthorized:
                        raise Exception("You are not registered at Facepager.")

                # Get page access token
                pageid = self.pageIdEdit.text().strip()
                if pageid != '':
                    data, headers, status = self.request(None, self.basepathEdit.currentText().strip()+'/'+pageid+'?fields=access_token&scope=pages_show_list&access_token='+token)
                    if status != 'fetched (200)':
                        raise Exception("Could not authorize for page. Check page ID in the settings.")

                    token = data.get('access_token','')

                # Set token
                self.tokenEdit.setText(token)
            except Exception as e:
                QMessageBox.critical(self,"Login error",
                                     str(e),QMessageBox.StandardButton.Ok)
            self.closeLoginWindow()


class AmazonTab(AuthTab):

    # see YoutubeTab for keys in the options-parameter
    def __init__(self, mainWindow=None, name='Amazon'):
        super(AmazonTab, self).__init__(mainWindow, name)

        self.defaults['region'] = 'us-east-1'  # 'eu-central-1'
        self.defaults['service'] = 's3'
        self.defaults['format'] = 'xml'

        # Standard inputs
        self.initInputs()

        # Header, Verbs
        self.initHeaderInputs()
        self.initVerbInputs()
        self.initUploadFolderInput()

        # Extract input
        self.initResponseInputs(True)

        # Pages Box
        self.initPagingInputs(True)

        # Login inputs
        self.initLoginInputs()

        self.loadDoc()
        self.loadSettings()


    def initLoginInputs(self):
        # token and login button
        loginwidget = QWidget()
        loginlayout = QHBoxLayout()
        loginlayout.setContentsMargins(0, 0, 0, 0)
        loginwidget.setLayout(loginlayout)

        self.accesskeyEdit = QLineEdit()
        self.accesskeyEdit.setEchoMode(QLineEdit.Password)
        loginlayout.addWidget(self.accesskeyEdit)

        loginlayout.addWidget(QLabel('Secret Key'))
        self.secretkeyEdit = QLineEdit()
        self.secretkeyEdit.setEchoMode(QLineEdit.Password)
        loginlayout.addWidget(self.secretkeyEdit)

        loginlayout.addWidget(QLabel('Service'))
        self.serviceEdit = QLineEdit()
        loginlayout.addWidget(self.serviceEdit)

        loginlayout.addWidget(QLabel('Region'))
        self.regionEdit = QLineEdit()
        loginlayout.addWidget(self.regionEdit)

        self.extraLayout.addRow("Access Key", loginwidget)

    def getSettings(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = super(AmazonTab, self).getSettings(purpose)

        options['auth'] = 'disable'
        #options['format'] = self.defaults.get('format', '')
        options['service'] = self.serviceEdit.text().strip() if self.serviceEdit.text() != "" else self.defaults.get('service', '')
        options['region'] = self.regionEdit.text().strip() if self.regionEdit.text() != "" else self.defaults.get(
            'region', '')

        if purpose != 'preset':
            options['secretkey'] = self.secretkeyEdit.text().strip() #if self.secretkeyEdit.text() != "" else self.defaults.get('auth_uri', '')
            options['accesskey'] = self.accesskeyEdit.text().strip() #if self.accesskeyEdit.text() != "" else self.defaults.get('redirect_uri', '')

        return options

    def setSettings(self, settings = {}):
        settings = super(AmazonTab, self).setSettings(settings)

        if 'secretkey' in settings:
            self.secretkeyEdit.setText(settings.get('secretkey'))

        if 'accesskey' in settings:
            self.accesskeyEdit.setText(settings.get('accesskey'))

        self.serviceEdit.setText(settings.get('service'))
        self.regionEdit.setText(settings.get('region'))

        return settings


    # Get authorization header
    # See https://docs.aws.amazon.com/de_de/general/latest/gr/sigv4-signed-request-examples.html
    def signRequest(self, urlpath, urlparams, headers, method, payload, options):

        # Access keys
        access_key = options.get('accesskey', '')
        secret_key = options.get('secretkey', '')

        region = options.get('region', '')
        service = options.get('service', '')

        if access_key == '' or secret_key == '':
            raise Exception('Access key or secret key is missing, please fill the input fields!')


        # Key derivation functions. See:
        # http://docs.aws.amazon.com/general/latest/gr/signature-v4-examples.html#signature-v4-examples-python
        def sign(key, msg):
            return hmac.new(key, msg.encode('utf-8'), hashlib.sha256).digest()

        def getSignatureKey(key, dateStamp, regionName, serviceName):
            kDate = sign(('AWS4' + key).encode('utf-8'), dateStamp)
            kRegion = sign(kDate, regionName)
            kService = sign(kRegion, serviceName)
            kSigning = sign(kService, 'aws4_request')
            return kSigning

        timenow = datetime.utcnow()
        amzdate = timenow.strftime('%Y%m%dT%H%M%SZ')
        datestamp = timenow.strftime('%Y%m%d')  # Date w/o time, used in credential scope

        # Create canonical URI--the part of the URI from domain to query string
        urlcomponents = urllib.parse.urlparse(urlpath)
        canonical_uri = '/' if urlcomponents.path == '' else urlcomponents.path

        # Create the canonical query string. In this example (a GET request),
        # request parameters are in the query string. Query string values must
        # be URL-encoded (space=%20). The parameters must be sorted by name.
        # For this example, the query string is pre-formatted in the request_parameters variable.
        urlparams = {} if urlparams is None else urlparams
        canonical_querystring = OrderedDict(sorted(urlparams.items()))
        canonical_querystring = urllib.parse.urlencode(canonical_querystring)

        # Create the canonical headers and signed headers. Header names
        # must be trimmed and lowercase, and sorted in code point order from
        # low to high. Note that there is a trailing \n.
        canonical_headers = {
            'host': urlcomponents.hostname,
            'x-amz-date': amzdate
        }

        if headers is not None:
            canonical_headers.update(headers)

        canonical_headers = {k.lower(): v for k, v in list(canonical_headers.items())}
        canonical_headers = OrderedDict(sorted(canonical_headers.items()))
        canonical_headers_str = "".join(
            [key + ":" + value + '\n' for (key, value) in canonical_headers.items()])

        # Create the list of signed headers. This lists the headers
        # in the canonical_headers list, delimited with ";" and in alpha order.
        # Note: The request can include any headers; canonical_headers and
        # signed_headers lists those that you want to be included in the
        # hash of the request. "Host" and "x-amz-date" are always required.
        signed_headers = ';'.join(list(canonical_headers.keys()))

        # Create payload hash (hash of the request body content). For GET
        # requests, the payload is an empty string ("").
        payload = b'' if payload is None else payload
        if isinstance(payload, BufferReader):
            payload_buffer = payload
            payload = payload_buffer.read()
            payload_buffer.rewind()
            #payload = payload.decode('utf-8')

        payload_hash = hashlib.sha256(payload).hexdigest()

        # Combine elements to create canonical request
        canonical_request = method + '\n' + canonical_uri + '\n' + canonical_querystring + '\n' + canonical_headers_str + '\n' + signed_headers + '\n' + payload_hash

        # Match the algorithm to the hashing algorithm you use, either SHA-1 or
        # SHA-256 (recommended)
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = datestamp + '/' + region + '/' + service + '/' + 'aws4_request'
        string_to_sign = algorithm + '\n' + amzdate + '\n' + credential_scope + '\n' + hashlib.sha256(
            canonical_request.encode('utf-8')).hexdigest()

        # Create the signing key using the function defined above.
        signing_key = getSignatureKey(secret_key, datestamp, region, service)

        # Sign the string_to_sign using the signing_key
        signature = hmac.new(signing_key, (string_to_sign).encode('utf-8'), hashlib.sha256).hexdigest()

        # The signing information can be either in a query string value or in
        # a header named Authorization. This code shows how to use a header.
        # Create authorization header and add to request headers
        authorization_header = algorithm + ' ' + 'Credential=' + access_key + '/' + credential_scope + ', ' + 'SignedHeaders=' + signed_headers + ', ' + 'Signature=' + signature

        # The request can include any headers, but MUST include "host", "x-amz-date",
        # and (for this scenario) "Authorization". "host" and "x-amz-date" must
        # be included in the canonical_headers and signed_headers, as noted
        # earlier. Order here is not significant.
        # Python note: The 'host' header is added automatically by the Python 'requests' library.
        headers.update({'x-amz-date': amzdate,
                        'x-amz-content-sha256': payload_hash,
                        # 'x-amz-content-sha256':'UNSIGNED-PAYLOAD',
                        'Authorization': authorization_header
                        # 'Accepts': 'application/json'
                        })

        return (headers)

class TwitterTab(AuthTab):
    def __init__(self, mainWindow=None):
        super(TwitterTab, self).__init__(mainWindow, "Twitter")

        # Authorization
        self.auth_userauthorized = False

        # Defaults
        self.defaults['basepath'] = 'https://api.twitter.com/1.1'
        self.defaults['resource'] = '/search/tweets'
        self.defaults['params'] = {'q': '<Object ID>'}
        #self.defaults['extension'] = ".json"

        self.defaults['auth_type'] = 'OAuth1'
        self.defaults['access_token_url'] = 'https://api.twitter.com/oauth/access_token'
        self.defaults['authorize_url'] = 'https://api.twitter.com/oauth/authorize'
        self.defaults['request_token_url'] = 'https://api.twitter.com/oauth/request_token'
        self.defaults['login_window_caption'] = 'Twitter Login Page'

        # Query and Parameter Box
        self.initInputs()
        self.initPagingInputs()

        self.initAuthSetupInputs()
        self.initLoginInputs()

        self.loadDoc()
        self.loadSettings()

    def initLoginInputs(self):
        # Login-Boxes
        loginlayout = QHBoxLayout()

        self.tokenEdit = QLineEdit()
        self.tokenEdit.setEchoMode(QLineEdit.Password)
        loginlayout.addWidget(self.tokenEdit)

        loginlayout.addWidget(QLabel("Access Token Secret"))
        self.tokensecretEdit = QLineEdit()
        self.tokensecretEdit.setEchoMode(QLineEdit.Password)
        loginlayout.addWidget(self.tokensecretEdit)

        self.authButton = QPushButton('Settings', self)
        self.authButton.clicked.connect(self.editAuthSettings)
        loginlayout.addWidget(self.authButton)

        self.loginButton = QPushButton(" Login to Twitter ", self)
        self.loginButton.clicked.connect(self.doLogin)
        loginlayout.addWidget(self.loginButton)


        # Add to main-Layout
        self.extraLayout.addRow("Access Token", loginlayout)

    def initAuthSetupInputs(self):
        authlayout = QFormLayout()
        authlayout.setContentsMargins(0, 0, 0, 0)
        self.authWidget.setLayout(authlayout)

        self.authTypeEdit= QComboBox()
        self.authTypeEdit.addItems(['OAuth1', 'OAuth2 Client Credentials'])
        authlayout.addRow("Authentication type", self.authTypeEdit)

        self.clientIdEdit = QLineEdit()
        self.clientIdEdit.setEchoMode(QLineEdit.Password)
        authlayout.addRow("Consumer Key", self.clientIdEdit)

        self.clientSecretEdit = QLineEdit()
        self.clientSecretEdit.setEchoMode(QLineEdit.Password)
        authlayout.addRow("Consumer Secret", self.clientSecretEdit)

    def getSettings(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = super(TwitterTab, self).getSettings(purpose)

        if options['auth_type'] == 'OAuth2 Client Credentials':
            options['auth_uri'] = 'https://api.twitter.com/oauth2/token/'
            options['auth'] = 'header'
            options['auth_prefix'] = 'Bearer '
            options['auth_tokenname'] = "Authorization"

        return options

    def getUserId(self, session):
        # Send request
        response = session.request('GET', 'https://api.twitter.com/1.1/account/settings.json', timeout=self.timeout)
        if not response.ok :
             return None

        data = response.json() if response.text != '' else []
        return getDictValueOrNone(data, 'screen_name')

    def fetchData(self, nodedata, options=None, logData=None, logMessage=None, logProgress=None):
        # Preconditions
        if not self.auth_userauthorized and self.auth_preregistered:
            raise Exception('You are not authorized, login please!')

        self.connected = True
        self.speed = options.get('speed', None)
        self.timeout = options.get('timeout', 15)
        self.maxsize = options.get('maxsize', 5)
        session_no = options.get('threadnumber',0)

        # Init pagination
        options = self.initPagingOptions(nodedata, options)
        if options is None:
            return False

        for page in range(options.get('currentpage', 0), options.get('pages', 1)):
            # Save page
            options = deepcopy(options)
            options['currentpage'] = page

            method, urlpath, urlparams, payload, requestheaders = self.buildUrl(nodedata, options, logProgress)

            if options['logrequests']:
                logpath = self.getLogURL(urlpath, urlparams, options)
                logMessage("Fetching data for {0} from {1}".format(nodedata['objectid'], logpath))

            # data
            data, headers, status = self.request(session_no, urlpath, urlparams, requestheaders)
            options['querytime'] = str(datetime.now())
            options['querystatus'] = status
            options['ratelimit'] = (status == "error (429)")

            # rate limit info
            if 'x-rate-limit-remaining' in headers:
                options['info'] = {'x-rate-limit-remaining': "{} requests remaining until rate limit".format(
                    headers['x-rate-limit-remaining'])}

            logData(data, options, headers)
            if logProgress is not None:
                logProgress({'page': page + 1})

            # Pagination
            paging = self.updatePagingOptions(data, options)

            # paging with next_results; Note: Do not rely on the search_metadata information,
            # sometimes the next_results param is missing, this is a known bug
            # applies to /search/tweets
            if (paging is None) and isinstance(data, dict) and hasDictValue(data, "search_metadata.next_results"):
                paging = options
                url, params = self.parseURL(getDictValue(data, "search_metadata.next_results", False))
                options['url'] = urlpath
                options['params'] = params

                # Workaround for Twitter bug (carry on tweet_mode=extended)
                if 'tweet_mode' in urlparams:
                    options['params']['tweet_mode'] = urlparams['tweet_mode']

            if paging is not None:
                options = paging
            else:
                break

            if not self.connected:
                break



class TwitterStreamingTab(TwitterTab):
    def __init__(self, mainWindow=None):
        super(TwitterTab, self).__init__(mainWindow, "Twitter Streaming")

        # Authorization
        self.auth_userauthorized = False

        self.defaults['auth_type'] = 'OAuth1'
        self.defaults['access_token_url'] = 'https://api.twitter.com/oauth/access_token'
        self.defaults['authorize_url'] = 'https://api.twitter.com/oauth/authorize'
        self.defaults['request_token_url'] = 'https://api.twitter.com/oauth/request_token'
        self.defaults['login_window_caption'] = 'Twitter Login Page'

        self.defaults['basepath'] = 'https://stream.twitter.com/1.1'
        self.defaults['resource'] = '/statuses/filter'
        self.defaults['params'] = {'track': '<Object ID>'}
        #self.defaults['extension'] = ".json"

        self.defaults['key_objectid'] = 'id'
        self.defaults['key_nodedata'] = None

        # Query Box
        self.initInputs()
        self.initAuthSetupInputs()
        self.initLoginInputs()

        self.loadDoc()
        self.loadSettings()

        self.timeout = 30
        self.connected = False

    def stream(self, session_no=0, path='', args=None, headers=None):
        self.connected = True
        self.retry_counter=0
        self.last_reconnect=QDateTime.currentDateTime()
        try:
            session = self.initSession(session_no)

            def _send():
                self.last_reconnect = QDateTime.currentDateTime()
                while self.connected:
                    try:
                        if headers is not None:
                            response = session.post(path, params=args,
                                                         headers=headers,
                                                         timeout=self.timeout,
                                                         stream=True)
                        else:
                            response = session.get(path, params=args, timeout=self.timeout,
                                                        stream=True)

                    except requests.exceptions.Timeout:
                        raise Exception('Request timed out.')
                    else:
                        if response.status_code != 200:
                            if self.retry_counter<=5:
                                self.logMessage("Reconnecting in 3 Seconds: " + str(response.status_code) + ". Message: "+ str(response.content))
                                time.sleep(3)
                                if self.last_reconnect.secsTo(QDateTime.currentDateTime())>120:
                                    self.retry_counter = 0
                                    _send()
                                else:
                                    self.retry_counter+=1
                                    _send()
                            else:
                                #self.connected = False
                                self.disconnectSocket()
                                raise Exception("Request Error: " + str(response.status_code) + ". Message: "+str(response.content))

                        return response


            while self.connected:
                response = _send()
                if response:
                    status = 'fetched' if response.ok else 'error'
                    status = status + ' (' + str(response.status_code) + ')'
                    headers = dict(list(response.headers.items()))

                    for line in response.iter_lines():
                        if not self.connected:
                            break
                        if line:
                            try:
                                data = json.loads(line)
                            except ValueError:  # pragma: no cover
                                raise Exception("Unable to decode response, not valid JSON")
                            else:
                                yield data, headers, status
                else:
                    break
            response.close()

        except AttributeError:
            #This exception is thrown when canceling the connection
            #Only re-raise if not manually canceled
            if self.connected:
                raise
        finally:
            self.connected = False

    def fetchData(self, nodedata, options=None, logData=None, logMessage=None, logProgress=None):
        # Preconditions
        if not self.auth_userauthorized and self.auth_preregistered:
            raise Exception('You are not authorized, login please!')

        if not ('url' in options):
            urlpath = options["basepath"] + options["resource"] + options.get('extension', '')
            urlpath, urlparams, templateparams = self.getURL(urlpath, options["params"], nodedata, options)
        else:
            urlpath = options['url']
            urlparams = options["params"]

        if options['logrequests']:
            logpath = self.getLogURL(urlpath, urlparams, options)
            logMessage("Fetching data for {0} from {1}".format(nodedata['objectid'], logpath))

        self.timeout = options.get('timeout',30)
        self.maxsize = options.get('maxsize', 5)

        # data
        session_no = options.get('threadnumber',0)
        for data, headers, status in self.stream(session_no, path=urlpath, args=urlparams):
            # data
            options['querytime'] = str(datetime.now())
            options['querystatus'] = status

            logData(data, options, headers)

class YoutubeTab(AuthTab):
    def __init__(self, mainWindow=None):

        super(YoutubeTab, self).__init__(mainWindow, "YouTube")

        # Authorization
        self.auth_userauthorized = False

        # Defaults
        self.defaults['auth_type'] = "OAuth2 External"
        self.defaults['auth_uri'] = 'https://accounts.google.com/o/oauth2/auth'
        self.defaults['token_uri'] = "https://accounts.google.com/o/oauth2/token"
        self.defaults['redirect_uri'] = 'https://localhost'
        self.defaults['scope'] = "https://www.googleapis.com/auth/youtube https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.force-ssl"
        self.defaults['response_type'] = "code"

        self.defaults['login_buttoncaption'] = " Login to Google "
        self.defaults['login_window_caption'] = "YouTube Login Page"

        self.defaults['auth'] = 'param'
        self.defaults['basepath'] = "https://www.googleapis.com/youtube/v3"
        self.defaults['resource'] = '/search'
        self.defaults['params'] = {'q':'<Object ID>','part':'snippet','maxResults':'50'}

        # Standard inputs
        self.initInputs()

        # Pages Box
        self.initPagingInputs()

        # Login inputs
        self.initAuthSetupInputs()
        self.initLoginInputs(False)

        self.loadDoc()
        self.loadSettings()

    def initAuthSetupInputs(self):
        authlayout = QFormLayout()
        authlayout.setContentsMargins(0,0,0,0)
        self.authWidget.setLayout(authlayout)

        self.authTypeEdit= QComboBox()
        self.authTypeEdit.addItems(['OAuth2', 'OAuth2 External','API key'])
        authlayout.addRow("Authentication type", self.authTypeEdit)

        self.clientIdEdit = QLineEdit()
        self.clientIdEdit.setEchoMode(QLineEdit.Password)
        authlayout.addRow("Client Id", self.clientIdEdit)

        self.clientSecretEdit = QLineEdit()
        self.clientSecretEdit.setEchoMode(QLineEdit.Password)
        authlayout.addRow("Client Secret", self.clientSecretEdit)

        self.scopeEdit = QLineEdit()
        authlayout.addRow("Scopes",self.scopeEdit)

    def getUserId(self, token):
        data, headers, status = self.request(
            None, 'https://www.googleapis.com/youtube/v3/channels?mine=true&access_token='+token)

        if status != 'fetched (200)':
            return None

        return getDictValueOrNone(data,'items.0.id')

    def getSettings(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = super(YoutubeTab, self).getSettings(purpose)

        if options.get('auth_type') == 'API key':
            options['auth'] = 'param'
            options['auth_prefix'] = ''
            options['auth_tokenname'] = 'key'
        else: # OAuth2
            options['auth'] = 'header'
            options['auth_prefix'] = 'Bearer '
            options['auth_tokenname'] = 'Authorization'

        return options


# https://stackoverflow.com/questions/10123929/python-requests-fetch-a-file-from-a-local-url
class LocalFileAdapter(requests.adapters.BaseAdapter):
    """Protocol Adapter to allow Requests to GET file:// URLs

    @todo: Properly handle non-empty hostname portions.
    """

    @staticmethod
    def _chkpath(method, path):
        """Return an HTTP status for the given filesystem path."""
        if method.lower() in ('put', 'delete'):
            return 501, "Not Implemented"  # TODO
        elif method.lower() not in ('get', 'head'):
            return 405, "Method Not Allowed"
        elif os.path.isdir(path):
            return 400, "Path Not A File"
        elif not os.path.isfile(path):
            return 404, "File Not Found"
        elif not os.access(path, os.R_OK):
            return 403, "Access Denied"
        else:
            return 200, "OK"

    def send(self, req, **kwargs):  # pylint: disable=unused-argument
        """Return the file specified by the given request

        @type req: C{PreparedRequest}
        @todo: Should I bother filling `response.headers` and processing
               If-Modified-Since and friends using `os.stat`?
        """
        path = os.path.normcase(os.path.normpath(url2pathname(req.path_url)))
        response = requests.Response()

        response.status_code, response.reason = self._chkpath(req.method, path)
        if response.status_code == 200 and req.method.lower() != 'head':
            try:
                response.raw = open(path, 'rb')
                response.encoding = cchardet.detect(response.content)['encoding']
            except (OSError, IOError) as err:
                response.status_code = 500
                response.reason = str(err)

        if isinstance(req.url, bytes):
            response.url = req.url.decode('utf-8')
        else:
            response.url = req.url

        response.request = req
        response.connection = self

        return response

    def close(self):
        pass

class DataTooBigError(Exception):
    pass