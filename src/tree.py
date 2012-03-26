from PySide.QtCore import *
from PySide.QtGui import *
from models import *

class Tree(QTreeWidget):

    def __init__(self,parent=None):
        super(Tree,self).__init__(parent)
        self.setColumnCount(15)
        self.setHeaderLabels(['Site ID','Category', 'Description','Username', 'Website', 'Name','Products','Company_overview', 'Talking_about_count',\
                                         'Mission', 'Founded', 'Phone', 'Link', 'Likes', 'General_info', 'Checkins'])        
        self.setSortingEnabled(True)
        self.itemClicked.connect(self.updateHeader)
        self.itemActivated.connect(self.updateHeader)

    @Slot()
    def updateHeader(self,item):
        if item.type() is 1:
            self.setColumnCount(15)
            self.setHeaderLabels(['Site ID','Category', 'Description','Username', 'Website', 'Name','Products','Company_overview', 'Talking_about_count',\
                                         'Mission', 'Founded', 'Phone', 'Link', 'Likes', 'General_info', 'Checkins'])
        elif item.type() is 2:
            self.setColumnCount(13)
            self.setHeaderLabels(["Post_ID","Created","Author","Description","Title","Message","Type","Link","Source","Likes","Liker","Shares","Comments Count"])
    
    
    def addSite(self,site):
        if type(site)!=list:
            site=[site,]
        items=[]
        for item in site:
            site_item=QTreeWidgetItem(parent=self,type=1)
            site_item.setText(0,item.id)
            site_item.setText(1,item.category)
            site_item.setText(2,item.description)
            site_item.setText(3,item.username)
            site_item.setText(4,item.website)
            site_item.setText(5,item.name)
            site_item.setText(6,item.products)
            site_item.setText(7,item.company_overview)
            site_item.setText(8,str(item.talking_about_count))
            site_item.setText(9,item.mission)
            site_item.setText(10,item.founded)
            site_item.setText(11,item.phone)
            site_item.setText(12,item.link)
            site_item.setText(13,str(item.likes))
            site_item.setText(14,item.general_info)
            site_item.setText(15,str(item.checkins))
            items.append(site_item)
            for r in range(1,self.columnCount(),1):
                    site_item.setSizeHint(r,QSize(5,9))
        self.addTopLevelItems(items)
        
    def addPost(self,post,site_item):
        if type(post)!=list:
            post=[site_item,]
        items=[]
        
        for item in post:
           if item.site_id==int(site_item.data(0,0)): 
                post_item=QTreeWidgetItem(parent=site_item,type=2)
                post_item.setText(0,item.id)
                post_item.setText(1,item.created_time[:10])
                post_item.setText(2,item.author)
                post_item.setText(3,item.description)
                post_item.setText(4,item.title)
                post_item.setText(5,item.message)
                post_item.setText(6,item.type)
                post_item.setText(7,item.link)
                post_item.setText(8,item.source)
                post_item.setText(9,str(item.likes))
                post_item.setText(10,str(item.liker))
                post_item.setText(11,str(item.shares_count))
                post_item.setText(12,str(item.comments_count))
                post_item.setSizeHint(0,QSize(5,5))
                for r in range(1,self.columnCount(),1):
                    post_item.setSizeHint(r,QSize(6,15))
                items.append(post_item)
        site_item.addChildren(items)
        
    
    def loadAll(self):
        self.clear()
        self.addSite(Site.query.all())
        for tl in range(0,self.topLevelItemCount(),1):
            tli=self.topLevelItem(tl)
            self.addPost(Post.query.filter(Post.site_id==tli.data(0,0)).all(),tli)
            
    