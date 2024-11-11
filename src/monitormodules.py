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
        self.mainLayout = QFormLayout()
        self.mainLayout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.mainLayout.setLabelAlignment(Qt.AlignLeft)
        self.mainLayout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.mainLayout.setSizeConstraint(QLayout.SetMaximumSize)

        # Status / Loglist
        self.loglist = QTextEdit()
        self.loglist.setLineWrapMode(QTextEdit.NoWrap)
        self.loglist.setWordWrapMode(QTextOption.NoWrap)
        self.loglist.setAcceptRichText(False)
        self.loglist.clear()

        self.mainLayout.addWidget(self.loglist)
        self.setLayout(self.mainLayout)


class PreviewTab(QScrollArea):
    def __init__(self, mainWindow=None):
        QScrollArea.__init__(self, mainWindow)
