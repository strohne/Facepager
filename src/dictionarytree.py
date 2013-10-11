from PySide.QtCore import *
from PySide.QtGui import *
import json

class DictionaryTree(QTreeView):

    def __init__(self,parent=None,mainWindow=None):
        super(DictionaryTree,self).__init__(parent)
        self.mainWindow=mainWindow
                
        #self.setSortingEnabled(True)
        #self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QTreeView.SelectRows)
        #self.setHeaderHidden(True)
        self.setUniformRowHeights(True)
        
        delegate = DictionaryTreeItemDelegate();    
        self.setItemDelegate(delegate);        
        
        self.treemodel = DictionaryTreeModel(self)
        self.setModel(self.treemodel)        

    def showDict(self,data={}):        
        self.treemodel.setdata(data)
        
    def clear(self):
        self.treemodel.reset()     
        
    def selectedKey(self):
        selected=[x for x in self.selectedIndexes() if x.column()==0]
        if not len(selected):return ''
        index = selected[0]
        if not index.isValid():
            return ''
        
        treeitem=index.internalPointer()
        return treeitem.keyPath()

    def keyPressEvent(self, e):
        if e == QKeySequence.Copy:
            self.copyToClipboard()
        else:
            super(DictionaryTree,self).keyPressEvent(e)
            
                
    def copyToClipboard(self):
        clipboard = QApplication.clipboard()
        try:
            value = self.treemodel.getdata()                        
            clipboard.setText(json.dumps(value,indent=4))
        except Exception as e:
            clipboard.setText('')
            
                            

class DictionaryTreeItemDelegate(QItemDelegate):

    def sizeHint(self,option, index ):
        return QSize(20,17);

class DictionaryTreeModel(QAbstractItemModel):
    def __init__(self, parent=None, dic={}):
        super(DictionaryTreeModel, self).__init__(parent)        
        self.rootItem = DictionaryTreeItem(('root',{}), None)
        self.setdata(dic)

    def reset(self):        
        self.rootItem.clear()
        super(DictionaryTreeModel, self).reset()     
          
    def setdata(self,data):
        self.reset()
        if not isinstance(data, dict): data = {'':data} 
        items = data.items()
        #items.sort()
        for item in items:
            newparent = DictionaryTreeItem(item, self.rootItem)
            self.rootItem.appendChild(newparent)
    
    def getdata(self):
        key,val = self.rootItem.getValue()
        return val

    def columnCount(self, parent):
        return 2   
                                            

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            captions=['Key','Value']                
            return captions[section] if section < len(captions) else ""

        return None

    def data(self, index, role):
        if not index.isValid():
            return None

        if role != Qt.DisplayRole:
            return None

        item = index.internalPointer()
       
        if index.column()==0:
            return item.itemDataKey
        elif index.column()==1:
            return item.itemDataValue              

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

    def __init__(self, dicItem, parentItem):
        key, value = dicItem
        self.parentItem = parentItem
        self.childItems = []

        self.itemDataKey = key
        self.itemDataValue = value
        self.itemDataType = "atom"
        
        if isinstance(value, dict):            
            items = value.items()
            self.itemDataValue = '{'+str(len(items))+'}'
            self.itemDataType = "dict"
            #items.sort()
            for item in items:
                self.appendChild(DictionaryTreeItem(item, self))
        
        elif isinstance(value, list):
            self.itemDataValue = '['+str(len(value))+']'
            self.itemDataType = "list"
            for idx,item in enumerate(value):
                self.appendChild(DictionaryTreeItem((idx,item), self))

        elif isinstance(value, (int, long)):
            self.itemDataType = "atom"
            self.itemDataValue = str(value)            
        else:
            self.itemDataType = "atom"
            self.itemDataValue = value
            

    def clear(self):
        self.childItems=[]
        
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
        node = self;
        nodes = [];
        while (node.parentItem != None):
            nodes.insert(0,str(node.itemDataKey))
            node = node.parentItem
        
        return '.'.join(nodes)
    
    def getValue(self):
        if self.itemDataType == "atom":
            value = self.itemDataValue 
        elif self.itemDataType == "list":
            value = [node.getValue()[1] for node in self.childItems]
        elif (self.itemDataType == "dict"):
            value = {}
            for node in self.childItems:
                key, val = node.getValue()
                value[key] = val
        
        return (self.itemDataKey,value)
        