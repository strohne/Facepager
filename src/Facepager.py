import cProfile
import sys
from PySide.QtCore import *
from PySide.QtGui import *
from toolbar import Toolbar
from tree import *
from models import *
from actions import *


class MainWindow(QMainWindow):
    
    def __init__(self,central=None):
        super(MainWindow,self).__init__()
        
        self.setWindowTitle("Facepager")                
        #self.setWindowIcon(QIcon("../icons/icon_facepager.png"))
        self.setWindowIcon(QIcon("./icon_facepager.png"))        
        self.setMinimumSize(700,400)
        
        self.readSettings() 
        self.createActions()
        self.createUI()
        self.createDB()
                                        
        self.updateUI()
        
        
    def createDB(self):
        self.database = Database()
        if os.path.isfile(self.settings.value("lastpath")):
            self.database.connect(self.settings.value("lastpath"))
        
        self.treemodel = TreeModel(self,self.database)
        self.tree.setModel(self.treemodel)        
        self.actions.actionShowColumns.trigger()
        

    def createActions(self):
        self.actions=Actions(self)       

                        
    def createUI(self):
        self.toolbar=Toolbar(parent=self,mainWindow=self)
        self.addToolBar(Qt.LeftToolBarArea,self.toolbar)    
        
        self.statusBar().showMessage('No database connection')
        self.statusBar().setSizeGripEnabled(False)       
        
        #dummy widget to contain the layout manager
        self.mainWidget=QWidget(self) 
        self.setCentralWidget(self.mainWidget)        
        mainLayout=QHBoxLayout()
        self.mainWidget.setLayout(mainLayout)                
         
        #tree                                                
        self.tree=Tree(self.mainWidget,self)
        mainLayout.addWidget(self.tree,1)
        
        #right sidebar
        detailLayout=QVBoxLayout()
        mainLayout.addLayout(detailLayout,0)
        
        #fetch data
        detailGroup=QGroupBox("Fetch Data")
        detailLayout.addWidget(detailGroup)
        groupLayout=QFormLayout()
        detailGroup.setLayout(groupLayout)
        
        groupLayout.addRow(QLabel("Input"))        

        #-Level
        self.levelEdit=QSpinBox(self.mainWidget)
        self.levelEdit.setMinimum(1)
        groupLayout.addRow("Level",self.levelEdit)
        
        groupLayout.addRow(QLabel('\nThroughput'))
                
        #-Query Type
        self.relationEdit=QComboBox(self.mainWidget)
        self.relationEdit.insertItems(0,['<self>','<search>','feed','posts','comments','likes','global_brand_children','groups','insights','members','picture','docs','noreply','invited','attending','maybe','declined','videos','accounts','achievements','activities','albums','books','checkins','events','family','friendlists','friends','games','home','interests','links','locations','movies','music','notes','photos','questions','scores','statuses','subscribedto','tagged','television'])        
        self.relationEdit.setEditable(True)
        groupLayout.addRow("Query",self.relationEdit)

        #-Since
        self.sinceEdit=QDateEdit(self.mainWidget)
        self.sinceEdit.setDate(datetime.datetime.today().replace(year=datetime.datetime.today().year-1,day=datetime.datetime.today().day-1))
        groupLayout.addRow("Since",self.sinceEdit)
        

        #-Until
        self.untilEdit=QDateEdit(self.mainWidget)
        self.untilEdit.setDate(datetime.datetime.today())
        groupLayout.addRow("Until",self.untilEdit)
        
        #-Offset
        self.offsetEdit=QSpinBox(self.mainWidget)
        self.offsetEdit.setMaximum(500)
        self.offsetEdit.setMinimum(0)
        self.offsetEdit.setValue(0)
        groupLayout.addRow("Offset",self.offsetEdit)

        #-Limit
        self.limitEdit=QSpinBox(self.mainWidget)
        self.limitEdit.setMaximum(1000)
        self.limitEdit.setMinimum(1)
        self.limitEdit.setValue(500)
        groupLayout.addRow("Limit",self.limitEdit)

        groupLayout.addRow(QLabel('\nOutput'))
        
        #-Empty record
        self.emptyEdit=QCheckBox("Add empty records for empty results",self.mainWidget)        
        groupLayout.addRow(self.emptyEdit)
        
        #-Delete records
#        self.deleteEdit=QCheckBox("Delete all! records of same query type and level before fetching",self.mainWidget)        
#        groupLayout.addRow(self.deleteEdit)

        
        #-button        
        button=QPushButton("Fetch Data", self.mainWidget)
        button.clicked.connect(self.actions.actionQuery.trigger)
        groupLayout.addRow(button)         
        
        #detail data
        detailGroup=QGroupBox("Raw Data")
        detailLayout.addWidget(detailGroup)
        groupLayout=QVBoxLayout()
        detailGroup.setLayout(groupLayout)
                        
        self.detailData=QTextEdit()                        
        self.detailData.setLineWrapMode(QTextEdit.NoWrap)
        self.detailData.setWordWrapMode(QTextOption.NoWrap)
        self.detailData.acceptRichText=False    
        groupLayout.addWidget(self.detailData)
        
#        #unpack data
#        detailGroup=QGroupBox("Unpack Data")
#        detailLayout.addWidget(detailGroup)
#        groupLayout=QFormLayout()
#        detailGroup.setLayout(groupLayout)
#        
#        #-Level
#        self.unpackLevelEdit=QSpinBox(self.mainWidget)
#        self.unpackLevelEdit.setMinimum(1)
#        groupLayout.addRow("Level",self.unpackLevelEdit)
#                
#        #-Key
#        self.unpackKeyEdit=QComboBox(self.mainWidget)
#        #self.unpackKeyEdit.insertItems(0,['<self>','<search>','feed','posts','comments','likes','groups','insights','members','picture','docs','noreply','invited','attending','maybe','declined','videos','accounts','achievements','activities','albums','books','checkins','events','family','friendlists','friends','games','home','interests','links','locations','movies','music','notes','photos','questions','scores','statuses','subscribedto','tagged','television'])        
#        self.unpackKeyEdit.setEditable(True)
#        groupLayout.addRow("Key",self.unpackKeyEdit)        
#        
#        #-Button 
#        button=QPushButton("Unpack Data")
#        button.clicked.connect(self.actions.actionUnpackData.trigger)
#        groupLayout.addWidget(button)   
        
                        
        #fields
        detailGroup=QGroupBox("Custom Table Columns (one key per line)")
        detailLayout.addWidget(detailGroup)
        groupLayout=QVBoxLayout()
        detailGroup.setLayout(groupLayout)
        
        self.fieldList=QTextEdit()                        
        self.fieldList.setLineWrapMode(QTextEdit.NoWrap)
        self.fieldList.setWordWrapMode(QTextOption.NoWrap)
        self.fieldList.acceptRichText=False
        self.fieldList.clear()
        self.fieldList.append('name')
        self.fieldList.append('message')
        self.fieldList.append('type')
        self.fieldList.append('metadata.type')
        self.fieldList.append('talking_about_count')
        self.fieldList.append('likes')                
        self.fieldList.append('likes.count')        
        self.fieldList.append('shares.count')
        self.fieldList.append('comments.count')
        self.fieldList.append('created_time')
        self.fieldList.append('updated_time')
       
                    
        groupLayout.addWidget(self.fieldList)        
                
        button=QPushButton("Apply Column Setup")
        button.clicked.connect(self.actions.actionShowColumns.trigger)
        groupLayout.addWidget(button)   

        #expand all
        detailGroup=QGroupBox("Tree")
        detailLayout.addWidget(detailGroup)
        groupLayout=QFormLayout()
        detailGroup.setLayout(groupLayout)
                
        #-Button 
        button=QPushButton("Expand all nodes")
        button.clicked.connect(self.actions.actionExpandAll.trigger)
        groupLayout.addWidget(button)   
        
        #-Button 
        button=QPushButton("Collapse all nodes")
        button.clicked.connect(self.actions.actionCollapseAll.trigger)
        groupLayout.addWidget(button)        

    def updateUI(self):
        #disable buttons that do not work without an opened database                   
        self.actions.databaseActions.setEnabled(self.database.connected)
        
        if self.database.connected:
            self.statusBar().showMessage(self.database.filename)
        else:
            self.statusBar().showMessage('No database connection')    
        
        
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

def startMain():
    app = QApplication(sys.argv)

    main=MainWindow()    
    main.show()
    
    sys.exit(app.exec_())    

  
if __name__ == "__main__":
    #cProfile.run('startMain()')
    startMain()

