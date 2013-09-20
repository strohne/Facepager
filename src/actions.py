from PySide.QtCore import *
from PySide.QtGui import *
from models import *
import csv
import sys
import help

class Actions(object):
    
    def __init__(self,mainWindow):

        self.mainWindow=mainWindow
        
        self.basicActions=QActionGroup(self.mainWindow)       
        self.actionOpen=self.basicActions.addAction(QIcon(":/icons/save.png"),"Open Database")        
        self.actionNew=self.basicActions.addAction(QIcon(":/icons/new.png"),"New Database")        
                
        self.databaseActions=QActionGroup(self.mainWindow)
        self.actionExport=self.databaseActions.addAction(QIcon(":/icons/export.png"),"Export Data")        
        self.actionAdd=self.databaseActions.addAction(QIcon(":/icons/add.png"),"Add Nodes")                
        self.actionDelete=self.databaseActions.addAction(QIcon(":/icons/delete.png"),"Delete Nodes")
        
        self.dataActions=QActionGroup(self.mainWindow)        
        self.actionQuery=self.dataActions.addAction(QIcon(":/icons/fetch.png"),"Query")                
        self.actionShowColumns=self.dataActions.addAction("Show Columns")
        self.actionAddColumn=self.dataActions.addAction("Add Column")
        self.actionUnpack=self.dataActions.addAction("Unpack List")
        #self.actionUnpackData=self.dataActions.addAction("Unpack Data")
        self.actionExpandAll=self.dataActions.addAction(QIcon(":/icons/expand.png"),"Expand nodes")
        self.actionCollapseAll=self.dataActions.addAction(QIcon(":/icons/collapse.png"),"Collapse nodes")
        self.actionHelp=self.dataActions.addAction(QIcon(":/icons/help.png"),"Help")
        
        self.actionLoadPreset=self.dataActions.addAction(QIcon(":/icons/presets.png"),"Presets")

        #connect the actions to their corresponding action functions (slots)
        self.actionOpen.triggered.connect(self.openDB)
        self.actionNew.triggered.connect(self.makeDB)
        self.actionExport.triggered.connect(self.exportNodes)
        self.actionAdd.triggered.connect(self.addNodes)        
        self.actionDelete.triggered.connect(self.deleteNodes)
        self.actionQuery.triggered.connect(self.queryNodes)
        self.actionShowColumns.triggered.connect(self.showColumns)
        self.actionAddColumn.triggered.connect(self.addColumn)
        self.actionUnpack.triggered.connect(self.unpackList)
        self.actionLoadPreset.triggered.connect(self.loadPreset)
        #self.actionUnpackData.triggered.connect(self.unpackData)
        self.actionExpandAll.triggered.connect(self.expandAll)
        self.actionCollapseAll.triggered.connect(self.collapseAll)
        self.actionHelp.triggered.connect(self.help)
       
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
            self.mainWindow.database.connect(fldg.selectedFiles()[0])           
            self.mainWindow.settings.setValue("lastpath",fldg.selectedFiles()[0])                            
            self.mainWindow.updateUI()
            self.mainWindow.treemodel.reset()  

            
    @Slot()
    def makeDB(self):
        #same as openDB-Slot, but now for creating a new one on the file system
        datadir=self.mainWindow.settings.value("lastpath",os.path.expanduser("~"))
        fldg=QFileDialog(caption="Save DB File",directory=datadir,filter="DB files (*.db)")        
        fldg.setAcceptMode(QFileDialog.AcceptSave)
        fldg.setDefaultSuffix("db")
               
        if fldg.exec_():
            self.mainWindow.database.createconnect(fldg.selectedFiles()[0])
            self.mainWindow.settings.setValue("lastpath",fldg.selectedFiles()[0])
            self.mainWindow.updateUI()
            self.mainWindow.treemodel.reset()

        
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
        
        c=0
        for index in todo:            
            progress.setValue(c)
            c+=1            
            
            self.mainWindow.treemodel.deleteNode(index)           
           
            if progress.wasCanceled():
                break 
        progress.cancel()

                     
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
                for key in self.mainWindow.treemodel.customcolumns:
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
                        for key in self.mainWindow.treemodel.customcolumns:                    
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
            self.mainWindow.treemodel.addNodes(input.toPlainText().splitlines())
            dialog.close()  

        def close():
            dialog.close()
            
        #connect the nested functions above to the dialog-buttons
        buttons.accepted.connect(createNodes)
        buttons.rejected.connect(close)
        dialog.exec_()
        
        
    @Slot()     
    def showColumns(self):
        self.mainWindow.treemodel.setCustomColumns(self.mainWindow.fieldList.toPlainText().splitlines())

    @Slot()     
    def addColumn(self):
        key = self.mainWindow.detailTree.selectedKey()
        if key != '': self.mainWindow.fieldList.append(key)
        self.mainWindow.treemodel.setCustomColumns(self.mainWindow.fieldList.toPlainText().splitlines())


    @Slot()     
    def loadPreset(self):
        self.mainWindow.presetWindow.showPresets()

                                        
    @Slot()     
    def unpackList(self):
        key = self.mainWindow.detailTree.selectedKey()
        selected=[x for x in self.mainWindow.tree.selectedIndexes() if x.column()==0]
        if (key != '') and (len(selected)): self.mainWindow.treemodel.unpackList(selected[0],key)   
  
    @Slot()     
    def expandAll(self):
        self.mainWindow.tree.expandAll()

    @Slot()     
    def collapseAll(self):
        self.mainWindow.tree.collapseAll()
              
    @Slot()
    def queryNodes(self):
        #Show progress window         
        progress = QProgressDialog("Fetching data...", "Abort", 0, 0,self.mainWindow)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.forceShow()       
                                
        #Get selected nodes
        level=self.mainWindow.levelEdit.value()
        todo=self.mainWindow.tree.selectedIndexesAndChildren(level)
        progress.setMaximum(len(todo))
                            
        #Fetch data
        c=0
        for index in todo:            
            progress.setValue(c)
            c+=1                        
            self.mainWindow.treemodel.queryData(index)                                  
            if progress.wasCanceled(): break  

        progress.cancel()   

        
 
           