#!/usr/bin/env python
"""Facepager was made for fetching public available data from Facebook, Twitter and other JSON-based API. All data is stored in a SQLite database and may be exported to csv. """

# MIT License

# Copyright (c) 2016 Till Keyling and Jakob Jünger

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


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

        self.setWindowTitle("Facepager 3.8")
        self.setWindowIcon(QIcon(":/icons/icon_facepager.png"))

        # This is needed to display the app icon on the taskbar on Windows 7
        if os.name == 'nt':
            import ctypes
            myappid = 'Facepager.3.8' # arbitrary string
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        self.setMinimumSize(800,600)
        #self.setMinimumSize(1400,710)
        #self.move(QDesktopWidget().availableGeometry().center() - self.frameGeometry().center()-QPoint(0,100))
        #self.setStyleSheet("* {font-size:21px;}")
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
        #
        #  Windows
        #

        self.helpwindow=HelpWindow(self)
        self.presetWindow=PresetWindow(self)
        self.timerWindow=TimerWindow(self)
        #self.selectNodesWindow=SelectNodesWindow(self,self.tree)

        self.timerWindow.timerstarted.connect(self.actions.timerStarted)
        self.timerWindow.timerstopped.connect(self.actions.timerStopped)
        self.timerWindow.timercountdown.connect(self.actions.timerCountdown)
        self.timerWindow.timerfired.connect(self.actions.timerFired)

        #
        #  Statusbar and toolbar
        #

        self.statusbar = self.statusBar()
        self.toolbar=Toolbar(parent=self,mainWindow=self)
        self.addToolBar(Qt.TopToolBarArea,self.toolbar)

        self.timerStatus = QLabel("Timer stopped ")
        self.statusbar.addPermanentWidget(self.timerStatus)

        self.databaseLabel = QLabel("No database connection ")
        #self.databaseLabel.clicked.connect(self.actions.openDBFolder)
        self.statusbar.addWidget(self.databaseLabel)

        self.selectionStatus = QLabel("0 node(s) selected ")
        self.statusbar.addPermanentWidget(self.selectionStatus)
        #self.statusBar.showMessage('No database connection')
        self.statusbar.setSizeGripEnabled(False)

        #
        #  Layout
        #

        #dummy widget to contain the layout manager
        self.mainWidget=QSplitter(self)
        self.mainWidget.setOrientation(Qt.Vertical)
        self.setCentralWidget(self.mainWidget)

        #top
        topWidget=QWidget(self)
        self.mainWidget.addWidget(topWidget)
        dataLayout=QHBoxLayout()
        topWidget.setLayout(dataLayout)
        dataSplitter = QSplitter(self)
        dataLayout.addWidget(dataSplitter)

        #top left
        dataWidget=QWidget()
        dataLayout=QVBoxLayout()
        dataLayout.setContentsMargins(0,0,0,0)
        dataWidget.setLayout(dataLayout)
        dataSplitter.addWidget(dataWidget)
        dataSplitter.setStretchFactor(0, 1);

        #top right
        detailWidget=QWidget()
        detailLayout=QVBoxLayout()
        detailLayout.setContentsMargins(11,0,0,0)
        detailWidget.setLayout(detailLayout)
        dataSplitter.addWidget(detailWidget)
        dataSplitter.setStretchFactor(1, 0);

        #bottom
        bottomWidget=QWidget(self)
        self.mainWidget.addWidget(bottomWidget)
        self.mainWidget.setStretchFactor(0, 1);

        requestLayout=QHBoxLayout()
        bottomWidget.setLayout(requestLayout)

        #bottom left
        moduleslayout=QVBoxLayout()
        requestLayout.addLayout(moduleslayout,1)

        #bottom middle
        fetchLayout=QVBoxLayout()
        requestLayout.addLayout(fetchLayout,1)

        settingsGroup=QGroupBox("Settings")
        fetchLayout.addWidget(settingsGroup)

        fetchsettings = QFormLayout()
        fetchsettings.setRowWrapPolicy(QFormLayout.DontWrapRows)
        fetchsettings.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        fetchsettings.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        fetchsettings.setLabelAlignment(Qt.AlignLeft)
        settingsGroup.setLayout(fetchsettings)
        #fetchLayout.addLayout(fetchsettings)

        fetchdata=QHBoxLayout()
        fetchdata.setContentsMargins(10,0,10,0)
        fetchLayout.addLayout(fetchdata)

        #bottom right
        statusLayout=QVBoxLayout()
        requestLayout.addLayout(statusLayout,2)

        #
        #  Components
        #

        #main tree
        treetoolbar = QToolBar(self)
        treetoolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);
        treetoolbar.setIconSize(QSize(16,16))

        treetoolbar.addActions(self.actions.treeActions.actions())
        dataLayout.addWidget (treetoolbar)

        self.tree=DataTree(self.mainWidget)
        self.tree.nodeSelected.connect(self.actions.treeNodeSelected)
        dataLayout.addWidget(self.tree)


        #right sidebar - toolbar
        detailtoolbar = QToolBar(self)
        detailtoolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);
        detailtoolbar.setIconSize(QSize(16,16))
        detailtoolbar.addActions(self.actions.detailActions.actions())
        detailLayout.addWidget (detailtoolbar)

        #right sidebar - json viewer
        self.detailTree=DictionaryTree(self.mainWidget)
        detailLayout.addWidget(self.detailTree,2)

        #right sidebar - column setup
        detailGroup=QGroupBox("Custom Table Columns (one key per line)")
        detailLayout.addWidget(detailGroup,1)
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
        button.setToolTip("Apply the columns to the central data view. New columns may be hidden and are appended on the right side")
        button.clicked.connect(self.actions.actionShowColumns.trigger)
        groupLayout.addWidget(button)


        #Requests/Apimodules
        self.RequestTabs=QTabWidget()
        moduleslayout.addWidget(self.RequestTabs)
        self.RequestTabs.addTab(FacebookTab(self),"Facebook")
        self.RequestTabs.addTab(TwitterTab(self),"Twitter")
        self.RequestTabs.addTab(GenericTab(self),"Generic")
        self.RequestTabs.addTab(FilesTab(self),"Files")
        self.RequestTabs.addTab(TwitterStreamingTab(self),"Twitter Streaming")


        #Fetch settings


        #-Level
        self.levelEdit=QSpinBox(self.mainWidget)
        self.levelEdit.setMinimum(1)
        self.levelEdit.setToolTip("Based on the selected nodes, only fetch data for nodes and subnodes of the specified level (base level is 1)")
        fetchsettings.addRow("Node level",self.levelEdit)

        #Object types
        self.typesEdit = QLineEdit('seed,data,unpacked')
        self.typesEdit.setToolTip("Based on the selected nodes, only fetch data for nodes with one of the listed object types (normally should not be changed)")
        fetchsettings.addRow("Object types",self.typesEdit)

        # Thread Box
        self.threadsEdit = QSpinBox(self)
        self.threadsEdit.setMinimum(1)
        self.threadsEdit.setMaximum(10)
        self.threadsEdit.setToolTip("The number of concurrent threads performing the requests. Higher values increase the speed, but may result in API-Errors/blocks")
        fetchsettings.addRow("Parallel Threads", self.threadsEdit)

        # Speed Box
        self.speedEdit = QSpinBox(self)
        self.speedEdit.setMinimum(1)
        self.speedEdit.setMaximum(60000)
        self.speedEdit.setValue(200)
        self.speedEdit.setToolTip("Limit the total amount of requests per minute (calm down to avoid API blocking)")
        fetchsettings.addRow("Requests per minute", self.speedEdit)


        #Error Box
        self.errorEdit = QSpinBox(self)
        self.errorEdit.setMinimum(1)
        self.errorEdit.setMaximum(10)
        self.errorEdit.setValue(3)
        self.errorEdit.setToolTip("Set the number of consecutive errors after which fetching will be cancelled. Please handle with care! Continuing with erroneous requests places stress on the servers.")
        fetchsettings.addRow("Maximum errors", self.errorEdit)

        #Log Setttings
        self.logCheckbox = QCheckBox(self)
        self.logCheckbox.setCheckState(Qt.Checked)
        self.logCheckbox.setToolTip("Check to see every request in status window; uncheck to hide request messages.")
        fetchsettings.addRow("Log all requests", self.logCheckbox)


        #Fetch data

        #-button
        f=QFont()
        f.setPointSize(11)
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


    def updateUI(self):
        #disable buttons that do not work without an opened database
        self.actions.databaseActions.setEnabled(self.database.connected)

        if self.database.connected:
            #self.statusBar().showMessage(self.database.filename)
            self.databaseLabel.setText(self.database.filename)
        else:
            #self.statusBar().showMessage('No database connection')
            self.databaseLabel.setText('No database connection')


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
            time.sleep(0)

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


