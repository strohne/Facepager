from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

from progressbar import ProgressBar

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
        self.extractLayout.addRow("Key for Object ID:",self.input_id)

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
        self.show()
        self.raise_()

    @Slot()
    def delayPreview(self):
        self.previewTimer.stop()
        self.previewTimer.start(500)

    @Slot()
    def showPreview(self):
        if self.togglePreviewCheckbox.isChecked():
            try:
                # Get nodes
                key_nodes = self.input_extract.text()
                selected = self.mainWindow.tree.selectionModel().selectedRows()
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
                value = ''
                nodes = [nodes] if not (type(nodes) is list) else nodes
                for n in nodes:
                    n = json.dumps(n) if isinstance(n, Mapping) else n
                    value += n + '\n\n'
            except Exception as e:
                value = str(e)

            self.dataEdit.setPlainText(value)

        self.dataEdit.setVisible(self.togglePreviewCheckbox.isChecked())
        if not self.togglePreviewCheckbox.isChecked():
            self.adjustSize()
        self.show()

    @Slot()
    def createNodes(self):
        key_nodes = self.input_extract.text()
        key_objectid = self.input_id.text()
        if key_nodes == '':
            #self.close()
            return False

        try:
            progress = ProgressBar("Extracting data...", self.mainWindow)
            selected = self.mainWindow.tree.selectionModel().selectedRows()
            progress.setMaximum(len(selected))
            for item in selected:
                progress.step()
                if progress.wasCanceled:
                    break
                if not item.isValid():
                    continue
                treenode = item.internalPointer()
                treenode.unpackList(key_nodes, key_objectid, delaycommit = True)
        except Exception as e:
            self.mainWindow.logmessage(e)
        finally:
            self.mainWindow.tree.treemodel.commitNewNodes()
            progress.close()

        #self.close()
        return True
