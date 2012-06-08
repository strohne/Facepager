from PySide.QtCore import *
from PySide.QtGui import *
from models import *
import time
import os
import icons
import codecs
import xlwt

class Toolbar(QToolBar):
    '''
    Initialize the main toolbar for the facepager-too that provides the central interface and functions.
    '''
    def __init__(self,parent=None):
        super(Toolbar,self).__init__(parent)
        self.setIconSize(QSize(32,32))
        self.createComponents()
        self.createConnects()
        #disable buttons that do not work without an opened database
        if 'dbpipe'  not in globals():
            self.buttongroup.setEnabled(False)
        
    def createComponents(self):
        #create the interface or toolbar buttons and their corresponding Icons and Names
        self.actionOpen=self.addAction(QIcon(":/icons/data/icons/document-import.png"),"Open Database")
        self.actionExport=self.addAction(QIcon(":icons/data/icons/document-export.png"),"Export Database")
        self.actionNew=self.addAction(QIcon(":/icons/data/icons/window_new.png"),"New Database")
        self.addSeparator()
        self.buttongroup=QActionGroup(self)
        self.actionSave=self.buttongroup.addAction(QIcon(":/icons/data/icons/filesave.png"),"Save Database")
        self.actionReload=self.buttongroup.addAction(QIcon(":/icons/data/icons/view-refresh.png"),"Reload Database")
        self.actionAdd=self.buttongroup.addAction(QIcon(":/icons/data/icons/bookmark_add.png"),"Add Site")
        self.actionQuery=self.buttongroup.addAction(QIcon(":/icons/data/icons/find.png"),"Query")
        self.actionDelete=self.buttongroup.addAction(QIcon(":/icons/data/icons/editdelete.png"),"Delete")

        self.addActions(self.buttongroup.actions())
        
    def createConnects(self):
        #connect the buttons to their corresponding action functions (slots)
        self.actionOpen.triggered.connect(self.openDB)
        self.actionSave.triggered.connect(self.saveDB)
        self.actionNew.triggered.connect(self.makeDB)
        self.actionExport.triggered.connect(self.doExport)
        self.actionAdd.triggered.connect(self.addSite)
        self.actionQuery.triggered.connect(self.queryDB)
        self.actionReload.triggered.connect(self.doReload)
        self.actionDelete.triggered.connect(self.doDelete)


    
    @Slot()
    def openDB(self):
        #open a file dialog with a .db filter
        fldg=QFileDialog(caption="Open DB File",directory=self.parent().settings.value("lastpath","."),filter="DB files (*.db)")
        fldg.setFileMode(QFileDialog.ExistingFile)
        if fldg.exec_():
            #disconnect all existing db connections
            killPipe()
            #open a new,central db connection based on the filename of the dialog
            global dbpipe
            dbpipe=DBPipe(str(fldg.selectedFiles()[0]))
            #remember the last chosen path; saved in the central preferences
            self.parent().settings.setValue("lastpath",fldg.selectedFiles()[0])                 
            #load the Sites
            self.parent().Tree.loadSites()
            #activate the other buttons
            self.buttongroup.setEnabled(True)
            
        
    @Slot()
    def saveDB(self):
        if 'dbpipe' in globals():
            try:
                with saverPipe(dbpipe) as pipe:
                    pipe.commit
            except Exception as e:
                err=QErrorMessage()
                err.showMessage(str(e))
        else:
            QMessageBox.warning(self, self.tr("Save Error"),
                               self.tr("Please create a Database first"),
                               QMessageBox.Ok)
         
            
    @Slot()
    def makeDB(self):
        #same as openDB-Slot, but now for creating a new one on the file system
        fldg=QFileDialog(caption="Save DB File",directory=self.parent().settings.value("lastpath","."),filter="DB files (*.db)")
        # set a Save-Button
        fldg.setAcceptMode(QFileDialog.AcceptSave)
        fldg.setDefaultSuffix("db")
               
        if fldg.exec_():
            killPipe()
            global dbpipe
            #ask for duplicates and delete if
            if os.path.isfile(fldg.selectedFiles()[0]):
                os.remove(fldg.selectedFiles()[0])                
            dbpipe=DBPipe(fldg.selectedFiles()[0])
            self.parent().Tree.loadSites()
            self.buttongroup.setEnabled(True)
        
        
    @Slot()
    def doExport(self):
                            
        if self.parent().Tree.currentItem() is not None:
            site=Site.query.get(self.parent().Tree.currentItem().data(0,0))
            fldg=QFileDialog(caption="Export DB File to XLS",directory=self.parent().settings.value("lastpath","."),filter="XLS Files (*.xls")
            fldg.setAcceptMode(QFileDialog.AcceptSave)
            fldg.setDefaultSuffix("xls")
            
            if fldg.exec_():
                if os.path.isfile(fldg.selectedFiles()[0]):
                    os.remove(fldg.selectedFiles()[0])
                
                x=xlwt.Workbook(encoding="latin-1")
                xs=x.add_sheet("Output")
                
                def itemwriter(obj,col,row):
                    for k,v in obj.__dict__.items():
                        if k not in ('_sa_instance_state','comments'):
                            try:
                                if len(unicode(v))<32760:
                                    xs.write(row,col,unicode(v))
                                else:
                                    xs.write(row,col,"ERROR")
                            except:
                                xs.write(row,col,"ERROR")
                            col+=1

                
                posts=site.posts
                row=1

                for p in posts:
                    xs.write(row,0,"POST")
                    itemwriter(p,1,row)
                    row+=1
                    for c in p.comments:
                        xs.write(row,0,"COMMENT")
                        itemwriter(c,1,row)
                        row+=1                    
                x.save(fldg.selectedFiles()[0])
        else:
            QMessageBox.warning(self, self.tr("Missing Facebook Page"),
                               self.tr("Please select a Facebook Page in the Viewer"),
                               QMessageBox.Ok)
    

            
    @Slot()
    def addSite(self):
        # makes the user add a new facebook page into the db
        dialog=QDialog(self.parent())
        dialog.setWindowTitle("Add a Facebook Page")
        label1=QLabel("<b>Facebook Page:</b>")
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        input=QLineEdit()
        input.setFocusPolicy(Qt.ClickFocus)
        input.setPlaceholderText("Enter a Facebook Page ID or Name here")
        input.setMinimumWidth(500)
        formlay=QFormLayout()
        formlay.addRow(label1,input)
        layout=QVBoxLayout()
        layout.addLayout(formlay)
        layout.addWidget(buttons)
        dialog.setLayout(layout)
        
        def createSite():
            #adds a new Site via API-Call   
            try:
                new=Site(input.text())
                with saverPipe(dbpipe) as pipe:
                    pipe.add(new)
            except Exception as e:
                err=QErrorMessage(dialog)
                err.showMessage(str(e))
            else:
                self.parent().Tree.loadSites()
                dialog.close()

        def close():
            dialog.close()
        #connect the nested functions above to the dialog-buttons
        buttons.accepted.connect(createSite)
        buttons.rejected.connect(close)
        dialog.exec_()
    
    
    
    @Slot()
    def queryDB(self):
        dialog=QDialog(self.parent())
        dialog.setWindowTitle("Date Selection")
        dialog.setMinimumSize(500,500)
        start=QCalendarWidget()
        start.setGridVisible(True)
        end=QCalendarWidget()
        end.setGridVisible(True)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        label1=QLabel("<b>Startdate</b>")
        label1.setAlignment(Qt.AlignCenter)
        label2=QLabel("<b>Enddate</b>")
        label2.setAlignment(Qt.AlignCenter) 
            
        def cancel():
            dialog.close()    
              
        def updateToplevel(toplevel):
            for i in Post.query.filter(Post.site_id==toplevel.data(0,0)).all():
                date=QDate().fromString(i.created_time[:10],"yyyy-MM-dd")
                start.setDateTextFormat(date,dateform)
                end.setDateTextFormat(date,dateform)
                
        def query(toplevel=self.parent().Tree.currentItem()):
                candidate=Site.query.get(toplevel.data(0,0))          
                         
                with saverPipe(dbpipe) as pipe:
                    candidate.getPosts(start.selectedDate().toString("yyyy-MM-dd"),end.selectedDate().toString("yyyy-MM-dd"))
                       
                for new in candidate.posts:
                    date=QDate().fromString(new.created_time[:10],"yyyy-MM-dd")
                    start.setDateTextFormat(date,dateform)
                    end.setDateTextFormat(date,dateform)

                self.parent().Tree.loadPosts(toplevel)
                       
       
        #layout for the dialog pop-up
        layout=QVBoxLayout()
        layout.addWidget(label1)
        layout.addWidget(start)
        layout.addWidget(label2)
        layout.addWidget(end)
        layout.addWidget(buttons)    
        dateform=QTextCharFormat()
        dateform.setFontWeight(90)
        dateform.setBackground(QColor(205,200,177))
        dialog.setLayout(layout)
                      
            
        if self.parent().Tree.currentItem()is not None and self.parent().Tree.currentItem().parent() is None:
            tl=self.parent().Tree.currentItem()
            updateToplevel(tl)
            buttons.accepted.connect(query)
            buttons.rejected.connect(cancel)
            dialog.exec_()
            
        else:
            QMessageBox.warning(self, self.tr("Missing Facebook Page"),
                               self.tr("Please select a Facebook Page in the Viewer"),
                               QMessageBox.Ok)
         
         
               
                    
    @Slot()
    def doReload(self):
        self.parent().Tree.clear()
        self.parent().Tree.loadSites()
        
    @Slot()
    def doDelete(self):
        candidate=self.parent().Tree.currentItem()
        if self.parent().Tree.indexOfTopLevelItem(candidate)is int(-1):
            dbpipe.session.delete(Post.query.get(candidate.data(0,0)))
        else:
            dbpipe.session.delete(Site.query.get(candidate.data(0,0)))     
        self.parent().Tree.invisibleRootItem().removeChild(candidate)
        with saverPipe(dbpipe) as pipe:
            pipe.commit()
