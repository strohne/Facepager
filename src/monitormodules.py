import sys
import argparse
from datetime import datetime
from dialogs.webdialog import *

import html

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QWidget, QStyleFactory, QMainWindow
from PySide2.QtWebEngineCore import QWebEngineHttpRequest


from icons import *
from widgets.datatree import DataTree
from widgets.dictionarytree import DictionaryTree
from actions import *
from apimodules import *
from dialogs.help import *
from widgets.progressbar import ProgressBar
from dialogs.presets import *
from dialogs.timer import *
from dialogs.apiviewer import *
from dialogs.dataviewer import *
from dialogs.selectnodes import *
from dialogs.transfernodes import *

import logging
import threading
from server import Server, RequestHandler

import urllib.parse
import urllib.request, urllib.error

import secrets
import hashlib, hmac, base64
from mimetypes import guess_all_extensions
from datetime import datetime
from copy import deepcopy
import re
import os, sys, time
import io
from collections import OrderedDict
import threading

from PySide2.QtWebEngineWidgets import QWebEngineView
from PySide2.QtCore import Qt, QUrl

from PySide2.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QScrollArea, QSizePolicy
from PySide2.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PySide2.QtCore import Signal, Qt

import requests
from requests.exceptions import *
from rauth import OAuth1Service
from requests_oauthlib import OAuth2Session
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from urllib.parse import urlparse, parse_qs, parse_qsl

import webbrowser
import cchardet
import json

if sys.version_info.major < 3:
    from urllib import url2pathname
else:
    from urllib.request import url2pathname

import dateutil.parser

from dialogs.folder import SelectFolderDialog
from server import LoginServer
from widgets.paramedit import *
from utilities import *

class StatusTab(QWidget):
    def __init__(self, mainWindow=None):
        super(StatusTab, self).__init__(mainWindow)

        # Layout
        statusLayout = QFormLayout()
        statusLayout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        statusLayout.setLabelAlignment(Qt.AlignLeft)
        statusLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        statusLayout.setSizeConstraint(QLayout.SetMaximumSize)

        # Status / Loglist
        self.loglist = QTextEdit()
        self.loglist.setLineWrapMode(QTextEdit.NoWrap)
        self.loglist.setWordWrapMode(QTextOption.NoWrap)
        self.loglist.setAcceptRichText(False)
        self.loglist.clear()

        statusLayout.addWidget(self.loglist)
        self.setLayout(statusLayout)


# class PreviewTab(QMainWindow):
#     logMessage = Signal(str)
#     captureData = Signal(dict, dict, dict)
#     newCookie = Signal(str, str)
#
#     # loadFinished = Signal(bool)
#     # urlChanged = Signal(str)
#     # urlNotFound = Signal(QUrl)
#
#     def __init__(self, parent=None, caption="", width=600, height=600):
#         super(PreviewTab, self).__init__(parent)
#
#         self.setAttribute(Qt.WA_DeleteOnClose)
#         self.resize(width, height)
#         self.setWindowTitle(caption)
#
#         self.url = None
#         self.domain = None
#         self.headers = {}
#         self.stopped = False
#         self.cookie = ''
#         self.ready = False
#
#         central = QWidget()
#         self.setCentralWidget(central)
#         self.mainLayout = QVBoxLayout(central)
#
#         self.topLayout = QHBoxLayout()
#         self.mainLayout.addLayout(self.topLayout)
#
#         # Status bar
#         self.statusBar = self.statusBar()
#         self.cookieLabel = QScrollLabel()
#         self.cookieLabel.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Ignored)
#         self.statusBar.addWidget(self.cookieLabel)
#         self.cookieLabel.textVisible(False)
#
#         self.loadingLabel = QLabel()
#         self.statusBar.addPermanentWidget(self.loadingLabel)
#
#         # Adress bar
#         self.addressBar = QLineEdit()
#         self.addressBar.returnPressed.connect(self.addressChanged)
#         self.topLayout.addWidget(self.addressBar)
#         self.addressBar.setVisible(False)
#
#         # Create WebView
#         self.webview = QWebEngineView(self)
#         QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
#         QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.ScreenCaptureEnabled, True)
#         self.webpage = WebPageCustom(self.webview)
#         self.webview.setPage(self.webpage)
#         self.mainLayout.addWidget(self.webview)
#         self.webview.show()
#
#         # Signals
#         self.webpage.logMessage.connect(self.logMessage)
#         self.webpage.cookieChanged.connect(self.cookieChanged)
#         self.webview.urlChanged.connect(self.urlChanged)
#         self.webpage.loadFinished.connect(self.loadFinished)
#         self.webpage.loadStarted.connect(self.loadStarted)
#
#         # Button layout
#         self.buttonLayout = QHBoxLayout()
#         self.topLayout.addLayout(self.buttonLayout)
#
#         # Buttons
#         buttonDismiss = QPushButton(self)
#         buttonDismiss.setText("Close")
#         buttonDismiss.setDefault(True)
#         buttonDismiss.clicked.connect(self.close)
#         self.buttonLayout.addWidget(buttonDismiss)
#
#     def loadPage(self, url="", headers={}, options={}, foldername=None, filename=None, fileext=None):
#
#         self.url = url
#         self.headers = headers
#         self.options = options
#         self.strip = self.options.get('access_token', '')
#
#         self.foldername = foldername
#         self.filename = filename
#         self.fileext = fileext
#
#         try:
#             targeturl = urllib.parse.urlparse(url)
#             self.domain = targeturl.netloc
#         except:
#             self.domain = None
#
#         request = QWebEngineHttpRequest(QUrl(self.url))
#         for key, val in self.headers.items():
#             key = key.encode('utf-8')
#             val = val.encode('utf-8')
#             request.setHeader(QByteArray(key), QByteArray(val))
#
#         self.webview.load(request)
#         self.show()
#
#     @Slot()
#     def loadStarted(self):
#         self.ready = False
#         self.loadingLabel.setText('Loading...')
#
#     @Slot()
#     def loadFinished(self, ok):
#         if ok:
#             self.ready = True
#
#             self.loadingLabel.setText('Loading finished.')
#         else:
#             self.ready = False
#             self.loadingLabel.setText('Loading failed.')
#
#     @Slot()
#     def urlChanged(self, url):
#         url = url.toString().replace(self.strip, '')
#         self.addressBar.setText(url)
#
#     @Slot()
#     def addressChanged(self):
#         url = self.addressBar.text()
#         request = QWebEngineHttpRequest(QUrl(url))
#         self.webview.load(request)
#
#     # Scrape HTML
#     def activateCaptureButton(self, handler):
#         self.captureData.connect(handler)
#
#         buttonCapture = QPushButton(self)
#         buttonCapture.setText("Capture")
#         buttonCapture.setDefault(True)
#         buttonCapture.clicked.connect(self.captureDataClicked)
#         self.buttonLayout.addWidget(buttonCapture)
#
#         self.addressBar.setVisible(True)
#
#     @Slot()
#     def captureDataClicked(self):
#
#         # Metadata
#         data = {}
#         data['title'] = self.webpage.title()
#
#         try:
#             data['url'] = {
#                 'final': self.webpage.url().toString().replace(self.strip, ''),
#                 'requested': self.webpage.requestedUrl().toString().replace(self.strip, '')
#             }
#
#             # Fetch HTML
#             data['text'] = self.getHtml()
#
#             # Fetch plain text
#             data['plaintext'] = self.getText()
#
#             if self.foldername is not None:
#
#                 # Screenshot
#                 try:
#                     fullfilename = makefilename(data['url']['final'], self.foldername, self.filename, fileext='.png',
#                                                 appendtime=True)
#                     data['screenshot'] = self.getScreenShot(fullfilename)
#                 except Exception as e:
#                     self.logMessage.emit('Error capturing screenshot: ' + str(e))
#
#                 # HTML file
#                 try:
#                     fullfilename = makefilename(data['url']['final'], self.foldername, self.filename, self.fileext,
#                                                 appendtime=True)
#                     file = open(fullfilename, 'wb')
#                     if file is not None:
#                         try:
#                             file.write(data['text'].encode())
#                         finally:
#                             file.close()
#                 except Exception as e:
#                     self.logMessage.emit('Error saving HTML: ' + str(e))
#
#                 # PDF
#                 try:
#                     fullfilename = makefilename(data['url']['final'], self.foldername, self.filename, fileext='.pdf',
#                                                 appendtime=True)
#                     self.webpage.printToPdf(fullfilename)
#                     data['pdf'] = fullfilename
#                 except Exception as e:
#                     self.logMessage.emit('Error printing to PDF: ' + str(e))
#
#         except Exception as e:
#             data['error'] = str(e)
#             self.logMessage.emit(str(e))
#
#         # Options
#         options = self.options
#         options['querytime'] = str(datetime.now())
#         options['querystatus'] = 'captured'
#         options['querytype'] = 'captured'
#         # options['objectid'] = 'url.final'
#         # options['nodedata'] = None
#
#         # Headers
#         headers = {}
#
#         self.captureData.emit(data, options, headers)
#
#     def getHtml(self):
#         def newHtmlData(html):
#             self.capturedhtml = html
#
#         self.capturedhtml = None
#         self.webpage.toHtml(newHtmlData)
#
#         waitstart = QDateTime.currentDateTime()
#         while (self.capturedhtml is None) and (waitstart.msecsTo(QDateTime.currentDateTime()) < 1000):
#             QApplication.processEvents()
#             time.sleep(0.01)
#
#         return self.capturedhtml
#
#     def getText(self):
#
#         def newTextData(txt):
#             self.capturedtext = txt
#
#         self.capturedtext = None
#         self.webpage.toPlainText(newTextData)
#
#         waitstart = QDateTime.currentDateTime()
#         while (self.capturedtext is None) and (waitstart.msecsTo(QDateTime.currentDateTime()) < 1000):
#             QApplication.processEvents()
#             time.sleep(0.01)
#
#         return self.capturedtext
#
#     # https://stackoverflow.com/questions/55231170/taking-a-screenshot-of-a-web-page-in-pyqt5
#     # screenshots: https://stackoverrun.com/de/q/12970119
#
#     def getScreenShot(self, filename):
#         try:
#             # Resize
#             oldSize = self.webview.size()
#             newSize = self.webpage.contentsSize().toSize()
#             self.webview.settings().setAttribute(QWebEngineSettings.ShowScrollBars, False)
#             self.webview.setAttribute(Qt.WA_DontShowOnScreen, True)
#             self.webview.resize(newSize)
#             # self.webview.repaint()
#             # self.webview.show()
#
#             # Wait for resize
#             waitstart = QDateTime.currentDateTime()
#             while (waitstart.msecsTo(QDateTime.currentDateTime()) < 500):
#                 QApplication.processEvents()
#                 time.sleep(0.01)
#
#             # Capture
#             pixmap = QPixmap(newSize)
#             self.webview.render(pixmap, QPoint(0, 0))
#             pixmap.save(filename, 'PNG')
#
#             self.webview.resize(oldSize)
#             self.webview.setAttribute(Qt.WA_DontShowOnScreen, False)
#             self.webview.settings().setAttribute(QWebEngineSettings.ShowScrollBars, True)
#             self.repaint()
#
#         except Exception as e:
#             self.logMessage.emit(str(e))
#
#         return filename
#
#     # Get cookie from initial domain
#     def activateCookieButton(self, handler):
#         self.newCookie.connect(handler)
#
#         self.cookieLabel.textVisible(True)
#         buttonCookie = QPushButton(self)
#         buttonCookie.setText("Transfer cookie")
#         buttonCookie.setDefault(True)
#         buttonCookie.clicked.connect(self.transferCookieClicked)
#         self.buttonLayout.addWidget(buttonCookie)
#
#         self.addressBar.setVisible(True)
#
#     @Slot()
#     def transferCookieClicked(self):
#         self.newCookie.emit(self.domain, self.cookie)
#
#     @Slot(str, str)
#     def cookieChanged(self, domain, cookie):
#         if domain == self.domain:
#             self.cookie = cookie
#             self.cookieLabel.setText("Cookie for domain: " + domain + ": " + cookie)

class PreviewTab(QWidget):
    logMessage = Signal(str)
    captureData = Signal(dict, dict, dict)
    newCookie = Signal(str, str)

    def __init__(self, parent=None):
        super(PreviewTab, self).__init__(parent)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self.url = None
        self.domain = None
        self.headers = {}
        self.stopped = False
        self.cookie = ''
        self.strip = ''
        self.ready = False

        # Layout
        self.mainLayout = QVBoxLayout(self)
        self.setLayout(self.mainLayout)

        self.topLayout = QHBoxLayout()
        self.mainLayout.addLayout(self.topLayout)

        # Status bar
        # self.statusLayout = QHBoxLayout()
        # self.mainLayout.addLayout(self.statusLayout)

        self.cookieLabel = QScrollLabel()
        self.cookieLabel.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Ignored)
        # self.statusLayout.addWidget(self.cookieLabel)
        self.cookieLabel.textVisible(False)

        self.loadingLabel = QLabel()
        # self.statusLayout.addWidget(self.loadingLabel)

        # Address bar
        self.addressBar = QLineEdit()
        self.addressBar.returnPressed.connect(self.addressChanged)
        self.topLayout.addWidget(self.addressBar)
        self.addressBar.setVisible(True)

        # Web view
        self.webview = QWebEngineView(self)
        QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
        QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.ScreenCaptureEnabled, True)
        self.webpage = WebPageCustom(self.webview)
        self.webview.setPage(self.webpage)
        self.mainLayout.addWidget(self.webview)

        # Signals
        self.webpage.logMessage.connect(self.logMessage)
        self.webpage.cookieChanged.connect(self.cookieChanged)
        self.webview.urlChanged.connect(self.urlChanged)
        self.webpage.loadFinished.connect(self.loadFinished)
        self.webpage.loadStarted.connect(self.loadStarted)

    def loadPage(self, url="", headers={}, options={}, foldername=None, filename=None, fileext=None):

        self.url = url
        # self.url = "https://github.com/strohne/Facepager"
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
        print("Page loading started.")

    @Slot()
    def loadFinished(self, ok):
        print(f"Page loading finished: {ok}")
        if ok:
            self.ready = True

            self.loadingLabel.setText('Loading finished.')
        else:
            self.ready = False
            self.loadingLabel.setText('Loading failed.')

    @Slot()
    def urlChanged(self, url):
        url = url.toString().replace(self.strip, '')
        self.addressBar.setText(url)

    @Slot()
    def addressChanged(self):
        url = self.addressBar.text()
        request = QWebEngineHttpRequest(QUrl(url))
        self.webview.load(request)

    # Scrape HTML
    # def activateCaptureButton(self, handler):
    #     self.captureData.connect(handler)
    #
    #     buttonCapture = QPushButton(self)
    #     buttonCapture.setText("Capture")
    #     buttonCapture.setDefault(True)
    #     buttonCapture.clicked.connect(self.captureDataClicked)
    #     self.buttonLayout.addWidget(buttonCapture)
    #
    #     self.addressBar.setVisible(True)

    @Slot()
    def captureDataClicked(self):

        # Metadata
        data = {}
        data['title'] = self.webpage.title()

        try:
            data['url'] = {
                'final': self.webpage.url().toString().replace(self.strip, ''),
                'requested': self.webpage.requestedUrl().toString().replace(self.strip, '')
            }

            # Fetch HTML
            data['text'] = self.getHtml()

            # Fetch plain text
            data['plaintext'] = self.getText()

            if self.foldername is not None:

                # Screenshot
                try:
                    fullfilename = makefilename(data['url']['final'], self.foldername, self.filename, fileext='.png',
                                                appendtime=True)
                    data['screenshot'] = self.getScreenShot(fullfilename)
                except Exception as e:
                    self.logMessage.emit('Error capturing screenshot: ' + str(e))

                # HTML file
                try:
                    fullfilename = makefilename(data['url']['final'], self.foldername, self.filename, self.fileext,
                                                appendtime=True)
                    file = open(fullfilename, 'wb')
                    if file is not None:
                        try:
                            file.write(data['text'].encode())
                        finally:
                            file.close()
                except Exception as e:
                    self.logMessage.emit('Error saving HTML: ' + str(e))

                # PDF
                try:
                    fullfilename = makefilename(data['url']['final'], self.foldername, self.filename, fileext='.pdf',
                                                appendtime=True)
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
        # options['objectid'] = 'url.final'
        # options['nodedata'] = None

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
    # screenshots: https://stackoverrun.com/de/q/12970119

    def getScreenShot(self, filename):
        try:
            # Resize
            oldSize = self.webview.size()
            newSize = self.webpage.contentsSize().toSize()
            self.webview.settings().setAttribute(QWebEngineSettings.ShowScrollBars, False)
            self.webview.setAttribute(Qt.WA_DontShowOnScreen, True)
            self.webview.resize(newSize)
            # self.webview.repaint()
            # self.webview.show()

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