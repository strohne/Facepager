from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QDialog

from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage



import os
import sys
import webbrowser

class WebDialog(QDialog):
    def __init__(self, parent=None, caption = "", url=""):
        super(WebDialog,self).__init__(parent)

        self.url = url

        self.setWindowTitle(caption)
        self.setMinimumWidth(600);
        self.setMinimumHeight(600);

        vLayout = QVBoxLayout()
        self.setLayout(vLayout)

        self.page = MyQWebEnginePage()
        self.browser = QWebEngineView(self)
        self.browser.setPage(self.page)
        vLayout.addWidget(self.browser)

        # Buttons
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        hLayout.addStretch(5)

        buttonDismiss = QPushButton(self)
        buttonDismiss.setText("Cancel")
        buttonDismiss.clicked.connect(self.reject)
        hLayout.addWidget(buttonDismiss)

        buttonProceed = QPushButton(self)
        buttonProceed.setText("Proceed")
        buttonProceed.setDefault(True)
        buttonProceed.clicked.connect(self.accept)
        hLayout.addWidget(buttonProceed)

        self.loadPage()
        #browser.setBackgroundRole(QPalette.Window)

    def loadPage(self):
        self.browser.load(QUrl(self.url))

    def show(self):
        #super(WebDialog, self).show()
        return self.exec_()

class MyQWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super(MyQWebEnginePage,self).__init__(parent)

    def acceptNavigationRequest(self, url, type, isMainFrame):
        if (type == QWebEnginePage.NavigationTypeLinkClicked):
            url = url.toString()
            webbrowser.open(url)
            return False

        return True
