from PySide.QtCore import *
from PySide.QtGui import *
from models import *

class Toolbar(QToolBar):
    def __init__(self,parent=None):
        super(Toolbar,self).__init__(parent)
        self.createComponents()
        self.createConnects()
        
        
    def createComponents(self):
        self.actionOpen=self.addAction("Open")
        self.actionExport=self.addAction("Export")
        self.actionNew=self.addAction("Save")
        self.addSeparator()
        self.actionAdd=self.addAction("Add")
        self.actionQuery=self.addAction("Querry")
        self.actionReload=self.addAction("Reload")
        self.actionDelete=self.addAction("Delete")
        
    def createConnects(self):
        self.actionOpen.triggered.connect(self.openFile)
        self.actionNew.triggered.connect(self.newFile)
        self.actionExport.triggered.connect(self.doExport)
        self.actionAdd.triggered.connect(self.doAdd)
        self.actionQuery.triggered.connect(self.doQuery)
        self.actionReload.triggered.connect(self.doReload)
        self.actionDelete.triggered.connect(self.doDelete)


    @Slot()
    def openFile(self):
        if hasattr(self.parent(),"dbpipe"):
            self.parent().dbpipe.session.commit()
            self.parent().dbpipe.session.close()
        
        self.parentWidget().dbpipe=DBPipe(QFileDialog.getOpenFileName(self,"Open DB File",".","DB files (*.db)")[0])
        self.parent().Tree.loadAll()


    @Slot()
    def newFile(self):
        self.parentWidget().dbpipe=DBPipe(QFileDialog.getSaveFileName(self,"Open DB File",".","DB files (*.db)")[0])
        
        
    @Slot()
    def doExport(self):
        
        outfile = open('Site.csv', 'wb')
        outcsv = csv.DictWriter(outfile, delimiter=";",fieldnames={'category', 'username', 'website', 'name','products','company_overview', 'talking_about_count',\
                                         'mission', 'founded', 'phone', 'link', 'likes', 'general_info', 'checkins', 'id', 'description'},extrasaction='ignore',restval="Export Error")
        outcsv.writeheader()
        records = Site.query.all()
        sitedicts=[i.__dict__ for i in records]
        outcsv.writerows(sitedicts)
        outfile.close()


    @Slot()
    def doAdd(self):
        dialog=QDialog(self.parent())
        buttons=QDialogButtonBox(QDialogButtonBox.Apply|QDialogButtonBox.Cancel)
        input=QLineEdit()
       
        
        layout=QVBoxLayout()
        layout.addWidget(input)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
        pass
    @Slot()
    def doQuery(self):
        dialog=QDialog(self.parent())
        dialog.setWindowTitle("Date Selection")
        #dialog elemts
        start=QCalendarWidget()
        start.setGridVisible(True)
        end=QCalendarWidget()
        end.setGridVisible(True)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        #signals and slots
        def query():
            pass
      
        def cancel():
            dialog.close()           
        
        buttons.accepted.connect(query)
        buttons.rejected.connect(cancel)
        #labels
        label1=QLabel("<b>Startdate</b>")
        label1.setAlignment(Qt.AlignCenter)
        label2=QLabel("<b>Enddate</b>")
        label2.setAlignment(Qt.AlignCenter)
        #layout for the dialog pop-up
        layout=QVBoxLayout()
        layout.addWidget(label1)
        layout.addWidget(start)
        layout.addWidget(label2)
        layout.addWidget(end)
        layout.addWidget(buttons)    
        dateform=QTextCharFormat()
        dateform.setFontWeight(90)
        dialog.setLayout(layout)
        #
        if self.parent().Tree.currentItem() is not None:
            if self.parent().Tree.currentItem().parent() is None:
                toplevel=self.parent().Tree.currentItem()
            else:
                toplevel=self.parent().Tree.currentItem().parent()
            for i in Post.query.filter(Post.site_id==toplevel.data(0,0)).all():
                date=QDate().fromString(i.created_time[:10],"yyyy-MM-dd")
                start.setDateTextFormat(date,dateform)
                end.setDateTextFormat(date,dateform)
            dialog.exec_()
        else:
            msg=QMessageBox.warning(self, self.tr("Query missing Facebook Page"),
                               self.tr("Please select a Facebook Page  or a Post of this Page in the main view"),
                               QMessageBox.Ok)
            
           
                    
    @Slot()
    def doReload(self):
        self.parent().Tree.loadAll()
        
    @Slot()
    def doDelete(self):
        candidate=self.parent().Tree.currentItem()
        if self.parent().Tree.indexOfTopLevelItem(candidate)is int(-1):
            self.parent().dbpipe.session.delete(Post.query.get(candidate.data(0,0)))
        else:
            self.parent().dbpipe.session.delete(Site.query.get(candidate.data(0,0)))     
        self.parent().Tree.invisibleRootItem().removeChild(candidate)
        self.parent().dbpipe.session.commit()
        
            
     