from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtGui import *
import os
import sys
import re
import json

class PresetWindow(QDialog):
    def __init__(self, parent=None):
        super(PresetWindow,self).__init__(parent)
        
        self.mainWindow = parent
        self.setWindowTitle("Presets")   
        self.setMinimumWidth(600);
        self.setMinimumHeight(400);
        
        #layout
        layout = QVBoxLayout(self)        
        central = QHBoxLayout()
        layout.addLayout(central,1)
        self.setLayout(layout)

        #list view
        self.presetList = QListWidget(self)
        self.presetList.itemSelectionChanged.connect(self.currentChanged)
        central.addWidget(self.presetList,1)
        
        #detail view                
        self.detailView=QFrame()
        self.detailView.setFrameStyle(QFrame.Box)                    
        self.detailForm=QFormLayout()
        self.detailView.setLayout(self.detailForm)
        
        central.addWidget(self.detailView,2)               
        
        self.detailName = QLabel('')
        self.detailForm.addRow('<b>Name</b>',self.detailName)

               
        self.detailDescription = QTextEdit()
        self.detailDescription.setStyleSheet("background: rgba(0,0,0,0);border:0px;")
        
        self.detailDescription.acceptRichText=False
        self.detailDescription.setReadOnly(True)
        self.detailForm.addRow('<b>Description</b>',self.detailDescription)

        self.detailModule = QLabel('')
        self.detailForm.addRow('<b>Module</b>',self.detailModule)
                        
        self.detailOptions = QTextEdit()
        self.detailOptions.setStyleSheet("background: rgba(0,0,0,0);border:0px;")        
        self.detailOptions.acceptRichText=False
        self.detailOptions.setReadOnly(True)
        self.detailForm.addRow('<b>Options</b>',self.detailOptions)
                
        self.detailColumns = QTextEdit()
        self.detailColumns.setStyleSheet("background: rgba(0,0,0,0);border:0px;")
        self.detailColumns.acceptRichText=False
        self.detailColumns.setReadOnly(True)
        self.detailForm.addRow('<b>Columns</b>',self.detailColumns)        
                
                

        #buttons
        buttons=QDialogButtonBox()
        self.saveButton = QPushButton('New preset')        
        self.saveButton.clicked.connect(self.newPreset)
        buttons.addButton(self.saveButton,QDialogButtonBox.ActionRole)
        
        self.deleteButton = QPushButton('Delete preset')
        self.deleteButton.clicked.connect(self.deletePreset)
        buttons.addButton(self.deleteButton,QDialogButtonBox.ActionRole)
        
        #layout.addWidget(buttons,1)        
        
        
                        
        #buttons=QDialogButtonBox()
        self.applyButton=QPushButton('Apply')
        self.applyButton.setDefault(True)
        self.applyButton.clicked.connect(self.loadPreset)
        buttons.addButton(self.applyButton,QDialogButtonBox.AcceptRole)
        
        buttons.addButton(QDialogButtonBox.Cancel)
        buttons.rejected.connect(self.close)                        
        layout.addWidget(buttons,0)
        
        #self.presetFolder = os.path.join(os.path.dirname(self.mainWindow.settings.fileName()),'presets')
        self.presetFolder = os.path.join(os.path.expanduser("~"),'Facepager','Presets')
        
        
        if getattr(sys, 'frozen', False):
            self.defaultPresetFolder = os.path.join(os.path.dirname(sys.executable),'presets')
        elif __file__:
            self.defaultPresetFolder = os.path.join(os.path.dirname(__file__),'presets')
        
        self.presetSuffix = '-3_2.json'        
    
    def currentChanged(self):
        #hide
        self.detailName.setText("") 
        self.detailModule.setText("")
        self.detailDescription.setText("")
        self.detailOptions.setText("")
        self.detailColumns.setText("")
     
        current = self.presetList.currentItem()
        if current and current.isSelected(): 
            data = current.data(Qt.UserRole)   
            self.detailName.setText(data.get('name')) 
            self.detailModule.setText(data.get('module'))
            self.detailDescription.setText(data.get('description'))
            self.detailOptions.setText(json.dumps(data.get('options'),indent=2, separators=(',', ': ')))
            self.detailColumns.setText("\n".join(data.get('columns',[])))

            
     
        
    def showPresets(self):
        self.initPresets()        
        self.exec_()
        
    def addPresetItem(self,folder,filename,default=False):
        try:            
            with open(os.path.join(folder, filename), 'r') as input:
                data = json.load(input)
            data['filename'] = filename
            data['default'] = default
        
            newItem = QListWidgetItem()
            newItem.setText(data['name'])    
            newItem.setData(Qt.UserRole,data)

            if default:
                ft = newItem.font()
                ft.setWeight(QFont.Bold)
                newItem.setFont(ft)
                

                        
            self.presetList.addItem(newItem)
        except Exception as e:
             QMessageBox.information(self,"Facepager","Error loading preset:"+str(e))   
        
            
    def initPresets(self):
        #self.defaultPresetFolder
        self.presetList.clear()
        
        if os.path.exists(self.defaultPresetFolder):    
            files = [f for f in os.listdir(self.defaultPresetFolder) if f.endswith(self.presetSuffix)]
            for filename in files: self.addPresetItem(self.defaultPresetFolder,filename,True)

        if os.path.exists(self.presetFolder):
            files = [f for f in os.listdir(self.presetFolder) if f.endswith(self.presetSuffix)]
            for filename in files: self.addPresetItem(self.presetFolder,filename)
        
        self.presetList.setFocus()
        self.presetList.setCurrentRow(0)
        self.applyButton.setDefault(True)
        
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
        
        reply = QMessageBox.question(self, 'Delete Preset',"Are you sure to delete the preset \"{0}\"?".format(data.get('name','')), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
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
            data = {
                    'name':name.text(),
                    'description':description.toPlainText(),
                    'module':self.mainWindow.RequestTabs.currentWidget().name,
                    'options':self.mainWindow.RequestTabs.currentWidget().getOptions('preset'),
                    'columns':self.mainWindow.fieldList.toPlainText().splitlines()
            }
            
            filename= self.uniqueFilename(name.text())

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
   