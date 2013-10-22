import cProfile
import sys
from PySide.QtCore import *
from PySide.QtGui import *
import icons
from datatree import *
from dictionarytree import *
from database import *
from actions import *
from apimodules import * 
from help import *
from presets import *
from timer import *

class MainWindow(QMainWindow):
    
    def __init__(self,central=None):
        super(MainWindow,self).__init__()
        
        self.setWindowTitle("Facepager 3.3")                
        self.setWindowIcon(QIcon(":/icons/icon_facepager.png"))        
        self.setMinimumSize(900,700)
        self.move(QDesktopWidget().availableGeometry().center() - self.frameGeometry().center()-QPoint(0,100))
        #self.setStyleSheet("* {font-size:18px;}")
        #self.deleteSettings()
        self.readSettings() 
        self.createActions()
        self.createUI()
        self.createDB()
                                        
        self.updateUI()
        
    def createDB(self):        
        self.database = Database(self)
        lastpath = self.settings.value("lastpath")
        if lastpath and os.path.isfile(lastpath):
            self.database.connect(self.settings.value("lastpath"))        
        
        self.tree.loadData(self.database)
        self.actions.actionShowColumns.trigger()
        

    def createActions(self):
        self.actions=Actions(self)       

                        
    def createUI(self):
        
        self.helpwindow=HelpWindow(self)
        self.presetWindow=PresetWindow(self)
        self.timerWindow=TimerWindow(self)
        
        self.timerWindow.timerstarted.connect(self.timerStarted)
        self.timerWindow.timerstopped.connect(self.timerStopped)
        self.timerWindow.timercountdown.connect(self.timerCountdown)
        self.timerWindow.timerfired.connect(self.timerFired)
        self.timerStatus = QLabel("Timer stopped ")
        self.statusBar().addPermanentWidget(self.timerStatus)        
        self.toolbar=Toolbar(parent=self,mainWindow=self)
        self.addToolBar(Qt.TopToolBarArea,self.toolbar)    
        
        self.selectionStatus = QLabel("0 node(s) selected ")
        self.statusBar().addPermanentWidget(self.selectionStatus)        
        self.statusBar().showMessage('No database connection')
        self.statusBar().setSizeGripEnabled(False)       
        
        #dummy widget to contain the layout manager
        #self.mainWidget=QWidget(self) 
        self.mainWidget=QSplitter(self)
        self.mainWidget.setOrientation(Qt.Vertical)        
        self.setCentralWidget(self.mainWidget)        
        
        #top widget
        topWidget=QWidget(self)
        self.mainWidget.addWidget(topWidget)

        bottomWidget=QWidget(self)
        self.mainWidget.addWidget(bottomWidget)
        self.mainWidget.setStretchFactor(0, 1);
        
        #mainLayout=QVBoxLayout()
        #self.mainWidget.setLayout(mainLayout)                
         
         
        dataLayout=QHBoxLayout()
        topWidget.setLayout(dataLayout)
        dataSplitter = QSplitter(self)
        dataLayout.addWidget(dataSplitter)
        
        requestLayout=QHBoxLayout()
        bottomWidget.setLayout(requestLayout)

         
        #tree                                                        
        self.tree=DataTree(self.mainWidget,self)
        dataSplitter.addWidget(self.tree)
        dataSplitter.setStretchFactor(0, 1);

        
        #right sidebar
        detailWidget=QWidget()
        detailLayout=QVBoxLayout()
        detailLayout.setContentsMargins(11,0,0,11)
        detailWidget.setLayout(detailLayout)
        dataSplitter.addWidget(detailWidget)        
        dataSplitter.setStretchFactor(1, 0);
     
        self.detailTree=DictionaryTree(self.mainWidget,self)
        detailLayout.addWidget(self.detailTree)

        buttonLayout=QHBoxLayout()
        detailLayout.addLayout(buttonLayout)
        
        button=QPushButton("Add Column")
        button.clicked.connect(self.actions.actionAddColumn.trigger)
        buttonLayout.addWidget(button)

        button=QPushButton("Unpack list")
        button.clicked.connect(self.actions.actionUnpack.trigger)
        buttonLayout.addWidget(button)   
        
        #requests
        actionlayout=QVBoxLayout()
        requestLayout.addLayout(actionlayout,1)
        
        self.RequestTabs=QTabWidget()
        actionlayout.addWidget(self.RequestTabs)        
        loadTabs(self)
        
    
        #fetch data      
        f=QFont()
        f.setPointSize(11)

                                     
        fetchdata=QHBoxLayout()
        fetchdata.setContentsMargins(10,0,10,0)
        actionlayout.addLayout(fetchdata)        
        #fetchdata.addStretch(1)                         
                                    
        #-Level
        self.levelEdit=QSpinBox(self.mainWidget)
        self.levelEdit.setMinimum(1)
        self.levelEdit.setFont(f)
        self.levelEdit.setMinimumHeight(35)
        label=QLabel("For all selected nodes and \ntheir children of level")
        #label.setFont(f)    
 
        #label.setWordWrap(True)
        #label.setMaximumWidth(100)
        fetchdata.addWidget(label,0)
        fetchdata.addWidget(self.levelEdit,0)
        
        #-button
        button=QPushButton(QIcon(":/icons/fetch.png"),"Fetch Data", self.mainWidget)
        button.setMinimumSize(QSize(120,40))
        button.setIconSize(QSize(32,32))
        button.clicked.connect(self.actions.actionQuery.trigger)
        button.setFont(f)
        fetchdata.addWidget(button,1)
        
        #-timer button
        button=QToolButton(self.mainWidget)
        button.setIcon(QIcon(":/icons/timer.png"))
        button.setMinimumSize(QSize(40,40))
        button.setIconSize(QSize(25,25))
        button.clicked.connect(self.actions.actionTimer.trigger)
        fetchdata.addWidget(button,1)
        
        #Status
        statusLayout=QVBoxLayout()        
        requestLayout.addLayout(statusLayout,2)

        detailGroup=QGroupBox("Status Log")
        groupLayout=QVBoxLayout()
        detailGroup.setLayout(groupLayout)
        statusLayout.addWidget(detailGroup,1)
                
        self.loglist=QTextEdit()
        self.loglist.setLineWrapMode(QTextEdit.NoWrap)
        self.loglist.setWordWrapMode(QTextOption.NoWrap)
        self.loglist.acceptRichText=False
        self.loglist.clear()
        groupLayout.addWidget(self.loglist)

        #fields
        detailGroup=QGroupBox("Custom Table Columns (one key per line)")
        requestLayout.addWidget(detailGroup)
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
       
        self.fieldList.setPlainText(self.settings.value('columns',self.fieldList.toPlainText()))       
                    
        groupLayout.addWidget(self.fieldList)        
                
        button=QPushButton("Apply Column Setup")
        button.clicked.connect(self.actions.actionShowColumns.trigger)
        groupLayout.addWidget(button)           
                
    def updateUI(self):
        #disable buttons that do not work without an opened database                   
        self.actions.databaseActions.setEnabled(self.database.connected)
        
        if self.database.connected:
            self.statusBar().showMessage(self.database.filename)
        else:
            self.statusBar().showMessage('No database connection')    
   
    @Slot()     
    def timerStarted(self,time):
        self.timerStatus.setStyleSheet("QLabel {color:red;}")
        self.timerStatus.setText("Timer will be fired at "+time.toString("d MMM yyyy - hh:mm")+" ")

    @Slot()
    def timerStopped(self):
        self.timerStatus.setStyleSheet("QLabel {color:black;}")
        self.timerStatus.setText("Timer stopped ")

    @Slot()
    def timerCountdown(self,countdown):
        self.timerStatus.setStyleSheet("QLabel {color:red;}")
        self.timerStatus.setText("Timer will be fired in "+str(countdown)+ " seconds ")
        
    @Slot()
    def timerFired(self,data):        
        self.timerStatus.setText("Timer fired ")
        self.timerStatus.setStyleSheet("QLabel {color:red;}")
        self.actions.queryNodes(data.get('indexes',[]),data.get('module',None),data.get('options',{}).copy() )
        
        
        
    def writeSettings(self):
        QCoreApplication.setOrganizationName("Keyling")
        QCoreApplication.setApplicationName("Facepager")

        self.settings = QSettings()        
        self.settings.beginGroup("MainWindow")
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())        
        self.settings.setValue("version","3.0")
        self.settings.endGroup()
        
        self.settings.setValue('columns',self.fieldList.toPlainText())
        
        for i in range(self.RequestTabs.count()):
            self.RequestTabs.widget(i).saveSettings()
        
    def readSettings(self):
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QCoreApplication.setOrganizationName("Keyling")
        QCoreApplication.setApplicationName("Facepager")
        self.settings = QSettings()        
        self.settings.beginGroup("MainWindow")
        
        #self.resize(self.settings.value("size", QSize(800, 800)))
        #self.move(self.settings.value("pos", QPoint(200, 10)))
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
            
    @Slot(str)        
    def logmessage(self,message):
        self.loglist.append(str(datetime.now())+" "+message)
        QApplication.processEvents()            

    def showProgress(self,current = None,maximum = None,message = None):                
        if not hasattr(self, 'progresswindow') or (self.progresswindow is None):
            if message == None: message = ""
            self.progresswindow = QProgressDialog(message, "Abort", 0, 0,self)
            self.progresswindow.setWindowModality(Qt.WindowModal)
            self.progresswindow.setMinimumDuration(0)
            self.progresswindow.forceShow()
        
        if maximum != None: self.progresswindow.setMaximum(maximum)                           
        if current != None: self.progresswindow.setValue(current)
        if message != None: self.progresswindow.setLabelText(message)
        QApplication.processEvents()
            
    
    def progressCanceled(self):
        return (not self.progresswindow) or (self.progresswindow.wasCanceled()) 
        
    def hideProgress(self):
        self.progresswindow.cancel()
        self.progresswindow = None
        
        
                 
class Toolbar(QToolBar):
    '''
    Initialize the main toolbar for the facepager - that provides the central interface and functions.
    '''
    def __init__(self,parent=None,mainWindow=None):
        super(Toolbar,self).__init__(parent)
        self.mainWindow=mainWindow
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);
        self.setIconSize(QSize(24,24))
        
        self.addActions(self.mainWindow.actions.basicActions.actions())        
        self.addSeparator()
        self.addActions(self.mainWindow.actions.databaseActions.actions())
        
        self.addSeparator()
        self.addAction(self.mainWindow.actions.actionExpandAll)        
        self.addAction(self.mainWindow.actions.actionCollapseAll)
        self.addAction(self.mainWindow.actions.actionLoadPreset)
        self.addAction(self.mainWindow.actions.actionHelp)
    

            
def startMain():
    app = QApplication(sys.argv)

    main=MainWindow()    
    main.show()
    
    sys.exit(app.exec_())    

  
if __name__ == "__main__":
    #cProfile.run('startMain()')
    startMain()

