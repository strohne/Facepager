from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QFileDialog, QCheckBox, QComboBox, QLabel, QHBoxLayout, QLineEdit
import csv
import tempfile
from widgets.progressbar import ProgressBar
from database import *

class ExportFileDialog(QFileDialog):
    """
    Create a custom Export-File Dialog with options like BOM etc.
    """

    def __init__(self,*args,**kwargs):
        super(ExportFileDialog,self).__init__(*args,**kwargs)

        self.mainWindow = self.parent()
        self.setWindowTitle("Export nodes to CSV")
        self.setAcceptMode(QFileDialog.AcceptSave)
        self.setOption(QFileDialog.DontUseNativeDialog)
        #self.setFilter("CSV Files (*.csv)")
        self.setDefaultSuffix("csv")

        self.optionBOM = QCheckBox("Use a BOM",self)
        self.optionBOM.setCheckState(Qt.CheckState.Checked)

        self.optionLinebreaks = QCheckBox("Remove line breaks",self)
        self.optionLinebreaks.setCheckState(Qt.CheckState.Checked)

        self.optionSeparator = QComboBox(self)
        self.optionSeparator.insertItems(0, [";","\\t",","])
        self.optionSeparator.setEditable(True)

        self.optionLevel = QLineEdit(self)
        self.optionLevel.setToolTip(wraptip("Leave empty to export all levels or enter a single level, starting from 0."))

        self.optionObjectTypes = QLineEdit(self)
        self.optionObjectTypes.setToolTip(wraptip("Leave empty to export all types or enter a comma separated list."))

        # if none or all are selected, export all
        # if one or more are selected, export selective
        self.optionAll = QComboBox(self)
        self.optionAll.insertItems(0, [
            'All nodes (faster for large datasets, ordered by internal ID)',
            'Selected nodes (ordered like shown in nodes view)',
            'Selected nodes in wide format (each row includes all ancestor colums)'
        ])
        if self.mainWindow.tree.noneOrAllSelected():
            self.optionAll.setCurrentIndex(0)
        else:
            self.optionAll.setCurrentIndex(1)

        layout = self.layout()
        row = layout.rowCount()
        layout.addWidget(QLabel('Options'),row,0)

        options = QHBoxLayout()
        options.addWidget(self.optionBOM)
        options.addWidget(self.optionLinebreaks)
        options.addWidget(QLabel('Separator'))
        options.addWidget(self.optionSeparator)
        options.addWidget(QLabel('Level'))
        options.addWidget(self.optionLevel)
        options.addWidget(QLabel('Object types'))
        options.addWidget(self.optionObjectTypes)
        options.addStretch(1)

        layout.addLayout(options,row,1,1,2)

        layout.addWidget(QLabel('Export mode'),row+2,0)
        layout.addWidget(self.optionAll,row+2,1,1,2)
        self.setLayout(layout)

        dbfilename = self.mainWindow.database.filename
        #self.setDirectory(os.path.dirname(dbfilename))
        filename, ext = os.path.splitext(dbfilename)
        self.selectFile(filename+'.csv')

        # if not os.path.exists(dbfilename):
        #     dbfilename = self.mainWindow.settings.value("lastpath", os.path.expanduser("~"))
        # if not os.path.exists(dbfilename):
        #     dbfilename = os.path.expanduser("~")

        if self.exec_():
            try:
                if os.path.isfile(self.selectedFiles()[0]):
                    os.remove(self.selectedFiles()[0])
            except Exception as e:
                QMessageBox.information(self,"Facepager","Could not overwrite file:"+str(e))
                return False

            try:
                output = open(self.selectedFiles()[0], 'w', newline='', encoding='utf8')
                try:
                    if self.optionAll.currentIndex() == 0:
                        self.exportAllNodes(output)
                    else:
                        joinLevels = self.optionAll.currentIndex() == 2
                        self.exportSelectedNodes(output, joinLevels)
                finally:
                    output.close()
            except Exception as e:
                QMessageBox.information(self,"Facepager","Could not export file:"+str(e))
                return False

    def exportSelectedNodes(self,output, joinLevels):
        """
        Export the selected nodes and their children

        :param output: A file handle
        :return:
        """
        progress = ProgressBar("Exporting data...", self.mainWindow)

        indexes = self.mainWindow.tree.selectedIndexesAndChildren()
        indexes = list(indexes)
        progress.setMaximum(len(indexes))

        rowfile = tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', newline='', delete=False)
        tmpfilename = rowfile.name

        try:
            addpath = True

            try:
                targetLevel = int(self.optionLevel.text())
            except (ValueError, TypeError):
                targetLevel = None

            targetTypes = self.optionObjectTypes.text()
            targetTypes = targetTypes.split(',') if targetTypes != "" else None

            delimiter = self.optionSeparator.currentText()
            delimiter = delimiter.encode('utf-8').decode('unicode_escape')
            writer = csv.writer(
                rowfile, delimiter=delimiter, quotechar='"', quoting=csv.QUOTE_ALL, doublequote=True,
                lineterminator='\r\n'
            )

            #rows
            maxLevel = 0
            path = []
            parentRows = []
            for index in indexes:
                if progress.wasCanceled:
                    break

                # data
                fixedRowData = self.mainWindow.tree.treemodel.getFixedRowData(index)
                customRowData = self.mainWindow.tree.treemodel.getCustomRowData(index)
                currentLevel = int(fixedRowData[2])
                currentType = fixedRowData[4]
                maxLevel = max(maxLevel, currentLevel)

                # path of parents (#2=level;#3=object ID)
                if addpath:
                    while currentLevel < len(path):
                        path.pop()
                    path.append(fixedRowData[3])
                    fixedRowData = ["/".join(path)] + fixedRowData

                row = fixedRowData

                if joinLevels:
                    while currentLevel < len(parentRows):
                        parentRows.pop()
                    parentRows.append(customRowData)
                    for parentRow in parentRows:
                        row = row + parentRow
                else:
                    row = row + customRowData

                targetRow = (targetLevel is None) or (currentLevel == targetLevel)
                targetRow = targetRow and (targetTypes is None) or (currentType in targetTypes)

                if targetRow:
                    row = prepareList(
                        [str(val) for val in row],
                        self.optionLinebreaks.isChecked()
                    )
                    writer.writerow(row)

                progress.step()

            rowfile.flush()
            rowfile.seek(0)

            #bom
            if self.optionBOM.isChecked():
                output.write('\ufeff')

            #headers
            outputWriter = csv.writer(
                output, delimiter=delimiter, quotechar='"', quoting=csv.QUOTE_ALL, doublequote=True,
                lineterminator='\r\n'
            )

            fixedColumns = self.mainWindow.tree.treemodel.getFixedRowHeader()
            if addpath:
                fixedColumns = ['path'] + fixedColumns
            row = fixedColumns

            customColumns = self.mainWindow.tree.treemodel.getCustomRowHeader()
            if joinLevels:
                for i in range(maxLevel+1):
                    row = row + ['lvl_' + str(i) + '_' + x for x in customColumns]
            else:
                row = row + customColumns

            row = prepareList(
                [str(val) for val in row],
                self.optionLinebreaks.isChecked()
            )
            outputWriter.writerow(row)

            # Copy rows from tmp file to output
            for line in rowfile:
                output.write(line)

        finally:
            progress.close()
            rowfile.close()
            os.unlink(tmpfilename)


    def exportAllNodes(self,output):
        progress = ProgressBar("Exporting data...", self.mainWindow)
        progress.setMaximum(Node.query.count())

        try:
            if self.optionBOM.isChecked():
                output.write('\ufeff')

            downloadFolder = self.mainWindow.getDownloadFolder()

            try:
                targetLevel = int(self.optionLevel.text())
            except (ValueError, TypeError):
                targetLevel = None

            targetTypes = self.optionObjectTypes.text()
            targetTypes = targetTypes.split(',') if targetTypes != "" else None

            delimiter = self.optionSeparator.currentText()
            delimiter = delimiter.encode('utf-8').decode('unicode_escape')
            writer = csv.writer(output, delimiter=delimiter, quotechar='"',
                                quoting=csv.QUOTE_ALL, doublequote=True,
                                lineterminator='\r\n')

            # Headers
            row = ["level", "id", "parent_id", "object_id", "object_type","object_key",
                   "query_status", "query_time", "query_type"]
            for key in extractNames(self.mainWindow.tree.treemodel.customcolumns):
                row.append(key)
            if self.optionLinebreaks.isChecked():
                row = [val.replace('\n', ' ').replace('\r',' ') for val in row]
            writer.writerow(row)

            # Rows
            page = 0
            while not progress.wasCanceled:
                allnodes = Node.query.offset(page * 5000).limit(5000)
                if allnodes.count() == 0:
                    break

                for node in allnodes:
                    if progress.wasCanceled:
                        break

                    currentLevel = node.level
                    currentType = node.objecttype
                    targetRow = (targetLevel is None) or (currentLevel == targetLevel)
                    targetRow = targetRow and (targetTypes is None) or (currentType in targetTypes)

                    if targetRow:
                        row = [currentLevel, node.id, node.parent_id, node.objectid,
                               currentType,getDictValue(node.queryparams,'nodedata'),
                               node.querystatus, node.querytime, node.querytype]
                        for key in self.mainWindow.tree.treemodel.customcolumns:
                            row.append(node.getResponseValue(key, None, downloadFolder)[1])

                        if self.optionLinebreaks.isChecked():
                            row = [str(val).replace('\n', ' ').replace('\r',' ') for val in row]

                        writer.writerow(row)

                    # Step the bar
                    progress.step()

                page += 1

        finally:
            progress.close()
