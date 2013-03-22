from PySide.QtCore import *
from PySide.QtGui import *

class HelpWindow(QMainWindow):
    def __init__(self, parent=None):
        super(HelpWindow,self).__init__(parent)
        
        self.setWindowTitle("Facepager 3.0 - Help")   
        self.setMinimumWidth(600);
        self.setMinimumHeight(600);
        central = QWidget()
        self.setCentralWidget(central)
        vLayout = QVBoxLayout(central)
        browser = QTextBrowser(central)
        browser.setSource(QUrl().fromLocalFile("../help/help.html"))
        vLayout.addWidget(browser)
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        hLayout.addStretch(5)
        dismiss = QPushButton(central)
        dismiss.setText("Close")
        dismiss.clicked.connect(self.hide)
        hLayout.addWidget(dismiss)     
        #browser.setBackgroundRole(QPalette.Window)   

