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
        self.setWindowIcon(QIcon("./icon_facepager.png"))
        self.createComponents()
        self.setMinimumSize(700,400)
        self.settings=None
        self.readSettings()
        
    def createComponents(self):
        self.Tree=Tree(parent=self)
        self.Toolbar=Toolbar(parent=self)
        self.addToolBar(self.Toolbar)    
        self.setCentralWidget(self.Tree) 

    def createLayouts(self):
        layoutMain=QHBoxLayout()
        layoutMain.addWidget(self.Tree)
        self.setLayout(layoutMain)
        
    def writeSettings(self):
        self.settings = QSettings("Keyling", "Facepager")
        self.settings.beginGroup("MainWindow")
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())
        self.settings.endGroup()
        
     

    def readSettings(self):
        self.settings = QSettings("Keyling", "Facepager")
        self.settings.beginGroup("MainWindow")
        self.resize(self.settings.value("size", QSize(400, 400)))
        self.move(self.settings.value("pos", QPoint(200, 200)))
        self.settings.endGroup()
        

    def closeEvent(self, event=QCloseEvent()):
        if self.close():
            self.writeSettings()
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main=MainWindow()
    
    main.show()
    
    sys.exit(app.exec_())
