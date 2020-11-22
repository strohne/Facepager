from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QMainWindow

from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage



import os
import sys
import webbrowser

class HelpWindow(QMainWindow):
    def __init__(self, parent=None):
        super(HelpWindow,self).__init__(parent)

        self.setWindowTitle("Facepager 4 - Help")
        self.setMinimumWidth(600);
        self.setMinimumHeight(600);
        central = QWidget()
        self.setCentralWidget(central)
        vLayout = QVBoxLayout(central)

        self.page = MyQWebEnginePage()
        self.browser = QWebEngineView(central)
        self.browser.setPage(self.page)

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
        self.browser.load(QUrl("http://strohne.github.io/Facepager/"))

class MyQWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super(MyQWebEnginePage,self).__init__(parent)


    def acceptNavigationRequest(self, url, type, isMainFrame):
        if (type == QWebEnginePage.NavigationTypeLinkClicked):
            url = url.toString()
            if not url.startswith("http://strohne.github.io/Facepager/"):
                webbrowser.open(url)
                return False

        return True
