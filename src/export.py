from PySide.QtCore import *
from PySide.QtGui import *
import csv
from progressbar import ProgressBar
import codecs

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
        self.setFilter("CSV Files (*.csv)")
        self.setDefaultSuffix("csv")

        self.BOMcheck = QCheckBox("Use a BOM",self)
        self.BOMcheck.setCheckState(Qt.CheckState.Checked)

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
        layout.addWidget(self.BOMcheck,row,1,1,2)
        layout.addWidget(QLabel('Export mode'),row+1,0)
        layout.addWidget(self.optionAll,row+1,1,1,2)
        self.setLayout(layout)

        if self.exec_():

            if os.path.isfile(self.selectedFiles()[0]):
                os.remove(self.selectedFiles()[0])
            output = open(self.selectedFiles()[0], 'wb')
            try:
                if self.BOMcheck.isChecked():
                    output.write(codecs.BOM_UTF8)

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
        progress.setMaximum(len(indexes))

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
            progress.close()


    def exportAllNodes(self,output):
        progress = ProgressBar("Exporting data...", self.mainWindow)
        progress.setMaximum(Node.query.count())


        try:
            writer = csv.writer(output, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL, doublequote=True,
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
                allnodes = Node.query.offset(page * 5000).limit(5000)
                if allnodes.count() == 0:
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
            progress.close()