import sys
from PySide.QtCore import *
from PySide.QtGui import *
from models import *

class MainWindow(QMainWindow):
    
    def __init__(self,central=None):
        super(MainWindow,self).__init__()
        self.createComponents()
    
    def createComponents(self):
        #self.Tree=Tree()
        self.toolbar=self.addToolBar(Toolbar(self))    
        self.setCentralWidget(self.toolbar) 

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
        self.parentWidget().dbpipe=DBPipe(QFileDialog.getOpenFileName(None,"Open DB File",".","DB files (*.db)")[0])
        print self.parentWidget().dbpipe.session.query(Site).all() 


    @Slot()
    def newFile(self):
        self.parentWidget().dbpipe=DBPipe(QFileDialog.getSaveFileName(None,"Open DB File",".","DB files (*.db)")[0])
            
        pass
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


class SiteItem(QStandardItem):

    def __init__(self,site):
        super(SiteItem,self).__init__(site.id)



SiteItemModel=QStandardItemModel()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main=MainWindow()
    d=DBPipe("./comments.db")
    ds=Site.query.all()
    si=[SiteItem(s) for s in ds]
    [SiteItemModel.appendRow(i) for i in si]
    view=QListView()
    view.setModel(SiteItemModel)
    view.show()
    main.show()
    sys.exit(app.exec_())

