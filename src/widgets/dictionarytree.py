from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *
import json
from utilities import *
import re
import os
import sys

class DictionaryTree(QTreeView):
    def __init__(self, parent=None, apiWindow = None):
        super(DictionaryTree, self).__init__(parent)
        self.setSelectionBehavior(QTreeView.SelectRows)
        self.setUniformRowHeights(True)

        delegate = DictionaryTreeItemDelegate()
        self.setItemDelegate(delegate)

        self.treemodel = DictionaryTreeModel(self,apiWindow)
        self.setModel(self.treemodel)
        self.setColumnWidth(0, 200)

        # enable righklick-context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

    def on_context_menu(self,event):
        contextmenu = QMenu()
        actionCopy = QAction(QIcon(":/icons/toclip.png"), "Copy to Clipboard", self.copyToClipboard())
        contextmenu.addAction(actionCopy)
        contextmenu.exec_(self.viewport().mapToGlobal(event))

    def showDict(self, data={},itemtype='Generic', options= {}):
        self.treemodel.setdata(data, itemtype, options)
        self.expandAll()

    def clear(self):
        self.treemodel.reset()

    def selectedValue(self):
        selected = [x for x in self.selectedIndexes() if x.column() == 0]
        if not len(selected):
            return ''
        index = selected[0]
        if not index.isValid():
            return ''

        treeitem = index.internalPointer()
        return treeitem.itemDataValue

    def selectedKey(self):
        selected = [x for x in self.selectedIndexes() if x.column() == 0]
        if not len(selected):
            return ''
        index = selected[0]
        if not index.isValid():
            return ''

        treeitem = index.internalPointer()
        return treeitem.keyPath()

    def copyToClipboard(self):
        clipboard = QApplication.clipboard()
        try:
            value = self.treemodel.getdata()
            clipboard.setText(json.dumps(value, indent=4))
        except Exception:
            clipboard.setText('')


class DictionaryTreeItemDelegate(QItemDelegate):
    pass
    #def sizeHint(self, option, index):
    #    return QSize(20, 17)


class DictionaryTreeModel(QAbstractItemModel):
    def __init__(self, parent=None, apiWindow = None):
        super(DictionaryTreeModel, self).__init__(parent)
        self.apiWindow = apiWindow
        self.itemtype = None
        self.options = None
        self.rootItem = DictionaryTreeItem(('root', {}), None,self)
        self.setdata()

    def reset(self):
        self.beginResetModel()
        self.rootItem.clear()
        self.endResetModel()

    def setdata(self, data = {}, itemtype='', options={}):
        self.reset()

        self.itemtype = itemtype
        self.options = options

        self.module = itemtype.split(':', 1)[0] if itemtype is not None else ''
        self.basepath = options.get('basepath','')
        self.path = options.get('resource', '')
        self.fieldprefix = options.get('nodedata') + '.' if options.get('nodedata', None) is not None else ''

        if not isinstance(data, dict):
            data = {'': data}
        items = list(data.items())
        #items.sort()
        for item in items:
            newparent = DictionaryTreeItem(item, self.rootItem,self)
            self.rootItem.appendChild(newparent)

    def getdata(self):
        key, val = self.rootItem.getValue()
        return val

    def getDoc(self, field):
        try:
            if (self.apiWindow is not None) and (self.itemtype is not None):
                field = self.fieldprefix+field
                doc = self.apiWindow.getApiField(self.module,self.basepath, self.path, field)
                doc = field if doc is None else doc
            else:
                doc = field

            return doc
        except:
            return field

    def columnCount(self, parent):
        return 2


    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            captions = ['Key', 'Value']
            return captions[section] if section < len(captions) else ''

        return None

    def data(self, index, role):
        if not index.isValid():
            return None
        item = index.internalPointer()

        if role == Qt.ToolTipRole:
            return item.itemToolTip

        if role == Qt.TextAlignmentRole:
            return Qt.AlignTop | Qt.AlignLeft

        if role != Qt.DisplayRole:
            return None

        if index.column() == 0:
            return item.itemDataKey
        elif index.column() == 1:
            value = item.itemDataShortValue \
                if item.itemDataShortValue is not None \
                else item.itemDataValue

            return value

        return None

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        if not childItem:
            return QModelIndex()

        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            return self.rootItem.childCount()
        else:
            return parent.internalPointer().childCount()


class DictionaryTreeItem(object):
    def __init__(self, dicItem, parentItem,model):
        key, value = dicItem
        self.model = model
        self.parentItem = parentItem
        self.childItems = []

        self.itemDataKey = key
        self.itemDataValue = value
        self.itemDataType = 'atom'
        self.itemDataShortValue = None

        self.itemToolTip = wraptip(self.model.getDoc(self.keyPath()))

        if isinstance(value, dict):
            items = list(value.items())
            self.itemDataValue = '{' + str(len(items)) + '}'
            self.itemDataType = 'dict'
            #items.sort()
            for item in items:
                self.appendChild(DictionaryTreeItem(item, self,self.model))

        elif isinstance(value, list):
            self.itemDataValue = '[' + str(len(value)) + ']'
            self.itemDataType = 'list'
            for idx, item in enumerate(value):
                self.appendChild(DictionaryTreeItem((idx, item), self,self.model))

        elif isinstance(value, int):
            self.itemDataType = 'atom'
            self.itemDataValue = str(value)

            try:
                self.itemToolTip = self.itemToolTip + "<p>"+str(wraptip(self.itemDataValue))+"</p>"
            except:
                pass

        else:
            self.itemDataType = 'atom'
            self.itemDataValue = value

            try:
                self.itemDataShortValue = str(self.itemDataValue)
                self.itemDataShortValue = self.itemDataShortValue.replace('\n', ' ').replace('\r', '')
                self.itemDataShortValue = (self.itemDataShortValue[:2000] + '...')\
                    if len(self.itemDataShortValue) > 2000 else self.itemDataShortValue
            except:
                self.itemDataShortValue = ""

            try:
                self.itemToolTip = self.itemToolTip + "<p>"+str(wraptip(self.itemDataShortValue))+"</p>"
            except:
                pass


    def clear(self):
        self.childItems = []

    def appendChild(self, item):
        self.childItems.append(item)

    def child(self, row):
        return self.childItems[row]

    def childCount(self):
        return len(self.childItems)

    def columnCount(self):
        return 2


    def parent(self):
        return self.parentItem

    def row(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)
        return 0

    def keyPath(self):
        node = self
        nodes = []
        while node.parentItem is not None:
            nodes.insert(0, str(node.itemDataKey))
            node = node.parentItem

        return '.'.join(nodes)

    def getValue(self):
        if self.itemDataType == 'atom':
            value = self.itemDataValue
        elif self.itemDataType == 'list':
            value = [node.getValue()[1] for node in self.childItems]
        elif self.itemDataType == 'dict':
            value = {}
            for node in self.childItems:
                key, val = node.getValue()
                value[key] = val
                # any pythonic dict-update solution here?
        return (self.itemDataKey, value)
