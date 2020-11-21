from PySide2.QtCore import *
from PySide2.QtWidgets import *
from datetime import datetime, timedelta

class SelectNodesWindow(QDialog):
    
    
    def __init__(self, parent=None):
        super(SelectNodesWindow,self).__init__(parent)
        
        self.mainWindow = parent
        self.setWindowTitle("Find nodes")
        self.setMinimumWidth(200);

        # Status
        self.progressUpdateNext = None
        self.progressTotal = None
        self.progressLevel = None
        self.canceled = False
        self.running = False

        #layout
        layout = QVBoxLayout()
        central = QHBoxLayout()
        layout.addLayout(central, 1)
        self.setLayout(layout)
        
        searchLayout=QFormLayout()
        central.addLayout(searchLayout, 1)
        
        # Search inputs
        self.objectidEdit = QLineEdit()
        searchLayout.addRow("Object ID",self.objectidEdit)
        self.objecttypeEdit = QLineEdit()
        searchLayout.addRow("Object type",self.objecttypeEdit)
        self.querystatusEdit = QLineEdit()
        searchLayout.addRow("Query status",self.querystatusEdit)
        self.querytimeEdit = QLineEdit()
        searchLayout.addRow("Query time", self.querytimeEdit)
        self.querytypeEdit = QLineEdit()
        searchLayout.addRow("Query type", self.querytypeEdit)
        self.responseEdit = QLineEdit()
        searchLayout.addRow("Response", self.responseEdit)

        # Exact match
        self.partialCheck = QCheckBox("Partial match")
        self.partialCheck .setChecked(False)
        searchLayout.addRow(self.partialCheck)

        # Level / recursion
        self.recursiveCheck = QCheckBox("Search recursively")
        self.recursiveCheck.setChecked(False)
        searchLayout.addRow(self.recursiveCheck)

        # Button row layout
        buttons= QHBoxLayout()

        # Progress
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0,0)
        self.progressBar.hide()
        buttons.addWidget(self.progressBar)
        buttons.addStretch()

        #buttons
        self.nextButton = QPushButton('Find next')
        self.nextButton.clicked.connect(self.selectNext)
        buttons.addWidget(self.nextButton)

        self.cancelButton = QPushButton('Cancel')
        self.cancelButton.clicked.connect(self.cancel)
        buttons.addWidget(self.cancelButton)

        layout.addLayout(buttons)

    def showWindow(self):
        self.show()
        self.raise_()

    def cancel(self):
        if self.running:
            self.canceled = True
        else:
            self.close()

    def initProgress(self):
        self.progressTotal = None
        self.progressLevel = None
        self.progressUpdate = datetime.now()

        self.progressBar.setRange(0, 0)
        self.progressBar.show()

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

        return not self.canceled

    def finishProgress(self):
        self.progressBar.hide()

    def selectNext(self):
        if self.running:
            return False

        self.nextButton.hide()
        self.initProgress()
        self.running = True
        self.canceled = False

        try:
            filter = {}
            filter['objectid'] = self.objectidEdit.text()
            filter['objecttype'] = self.objecttypeEdit.text()
            filter['querystatus'] = self.querystatusEdit.text()
            filter['querytime'] = self.querytimeEdit.text()
            filter['querytype'] = self.querytypeEdit.text()
            filter['response'] = self.responseEdit.text()

            filter = {k: v for k, v in filter.items() if v != ""}
            if not filter:
                return False

            conditions = {'filter': filter,
                          'exact': not self.partialCheck.isChecked(),
                          'recursive': self.recursiveCheck.isChecked()}

            self.mainWindow.tree.selectNext(conditions, progress=self.updateProgress)
        finally:
            self.running = False
            self.canceled = False
            self.finishProgress()
            self.nextButton.show()

