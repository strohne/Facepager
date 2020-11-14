from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QDialog, QMainWindow, QLabel
from PySide2.QtWebEngineCore import QWebEngineHttpRequest
from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile

import os
import sys
import webbrowser
import urllib.parse

class WebDialog(QDialog):
    def __init__(self, parent=None, caption = "", url=""):
        super(WebDialog,self).__init__(parent)

        self.url = url

        self.setWindowTitle(caption)
        self.setMinimumWidth(600);
        self.setMinimumHeight(500);

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

class BrowserDialog(QMainWindow):
    logMessage = Signal(str)
    scrapeData = Signal(str)
    newCookie = Signal(str, str)
    loadFinished = Signal(bool)
    urlChanged = Signal(str)
    urlNotFound = Signal(QUrl)


    def __init__(self, parent=None, caption = "",  width=600, height=600):
        super(BrowserDialog,self).__init__(parent)

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(width, height)
        self.setWindowTitle(caption)

        self.url = None
        self.domain = None
        self.headers = {}
        self.stopped = False
        self.cookie = ''

        central = QWidget()
        self.setCentralWidget(central)
        self.mainLayout = QVBoxLayout(central)
        #self.browserStatus = self.statusBar()

        # Create WebView
        self.browserWebview = QWebEngineView(self)
        self.webpage = QWebPageCustom(self.browserWebview)
        self.browserWebview.setPage(self.webpage)
        self.mainLayout.addWidget(self.browserWebview)
        self.browserWebview.show()

        # Signals
        self.webpage.logMessage.connect(self.logMessage)
        self.webpage.cookieChanged.connect(self.cookieChanged)
        #self.browserWebview.urlChanged.connect(self.urlChanged)
        #self.webpage.urlNotFound.connect(self.urlNotFound)
        #self.browserWebview.loadFinished.connect(self.loadFinished)

        # Buttons
        self.buttonLayout = QHBoxLayout()
        self.mainLayout.addLayout(self.buttonLayout)
        self.statusLabel = QLabel()
        self.buttonLayout.addWidget(self.statusLabel)
        self.buttonLayout.addStretch(5)

        buttonDismiss = QPushButton(self)
        buttonDismiss.setText("Close")
        buttonDismiss.setDefault(True)
        buttonDismiss.clicked.connect(self.close)
        self.buttonLayout.addWidget(buttonDismiss)

    def loadPage(self, url="", headers={}):
        self.url = url
        self.headers = headers

        try:
            targeturl = urllib.parse.urlparse(url)
            self.domain = targeturl.netloc
        except:
            self.domain = None

        request = QWebEngineHttpRequest(QUrl(self.url))
        for key, val in self.headers.items():
            key = key.encode('utf-8')
            val = val.encode('utf-8')
            request.setHeader(QByteArray(key), QByteArray(val))

        self.browserWebview.load(request)
        self.show()

    # Scrape HTML
    def activateScrapeButton(self, handler):
        self.scrapeData.connect(handler)

        buttonScrape = QPushButton(self)
        buttonScrape.setText("Scrape data")
        buttonScrape.setDefault(True)
        buttonScrape.clicked.connect(self.scrapeDataClicked)
        self.buttonLayout.addWidget(buttonScrape)

    @Slot()
    def scrapeDataClicked(self):
        self.webpage.toHtml(self.newHtmlData)

    def newHtmlData(self, data):
        self.scrapeData.emit(data)


    # Get cookie from initial domain
    def activateCookieButton(self, handler):
        self.newCookie.connect(handler)

        buttonCookie = QPushButton(self)
        buttonCookie.setText("Transfer cookie")
        buttonCookie.setDefault(True)
        buttonCookie.clicked.connect(self.transferCookieClicked)
        self.buttonLayout.addWidget(buttonCookie)

    @Slot()
    def transferCookieClicked(self):
        self.newCookie.emit(self.domain, self.cookie)

    @Slot(str, str)
    def cookieChanged(self, domain, cookie):
        if domain == self.domain:
            self.cookie = cookie
            self.statusLabel.setText("Domain: "+domain+". Cookie: "+cookie)


class QWebPageCustom(QWebEnginePage):
    logMessage = Signal(str)
    urlNotFound = Signal(QUrl)
    cookieChanged = Signal(str, str)

    def __init__(self, parent):
        #super(QWebPageCustom, self).__init__(*args, **kwargs)
        super(QWebPageCustom, self).__init__(parent)

        self.cookiecache = {}

        profile = self.profile()
        profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
        profile.clearHttpCache()
        #print(profile.httpUserAgent())

        cookies = profile.cookieStore()
        profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        cookies.deleteAllCookies()
        cookies.cookieAdded.connect(self.cookieAdded)


    @Slot()
    def cookieAdded(self, cookie):
        """
        Save cookies in cookie jar and emit cookie signal
        :param cookie:
        :return:
        """
        #value = cookie.toRawForm(QNetworkCookie.NameAndValueOnly).data().decode()

        cookieid = cookie.domain() + cookie.path()
        domain = cookie.domain().strip(".")
        name = cookie.name().data().decode()
        value = cookie.value().data().decode()

        cookies = self.cookiecache.get(cookieid,{})
        cookies[name] = value
        self.cookiecache[cookieid] = cookies

        fullcookie = '; '.join(['{}={}'.format(k, v) for k, v in cookies.items()])

        self.cookieChanged.emit(domain, fullcookie)

    def supportsExtension(self, extension):
        if extension == QWebEnginePage.ErrorPageExtension:
            return True
        else:
            return False

    def extension(self, extension, option=0, output=0):
        if extension != QWebEnginePage.ErrorPageExtension: return False

        if option.domain == QWebEnginePage.QtNetwork:
            #msg = "Network error (" + str(option.error) + "): " + option.errorString
            #self.logMessage.emit(msg)
            self.urlNotFound.emit(option.url)

        elif option.domain == QWebEnginePage.Http:
            msg = "HTTP error (" + str(option.error) + "): " + option.errorString
            self.logMessage.emit(msg)

        elif option.domain == QWebEnginePage.WebKit:
            msg = "WebKit error (" + str(option.error) + "): " + option.errorString
            self.logMessage.emit(msg)
        else:
            msg = option.errorString
            self.logMessage.emit(msg)

        return True
