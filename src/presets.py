from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtGui import *
import os
import sys
import re
import json
from textviewer import *
from urlparse import urlparse
import requests
import threading
import webbrowser
import platform
from dictionarytree import *

class PresetWindow(QDialog):
    def __init__(self, parent=None):
        super(PresetWindow,self).__init__(parent)

        self.mainWindow = parent
        self.setWindowTitle("Presets")
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
        self.presetList = QTreeWidget(self)
        self.presetList.setHeaderHidden(True)
        self.presetList.setColumnCount(1)
        self.presetList.setIndentation(15)
        self.presetList.itemSelectionChanged.connect(self.currentChanged)
        central.addWidget(self.presetList,2)

        #detail view
        self.detailView=QScrollArea()
        self.detailView.setWidgetResizable(True)
        self.detailWidget = QWidget()
        self.detailWidget.setAutoFillBackground(True)
        self.detailWidget.setStyleSheet("background-color: rgb(255,255,255);")

        #self.detailView.setFrameStyle(QFrame.Box)
        self.detailLayout=QVBoxLayout()
        self.detailWidget.setLayout(self.detailLayout)
        self.detailView.setWidget(self.detailWidget)

        central.addWidget(self.detailView,3)

        self.detailName = QLabel('')
        self.detailName.setWordWrap(True)
        self.detailName.setStyleSheet("QLabel  {font-size:15pt;}")

        self.detailLayout.addWidget(self.detailName)


        self.detailDescription = TextViewer()
        self.detailLayout.addWidget(self.detailDescription)


        self.detailForm=QFormLayout()
        self.detailForm.setRowWrapPolicy(QFormLayout.DontWrapRows);
        self.detailForm.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow);
        self.detailForm.setFormAlignment(Qt.AlignLeft | Qt.AlignTop);
        self.detailForm.setLabelAlignment(Qt.AlignLeft);

        self.detailOptions = DictionaryTree()
        self.detailOptions.setFrameShape(QFrame.NoFrame)
        #self.detailLayout.addWidget(self.detailViewer)

        self.detailLayout.addLayout(self.detailForm,1)

        self.detailModule = QLabel('')
        self.detailForm.addRow('<b>Module</b>',self.detailModule)

        #self.detailOptions = QLabel()
        #self.detailOptions.setWordWrap(True)
        #self.detailOptions.setStyleSheet("background: rgba(0,0,0,0);border:0px;")
        self.detailForm.addRow('<b>Options</b>',self.detailOptions)

        self.detailColumns = QLabel()
        self.detailColumns.setWordWrap(True)
        #self.detailColumns.setStyleSheet("background: rgba(0,0,0,0);border:0px;")
        detailColumnsLabel = QLabel('<b>Columns</b>')
        #detailColumnsLabel.setStyleSheet("QLabel { background-color : red;margin-top:0px;padding-top:0px;line-height:1em;vertical-align:top;border-top:0px;}")
        self.detailColumns.setStyleSheet("QLabel {margin-top:5px;}")
        detailColumnsLabel.setStyleSheet("QLabel {height:25px;}")
        self.detailForm.addRow(detailColumnsLabel,self.detailColumns)


        #buttons
        buttons= QHBoxLayout() #QDialogButtonBox()
        self.saveButton = QPushButton('New preset')
        self.saveButton.clicked.connect(self.newPreset)
        self.saveButton.setToolTip("Create a new preset using the current tab and parameters")
        #buttons.addButton(self.saveButton,QDialogButtonBox.ActionRole)
        buttons.addWidget(self.saveButton)

        self.overwriteButton = QPushButton('Overwrite preset')
        self.overwriteButton.clicked.connect(self.overwritePreset)
        self.overwriteButton.setToolTip("Overwrite the selected presets with the current tab and parameters")
        #buttons.addButton(self.overwriteButton,QDialogButtonBox.ActionRole)
        buttons.addWidget(self.overwriteButton)

        self.deleteButton = QPushButton('Delete preset')
        self.deleteButton.clicked.connect(self.deletePreset)
        self.deleteButton.setToolTip("Delete the selected preset. Default presets can not be deleted.")
        #buttons.addButton(self.deleteButton,QDialogButtonBox.ActionRole)
        buttons.addWidget(self.deleteButton)

        #layout.addWidget(buttons,1)


        buttons.addStretch()

        #buttons=QDialogButtonBox()
        self.rejectButton=QPushButton('Cancel')
        self.rejectButton.clicked.connect(self.close)
        self.rejectButton.setToolTip("Close the preset dialog.")
        buttons.addWidget(self.rejectButton)

        self.applyButton=QPushButton('Apply')
        self.applyButton.setDefault(True)
        self.applyButton.clicked.connect(self.loadPreset)
        self.applyButton.setToolTip("Load the selected preset.")
        #buttons.addButton(self.applyButton,QDialogButtonBox.AcceptRole)
        buttons.addWidget(self.applyButton)

        #buttons.addButton(QDialogButtonBox.Cancel)
        #buttons.rejected.connect(self.close)


        #layout.addWidget(buttons,0)
        layout.addLayout(buttons)

        #status bar
        self.statusbar = QStatusBar()
        #self.folderLabel = QLabel("")
        self.folderButton = QPushButton("")
        self.folderButton.setFlat(True)
        self.folderButton.clicked.connect(self.statusBarClicked)
        self.statusbar.insertWidget(0,self.folderButton)
        layout.addWidget(self.statusbar)


        #self.presetFolder = os.path.join(os.path.dirname(self.mainWindow.settings.fileName()),'presets')
        self.presetFolder = os.path.join(os.path.expanduser("~"),'Facepager','Presets')
        self.presetFolderDefault = os.path.join(os.path.expanduser("~"),'Facepager','DefaultPresets')
        self.folderButton.setText(self.presetFolder)

        self.presetsDownloaded = False
        self.presetSuffix = '.3_9.json'

#         if getattr(sys, 'frozen', False):
#             self.defaultPresetFolder = os.path.join(os.path.dirname(sys.executable),'presets')
#         elif __file__:
#             self.defaultPresetFolder = os.path.join(os.path.dirname(__file__),'presets')

    def statusBarClicked(self):
        if not os.path.exists(self.presetFolder):
            os.makedirs(self.presetFolder)

        if platform.system() == "Windows":
            webbrowser.open(self.presetFolder)
        elif platform.system() == "Darwin":
            webbrowser.open('file:///'+self.presetFolder)
        else:
            webbrowser.open('file:///'+self.presetFolder)




    def currentChanged(self):
        #hide
        self.detailName.setText("")
        self.detailModule.setText("")
        self.detailDescription.setText("")
        self.detailOptions.clear()
        self.detailColumns.setText("")
        self.detailWidget.hide()

        current = self.presetList.currentItem()
        if current and current.isSelected():
            data = current.data(0,Qt.UserRole)

            if not data.get('iscategory',False):
                self.detailName.setText(data.get('name'))
                self.detailModule.setText(data.get('module'))
                self.detailDescription.setText(data.get('description')+"\n")

                self.detailOptions.showDict(data.get('options',[]))

                #self.detailOptions.setText(json.dumps(data.get('options'),indent=2, separators=(',', ': '))[2:-2].replace('\"',''))
                self.detailColumns.setText("\r\n".join(data.get('columns',[])))

                self.detailWidget.show()

    def showPresets(self):
        self.clear()
        self.show()
        QApplication.processEvents()

        self.initPresets()
        self.exec_()

    def addPresetItem(self,folder,filename,default=False,online=False):
        try:
            if online:
                data= requests.get(folder+filename).json()
            else:
                with open(os.path.join(folder, filename), 'r') as input:
                    data = json.load(input)

            data['filename'] = filename
            data['default'] = default
            data['online'] = online

            if (data.get('module') in ['Generic','Files']):
                try:
                    data['caption'] = data.get('name')
                    data['category'] = data.get('module') + " ("+urlparse(data['options']['basepath']).netloc+")"
                except:
                    data['caption'] = data.get('name')
                    data['category'] = data.get('module')
            else:
                data['caption'] = data.get('name')
                data['category'] = data.get('module')

            if default:
                data['caption'] = data['caption'] +"*"

            if not data['category'] in self.categoryNodes:
                categoryItem = QTreeWidgetItem()
                categoryItem.setText(0,data['category'])

                ft = categoryItem.font(0)
                ft.setWeight(QFont.Bold)
                categoryItem.setFont(0,ft)

                categoryItem.setData(0,Qt.UserRole,{'iscategory':True})


                self.presetList.addTopLevelItem(categoryItem)
                self.categoryNodes[data['category']] = categoryItem

            else:
                categoryItem = self.categoryNodes[data['category']]

            newItem = QTreeWidgetItem()
            newItem.setText(0,data['caption'])
            newItem.setData(0,Qt.UserRole,data)
            categoryItem.addChild(newItem)

            #self.presetList.setCurrentItem(newItem,0)
            QApplication.processEvents()

            return newItem

        except Exception as e:
             QMessageBox.information(self,"Facepager","Error loading preset:"+str(e))
             return None



    def clear(self):
        self.presetList.clear()
        self.detailWidget.hide()
        self.loadingIndicator.show()

    def downloadDefaultPresets(self):
        with self.loadingLock:
            if self.presetsDownloaded:
                return False

            try:
                #Create folder
                if not os.path.exists(self.presetFolderDefault):
                    os.makedirs(self.presetFolderDefault)

                #Clear folder
                for filename in os.listdir(self.presetFolderDefault):
                    os.remove(os.path.join(self.presetFolderDefault,filename))

                #Download
                files = requests.get("https://api.github.com/repos/strohne/Facepager/contents/presets").json()
                files = [f['path'] for f in files if f['path'].endswith(self.presetSuffix)]
                for filename in files:
                    response = requests.get("https://raw.githubusercontent.com/strohne/Facepager/master/"+filename)
                    with open(os.path.join(self.presetFolderDefault, os.path.basename(filename)), 'wb') as f:
                        f.write(response.content)
            except Exception as e:
                 QMessageBox.information(self,"Facepager","Error downloading default presets:"+str(e))
                 return False
            else:
                self.presetsDownloaded = True
                return True

    def initPresets(self):
        self.loadingIndicator.show()

        #self.defaultPresetFolder
        self.categoryNodes = {}
        self.presetList.clear()
        self.detailWidget.hide()

        self.downloadDefaultPresets()
        if os.path.exists(self.presetFolderDefault):
            files = [f for f in os.listdir(self.presetFolderDefault) if f.endswith(self.presetSuffix)]
            for filename in files:
                self.addPresetItem(self.presetFolderDefault,filename,True)

        if os.path.exists(self.presetFolder):
            files = [f for f in os.listdir(self.presetFolder) if f.endswith(self.presetSuffix)]
            for filename in files:
                self.addPresetItem(self.presetFolder,filename)

        self.presetList.expandAll()
        self.presetList.setFocus()
        self.presetList.sortItems(0,Qt.AscendingOrder)

        self.presetList.setCurrentItem(self.presetList.topLevelItem(0))

        self.applyButton.setDefault(True)
        self.loadingIndicator.hide()

        #self.currentChanged()

    def loadPreset(self):
        if not self.presetList.currentItem():
            return False

        data = self.presetList.currentItem().data(0,Qt.UserRole)
        if not data.get('iscategory',False):

            #Find API module
            for i in range(0, self.mainWindow.RequestTabs.count()):
                if self.mainWindow.RequestTabs.widget(i).name == data.get('module',''):
                    tab = self.mainWindow.RequestTabs.widget(i)
                    tab.setOptions(data.get('options',{}))
                    self.mainWindow.RequestTabs.setCurrentWidget(tab)
                    break

            #Set columns
            self.mainWindow.fieldList.setPlainText("\n".join(data.get('columns',[])))
            self.mainWindow.actions.showColumns()

            #Set global settings
            self.mainWindow.speedEdit.setValue(data.get('speed',200))

        self.close()

    def uniqueFilename(self,name):
        filename = re.sub('[^a-zA-Z0-9_-]+', '_', name )+self.presetSuffix
        i = 1
        while os.path.exists(os.path.join(self.presetFolder, filename)) and i < 10000:
            filename = re.sub('[^a-zA-Z0-9_-]+', '_', name )+"-"+str(i)+self.presetSuffix
            i+=1

        if os.path.exists(os.path.join(self.presetFolder, filename)):
            raise Exception('Could not find unique filename')
        return filename

    def deletePreset(self):
        if not self.presetList.currentItem():
            return False
        data = self.presetList.currentItem().data(0,Qt.UserRole)
        if data.get('default',False):
            QMessageBox.information(self,"Facepager","Cannot delete default presets.")
            return False

        if data.get('iscategory',False):
            return False

        reply = QMessageBox.question(self, 'Delete Preset',u"Are you sure to delete the preset \"{0}\"?".format(data.get('name','')), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes: return

        os.remove(os.path.join(self.presetFolder, data.get('filename')))
        self.initPresets()

    def editPreset(self,data = None):
        dialog=QDialog(self.mainWindow)
        if data is None:
            dialog.setWindowTitle("New Preset")
            data = {}
        else:
            dialog.setWindowTitle("Overwrite selected preset")

        self.currentFilename = data.get('filename',None)

        layout=QVBoxLayout()
        label=QLabel("<b>Name</b>")
        layout.addWidget(label)
        name=QLineEdit()
        name.setText(data.get('name',''))
        layout.addWidget(name,0)

        label=QLabel("<b>Description</b>")
        layout.addWidget(label)

        description=QTextEdit()
        description.setMinimumWidth(500)
        description.acceptRichText=False
        description.setPlainText(data.get('description',''))
        description.setFocus()
        layout.addWidget(description,1)

        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        layout.addWidget(buttons,0)
        dialog.setLayout(layout)

        def save():
            if self.currentFilename == None:
                self.currentFilename = self.uniqueFilename(self.mainWindow.RequestTabs.currentWidget().name+"-"+name.text())

            data = {
                    'name':name.text(),
                    'description':description.toPlainText(),
                    'module':self.mainWindow.RequestTabs.currentWidget().name,
                    'options':self.mainWindow.RequestTabs.currentWidget().getOptions('preset'),
                    'speed':self.mainWindow.speedEdit.value(),
                    'columns':self.mainWindow.fieldList.toPlainText().splitlines()
            }

            if not os.path.exists(self.presetFolder):
                os.makedirs(self.presetFolder)

            if os.path.exists(os.path.join(self.presetFolder,self.currentFilename)):
                reply = QMessageBox.question(self, 'Overwrite Preset',u"Are you sure to overwrite the selected preset \"{0}\" with the current settings?".format(data.get('name','')), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply != QMessageBox.Yes:
                    dialog.close()
                    self.currentFilename = None
                    return False


            with open(os.path.join(self.presetFolder,self.currentFilename), 'w') as outfile:
                json.dump(data, outfile,indent=2, separators=(',', ': '))

            dialog.close()
            return True



        def close():
            dialog.close()
            self.currentFilename = None
            return False

        #connect the nested functions above to the dialog-buttons
        buttons.accepted.connect(save)
        buttons.rejected.connect(close)
        dialog.exec_()
        return self.currentFilename


    def newPreset(self):
        filename = self.editPreset()
        if filename is not None:
            newitem = self.addPresetItem(self.presetFolder,filename)
            self.presetList.sortItems(0,Qt.AscendingOrder)
            self.presetList.setCurrentItem(newitem,0)


    def overwritePreset(self):
        if not self.presetList.currentItem():
            return False

        item = self.presetList.currentItem()
        data = item.data(0,Qt.UserRole)

        if data.get('default',False):
            QMessageBox.information(self,"Facepager","Cannot overwrite default presets.")
            return False

        if data.get('iscategory',False):
            return False

        filename = self.editPreset(data)

        if filename is not None:
            item.parent().removeChild(item)
            item = self.addPresetItem(self.presetFolder,filename)

            self.presetList.sortItems(0,Qt.AscendingOrder)
            self.presetList.setCurrentItem(item,0)


