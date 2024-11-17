import sys
import argparse
from datetime import datetime

import html

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QWidget, QStyleFactory, QMainWindow


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
from dialogs.webdialog import PreLoginWebDialog, LoginWebDialog, BrowserDialog, WebPageCustom
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

class PreviewTab(QWidget):
    logMessage = Signal(str)
    captureData = Signal(dict, dict, dict)
    newCookie = Signal(str, str)

    def __init__(self, parent=None, caption="", width=600, height=600):
        super(PreviewTab, self).__init__(parent)

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(width, height)
        self.setWindowTitle(caption)

        self.url = None
        self.domain = None
        self.headers = {}
        self.stopped = False
        self.cookie = ''
        self.ready = False

        # Main layout
        self.mainLayout = QVBoxLayout(self)

        # Address bar and buttons layout
        self.topLayout = QHBoxLayout()
        self.mainLayout.addLayout(self.topLayout)

        # Status bar for cookie info
        self.cookieLabel = QLabel(self)
        self.cookieLabel.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Ignored)
        self.cookieLabel.setText("Cookie: Not captured")
        self.mainLayout.addWidget(self.cookieLabel)

        self.loadingLabel = QLabel()
        self.mainLayout.addWidget(self.loadingLabel)

        # Address bar (URL input)
        self.addressBar = QLineEdit(self)
        self.addressBar.returnPressed.connect(self.addressChanged)
        self.topLayout.addWidget(self.addressBar)

        # WebView to load and display content
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

        # Buttons (close, capture, etc.)
        self.buttonLayout = QHBoxLayout()
        self.topLayout.addLayout(self.buttonLayout)

        buttonDismiss = QPushButton("Close", self)
        buttonDismiss.clicked.connect(self.close)
        self.buttonLayout.addWidget(buttonDismiss)

    def loadPage(self, url="", headers={}, options={}, foldername=None, filename=None, fileext=None):
        self.url = url
        self.headers = headers
        self.options = options
        self.foldername = foldername
        self.filename = filename
        self.fileext = fileext

        # Parse domain from URL
        try:
            targeturl = urllib.parse.urlparse(url)
            self.domain = targeturl.netloc
        except:
            self.domain = None

        # Set up HTTP request with headers
        request = QWebEngineHttpRequest(QUrl(self.url))
        for key, val in self.headers.items():
            key = key.encode('utf-8')
            val = val.encode('utf-8')
            request.setHeader(QByteArray(key), QByteArray(val))

        self.webview.load(request)

    def loadStarted(self):
        self.ready = False
        self.loadingLabel.setText('Loading...')

    def loadFinished(self, ok):
        if ok:
            self.ready = True
            self.loadingLabel.setText('Loading finished.')
        else:
            self.ready = False
            self.loadingLabel.setText('Loading failed.')

    def urlChanged(self, url):
        self.addressBar.setText(url.toString())

    def addressChanged(self):
        url = self.addressBar.text()
        self.webview.load(QUrl(url))

    def activateCaptureButton(self, handler):
        self.captureData.connect(handler)

        buttonCapture = QPushButton("Capture", self)
        buttonCapture.clicked.connect(self.captureDataClicked)
        self.buttonLayout.addWidget(buttonCapture)

    def captureDataClicked(self):
        data = {}
        data['title'] = self.webpage.title()

        try:
            data['url'] = {
                'final': self.webpage.url().toString(),
                'requested': self.webpage.requestedUrl().toString()
            }
            data['text'] = self.getHtml()
            data['plaintext'] = self.getText()

            if self.foldername is not None:
                # Screenshot
                try:
                    fullfilename = f"{self.foldername}/{self.filename}_screenshot.png"
                    data['screenshot'] = self.getScreenShot(fullfilename)
                except Exception as e:
                    self.logMessage.emit(f"Error capturing screenshot: {str(e)}")

                # HTML file
                try:
                    fullfilename = f"{self.foldername}/{self.filename}.html"
                    with open(fullfilename, 'wb') as file:
                        file.write(data['text'].encode())
                except Exception as e:
                    self.logMessage.emit(f"Error saving HTML: {str(e)}")

                # PDF
                try:
                    fullfilename = f"{self.foldername}/{self.filename}.pdf"
                    self.webpage.printToPdf(fullfilename)
                    data['pdf'] = fullfilename
                except Exception as e:
                    self.logMessage.emit(f"Error printing to PDF: {str(e)}")

        except Exception as e:
            data['error'] = str(e)
            self.logMessage.emit(str(e))

        options = self.options
        options['querytime'] = str(datetime.now())
        options['querystatus'] = 'captured'
        options['querytype'] = 'captured'

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

    def getScreenShot(self, filename):
        try:
            oldSize = self.webview.size()
            newSize = self.webpage.contentsSize().toSize()
            self.webview.resize(newSize)

            # Wait for resize
            waitstart = QDateTime.currentDateTime()
            while (waitstart.msecsTo(QDateTime.currentDateTime()) < 500):
                QApplication.processEvents()
                time.sleep(0.01)

            # Capture
            pixmap = QPixmap(newSize)
            self.webview.render(pixmap)
            pixmap.save(filename, 'PNG')

            self.webview.resize(oldSize)
        except Exception as e:
            self.logMessage.emit(str(e))

        return filename

    def activateCookieButton(self, handler):
        self.newCookie.connect(handler)

        self.cookieLabel.setText("Cookie: Not captured")
        buttonCookie = QPushButton("Transfer cookie", self)
        buttonCookie.clicked.connect(self.transferCookieClicked)
        self.buttonLayout.addWidget(buttonCookie)

    def transferCookieClicked(self):
        self.newCookie.emit(self.domain, self.cookie)

    def cookieChanged(self, domain, cookie):
        if domain == self.domain:
            self.cookie = cookie
            self.cookieLabel.setText(f"Cookie: {self.cookie}")
