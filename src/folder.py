from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QFileDialog, QCheckBox, QHBoxLayout, QLabel

class SelectFolderDialog(QFileDialog):
    """
    Create a custom Folder Dialog with an option to import files as nodes
    """

    def __init__(self,*args,**kwargs):
        super(SelectFolderDialog,self).__init__(*args,**kwargs)
        self.setOption(QFileDialog.DontUseNativeDialog)
        self.setFileMode(QFileDialog.Directory)


        #QFileDialog.getExistingDirectory(self, 'Select Download Folder', datadir)) #, QFileDialog.ShowDirsOnly
        #self.mainWindow = self.parent()

        self.optionNodes = QCheckBox("Add selected files as nodes",self)
        self.optionNodes.clicked.connect(self.optionNodesClick)
        #self.optionNodes.setCheckState(Qt.CheckState.Checked)

        layout = self.layout()
        row = layout.rowCount()
        layout.addWidget(QLabel('Options'),row,0)

        options = QHBoxLayout()
        options.addWidget(self.optionNodes)
        options.addStretch(1)
        layout.addLayout(options,row,1,1,2)
        self.setLayout(layout)

        #if self.exec_():
            #if os.path.isfile(self.selectedFiles()[0]):
            
    def optionNodesClick(self):
        if self.optionNodes.isChecked():
            self.setFileMode(QFileDialog.ExistingFiles)
        else:
            self.setFileMode(QFileDialog.Directory)