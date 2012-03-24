from PySide.QtCore import *
from PySide.QtGui import *
from models import *

class Tree(QTreeWidget):

    def __init__(self,parent=None):
        super(Tree,self).__init__(parent)
        self.setColumnCount(5)
        self.setHeaderLabels(["ID","Author","Description","Content","Date","Title","Comments Count"])
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
        
        self.addTopLevelItems(items)
        
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
                post_item.setText(5,item.title)
                post_item.setText(6,str(item.comments_count))
                post_item.setSizeHint(0,QSize(5,5))
                post_item.setSizeHint(3,QSize(5,5))
                post_item.setSizeHint(2,QSize(5,5))
                items.append(post_item)
        site_item.addChildren(items)
        
    
    def loadAll(self):
        self.clear()
        self.addSite(Site.query.all())
        for tl in range(0,self.topLevelItemCount(),1):
            tli=self.topLevelItem(tl)
            self.addPost(Post.query.filter(Post.site_id==tli.data(0,0)).all(),tli)