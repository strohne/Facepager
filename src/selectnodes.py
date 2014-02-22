from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtGui import *
from paramedit import *

class SelectNodesWindow(QDialog):
    
    
    def __init__(self, parent=None,tree=None):
        super(SelectNodesWindow,self).__init__(parent)
        
        self.tree = tree
        self.setWindowTitle("Select Nodes")
        
        
        #layout
        layout = QVBoxLayout(self)        
        central = QHBoxLayout()
        layout.addLayout(central,1)
        self.setLayout(layout)
        
        settingsLayout=QFormLayout()
        central.addLayout(settingsLayout,1)
        
        #Params
        self.paramEdit = QParamEdit(self)
        self.paramEdit.setNameOptions(['<None>','since','until','offset','limit','type'])
        self.paramEdit.setValueOptions(['<None>','2013-07-17','page'])       
        settingsLayout.addRow("Parameters",self.paramEdit)
        
        #Checkboxes
        self.childrenCheckbox = QCheckBox('Apply to current selection and child nodes')
        self.childrenCheckbox.setChecked(True)
        settingsLayout.addRow(self.childrenCheckbox)
        
        #Level
        self.levelEdit=QSpinBox(self)
        self.levelEdit.setMinimum(1)        
        self.levelEdit.setMaximum(500)
        settingsLayout.addRow("Level",self.levelEdit)        
        
        #buttons
        buttons=QDialogButtonBox()
        self.selectButton = QPushButton('Apply Selection')        
        self.selectButton.clicked.connect(self.selectNodes)
        buttons.addButton(self.selectButton,QDialogButtonBox.ActionRole)
        
       
        buttons.addButton(QDialogButtonBox.Cancel)
        buttons.rejected.connect(self.close)                        
        layout.addWidget(buttons,0)

    def show(self):
        self.exec_()
        
    def selectNodes(self):  
        level = self.levelEdit.value()-1
              
        filter = {'level':level} #,'objecttype':['seed','data','unpacked']
        indexes = self.tree.selectedIndexesAndChildren(False,filter)

        selmod = self.tree.selectionModel()
        selmod.clearSelection()
        newselection = QItemSelection()
        #selmod.select(indexes, QItemSelectionModel.Select)
        for index in indexes:
            newselection.merge(QItemSelection(index,index),QItemSelectionModel.Select)       
        
        selmod.select(newselection, QItemSelectionModel.Select|QItemSelectionModel.Rows)
                         
        self.close()
                        
        
        
            
