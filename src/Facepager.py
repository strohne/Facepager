import cProfile
import sys
from PySide.QtCore import *
from PySide.QtGui import *
from toolbar import Toolbar
from tree import *
from models import *
from actions import *


class FacebookTab(QWidget):

    def __init__(self, parent=None,mainWindow=None):
        QWidget.__init__(self, parent)
        self.mainWindow=mainWindow
        mainLayout = QFormLayout()
                
        #-Query Type
        self.relationEdit=QComboBox(self)
        self.relationEdit.insertItems(0,['<self>','<search>','feed','posts','comments','likes','global_brand_children','groups','insights','members','picture','docs','noreply','invited','attending','maybe','declined','videos','accounts','achievements','activities','albums','books','checkins','events','family','friendlists','friends','games','home','interests','links','locations','movies','music','notes','photos','questions','scores','statuses','subscribedto','tagged','television'])        
        self.relationEdit.setEditable(True)
        mainLayout.addRow("Query",self.relationEdit)

        #-Since
        self.sinceEdit=QDateEdit(self)
        self.sinceEdit.setDate(datetime.datetime.today().replace(year=datetime.datetime.today().year-1,day=datetime.datetime.today().day-1))
        mainLayout.addRow("Since",self.sinceEdit)
        

        #-Until
        self.untilEdit=QDateEdit(self)
        self.untilEdit.setDate(datetime.datetime.today())
        mainLayout.addRow("Until",self.untilEdit)
        
        #-Offset
        self.offsetEdit=QSpinBox(self)
        self.offsetEdit.setMaximum(500)
        self.offsetEdit.setMinimum(0)
        self.offsetEdit.setValue(0)
        mainLayout.addRow("Offset",self.offsetEdit)

        #-Limit
        self.limitEdit=QSpinBox(self)
        self.limitEdit.setMaximum(1000)
        self.limitEdit.setMinimum(1)
        self.limitEdit.setValue(50)
        mainLayout.addRow("Limit",self.limitEdit)
        
        self.setLayout(mainLayout)
        
    def getOptions(self):      
        options={}
        
        #options for request  
        options['requester']='facebook'       
        options['querytype']=self.relationEdit.currentText()
        options['relation']=self.relationEdit.currentText()
        options['since']=self.sinceEdit.date().toString("yyyy-MM-dd")
        options['until']=self.untilEdit.date().toString("yyyy-MM-dd")
        options['offset']=self.offsetEdit.value()
        options['limit']=self.limitEdit.value()
        
        #options for data handling
        options['append']=True
        options['appendempty']=True
        options['objectid']='id'
        
        if (options['relation']=='<self>'):
            options['nodedata']=None
            options['splitdata']=False
        else:  
            options['nodedata']='data'
            options['splitdata']=True
               
        return options        
        


class TwitterTab(QWidget):

    def __init__(self, parent=None,mainWindow=None):
        QWidget.__init__(self, parent)
        self.mainWindow=mainWindow
        mainLayout = QFormLayout()
                
        #-Query Type
        self.relationEdit=QComboBox(self)
        self.relationEdit.insertItems(0,['statuses/user_timeline'])       
        self.relationEdit.setEditable(True)
        mainLayout.addRow("Resource",self.relationEdit)

        #Parameter
        self.objectidEdit=QComboBox(self)                
        self.objectidEdit.insertItems(0,['screen_name'])
        self.objectidEdit.insertItems(0,['user_id'])
        self.objectidEdit.setEditable(True)
        mainLayout.addRow("Object ID",self.objectidEdit)


        self.setLayout(mainLayout)
        
    def getOptions(self):      
        options={}
        
        #options for request 
        options['requester']='twitter'
        options['querytype']=self.relationEdit.currentText()
        options['objectidparam']=self.objectidEdit.currentText()
                
        #options for data handling
        options['append']=True
        options['appendempty']=True        
        options['splitdata']=True
        options['nodedata']='data'
        options['objectid']='id'        
        
        return options  

class GenericTab(QWidget):

    def __init__(self, parent=None,mainWindow=None):
        QWidget.__init__(self, parent)
        self.mainWindow=mainWindow
        mainLayout = QFormLayout()
                
        #URL prefix 
        self.prefixEdit=QComboBox(self)        
        self.prefixEdit.insertItems(0,['https://api.twitter.com/1/statuses/user_timeline.json?screen_name='])               
        self.prefixEdit.setEditable(True)
        mainLayout.addRow("URL prefix",self.prefixEdit)

        #URL field 
        self.fieldEdit=QComboBox(self)
        self.fieldEdit.insertItems(0,['<Object ID>','<None>'])       
        self.fieldEdit.setEditable(True)        
        mainLayout.addRow("URL field",self.fieldEdit)
        
        #URL suffix 
        self.suffixEdit=QComboBox(self)
        self.suffixEdit.insertItems(0,[''])       
        self.suffixEdit.setEditable(True)        
        mainLayout.addRow("URL suffix",self.suffixEdit)
        

        #Extract option 
        self.extractEdit=QComboBox(self)
        self.extractEdit.insertItems(0,['data'])
        self.extractEdit.insertItems(0,['data.matches'])               
        self.extractEdit.setEditable(True)
        mainLayout.addRow("Extract key",self.extractEdit)

        #Split option
        self.splitEdit=QCheckBox("Split data",self)
        self.splitEdit.setChecked(True)     
        mainLayout.addRow(self.splitEdit)


        self.setLayout(mainLayout)
        
    def getOptions(self):      
        options={}
        
        #options for request 
        options['requester']='generic'
        options['querytype']='generic'
        options['prefix']=self.prefixEdit.currentText()
        options['suffix']=self.suffixEdit.currentText()
        options['urlfield']=self.fieldEdit.currentText()
                
        #options for data handling
        options['append']=True
        options['appendempty']=True        
        options['splitdata']=self.splitEdit.isChecked()
        options['nodedata']=self.extractEdit.currentText() if self.extractEdit.currentText() != "" else False
        options['objectid']='id'        
        
        return options  

class MainWindow(QMainWindow):
    
    def __init__(self,central=None):
        super(MainWindow,self).__init__()
        
        self.setWindowTitle("Facepager")                
        #self.setWindowIcon(QIcon("../icons/icon_facepager.png"))
        self.setWindowIcon(QIcon("./icon_facepager.png"))        
        self.setMinimumSize(700,400)
        
        #self.deleteSettings()
        self.readSettings() 
        self.createActions()
        self.createUI()
        self.createDB()
                                        
        self.updateUI()
        
        
    def createDB(self):        
        self.database = Database()
        lastpath = self.settings.value("lastpath")
        if lastpath and os.path.isfile(lastpath):
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
        mainLayout=QVBoxLayout()
        self.mainWidget.setLayout(mainLayout)                
         
        dataLayout=QHBoxLayout()
        mainLayout.addLayout(dataLayout,0)
        
        requestLayout=QHBoxLayout()
        mainLayout.addLayout(requestLayout,0)

         
        #tree                                                
        self.tree=Tree(self.mainWidget,self)
        dataLayout.addWidget(self.tree,1)
        
        #right sidebar
        detailLayout=QVBoxLayout()
        dataLayout.addLayout(detailLayout,0)
        
     
        
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
        
        
        #requests
        self.RequestTabs=QTabWidget()
        requestLayout.addWidget(self.RequestTabs)
        
        #Tabs                      
        self.RequestTabs.addTab(FacebookTab(None,self),"Facebook")
        self.RequestTabs.addTab(TwitterTab(None,self),"Twitter")
        self.RequestTabs.addTab(GenericTab(None,self),"Generic")

        
        
        #request
        actionLayout=QVBoxLayout()        
        requestLayout.addLayout(actionLayout)

        #log
        detailGroup=QGroupBox("Status Log")
        groupLayout=QVBoxLayout()
        detailGroup.setLayout(groupLayout)
        actionLayout.addWidget(detailGroup,1)
                
        self.loglist=QTextEdit()
        self.loglist.setLineWrapMode(QTextEdit.NoWrap)
        self.loglist.setWordWrapMode(QTextOption.NoWrap)
        self.loglist.acceptRichText=False
        self.loglist.clear()
        groupLayout.addWidget(self.loglist)
                
        #fetch data                                    
        fetchdata=QHBoxLayout()
        mainLayout.addLayout(fetchdata)
                        
                                              
        #-Level
        self.levelEdit=QSpinBox(self.mainWidget)
        self.levelEdit.setMinimum(1)
        fetchdata.addWidget(QLabel("For all selected nodes and their children of level"))
        fetchdata.addWidget(self.levelEdit)
        
        #-button        
        button=QPushButton("Fetch Data", self.mainWidget)
        button.clicked.connect(self.actions.actionQuery.trigger)
        fetchdata.addWidget(button)
        
        fetchdata.addStretch(1)
        

          
        
                 

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
        self.resize(self.settings.value("size", QSize(800, 800)))
        self.move(self.settings.value("pos", QPoint(200, 10)))
        self.settings.endGroup()         
      
    def deleteSettings(self):    
        self.settings = QSettings("Keyling", "Facepager")
        self.settings.beginGroup("MainWindow")
        self.settings.remove("")
        self.settings.endGroup()
        self.settings.remove("lastpath")

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

