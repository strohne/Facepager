from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QActionGroup

from datetime import datetime, timedelta
import csv
from copy import deepcopy
from widgets.progressbar import ProgressBar
from database import *
from apimodules import *
from apithread import ApiThreadPool
from collections import defaultdict
import io
import os
import json
import threading

from dialogs.export import ExportFileDialog
if sys.version_info.major < 3:
    from urllib import pathname2url
else:
    from urllib.request import pathname2url

class ApiActions(object):
    """
    Actions called by GuiActions or Http clients
    """
    def __init__(self, mainWindow):
        self.mainWindow = mainWindow
        self.state = "idle"
        self.lock = threading.Lock()

    """ Only execute one action at a time"""
    def blockState(func):
        def wrapper(self, *args, **kwargs):
            if self.lock.acquire(False):
                try:
                    self.state = func.__name__
                    result = func(self, *args, **kwargs)
                finally:
                    self.state = "idle"
                    self.lock.release()

                return result

            else:
                self.mainWindow.logmessage("Call of {} skipped because the operation {} is still active.".format(func.__name__, self.state))
                return None
        return wrapper

    """ Return current action name """
    def getState(self):
        return self.state

    # Blocking methods
    @blockState
    def openDatabase(self, filename):
        # Don't create new databases
        if not os.path.isfile(filename):
            return False

        self.mainWindow.timerWindow.cancelTimer()
        self.mainWindow.tree.treemodel.clear()
        self.mainWindow.database.connect(filename)
        self.mainWindow.updateUI()

        self.mainWindow.tree.loadData(self.mainWindow.database)
        self.mainWindow.guiActions.actionShowColumns.trigger()
        return True

    @blockState
    def createDatabase(self, filename, overwrite=False):
        # Don't overwrite existing files
        if os.path.isfile(filename) and not overwrite:
            return False

        self.mainWindow.timerWindow.cancelTimer()
        self.mainWindow.tree.treemodel.clear()
        self.mainWindow.database.createconnect(filename)
        self.mainWindow.updateUI()
        return True


    @blockState
    def applySettings(self, settings={}):
        # Find API module
        module = settings.get('module', '')
        module = 'Generic' if module == 'Files' else module

        tab = self.mainWindow.getModule(module)
        if tab is not None:
            tab.setSettings(settings.get('options', {}))
            self.mainWindow.RequestTabs.setCurrentWidget(tab)

        # Set columns
        columns = settings.get('columns')
        if columns is not None:
            self.mainWindow.fieldList.setPlainText("\n".join(columns))
            self.mainWindow.guiActions.showColumns()

        # Set global settings
        tab.setGlobalOptions(settings)

        return True

    @blockState
    def addColumns(self, settings={}):
        newcolumns = settings.get('columns')
        columns = self.mainWindow.fieldList.toPlainText().splitlines()

        if newcolumns is not None:
            columns.extend([x for x in newcolumns if not x in columns])
            columns = [x.strip() for x in columns]
            columns = [x for x in columns if x != '']

            self.mainWindow.fieldList.setPlainText("\n".join(columns))
            self.mainWindow.tree.treemodel.setCustomColumns(columns)

        return True

    def loadPreset(self, filename):
        with open(filename, 'r', encoding="utf-8") as input:
            settings = json.load(input)
            return self.applySettings(settings)

    @blockState
    def addNodes(self, newnodes=[]):
        self.mainWindow.tree.treemodel.addSeedNodes(newnodes, True)
        self.mainWindow.tree.selectLastRow()
        return True

    @blockState
    def addCsv(self, filename, updateProgress=None):
        progress = ProgressBar("Adding nodes...", self.mainWindow)
        try:

            with open(filename, encoding="UTF-8-sig") as csvfile:
                rows = csv.DictReader(csvfile, delimiter=';', quotechar='"', doublequote=True)
                self.mainWindow.tree.treemodel.addSeedNodes(rows, progress=updateProgress)
                self.mainWindow.tree.selectLastRow()

            self.mainWindow.tree.selectLastRow()
        finally:
            progress.close()

    @blockState
    def fetchData(self, indexes=None, apimodule=False, options=None):
        # Check seed nodes
        if not (self.mainWindow.tree.selectedCount() or self.mainWindow.allnodesCheckbox.isChecked() or (indexes is not None)):
            return False

        # Get options
        apimodule, options = self.getQueryOptions(apimodule, options)
        if not apimodule.auth_userauthorized and apimodule.auth_preregistered:
            msg = 'You are not authorized, login please!'
            QMessageBox.critical(self.mainWindow, "Not authorized",msg,QMessageBox.StandardButton.Ok)
            return False

        #Show progress window
        progress = ProgressBar("Fetching Data", parent=self.mainWindow)

        try:
            # Get seed nodes
            indexes = self.getIndexes(options, indexes, progress)

            # Update progress window
            self.mainWindow.logmessage("Start fetching data.")
            totalnodes = 0
            hasindexes = True
            progress.setMaximum(totalnodes)
            self.mainWindow.tree.treemodel.nodecounter = 0

            #Init status messages
            statuscount = defaultdict(int)
            errorcount = 0
            ratelimitcount = 0
            allowedstatus = ['fetched (200)','downloaded (200)','fetched (202)']

            try:
                #Spawn Threadpool
                threadpool = ApiThreadPool(apimodule)
                threadpool.spawnThreads(options.get("threads", 1))

                #Process Logging/Input/Output Queue
                while True:
                    try:
                        #Logging (sync logs in threads with main thread)
                        msg = threadpool.getLogMessage()
                        if msg is not None:
                            self.mainWindow.logmessage(msg)

                        # Jobs in: packages of 100 at a time
                        jobsin = 0
                        while hasindexes and (jobsin < 100):
                            index = next(indexes, False)
                            if index:
                                jobsin += 1
                                totalnodes += 1
                                if index.isValid():
                                    job = self.prepareJob(index, options)
                                    threadpool.addJob(job)
                            else:
                                threadpool.applyJobs()
                                progress.setRemaining(threadpool.getJobCount())
                                progress.resetRate()
                                hasindexes = False
                                progress.removeInfo('input')
                                self.mainWindow.logmessage("Added {} node(s) to queue.".format(totalnodes))

                        if jobsin > 0:
                            progress.setMaximum(totalnodes)

                        #Jobs out
                        job = threadpool.getJob()

                        #-Finished all nodes (sentinel)...
                        if job is None:
                            break

                        #-Finished one node...
                        elif 'progress' in job:
                            progresskey = 'nodeprogress' + str(job.get('threadnumber', ''))

                            # Update single progress
                            if 'current' in job:
                                percent = int((job.get('current',0) * 100.0 / job.get('total',1)))
                                progress.showInfo(progresskey, "{}% of current node processed.".format(percent))
                            elif 'page' in job:
                                if job.get('page', 0) > 1:
                                    progress.showInfo(progresskey, "{} page(s) of current node processed.".format(job.get('page',0)))

                            # Update total progress
                            else:
                                progress.removeInfo(progresskey)
                                if not threadpool.suspended:
                                    progress.step()

                        #-Add data...
                        elif 'data' in job and (not progress.wasCanceled):
                            if not job['nodeindex'].isValid():
                                continue

                            # Add data
                            treeindex = job['nodeindex']
                            treenode = treeindex.internalPointer()

                            newcount = treenode.appendNodes(job['data'], job['options'], True)
                            if options.get('expand',False):
                                 self.mainWindow.tree.setExpanded(treeindex,True)

                            # Count status and errors
                            status = job['options'].get('querystatus', 'empty')
                            statuscount[status] += 1
                            errorcount += int(not status in allowedstatus)

                            # Detect rate limit
                            ratelimit = job['options'].get('ratelimit', False)
                            #ratelimit = ratelimit or (not newcount)
                            ratelimitcount += int(ratelimit)
                            autoretry = (ratelimitcount) or (status == "request error")

                            # Clear errors when everything is ok
                            if not threadpool.suspended and (status in allowedstatus) and (not ratelimit):
                                #threadpool.clearRetry()
                                errorcount = 0
                                ratelimitcount = 0
                                self.state = 'fetchdata'

                            # Suspend on error or ratelimit
                            elif (errorcount >= options['errors']) or (ratelimitcount > 0):
                                threadpool.suspendJobs()
                                self.state = 'ratelimit'

                                if ratelimit:
                                    msg = "You reached the rate limit of the API."
                                else:
                                    msg = "{} consecutive errors occurred.\nPlease check your settings.".format(errorcount)

                                timeout = 60 * 5 # 5 minutes

                                # Adjust progress
                                progress.showError(msg, timeout, autoretry)
                                self.mainWindow.tree.treemodel.commitNewNodes()

                            # Add job for retry
                            if not status in allowedstatus:
                                threadpool.addError(job)

                            # Show info
                            progress.showInfo(status,"{} response(s) with status: {}".format(statuscount[status],status))
                            progress.showInfo('newnodes',"{} new node(s) created".format(self.mainWindow.tree.treemodel.nodecounter))
                            progress.showInfo('threads',"{} active thread(s)".format(threadpool.getThreadCount()))
                            progress.setRemaining(threadpool.getJobCount())

                            # Custom info from modules
                            info = job['options'].get('info', {})
                            for name, value in info.items():
                                progress.showInfo(name, value)

                        # Abort
                        elif progress.wasCanceled:
                            progress.showInfo('cancel', "Disconnecting from stream, may take some time.")
                            threadpool.stopJobs()

                        # Retry
                        elif progress.wasResumed:
                            if progress.wasRetried:
                                threadpool.retryJobs()
                            else:
                                threadpool.clearRetry()
                                # errorcount = 0
                                # ratelimitcount = 0
                                threadpool.resumeJobs()

                            progress.setRemaining(threadpool.getJobCount())
                            progress.hideError()

                        # Continue
                        elif not threadpool.suspended:
                            threadpool.resumeJobs()

                        # Finished with pending errors
                        if not threadpool.hasJobs() and threadpool.hasErrorJobs():
                            msg = "All nodes finished but you have {} pending errors. Skip or retry?".format(threadpool.getErrorJobsCount())
                            autoretry = False
                            timeout = 60 * 5  # 5 minutes
                            progress.showError(msg, timeout, autoretry)

                        # Finished
                        if not threadpool.hasJobs():
                            progress.showInfo('cancel', "Work finished, shutting down threads.")
                            threadpool.stopJobs()

                        #-Waiting...
                        progress.computeRate()
                        time.sleep(1.0 / 1000.0)
                    finally:
                        QApplication.processEvents()

            finally:
                request_summary = [str(val)+" x "+key for key,val in statuscount.items()]
                request_summary = ", ".join(request_summary)
                request_end = "Fetching completed" if not progress.wasCanceled else 'Fetching cancelled by user'

                self.mainWindow.logmessage("{}, {} new node(s) created. Summary of responses: {}.".format(request_end, self.mainWindow.tree.treemodel.nodecounter,request_summary))

                self.mainWindow.tree.treemodel.commitNewNodes()
        except Exception as e:
            self.mainWindow.logmessage("Error in scheduler, fetching aborted: {}.".format(str(e)))
        finally:
            progress.close()
            return not progress.wasCanceled

    # Non-blocking methods (that may call blocking methods)
    def getDatabaseName(self):
        return (self.mainWindow.database.filename)

    def queryPipeline(self, pipeline, indexes=None):
        columns = []
        for preset in pipeline:
            # Select item in preset window
            item = preset.get('item')
            if item is not None:
                self.mainWindow.presetWindow.presetList.setCurrentItem(item)

            columns.extend(preset.get('columns', []))
            module = preset.get('module')
            options = preset.get('options')
            finished = self.fetchData(indexes, module, options)

            # todo: increase level of indexes instead of levelEdit
            if not finished or (indexes is not None):
                return False
            else:
                level = self.mainWindow.levelEdit.value()
                self.mainWindow.levelEdit.setValue(level + 1)

        # Set columns
        columns = list(dict.fromkeys(columns))
        self.mainWindow.fieldList.setPlainText("\n".join(columns))
        self.showColumns()



    def getPresetOptions(self):
        apimodule = self.mainWindow.RequestTabs.currentWidget()

        # Get global options
        settings = apimodule.getGlobalOptions()
        settings['module'] = apimodule.name

        # Columns
        settings['columns'] = self.mainWindow.fieldList.toPlainText().splitlines()

        # Module options
        settings['options'] = apimodule.getSettings('preset')

        return settings

    def getQueryOptions(self, apimodule=False, options=None):
        # Get module option
        if isinstance(apimodule, str):
            apimodule = self.mainWindow.getModule(apimodule)
        if apimodule == False:
            apimodule = self.mainWindow.RequestTabs.currentWidget()

        # Get global options
        globaloptions = apimodule.getGlobalOptions()

        apimodule.getProxies(True)

        if options is None:
            options = apimodule.getSettings('fetch')
        else:
            options = options.copy()
        options.update(globaloptions)

        return (apimodule, options)

    def getIndexes(self, options= {}, indexes=None, progress=None):
        # Get selected nodes
        if indexes is None:
            objecttypes = self.mainWindow.typesEdit.text().replace(' ', '').split(',')
            level = self.mainWindow.levelEdit.value() - 1
            select_all = options['allnodes']
            select_filter = {'level': level, '!objecttype': objecttypes}
            conditions = {'filter': select_filter,
                          'selectall': select_all,
                          'options': options}

            self.progressUpdate = datetime.now()
            def updateProgress(current, total, level=0):
                if not progress:
                    return True

                if datetime.now() >= self.progressUpdate:
                    progress.showInfo('input', "Adding nodes to queue ({}/{}).".format(current, total))
                    QApplication.processEvents()
                    self.progressUpdate = datetime.now() + timedelta(milliseconds=60)

                return not progress.wasCanceled

            indexes = self.mainWindow.tree.selectedIndexesAndChildren(conditions, updateProgress)

        elif isinstance(indexes, list):
            indexes = iter(indexes)

        return indexes

    # Copy node data and options
    def prepareJob(self, index, options):
        treenode = index.internalPointer()
        node_data = deepcopy(treenode.data)
        node_options = deepcopy(options)
        node_options['lastdata'] = treenode.lastdata if hasattr(treenode, 'lastdata') else None

        job = {'nodeindex': index,
               'nodedata': node_data,
               'options': node_options}

        return job

class ServerActions(object):
    """
    Actions triggered by the web server
    """

    def __init__(self, mainWindow, apiActions):
        self.mainWindow = mainWindow
        self.apiActions = apiActions

    @Slot()
    def action(self, action, filename, payload):
        try:
            if action == "opendatabase":
                self.apiActions.openDatabase(filename)
            elif action == "createdatabase":
                self.apiActions.createDatabase(filename)
            elif action == "loadpreset":
                self.apiActions.loadPreset(filename)
            elif action == "applysettings":
                self.apiActions.applySettings(payload)
            elif action == "addcsv":
                self.apiActions.addCsv(filename)
            elif action == "addnodes":
                self.apiActions.addNodes(payload)
            elif action == "fetchdata":
                self.apiActions.fetchData()
            else:
                self.mainWindow.logmessage("Invalid action from remote control.")
        except Exception as e:
            self.mainWindow.logmessage("Invalid request from remote control.")

    def getState(self, snippets=None):
        response = {}
        response['database'] = self.apiActions.getDatabaseName()
        response['state'] = self.apiActions.getState()

        if snippets == 'settings':
            options = self.apiActions.getPresetOptions()
            response['settings'] = options
        elif snippets == 'log':
            response['log'] = self.mainWindow.getlog()

        return response


class GuiActions(object):
    """
    Actions triggered by the user interface (buttons)
    """
    def __init__(self, mainWindow, apiActions):

        self.mainWindow = mainWindow
        self.apiActions = apiActions

        #Basic actions
        self.basicActions = QActionGroup(self.mainWindow)
        self.actionOpen = self.basicActions.addAction(QIcon(":/icons/save.png"), "Open Database")
        self.actionOpen.triggered.connect(self.openDB)

        self.actionNew = self.basicActions.addAction(QIcon(":/icons/new.png"), "New Database")
        self.actionNew.triggered.connect(self.makeDB)

        #Database actions
        self.databaseActions = QActionGroup(self.mainWindow)
        self.actionExport = self.databaseActions.addAction(QIcon(":/icons/export.png"), "Export Data")
        self.actionExport.setToolTip(wraptip("Export selected node(s) and their children to a .csv file. \n If no or all node(s) are selected inside the data-view, a complete export of all data in the DB is performed"))
        self.actionExport.triggered.connect(self.exportNodes)

        self.actionAdd = self.databaseActions.addAction(QIcon(":/icons/add.png"), "Add Nodes")
        self.actionAdd.setToolTip(wraptip("Add new node(s) as a starting point for further data collection"))
        self.actionAdd.triggered.connect(self.addNodes)

        self.actionDelete = self.databaseActions.addAction(QIcon(":/icons/delete.png"), "Delete Nodes")
        self.actionDelete.setToolTip(wraptip("Delete nodes(s) and their children"))
        self.actionDelete.triggered.connect(self.deleteNodes)


        #Data actions
        self.dataActions = QActionGroup(self.mainWindow)
        self.actionQuery = self.dataActions.addAction(QIcon(":/icons/fetch.png"), "Query")
        self.actionQuery.triggered.connect(self.querySelectedNodes)

        self.actionSettings = self.dataActions.addAction(QIcon(":/icons/more.png"), "More settings")
        self.actionSettings.setToolTip(wraptip("Can't get enough? Here you will find even more settings."))
        self.actionSettings.triggered.connect(self.openSettings)

        self.actionBrowse = self.dataActions.addAction(QIcon(":/icons/browser.png"), "Open")
        self.actionBrowse.setToolTip(wraptip("Open the resulting URL in the browser."))
        self.actionBrowse.triggered.connect(self.openBrowser)

        self.actionTimer = self.dataActions.addAction(QIcon(":/icons/fetch.png"), "Time")
        self.actionTimer.setToolTip(wraptip("Time your data collection with a timer. Fetches the data for the selected node(s) in user-defined intervalls"))
        self.actionTimer.triggered.connect(self.setupTimer)

        self.actionHelp = self.dataActions.addAction(QIcon(":/icons/help.png"), "Help")
        self.actionHelp.triggered.connect(self.help)

        self.actionLoadPreset = self.dataActions.addAction(QIcon(":/icons/presets.png"), "Presets")
        self.actionLoadPreset.triggered.connect(self.openPresets)

        self.actionLoadAPIs = self.dataActions.addAction(QIcon(":/icons/apis.png"), "APIs")
        self.actionLoadAPIs.triggered.connect(self.loadAPIs)

        #Detail actions
        self.detailActions = QActionGroup(self.mainWindow)

        self.actionJsonCopy = self.detailActions.addAction(QIcon(":/icons/toclip.png"), "Copy JSON to Clipboard")
        self.actionJsonCopy.setToolTip(wraptip("Copy the selected JSON-data to the clipboard"))
        self.actionJsonCopy.triggered.connect(self.jsonCopy)

        self.actionUnpack = self.detailActions.addAction(QIcon(":/icons/unpack.png"),"Extract Data")
        self.actionUnpack.setToolTip(wraptip("Extract new nodes from the data using keys." \
                                             "You can pipe the value to css selectors (e.g. text|div.main)" \
                                             "or xpath selectors (e.g. text|//div[@class='main']/text()"))
        self.actionUnpack.triggered.connect(self.unpackList)

        self.actionFieldDoc = self.detailActions.addAction(QIcon(":/icons/help.png"),"")
        self.actionFieldDoc.setToolTip(wraptip("Open the documentation for the selected item if available."))
        self.actionFieldDoc.triggered.connect(self.showFieldDoc)

        # Column setup actions
        self.columnActions = QActionGroup(self.mainWindow)

        self.actionAddColumn = self.columnActions.addAction(QIcon(":/icons/addcolumn.png"), "Add Column")
        self.actionAddColumn.setToolTip(wraptip("Add the current JSON-key as a column in the data view"))
        self.actionAddColumn.triggered.connect(self.addColumn)

        self.actionAddAllolumns = self.columnActions.addAction(QIcon(":/icons/addcolumn.png"), "Add All Columns")
        self.actionAddAllolumns.setToolTip(
            wraptip("Analyzes all selected nodes in the data view and adds all found keys as columns"))
        self.actionAddAllolumns.triggered.connect(self.addAllColumns)

        self.actionShowColumns = self.columnActions.addAction(QIcon(":/icons/apply.png"), "Apply Column Setup")
        self.actionShowColumns.setToolTip(wraptip(("Show the columns in the central data view. " +
            "Scroll right or left to see hidden columns.")))
        self.actionShowColumns.triggered.connect(self.showColumns)

        self.actionClearColumns = self.columnActions.addAction(QIcon(":/icons/clear.png"), "Clear Columns")
        self.actionClearColumns.setToolTip(wraptip("Remove all columns to get space for a new setup."))
        self.actionClearColumns.triggered.connect(self.clearColumns)

        #Tree actions
        self.treeActions = QActionGroup(self.mainWindow)
        self.actionExpandAll = self.treeActions.addAction(QIcon(":/icons/expand.png"), "Expand nodes")
        self.actionExpandAll.triggered.connect(self.expandAll)

        self.actionCollapseAll = self.treeActions.addAction(QIcon(":/icons/collapse.png"), "Collapse nodes")
        self.actionCollapseAll.triggered.connect(self.collapseAll)

        self.actionFind = self.treeActions.addAction(QIcon(":/icons/search.png"), "Find nodes")
        self.actionFind.triggered.connect(self.selectNodes)

        #self.actionSelectNodes=self.treeActions.addAction(QIcon(":/icons/collapse.png"),"Select nodes")
        #self.actionSelectNodes.triggered.connect(self.selectNodes)

        self.actionClipboard = self.treeActions.addAction(QIcon(":/icons/toclip.png"), "Copy Node(s) to Clipboard")
        self.actionClipboard.setToolTip(wraptip("Copy the selected nodes(s) to the clipboard"))
        self.actionClipboard.triggered.connect(self.clipboardNodes)

        self.actionTransfer = self.treeActions.addAction(QIcon(":/icons/transfer.png"), "Transfer nodes")
        self.actionTransfer.setToolTip(wraptip("Add the Object IDs of the selected nodes as seed nodes. Duplicates will be ignored. " \
                                             "Useful for crawling: after fetching data, add new nodes to the list."))
        self.actionTransfer.triggered.connect(self.duplicateNodes)


    @Slot()
    def help(self):
        self.mainWindow.helpwindow.show()

    @Slot()
    def openDB(self):
        #open a file dialog with a .db filter
        datadir = self.mainWindow.database.filename
        if not os.path.exists(datadir):
            datadir = self.mainWindow.settings.value("lastpath", os.path.expanduser("~"))
        if not os.path.exists(datadir):
            datadir = os.path.expanduser("~")
        datadir = os.path.dirname(datadir)

        fldg = QFileDialog(caption="Open DB File", directory=datadir, filter="DB files (*.db)")
        fldg.setFileMode(QFileDialog.ExistingFile)
        if fldg.exec_():
            self.apiActions.openDatabase(fldg.selectedFiles()[0])

    @Slot()
    def makeDB(self):
        datadir = self.mainWindow.database.filename
        if not os.path.exists(datadir):
            datadir = self.mainWindow.settings.value("lastpath", os.path.expanduser("~"))
        if not os.path.exists(datadir):
            datadir = os.path.expanduser("~")
        datadir = os.path.dirname(datadir)

        fldg = QFileDialog(caption="Save DB File", directory=datadir, filter="DB files (*.db)")
        fldg.setAcceptMode(QFileDialog.AcceptSave)
        fldg.setDefaultSuffix("db")

        if fldg.exec_():
            self.apiActions.createDatabase(fldg.selectedFiles()[0], True)

    @Slot()
    def deleteNodes(self):

        reply = QMessageBox.question(self.mainWindow, 'Delete Nodes', "Are you sure to delete all selected nodes?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        progress = ProgressBar("Deleting data...", self.mainWindow)

        self.mainWindow.tree.setUpdatesEnabled(False)
        try:
            todo = self.mainWindow.tree.selectedIndexesAndChildren({'persistent': True})
            todo = list(todo)
            progress.setMaximum(len(todo))
            for index in todo:
                progress.step()
                self.mainWindow.tree.treemodel.deleteNode(index, delaycommit=True)
                if progress.wasCanceled:
                    break
        finally:
            # commit the operation on the db-layer afterwards (delaycommit is True)
            self.mainWindow.tree.treemodel.commitNewNodes()
            self.mainWindow.tree.setUpdatesEnabled(True)
            progress.close()

    @Slot()
    def clipboardNodes(self):
        progress = ProgressBar("Copy to clipboard", self.mainWindow)

        indexes = self.mainWindow.tree.selectionModel().selectedRows()
        progress.setMaximum(len(indexes))

        output = io.StringIO()
        try:
            writer = csv.writer(output, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL, doublequote=True,
                                lineterminator='\r\n')

            #headers
            row = [str(val) for val in self.mainWindow.tree.treemodel.getRowHeader()]
            writer.writerow(row)

            #rows
            for no in range(len(indexes)):
                if progress.wasCanceled:
                    break

                row = [str(val) for val in self.mainWindow.tree.treemodel.getRowData(indexes[no])]
                writer.writerow(row)

                progress.step()

            clipboard = QApplication.clipboard()
            clipboard.setText(output.getvalue())
        finally:
            output.close()
            progress.close()

    @Slot()
    def exportNodes(self):
        fldg = ExportFileDialog(self.mainWindow, filter ="CSV Files (*.csv)")


    @Slot()
    def addNodes(self):
        if not self.mainWindow.database.connected:
            return False

        # makes the user add a new facebook object into the db
        dialog = QDialog(self.mainWindow)
        dialog.setWindowTitle("Add Nodes")
        layout = QVBoxLayout()

        label = QLabel("One <b>Object ID</b> per line")
        layout.addWidget(label)


        input = QPlainTextEdit()
        input.setMinimumWidth(500)
        input.LineWrapMode = QPlainTextEdit.NoWrap
        #input.acceptRichText=False
        input.setFocus()
        layout.addWidget(input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        filesbutton = buttons.addButton("Add files", QDialogButtonBox.ResetRole)
        filesbutton.setToolTip(wraptip("Add the names of files in a directory as nodes. Useful for uploading files in the Generic module or for importing data you downloaded before. The filenames are URIs an can be processed like any API or website."))

        loadbutton = buttons.addButton("Load CSV", QDialogButtonBox.ResetRole)
        loadbutton.setToolTip(wraptip("Import nodes from a csv file. Use semicolon as seperator. The first column becomes the Object ID, all columns are added to the data view as key value pairs."))
        layout.addWidget(buttons)

        dialog.setLayout(layout)

        self.progressUpdate = datetime.now()

        def createNodes():
            newnodes = [node.strip() for node in input.toPlainText().splitlines()]

            self.apiActions.addNodes(newnodes)
            dialog.close()

        def updateProgress():
            if datetime.now() >= self.progressUpdate:
                self.progressUpdate = datetime.now() + timedelta(milliseconds=50)
                QApplication.processEvents()
            return True

        def loadCSV():
            datadir = os.path.dirname(self.mainWindow.settings.value('lastpath', ''))
            datadir = os.path.expanduser('~') if datadir == '' else datadir

            filename, filetype = QFileDialog.getOpenFileName(dialog, "Load CSV", datadir, "CSV files (*.csv)")
            if filename != "":
                self.apiActions.addCsv(filename,updateProgress)
            dialog.close()

        def loadFilenames():
            datadir = os.path.dirname(self.mainWindow.settings.value('lastpath', ''))
            datadir = os.path.expanduser('~') if datadir == '' else datadir

            filenames, filter = QFileDialog.getOpenFileNames(dialog, "Add filenames", datadir)
            for filename in filenames:
                #with open(filename, encoding="UTF-8-sig") as file:

                data = {}
                data['fileurl'] = 'file:' + pathname2url(filename)
                data['filename'] = os.path.basename(filename)
                data['filepath'] = filename


                self.mainWindow.tree.treemodel.addSeedNodes([data])
                self.mainWindow.tree.selectLastRow()
                dialog.close()

                self.mainWindow.tree.selectLastRow()
                dialog.close()

        def close():
            dialog.close()

        #connect the nested functions above to the dialog-buttons
        buttons.accepted.connect(createNodes)
        buttons.rejected.connect(close)
        loadbutton.clicked.connect(loadCSV)
        filesbutton.clicked.connect(loadFilenames)

        dialog.exec_()

    @Slot()
    def showColumns(self):
        cols = self.mainWindow.fieldList.toPlainText().splitlines()
        cols = [x.strip() for x in cols]
        self.mainWindow.tree.treemodel.setCustomColumns(cols)

    @Slot()
    def clearColumns(self):
        self.mainWindow.fieldList.clear()
        self.mainWindow.tree.treemodel.setCustomColumns([])


    @Slot()
    def addColumn(self):
        key = self.mainWindow.detailTree.selectedKey()
        if key != '':
            self.mainWindow.fieldList.append(key)
        self.mainWindow.tree.treemodel.setCustomColumns(self.mainWindow.fieldList.toPlainText().splitlines())

    @Slot()
    def addAllColumns(self):
        progress = ProgressBar("Analyzing data...", self.mainWindow)
        columns = self.mainWindow.fieldList.toPlainText().splitlines()
        try:
            indexes = self.mainWindow.tree.selectedIndexesAndChildren()
            indexes = list(indexes)
            progress.setMaximum(len(indexes))

            for no in range(len(indexes)):
                progress.step()
                item = indexes[no].internalPointer()
                columns.extend([key for key in recursiveIterKeys(item.data['response']) if not key in columns])
                if progress.wasCanceled:
                    break
        finally:
            self.mainWindow.fieldList.setPlainText("\n".join(columns))
            self.mainWindow.tree.treemodel.setCustomColumns(columns)

            progress.close()

    @Slot()
    def openPresets(self):
        self.mainWindow.presetWindow.showPresets()

    @Slot()
    def loadAPIs(self):
        self.mainWindow.apiWindow.showWindow()

    @Slot()
    def jsonCopy(self):
        self.mainWindow.detailTree.copyToClipboard()

    @Slot()
    def unpackList(self):
        key = self.mainWindow.detailTree.selectedKey()
        self.mainWindow.dataWindow.showValue(key)

    @Slot()
    def duplicateNodes(self):
        self.mainWindow.transferWindow.show()

    @Slot()
    def showFieldDoc(self):
        tree = self.mainWindow.detailTree
        key = tree.selectedKey()
        if key == '':
            return False
        key = tree.treemodel.fieldprefix +  key

        if tree.treemodel.itemtype is not None:
            self.mainWindow.apiWindow.showDoc(tree.treemodel.module, tree.treemodel.basepath, tree.treemodel.path, key)


    @Slot()
    def expandAll(self):
        self.mainWindow.tree.expandAll()

    @Slot()
    def collapseAll(self):
        self.mainWindow.tree.collapseAll()

    @Slot()
    def selectNodes(self):
        self.mainWindow.selectNodesWindow.showWindow()

    def getQueryOptions(self, apimodule=False, options=None):
        if isinstance(apimodule, str):
            apimodule = self.mainWindow.getModule(apimodule)
        if apimodule == False:
            apimodule = self.mainWindow.RequestTabs.currentWidget()

        # Get global options
        globaloptions = apimodule.getGlobalOptions()
        apimodule.getProxies(True)

        # Get module option
        if options is None:
            options = apimodule.getSettings()
        else:
            options = options.copy()
        options.update(globaloptions)

        return (apimodule, options)

    def getIndexes(self, options= {}, indexes=None, progress=None):
        # Get selected nodes
        if indexes is None:
            objecttypes = self.mainWindow.typesEdit.text().replace(' ', '').split(',')
            level = self.mainWindow.levelEdit.value() - 1
            select_all = options['allnodes']
            select_filter = {'level': level, '!objecttype': objecttypes}
            conditions = {'filter': select_filter,
                          'selectall': select_all,
                          'options': options}

            self.progressUpdate = datetime.now()
            def updateProgress(current, total, level=0):
                if not progress:
                    return True

                if datetime.now() >= self.progressUpdate:
                    progress.showInfo('input', "Adding nodes to queue ({}/{}).".format(current, total))
                    QApplication.processEvents()
                    self.progressUpdate = datetime.now() + timedelta(milliseconds=60)

                return not progress.wasCanceled

            indexes = self.mainWindow.tree.selectedIndexesAndChildren(conditions, updateProgress)

        elif isinstance(indexes, list):
            indexes = iter(indexes)

        return indexes

    # Copy node data and options
    def prepareJob(self, index, options):
        treenode = index.internalPointer()
        node_data = deepcopy(treenode.data)
        node_options = deepcopy(options)
        node_options['lastdata'] = treenode.lastdata if hasattr(treenode, 'lastdata') else None

        job = {'nodeindex': index,
               'nodedata': node_data,
               'options': node_options}

        return job

    def queryNodes(self, indexes=None, apimodule=False, options=None):
        if not (self.mainWindow.tree.selectedCount() or self.mainWindow.allnodesCheckbox.isChecked() or (indexes is not None)):
            return False

        #Show progress window
        progress = ProgressBar("Fetching Data", parent=self.mainWindow)

        try:
            apimodule, options = self.getQueryOptions(apimodule, options)
            indexes = self.getIndexes(options, indexes, progress)

            # Update progress window
            self.mainWindow.logmessage("Start fetching data.")
            totalnodes = 0
            hasindexes = True
            progress.setMaximum(totalnodes)
            self.mainWindow.tree.treemodel.nodecounter = 0

            #Init status messages
            statuscount = defaultdict(int)
            errorcount = 0
            ratelimitcount = 0
            allowedstatus = ['fetched (200)','downloaded (200)','fetched (202)']

            try:
                #Spawn Threadpool
                threadpool = ApiThreadPool(apimodule)
                threadpool.spawnThreads(options.get("threads", 1))

                #Process Logging/Input/Output Queue
                while True:
                    try:
                        #Logging (sync logs in threads with main thread)
                        msg = threadpool.getLogMessage()
                        if msg is not None:
                            self.mainWindow.logmessage(msg)

                        # Jobs in: packages of 100 at a time
                        jobsin = 0
                        while hasindexes and (jobsin < 100):
                            index = next(indexes, False)
                            if index:
                                jobsin += 1
                                totalnodes += 1
                                if index.isValid():
                                    job = self.prepareJob(index, options)
                                    threadpool.addJob(job)
                            else:
                                threadpool.applyJobs()
                                progress.setRemaining(threadpool.getJobCount())
                                progress.resetRate()
                                hasindexes = False
                                progress.removeInfo('input')
                                self.mainWindow.logmessage("Added {} node(s) to queue.".format(totalnodes))

                        if jobsin > 0:
                            progress.setMaximum(totalnodes)

                        #Jobs out
                        job = threadpool.getJob()

                        #-Finished all nodes (sentinel)...
                        if job is None:
                            break

                        #-Finished one node...
                        elif 'progress' in job:
                            progresskey = 'nodeprogress' + str(job.get('threadnumber', ''))

                            # Update single progress
                            if 'current' in job:
                                percent = int((job.get('current',0) * 100.0 / job.get('total',1))) 
                                progress.showInfo(progresskey, "{}% of current node processed.".format(percent))
                            elif 'page' in job:
                                if job.get('page', 0) > 1:
                                    progress.showInfo(progresskey, "{} page(s) of current node processed.".format(job.get('page',0)))

                            # Update total progress
                            else:
                                progress.removeInfo(progresskey)
                                if not threadpool.suspended:
                                    progress.step()

                        #-Add data...
                        elif 'data' in job and (not progress.wasCanceled):
                            if not job['nodeindex'].isValid():
                                continue

                            # Add data
                            treeindex = job['nodeindex']
                            treenode = treeindex.internalPointer()

                            newcount = treenode.appendNodes(job['data'], job['options'], True)
                            if options.get('expand',False):
                                 self.mainWindow.tree.setExpanded(treeindex,True)

                            # Count status and errors
                            status = job['options'].get('querystatus', 'empty')
                            statuscount[status] += 1
                            errorcount += int(not status in allowedstatus)

                            # Detect rate limit
                            ratelimit = job['options'].get('ratelimit', False)
                            #ratelimit = ratelimit or (not newcount)
                            ratelimitcount += int(ratelimit)
                            autoretry = (ratelimitcount) or (status == "request error")

                            # Clear errors when everything is ok
                            if not threadpool.suspended and (status in allowedstatus) and (not ratelimit):
                                #threadpool.clearRetry()
                                errorcount = 0
                                ratelimitcount = 0

                            # Suspend on error or ratelimit
                            elif (errorcount >= options['errors']) or (ratelimitcount > 0):
                                threadpool.suspendJobs()

                                if ratelimit:
                                    msg = "You reached the rate limit of the API."
                                else:
                                    msg = "{} consecutive errors occurred.\nPlease check your settings.".format(errorcount)

                                timeout = 60 * 5 # 5 minutes

                                # Adjust progress
                                progress.showError(msg, timeout, autoretry)
                                self.mainWindow.tree.treemodel.commitNewNodes()

                            # Add job for retry
                            if not status in allowedstatus:
                                threadpool.addError(job)

                            # Show info
                            progress.showInfo(status,"{} response(s) with status: {}".format(statuscount[status],status))
                            progress.showInfo('newnodes',"{} new node(s) created".format(self.mainWindow.tree.treemodel.nodecounter))
                            progress.showInfo('threads',"{} active thread(s)".format(threadpool.getThreadCount()))
                            progress.setRemaining(threadpool.getJobCount())

                            # Custom info from modules
                            info = job['options'].get('info', {})
                            for name, value in info.items():
                                progress.showInfo(name, value)

                        # Abort
                        elif progress.wasCanceled:
                            progress.showInfo('cancel', "Disconnecting from stream, may take some time.")
                            threadpool.stopJobs()

                        # Retry
                        elif progress.wasResumed:
                            if progress.wasRetried:
                                threadpool.retryJobs()
                            else:
                                threadpool.clearRetry()
                                # errorcount = 0
                                # ratelimitcount = 0
                                threadpool.resumeJobs()

                            progress.setRemaining(threadpool.getJobCount())
                            progress.hideError()

                        # Continue
                        elif not threadpool.suspended:
                            threadpool.resumeJobs()

                        # Finished with pending errors
                        if not threadpool.hasJobs() and threadpool.hasErrorJobs():
                            msg = "All nodes finished but you have {} pending errors. Skip or retry?".format(threadpool.getErrorJobsCount())
                            autoretry = False
                            timeout = 60 * 5  # 5 minutes
                            progress.showError(msg, timeout, autoretry)

                        # Finished
                        if not threadpool.hasJobs():
                            progress.showInfo('cancel', "Work finished, shutting down threads.")
                            threadpool.stopJobs()

                        #-Waiting...
                        progress.computeRate()
                        time.sleep(1.0 / 1000.0)
                    finally:
                        QApplication.processEvents()

            finally:
                request_summary = [str(val)+" x "+key for key,val in statuscount.items()]
                request_summary = ", ".join(request_summary)
                request_end = "Fetching completed" if not progress.wasCanceled else 'Fetching cancelled by user'

                self.mainWindow.logmessage("{}, {} new node(s) created. Summary of responses: {}.".format(request_end, self.mainWindow.tree.treemodel.nodecounter,request_summary))

                self.mainWindow.tree.treemodel.commitNewNodes()
        except Exception as e:
            self.mainWindow.logmessage("Error in scheduler, fetching aborted: {}.".format(str(e)))
        finally:
            progress.close()
            return not progress.wasCanceled

    @Slot()
    def querySelectedNodes(self):
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            self.openBrowser()
        else:
            self.apiActions.fetchData()

    @Slot()
    def setupTimer(self):
        # Get data
        level = self.mainWindow.levelEdit.value() - 1
        objecttypes = self.mainWindow.typesEdit.text().replace(' ', '').split(',')
        conditions = {'persistent': True,
                      'filter': {
                          'level': level,
                          '!objecttype': objecttypes
                        }
                      }
        indexes = self.mainWindow.tree.selectedIndexesAndChildren(conditions)
        module = self.mainWindow.RequestTabs.currentWidget()
        options = module.getSettings()
        pipeline = [{'module': module, 'options': options}]

        # Show timer window
        self.mainWindow.timerWindow.setupTimer({'indexes': list(indexes), 'pipeline': pipeline})

    @Slot()
    def timerStarted(self, time):
        self.mainWindow.timerStatus.setStyleSheet("QLabel {color:red;}")
        self.mainWindow.timerStatus.setText("Timer will be fired at " + time.toString("d MMM yyyy - hh:mm") + " ")

    @Slot()
    def timerStopped(self):
        self.mainWindow.timerStatus.setStyleSheet("QLabel {color:black;}")
        self.mainWindow.timerStatus.setText("Timer stopped ")

    @Slot()
    def timerCountdown(self, countdown):
        self.mainWindow.timerStatus.setStyleSheet("QLabel {color:red;}")
        self.mainWindow.timerStatus.setText("Timer will be fired in " + str(countdown) + " seconds ")

    @Slot()
    def timerFired(self, data):
        self.mainWindow.timerStatus.setText("Timer fired ")
        self.mainWindow.timerStatus.setStyleSheet("QLabel {color:red;}")

        pipeline = data.get('pipeline',[])
        indexes = data.get('indexes',[])

        for preset in pipeline:
            module = preset.get('module')
            options = preset.get('options')

            self.fetchData(indexes, module, options)

            break

    @Slot()
    def openSettings(self):

        dialog = QDialog(self.mainWindow)
        dialog.setWindowTitle("More settings")
        layout = QVBoxLayout()
        dialog.setLayout(layout)

        layout.addWidget(self.mainWindow.settingsWidget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        layout.addWidget(buttons)

        buttons.accepted.connect(dialog.close)
        dialog.exec_()

    @Slot()
    def openBrowser(self, indexes=None, apimodule=False, options=None):
        # Check seed nodes
        if not (self.mainWindow.tree.selectedCount() or self.mainWindow.allnodesCheckbox.isChecked() or (
                indexes is not None)):
            return False

        # Get options
        apimodule, options = self.apiActions.getQueryOptions(apimodule, options)
        if not apimodule.auth_userauthorized and apimodule.auth_preregistered:
            msg = 'You are not authorized, login please!'
            QMessageBox.critical(self.mainWindow, "Not authorized",msg,QMessageBox.StandardButton.Ok)
            return False

        # Get seed nodes
        indexes = self.apiActions.getIndexes(options, indexes)
        index = next(indexes, False)
        if not index or not index.isValid():
            return False

        # Prepare job
        job = self.apiActions.prepareJob(index, options)

        # Open browser
        def logData(data, options, headers):
            data = sliceData(data, headers, options)

            # Add data
            treeindex = job['nodeindex']
            treenode = treeindex.internalPointer()

            newcount = treenode.appendNodes(data, options, False)
            if options.get('expand', False):
                self.mainWindow.tree.setExpanded(treeindex, True)

        apimodule.captureData(job['nodedata'], job['options'], logData, self.mainWindow.logmessage, logProgress=None)

    @Slot()
    def treeNodeSelected(self, current):
        #show details
        self.mainWindow.detailTree.clear()
        if current.isValid():
            item = current.internalPointer()
            self.mainWindow.detailTree.showDict(item.data['response'],item.data['querytype'], item.data['queryparams'])

        # update preview in extract data window
        if self.mainWindow.dataWindow.isVisible():
            self.mainWindow.dataWindow.updateNode(current)

        # update node level in duplicate nodes window
        if self.mainWindow.transferWindow.isVisible():
            self.mainWindow.transferWindow.updateNode(current)


        #select level
        level = 0
        c = current
        while c.isValid():
            level += 1
            c = c.parent()

        self.mainWindow.levelEdit.setValue(level)

        #show node count
        selcount = self.mainWindow.tree.selectedCount()
        self.mainWindow.selectionStatus.setText(str(selcount) + ' node(s) selected ')
        self.actionQuery.setDisabled(selcount == 0)

