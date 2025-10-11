from PySide6.QtCore import *
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QMainWindow

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage



import os
import sys
import webbrowser
from settings import *

class HelpWindow(QMainWindow):
    def __init__(self, parent=None):
        super(HelpWindow,self).__init__(parent)

        self.setWindowTitle(settings['applabel'] + " - Help")
        self.setMinimumWidth(600);
        self.setMinimumHeight(600);
        central = QWidget()
        self.setCentralWidget(central)
        vLayout = QVBoxLayout(central)

        self.page = MyHelpWebEnginePage()
        self.browser = QWebEngineView(central)
        self.browser.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.browser.setPage(self.page)

        vLayout.addWidget(self.browser)
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)
        hLayout.addStretch(5)
        dismiss = QPushButton(central)
        dismiss.setText("Close")
        dismiss.clicked.connect(self.hide)
        hLayout.addWidget(dismiss)

    def show(self):
        super(HelpWindow, self).show()
        self.loadPage()

    def loadPage(self):
        self.browser.load(QUrl(settings['help']))

class MyHelpWebEnginePage(QWebEnginePage):
    def __init__(self, parent=None):
        super(MyHelpWebEnginePage, self).__init__(parent)

    def acceptNavigationRequest(self, url, type, isMainFrame):
        if (type == QWebEnginePage.NavigationTypeLinkClicked):
            url = url.toString()
            if not url.startswith(settings['help']):
                webbrowser.open(url)
                return False

        return True
