from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

from widgets.progressbar import ProgressBar
from datetime import datetime, timedelta
import re
import lxml.html
import lxml.etree

from utilities import *


class DataViewer(QDialog):
    def __init__(self, parent=None):
        super(DataViewer, self).__init__(parent)

        # Main window
        self.mainWindow = parent
        self.setWindowTitle("Extract Data")
        self.setMinimumWidth(400)

        # layout
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        self.extractLayout = QFormLayout()
        layout.addLayout(self.extractLayout)

        # Extract key input
        self.input_extract = QLineEdit()
        self.input_extract.setFocus()
        self.input_extract.textChanged.connect(self.delayPreview)
        self.extractLayout.addRow("Key to extract:",self.input_extract)

        # Object ID key input
        self.input_id = QLineEdit()
        self.input_id.textChanged.connect(self.delayPreview)
        self.extractLayout.addRow("Key for Object ID:", self.input_id)

        # Options
        optionsLayout = QHBoxLayout()
        self.extractLayout.addRow(optionsLayout)

        self.allnodesCheckbox = QCheckBox("Select all nodes")
        self.allnodesCheckbox.setToolTip(wraptip("Check if you want to extract data for all nodes."))
        self.allnodesCheckbox.setChecked(False)
        optionsLayout.addWidget(self.allnodesCheckbox)

        self.levelEdit=QSpinBox()
        self.levelEdit.setMinimum(1)
        self.levelEdit.setToolTip(wraptip("Based on the selected nodes, only extract data for nodes and subnodes of the specified level (base level is 1)"))
        self.levelEdit.valueChanged.connect(self.delayPreview)
        optionsLayout.addWidget(QLabel("Node level"))
        optionsLayout.addWidget(self.levelEdit)

        self.objecttypeEdit = QLineEdit("offcut")
        self.objecttypeEdit.setToolTip(wraptip("Skip nodes with these object types."))
        self.objecttypeEdit.textChanged.connect(self.delayPreview)
        optionsLayout.addWidget(QLabel("Exclude object types"))
        optionsLayout.addWidget(self.objecttypeEdit)
        #self.extractLayout.addRow("Exclude object types", self.objecttypeEdit)


        # Preview toggle
        previewLayout = QHBoxLayout()
        layout.addLayout(previewLayout)
        self.togglePreviewCheckbox = QCheckBox()
        self.togglePreviewCheckbox .setCheckState(Qt.Checked)
        self.togglePreviewCheckbox.setToolTip(wraptip("Check to see a dumped preview of the value"))
        self.togglePreviewCheckbox.stateChanged.connect(self.showPreview)
        previewLayout.addWidget(self.togglePreviewCheckbox)

        self.previewTimer = QTimer()
        self.previewTimer.timeout.connect(self.showPreview)
        self.previewTimer.setSingleShot(True)

        self.togglePreviewLabel = QLabel("Preview")
        previewLayout.addWidget(self.togglePreviewLabel)
        previewLayout.addStretch()

        # Data
        self.dataEdit = QTextEdit(self)
        self.dataEdit.setReadOnly(True)
        self.dataEdit.setMinimumHeight(400)
        layout.addWidget(self.dataEdit)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Apply | QDialogButtonBox.Close)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self.createNodes)
        buttons.button(QDialogButtonBox.Close).clicked.connect(self.close)
        layout.addWidget(buttons)

    def showValue(self, key = ''):
        self.input_extract.setText(key)
        #self.input_id.setText(key)

        self.allnodesCheckbox.setChecked(self.mainWindow.allnodesCheckbox.isChecked())
        self.levelEdit.setValue(self.mainWindow.levelEdit.value())
        self.objecttypeEdit.setText(self.mainWindow.typesEdit.text())

        self.show()
        self.raise_()

    @Slot()
    def delayPreview(self):
        self.previewTimer.stop()
        self.previewTimer.start(500)

    def updateNode(self, current):
        self.delayPreview()
        if current.isValid():
            level = current.model().getLevel(current) + 1
            self.levelEdit.setValue(level)

    @Slot()
    def showPreview(self):
        if self.togglePreviewCheckbox.isChecked():
            try:
                # Get nodes
                key_nodes = self.input_extract.text()
                subkey = key_nodes.split('|').pop(0).rsplit('.', 1)[0]
                key_id = self.input_id.text()
                #selected = self.mainWindow.tree.selectionModel().selectedRows()

                objecttypes = self.objecttypeEdit.text().replace(' ', '').split(',')
                level = self.levelEdit.value() - 1
                conditions = {'filter': {'level': level, '!objecttype': objecttypes}}
                selected = self.mainWindow.tree.selectedIndexesAndChildren(conditions)

                nodes = []
                for item in selected:
                    if not item.isValid():
                        continue
                    treenode = item.internalPointer()
                    dbnode = treenode.dbnode()
                    if dbnode is not None:
                        name, nodes = extractValue(dbnode.response, key_nodes, dump=False)
                    break

                # Dump nodes
                value = []
                nodes = [nodes] if not (type(nodes) is list) else nodes

                for n in nodes:
                    nodedata = json.dumps(n) if isinstance(n, Mapping) else n

                    n = n if isinstance(n, Mapping) else {subkey: n}
                    objectid = extractValue(n, key_id, default=None)[1] if key_id != '' else ''

                    value.append((str(objectid), str(nodedata)))
            except Exception as e:
                value = [('',str(e))]

            value = ['<b>{}</b><p>{}</p><hr>'.format(html.escape(x),html.escape(y)) for x,y in value]
            value = "\n\n".join(value)

            self.dataEdit.setHtml(value)

        self.dataEdit.setVisible(self.togglePreviewCheckbox.isChecked())
        if not self.togglePreviewCheckbox.isChecked():
            self.adjustSize()
        self.show()

    def initProgress(self):
        self.progressBar = ProgressBar("Extracting data...", self.mainWindow)
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
        key_nodes = self.input_extract.text()
        key_objectid = self.input_id.text()
        if key_nodes == '':
            return False
        if key_objectid == '':
            key_objectid = None

        try:
            self.initProgress()
            objecttypes = self.objecttypeEdit.text().replace(' ', '').split(',')
            level = self.levelEdit.value() - 1
            allnodes = self.allnodesCheckbox.isChecked()
            conditions = {'filter': {'level': level, '!objecttype': objecttypes},
                          'selectall': allnodes}
            selected = self.mainWindow.tree.selectedIndexesAndChildren(conditions, self.updateProgress)

            for item in selected:
                if self.progressBar.wasCanceled:
                    break
                if not item.isValid():
                    continue
                treenode = item.internalPointer()
                treenode.unpackList(key_nodes, key_objectid, delaycommit=True)
        except Exception as e:
            self.mainWindow.logmessage(e)
        finally:
            self.mainWindow.tree.treemodel.commitNewNodes()
            self.finishProgress()

        #self.close()
        return True
