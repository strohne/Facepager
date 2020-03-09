import urllib.parse
import urllib.request, urllib.parse, urllib.error

import hashlib, hmac, base64
from mimetypes import guess_all_extensions
from datetime import datetime
from copy import deepcopy
import re
import os, sys, time
import io
from collections import OrderedDict
import threading

from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile
from PySide2.QtWidgets import *
from PySide2.QtCore import QUrl

import requests
from requests.exceptions import *
from rauth import OAuth1Service
from requests_oauthlib import OAuth2Session
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
import cchardet
import json

if sys.version_info.major < 3:
    from urllib import url2pathname
else:
    from urllib.request import url2pathname

import dateutil.parser

from folder import SelectFolderDialog
from paramedit import *
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
        self.mainWindow = mainWindow
        self.name = name
        self.connected = False
        self.lastrequest = None
        self.speed = None
        self.lock_session = threading.Lock()
        self.progress = None

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
                urlparams[name] = str(value)

        # Replace placeholders in urlpath
        urlpath = self.parsePlaceholders(urlpath, nodedata, templateparams)

        return urlpath, urlparams, templateparams

    def getPayload(self,payload, params, nodedata,options):
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
            
            payload = MultipartEncoder(fields=payload)

            def callback(monitor):
                self.uploadProgress(monitor.bytes_read,monitor.len)
            payload = MultipartEncoderMonitor(payload,callback)

            return payload
        
        # Replace placeholders in string and setup progress callback
        else:   
            payload = self.parsePlaceholders(payload, nodedata, params,options)                    
            payload = BufferReader(payload,self.uploadProgress)
            return payload

    # Gets data from input fields or defaults (never gets credentials from default values!)
    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = {}

        #options for request
        try:
            options['basepath'] = self.basepathEdit.currentText().strip()
            options['resource'] = self.resourceEdit.currentText().strip()
            options['params'] = self.paramEdit.getParams()
        except AttributeError:
            pass

        #headers and verbs
        try:
            options['headers'] = self.headerEdit.getParams()
            options['verb'] = self.verbEdit.currentText().strip()            
        except AttributeError:
            pass

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
            options['paging_type'] = self.pagingTypeEdit.currentText().strip() if self.pagingTypeEdit.currentText() != "" else self.defaults.get('paging_type', '')
            options['key_paging'] = self.pagingkeyEdit.text() if self.pagingkeyEdit.text() != "" else self.defaults.get('key_paging',None)
            options['paging_stop'] = self.pagingstopEdit.text()
            options['param_paging'] = self.pagingparamEdit.text() if self.pagingparamEdit.text() != "" else self.defaults.get('param_paging',None)
            options['offset_start'] = self.offsetStartEdit.value()
            options['offset_step'] = self.offsetStepEdit.value()


        except AttributeError:
            options['paging_type'] = self.defaults.get('paging_type',None)
            options['key_paging'] = self.defaults.get('key_paging',None)
            options['paging_stop'] = ''
            options['param_paging'] = self.defaults.get('param_paging',None)
            options['offset_start'] = 1
            options['offset_step'] = 1

        #options for data handling
        try:
            options['nodedata'] = self.extractEdit.text() if self.extractEdit.text() != "" else self.defaults.get('key_objectid',None)
            options['objectid'] = self.objectidEdit.text() if self.objectidEdit.text() != "" else self.defaults.get('key_nodedata',None)
        except AttributeError:
            options['objectid'] = self.defaults.get('key_objectid',None)
            options['nodedata'] = self.defaults.get('key_nodedata',None)

        # Scopes
        try:
            options['scope'] = self.scopeEdit.text().strip()
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
            
            try:
                options['consumer_key'] = self.consumerKeyEdit.text()
            except AttributeError:
                pass            

            try:
                options['consumer_secret'] = self.consumerSecretEdit.text()
            except AttributeError:
                pass            

        return options

    # Populates input fields from loaded options, presets and default values 
    def setOptions(self, options):
        # URLs
        try:
            self.basepathEdit.setEditText(options.get('basepath', self.defaults.get('basepath','')))
            self.resourceEdit.setEditText(options.get('resource', self.defaults.get('resource','')))
            self.onChangedRelation()
            self.paramEdit.setParams(options.get('params',self.defaults.get('params','')))
        except AttributeError:
            pass

        # Header and method
        try:
            self.headerEdit.setParams(options.get('headers', {}))
            self.verbEdit.setCurrentIndex(self.verbEdit.findText(options.get('verb', 'GET')))
            self.encodingEdit.setCurrentIndex(self.encodingEdit.findText(options.get('encoding', '<None>')))
            
            if options.get('encoding', '<None>') == 'multipart/form-data':                
                self.multipartEdit.setParams(options.get('payload',{}))
            else:
                self.payloadEdit.setPlainText(options.get('payload',''))
                    
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
            self.pagingTypeEdit.setCurrentIndex(self.pagingTypeEdit.findText(options.get('paging_type', self.defaults.get('paging_type', 'key'))))
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
            self.extractEdit.setText(options.get('nodedata', ''))
            self.objectidEdit.setText(options.get('objectid', ''))
        except AttributeError:
            pass
                
        #Scope
        try:
            self.scopeEdit.setText(options.get('scope',self.defaults.get('scope','')))
        except AttributeError:
            pass
                
        # Credentials
        try:
            if 'access_token' in options:
                self.tokenEdit.setText(options.get('access_token', ''))
            if 'access_token_secret' in options:
                self.tokensecretEdit.setText(options.get('access_token_secret', ''))
            if 'client_id' in options:
                self.clientIdEdit.setText(options.get('client_id',''))
            if 'client_secret' in options:
                self.clientSecretEdit.setText(options.get('client_secret',''))
            if 'consumer_key' in options:
                self.consumerKeyEdit.setText(options.get('consumer_key', ''))
            if 'consumer_secret' in options:
                self.consumerSecretEdit.setText(options.get('consumer_secret', ''))                                
        except AttributeError:
            pass


    def saveSettings(self):
        self.mainWindow.settings.beginGroup("ApiModule_" + self.name)
        options = self.getOptions('settings')

        for key in list(options.keys()):
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

    def reloadDoc(self):
        self.saveSettings()
        self.loadDoc()
        self.loadSettings()

    def loadDoc(self):
        '''
        Loads and prepares documentation
        '''

        self.resourceEdit.clear()
        self.apidoc = self.mainWindow.apiWindow.getDocModule(self.name)

        if self.apidoc and isinstance(self.apidoc,dict):
            # Add base path
            self.basepathEdit.addItem(getDictValue(self.apidoc,"servers.url"))

            # Add endpoints in reverse order
            endpoints = self.apidoc.get("paths",{})
            paths = endpoints.keys()
            for path in reversed(list(paths)):
                operations = endpoints[path]
                path = path.replace("{", "<").replace("}", ">")

                self.resourceEdit.insertItem(0, path)
                self.resourceEdit.setItemData(0, wraptip(getDictValue(operations,"get.summary","")), Qt.ToolTipRole)

                #store params for later use in onChangedRelation
                self.resourceEdit.setItemData(0, operations, Qt.UserRole)

            self.buttonApiHelp.setVisible(True)

        self.resourceEdit.insertItem(0, "<Object ID>")



    def showDoc(self):
        '''
        Open window with documentation
        '''
        basepath = self.basepathEdit.currentText().strip()
        path = self.resourceEdit.currentText().strip()
        self.mainWindow.apiWindow.showDoc(self.name, basepath, path)

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
        self.resourceEdit.currentIndexChanged.connect(self.onChangedRelation)

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
            self.pagingStepsWidget.show()
            self.pagingKeyWidget.hide()
        else:
            self.pagingStepsWidget.hide()
            self.pagingKeyWidget.show()

        if self.pagingTypeEdit.count() < 2:
            self.pagingTypeEdit.hide()


    def initPagingInputs(self,keys = False, count = False):
        layout= QHBoxLayout()
        
        if keys or count:
            # Paging type

            self.pagingTypeEdit = QComboBox(self)

            if keys:
                self.pagingTypeEdit.addItem('key')
            if count:
                self.pagingTypeEdit.addItem('count')

            self.pagingTypeEdit.setToolTip(wraptip("Select 'key' if the response contains data about the next page, e.g. page number or offset. Select 'count' if you want to increase the paging param by a fixed amount."))
            self.pagingTypeEdit.currentIndexChanged.connect(self.pagingChanged)
            layout.addWidget(self.pagingTypeEdit)
            layout.setStretch(0, 0)

            layout.addWidget(QLabel("Param"))
            self.pagingparamEdit = QLineEdit(self)
            self.pagingparamEdit.setToolTip(wraptip("This parameter will be added to the query. The value is extracted by the paging key."))
            layout.addWidget(self.pagingparamEdit)
            layout.setStretch(1, 0)
            layout.setStretch(2, 1)

            # Paging key
            self.pagingKeyWidget = QWidget()
            self.pagingKeyLayout = QHBoxLayout()
            self.pagingKeyLayout .setContentsMargins(0, 0, 0, 0)
            self.pagingKeyWidget.setLayout(self.pagingKeyLayout)

            self.pagingKeyLayout.addWidget(QLabel("Paging key"))
            self.pagingkeyEdit = QLineEdit(self)
            self.pagingkeyEdit.setToolTip(wraptip("If the respsonse contains data about the next page, specify the key. The value will be added as paging parameter."))
            self.pagingKeyLayout.addWidget(self.pagingkeyEdit)
            self.pagingKeyLayout.setStretch(0, 0)
            self.pagingKeyLayout.setStretch(1, 1)

            layout.addWidget(self.pagingKeyWidget)
            layout.setStretch(3, 2)

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
            self.offsetStepEdit.setValue(1)
            self.offsetStepEdit.setToolTip(wraptip("Amount to increase for each page, defaults to 1"))
            self.pagingStepsLayout.addWidget(self.offsetStepEdit)
            self.pagingStepsLayout.setStretch(2, 0)
            self.pagingStepsLayout.setStretch(3, 1)

            layout.addWidget(self.pagingStepsWidget)
            layout.setStretch(4, 1)

            # Stop if
            layout.addWidget(QLabel("Stop key"))
            self.pagingstopEdit = QLineEdit(self)
            self.pagingstopEdit.setToolTip(wraptip("Stops fetching data as soon as the given key is present but empty or false. For example, stops fetching if the value of 'hasNext' ist false, none or an empty list. Usually you can leave the field blank, since fetching will stop anyway when the paging key is empty."))
            layout.addWidget(self.pagingstopEdit)
            layout.setStretch(5, 0)
            layout.setStretch(6, 1)

            #Page count
            layout.addWidget(QLabel("Maximum pages"))
            self.pagesEdit = QSpinBox(self)
            self.pagesEdit.setMinimum(1)
            self.pagesEdit.setMaximum(50000)
            self.pagesEdit.setToolTip(wraptip("Number of maximum pages."))
            layout.addWidget(self.pagesEdit)
            layout.setStretch(7, 0)
            layout.setStretch(8, 0)

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
        self.verbEdit.addItems(['GET','POST','PUT','PATCH','DELETE'])
        self.verbEdit.currentIndexChanged.connect(self.verbChanged)

        self.encodingLabel = QLabel("Encoding")
        self.encodingEdit = QComboBox(self)
        self.encodingEdit.addItems(['<None>','multipart/form-data'])
        self.encodingEdit.currentIndexChanged.connect(self.verbChanged)
        

        layout= QHBoxLayout()
        layout.addWidget(self.verbEdit)
        layout.setStretch(0, 1);
        layout.addWidget(self.encodingLabel)
        layout.addWidget(self.encodingEdit)
        layout.setStretch(2, 1);
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
        if self.verbEdit.currentText() in ['GET','DELETE']:
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

    def initResponseInputs(self):
        layout= QHBoxLayout()
        
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

    @Slot()
    def onChangedRelation(self, index = None):
        '''
        Handles the automated parameter suggestion for the current
        selected API relation/endpoint based on the OpenAPI specification 3.0.0
        '''

        if index is None:
            index = self.resourceEdit.findText(self.resourceEdit.currentText())
            if index != -1:
                self.resourceEdit.setCurrentIndex(index)

        operations = self.resourceEdit.itemData(index,Qt.UserRole)
        params = getDictValue(operations,"get.parameters",False) if operations else []
        self.paramEdit.setOpenAPIOptions(params)

    @Slot()
    def onChangedParam(self,index=0):
        pass

    def getProxies(self):
        if not hasattr(self,"proxies"):
            try:
                filename = os.path.join(os.path.expanduser("~"), 'Facepager','proxies.json')
                if os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8') as f:
                        self.proxies = json.load(f)
                else:
                    self.proxies = {}
            except Exception as e:
                self.logMessage("Error loading proxies: {}".format(str(e)))
                self.proxies = {}

        return self.proxies


    def initSession(self):
        with self.lock_session:
            if not hasattr(self, "session"):
                self.session = requests.Session()
                self.session.proxies.update(self.getProxies())
                self.session.mount('file://', LocalFileAdapter())

        return self.session

    def closeSession(self):
        with self.lock_session:
            if hasattr(self, "session"):
                del self.session


    def uploadProgress(self,current = 0, total = 0):
        if self.progress is not None:
            self.progress({'current':current,'total':total})

    def request(self, path, args=None, headers=None, method="GET", payload=None,foldername=None,
                                                      filename=None, fileext=None, format='json'):
        """
        Start a new threadsafe session and request
        """

        def download(response,foldername=None,filename=None,fileext=None):
            if foldername is not None and filename is not None:
                if fileext is None:
                    guessed_ext = guess_all_extensions(response.headers["content-type"])
                    fileext = guessed_ext[-1] if len(guessed_ext) > 0 else None

                fullfilename = makefilename(path,foldername, filename, fileext)
                file = open(fullfilename, 'wb')
            else:
                fullfilename = None
                file = None

            # requests completely downloads data to memory if not stream=True
            # iter_content, text and content all fall back to the previously downloaded content
            # no need to download into string object a second time

            # try:
            #     content = io.BytesIO()
            #     try:
            #         for chunk in response.iter_content(1024):
            #             content.write(chunk)
            #             if file is not None:
            #                 file.write(chunk)
            #
            #         out = content.getvalue().decode('utf-8')
            #     except Exception as e:
            #         out = str(e)
            #     finally:
            #         content.close()
            # finally:
            #     if file is not None:
            #         file.close()

            if file is not None:
                try:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
                finally:
                    file.close()


            return fullfilename

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
                    response = session.request(method,path, params=args,headers=headers,data=payload, timeout=self.timeout) # verify=False

                except (HTTPError, ConnectionError) as e:
                    maxretries -= 1
                    if maxretries > 0:
                        time.sleep(0.1)
                        self.logMessage("Automatic retry: Request Error: {0}".format(str(e)))
                    else:
                        raise e
                else:
                    break

        except (HTTPError, ConnectionError, InvalidURL, MissingSchema) as e:
            status = 'request error'
            data = {'error':str(e)}
            headers = {}
            return data, headers, status
            #raise Exception("Request Error: {0}".format(str(e)))

        else:
            status = 'fetched' if response.ok else 'error'
            status = status + ' (' + str(response.status_code) + ')'
            headers = dict(list(response.headers.items()))

            # Download data
            data = {
                'content-type': response.headers.get("content-type",""),
                'sourcepath': path,'sourcequery': args,'finalurl': response.url
            }

            fullfilename = download(response, foldername, filename, fileext)

            if fullfilename is not None:
                data['filename'] = os.path.basename(fullfilename)
                data['filepath'] = fullfilename

            # Text
            if format == 'text':
                    data['text'] = response.text  # str(response.text)

             # Scrape links
            elif format == 'links':
                try:
                    links, base = extractLinks(response.text, response.url)
                    data['links'] = links
                    data['base'] = base
                except Exception as  e:
                    data['error'] = 'Could not extract Links.'
                    data['message'] = str(e)
                    data['response'] = response.text

            # JSON
            elif format == 'json':
                try:
                    data = response.json() if response.text != '' else []
                except Exception as e:
                    self.logMessage("No valid JSON data, try to convert XML to JSON ("+str(e)+")")
                    try:
                        data = xmlToJson(response.text)
                    except:
                        data = {'error': 'Data could not be converted to JSON','response': response.text}

            # JSON
            elif format == 'xml':
                try:
                    data = xmlToJson(response.text)
                except:
                    data = {'error': 'Data could not be converted to JSON','response': response.text}

            return data, headers, status

    def disconnectSocket(self):
        """Used to disconnect when canceling requests"""
        self.connected = False

    @Slot()
    def editAuthSettings(self):
        dialog = QDialog(self,Qt.WindowSystemMenuHint | Qt.WindowTitleHint)
        dialog.setWindowTitle("Authentication settings")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout()
        layout.addWidget(self.authWidget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        layout.addWidget(buttons)
        dialog.setLayout(layout)

        def close():
            dialog.close()

        #connect the nested functions above to the dialog-buttons
        buttons.accepted.connect(close)
        dialog.exec_()

    @Slot()
    def showLoginWindow(self, query=False, caption='', url='',width=600,height=600):
        """
        Create a SSL-capable WebView for the login-process
        Uses a Custom QT-Webpage Implementation
        Supply a getToken-Slot to fetch the API-Token
        """

        self.doQuery = query
        self.loginWindow = QMainWindow(self.mainWindow)
        self.loginWindow.resize(width, height)
        self.loginWindow.setWindowTitle(caption)
        self.loginWindow.stopped = False


        #create WebView with Facebook log-Dialog, OpenSSL needed
        self.loginStatus = self.loginWindow.statusBar()
        self.login_webview = QWebEngineView(self.loginWindow)
        self.loginWindow.setCentralWidget(self.login_webview)

        # Use the custom- WebPage class
        webpage = QWebPageCustom(self)
        webpage.logmessage.connect(self.logMessage)
        self.login_webview.setPage(webpage)

        #Connect to the getToken-method
        self.login_webview.urlChanged.connect(self.getToken)
        webpage.urlNotFound.connect(self.getToken) #catch redirects to localhost or nonexistent uris

        # Connect to the loadFinished-Slot for an error message
        self.login_webview.loadFinished.connect(self.loadFinished)


        self.login_webview.load(QUrl(url))
        #self.login_webview.resize(window.size())
        self.login_webview.show()

        self.loginWindow.show()

    @Slot()
    def closeLoginWindow(self):
        self.loginWindow.stopped = True
        self.login_webview.stop()
        self.loginWindow.close()

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
                self.mainWindow.tree.treemodel.addNodes(newnodes)
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
                self.mainWindow.tree.treemodel.addNodes(newnodes)
                folder = os.path.dirname(dlg.selectedFiles()[0])
                self.downloadfolderEdit.setText(folder)
            else:
                folder = dlg.selectedFiles()[0]
                self.downloadfolderEdit.setText(folder)


class AuthTab(ApiTab):

    # see YoutubeTab for keys in the options-parameter
    def __init__(self, mainWindow=None, name='NoName'):
        super(AuthTab, self).__init__(mainWindow, name)

        self.defaults['login_buttoncaption'] = " Login "
        self.defaults['login_window_caption'] = "Login Page"
        self.defaults['auth_type'] = "OAuth2"

    def initAuthSetupInputs(self):
        authlayout = QFormLayout()
        authlayout.setContentsMargins(0, 0, 0, 0)
        self.authWidget.setLayout(authlayout)

        self.authTypeEdit = QComboBox()
        self.authTypeEdit.addItems(['OAuth2', 'Twitter App-only'])
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

    def initLoginInputs(self, toggle=True):
        # token and login button
        loginlayout = QHBoxLayout()

        if toggle:
            self.authEdit = QComboBox(self)
            self.authEdit.addItems(['disable', 'param', 'header'])
            self.authEdit.setToolTip(wraptip(
                "Disable: no authorization. Param: an access_token parameter containing the access token will be added to the query. Header: a bearer token header containing the access token will be sent."))
            loginlayout.addWidget(self.authEdit)

            loginlayout.addWidget(QLabel("Name"))
            self.tokenNameEdit = QLineEdit()
            self.tokenNameEdit.setToolTip(wraptip("The name of the access token parameter or the authorization header. If you leave this empty, the default value is 'access_token' for param-method and 'Authorization' for header-method. The authorization header value is automatically prefixed with 'Bearer '"))
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

    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = super(AuthTab, self).getOptions(purpose)

        # Auth type
        try:
            options['auth_type'] = self.authTypeEdit.currentText().strip() if self.authTypeEdit.currentText() != "" else self.defaults.get('auth_type', '')
        except AttributeError:
            pass

        # OAUTH URIs
        try:
            options[
                'auth_uri'] = self.authURIEdit.text().strip() if self.authURIEdit.text() != "" else self.defaults.get(
                'auth_uri', '')
            options[
                'redirect_uri'] = self.redirectURIEdit.text().strip() if self.redirectURIEdit.text() != "" else self.defaults.get(
                'redirect_uri', '')
            options[
                'token_uri'] = self.tokenURIEdit.text().strip() if self.tokenURIEdit.text() != "" else self.defaults.get(
                'token_uri', '')
        except AttributeError:
            options['auth_uri'] = self.defaults.get('auth_uri', '')
            options['redirect_uri'] = self.defaults.get('redirect_uri', '')
            options['token_uri'] = self.defaults.get('token_uri', '')

        try:
            options[
                'auth'] = self.authEdit.currentText().strip() if self.authEdit.currentText() != "" else self.defaults.get(
                'auth', 'disable')
            if self.tokenNameEdit.text() != "":
                options['auth_tokenname'] = self.tokenNameEdit.text()
            else:
                options.pop('auth_tokenname', None)

        except AttributeError:
            options.pop('auth_tokenname',None)
            options['auth'] = self.defaults.get('auth', 'disable')

        return options

    def setOptions(self, options):
        try:
            self.authTypeEdit.setCurrentIndex(
                self.authTypeEdit.findText(options.get('auth_type', self.defaults.get('auth_type', 'OAuth2'))))
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

        super(AuthTab, self).setOptions(options)

    def fetchData(self, nodedata, options=None, logData=None, logMessage=None, logProgress=None):
        self.closeSession()
        self.connected = True
        self.speed = options.get('speed', None)
        self.progress = logProgress

        # paging by auto count
        if (options.get('paging_type', 'key') == "count") and (options.get('param_paging', '') is not None):
            offset = options.get('offset_start', 1)
            options['params'][options.get('param_paging', '')] = offset

        # paging by key (continue previous fetching process based on last fetched child offcut node)
        elif (options.get('paging_type', 'key') == "key") and (options.get('key_paging') is not None) and (options.get('param_paging') is not None):
            # Get cursor of last offcut node
            offcut = getDictValueOrNone(options, 'offcutdata.response', dump=False)
            cursor = getDictValueOrNone(offcut,options.get('key_paging'))
            stopvalue = not extractValue(offcut,options.get('paging_stop'), dump = False, default = True)[1]

            # Dont't fetch if already finished (=offcut without next cursor)
            if options.get('paginate',False) and (offcut is not None) and ((cursor is None) or stopvalue):
                return False

            # Continue / start fetching
            elif (cursor is not None) :
                options['params'][options['param_paging']] = cursor


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
            if not ('url' in options):
                urlpath = options["basepath"] + options['resource']
                urlparams = {}
                urlparams.update(options['params'])

                urlpath, urlparams, templateparams = self.getURL(urlpath, urlparams, nodedata, options)

                requestheaders = options.get('headers', {})

                if options.get('auth', 'disable') == 'param':
                    urlparams[options.get('auth_tokenname','access_token')] = options['access_token']
                elif options.get('auth', 'disable') == 'header':
                    requestheaders[options.get('auth_tokenname','Authorization')] = "Bearer " + options['access_token']

                method = options.get('verb', 'GET')
                payload = self.getPayload(options.get('payload', None), templateparams, nodedata, options)
                if isinstance(payload, MultipartEncoder) or isinstance(payload, MultipartEncoderMonitor):
                    requestheaders["Content-Type"] = payload.content_type

            else:
                # requestheaders = {}
                payload = None
                urlpath = options['url']
                urlparams = options['params']

            # sign request (for Amazon tab)
            if hasattr(self, "signRequest"):
                requestheaders = self.signRequest(urlpath, urlparams, requestheaders, method, payload, options)

            if options['logrequests']:
                logMessage("Fetching data for {0} from {1}".format(nodedata['objectid'],
                                                                   urlpath + "?" + urllib.parse.urlencode(urlparams)))

            # data
            options['querytime'] = str(datetime.now())
            data, headers, status = self.request(urlpath, urlparams, requestheaders, method, payload,
                                                 foldername, filename, fileext, format=format)
            options['querystatus'] = status
            logData(data, options, headers)

            # rate limit info
            # if 'x-rate-limit-remaining' in headers:
            #     options['info'] = {'x-rate-limit-remaining': u"{} requests remaining until rate limit".format(headers['x-rate-limit-remaining'])}

            if self.progress is not None:
                self.progress({'page': page + 1})

            # Stop if result is empty
            if (options['nodedata'] is not None) and not hasValue(data,options['nodedata']):
                break

            # paging by key
            if (options.get('paging_type', 'key') == "key") and (options.get('key_paging') is not None) and (options.get('param_paging') is not None):
                cursor = getDictValueOrNone(data, options['key_paging'])
                if cursor is None:
                    break

                stopvalue = not extractValue(data, options.get('paging_stop'), dump = False, default=True)[1]
                if stopvalue:
                    break

                options['params'][options['param_paging']] = cursor

            # paging by auto count
            elif (options.get('paging_type', 'key') == "count") and (options.get('param_paging') is not None):
                offset = offset + options.get('offset_step', 1)
                options['params'][options['param_paging']] = offset
            else:
                break

            if not self.connected:
                break
        return True

    @Slot()
    def doLogin(self):
        self.closeSession()

        if hasattr(self, "authTypeEdit") and self.authTypeEdit.currentText() == 'Twitter App-only':
            self.doTwitterAppLogin()
        elif hasattr(self, "authTypeEdit") and self.authTypeEdit.currentText() == 'Twitter OAuth1':
            self.doOAuth1Login()
        else:
            self.doOAuth2Login()

    @Slot()
    def getToken(self, url=False):
        # if url is not False:
        #    self.loginStatus.showMessage(url.toDisplayString() )
        if hasattr(self, "authTypeEdit") and self.authTypeEdit.currentText() == 'Twitter App-only':
            return False
        elif hasattr(self, "authTypeEdit") and self.authTypeEdit.currentText() == 'Twitter OAuth1':
            self.getOAuth1Token()
        else:
            self.getOAuth2Token(url)

    @Slot()
    def initSession(self):
        if hasattr(self, "session"):
            return self.session

        if hasattr(self, "authTypeEdit") and self.authTypeEdit.currentText() == 'Twitter App-only':
            return self.initOAuth2Session()
        elif hasattr(self, "authTypeEdit") and self.authTypeEdit.currentText() == 'Twitter OAuth1':
            return self.initOAuth1Session()
        else:
            return self.initOAuth2Session()

    @Slot()
    def doOAuth1Login(self):
        try:
            self.oauth1service.consumer_key = self.clientIdEdit.text() if self.clientIdEdit.text() != "" else self.defaults.get(
                'consumer_key','')
            self.oauth1service.consumer_secret = self.clientSecretEdit.text() if self.clientSecretEdit.text() != "" else self.defaults.get(
                'consumer_secret','')

            if self.oauth1service.consumer_key == '':
                raise Exception('Consumer key is missing, please adjust settings!')

            if self.oauth1service.consumer_secret == '':
                raise Exception('Consumer secret is missing, please adjust settings!')

            self.oauthdata.pop('oauth_verifier', None)
            self.oauthdata['requesttoken'], self.oauthdata[
                'requesttoken_secret'] = self.oauth1service.get_request_token()

            self.showLoginWindow(False,
                                 self.defaults.get('login_window_caption', 'Login'),
                                 self.oauth1service.get_authorize_url(self.oauthdata['requesttoken']),
                                 self.defaults.get('login_window_width', 600),
                                 self.defaults.get('login_window_height', 600)
                                 )
        except Exception as e:
            QMessageBox.critical(self, "Login canceled",
                                 str(e),
                                 QMessageBox.StandardButton.Ok)

    @Slot()
    def getOAuth1Token(self):
        url = urllib.parse.parse_qs(self.login_webview.url().toString())
        if "oauth_verifier" in url:
            token = url["oauth_verifier"]
            if token:
                self.oauthdata['oauth_verifier'] = token[0]
                self.session = self.oauth1service.get_auth_session(self.oauthdata['requesttoken'],
                                                                   self.oauthdata['requesttoken_secret'], method="POST",
                                                                   data={'oauth_verifier': self.oauthdata[
                                                                       'oauth_verifier']})

                self.tokenEdit.setText(self.session.access_token)
                self.tokensecretEdit.setText(self.session.access_token_secret)

                self.closeLoginWindow()

    def initOAuth1Session(self):
        if (self.tokenEdit.text() != '') and (self.tokensecretEdit.text() != ''):
            self.oauth1service.consumer_key = self.clientIdEdit.text() if self.clientIdEdit.text() != "" else \
                self.defaults['consumer_key']
            self.oauth1service.consumer_secret = self.clientSecretEdit.text() if self.clientSecretEdit.text() != "" else \
                self.defaults['consumer_secret']
            self.oauth1service.base_url = self.basepathEdit.currentText().strip() if self.basepathEdit.currentText().strip() != "" else \
                self.defaults['basepath']

            self.session = self.oauth1service.get_session((self.tokenEdit.text(), self.tokensecretEdit.text()))
            return self.session

        else:
            raise Exception("No access, login please!")

    @Slot()
    def doOAuth2Login(self):
        try:
            options = self.getOptions()

            clientid = self.clientIdEdit.text() if self.clientIdEdit.text() != "" else self.defaults.get('client_id','')
            scope = self.scopeEdit.text() if self.scopeEdit.text() != "" else self.defaults.get('scope', None)
            loginurl = options.get('auth_uri', '')

            if loginurl == '':
                raise Exception('Login URL is missing, please adjust settings!')

            if clientid == '':
                raise Exception('Client Id is missing, please adjust settings!')

            self.session = OAuth2Session(clientid, redirect_uri=options['redirect_uri'], scope=scope)
            params = {'client_id': clientid,
                      'redirect_uri': options['redirect_uri'],
                      'response_type': options.get('response_type', 'code')}

            if scope is not None:
                params['scope'] = scope

            params = '&'.join('%s=%s' % (key, value) for key, value in iter(params.items()))
            url = loginurl + "?" + params

            self.showLoginWindow(False, self.defaults.get('login_window_caption', 'Login'),
                                 url,
                                 self.defaults.get('login_window_width', 600),
                                 self.defaults.get('login_window_height', 600)
                                 )
        except Exception as e:
            QMessageBox.critical(self, "Login canceled",
                                 str(e),
                                 QMessageBox.StandardButton.Ok)

    @Slot(QUrl)
    def getOAuth2Token(self, url):
        options = self.getOptions()

        if url.toString().startswith(options['redirect_uri']):
            try:
                clientsecret = self.clientSecretEdit.text() if self.clientSecretEdit.text() != "" else self.defaults.get(
                    'client_secret', '')

                token = self.session.fetch_token(options['token_uri'],
                                                 authorization_response=str(url.toString()),
                                                 client_secret=clientsecret)

                self.tokenEdit.setText(token['access_token'])

                try:
                    self.authEdit.setCurrentIndex(self.authEdit.findText('header'))
                except AttributeError:
                    pass

            finally:
                self.closeLoginWindow()

    def initOAuth2Session(self):
        return super(AuthTab, self).initSession()

    @Slot()
    def doTwitterAppLogin(self):
        try:
            # See https://developer.twitter.com/en/docs/basics/authentication/overview/application-only
            options = self.getOptions()

            clientid = self.clientIdEdit.text()  # if self.clientIdEdit.text() != "" else self.defaults.get('client_id','')
            if clientid == '':
                raise Exception('Client Id is missing, please adjust settings!')

            clientsecret = self.clientSecretEdit.text()  # if self.clientSecretEdit.text() != "" else self.defaults.get('client_secret', '')
            if clientsecret == '':
                raise Exception('Client Secret is missing, please adjust settings!')

            basicauth = urllib.parse.quote_plus(clientid) + ':' + urllib.parse.quote_plus(clientsecret)
            basicauth = base64.b64encode(basicauth.encode('utf-8')).decode('utf-8')

            path = 'https://api.twitter.com/oauth2/token/'
            payload = 'grant_type=client_credentials'
            headers = {'Authorization': 'Basic ' + basicauth,
                       'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}
            data, headers, status = self.request(path, payload=payload, headers=headers, method="POST")

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


class FacebookTab(AuthTab):
    def __init__(self, mainWindow=None):
        super(FacebookTab, self).__init__(mainWindow, "Facebook")

        #Defaults
        self.defaults['scope'] = '' #user_groups
        self.defaults['basepath'] = 'https://graph.facebook.com/v2.10/'
        self.defaults['resource'] = '<Object ID>'
        self.defaults['auth_uri'] = 'https://www.facebook.com/dialog/oauth'
        self.defaults['redirect_uri'] = 'https://www.facebook.com/connect/login_success.html'
        self.defaults['key_objectid'] = 'id'
        self.defaults['key_nodedata'] = 'data'
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

    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = super(FacebookTab, self).getOptions(purpose)

        if purpose != 'preset':
            options['pageid'] = self.pageIdEdit.text().strip()

        return options

    def setOptions(self, options):
        if 'pageid' in options:
            self.pageIdEdit.setText(options.get('pageid'))

        super(FacebookTab, self).setOptions(options)

    def fetchData(self, nodedata, options=None, logData=None, logMessage=None, logProgress=None):
        # Preconditions
        if options.get('access_token','') == '':
            raise Exception('Access token is missing, login please!')
        self.connected = True
        self.speed = options.get('speed',None)
        self.progress = logProgress

        # # Abort condition for time based pagination
        # since = options['params'].get('since', False)
        # if (since != False):
        #     since = dateutil.parser.parse(since, yearfirst=True, dayfirst=False)
        #     since = int((since - datetime(1970, 1, 1)).total_seconds())

        # Abort condition: maximum page count
        for page in range(options.get('currentpage', 0), options.get('pages', 1)):
            # Save page
            options['currentpage'] = page

            # build url
            if not ('url' in options):
                urlpath = options["basepath"].strip() + options['resource'].strip()
                urlparams = {}

                urlparams.update(options['params'])

                urlpath, urlparams, templateparams = self.getURL(urlpath, urlparams, nodedata,options)
                urlparams["access_token"] = options['access_token']
            else:
                urlpath = options['url']
                urlparams = options['params']

            if options['logrequests']:
                logMessage("Fetching data for {0} from {1}".format(nodedata['objectid'],
                                                                    urlpath + "?" + urllib.parse.urlencode(
                                                                                       urlparams)))

            # data
            options['querytime'] = str(datetime.now())
            data, headers, status = self.request(urlpath, urlparams)

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

            # options for data handling

            if hasDictValue(data, 'data'):
                options['nodedata'] = 'data'
            else:
                options['nodedata'] = None

            logData(data, options, headers)
            if self.progress is not None:
                self.progress({'page':page+1})

            # paging
            if hasDictValue(data, 'paging.next'):
                url, params = self.parseURL(getDictValue(data, 'paging.next', False))

                # # abort time based pagination
                # until = params.get('until', False)
                # if (since != False) and (until != False) and (int(until) < int(since)):
                #     break

                options['params'] = params
                options['url'] = url
            else:
                break

            if not self.connected:
                break


    @Slot()
    def doLogin(self, query=False, caption="Facebook Login Page",url=""):
        try:
            #use credentials from input if provided
            clientid = self.clientIdEdit.text() if self.clientIdEdit.text() != "" else self.defaults.get('client_id','')
            scope= self.scopeEdit.text() if self.scopeEdit.text() != "" else self.defaults.get('scope','')
            
            if clientid  == '':
                 raise Exception('Client ID missing, please adjust settings!')
            
            url = self.defaults['auth_uri'] +"?client_id=" + clientid + "&redirect_uri="+self.defaults['redirect_uri']+"&response_type=token&scope="+scope+"&display=popup"
    
            self.showLoginWindow(query, caption, url)
        except Exception as e:
            QMessageBox.critical(self, "Login canceled",str(e),QMessageBox.StandardButton.Ok)

    @Slot(QUrl)
    def getToken(self,url):
        if url.toString().startswith(self.defaults['redirect_uri']):
            try:
                url = urllib.parse.parse_qs(url.toString())
                token = url.get(self.defaults['redirect_uri']+"#access_token",[''])
                self.closeSession()
                self.tokenEdit.setText(token[0])

                # Get page access token
                pageid = self.pageIdEdit.text().strip()
                if  pageid != '':
                    data, headers, status = self.request(self.basepathEdit.currentText().strip()+'/'+pageid+'?fields=access_token&scope=pages_show_list&access_token='+token[0])
                    if status != 'fetched (200)':
                        raise Exception("Could not authorize for page. Check page ID in the settings.")

                    token = data['access_token']
                    self.tokenEdit.setText(token)

                else:
                    self.tokenEdit.setText(token[0])
            except Exception as e:
                QMessageBox.critical(self,"Login error",
                                     str(e),QMessageBox.StandardButton.Ok)
            self.closeLoginWindow()


class TwitterStreamingTab(ApiTab):
    def __init__(self, mainWindow=None):
        super(TwitterStreamingTab, self).__init__(mainWindow, "Twitter Streaming")

        self.defaults['access_token_url'] = 'https://api.twitter.com/oauth/access_token'
        self.defaults['authorize_url'] = 'https://api.twitter.com/oauth/authorize'
        self.defaults['request_token_url'] = 'https://api.twitter.com/oauth/request_token'
        self.defaults['basepath'] = 'https://stream.twitter.com/1.1/'
        self.defaults['resource'] = 'statuses/filter'
        self.defaults['params'] = {'track': '<Object ID>'}        
        self.defaults['key_objectid'] = 'id'
        self.defaults['key_nodedata'] = None
        
        # Query Box
        self.initInputs()
        self.initAuthSettingsInputs()
        self.initLoginInputs()

        self.loadDoc()
        self.loadSettings()

        # Twitter OAUTH consumer key and secret should be defined in credentials.py
        self.oauthdata = {}
        self.twitter = OAuth1Service(
            consumer_key=self.defaults.get('consumer_key'),
            consumer_secret=self.defaults.get('consumer_secret'),
            name='twitterstreaming',
            access_token_url=self.defaults.get('access_token_url'),
            authorize_url=self.defaults.get('authorize_url'),
            request_token_url=self.defaults.get('request_token_url'),
            base_url=self.defaults.get('basepath'))
        self.timeout = 60
        self.connected = False

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


    def initAuthSettingsInputs(self):
        authlayout = QFormLayout()
        authlayout.setContentsMargins(0,0,0,0)
        self.authWidget.setLayout(authlayout)

        self.consumerKeyEdit = QLineEdit()
        self.consumerKeyEdit.setEchoMode(QLineEdit.Password)
        authlayout.addRow("Consumer Key", self.consumerKeyEdit)

        self.consumerSecretEdit = QLineEdit()
        self.consumerSecretEdit.setEchoMode(QLineEdit.Password)
        authlayout.addRow("Consumer Secret",self.consumerSecretEdit)

    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = super(TwitterStreamingTab, self).getOptions(purpose)

        # options for data handling
        if purpose == 'fetch':            
            if options["resource"] == 'search/tweets':
                options['nodedata'] = 'statuses'
            elif options["resource"] == 'followers/list':
                options['nodedata'] = 'users'
            elif options["resource"] == 'friends/list':
                options['nodedata'] = 'users'
            else:
                options['nodedata'] = None

        return options
    
    def initSession(self):
        if hasattr(self, "session"):
            return self.session

        elif (self.tokenEdit.text() != '') and (self.tokensecretEdit.text() != ''):
            self.twitter.consumer_key = self.consumerKeyEdit.text() if self.consumerKeyEdit.text() != "" else self.defaults['consumer_key']
            self.twitter.consumer_secret = self.consumerSecretEdit.text() if self.consumerSecretEdit.text() != "" else self.defaults['consumer_secret']
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
                                                         stream=True)
                        else:
                            response = self.session.get(path, params=args, timeout=self.timeout,
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
                        print("good response")
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

    def fetchData(self, nodedata, options=None, logData=None, logMessage=None, logProgress=None):
        if not ('url' in options):
            urlpath = options["basepath"] + options["resource"] + ".json"
            urlpath, urlparams, templateparams = self.getURL(urlpath, options["params"], nodedata,options)
        else:
            urlpath = options['url']
            urlparams = options["params"]

        if options['logrequests']:
            logMessage("Fetching data for {0} from {1}".format(nodedata['objectid'], urlpath + "?" + urllib.parse.urlencode(urlparams)))

        # data
        headers = None
        for data in self.request(path=urlpath, args=urlparams):
            # data
            options['querytime'] = str(datetime.now())
            options['querystatus'] = 'stream'

            logData(data, options, headers)


    @Slot()
    def doLogin(self, query=False, caption="Twitter Login Page", url=""):
        try:
            self.twitter.consumer_key = self.consumerKeyEdit.text() if self.consumerKeyEdit.text() != "" else self.defaults.get('consumer_key','')
            self.twitter.consumer_secret = self.consumerSecretEdit.text() if self.consumerSecretEdit.text() != "" else self.defaults.get('consumer_secret','')
            if self.twitter.consumer_key  == '' or self.twitter.consumer_secret == '':
                 raise Exception('Consumer key or consumer secret is missing, please adjust settings!')
                
            self.oauthdata.pop('oauth_verifier', None)
            self.oauthdata['requesttoken'], self.oauthdata['requesttoken_secret'] = self.twitter.get_request_token()
    
            self.showLoginWindow(query, caption,self.twitter.get_authorize_url(self.oauthdata['requesttoken']))
        except Exception as e:
            QMessageBox.critical(self, "Login canceled",
                                            str(e),
                                            QMessageBox.StandardButton.Ok)

    @Slot()
    def getToken(self):
        url = urllib.parse.parse_qs(self.login_webview.url().toString())
        if 'oauth_verifier' in url:
            token = url['oauth_verifier']
            if token:
                self.oauthdata['oauth_verifier'] = token[0]
                self.session = self.twitter.get_auth_session(self.oauthdata['requesttoken'],
                                                             self.oauthdata['requesttoken_secret'], method='POST',
                                                             data={'oauth_verifier': self.oauthdata['oauth_verifier']})

                self.tokenEdit.setText(self.session.access_token)
                self.tokensecretEdit.setText(self.session.access_token_secret)

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
        self.initResponseInputs()

        # Pages Box
        self.initPagingInputs(True, True)

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

    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = super(AmazonTab, self).getOptions(purpose)

        options['format'] = self.defaults.get('format', '')
        options['service'] = self.serviceEdit.text().strip() if self.serviceEdit.text() != "" else self.defaults.get('service', '')
        options['region'] = self.regionEdit.text().strip() if self.regionEdit.text() != "" else self.defaults.get(
            'region', '')

        if purpose != 'preset':
            options['secretkey'] = self.secretkeyEdit.text().strip() #if self.secretkeyEdit.text() != "" else self.defaults.get('auth_uri', '')
            options['accesskey'] = self.accesskeyEdit.text().strip() #if self.accesskeyEdit.text() != "" else self.defaults.get('redirect_uri', '')

        return options

    def setOptions(self, options):
        if 'secretkey' in options:
            self.secretkeyEdit.setText(options.get('secretkey'))

        if 'accesskey' in options:
            self.accesskeyEdit.setText(options.get('accesskey'))

        self.serviceEdit.setText(options.get('service'))
        self.regionEdit.setText(options.get('region'))

        super(AmazonTab, self).setOptions(options)


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

        # Defaults
        self.defaults['basepath'] = 'https://api.twitter.com/1.1/'
        self.defaults['resource'] = 'search/tweets'
        self.defaults['params'] = {'q': '<Object ID>'}
        self.defaults['key_objectid'] = 'id'
        self.defaults['key_nodedata'] = None

        self.defaults['auth_type'] = 'Twitter OAuth1'
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

        # Twitter OAUTH consumer key and secret should be defined in credentials.py
        self.oauthdata = {}
        self.oauth1service = OAuth1Service(
            consumer_key=self.defaults.get('consumer_key'),
            consumer_secret=self.defaults.get('consumer_secret'),
            name='oauth1',
            access_token_url=self.defaults.get('access_token_url'),
            authorize_url=self.defaults.get('authorize_url'),
            request_token_url=self.defaults.get('request_token_url'),
            base_url=self.defaults.get('basepath'))

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
        self.authTypeEdit.addItems(['Twitter OAuth1', 'Twitter App-only'])
        authlayout.addRow("Authentication type", self.authTypeEdit)

        self.clientIdEdit = QLineEdit()
        self.clientIdEdit.setEchoMode(QLineEdit.Password)
        authlayout.addRow("Consumer Key", self.clientIdEdit)

        self.clientSecretEdit = QLineEdit()
        self.clientSecretEdit.setEchoMode(QLineEdit.Password)
        authlayout.addRow("Consumer Secret", self.clientSecretEdit)

    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'

        options = super(TwitterTab, self).getOptions(purpose)

        # options for data handling
        if purpose == 'fetch':
            doc = 'paths.' + options.get('resource','') + '.get.responses.200.content.application/json.schema.x-facepager-extract'
            nodedata = getDictValue(self.apidoc,doc,dump=False)
            options['nodedata'] = nodedata if nodedata != '' else None

        return options

    def fetchData(self, nodedata, options=None, logData=None, logMessage=None, logProgress=None):
        self.connected = True
        self.speed = options.get('speed', None)
        self.progress = logProgress

        for page in range(options.get('currentpage', 0), options.get('pages', 1)):
            # Save page
            options = deepcopy(options)
            options['currentpage'] = page

            # Build URL
            if not ('url' in options):
                urlpath = options["basepath"] + options["resource"] + ".json"
                urlpath, urlparams, templateparams = self.getURL(urlpath, options["params"], nodedata, options)
            else:
                urlpath = options['url']
                urlparams = options["params"]

            if options['logrequests']:
                logMessage("Fetching data for {0} from {1}".format(nodedata['objectid'],
                                                                    urlpath + "?" + urllib.parse.urlencode(
                                                                        urlparams)))
            # App auth
            requestheaders = options.get('headers', {})
            if options.get('auth_type','Twitter OAuth1') == 'Twitter App-only':
                requestheaders["Authorization"] = "Bearer "+options['access_token']

            # data
            data, headers, status = self.request(urlpath, urlparams, requestheaders)
            options['querytime'] = str(datetime.now())
            options['querystatus'] = status

            # rate limit info
            if 'x-rate-limit-remaining' in headers:
                options['info'] = {'x-rate-limit-remaining': "{} requests remaining until rate limit".format(
                    headers['x-rate-limit-remaining'])}

            options['ratelimit'] = (status == "error (429)")

            if hasDictValue(data,'results'):
                options['nodedata'] = 'results'
            #else:
            #    options['nodedata'] = None

            logData(data, options, headers)
            if self.progress is not None:
                self.progress({'page': page + 1})

            paging = False
            if isinstance(data, dict) and hasDictValue(data, "next_cursor_str") and (data["next_cursor_str"] != "0"):
                paging = True
                options['params']['cursor'] = data["next_cursor_str"]

            # paging with next-results; Note: Do not rely on the search_metadata information, sometimes the next_results param is missing, this is a known bug
            elif isinstance(data, dict) and hasDictValue(data, "search_metadata.next_results"):
                paging = True
                url, params = self.parseURL(getDictValue(data, "search_metadata.next_results", False))
                options['url'] = urlpath
                options['params'] = params

                # Workaround for Twitter bug (carry on tweet_mode=extended)
                if 'tweet_mode' in urlparams:
                    options['params']['tweet_mode'] = urlparams['tweet_mode']

            # manual paging with max-id
            # if there are still statuses in the response, use the last ID-1 for further pagination
            #elif isinstance(data, list) and (len(data) >= int(urlparams.get('count',1))):
            elif isinstance(data, list) and (len(data) > 0):
                options['params']['max_id'] = int(data[-1]["id"]) - 1
                paging = True

            if not paging:
                break

            if not self.connected:
                break

class YoutubeTab(AuthTab):
    def __init__(self, mainWindow=None):

        super(YoutubeTab, self).__init__(mainWindow, "YouTube")

        # Defaults
        self.defaults['auth_uri'] = 'https://accounts.google.com/o/oauth2/auth'
        self.defaults['token_uri'] = "https://accounts.google.com/o/oauth2/token"
        self.defaults['redirect_uri'] = 'https://localhost' #"urn:ietf:wg:oauth:2.0:oob" #, "http://localhost"
        self.defaults['scope'] = "https://www.googleapis.com/auth/youtube.readonly" #,"https://www.googleapis.com/auth/youtube.force-ssl"
        self.defaults['response_type'] = "code"

        self.defaults['login_buttoncaption'] = " Login to Google "
        self.defaults['login_window_caption'] = "YouTube Login Page"

        self.defaults['key_objectid'] = 'id.videoId'
        self.defaults['key_nodedata'] = 'items'
        self.defaults['paging_type'] = "key"
        self.defaults['key_paging'] = "nextPageToken"
        self.defaults['param_paging'] = 'pageToken'

        self.defaults['auth'] = 'param'
        self.defaults['basepath'] = "https://www.googleapis.com/youtube/v3/"
        self.defaults['resource'] = 'search'
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
        self.authTypeEdit.addItems(['OAuth2', 'API key'])
        authlayout.addRow("Authentication type", self.authTypeEdit)

        self.clientIdEdit = QLineEdit()
        self.clientIdEdit.setEchoMode(QLineEdit.Password)
        authlayout.addRow("Client Id", self.clientIdEdit)

        self.clientSecretEdit = QLineEdit()
        self.clientSecretEdit.setEchoMode(QLineEdit.Password)
        authlayout.addRow("Client Secret", self.clientSecretEdit)

        self.scopeEdit = QLineEdit()
        authlayout.addRow("Scopes",self.scopeEdit)

    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = super(YoutubeTab, self).getOptions(purpose)

        if options.get('auth_type','OAuth2') == 'API key':
            options['auth_tokenname'] = 'key'

        return options

    @Slot()
    def doLogin(self):
        if hasattr(self, "authTypeEdit") and self.authTypeEdit.currentText() == 'API key':
            QMessageBox.information(self, "Facepager", "Manually enter your API key into the access token field or switch to OAuth2")
        else:
            super(YoutubeTab, self).doLogin()

class GenericTab(AuthTab):
    def __init__(self, mainWindow=None):
        super(GenericTab, self).__init__(mainWindow, "Generic")

        # Standard inputs
        self.initInputs()

        # Header, Verbs
        self.initHeaderInputs()
        self.initVerbInputs()
        self.initUploadFolderInput()

        # Extract input
        self.initPagingInputs(True, True)
        self.initResponseInputs()

        self.initFileInputs()

        # Login inputs
        self.initAuthSetupInputs()
        self.initLoginInputs()

        self.loadDoc()
        self.loadSettings()
        self.timeout = 30

    def initResponseInputs(self):
        layout = QHBoxLayout()

        #Format
        self.formatEdit = QComboBox(self)
        self.formatEdit.addItems(['json','text','links','file'])
        self.formatEdit.setToolTip("<p>JSON: default option, data will be parsed as JSON or converted from XML to JSON. </p> \
                                    <p>Text: data will not be parsed and embedded in JSON. </p> \
                                    <p>Links: data will be parsed as xml and links will be extracted (set key to extract to 'links' and key for Object ID to 'url'). </p> \
                                    <p>File: data will only be downloaded to files, specify download folder and filename.</p>")
        layout.addWidget(self.formatEdit)
        layout.setStretch(0, 0)
        #self.formatEdit.currentIndexChanged.connect(self.formatChanged)

        # Extract
        layout.addWidget(QLabel("Key to extract"))
        self.extractEdit = QLineEdit(self)
        self.extractEdit.setToolTip(wraptip("If your data contains a list of objects, set the key of the list. Every list element will be adeded as a single node. Remaining data will be added as offcut node."))
        layout.addWidget(self.extractEdit)
        layout.setStretch(1, 0)
        layout.setStretch(2, 2)

        layout.addWidget(QLabel("Key for Object ID"))
        self.objectidEdit = QLineEdit(self)
        self.objectidEdit.setToolTip(wraptip("If your data contains unique IDs for every node, define the corresponding key."))
        layout.addWidget(self.objectidEdit)
        layout.setStretch(3, 0)
        layout.setStretch(4, 2)

        # Add layout
        self.extraLayout.addRow("Response", layout)


    def getOptions(self, purpose='fetch'):  # purpose = 'fetch'|'settings'|'preset'
        options = super(GenericTab, self).getOptions(purpose)

        if purpose != 'preset':
            options['querytype'] = self.name + ':'+options['basepath']+options['resource']

        return options

class QWebPageCustom(QWebEnginePage):
    logmessage = Signal(str)
    urlNotFound = Signal(QUrl)

    def __init__(self, parent):
        #super(QWebPageCustom, self).__init__(*args, **kwargs)
        super(QWebPageCustom, self).__init__(parent)

        profile = self.profile()
        profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
        profile.clearHttpCache()

        cookies = profile.cookieStore()
        profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        cookies.deleteAllCookies()

    def supportsExtension(self, extension):
        if extension == QWebEnginePage.ErrorPageExtension:
            return True
        else:
            return False

    def extension(self, extension, option=0, output=0):
        if extension != QWebEnginePage.ErrorPageExtension: return False

        if option.domain == QWebEnginePage.QtNetwork:
            #msg = "Network error (" + str(option.error) + "): " + option.errorString
            #self.logmessage.emit(msg)
            self.urlNotFound.emit(option.url)

        elif option.domain == QWebEnginePage.Http:
            msg = "HTTP error (" + str(option.error) + "): " + option.errorString
            self.logmessage.emit(msg)

        elif option.domain == QWebEnginePage.WebKit:
            msg = "WebKit error (" + str(option.error) + "): " + option.errorString
            self.logmessage.emit(msg)
        else:
            msg = option.errorString
            self.logmessage.emit(msg)

        return True

    # def onSslErrors(self, reply, errors):
    #     url = str(reply.url().toString())
    #     reply.ignoreSslErrors()
    #     self.logmessage.emit("SSL certificate error ignored: %s (Warning: Your connection might be insecure!)" % url)


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