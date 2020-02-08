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
        self.setMinimumHeight(400)

        # layout
        layout = QVBoxLayout(self)
        self.setLayout(layout)


        self.extractLayout = QHBoxLayout()
        layout.addLayout(self.extractLayout)

        # Extract key input
        self.extractLayout.addWidget(QLabel("Key to extract:"))
        self.input_extract = QLineEdit()
        self.input_extract.setFocus()
        self.extractLayout.addWidget(self.input_extract)

        # Object ID key input
        self.extractLayout.addWidget(QLabel("Key for Object ID:"))
        self.input_id = QLineEdit()
        self.extractLayout.addWidget(self.input_id)

        # Data
        self.dataLayout = QVBoxLayout()
        layout.addLayout(self.dataLayout)

        self.dataEdit = QTextEdit(self)
        self.dataLayout.addWidget(self.dataEdit)


        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.createNodes)
        buttons.rejected.connect(self.close)
        layout.addWidget(buttons)

    def showValue(self, key = '', value = ''):
        self.input_extract.setText(key)
        self.dataEdit.setPlainText(value)
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
