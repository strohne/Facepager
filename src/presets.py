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
        self.setMinimumHeight(600);
        
        #layout
        layout = QVBoxLayout(self)        
        central = QHBoxLayout()
        layout.addLayout(central,1)
        self.setLayout(layout)

        #list view
        self.presetList = QListWidget(self)
        self.presetList.itemSelectionChanged.connect(self.currentChanged)
        central.addWidget(self.presetList,0)
        
        #detail view
        self.detailView=QTextEdit()
        self.detailView.acceptRichText=False
        self.detailView.setReadOnly(True)
        self.detailView.clear()        
        
        central.addWidget(self.detailView,0)        

        #buttons                
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.load)
        buttons.rejected.connect(self.close)                        
        layout.addWidget(buttons,0)
        
        self.presetFolder = os.path.join(os.path.dirname(self.mainWindow.settings.fileName()),'presets')
        
    
    def currentChanged(self):
        #show raw data
        self.detailView.clear()
     
        #item=current.internalPointer()
        current = self.presetList.currentItem()
        if current and current.isSelected(): 
            data = current.data(Qt.UserRole)    
            self.detailView.append(json.dumps(data,indent=2, separators=(',', ': ')))
     
        
    def loadPreset(self):
        self.presetList.clear()
        files = [f for f in os.listdir(self.presetFolder) if f.endswith('.json')]
        for filename in files:
            try:            
                with open(os.path.join(self.presetFolder, filename), 'r') as input:
                    data = json.load(input)
            
                newItem = QListWidgetItem()
                newItem.setText(data['name'])
                newItem.setData(Qt.UserRole,data)            
                self.presetList.addItem(newItem)
            except:
                 pass   
        
        self.presetList.setFocus()
        self.exec_()
        
        
    def load(self):
        data = self.presetList.currentItem().data(Qt.UserRole)
        
        #Find API module
        for i in range(0, self.mainWindow.RequestTabs.count()):
            if self.mainWindow.RequestTabs.widget(i).name == data.get('name',''):
                tab = self.mainWindow.RequestTabs.widget(i)
                tab.setOptions(data.get('options',{}))
                tab.show()
                break                    

        #Set columns
        self.mainWindow.fieldList.setPlainText(data.get('columns',''))
        self.close()
               

    def savePreset(self):
        dialog=QDialog(self.mainWindow)
        dialog.setWindowTitle("Save Preset")
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
                    'module':self.mainWindow.RequestTabs.currentWidget().name,
                    'options':self.mainWindow.RequestTabs.currentWidget().getOptions(True),
                    'columns':self.mainWindow.fieldList.toPlainText(),
                    'description':description.toPlainText(),
                    'name':name.text()
            }
            
            filename= os.path.join(self.presetFolder,re.sub('[^a-zA-Z0-9_-]+', '_', name.text() )+'.json')
            
            if os.path.isfile(filename):
                pass

            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))            
            
            with open(filename, 'w') as outfile:
                json.dump(data, outfile)
            
            dialog.close()
                  
                      

        def close():
            dialog.close()
            
        #connect the nested functions above to the dialog-buttons
        buttons.accepted.connect(save)
        buttons.rejected.connect(close)
        dialog.exec_()        
   