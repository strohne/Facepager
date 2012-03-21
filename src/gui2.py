import sys
import csv
from PySide.QtCore import *
from PySide.QtGui import *
from models import *

class MainWindow(QMainWindow):
    
    def __init__(self,central=None):
        super(MainWindow,self).__init__()
        self.createComponents()
    
    def createComponents(self):
        self.Tree=Tree(parent=self)
        self.toolbar=self.addToolBar(Toolbar(self))    
        self.setCentralWidget(self.Tree) 

    def createLayouts(self):
        layoutMain=QHBoxLayout()
        layoutMain.addWidget(self.Tree)
        self.setLayout(layoutMain)
    

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
        self.parent().Tree.clear()
        self.parent().Tree.loadAll()


    @Slot()
    def newFile(self):
        self.parentWidget().dbpipe=DBPipe(QFileDialog.getSaveFileName(self,"Open DB File",".","DB files (*.db)")[0])
        
        
    @Slot()
    def doExport(self):
        outfile = open('Site.csv', 'wb')
        outcsv = csv.DictWriter(outfile,fieldnames={'category', 'username', 'website', 'name', 'company_overview', 'talking_about_count',\
                                         'mission', 'founded', 'phone', 'link', 'likes', 'general_info', 'checkins', 'id', 'description'},extrasaction='ignore',restval="NONE")
        outcsv.writeheader()
        records = Site.query.all()
        sitedicts=[i.__dict__ for i in records]
        outcsv.writerows(sitedicts)
        outfile.close()


    @Slot()
    def doAdd(self):
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
        dateform=QTextCharFormat()
        dateform.setFontWeight(90)
        for i in Post.query.filter(Post.site_id==self.parent().Tree.currentItem().data(0,0)).all():
            date=QDate().fromString(i.created_time[:10],"yyyy-MM-dd")
            start.setDateTextFormat(date,dateform)
            end.setDateTextFormat(date,dateform)
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
                
        dialog.setLayout(layout)
        dialog.exec_()
    @Slot()
    def doReload(self):
        pass
    @Slot()
    def doDelete(self):
        pass


class DBPipe(object):
    
    def __init__(self,filename):
        self.engine = create_engine('sqlite:///%s'%filename, convert_unicode=True)
        self.session = scoped_session(sessionmaker(autocommit=False,autoflush=False,bind=self.engine))
        Base.query = self.session.query_property()
        Base.metadata.create_all(bind=self.engine)
        


class Tree(QTreeWidget):

    def __init__(self,parent=None):
        super(Tree,self).__init__(parent)
        self.setColumnCount(5)
        self.setHeaderLabels(["ID","AUTHOR","DESCRIPTION","CONTENT","DATE"])
        self.setSortingEnabled(True)

    def addSite(self,site):
        if type(site)!=list:
            site=[site,]
        items=[]
        for item in site:
            site_item=QTreeWidgetItem(self)
            site_item.setSizeHint(0,QSize(5,5))
            site_item.setSizeHint(3,QSize(5,5))
            site_item.setSizeHint(2,QSize(5,5))
            site_item.setText(0,item.id)
            site_item.setText(1,item.name)
            site_item.setText(2,item.description)
            site_item.setText(3,item.mission)
            items.append(site_item)
        
        self.insertTopLevelItems(0,items)
        
    def addPost(self,post,site_item):
        if type(post)!=list:
            post=[site_item,]
        items=[]
        
        for item in post:
           if item.site_id==int(site_item.data(0,0)): 
                post_item=QTreeWidgetItem(parent=site_item)
                post_item.setText(0,item.id)
                post_item.setText(1,item.author)
                post_item.setText(2,item.description)
                post_item.setText(3,item.message)
                post_item.setText(4,item.created_time[:10])
                post_item.setSizeHint(0,QSize(5,5))
                post_item.setSizeHint(3,QSize(5,5))
                post_item.setSizeHint(2,QSize(5,5))
                items.append(post_item)
        site_item.addChildren(items)
        
    
    def loadAll(self):
        self.addSite(Site.query.all())
        for tl in range(0,self.topLevelItemCount(),1):
            tli=self.topLevelItem(tl)
            self.addPost(Post.query.filter(Post.site_id==tli.data(0,0)).all(),tli)
        


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main=MainWindow()
    main.show()
    sys.exit(app.exec_())

