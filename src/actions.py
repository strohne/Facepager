from PySide.QtCore import *
from PySide.QtGui import *
from database import *
import csv
import sys
import help

class Actions(object):
    
    def __init__(self,mainWindow):

        self.mainWindow=mainWindow
        
        self.basicActions=QActionGroup(self.mainWindow)               
        self.actionOpen=self.basicActions.addAction(QIcon(":/icons/save.png"),"Open Database")
        self.actionOpen.triggered.connect(self.openDB)
                
        self.actionNew=self.basicActions.addAction(QIcon(":/icons/new.png"),"New Database")        
        self.actionNew.triggered.connect(self.makeDB)
                
        self.databaseActions=QActionGroup(self.mainWindow)
        self.actionExport=self.databaseActions.addAction(QIcon(":/icons/export.png"),"Export Data")
        self.actionExport.triggered.connect(self.exportNodes)
                
        self.actionAdd=self.databaseActions.addAction(QIcon(":/icons/add.png"),"Add Nodes")
        self.actionAdd.triggered.connect(self.addNodes)
                        
        self.actionDelete=self.databaseActions.addAction(QIcon(":/icons/delete.png"),"Delete Nodes")
        self.actionDelete.triggered.connect(self.deleteNodes)
        
        self.dataActions=QActionGroup(self.mainWindow)        
        self.actionQuery=self.dataActions.addAction(QIcon(":/icons/fetch.png"),"Query")
        self.actionQuery.triggered.connect(self.querySelectedNodes)

        self.actionTimer=self.dataActions.addAction(QIcon(":/icons/fetch.png"),"Time")
        self.actionTimer.triggered.connect(self.setupTimer)        
                        
        self.actionShowColumns=self.dataActions.addAction("Show Columns")
        self.actionShowColumns.triggered.connect(self.showColumns)
        
        self.actionAddColumn=self.dataActions.addAction("Add Column")
        self.actionAddColumn.triggered.connect(self.addColumn)
        
        self.actionUnpack=self.dataActions.addAction("Unpack List")
        self.actionUnpack.triggered.connect(self.unpackList)
        
        self.actionExpandAll=self.dataActions.addAction(QIcon(":/icons/expand.png"),"Expand nodes")
        self.actionExpandAll.triggered.connect(self.expandAll)
        
        self.actionCollapseAll=self.dataActions.addAction(QIcon(":/icons/collapse.png"),"Collapse nodes")
        self.actionCollapseAll.triggered.connect(self.collapseAll)
        
        self.actionHelp=self.dataActions.addAction(QIcon(":/icons/help.png"),"Help")
        self.actionHelp.triggered.connect(self.help)
        
        self.actionLoadPreset=self.dataActions.addAction(QIcon(":/icons/presets.png"),"Presets")
        self.actionLoadPreset.triggered.connect(self.loadPreset)
       
    @Slot()
    def help(self):
        self.mainWindow.helpwindow.show()
                
    @Slot()
    def openDB(self):
        #open a file dialog with a .db filter
        datadir=self.mainWindow.settings.value("lastpath",os.path.expanduser("~"))
        fldg=QFileDialog(caption="Open DB File",directory=datadir,filter="DB files (*.db)")
        fldg.setFileMode(QFileDialog.ExistingFile)
        if fldg.exec_():
            self.mainWindow.timerWindow.cancelTimer()
            self.mainWindow.database.connect(fldg.selectedFiles()[0])           
            self.mainWindow.settings.setValue("lastpath",fldg.selectedFiles()[0])                            
            self.mainWindow.updateUI()
            self.mainWindow.tree.treemodel.reset()  

            
    @Slot()
    def makeDB(self):
        #same as openDB-Slot, but now for creating a new one on the file system
        datadir=self.mainWindow.settings.value("lastpath",os.path.expanduser("~"))
        fldg=QFileDialog(caption="Save DB File",directory=datadir,filter="DB files (*.db)")        
        fldg.setAcceptMode(QFileDialog.AcceptSave)
        fldg.setDefaultSuffix("db")
               
        if fldg.exec_():
            self.mainWindow.timerWindow.cancelTimer()
            self.mainWindow.database.createconnect(fldg.selectedFiles()[0])
            self.mainWindow.settings.setValue("lastpath",fldg.selectedFiles()[0])
            self.mainWindow.updateUI()
            self.mainWindow.tree.treemodel.reset()

        
    @Slot()
    def deleteNodes(self):

        reply = QMessageBox.question(self.mainWindow, 'Delete Nodes',"Are you sure to delete all selected nodes?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes: return
    
        progress = QProgressDialog("Deleting data...", "Abort", 0, 0,self.mainWindow)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.forceShow()     
                             
        todo=self.mainWindow.tree.selectedIndexesAndChildren(None,True)
        progress.setMaximum(len(todo))            
        
        #self.mainWindow.tree.treemodel.beginResetModel()
        
        c=0
        for index in todo:            
            progress.setValue(c)
            c+=1            
            
            self.mainWindow.tree.treemodel.deleteNode(index)           
           
            if progress.wasCanceled():
                break 
        progress.cancel()
        #self.mainWindow.tree.treemodel.endResetModel()

                     
    @Slot()
    def exportNodes(self):
        fldg=QFileDialog(caption="Export DB File to CSV",filter="CSV Files (*.csv)")
        fldg.setAcceptMode(QFileDialog.AcceptSave)
        fldg.setDefaultSuffix("csv")
        
        if fldg.exec_():               
            progress = QProgressDialog("Saving data...", "Abort", 0, 0,self.mainWindow)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.forceShow()   
                                     
            progress.setMaximum(Node.query.count())
                                
            if os.path.isfile(fldg.selectedFiles()[0]):
                os.remove(fldg.selectedFiles()[0])
           
            
            f = open(fldg.selectedFiles()[0], 'wb')
            try:
                writer = csv.writer(f,delimiter=';',quotechar='"', quoting=csv.QUOTE_ALL,doublequote=True,lineterminator='\r\n')
                
                #headers    
                row=["level","id","parent_id","object_id","query_status","query_time","query_type"]
                for key in self.mainWindow.tree.treemodel.customcolumns:
                    row.append(key)                        
                writer.writerow(row)
                
                #rows             
                page=0
                no=0  
                while True:            
                    allnodes=Node.query.offset(page*5000).limit(5000).all()
    
                    for node in allnodes:      
                        if progress.wasCanceled():
                            break
                                   
                        progress.setValue(no)
                        no+=1               
                        
                        row=[node.level,node.id,node.parent_id,node.objectid_encoded,node.objecttype,node.querystatus,node.querytime,node.querytype]    
                        for key in self.mainWindow.tree.treemodel.customcolumns:                    
                            row.append(node.getResponseValue(key,"utf-8"))    
                         
                        writer.writerow(row) 
                     
                    if progress.wasCanceled():
                        break
                               
                    if len(allnodes) == 0:
                        break
                    else:
                        page +=1   
                                             
            finally:                                            
                f.close()                            
                progress.cancel()
                                             

    @Slot()
    def addNodes(self):
        if not self.mainWindow.database.connected:
            return False
        
        # makes the user add a new facebook object into the db
        dialog=QDialog(self.mainWindow)
        dialog.setWindowTitle("Add Nodes")
        layout=QVBoxLayout()
        
        label=QLabel("<b>Object IDs (one ID per line):</b>")
        layout.addWidget(label)
        
        input=QTextEdit()           
        input.setMinimumWidth(500)
        input.LineWrapMode=QTextEdit.NoWrap
        input.acceptRichText=False
        input.setFocus()
        layout.addWidget(input)
                
        
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        def createNodes():
            self.mainWindow.tree.treemodel.addNodes(input.toPlainText().splitlines())
            dialog.close()  

        def close():
            dialog.close()
            
        #connect the nested functions above to the dialog-buttons
        buttons.accepted.connect(createNodes)
        buttons.rejected.connect(close)
        dialog.exec_()
        
        
    @Slot()     
    def showColumns(self):
        self.mainWindow.tree.treemodel.setCustomColumns(self.mainWindow.fieldList.toPlainText().splitlines())

    @Slot()     
    def addColumn(self):
        key = self.mainWindow.detailTree.selectedKey()
        if key != '': self.mainWindow.fieldList.append(key)
        self.mainWindow.tree.treemodel.setCustomColumns(self.mainWindow.fieldList.toPlainText().splitlines())


    @Slot()     
    def loadPreset(self):
        self.mainWindow.presetWindow.showPresets()

                                        
    @Slot()     
    def unpackList(self):
        key = self.mainWindow.detailTree.selectedKey()
        #selected=[x for x in self.mainWindow.tree.selectedIndexes() if x.column()==0]
        selected = self.mainWindow.tree.selectedIndexes() 
        if (key != ''):
            for item in selected: self.mainWindow.tree.treemodel.unpackList(item,key)   
  
    @Slot()     
    def expandAll(self):
        self.mainWindow.tree.expandAll()

    @Slot()     
    def collapseAll(self):
        self.mainWindow.tree.collapseAll()


    def queryNodes(self,indexes=False,module = False,options = False):
        #Show progress window                 
        progress = QProgressDialog("Fetching data...", "Abort", 0, 0,self.mainWindow)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.forceShow()       
                                
        #Get selected nodes
        if indexes == False:
            level=self.mainWindow.levelEdit.value()
            indexes=self.mainWindow.tree.selectedIndexesAndChildren(level)
        
        if module == False: module = self.mainWindow.RequestTabs.currentWidget()
        if options == False: options=module.getOptions();
                
        progress.setMaximum(len(indexes))
                            
        #Fetch data
        c=0
        for index in indexes:            
            progress.setValue(c)
            c+=1                        
            self.mainWindow.tree.treemodel.queryData(index,module,options)                                  
            if progress.wasCanceled(): break  

        progress.cancel()   
                      
    @Slot()
    def querySelectedNodes(self):
        self.queryNodes()

    @Slot()
    def setupTimer(self):
        #Get data
        level=self.mainWindow.levelEdit.value()
        indexes=self.mainWindow.tree.selectedIndexesAndChildren(level,True)
        module = self.mainWindow.RequestTabs.currentWidget()
        options=module.getOptions();        
                        
        #show timer window
        self.mainWindow.timerWindow.setupTimer({'indexes':indexes,'nodecount':len(indexes),'module':module,'options':options})
                            
        
 
           