from PySide.QtCore import *
from PySide.QtGui import *
from models import *
import codecs
import xlwt

class Actions(object):
    
    def __init__(self,mainWindow):

        self.mainWindow=mainWindow
        
        self.basicActions=QActionGroup(self.mainWindow)        
        self.actionOpen=self.basicActions.addAction(QIcon(":/icons/data/icons/document-import.png"),"Open Database")        
        self.actionNew=self.basicActions.addAction(QIcon(":/icons/data/icons/window_new.png"),"New Database")        
                
        self.databaseActions=QActionGroup(self.mainWindow)
        self.actionExport=self.databaseActions.addAction(QIcon(":icons/data/icons/document-export.png"),"Export Data")        
        self.actionAdd=self.databaseActions.addAction(QIcon(":/icons/data/icons/bookmark_add.png"),"Add Nodes")                
        self.actionDelete=self.databaseActions.addAction(QIcon(":/icons/data/icons/editdelete.png"),"Delete Selected Nodes")
        
        self.facebookActions=QActionGroup(self.mainWindow)        
        self.actionQuery=self.facebookActions.addAction(QIcon(":/icons/data/icons/find.png"),"Query")                
        self.actionShowColumns=self.facebookActions.addAction("Show Columns")

        #connect the actions to their corresponding action functions (slots)
        self.actionOpen.triggered.connect(self.openDB)
        self.actionNew.triggered.connect(self.makeDB)
        self.actionExport.triggered.connect(self.exportNodes)
        self.actionAdd.triggered.connect(self.addNodes)        
        self.actionDelete.triggered.connect(self.deleteNodes)
        self.actionQuery.triggered.connect(self.queryNodes)
        self.actionShowColumns.triggered.connect(self.showColumns)
        
    @Slot()
    def openDB(self):
        #open a file dialog with a .db filter
        fldg=QFileDialog(caption="Open DB File",directory=self.mainWindow.settings.value("lastpath","."),filter="DB files (*.db)")
        fldg.setFileMode(QFileDialog.ExistingFile)
        if fldg.exec_():
            self.mainWindow.database.connect(fldg.selectedFiles()[0])           
            self.mainWindow.settings.setValue("lastpath",fldg.selectedFiles()[0])                            
            self.mainWindow.updateUI()
            self.mainWindow.treemodel.reset()  

            
    @Slot()
    def makeDB(self):
        #same as openDB-Slot, but now for creating a new one on the file system
        fldg=QFileDialog(caption="Save DB File",directory=self.mainWindow.settings.value("lastpath","."),filter="DB files (*.db)")        
        fldg.setAcceptMode(QFileDialog.AcceptSave)
        fldg.setDefaultSuffix("db")
               
        if fldg.exec_():
            self.mainWindow.database.createconnect(fldg.selectedFiles()[0])
            self.mainWindow.settings.setValue("lastpath",fldg.selectedFiles()[0])
            self.mainWindow.updateUI()
            self.mainWindow.treemodel.reset()

        
    @Slot()
    def deleteNodes(self):   
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
                                        
        fldg=QFileDialog(caption="Export DB File to XLS",filter="XLS Files (*.xls)")
        fldg.setAcceptMode(QFileDialog.AcceptSave)
        fldg.setDefaultSuffix("xls")
        
        if fldg.exec_():               
            progress = QProgressDialog("Saving data...", "Abort", 0, 0,self.mainWindow)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)
            progress.forceShow()   
             
            
                   
            #selected=self.mainWindow.tree.selectedIndexesAndChildren()
            progress.setMaximum(Node.query.count())
            allnodes=Node.query.all()
                    
            if os.path.isfile(fldg.selectedFiles()[0]):
                os.remove(fldg.selectedFiles()[0])
            
            x=xlwt.Workbook(encoding="latin-1")
            
            sheets={}
            def getSheet(level=1):
                sh = sheets.get(level,None)
                if sh==None:                  
                    xs=x.add_sheet("Level"+str(level))                                       
                    xs.write(0,0,"level")
                    xs.write(0,1,"id")
                    xs.write(0,2,"parent_id")                
                    xs.write(0,3,"facebook id")
                    xs.write(0,4,"query status")
                    xs.write(0,5,"query time")
                    xs.write(0,6,"query type")
                    xs.write(0,7,"response")
                    col=8    
                    for key in self.mainWindow.treemodel.customcolumns:
                        xs.write(0,col,key)
                        col+=1                     
                    
                    sh={'sheet':xs,'row':1}
                    sheets[level]=sh
                return sh                    
            
            

            no=0                
            for node in allnodes:                     
                progress.setValue(no)
                no+=1            
               
                if progress.wasCanceled():
                    break 
                                   
                sh=getSheet(node.level)
                xs=sh['sheet']
                row=sh['row']
                sh['row']+=1
                             
                xs.write(row,0,node.level)
                xs.write(row,1,node.id)
                xs.write(row,2,node.parent_id)
                xs.write(row,3,node.facebookid)
                xs.write(row,4,node.querystatus)
                xs.write(row,5,node.querytime)
                xs.write(row,6,node.querytype)
                xs.write(row,7,node.response_raw)
                        
                col=8    
                for key in self.mainWindow.treemodel.customcolumns:                    
                    value=node.getResponseValue(key)
                    try:
                        if len(unicode(key))<32760:
                            xs.write(row,col,unicode(value))
                        else:
                            xs.write(row,col,"ERROR")
                    except:
                        xs.write(row,col,"ERROR")
                    col+=1  
                                      
                  
            progress.cancel()                  
            x.save(fldg.selectedFiles()[0])

    

    @Slot()
    def addNodes(self):
        if not self.mainWindow.database.connected:
            return False
        
        # makes the user add a new facebook object into the db
        dialog=QDialog(self.mainWindow)
        dialog.setWindowTitle("Add Facebook Objects")
        layout=QVBoxLayout()
        
        label=QLabel("<b>Facebook IDs (one ID per line):</b>")
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
            

        #Set options
        relation=self.mainWindow.relationEdit.currentText()
        options={}
        options['since']=self.mainWindow.sinceEdit.date().toString("yyyy-MM-dd")
        options['until']=self.mainWindow.untilEdit.date().toString("yyyy-MM-dd")
        options['offset']=self.mainWindow.offsetEdit.value()
        options['limit']=self.mainWindow.limitEdit.value()
        
        #Fetch data
        c=0
        for index in todo:            
            progress.setValue(c)
            c+=1            
            
            self.mainWindow.treemodel.queryData(index,relation,options)           
           
            if progress.wasCanceled():
                break 
 

        progress.cancel()   

        
 
           