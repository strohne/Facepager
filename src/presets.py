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
        self.loadingIndicator = QLabel('Loading...please wait a second.')
        self.loadingIndicator.hide()
        layout.addWidget(self.loadingIndicator)


        #Middle
        central = QHBoxLayout()
        layout.addLayout(central,1)


        #list view
        self.presetList = QListWidget(self)
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

        self.detailLayout.addLayout(self.detailForm,1)

        self.detailModule = QLabel('')
        self.detailForm.addRow('<b>Module</b>',self.detailModule)

        self.detailOptions = QLabel()
        self.detailOptions.setWordWrap(True)
        #self.detailOptions.setStyleSheet("background: rgba(0,0,0,0);border:0px;")
        self.detailForm.addRow('<b>Options</b>',self.detailOptions)


        self.detailColumns = QLabel()
        self.detailColumns.setWordWrap(True)
        #self.detailColumns.setStyleSheet("background: rgba(0,0,0,0);border:0px;")
        self.detailForm.addRow('<b>Columns</b>',self.detailColumns)


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
        #self.statusbar.addWidget(self.folderLabel)
        layout.addWidget(self.statusbar)


        #self.presetFolder = os.path.join(os.path.dirname(self.mainWindow.settings.fileName()),'presets')
        self.presetFolder = os.path.join(os.path.expanduser("~"),'Facepager','Presets')
        self.statusbar.showMessage(self.presetFolder)


        self.presetVersion = '3_9'
        self.presetSuffix = '-'+self.presetVersion+'.json'

#         if getattr(sys, 'frozen', False):
#             self.defaultPresetFolder = os.path.join(os.path.dirname(sys.executable),'presets')
#         elif __file__:
#             self.defaultPresetFolder = os.path.join(os.path.dirname(__file__),'presets')


    def currentChanged(self):
        #hide
        self.detailName.setText("")
        self.detailModule.setText("")
        self.detailDescription.setText("")
        self.detailOptions.setText("")
        self.detailColumns.setText("")
        self.detailWidget.hide()

        current = self.presetList.currentItem()
        if current and current.isSelected():
            data = current.data(Qt.UserRole)
            self.detailName.setText(data.get('name'))
            self.detailModule.setText(data.get('module'))
            self.detailDescription.setText(data.get('description')+"\n")

            self.detailOptions.setText(json.dumps(data.get('options'),indent=2, separators=(',', ': '))[2:-2].replace('\"',''))
            self.detailColumns.setText("\n".join(data.get('columns',[])))

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

            if (data.get('module') == 'Generic'):
                try: data['caption'] = data.get('module')  + ' ('+urlparse(data['options']['urlpath']).netloc + "): "+data.get('name')
                except: data['caption'] = data.get('module') + ": "+data.get('name')
            else: data['caption'] = data.get('module') + ": "+data.get('name')
            if default: data['caption'] = data['caption'] +"*"

            newItem = QListWidgetItem()
            newItem.setText(data['caption'])
            newItem.setData(Qt.UserRole,data)


#            if default:
#                ft = newItem.font()
#                ft.setWeight(QFont.Bold)
#                newItem.setFont(ft)



            self.presetList.addItem(newItem)
        except Exception as e:
             QMessageBox.information(self,"Facepager","Error loading preset:"+str(e))



    def clear(self):
        self.presetList.clear()
        self.detailWidget.hide()
        self.loadingIndicator.show()

    def initPresets(self):
        self.loadingIndicator.show()

        #self.defaultPresetFolder
        self.presetList.clear()
        self.detailWidget.hide()

        try:
            files = requests.get("https://api.github.com/repos/strohne/Facepager/contents/presets").json()
            files = [f['path'] for f in files if f['path'].endswith(self.presetSuffix)]
            for filename in files:
                self.addPresetItem("https://raw.githubusercontent.com/strohne/Facepager/master/",filename,True,True)
        except Exception as e:
             QMessageBox.information(self,"Facepager","Error loading online presets:"+str(e))

#         if os.path.exists(self.defaultPresetFolder):
#             files = [f for f in os.listdir(self.defaultPresetFolder) if f.endswith(self.presetSuffix)]
#             for filename in files:
#                 self.addPresetItem(self.defaultPresetFolder,filename,True)

        if os.path.exists(self.presetFolder):
            files = [f for f in os.listdir(self.presetFolder) if f.endswith(self.presetSuffix)]
            for filename in files:
                self.addPresetItem(self.presetFolder,filename)

        self.presetList.setFocus()
        self.presetList.setCurrentRow(0)
        self.presetList.sortItems()
        self.applyButton.setDefault(True)

        self.loadingIndicator.hide()

        #self.currentChanged()

    def loadPreset(self):
        if not self.presetList.currentItem(): return False

        data = self.presetList.currentItem().data(Qt.UserRole)

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
        self.close()

    def uniqueFilename(self,name):
        filename = os.path.join(self.presetFolder,re.sub('[^a-zA-Z0-9_-]+', '_', name )+self.presetSuffix)
        i = 1
        while os.path.exists(filename) and i < 10000:
            filename = os.path.join(self.presetFolder,re.sub('[^a-zA-Z0-9_-]+', '_', name )+"-"+str(i)+self.presetSuffix)
            i+=1
        if os.path.exists(filename):
            raise Exception('Could not find unique filename')
        return filename

    def deletePreset(self):
        if not self.presetList.currentItem(): return False
        data = self.presetList.currentItem().data(Qt.UserRole)
        if data.get('default',False):
            QMessageBox.information(self,"Facepager","Cannot delete default presets.")
            return False

        reply = QMessageBox.question(self, 'Delete Preset',u"Are you sure to delete the preset \"{0}\"?".format(data.get('name','')), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes: return

        os.remove(os.path.join(self.presetFolder, data.get('filename')))
        self.initPresets()

    def newPreset(self):
        dialog=QDialog(self.mainWindow)
        dialog.setWindowTitle("New Preset")
        layout=QVBoxLayout()

        label=QLabel("<b>Name</b>")
        layout.addWidget(label)
        name=QLineEdit()
        layout.addWidget(name,0)


        label=QLabel("<b>Description</b>")
        layout.addWidget(label)

        description=QTextEdit()
        description.setMinimumWidth(500)
        description.acceptRichText=False
        description.setFocus()
        layout.addWidget(description,1)


        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        layout.addWidget(buttons,0)
        dialog.setLayout(layout)

        def save():
            filename= self.uniqueFilename(self.mainWindow.RequestTabs.currentWidget().name+"-"+name.text())

            data = {
                    'name':name.text(),
                    'description':description.toPlainText(),
                    'module':self.mainWindow.RequestTabs.currentWidget().name,
                    'options':self.mainWindow.RequestTabs.currentWidget().getOptions('preset'),
                    'columns':self.mainWindow.fieldList.toPlainText().splitlines()
            }

            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))

            with open(filename, 'w') as outfile:
                json.dump(data, outfile,indent=2, separators=(',', ': '))

            self.initPresets()
            dialog.close()



        def close():
            dialog.close()

        #connect the nested functions above to the dialog-buttons
        buttons.accepted.connect(save)
        buttons.rejected.connect(close)
        dialog.exec_()

    def overwritePreset(self):
        if not self.presetList.currentItem():
            return False
        data = self.presetList.currentItem().data(Qt.UserRole)

        if data.get('default',False):
            QMessageBox.information(self,"Facepager","Cannot overwrite default presets.")
            return False

        dialog=QDialog(self.mainWindow)
        dialog.setWindowTitle("Overwrite selected preset")
        layout=QVBoxLayout()

        label=QLabel("<b>Name</b>")
        layout.addWidget(label)
        name=QLineEdit()
        name.setText(data.get('name'))
        layout.addWidget(name,0)

        label=QLabel("<b>Description</b>")
        layout.addWidget(label)

        description=QTextEdit()
        description.setMinimumWidth(500)
        description.acceptRichText=False
        description.setPlainText(data.get('description'))
        description.setFocus()
        layout.addWidget(description,1)

        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        layout.addWidget(buttons,0)
        dialog.setLayout(layout)

        def save():
            filename = os.path.join(self.presetFolder,data.get('filename'))
            #filename= self.uniqueFilename(name.text())

            data.update ({
                    'name':name.text(),
                    'description':description.toPlainText(),
                    'module':self.mainWindow.RequestTabs.currentWidget().name,
                    'options':self.mainWindow.RequestTabs.currentWidget().getOptions('preset'),
                    'columns':self.mainWindow.fieldList.toPlainText().splitlines()
            })

            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))

            reply = QMessageBox.question(self, 'Overwrite Preset',u"Are you sure to overwrite the selected preset \"{0}\" with the current settings?".format(data.get('name','')), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                with open(filename, 'w') as outfile:
                    json.dump(data, outfile,indent=2, separators=(',', ': '))

                dialog.close()
                self.initPresets()
            else:
                dialog.close()



        def close():
            dialog.close()

        #connect the nested functions above to the dialog-buttons
        buttons.accepted.connect(save)
        buttons.rejected.connect(close)
        dialog.exec_()
