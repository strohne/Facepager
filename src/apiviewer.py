from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

import os
import sys
import re
import json
from textviewer import *
from urllib.parse import urlparse
import requests
import threading
import webbrowser
import platform
from utilities import *

class ApiViewer(QDialog):
    def __init__(self, parent=None):
        super(ApiViewer,self).__init__(parent)

        self.mainWindow = parent
        self.setWindowTitle("API Viewer")
        self.setMinimumWidth(700);
        self.setMinimumHeight(600);

        #layout
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        #loading indicator
        self.loadingLock = threading.Lock()
        self.loadingIndicator = QLabel('Loading...please wait a second.')
        self.loadingIndicator.hide()
        layout.addWidget(self.loadingIndicator)

        #Middle
        central = QHBoxLayout()
        layout.addLayout(central,1)

        #list view
        self.itemList = QTreeWidget(self)
        self.itemList.setHeaderHidden(True)
        self.itemList.setColumnCount(1)
        self.itemList.setIndentation(15)
        self.itemList.itemSelectionChanged.connect(self.currentChanged)
        central.addWidget(self.itemList,1)

        #detail view
        self.detailView=QScrollArea()
        self.detailView.setWidgetResizable(True)
        self.detailWidget = QWidget()
        self.detailWidget.setAutoFillBackground(True)
        self.detailWidget.setStyleSheet("background-color: rgb(255,255,255);")

        self.detailLayout=QVBoxLayout()
        self.detailWidget.setLayout(self.detailLayout)
        self.detailView.setWidget(self.detailWidget)

        central.addWidget(self.detailView,3)

        self.detailName = QLabel('')
        self.detailName.setWordWrap(True)
        self.detailName.setStyleSheet("QLabel  {font-size:15pt;font-weight:bold;}")
        self.detailLayout.addWidget(self.detailName)

        self.detailDescription = TextViewer()
        #self.detailDescription .setStyleSheet("QTextViewer  {padding-left:0px;}")
        self.detailLayout.addWidget(self.detailDescription)

        self.detailForm=QFormLayout()
        self.detailForm.setRowWrapPolicy(QFormLayout.DontWrapRows);
        self.detailForm.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow);
        self.detailForm.setFormAlignment(Qt.AlignLeft | Qt.AlignTop);
        self.detailForm.setLabelAlignment(Qt.AlignLeft);
        self.detailLayout.addLayout(self.detailForm,1)

        #buttons
        buttons= QHBoxLayout() #QDialogButtonBox()
        
        self.folderButton = QPushButton("")
        self.folderButton.setFlat(True)
        self.folderButton.clicked.connect(self.folderClicked)
        buttons.addWidget(self.folderButton)
        
        buttons.addStretch()

        self.rejectButton=QPushButton('Close')
        self.rejectButton.clicked.connect(self.close)
        self.rejectButton.setToolTip("Close the window")
        buttons.addWidget(self.rejectButton)

        # self.applyButton=QPushButton('Apply')
        # self.applyButton.setDefault(True)
        # self.applyButton.clicked.connect(self.applyItem)
        # self.applyButton.setToolTip("Apply the selected option.")
        # buttons.addWidget(self.applyButton)
        layout.addLayout(buttons)

        #status bar
        #self.statusbar = QStatusBar()
        #self.statusbar.insertWidget(0,self.folderButton)
        #layout.addWidget(self.statusbar)

        self.folder = os.path.join(os.path.expanduser("~"), 'Facepager', 'APIs')
        self.folderButton.setText(self.folder)
        self.filesSuffix = ['.json']
        self.lastSelected = None
        self.moduleDoc = {}
        self.topNodes= {}

        self.allFilesLoaded = False
        if getattr(sys, 'frozen', False):
            self.folderDefault = os.path.join(os.path.expanduser("~"), 'Facepager', 'DefaultAPIs')
            self.filesDownloaded = False
        else:
            self.folderDefault = os.path.join(getResourceFolder(), 'docs')
            self.filesDownloaded = True


    def folderClicked(self):
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)

        if platform.system() == "Windows":
            webbrowser.open(self.folder)
        elif platform.system() == "Darwin":
            webbrowser.open('file:///' + self.folder)
        else:
            webbrowser.open('file:///' + self.folder)

    def showWindow(self):
        self.show()
        QApplication.processEvents()

        # Load files
        self.loadFiles()

        # Select item
        if (self.lastSelected is None) or (self.lastSelected not in self.topNodes):
            selected = self.itemList.topLevelItem(0)
        else:
            selected = self.topNodes.get(self.lastSelected)
        self.itemList.setCurrentItem(selected)
        self.itemList.setFocus()

        #self.applyButton.setDefault(True)
        self.loadingIndicator.hide()
        self.exec_()

    def addDetailRowCaption(self,caption):
        caption = QLabel(caption)
        caption.setWordWrap(True)
        caption.setStyleSheet("QLabel  {font-size:12pt;margin-top:1em;margin-bottom:0.5em;font-weight:bold;}")

        self.detailForm.addRow(caption)

    def addDetailRow(self,name,value):
        name =  QLabel(name)
        name.setWordWrap(True)
        name.setStyleSheet("QLabel  {padding-left:0.4em;}")

        valueWidget = TextViewer()
        valueWidget.setText(value)
        self.detailForm.addRow(name,valueWidget)

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
                    self.addDetailRowCaption('Paths')
                    self.addDetailRow('Documentation: ', getDictValue(operation, 'externalDocs.url'))
                    self.addDetailRow('Base path: ', getDictValue(data, 'info.servers.0.url'))
                    self.addDetailRow('Path: ', getDictValue(data, 'path'))

                    # Parameters
                    params = operation.get('parameters',{})
                    if params:
                        self.addDetailRowCaption('Parameters')
                        for param in params:
                            self.addDetailRow(param.get('name'),param.get('description'))

                    response = getDictValue(operation, 'responses.200.content.application/json.schema.properties', False)
                    if not response:
                        response = getDictValue(operation, 'responses.200.content.application/json.schema.items.properties',False)

                    if response and isinstance(response,dict):
                        self.addDetailRowCaption('Response')
                        for name, value in response.items():
                            self.addDetailRow(name,value.get('description'))

            self.detailWidget.show()

    def clearDetails(self):
        self.detailWidget.hide()

        self.detailName.setText("")
        self.detailDescription.setText("")

        while self.detailForm.rowCount() > 0:
            self.detailForm.removeRow(0)

    def clear(self):
        self.itemList.clear()
        self.clearDetails()

    def downloadDefaultFiles(self,silent=False):
        return False
        
        # with self.loadingLock:
        #     if self.presetsDownloaded:
        #         return False
        #
        #     try:
        #         #Create folder
        #         if not os.path.exists(self.folderDefault):
        #             os.makedirs(self.folderDefault)
        #
        #         #Clear folder
        #         for filename in os.listdir(self.folderDefault):
        #             os.remove(os.path.join(self.folderDefault, filename))
        #
        #         #Download
        #         files = requests.get("https://api.github.com/repos/strohne/Facepager/contents/docs").json()
        #         files = [f['path'] for f in files if f['path'].endswith(tuple(self.filesSuffix))]
        #         for filename in files:
        #             response = requests.get("https://raw.githubusercontent.com/strohne/Facepager/master/"+filename)
        #             with open(os.path.join(self.folderDefault, os.path.basename(filename)), 'wb') as f:
        #                 f.write(response.content)
        #     except Exception as e:
        #         if not silent:
        #             QMessageBox.information(self,"Facepager","Error downloading default API specifications:"+str(e))
        #         return False
        #     else:
        #         self.presetsDownloaded = True
        #         return True

    def loadFiles(self):
        if self.allFilesLoaded:
            return False

        self.loadingIndicator.show()
        try:
            self.downloadDefaultFiles()
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


    def loadFile(self, folder, filename, default=False):

        if os.path.join(folder, filename) in self.topNodes:
            return self.topNodes[os.path.join(folder, filename)]

        if not os.path.isfile(os.path.join(folder, filename)):
            return None

        try:
            with open(os.path.join(folder, filename), 'r') as input:
                data = json.load(input)

            # Add file item
            itemData = {}
            itemData['type'] = 'file'
            itemData['filename'] = filename
            itemData['folder'] = folder
            itemData['default'] = default

            itemData['info'] = data.get('info',{})
            itemData['info']['externalDocs'] = data.get('externalDocs',{})
            itemData['info']['servers'] = data.get('servers', {})
            itemData['module'] = data.get("x-facepager-module", "Generic")

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
            self.moduleDoc[itemData['module']] = data
            self.topNodes[os.path.join(folder, filename)] = topItem

            # Path nodes
            for path,operations in data.get('paths',{}).items():
                pathItemData = itemData.copy()
                pathItemData['type'] = 'path'
                pathItemData['caption'] = path
                pathItemData['path'] = path
                pathItemData['operations'] = operations


                newItem = ApiWidgetItem()
                newItem.setText(0,path)
                newItem.setData(0,Qt.UserRole, pathItemData)

                topItem.addChild(newItem)
                QApplication.processEvents()

            return topItem

        except Exception as e:
             QMessageBox.information(self,"Facepager","Error loading items:"+str(e))
             return None

    def getDocumentation(self, module, path=None, field=None):
        try:
            # Documentation
            filename = module + 'Tab'+self.filesSuffix[0]
            self.loadFile(self.folderDefault, filename, True)
            data = self.moduleDoc.get(module, None)

            if data is not None:
                if path is None:
                    return data

                basepath = getDictValue(data,"servers.0.url") if data is not None else None
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
                response = getDictValue(operation, 'content.application/json.schema.properties', False)
                if not response:
                    response = getDictValue(operation, 'content.application/json.schema.items.properties', False)

                if response and isinstance(response, dict):
                    if  not field in response:
                        parts = field.split(".")
                        field = parts[0] if len(parts) > 0 else None

                    if field is not None and field in response:
                        return response.get(field).get('description')

            return None
        except Exception as e:
            return None

    def applyItem(self):
        if not self.itemList.currentItem():
            return False

        data = self.itemList.currentItem().data(0,Qt.UserRole)
        if not data.get('iscategory',False):
            pass

            # #Find API module
            # for i in range(0, self.mainWindow.RequestTabs.count()):
            #     if self.mainWindow.RequestTabs.widget(i).name == data.get('module',''):
            #         tab = self.mainWindow.RequestTabs.widget(i)
            #         tab.setOptions(data.get('options',{}))
            #         self.mainWindow.RequestTabs.setCurrentWidget(tab)
            #         break
            # 
            # #Set columns
            # self.mainWindow.fieldList.setPlainText("\n".join(data.get('columns',[])))
            # self.mainWindow.actions.showColumns()
            # 
            # #Set global settings
            # self.mainWindow.speedEdit.setValue(data.get('speed',200))
            # self.mainWindow.headersCheckbox.setChecked(data.get('headers',False))

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
