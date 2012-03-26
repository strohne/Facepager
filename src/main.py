import sys
import csv
from PySide.QtCore import *
from PySide.QtGui import *
from toolbar import Toolbar
from tree import Tree


class MainWindow(QMainWindow):
    
    def __init__(self,central=None):
        super(MainWindow,self).__init__()
        self.setWindowTitle("Facepager")
        self.createComponents()
        self.setMinimumSize(700,400)
    
    def createComponents(self):
        self.Tree=Tree(parent=self)
        self.Toolbar=Toolbar(parent=self)
        self.addToolBar(self.Toolbar)    
        self.setCentralWidget(self.Tree) 

    def createLayouts(self):
        layoutMain=QHBoxLayout()
        layoutMain.addWidget(self.Tree)
        self.setLayout(layoutMain)
        


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main=MainWindow()
    
    main.show()

    sys.exit(app.exec_())

