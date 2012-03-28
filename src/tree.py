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
        self.itemExpanded.connect(self.updateItem)

    
    @Slot()
    def updateItem(self,current):
        if current.type() is 1:
            self.loadPosts(site_item=current,all=True)
            
        elif current.type() is 2:
            self.loadComments(post_item=current, all=True)


    
    @Slot()
    def updateHeader(self,item):
        if item.type() is 1:
            self.setColumnCount(15)

            self.setHeaderLabels(['Site ID','Category', 'Description','Username', 'Website', 'Name','Products','Company_overview', 'Talking_about_count',\
                                         'Mission', 'Founded', 'Phone', 'Link', 'Likes', 'General_info', 'Checkins'])
        elif item.type() is 2:
            self.setColumnCount(13)
            self.setHeaderLabels(["Post_ID","Created","Author","Description","Title","Message","Type","Link","Source","Likes","Liker","Shares","Comments Count"])
        elif item.type() is 3:
            self.setColumnCount(7)
            self.setHeaderLabels(["Comment_ID","Created","Author","Message","Likes","Liker"])

       
    
    @Slot()
    def loadSites(self):
        self.clear()
        dbsites=Site.query.all()
        if dbsites:
            todo=[]
            for dbsite in dbsites:
                item_site=QTreeWidgetItem(type=1)
                item_site.setText(0,dbsite.id)
                item_site.setText(1,dbsite.category)
                item_site.setText(2,dbsite.description)
                item_site.setText(3,dbsite.username)
                item_site.setText(4,dbsite.website)
                item_site.setText(5,dbsite.name)
                item_site.setText(6,dbsite.products)
                item_site.setText(7,dbsite.company_overview)
                item_site.setText(8,str(dbsite.talking_about_count))
                item_site.setText(9,dbsite.mission)
                item_site.setText(10,dbsite.founded)
                item_site.setText(11,dbsite.phone)
                item_site.setText(12,dbsite.link)
                item_site.setText(13,str(dbsite.likes))
                item_site.setText(14,dbsite.general_info)
                item_site.setText(15,str(dbsite.checkins))
                
                for r in range(1,self.columnCount(),1):
                        item_site.setSizeHint(r,QSize(5,9))
                        item_site.setBackground(r,QColor(139,136,120))
                self.loadPosts(item_site,all=False)
                todo.append(item_site)
            self.addTopLevelItems(todo)
        
    @Slot()    
    def loadPosts(self,site_item,all=False):
        if all==True:
            dbposts=[i for i in Post.query.filter(Post.site_id==site_item.data(0,0)).all()]
            if dbposts:
                todo=[]
                site_item.takeChildren()
                for  dbpost in dbposts:
                    item_post=QTreeWidgetItem(type=2)
                    item_post.setText(0,dbpost.id)
                    item_post.setText(1,dbpost.created_time[:10])
                    item_post.setText(2,dbpost.author)
                    item_post.setText(3,dbpost.description)
                    item_post.setText(4,dbpost.title)
                    item_post.setText(5,dbpost.message)
                    item_post.setText(6,dbpost.type)
                    item_post.setText(7,dbpost.link)
                    item_post.setText(8,dbpost.source)
                    item_post.setText(9,str(dbpost.likes))
                    item_post.setText(10,str(dbpost.liker))
                    item_post.setText(11,str(dbpost.shares_count))
                    item_post.setText(12,str(dbpost.comments_count))
                    for r in range(1,self.columnCount(),1):
                            item_post.setSizeHint(r,QSize(6,9)) 
                            item_post.setBackground(r,QColor(205,200,177))
                    self.loadComments(item_post,all=False)
                    todo.append(item_post)
            site_item.addChildren(todo)
        elif all==False:
            singlepost=Post.query.filter(Post.site_id==site_item.data(0,0)).first()
            if singlepost is not None:
                site_item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        
                        
               


    
    @Slot()
    def loadComments(self,post_item,all=False):
        if all is True:
            dbcomments=Comment.query.filter(Comment.post_id==post_item.data(0,0)).all()
            if dbcomments:
                todo=[]
                post_item.takeChildren()
                for dbcom in dbcomments:
                        item_comment=QTreeWidgetItem(type=3)
                        item_comment.setText(0,dbcom.id)
                        item_comment.setText(1,dbcom.created_time[:10])
                        item_comment.setText(2,dbcom.author)
                        item_comment.setText(3,dbcom.message)
                        item_comment.setText(4,str(dbcom.likes))
                        item_comment.setText(5,str(dbcom.liker))
                        for r in range(1,self.columnCount(),1):
                             item_comment.setBackground(r,QColor(238,232,205))
                             item_comment.setSizeHint(r,QSize(6,9))
                        todo.append(item_comment)
                post_item.addChildren(todo)
        
        elif all is False:
            singlecom=Comment.query.filter(Comment.post_id==post_item.data(0,0)).first()
            if singlecom is not None:
                post_item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
    
