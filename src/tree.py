from PySide.QtCore import *
from PySide.QtGui import *
from models import *

class Tree(QTreeView):

    def __init__(self,parent=None,mainWindow=None):
        super(Tree,self).__init__(parent)
        self.mainWindow=mainWindow
                
        #self.setSortingEnabled(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QTreeView.SelectRows)
        self.setUniformRowHeights(True)
                

    @Slot()
    def currentChanged(self,current,previous):
        #show raw data
        self.mainWindow.detailData.clear()
        if current.isValid():     
            item=current.internalPointer()
            for prop in item.data['response']:
                self.mainWindow.detailData.append(prop+": "+json.dumps(item.data['response'].get(prop)))
            
                
        #select level
        level=0
        c=current
        while c.isValid():
            level += 1
            c=c.parent()
        
        self.mainWindow.levelEdit.setValue(level)
            
            
    def selectedIndexesAndChildren(self,level=None,persistent=False):
        selected=[x for x in self.selectedIndexes() if x.column()==0]
        filtered=[]

        def getLevel(index):
            if not index.isValid():
                return 0
            
            treeitem=index.internalPointer()
            if (treeitem.data != None) and (treeitem.data['level'] != None):
                return treeitem.data['level']+1
            else:
                return 0

            
        def addIndex(index):
            if index not in filtered:
                if level==None or level==getLevel(index):
                    if persistent:
                        filtered.append(QPersistentModelIndex(index))
                    else:
                        filtered.append(index)    
                
                if level==None or level>getLevel(index) :
                    self.model().fetchMore(index)
                    child=index.child(0,0)
                    while child.isValid():
                        addIndex(child)
                        child=index.child(child.row()+1,0)
                            
        
        for index in selected:
            addIndex(index)
            
        return filtered     
  