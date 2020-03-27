from PySide2.QtCore import *
from PySide2.QtWidgets import *

class SelectNodesWindow(QDialog):
    
    
    def __init__(self, parent=None):
        super(SelectNodesWindow,self).__init__(parent)
        
        self.mainWindow = parent
        self.setWindowTitle("Find nodes")
        self.setMinimumWidth(200);

        # Status
        self.canceled = False
        self.running = False

        #layout
        layout = QVBoxLayout(self)        
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

        # Exact match
        self.exactCheck = QCheckBox("Exact match")
        self.exactCheck .setChecked(True)
        searchLayout.addRow(self.exactCheck )

        # Level / recursion
        self.recursiveCheck = QCheckBox("Search recursively (may take long, all data will be loaded)")
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
        self.progressBar.setRange(0, 0)
        self.progressBar.show()

    def updateProgress(self,current, total):
        self.progressBar.setMaximum(total)
        self.progressBar.setValue(current)
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

            filter = {k: v for k, v in filter.items() if v != ""}
            if filter:
                recursive = self.recursiveCheck.isChecked()
                exact = self.exactCheck.isChecked()
                self.mainWindow.tree.selectNext(filter, recursive, exact, progress=self.updateProgress)
        finally:
            self.running = False
            self.canceled = False
            self.finishProgress()
            self.nextButton.show()

