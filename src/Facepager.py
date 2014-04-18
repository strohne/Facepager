#import yappi
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
from selectnodes import *
import logging
import threading

class MainWindow(QMainWindow):

    def __init__(self,central=None):
        super(MainWindow,self).__init__()

        self.setWindowTitle("Facepager 3.5")
        self.setWindowIcon(QIcon(":/icons/icon_facepager.png"))
        self.setMinimumSize(900,700)
        self.move(QDesktopWidget().availableGeometry().center() - self.frameGeometry().center()-QPoint(0,100))
#        self.setStyleSheet("* {font-size:27px;}")
        #self.deleteSettings()
        self.lock_logging = threading.Lock()
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
        #self.selectNodesWindow=SelectNodesWindow(self,self.tree)

        self.timerWindow.timerstarted.connect(self.actions.timerStarted)
        self.timerWindow.timerstopped.connect(self.actions.timerStopped)
        self.timerWindow.timercountdown.connect(self.actions.timerCountdown)
        self.timerWindow.timerfired.connect(self.actions.timerFired)
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
        dataWidget=QWidget()
        dataLayout=QVBoxLayout()
        dataLayout.setContentsMargins(0,0,0,0)
        dataWidget.setLayout(dataLayout)
        dataSplitter.addWidget(dataWidget)
        dataSplitter.setStretchFactor(0, 1);

        treetoolbar = QToolBar(self)
        treetoolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);
        treetoolbar.setIconSize(QSize(16,16))

        treetoolbar.addActions(self.actions.treeActions.actions())
        dataLayout.addWidget (treetoolbar)

        self.tree=DataTree(self.mainWidget)
        self.tree.nodeSelected.connect(self.actions.treeNodeSelected)
        dataLayout.addWidget(self.tree)


        #button=QToolButton(self.mainWidget)
        #button.setIcon(QIcon(":/icons/timer.png"))


        #right sidebar
        detailWidget=QWidget()
        detailLayout=QVBoxLayout()
        detailLayout.setContentsMargins(11,0,0,0)
        detailWidget.setLayout(detailLayout)
        dataSplitter.addWidget(detailWidget)
        dataSplitter.setStretchFactor(1, 0);

        detailtoolbar = QToolBar(self)
        detailtoolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);
        detailtoolbar.setIconSize(QSize(16,16))

        detailtoolbar.addActions(self.actions.detailActions.actions())
        detailLayout.addWidget (detailtoolbar)

        self.detailTree=DictionaryTree(self.mainWidget)
        detailLayout.addWidget(self.detailTree)


        #requests
        actionlayout=QVBoxLayout()
        requestLayout.addLayout(actionlayout,1)

        self.RequestTabs=QTabWidget()
        actionlayout.addWidget(self.RequestTabs)
        self.RequestTabs.addTab(FacebookTab(self),"Facebook")
        self.RequestTabs.addTab(TwitterTab(self),"Twitter")
        self.RequestTabs.addTab(GenericTab(self),"Generic")
        self.RequestTabs.addTab(FilesTab(self),"Files")
        self.RequestTabs.addTab(TwitterStreamingTab(self),"Twitter Streaming")

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
        button.setToolTip("Fetch data from the API with the current settings")
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
        button.setToolTip("Apply the columns to the cental data view. New columns may be hidden and are appended on the right side")
        button.clicked.connect(self.actions.actionShowColumns.trigger)
        groupLayout.addWidget(button)

    def updateUI(self):
        #disable buttons that do not work without an opened database
        self.actions.databaseActions.setEnabled(self.database.connected)

        if self.database.connected:
            self.statusBar().showMessage(self.database.filename)
        else:
            self.statusBar().showMessage('No database connection')


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
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QCoreApplication.setOrganizationName("Keyling")
        QCoreApplication.setApplicationName("Facepager")
        self.settings = QSettings()

        self.settings.clear()
        self.settings.sync()

        #self.settings.beginGroup("ApiModule_Facebook")
        #print self.settings.allKeys()

#         self.settings.beginGroup("MainWindow")
#         self.settings.remove("")
#         self.settings.endGroup()
#         self.settings.remove("lastpath")

    def closeEvent(self, event=QCloseEvent()):
        if self.close():
            self.writeSettings()
            event.accept()
        else:
            event.ignore()

    @Slot(str)
    def logmessage(self,message):
        with self.lock_logging:
            if isinstance(message,Exception):
                self.loglist.append(str(datetime.now())+" Exception: "+str(message))
                logging.exception(message)

            else:
                self.loglist.append(str(datetime.now())+" "+message)


class Toolbar(QToolBar):
    """
    Initialize the main toolbar for the facepager - that provides the central interface and functions.
    """
    def __init__(self,parent=None,mainWindow=None):
        super(Toolbar,self).__init__(parent)
        self.mainWindow=mainWindow
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);
        self.setIconSize(QSize(24,24))

        self.addActions(self.mainWindow.actions.basicActions.actions())
        self.addSeparator()
        self.addActions(self.mainWindow.actions.databaseActions.actions())

        self.addSeparator()
        #self.addAction(self.mainWindow.actions.actionExpandAll)
        #self.addAction(self.mainWindow.actions.actionCollapseAll)
        #self.addAction(self.mainWindow.actions.actionSelectNodes)
        self.addAction(self.mainWindow.actions.actionLoadPreset)
        self.addAction(self.mainWindow.actions.actionHelp)



def startMain():
    app = QApplication(sys.argv)

    main=MainWindow()
    main.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    try:
        logfolder = os.path.join(os.path.expanduser("~"),'Facepager','Logs')
        if not os.path.isdir(logfolder):
            os.makedirs(logfolder)
        logging.basicConfig(filename=os.path.join(logfolder,'facepager.log'),level=logging.ERROR,format='%(asctime)s %(levelname)s:%(message)s')
    except Exception as e:
        print u"Error intitializing log file: {}".format(e.message)
    finally:
        #cProfile.run('startMain()')
        #yappi.start()
        startMain()
        #yappi.print_stats()


