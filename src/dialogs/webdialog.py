from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QDialog, QMainWindow, QLabel, QScrollArea, QLineEdit, QSizePolicy, QApplication
from PySide2.QtWebEngineCore import QWebEngineHttpRequest
from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile, QWebEngineSettings

import os
import sys
import time
import webbrowser
import urllib.parse
from datetime import datetime
from utilities import makefilename

class PreLoginWebDialog(QDialog):
    def __init__(self, parent=None, caption = "", url=""):
        super(PreLoginWebDialog, self).__init__(parent)

        self.url = url

        self.setWindowTitle(caption)
        self.setMinimumWidth(600);
        self.setMinimumHeight(500);

        vLayout = QVBoxLayout()
        self.setLayout(vLayout)

        self.browser = QWebEngineView(self)
        self.page = WebPageCustom(self.browser)
        self.page.allowLinks = False
        self.page.loadFinished.connect(self.loadFinished)
        self.page.loadStarted.connect(self.loadStarted)

        self.browser.setPage(self.page)
        vLayout.addWidget(self.browser)


        # Buttons
        hLayout = QHBoxLayout()
        vLayout.addLayout(hLayout)

        # Status bar
        self.reloadButton = QPushButton(self)
        self.reloadButton.setText("Retry")
        self.reloadButton.clicked.connect(self.loadPage)
        self.reloadButton.setVisible(False)
        hLayout.addWidget(self.reloadButton)

        self.loadingLabel = QLabel()
        hLayout.addWidget(self.loadingLabel)

        hLayout.addStretch(5)

        buttonDismiss = QPushButton(self)
        buttonDismiss.setText("Cancel")
        buttonDismiss.clicked.connect(self.reject)
        hLayout.addWidget(buttonDismiss)

        self.buttonProceed = QPushButton(self)
        self.buttonProceed.setText("Proceed")
        self.buttonProceed.setDefault(True)
        self.buttonProceed.clicked.connect(self.accept)
        self.buttonProceed.setDisabled(True)
        hLayout.addWidget(self.buttonProceed)

        self.loadPage()
        #browser.setBackgroundRole(QPalette.Window)

    def loadPage(self):
        self.browser.load(QUrl(self.url))

    def show(self):
        #super(WebDialog, self).show()
        return self.exec_()


    @Slot()
    def loadStarted(self):
        self.ready = False
        self.buttonProceed.setDisabled(True)
        self.loadingLabel.setText('Loading...')


    @Slot()
    def loadFinished(self, ok):
        if ok:
            self.ready = True
            self.reloadButton.setVisible(False)
            self.buttonProceed.setDisabled(False)
            self.loadingLabel.setText('Loading finished.')
        else:
            self.ready = False
            self.reloadButton.setVisible(True)
            self.buttonProceed.setDisabled(True)
            self.loadingLabel.setText('Loading failed.')

class BrowserDialog(QMainWindow):
    logMessage = Signal(str)
    captureData = Signal(dict, dict, dict)
    newCookie = Signal(str, str)
    #loadFinished = Signal(bool)
    #urlChanged = Signal(str)
    #urlNotFound = Signal(QUrl)


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
        self.ready = False

        central = QWidget()
        self.setCentralWidget(central)
        self.mainLayout = QVBoxLayout(central)

        self.topLayout = QHBoxLayout()
        self.mainLayout.addLayout(self.topLayout)

        # Status bar
        self.statusBar = self.statusBar()
        self.cookieLabel = QScrollLabel()
        self.cookieLabel.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Ignored)
        self.statusBar.addWidget(self.cookieLabel)
        self.cookieLabel.textVisible(False)

        self.loadingLabel = QLabel()
        self.statusBar.addPermanentWidget(self.loadingLabel)


        # Adress bar
        self.addressBar = QLineEdit()
        self.addressBar.returnPressed.connect(self.addressChanged)
        self.topLayout.addWidget(self.addressBar)
        self.addressBar.setVisible(False)

        # Create WebView
        self.webview = QWebEngineView(self)
        QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
        QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.ScreenCaptureEnabled, True)
        self.webpage = WebPageCustom(self.webview)
        self.webview.setPage(self.webpage)
        self.mainLayout.addWidget(self.webview)
        self.webview.show()

        # Signals
        self.webpage.logMessage.connect(self.logMessage)
        self.webpage.cookieChanged.connect(self.cookieChanged)
        self.webview.urlChanged.connect(self.urlChanged)
        self.webpage.loadFinished.connect(self.loadFinished)
        self.webpage.loadStarted.connect(self.loadStarted)

        #self.webpage.urlNotFound.connect(self.urlNotFound)
        #self.browserWebview.loadFinished.connect(self.loadFinished)
        #self.browserWebview.loadStarted.connect(self.loadStarted)

        # Button layout
        self.buttonLayout = QHBoxLayout()
        self.topLayout.addLayout(self.buttonLayout)

        # Buttons
        buttonDismiss = QPushButton(self)
        buttonDismiss.setText("Close")
        buttonDismiss.setDefault(True)
        buttonDismiss.clicked.connect(self.close)
        self.buttonLayout.addWidget(buttonDismiss)

    def loadPage(self, url="", headers={}, options={}, foldername=None, filename=None, fileext=None):

        self.url = url
        self.headers = headers
        self.options = options
        self.strip = self.options.get('access_token', '')

        self.foldername = foldername
        self.filename = filename
        self.fileext = fileext

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
    def loadStarted(self):
        self.ready = False
        self.loadingLabel.setText('Loading...')

    @Slot()
    def loadFinished(self, ok):
        if ok:
            self.ready = True
            
            self.loadingLabel.setText('Loading finished.')
        else:
            self.ready = False
            self.loadingLabel.setText('Loading failed.')

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
    def activateCaptureButton(self, handler):
        self.captureData.connect(handler)

        buttonCapture = QPushButton(self)
        buttonCapture.setText("Capture")
        buttonCapture.setDefault(True)
        buttonCapture.clicked.connect(self.captureDataClicked)
        self.buttonLayout.addWidget(buttonCapture)

        self.addressBar.setVisible(True)

    @Slot()
    def captureDataClicked(self):

        # Metadata
        data = {}
        data['title'] = self.webpage.title()

        try:
            data['url'] = {
                'final': self.webpage.url().toString().replace(self.strip,''),
                'requested':self.webpage.requestedUrl().toString().replace(self.strip,'')
            }

            # Fetch HTML
            data['text'] = self.getHtml()

            # Fetch plain text
            data['plaintext'] = self.getText()


            if self.foldername is not None:

                # Screenshot
                try:
                    fullfilename = makefilename(data['url']['final'], self.foldername, self.filename, fileext='.png', appendtime=True)
                    data['screenshot'] = self.getScreenShot(fullfilename)
                except Exception as e:
                    self.logMessage.emit('Error capturing screenshot: '+str(e))

                # HTML file
                try:
                    fullfilename = makefilename(data['url']['final'], self.foldername, self.filename,self.fileext, appendtime=True)
                    file = open(fullfilename, 'wb')
                    if file is not None:
                        try:
                            file.write(data['text'].encode())
                        finally:
                            file.close()
                except Exception as e:
                    self.logMessage.emit('Error saving HTML: '+str(e))

                # PDF
                try:
                    fullfilename = makefilename(data['url']['final'],self.foldername,self.filename, fileext='.pdf',appendtime=True)
                    self.webpage.printToPdf(fullfilename)
                    data['pdf'] = fullfilename
                except Exception as e:
                    self.logMessage.emit('Error printing to PDF: ' + str(e))

        except Exception as e:
            data['error'] = str(e)
            self.logMessage.emit(str(e))

        # Options
        options = self.options
        options['querytime'] = str(datetime.now())
        options['querystatus'] = 'captured'
        options['querytype'] = 'captured'
        #options['objectid'] = 'url.final'
        #options['nodedata'] = None

        # Headers
        headers = {}

        self.captureData.emit(data, options, headers)

    def getHtml(self):
        def newHtmlData(html):
            self.capturedhtml = html

        self.capturedhtml = None
        self.webpage.toHtml(newHtmlData)

        waitstart = QDateTime.currentDateTime()
        while (self.capturedhtml is None) and (waitstart.msecsTo(QDateTime.currentDateTime()) < 1000):
            QApplication.processEvents()
            time.sleep(0.01)

        return self.capturedhtml

    def getText(self):

        def newTextData(txt):
            self.capturedtext = txt

        self.capturedtext = None
        self.webpage.toPlainText(newTextData)

        waitstart = QDateTime.currentDateTime()
        while (self.capturedtext is None) and (waitstart.msecsTo(QDateTime.currentDateTime()) < 1000):
            QApplication.processEvents()
            time.sleep(0.01)

        return self.capturedtext

    # https://stackoverflow.com/questions/55231170/taking-a-screenshot-of-a-web-page-in-pyqt5
    #screenshots: https://stackoverrun.com/de/q/12970119

    def getScreenShot(self, filename):
        try:
            # Resize
            oldSize = self.webview.size()
            newSize = self.webpage.contentsSize().toSize()
            self.webview.settings().setAttribute(QWebEngineSettings.ShowScrollBars, False)
            self.webview.setAttribute(Qt.WA_DontShowOnScreen, True)
            self.webview.resize(newSize)
            #self.webview.repaint()
            #self.webview.show()

            # Wait for resize
            waitstart = QDateTime.currentDateTime()
            while (waitstart.msecsTo(QDateTime.currentDateTime()) < 500):
                QApplication.processEvents()
                time.sleep(0.01)

            # Capture
            pixmap = QPixmap(newSize)
            self.webview.render(pixmap, QPoint(0, 0))
            pixmap.save(filename, 'PNG')

            self.webview.resize(oldSize)
            self.webview.setAttribute(Qt.WA_DontShowOnScreen, False)
            self.webview.settings().setAttribute(QWebEngineSettings.ShowScrollBars, True)
            self.repaint()

        except Exception as e:
            self.logMessage.emit(str(e))

        return filename

    # Get cookie from initial domain
    def activateCookieButton(self, handler):
        self.newCookie.connect(handler)

        self.cookieLabel.textVisible(True)
        buttonCookie = QPushButton(self)
        buttonCookie.setText("Transfer cookie")
        buttonCookie.setDefault(True)
        buttonCookie.clicked.connect(self.transferCookieClicked)
        self.buttonLayout.addWidget(buttonCookie)

        self.addressBar.setVisible(True)

    @Slot()
    def transferCookieClicked(self):
        self.newCookie.emit(self.domain, self.cookie)

    @Slot(str, str)
    def cookieChanged(self, domain, cookie):
        if domain == self.domain:
            self.cookie = cookie
            self.cookieLabel.setText("Cookie for domain: " + domain + ": " + cookie)


class WebPageCustom(QWebEnginePage):
    logMessage = Signal(str)
    urlNotFound = Signal(QUrl)
    cookieChanged = Signal(str, str)

    def __init__(self, parent):
        #super(QWebPageCustom, self).__init__(*args, **kwargs)
        super(WebPageCustom, self).__init__(parent)

        self.allowLinks = True
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
        if extension != QWebEnginePage.ErrorPageExtension:
            return False

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

    def acceptNavigationRequest(self, url, type, isMainFrame):
        if self.allowLinks == True:
            return True
        elif (type == QWebEnginePage.NavigationTypeLinkClicked):
            url = url.toString()
            webbrowser.open(url)
            return False

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