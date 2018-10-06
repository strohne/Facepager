from PySide.QtCore import *
from PySide.QtGui import *

class SelectFolderDialog(QFileDialog):
    """
    Create a custom Folder Dialog with an option to import files as nodes
    """

    def __init__(self,*args,**kwargs):
        super(SelectFolderDialog,self).__init__(*args,**kwargs)        
        self.setFileMode(QFileDialog.Directory)


        #QFileDialog.getExistingDirectory(self, 'Select Download Folder', datadir)) #, QFileDialog.ShowDirsOnly
        #self.mainWindow = self.parent()

        self.optionNodes = QCheckBox("Add files as nodes",self)
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
