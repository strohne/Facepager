from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import QTextBrowser
import re
import html

class TextViewer(QTextBrowser):

    def __init__(self, *args, **kwargs):
        super(TextViewer, self).__init__(*args, **kwargs)          
        self.setOpenExternalLinks(True)
        self.setStyleSheet("border:0px;")
        self.setReadOnly(True)
        self.document().contentsChanged.connect(self.sizeChanged)
        self.document().documentLayout().documentSizeChanged.connect(self.sizeChanged)
       
    def sizeChanged(self):
        docHeight = self.document().size().height()        
        self.setMaximumHeight(docHeight)
        self.setMinimumHeight(docHeight)
        
    def setText(self,text):
        text = '' if text is None else text
        text = html.escape(text)
        text = self.autoLinkText(text)
        text = self.autoBrText(text)
        self.setHtml(text)

    def autoBrText(self,html):
        return html.replace('\n', '<br />')
        
    def autoLinkText(self,html):
        # match all the urls
        # this returns a tuple with two groups
        # if the url is part of an existing link, the second element
        # in the tuple will be "> or </a>
        # if not, the second element will be an empty string
        urlre = re.compile("(\(?https?://[-A-Za-z0-9+&@#/%?=~_()|!:,.;]*[-A-Za-z0-9+&@#/%=~_()|])(\">|</a>)?")
        urls = urlre.findall(html)
        clean_urls = []
    
        # remove the duplicate matches
        # and replace urls with a link
        for url in urls:
            # ignore urls that are part of a link already
            if url[1]: continue
            c_url = url[0]
            # ignore parens if they enclose the entire url
            if c_url[0] == '(' and c_url[-1] == ')':
                c_url = c_url[1:-1]
    
            if c_url in clean_urls: continue # We've already linked this url
    
            clean_urls.append(c_url)
            # substitute only where the url is not already part of a
            # link element.
            html = re.sub("(?<!(=\"|\">))" + re.escape(c_url), 
                          "<a href=\"" + c_url + "\">" + c_url + "</a>",
                          html)
        return html