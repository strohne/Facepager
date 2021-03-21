from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QFileDialog, QCheckBox, QComboBox, QLabel, QHBoxLayout
import csv
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

        # if none or all are selected, export all
        # if one or more are selected, export selective
        self.optionAll = QComboBox(self)
        self.optionAll.insertItems(0, ['All nodes (faster for large datasets, ordered by internal ID)','Selected nodes (ordered like shown in nodes view)'])
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

            output = open(self.selectedFiles()[0], 'w', newline='', encoding='utf8')
            try:
                if self.optionBOM.isChecked():
                    output.write('\ufeff')

                if self.optionAll.currentIndex() == 0:
                    self.exportAllNodes(output)
                else:
                    self.exportSelectedNodes(output)
            finally:
                output.close()

    def exportSelectedNodes(self,output):
        progress = ProgressBar("Exporting data...", self.mainWindow)

        #indexes = self.mainWindow.tree.selectionModel().selectedRows()
        #if child nodes should be exported as well, uncomment this line an comment the previous one
        indexes = self.mainWindow.tree.selectedIndexesAndChildren()
        indexes = list(indexes)
        progress.setMaximum(len(indexes))

        try:
            delimiter = self.optionSeparator.currentText()
            delimiter = delimiter.encode('utf-8').decode('unicode_escape')
            writer = csv.writer(output, delimiter=delimiter, quotechar='"', quoting=csv.QUOTE_ALL, doublequote=True,
                                lineterminator='\r\n')


            #headers
            row = [str(val) for val in self.mainWindow.tree.treemodel.getRowHeader()]
            if self.optionLinebreaks.isChecked():
                row = [val.replace('\n', ' ').replace('\r',' ') for val in row]
            row = ['path'] + row
            writer.writerow(row)

            #rows
            path = []
            for index in indexes:
                if progress.wasCanceled:
                    break

                # data
                rowdata = self.mainWindow.tree.treemodel.getRowData(index)

                # path of parents (#2=level;#3=object ID)
                while rowdata[2] < len(path):
                    path.pop()
                path.append(rowdata[3])

                # values
                row = [str(val) for val in rowdata]
                row = ["/".join(path)] + row
                if self.optionLinebreaks.isChecked():
                    row = [val.replace('\n', ' ').replace('\r',' ') for val in row]

                writer.writerow(row)

                progress.step()

        finally:
            progress.close()


    def exportAllNodes(self,output):
        progress = ProgressBar("Exporting data...", self.mainWindow)
        progress.setMaximum(Node.query.count())

        try:
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

                    row = [node.level, node.id, node.parent_id, node.objectid,
                           node.objecttype,getDictValue(node.queryparams,'nodedata'),
                           node.querystatus, node.querytime, node.querytype]
                    for key in self.mainWindow.tree.treemodel.customcolumns:
                        row.append(node.getResponseValue(key)[1])

                    if self.optionLinebreaks.isChecked():
                        row = [str(val).replace('\n', ' ').replace('\r',' ') for val in row]

                    writer.writerow(row)

                    # Step the bar
                    progress.step()

                page += 1

        finally:
            progress.close()
