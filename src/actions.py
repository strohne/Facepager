#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
from copy import deepcopy
from progressbar import ProgressBar
from database import *
from apimodules import *
from apithread import ApiThreadPool
import StringIO
import codecs

class Actions(object):
    def __init__(self, mainWindow):

        self.mainWindow = mainWindow

        #Basic actions
        self.basicActions = QActionGroup(self.mainWindow)
        self.actionOpen = self.basicActions.addAction(QIcon(":/icons/save.png"), "Open Database")
        self.actionOpen.triggered.connect(self.openDB)

        self.actionNew = self.basicActions.addAction(QIcon(":/icons/new.png"), "New Database")
        self.actionNew.triggered.connect(self.makeDB)

        #Database actions
        self.databaseActions = QActionGroup(self.mainWindow)
        self.actionExport = self.databaseActions.addAction(QIcon(":/icons/export.png"), "Export Data")
        self.actionExport.setToolTip("Export selected node(s) and their children to a .csv file. \n If no or all node(s) are selected inside the data-view, a complete export of all data in the DB is performed")
        self.actionExport.triggered.connect(self.exportNodes)

        self.actionAdd = self.databaseActions.addAction(QIcon(":/icons/add.png"), "Add Nodes")
        self.actionAdd.setToolTip("Add new node(s) as a starting point for further data collection")
        self.actionAdd.triggered.connect(self.addNodes)

        self.actionDelete = self.databaseActions.addAction(QIcon(":/icons/delete.png"), "Delete Nodes")
        self.actionDelete.setToolTip("Delete nodes(s) and their children")
        self.actionDelete.triggered.connect(self.deleteNodes)


        #Data actions
        self.dataActions = QActionGroup(self.mainWindow)
        self.actionQuery = self.dataActions.addAction(QIcon(":/icons/fetch.png"), "Query")
        self.actionQuery.triggered.connect(self.querySelectedNodes)

        self.actionTimer = self.dataActions.addAction(QIcon(":/icons/fetch.png"), "Time")
        self.actionTimer.setToolTip("Time your data collection with a timer. Fetches the data for the selected node(s) in user-defined intervalls")
        self.actionTimer.triggered.connect(self.setupTimer)

        self.actionHelp = self.dataActions.addAction(QIcon(":/icons/help.png"), "Help")
        self.actionHelp.triggered.connect(self.help)

        self.actionLoadPreset = self.dataActions.addAction(QIcon(":/icons/presets.png"), "Presets")
        self.actionLoadPreset.triggered.connect(self.loadPreset)

        self.actionShowColumns = self.dataActions.addAction("Show Columns")
        self.actionShowColumns.triggered.connect(self.showColumns)

        #Detail actions
        self.detailActions = QActionGroup(self.mainWindow)
        self.actionAddColumn = self.detailActions.addAction(QIcon(":/icons/addcolumn.png"),"Add Column")
        self.actionAddColumn.setToolTip("Add the current JSON-key as a column in the data view")
        self.actionAddColumn.triggered.connect(self.addColumn)

        self.actionUnpack = self.detailActions.addAction(QIcon(":/icons/unpack.png"),"Unpack List")
        self.actionUnpack.setToolTip("Unpacks a list in the JSON-data and creates a new node containing the list content")
        self.actionUnpack.triggered.connect(self.unpackList)

        self.actionJsonCopy = self.detailActions.addAction(QIcon(":/icons/toclip.png"),"Copy JSON to Clipboard")
        self.actionJsonCopy.setToolTip("Copy the selected JSON-data to the clipboard")
        self.actionJsonCopy.triggered.connect(self.jsonCopy)

        #Tree actions
        self.treeActions = QActionGroup(self.mainWindow)
        self.actionExpandAll = self.treeActions.addAction(QIcon(":/icons/expand.png"), "Expand nodes")
        self.actionExpandAll.triggered.connect(self.expandAll)

        self.actionCollapseAll = self.treeActions.addAction(QIcon(":/icons/collapse.png"), "Collapse nodes")
        self.actionCollapseAll.triggered.connect(self.collapseAll)

        #self.actionSelectNodes=self.treeActions.addAction(QIcon(":/icons/collapse.png"),"Select nodes")
        #self.actionSelectNodes.triggered.connect(self.selectNodes)

        self.actionClipboard = self.treeActions.addAction(QIcon(":/icons/toclip.png"), "Copy Node(s) to Clipboard")
        self.actionClipboard.setToolTip("Copy the selected nodes(s) to the clipboard")
        self.actionClipboard.triggered.connect(self.clipboardNodes)


    @Slot()
    def help(self):
        self.mainWindow.helpwindow.show()

    @Slot()
    def openDB(self):
        #open a file dialog with a .db filter
        datadir = self.mainWindow.settings.value("lastpath", os.path.expanduser("~"))
        fldg = QFileDialog(caption="Open DB File", directory=datadir, filter="DB files (*.db)")
        fldg.setFileMode(QFileDialog.ExistingFile)
        if fldg.exec_():
            self.mainWindow.timerWindow.cancelTimer()
            self.mainWindow.database.connect(fldg.selectedFiles()[0])
            self.mainWindow.settings.setValue("lastpath", fldg.selectedFiles()[0])
            self.mainWindow.updateUI()
            self.mainWindow.tree.treemodel.reset()


    @Slot()
    def makeDB(self):
        #same as openDB-Slot, but now for creating a new one on the file system
        datadir = self.mainWindow.settings.value("lastpath", os.path.expanduser("~"))
        fldg = QFileDialog(caption="Save DB File", directory=datadir, filter="DB files (*.db)")
        fldg.setAcceptMode(QFileDialog.AcceptSave)
        fldg.setDefaultSuffix("db")

        if fldg.exec_():
            self.mainWindow.timerWindow.cancelTimer()
            self.mainWindow.database.createconnect(fldg.selectedFiles()[0])
            self.mainWindow.settings.setValue("lastpath", fldg.selectedFiles()[0])
            self.mainWindow.updateUI()
            self.mainWindow.tree.treemodel.reset()


    @Slot()
    def deleteNodes(self):

        reply = QMessageBox.question(self.mainWindow, 'Delete Nodes', "Are you sure to delete all selected nodes?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        progress = ProgressBar("Deleting data...", self.mainWindow)

        try:
            todo = self.mainWindow.tree.selectedIndexesAndChildren(True)
            progress.setMaximum(len(todo))
            for index in todo:
                progress.step()
                self.mainWindow.tree.treemodel.deleteNode(index, delaycommit=True)
                if progress.wasCanceled:
                    break
        finally:
            # commit the operation on the db-layer afterwards (delaycommit is True)
            self.mainWindow.tree.treemodel.commitNewNodes()
            progress.close()

    @Slot()
    def clipboardNodes(self):
        progress = ProgressBar("Copy to clipboard", self.mainWindow)
        
        indexes = self.mainWindow.tree.selectionModel().selectedRows()
        progress.setMaximum(len(indexes))

        output = StringIO.StringIO()
        try:
            writer = csv.writer(output, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL, doublequote=True,
                                lineterminator='\r\n')

            #headers    
            row = [unicode(val).encode("utf-8") for val in self.mainWindow.tree.treemodel.getRowHeader()]
            writer.writerow(row)

            #rows
            for no in range(len(indexes)):
                if progress.wasCanceled:
                    break

                row = [unicode(val).encode("utf-8") for val in self.mainWindow.tree.treemodel.getRowData(indexes[no])]
                writer.writerow(row)

                progress.step()
                
            clipboard = QApplication.clipboard()
            clipboard.setText(output.getvalue())
        finally:
            output.close()
            progress.close()

    @Slot()
    def exportNodes(self):
        # if none or all are selected, export all
        # if one or more are selected, export selective
        if self.mainWindow.tree.noneOrAllSelected():
            self.exportAllNodes()        
        else:
            self.exportSelectedNodes()
        
        
    @Slot()
    def exportSelectedNodes(self):
        fldg = QFileDialog(caption="Export selected nodes to CSV", filter="CSV Files (*.csv)")
        fldg.setAcceptMode(QFileDialog.AcceptSave)
        fldg.setDefaultSuffix("csv")

        if fldg.exec_():

            progress = ProgressBar("Exporting data...", self.mainWindow)

            #indexes = self.mainWindow.tree.selectionModel().selectedRows()
            #if child nodes should be exported as well, uncomment this line an comment the previous one
            indexes = self.mainWindow.tree.selectedIndexesAndChildren()


            progress.setMaximum(len(indexes))

            if os.path.isfile(fldg.selectedFiles()[0]):
                os.remove(fldg.selectedFiles()[0])
            output = open(fldg.selectedFiles()[0], 'wb')

            try:
                writer = csv.writer(output, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL, doublequote=True,
                                    lineterminator='\r\n')


                #headers
                row = [unicode(val).encode("utf-8") for val in self.mainWindow.tree.treemodel.getRowHeader()]
                writer.writerow(row)

                #rows
                for no in range(len(indexes)):
                    if progress.wasCanceled:
                        break

                    row = [unicode(val).encode("utf-8") for val in self.mainWindow.tree.treemodel.getRowData(indexes[no])]
                    writer.writerow(row)

                    progress.step()

            finally:
                output.close()
                progress.close()


    @Slot()
    def exportAllNodes(self):
        fldg = QFileDialog(caption="Export all nodes to CSV", filter="CSV Files (*.csv)")
        fldg.setAcceptMode(QFileDialog.AcceptSave)
        fldg.setDefaultSuffix("csv")

        if fldg.exec_():
            progress = ProgressBar("Exporting data...", self.mainWindow)
            progress.setMaximum(Node.query.count())

            if os.path.isfile(fldg.selectedFiles()[0]):
                os.remove(fldg.selectedFiles()[0])

            f = open(fldg.selectedFiles()[0], 'wb')
            try:
                f.write(codecs.BOM_UTF8) #UTF8 BOM
                writer = csv.writer(f, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL, doublequote=True,
                                    lineterminator='\r\n')

                #headers    
                row = ["level", "id", "parent_id", "object_id", "object_type", "query_status", "query_time",
                       "query_type"]
                for key in self.mainWindow.tree.treemodel.customcolumns:
                    row.append(key)
                writer.writerow(row)
                #rows
                page = 0

                while True:
                    allnodes = Node.query.offset(page * 5000).limit(5000).all()
                    if len(allnodes) == 0:
                        break
                    for node in allnodes:
                        if progress.wasCanceled:
                            break
                        row = [node.level, node.id, node.parent_id, node.objectid_encoded, node.objecttype,
                               node.querystatus, node.querytime, node.querytype]
                        for key in self.mainWindow.tree.treemodel.customcolumns:
                            row.append(node.getResponseValue(key, "utf-8"))
                        writer.writerow(row)
                        # step the Bar
                        progress.step()
                    if progress.wasCanceled:
                        break
                    else:
                        page += 1

            finally:
                f.close()
                progress.close()


    @Slot()
    def addNodes(self):
        if not self.mainWindow.database.connected:
            return False

        # makes the user add a new facebook object into the db
        dialog = QDialog(self.mainWindow)
        dialog.setWindowTitle("Add Nodes")
        layout = QVBoxLayout()

        label = QLabel("<b>Object IDs (one ID per line):</b>")
        layout.addWidget(label)

        input = QPlainTextEdit()
        input.setMinimumWidth(500)
        input.LineWrapMode = QPlainTextEdit.NoWrap
        #input.acceptRichText=False
        input.setFocus()
        layout.addWidget(input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        dialog.setLayout(layout)

        def createNodes():
            self.mainWindow.tree.treemodel.addNodes(input.toPlainText().splitlines())
            dialog.close()

        def close():
            dialog.close()

        #connect the nested functions above to the dialog-buttons
        buttons.accepted.connect(createNodes)
        buttons.rejected.connect(close)
        dialog.exec_()


    @Slot()
    def showColumns(self):
        self.mainWindow.tree.treemodel.setCustomColumns(self.mainWindow.fieldList.toPlainText().splitlines())

    @Slot()
    def addColumn(self):
        key = self.mainWindow.detailTree.selectedKey()
        if key != '':
            self.mainWindow.fieldList.append(key)
        self.mainWindow.tree.treemodel.setCustomColumns(self.mainWindow.fieldList.toPlainText().splitlines())


    @Slot()
    def loadPreset(self):
        self.mainWindow.presetWindow.showPresets()

    @Slot()
    def jsonCopy(self):
        self.mainWindow.detailTree.copyToClipboard()


    @Slot()
    def unpackList(self):
        try:
            key = self.mainWindow.detailTree.selectedKey()
            if key == '':
                return False
            selected = self.mainWindow.tree.selectionModel().selectedRows()
            for item in selected:
                if not item.isValid():
                    continue
                treenode = item.internalPointer()
                treenode.unpackList(key)
        except Exception as e:
            self.mainWindow.logmessage(e)

    @Slot()
    def expandAll(self):
        self.mainWindow.tree.expandAll()

    @Slot()
    def collapseAll(self):
        self.mainWindow.tree.collapseAll()

    @Slot()
    def selectNodes(self):
        self.mainWindow.selectNodesWindow.show()


    def queryNodes(self, indexes=False, apimodule=False, options=False):
        #Show progress window
        progress = ProgressBar(u"Fetching Data",parent=self.mainWindow)

        #Get selected nodes
        if indexes == False:
            level = self.mainWindow.levelEdit.value() - 1
            indexes = self.mainWindow.tree.selectedIndexesAndChildren(False, {'level': level,
                                                                              'objecttype': ['seed', 'data',
                                                                                             'unpacked']})
        #Update progress window
        progress.setMaximum(len(indexes))
        self.mainWindow.tree.treemodel.nodecounter = 0
        
        if apimodule == False:
            apimodule = self.mainWindow.RequestTabs.currentWidget()
        if options == False:
            options = apimodule.getOptions()

        try:
            #Spawn Threadpool
            threadpool = ApiThreadPool(apimodule,self.mainWindow.logmessage)

            #Fill Input Queue
            number = 0
            for index in indexes:
                number += 1
                if not index.isValid():
                    continue

                treenode = index.internalPointer()
                job = {'number': number, 'nodeindex': index, 'data': deepcopy(treenode.data),
                       'options': deepcopy(options)}
                threadpool.addJob(job)

            threadpool.processJobs()

            #Process Output Queue
            while True:
                try:
                    job = threadpool.getJob()

                    #-Finished all nodes...
                    if job is None:
                        break

                    #-Waiting...
                    elif 'waiting' in job:
                        time.sleep(0)

                    #-Finished one node...
                    elif 'progress' in job:
                        #Update progress
                        progress.step()                        

                    #-Add data...
                    else:
                        if not job['nodeindex'].isValid():
                            continue
                        treenode = job['nodeindex'].internalPointer()
                        treenode.appendNodes(job['data'], job['options'], job['headers'], True)
                        progress.showInfo('newnodes',u"{} new node(s) created".format(self.mainWindow.tree.treemodel.nodecounter))

                        #Abort
                    if progress.wasCanceled:
                        progress.showInfo('cancel',u"Disconnecting from stream may take up to one minute.")
                        threadpool.stopJobs()
                        #break

                finally:
                    QApplication.processEvents()

        finally:            
            self.mainWindow.tree.treemodel.commitNewNodes()
            progress.close()

    @Slot()
    def querySelectedNodes(self):
        self.queryNodes()

    @Slot()
    def setupTimer(self):
        #Get data
        level = self.mainWindow.levelEdit.value() - 1
        indexes = self.mainWindow.tree.selectedIndexesAndChildren(True, {'level': level,
                                                                         'objecttype': ['seed', 'data', 'unpacked']})
        module = self.mainWindow.RequestTabs.currentWidget()
        options = module.getOptions()

        #show timer window
        self.mainWindow.timerWindow.setupTimer(
            {'indexes': indexes, 'nodecount': len(indexes), 'module': module, 'options': options})

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
        self.queryNodes(data.get('indexes', []), data.get('module', None), data.get('options', {}).copy())

    @Slot()
    def treeNodeSelected(self, current, selected):
        #show details
        self.mainWindow.detailTree.clear()
        if current.isValid():
            item = current.internalPointer()
            self.mainWindow.detailTree.showDict(item.data['response'],item.data['querytype'])

        #select level
        level = 0
        c = current
        while c.isValid():
            level += 1
            c = c.parent()

        self.mainWindow.levelEdit.setValue(level)
        
        #show node count        
        self.mainWindow.selectionStatus.setText(str(len(selected)) + ' node(s) selected ')

