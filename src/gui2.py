import sys
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
        self.actionOpen=self.addAction("Open",self.openFile)
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
        
        self.parentWidget().dbpipe=DBPipe(QFileDialog.getOpenFileName(None,"Open DB File",".","DB files (*.db)")[0])
        self.parent().Tree.clear()
        self.parent().Tree.loadAll()


    @Slot()
    def newFile(self):
        self.parentWidget().dbpipe=DBPipe(QFileDialog.getSaveFileName(None,"Open DB File",".","DB files (*.db)")[0])
        
        
    @Slot()
    def doExport(self):
        pass
    @Slot()
    def doAdd(self):
        pass
    @Slot()
    def doQuery(self):
        pass
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
        self.setColumnCount(3)
        self.setHeaderLabels(["ID","DESCRIPTION","DATE"])
        self.setSortingEnabled(True)

    def addSite(self,site):
        if type(site)!=list:
            site=[site,]
        items=[]
        for item in site:
            site_item=QTreeWidgetItem(self)
            site_item.setText(1,item.description)
            site_item.setText(0,item.id)
            items.append(site_item)
        
        self.insertTopLevelItems(0,items)
        
    def addPost(self,post,site_item):
        if type(post)!=list:
            post=[site_item,]
        items=[]
        
        for item in post:
           if item.site_id==int(site_item.data(0,0)):
                print "match"            
                post_item=QTreeWidgetItem(parent=site_item)
                post_item.setText(1,item.message)
                post_item.setText(0,item.id)
                post_item.setText(2,str(item.created_time))
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

