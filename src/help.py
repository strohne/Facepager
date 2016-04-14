from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtGui import *
import os
import sys
import webbrowser

class HelpWindow(QMainWindow):
    def __init__(self, parent=None):
        super(HelpWindow,self).__init__(parent)

        self.setWindowTitle("Facepager 3.0 - Help")
        self.setMinimumWidth(600);
        self.setMinimumHeight(600);
        central = QWidget()
        self.setCentralWidget(central)
        vLayout = QVBoxLayout(central)
        self.browser = QWebView(central)

        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)

        #self.loadPage()

        vLayout.addWidget(self.browser)
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        hLayout.addStretch(5)
        dismiss = QPushButton(central)
        dismiss.setText("Close")
        dismiss.clicked.connect(self.hide)
        hLayout.addWidget(dismiss)
        #browser.setBackgroundRole(QPalette.Window)

    def show(self):
        super(HelpWindow,self).show()
        self.loadPage()


    def loadPage(self):
        self.browser.load(QUrl("https://htmlpreview.github.io/?https://github.com/strohne/Facepager/blob/master/src/help/help.html"))
        self.browser.page().setLinkDelegationPolicy(QWebPage.DelegateExternalLinks)
        self.browser.page().linkClicked.connect(self.linkClicked)


    def linkClicked(self,url):
        url = url.toString()
        if url.startswith("https://htmlpreview.github.io/?https://github.com/strohne/Facepager/blob/master/src/help/help.html"):
            self.browser.load(url)
        else:
            webbrowser.open(url)
