from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

import os
import shutil
from tempfile import TemporaryDirectory
import sys
import re
import json
from widgets.textviewer import *
from urllib.parse import urlparse
import requests
import threading
import webbrowser
import platform
from utilities import *
from widgets.progressbar import ProgressBar

class ApiViewer(QDialog):
    logmessage = Signal(str)

    def __init__(self, parent=None):
        super(ApiViewer,self).__init__(parent)

        # Main window
        self.mainWindow = parent
        self.setWindowTitle("API Viewer")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        # Properties
        self.folder = os.path.join(os.path.expanduser("~"), 'Facepager', 'APIs')
        self.folderDefault = os.path.join(os.path.expanduser("~"), 'Facepager', 'DefaultAPIs')
        self.filesSuffix = ['.oa3.json']
        self.lastSelected = None

        # Hold the list of loaded ApiDocs,
        # indexed by filename
        self.apis = {}

        # List of top nodes in the view,
        # indexed by filename
        # deprecated: use self.apis instead
        self.topNodes= {}

        self.detailTables = {}
        self.detailWidgets = {}

        self.allFilesLoaded = False
        self.filesDownloaded = False

        #layout
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        #loading indicator
        self.loadingLock = threading.Lock()
        self.loadingIndicator = QLabel('Loading...please wait a second.')
        self.loadingIndicator.hide()
        layout.addWidget(self.loadingIndicator)

        #Middle
        central = QSplitter(self)
        layout.addWidget(central,1)

        #list view
        self.itemList = QTreeWidget(self)
        self.itemList.setHeaderHidden(True)
        self.itemList.setColumnCount(1)
        self.itemList.setIndentation(15)
        self.itemList.itemSelectionChanged.connect(self.currentChanged)
        central.addWidget(self.itemList)
        central.setStretchFactor(0, 0)

        #detail view
        self.detailView=QScrollArea()
        self.detailView.setWidgetResizable(True)
        self.detailWidget = QWidget()
        self.detailWidget.setAutoFillBackground(True)
        self.detailWidget.setStyleSheet("background-color: rgb(255,255,255);")

        self.detailLayout=QVBoxLayout()
        self.detailWidget.setLayout(self.detailLayout)
        self.detailView.setWidget(self.detailWidget)

        central.addWidget(self.detailView)
        central.setStretchFactor(1, 2)

        self.detailName = QLabel('')
        self.detailName.setWordWrap(True)
        self.detailName.setStyleSheet("QLabel  {font-size:15pt;font-weight:bold;}")
        self.detailLayout.addWidget(self.detailName)

        self.detailDescription = TextViewer()
        #self.detailDescription .setStyleSheet("QTextViewer  {padding-left:0px;}")
        self.detailLayout.addWidget(self.detailDescription)

        self.detailLayout.addStretch(100)
        #buttons
        buttons= QHBoxLayout() #QDialogButtonBox()
        
        self.folderButton = QPushButton("")
        self.folderButton.setFlat(True)
        self.folderButton.setText(self.folder)
        self.folderButton.clicked.connect(self.folderClicked)
        buttons.addWidget(self.folderButton)

        buttons.addStretch()

        self.reloadButton=QPushButton('Reload')
        self.reloadButton.clicked.connect(self.reloadDocs)
        self.reloadButton.setToolTip("Reload all API files.")
        buttons.addWidget(self.reloadButton)

        self.rejectButton=QPushButton('Close')
        self.rejectButton.clicked.connect(self.close)
        self.rejectButton.setToolTip("Close the window")
        buttons.addWidget(self.rejectButton)

        self.applyButton=QPushButton('Apply')
        self.applyButton.setDefault(True)
        self.applyButton.clicked.connect(self.applyItem)
        self.applyButton.setToolTip("Apply the selected path.")
        buttons.addWidget(self.applyButton)
        layout.addLayout(buttons)

        #status bar
        #self.statusbar = QStatusBar()
        #self.statusbar.insertWidget(0,self.folderButton)
        #layout.addWidget(self.statusbar)



    def folderClicked(self):
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

        if platform.system() == "Windows":
            webbrowser.open(self.folder)
        elif platform.system() == "Darwin":
            webbrowser.open('file:///' + self.folder)
        else:
            webbrowser.open('file:///' + self.folder)

    def reloadDocs(self):
        self.filesDownloaded = False
        self.downloadDefaultFiles()

        self.clear()
        self.topNodes = {}
        self.apis = {}
        self.initDocs()

        for i in range(0, self.mainWindow.RequestTabs.count()):
            tab = self.mainWindow.RequestTabs.widget(i)
            tab.reloadDoc()

    def showWindow(self):
        self.show()
        QApplication.processEvents()

        # Load files
        self.initDocs()

        # Select item
        if (self.lastSelected is None) or (self.lastSelected not in self.topNodes):
            selected = self.itemList.topLevelItem(0)
        else:
            selected = self.topNodes.get(self.lastSelected)
        self.itemList.setCurrentItem(selected)
        self.itemList.setFocus()

        #self.applyButton.setDefault(True)
        self.raise_()

    def showDoc(self, module, basepath, path, field = None):
        # Show
        self.show()
        QApplication.processEvents()
        self.initDocs()

        # Find file / module / api
        selectedItem = self.getApiNode(module, basepath, path)
        self.itemList.setCurrentItem(selectedItem)
        self.itemList.setFocus()

        # Focus field
        if field is not None:
            params = self.detailWidgets.get('Response',{})

            while (not field in params) and (field != ''):
                field = field.rsplit('.', 1)
                field = field[0] if len(field) > 1 else ''

            if field in params:
                valuewidget = params.get(field)
                valuewidget.setStyleSheet("border: 2px solid blue;font-weight:bold;")
                self.detailView.ensureWidgetVisible(valuewidget)

        #self.exec_()

    def addDetailTable(self, caption):
        detailForm=QFormLayout()
        detailForm.setRowWrapPolicy(QFormLayout.DontWrapRows);
        detailForm.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow);
        detailForm.setFormAlignment(Qt.AlignLeft | Qt.AlignTop);
        detailForm.setLabelAlignment(Qt.AlignLeft);
        self.detailLayout.insertLayout(self.detailLayout.count()-1, detailForm,1)
        self.detailTables[caption] = detailForm

        caption = QLabel(caption)
        caption.setWordWrap(True)
        caption.setStyleSheet("QLabel  {font-size:12pt;margin-top:1em;margin-bottom:0.5em;font-weight:bold;}")
        detailForm.addRow(caption)

    def addDetailText(self,value):
        detailCaption, detailForm = list(self.detailTables.items())[-1]

        caption = QLabel(value)
        caption.setStyleSheet("QLabel  {padding-left:0.4em;}")
        caption.setWordWrap(True)
        detailForm.addRow(caption)


    def addDetailRow(self,name,value):
        detailCaption, detailForm = list(self.detailTables.items())[-1]

        nameWidget =  QLabel(name)
        nameWidget.setWordWrap(True)
        nameWidget.setStyleSheet("QLabel  {padding-left:0.4em;}")

        valueWidget = TextViewer()
        valueWidget.setText(value)
        detailForm.addRow(nameWidget,valueWidget)

        if not detailCaption in self.detailWidgets:
            self.detailWidgets[detailCaption] = {}
        self.detailWidgets[detailCaption][name] = nameWidget

    def currentChanged(self):
        self.clearDetails()

        current = self.itemList.currentItem()
        if current and current.isSelected():
            data = current.data(0,Qt.UserRole)
            self.lastSelected = os.path.join(data.get('folder',''),data.get('filename',''))

            # Caption
            if data.get('type', '') == 'file':
                title = getDictValue(data, 'info.title')
                self.detailName.setText(title)

                # Description
                self.detailDescription.setText(getDictValue(data,'info.description'))

                # Info
                self.addDetailTable('Paths')
                self.addDetailRow('Documentation: ',getDictValue(data, 'info.externalDocs.url'))
                self.addDetailRow('Base path: ', getDictValue(data, 'info.servers.0.url'))

            elif data.get('type', '') == 'path':
                title = getDictValue(data, 'info.title') + " " + data['path']
                self.detailName.setText(title)

                operation = getDictValue(data, 'operations.get', False)
                if operation:
                    # Description
                    self.detailDescription.setText(getDictValue(operation, 'summary'))

                    # Info
                    self.addDetailTable('Paths')
                    self.addDetailRow('Documentation: ', getDictValue(operation, 'externalDocs.url'))
                    self.addDetailRow('Base path: ', getDictValue(data, 'info.servers.0.url'))
                    self.addDetailRow('Resource path: ', getDictValue(data, 'path'))

                    # Parameters
                    params = operation.get('parameters',{})
                    if params:
                        self.addDetailTable('Parameters')
                        for param in params:
                            paramname = param.get('name')
                            if param.get('in','query') == 'path':
                                paramname = '<'+paramname+'>'

                            # Description
                            description = param.get('description')

                            # Options
                            schema = param.get('schema',{})
                            items = schema.get('items', {}) if schema.get('type') == 'array' else schema
                            enum = items.get('enum', [])
                            oneof = [value.get('const', '') for value in  items.get('oneOf', [])]
                            bool = ['0','1'] if items.get('type') == 'boolean' else []
                            options = ",".join(enum+oneof+bool)
                            if options != '':
                                description += "\n\nOptions: "+options

                            self.addDetailRow(paramname, description)

                    # Response
                    self.addDetailTable('Response')
                    self.addDetailText(getDictValue(operation, 'responses.200.description', ''))


                    def addDetailProperties(schema, key = ''):
                        if not isinstance(schema, dict):
                            return False

                        if schema.get('type', None) == 'object':
                            properties = schema.get('properties',None)
                            if isinstance(properties, dict):
                                ref = properties.get("$ref",None)
                                if ref is not None:
                                    properties = self.getSchemaComponent(data, ref)

                            if isinstance(properties, dict):
                                for name, value in properties.items():
                                    if not isinstance(value,dict):
                                        return False

                                    self.addDetailRow(key + name, value.get('description', ''))
                                    if value.get("type",None) == "object":
                                        addDetailProperties(value,key+name+".")
                                    elif value.get("type",None) == "array":
                                        addDetailProperties(value,key+name+".")

                        elif schema.get('type', None) == 'array':
                            items = schema.get('items',{})
                            addDetailProperties(items, key+'*.')


                    schema = getDictValue(operation, 'responses.200.content.application/json.schema', None)
                    addDetailProperties(schema)


            self.detailWidget.show()

    def clearDetails(self):
        self.detailWidget.hide()

        self.detailName.setText("")
        self.detailDescription.setText("")

        for detailCaption,detailForm in self.detailTables.items():
            while detailForm.rowCount() > 0:
               detailForm.removeRow(0)
            self.detailLayout.removeItem(detailForm)

        self.detailTables = {}
        self.detailWidgets = {}

    def clear(self):
        self.allFilesLoaded=False
        self.itemList.clear()
        self.clearDetails()

    def checkDefaultFiles(self):
        if not os.path.exists(self.folderDefault):
            self.reloadDocs()
        elif len(os.listdir(self.folderDefault)) == 0:
            self.reloadDocs()

    def downloadDefaultFiles(self,silent=False):
        with self.loadingLock:
            if self.filesDownloaded:
                return False

            # Progress
            progress = ProgressBar("Downloading default API definitions from GitHub...", self) if not silent else None
            QApplication.processEvents()

            # Create temporary download folder
            tmp = TemporaryDirectory(suffix='FacepagerDefaultAPIs')
            try:
                 #Download
                files = requests.get("https://api.github.com/repos/strohne/Facepager/contents/apis").json()
                files = [f['path'] for f in files if f['path'].endswith(tuple(self.filesSuffix))]
                if progress is not None:
                    progress.setMaximum(len(files))
                for filename in files:
                    response = requests.get("https://raw.githubusercontent.com/strohne/Facepager/master/"+filename)
                    if response.status_code != 200:
                        raise(f"GitHub is not available (status code {response.status_code})")
                    with open(os.path.join(tmp.name, os.path.basename(filename)), 'wb') as f:
                        f.write(response.content)
                    if progress is not None:
                        progress.step()

                    # Create folder
                if not os.path.exists(self.folderDefault):
                    os.makedirs(self.folderDefault)

                     # Clear folder
                for filename in os.listdir(self.folderDefault):
                    os.remove(os.path.join(self.folderDefault, filename))

                 # Move files from tempfolder
                for filename in os.listdir(tmp.name):
                    shutil.move(os.path.join(tmp.name, filename), self.folderDefault)

                self.logmessage.emit("Default API definitions downloaded from GitHub.")
            except Exception as e:
                if not silent:
                    QMessageBox.information(self,"Facepager","Error downloading default API definitions:"+str(e))

                self.logmessage.emit("Error downloading default API definitions:"+str(e))

                return False
            else:
                self.filesDownloaded = True
                return True
            finally:
                tmp.cleanup()
                if progress is not None:
                    progress.close()

    def initDocs(self):
        if self.allFilesLoaded:
            return False

        self.loadingIndicator.show()
        QApplication.processEvents()

        try:
            #self.downloadDefaultFiles()
            if os.path.exists(self.folderDefault):
                files = [f for f in os.listdir(self.folderDefault) if f.endswith(tuple(self.filesSuffix))]
                for filename in files:
                    self.loadFile(self.folderDefault, filename, True)

            if os.path.exists(self.folder):
                files = [f for f in os.listdir(self.folder) if f.endswith(tuple(self.filesSuffix))]
                for filename in files:
                    self.loadFile(self.folder, filename)

            self.itemList.sortItems(0, Qt.AscendingOrder)
            self.allFilesLoaded = True
        except:
            self.loadingIndicator.hide()
            return False
        finally:
            self.loadingIndicator.hide()
            return True


    def loadFiles(self,folder, module, default=False):
        # self.downloadDefaultFiles(True)

        # Create folders
        if not os.path.exists(folder):
            os.makedirs(folder)

        module = module.replace(" ", "")
        for filename in os.listdir(folder):
            if filename.startswith(module) and filename.endswith(self.filesSuffix[0]):
                self.loadFile(folder, filename, default)

    def loadFile(self, folder, filename, default=False):
        if os.path.join(folder, filename) in self.topNodes:
            return self.topNodes[os.path.join(folder, filename)]

        if not os.path.isfile(os.path.join(folder, filename)):
            return None

        try:
            with open(os.path.join(folder, filename), 'r',encoding="utf-8") as input:
                data = json.load(input)

            if not isinstance(data,dict):
                return None

            data['x-facepager-default'] = default
            self.apis[os.path.join(folder, filename)] = data

            # Prepare node
            itemData = {}
            itemData = {k:v for (k,v) in data.items() if k.startswith('x-facepager-')}
            itemData['type'] = 'file'
            itemData['filename'] = filename
            itemData['folder'] = folder
            itemData['default'] = default

            itemData['info'] = data.get('info',{})
            itemData['info']['externalDocs'] = data.get('externalDocs',{})
            itemData['info']['servers'] = data.get('servers', [])
            itemData['module'] = data.get("x-facepager-module", "Generic")

            # Root node in the view
            if default:
                itemData['caption'] = itemData['info'].get('title', '') +" *"
            else:
                itemData['caption'] = itemData['info'].get('title', '')

            topItem = ApiWidgetItem()
            topItem.setText(0,itemData['caption'])
            ft = topItem.font(0)
            ft.setWeight(QFont.Bold)
            topItem.setFont(0,ft)
            if default:
                topItem.setForeground(0, QBrush(QColor("darkblue")))

            topItem.setData(0,Qt.UserRole,itemData)
            self.itemList.addTopLevelItem(topItem)
            self.topNodes[os.path.join(folder, filename)] = topItem

            # Path nodes
            for path,operations in data.get('paths',{}).items():
                path = path.replace("{", "<").replace("}", ">")
                pathItemData = itemData.copy()
                pathItemData['type'] = 'path'
                pathItemData['caption'] = path
                pathItemData['path'] = path
                pathItemData['operations'] = operations
                pathItemData['components'] = data.get('components',{})


                newItem = ApiWidgetItem()
                newItem.setText(0,path)
                newItem.setData(0,Qt.UserRole, pathItemData)

                topItem.addChild(newItem)
                QApplication.processEvents()

            return topItem

        except Exception as e:
             QMessageBox.information(self,"Facepager","Error loading items:"+str(e))
             return None

    def getApiBasePaths(self, module):
        urls = []
        try:
            # Load files
            self.loadFiles(self.folder, module)
            self.loadFiles(self.folderDefault, module)

            # Extract urls
            for k,v in self.apis.items():
                api_module = getDictValue(v,'x-facepager-module','Generic')
                if (api_module == module):
                    api_urls = getDictValue(v, 'servers.*.url', [])
                    urls.extend(api_urls)
                    urls= list(set(urls))

        except Exception as e:
            self.logmessage(f"Error loading base paths: {str(e)}")

        return urls

    def getApiDoc(self, module, basepath = ''):
        try:
            # Documentation
            self.loadFiles(self.folder, module)
            self.loadFiles(self.folderDefault, module, True)

            # Get best match based on module and basepath
            api = None
            for k,v in self.apis.items():
                api_module = getDictValue(v,'x-facepager-module','Generic')
                api_urls = getDictValue(v,'servers.*.url',[])
                api_default = getDictValue(v,'x-facepager-default',False)

                # Prio 1: user defined docs matching module and basepath
                if (api_module == module) and (basepath in api_urls) and (not api_default):
                    api = v
                    break

                # Prio 2: default docs matching module and basepath
                elif (api_module == module) and (basepath in api_urls):
                    api = v

                # Prio 3: docs matching module
                elif (api_module == module):
                    api = v if api is None else api

            return api
        except:
            return None

    def getApiNode(self, module, basepath, path):
        node = None
        for idx_file in range(self.itemList.topLevelItemCount()):
            topItem = self.itemList.topLevelItem(idx_file)
            topData = topItem.data(0, Qt.UserRole)

            # Find path
            # TODO: prioritize non default apis
            # TODO: fuzzy match (module matches, basepath is similar)
            api_module = topData.get('module', 'Generic')
            api_urls = getDictValue(topData, 'info.servers.*.url', [])
            api_default = topData['default']

            if (api_module == module) and (basepath in api_urls):
                node = topItem

                for idx_path in range(topItem.childCount()):
                    pathItem = topItem.child(idx_path)
                    pathData = pathItem.data(0, Qt.UserRole)

                    if pathData.get('path', None) == path:
                        return pathItem

        return node

    def getApiField(self, module = '', basepath = '', path='', field=''):
        try:
            data = self.getApiDoc(module, basepath)
            if data is not None:

                basepath = getDictValue(data,"servers.0.url") if data is not None else basepath
                paths = data.get('paths',{}) if data is not None else None

                # Operation response
                path = path.replace("<", "{").replace(">", "}")
                if path in paths:
                    operation = paths.get(path)
                elif path.replace(basepath,"") in paths:
                    operation = paths.get(path.replace(basepath,""))
                else:
                    operation = None
                operation = getDictValue(operation,"get.responses.200",False) if operation is not None else {}

                # Field
                if field is None and operation is not None and isinstance(operation, dict):
                    return operation.get('description',None)

                # Field
                def findFieldProperties(key, schema):
                    if not isinstance(schema, dict):
                        return schema

                    keys = key.split('.', 1)
                    if keys[0] == '':
                        return schema

                    if schema.get('type', None) == 'object':
                        properties = schema.get('properties', None)

                        if isinstance(properties, dict):
                            ref = properties.get("$ref", None)
                            if ref is not None:
                                properties = self.getSchemaComponent(data, ref)

                        if isinstance(properties, dict):
                            value = properties.get(keys[0],{})

                            if len(keys) == 1:
                                return value
                            else:
                                return findFieldProperties(keys[1], value)

                    elif (schema.get('type', None) == 'array') and (keys[0] == '*'):
                        value = schema.get('items', {})

                        if len(keys) == 1:
                            return value
                        else:
                            return findFieldProperties(keys[1], value)

                    return schema

                schema = getDictValue(operation, 'content.application/json.schema', None)
                fieldprops = findFieldProperties(field, schema)
                if fieldprops is not None:
                    return fieldprops.get('description','')


                # response = getDictValue(operation, 'content.application/json.schema.properties', False)
                # if not response:
                #     response = getDictValue(operation, 'content.application/json.schema.items.properties', False)
                #
                # if response and isinstance(response, dict):
                #     if not field in response:
                #         parts = field.split(".")
                #         field = parts[0] if len(parts) > 0 else None
                #
                #     if field is not None and field in response:
                #         return response.get(field).get('description')

            return None
        except:
            return None


    def getSchemaComponent(self, data, key):
        # eg "#components/schema/user/properties
        key = key.replace("#", "").replace("/", ".")
        return getDictValue(data, key, False)


    def applyItem(self):
        if not self.itemList.currentItem():
            return False

        # Find API module
        data = self.itemList.currentItem().data(0,Qt.UserRole)
        module = data.get('module', None)
        if module is None:
            return False

        tab = self.mainWindow.getModule(module)
        if tab is not None:
            path = data.get('path', '')
            options = {
                'basepath' : getDictValue(data, 'info.servers.0.url',''),
                'resource' : path
            }

            # Will pull the default settings from the API doc
            tab.setSettings(options)
            self.mainWindow.RequestTabs.setCurrentWidget(tab)

        self.close()


class ApiWidgetItem(QTreeWidgetItem):
    def __lt__(self, other):
        data1 = self.data(0,Qt.UserRole)
        data2 = other.data(0,Qt.UserRole)

        if data1.get('iscategory',False) and data2.get('iscategory',False):
            return data1.get('name','') < data2.get('name','')
        elif data1.get('default',False) != data2.get('default',False):
            return data1.get('default',False)
        else:
            return data1.get('name','') < data2.get('name','')
