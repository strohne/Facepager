from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

from widgets.progressbar import ProgressBar
from datetime import datetime, timedelta
import re
import lxml.html
import lxml.etree

from utilities import *
from database import *

class TransferNodes(QDialog):
    def __init__(self, parent=None):
        super(TransferNodes, self).__init__(parent)

        # Main window
        self.mainWindow = parent
        self.setWindowTitle("Add selected nodes as seed nodes")
        #self.setMinimumWidth(400)

        # layout
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.extractLayout = QFormLayout()
        layout.addLayout(self.extractLayout)

        # Options
        self.levelEdit=QSpinBox()
        self.levelEdit.setMinimum(1)
        self.levelEdit.setToolTip(wraptip("Based on the selected nodes, only subnodes of the specified level are processed (base level is 1)"))
        self.extractLayout.addRow("Node level", self.levelEdit)

        self.allnodesCheckbox = QCheckBox("Transfer all nodes")
        self.allnodesCheckbox.setToolTip(wraptip("Check if you want to transfer all nodes on the level, even if not selected."))
        self.allnodesCheckbox.setChecked(False)
        self.extractLayout.addRow("Nodes", self.allnodesCheckbox)

        self.keyEdit = QLineEdit("key")
        self.keyEdit.setToolTip(wraptip("Which value should be extracted from the source node? Leave empty to use the Object ID (default)."))
        self.extractLayout.addRow("Extraction key", self.keyEdit)
        self.keyEdit.setText('Object ID')

        self.noduplicatesCheckbox = QCheckBox("Skip duplicates")
        self.noduplicatesCheckbox.setToolTip(
            wraptip("Check if you want to skip duplicates, which is advised.")
        )
        self.noduplicatesCheckbox.setChecked(True)
        self.extractLayout.addRow("Duplicates", self.noduplicatesCheckbox)

        self.objecttypeEdit = QLineEdit("offcut")
        self.objecttypeEdit.setToolTip(wraptip("Skip nodes with these object types."))
        self.extractLayout.addRow("Exclude object types", self.objecttypeEdit)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self.createNodes)
        buttons.button(QDialogButtonBox.Close).clicked.connect(self.close)
        layout.addWidget(buttons)

    def show(self):
        self.allnodesCheckbox.setChecked(self.mainWindow.allnodesCheckbox.isChecked())
        self.levelEdit.setValue(self.mainWindow.levelEdit.value())
        self.objecttypeEdit.setText(self.mainWindow.typesEdit.text())

        super(TransferNodes, self).show()
        self.raise_()

    def updateNode(self, current):
        if current.isValid():
            level = current.model().getLevel(current) + 1
            self.levelEdit.setValue(level)

    def initProgress(self):
        self.progressBar = ProgressBar("Transferring nodes...", self.mainWindow)
        self.progressTotal = None
        self.progressLevel = None
        self.progressUpdate = datetime.now()

    def updateProgress(self,current, total, level=0):
        if datetime.now() >= self.progressUpdate:
            if (self.progressLevel is None) or (level < self.progressLevel):
                self.progressLevel = level
                self.progressTotal = total

            if (level == self.progressLevel) or (total > self.progressTotal):
                self.progressBar.setMaximum(total)
                self.progressBar.setValue(current)
                self.progressUpdate = datetime.now() + timedelta(milliseconds=50)

            QApplication.processEvents()

        return not self.progressBar.wasCanceled

    def finishProgress(self):
        self.progressBar.close()

    @Slot()
    def createNodes(self):
        try:
            self.initProgress()

            # Get list of seed nodes to avoid duplicates
            skipduplicates = self.noduplicatesCheckbox.isChecked()
            seednodes = Node.query.filter(Node.parent_id == None).add_columns(Node.objectid)
            seednodes = [node.objectid for node in seednodes]

            # Iterate nodes
            key = self.keyEdit.text()
            objecttypes = self.objecttypeEdit.text().replace(' ', '').split(',')
            level = self.levelEdit.value() - 1
            allnodes = self.allnodesCheckbox.isChecked()
            conditions = {
                'filter': {'level': level, '!objecttype': objecttypes},
                'selectall': allnodes
            }
            selected = self.mainWindow.tree.selectedIndexesAndChildren(conditions, self.updateProgress)
            nodes_new = 0
            nodes_dupl = 0


            for item in selected:
                if self.progressBar.wasCanceled:
                    break
                if not item.isValid():
                    continue

                treenode = item.internalPointer()

                if key == 'Object ID' or key == '':
                    objectids = treenode.data.get("objectid")
                else:
                    objectids = extractValue(treenode.data.get('response',''),key, dump=False)[1]
                objectids = objectids if type(objectids) is list else [objectids]

                for objectid in objectids:
                    # count duplicates
                    if objectid in seednodes:
                        nodes_dupl += 1

                    # copy node
                    if (not skipduplicates) or (not objectid in seednodes):
                        treenode.model.addSeedNodes([objectid], delaycommit=True)
                        seednodes.append(objectid)
                        nodes_new += 1

            self.mainWindow.tree.treemodel.commitNewNodes()
            self.mainWindow.tree.selectLastRow()
            nodes_skipped = 'skipped' if skipduplicates else 'created'
            self.mainWindow.logmessage(f"{nodes_new} nodes added as seed nodes. {nodes_dupl} duplicate nodes {nodes_skipped}.")
            self.close()

        except Exception as e:
            self.mainWindow.logmessage(e)
        finally:
            self.mainWindow.tree.treemodel.commitNewNodes()
            self.finishProgress()

        #self.close()
        return True
