from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QDialog, QMainWindow, QLabel, QScrollArea, QLineEdit, QSizePolicy
from PySide2.QtWebEngineCore import QWebEngineHttpRequest
from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile, QWebEngineSettings

import os
import sys
import webbrowser
import urllib.parse
from datetime import datetime
from utilities import makefilename

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
    scrapeData = Signal(dict,dict,dict)
    newCookie = Signal(str, str)
    loadFinished = Signal(bool)
    #urlChanged = Signal(str)
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

        # Adress bar
        self.addressBar = QLineEdit()
        self.addressBar.returnPressed.connect(self.addressChanged)
        self.mainLayout.addWidget(self.addressBar)
        self.addressBar.setVisible(False)

        # Create WebView
        self.webview = QWebEngineView(self)
        QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
        QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.ScreenCaptureEnabled, True)
        self.webpage = QWebPageCustom(self.webview)
        self.webview.setPage(self.webpage)
        self.mainLayout.addWidget(self.webview)
        self.webview.show()

        # Signals
        self.webpage.logMessage.connect(self.logMessage)
        self.webpage.cookieChanged.connect(self.cookieChanged)
        self.webview.urlChanged.connect(self.urlChanged)
        #self.webpage.urlNotFound.connect(self.urlNotFound)
        #self.browserWebview.loadFinished.connect(self.loadFinished)
        #self.browserWebview.loadStarted.connect(self.loadStarted)

        # Button layout
        self.buttonLayout = QHBoxLayout()
        self.mainLayout.addLayout(self.buttonLayout)

        # Status label
        self.statusLabel = QScrollLabel()

        self.statusLabel.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.Ignored)
        self.buttonLayout.addWidget(self.statusLabel)
        self.statusLabel.textVisible(False)

        # Buttons
        buttonDismiss = QPushButton(self)
        buttonDismiss.setText("Close")
        buttonDismiss.setDefault(True)
        buttonDismiss.clicked.connect(self.close)
        self.buttonLayout.addWidget(buttonDismiss)

    def loadPage(self, url="", headers={}, strip="", foldername=None, filename=None, fileext=None):

        self.url = url
        self.headers = headers
        self.strip = strip
        self.screenshotfolder = foldername

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

        self.webview.load(request)
        self.show()

    @Slot()
    def urlChanged(self, url):
        url = url.toString().replace(self.strip,'')
        self.addressBar.setText(url)

    @Slot()
    def addressChanged(self):
        url = self.addressBar.text()
        request = QWebEngineHttpRequest(QUrl(url))
        self.webview.load(request)

    # Scrape HTML
    def activateScrapeButton(self, handler):
        self.scrapeData.connect(handler)

        buttonScrape = QPushButton(self)
        buttonScrape.setText("Capture")
        buttonScrape.setDefault(True)
        buttonScrape.clicked.connect(self.scrapeDataClicked)
        self.buttonLayout.addWidget(buttonScrape)

        self.addressBar.setVisible(True)

    @Slot()
    def scrapeDataClicked(self):
        self.webpage.toHtml(self.newHtmlData)


    # https://stackoverflow.com/questions/55231170/taking-a-screenshot-of-a-web-page-in-pyqt5
    #screenshots: https://stackoverrun.com/de/q/12970119

    def doScreenShot(self, filename):
        try:
            # page = self.webview.page()
            # oldSize = self.webview.size()
            # size = page.contentsSize().toSize()

            # Version 1
            # oldSize = self.webview.size()
            # self.webview.setAttribute(Qt.WA_DontShowOnScreen)
            # # self.webview.settings().setAttribute(QWebEngineSettings.ShowScrollBars, False)
            # self.webview.resize(self.webpage.contentsSize().toSize())
            # self.webview.show()
            #
            #
            # rect = self.webview.contentsRect()
            # size = rect.size()
            # img = QImage(size, QImage.Format_ARGB32_Premultiplied)
            # img.fill(Qt.transparent)
            # painter = QPainter()
            # painter.begin(img)
            # painter.setRenderHint(QPainter.Antialiasing, True)
            # painter.setRenderHint(QPainter.TextAntialiasing, True)
            # painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            #
            # self.webview.render(painter, QPoint(0, 0))
            # painter.end()
            # img.save(filename)
            #
            # self.webView.resize(oldSize)

            # VErsion 2
            #size = self.webpage.contentsSize().toSize()
            #self.webview.resize(size)
            #self.webview.show()
            pixmap = self.webview.grab() #.save(tmp, b'PNG')
            pixmap.save(filename, 'PNG')

        except Exception as e:
            self.logMessage(str(e))

        return filename


    def newHtmlData(self, html):
        data = {}
        data['title'] = self.webpage.title()

        data['url'] = {
            'final': self.webpage.url().toString().replace(self.strip,''),
            'requested':self.webpage.requestedUrl().toString().replace(self.strip,'')
        }
        data['html'] = html

        if self.screenshotfolder is not None:
            fullfilename = makefilename(data['url']['final'],self.screenshotfolder, fileext='.png',appendtime=True)
            data['screenshot'] = self.doScreenShot(fullfilename)

        options = {}
        options['querytime'] = str(datetime.now())
        options['querystatus'] = 'captured'
        options['querytype'] = 'captured'
        options['objectid'] = 'url.final'
        options['nodedata'] = None

        headers = {}

        self.scrapeData.emit(data, options, headers)


    # Get cookie from initial domain
    def activateCookieButton(self, handler):
        self.newCookie.connect(handler)

        self.statusLabel.textVisible(True)
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
            self.statusLabel.setText("Cookie for domain: "+domain+": "+cookie)


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

class QScrollLabel(QScrollArea):
    def __init__(self, parent=None, text=''):
        super(QScrollLabel,self).__init__(parent)

        self.setStyleSheet("QScrollArea {border: 0px;}")

        self.label = QLabel(text)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)
        self.setWidget(self.label)

    def setText(self,text):
        self.label.setText(text)

    def getText(self,text):
        self.label.getText()

    def textVisible(self,visible):
        self.label.setVisible(visible)