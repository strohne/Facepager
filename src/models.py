#from requester import *
import sqlalchemy as sql
from sqlalchemy import Column, Integer, String,ForeignKey,Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref,sessionmaker,session,scoped_session

import json
from dateutil import parser
import datetime
import os
from PySide.QtGui import *
from PySide.QtCore import *

Base = declarative_base()

#at="109906609107292|_3rxWMZ_v1UoRroMVkbGKs_ammI"
#g=fb.GraphAPI("109906609107292|_3rxWMZ_v1UoRroMVkbGKs_ammI")


def getDictValue(data,multikey):
    keys=multikey.split('.')                
    value=data
    for key in keys:
        if type(value) is dict:
            value=value.get(key,"")
        elif type(value) is list:
            try:
                value=value[int(key)]
            except:
                return ""        
        else:
            return ""
    if type(value) is dict:
        return json.dumps(value) 
    else:        
        return value                    
    
class Database(object):
    
    def __init__(self,parent):
        self.parent = parent
        self.connected=False
        self.filename=""
        
    def connect(self,filename):
        try:   
            if self.connected:
                self.disconnect()
 
            self.engine = create_engine('sqlite:///%s'%filename, convert_unicode=True)
            self.session = scoped_session(sessionmaker(autocommit=False,autoflush=False,bind=self.engine))
            Base.query = self.session.query_property()
            Base.metadata.create_all(bind=self.engine)
            self.filename=filename
            self.connected=True
        except Exception as e:
            self.filename=""
            self.connected=False
            QMessageBox.critical(self.parent,"Facepager",str(e))
                
    def disconnect(self):
        if self.connected:
            self.session.close()
            
        self.filename=""    
        self.connected=False
        
    def createconnect(self,filename):    
        self.disconnect()
        if os.path.isfile(filename):
            os.remove(filename)
        self.connect(filename)     
                    
    def commit(self):
        if self.connected:
            try:
                self.session.commit()
            except Exception as e:
                QMessageBox.critical(self.parent,"Facepager",str(e))
        else:
            QMessageBox.information(self.parent,"Facepager","No database connection")

    def rollback(self):
        if self.connected:
            try:
                self.session.rollback()
            except Exception as e:
                QMessageBox.critical(self.parent,"Facepager",str(e))
        else:
            QMessageBox.information(self.parent,"Facepager","No database connection")            
            

            
class Node(Base):
        __tablename__='Nodes'

        objectid=Column(String)
        querystatus=Column(String)
        querytype=Column(String)
        querytime=Column(String)
        response_raw=Column("response",Text)                                        
        id=Column(Integer,primary_key=True,index=True)
        parent_id = Column(Integer, ForeignKey('Nodes.id'),index=True)
        children = relationship("Node",backref=backref('parent', remote_side=[id]))
        level=Column(Integer)                             
        childcount=Column(Integer)

        def __init__(self,objectid,parent_id=None):            
            self.objectid=objectid
            self.parent_id=parent_id
            self.level=0
            self.childcount=0
            self.querystatus='new'
            
        @property
        def response(self):
            if (self.response_raw == None): 
                return {}
            else:
                return  json.loads(self.response_raw)
    
        @response.setter
        def response(self, response_raw):
            self.response_raw = json.dumps(response_raw)               
            
        def getResponseValue(self,key,encoding=None):
            value=getDictValue(self.response,key)
            if encoding and isinstance(value, unicode):                
                return value.encode(encoding)
            else:
                return value
            
        @property
        def objectid_encoded(self):
            try:
                return str(self.objectid)
            except UnicodeEncodeError as e:
                return self.objectid.encode('utf-8')
                 
class Job(Base):
        __tablename__='Jobs'
        
        status=Column(String)        
        executed=Column(String)
        level=Column(Integer)                                            
        seeds=Column(Integer)
        query=Column(String)
        since=Column(String)
        until=Column(String)
        offset=Column(String)
        limit=Column(String)
        id=Column(Integer,primary_key=True)

        def __init__(self):
            pass            
                           
class TreeItem(object):
    def __init__(self, parent=None,id=None,data=None):
        self.id = id
        self.parentItem = parent        
        self.data = data
        self.childItems = []
        self.loaded=False                
        self._childcountallloaded=False
        self._childcountall=0

    def appendChild(self, item,persistent=False):
        item.parentItem=self
        self.childItems.append(item)
        if persistent:
            self._childcountall += 1

    def child(self, row):
        return self.childItems[row]
    
    def clear(self):
        self.childItems=[]
        self.loaded=False
        self._childcountallloaded=False
        
    def remove(self,persistent=False):
        self.parentItem.removeChild(self,persistent)            
        

    def removeChild(self,child,persistent=False):
        if child in self.childItems:            
            self.childItems.remove(child)
            if persistent:
                self._childcountall -= 1        
        
    def childCount(self):
        return len(self.childItems)
    
    def childCountAll(self):       
        if not self._childcountallloaded:                                     
            self._childcountall=Node.query.filter(Node.parent_id == self.id).count()
            self._childcountallloaded=True            
        return self._childcountall     
            
    def parent(self):
        return self.parentItem
    
    def parentid(self):
        return self.parentItem.id if self.parentItem else None     

    def level(self):
        if self.data == None:
            return 0
        else:
            return self.data['level']

    def row(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)
        return 0

    

class TreeModel(QAbstractItemModel):
    
    def __init__(self, mainWindow=None,database=None):
        super(TreeModel, self).__init__()
        self.mainWindow=mainWindow
        self.customcolumns=[]
        self.rootItem = TreeItem()
        self.database=database
        #self.requester=ApiRequester(mainWindow)

    def reset(self):        
        self.rootItem.clear()
        super(TreeModel, self).reset()        
                   
    def setCustomColumns(self,newcolumns=[]):
        self.customcolumns=newcolumns
        self.layoutChanged.emit()    
                            
    def delete(self,level,querytype):
        if (not self.database.connected):
            return False                                               

        #self.beginRemoveRows(index.parent(),index.row(),index.row())
        #item=index.internalPointer()                 
        self.beginResetModel()  
        Node.query.filter(Node.level == level,Node.querytype==querytype).delete()                            
        self.database.session.commit()                         
        #item.remove(True)
        
        self.reset()
        self.endResetModel()
        #self.reset()       
        #self.endRemoveRows()


    def deleteNode(self,index):
        if (not self.database.connected) or (not index.isValid()) or (index.column() <> 0):
            return False                                               

        self.beginRemoveRows(index.parent(),index.row(),index.row())
        item=index.internalPointer()
        
        
        #Node.query.filter(Node.id == item.parentid).update()
                           
        Node.query.filter(Node.id == item.id).delete()                            
        self.database.session.commit()                         
        item.remove(True)       
        self.endRemoveRows()

            
    def addNodes(self,objectids):
        try:       
            if not self.database.connected:
                return False
                
            #self.beginInsertRows(QModelIndex(),self.rootItem.childCount(),self.rootItem.childCount()+len(facebookids)-1)
            newnodes=[]   
            for objectid in objectids: 
                new=Node(objectid)
                newnodes.append(new)
                
                #self.database.session.flush()
                #itemdata=self.getItemData(new)     
                #self.rootItem.appendChild(TreeItem(self.rootItem,new.id,itemdata),True)

            self.database.session.add_all(newnodes)             
            self.database.session.commit()
            self.rootItem._childcountall+=len(objectids)
            self.layoutChanged.emit()
                                    
            #self.endInsertRows()
        except Exception as e:
            QMessageBox.critical(self.parent,"Facepager",str(e))                    

            
    def queryData(self,index):
        try:
            if not index.isValid():
                return False
                
            treenode=index.internalPointer()
            dbnode=Node.query.get(treenode.id)
                
            #get data
            try:
                options=self.mainWindow.RequestTabs.currentWidget().getOptions();
                response = self.mainWindow.RequestTabs.currentWidget().fetchData(treenode.data,options)
  
            except Exception as e:
                querystatus=str(e)
                self.mainWindow.logmessage(str(e))
                
                response={}
            else:
                querystatus="fetched"                
            
            
            #append nodes
            if options.get('append',True):
    
                #filter response
                if options['nodedata'] != None:
                    nodes=getDictValue(response,options['nodedata'])
                else:
                    nodes=response
                
                #single record
                if not (type(nodes) is list): nodes=[nodes]                                     
                
                #empty records                    
                if (len(nodes) == 0) and (options.get('appendempty',True)):                    
                    nodes=[{}]
                    querystatus="empty"                      
                                    
                newnodes=[]
                for n in nodes:                    
                    new=Node(getDictValue(n,options['objectid']),dbnode.id)
                    new.response=n
                    new.level=dbnode.level+1
                    new.querystatus=querystatus
                    new.querytime=str(datetime.datetime.now())
                    new.querytype=options['querytype']
                    newnodes.append(new)
    
                self.database.session.add_all(newnodes)    
                treenode._childcountall += len(newnodes)    
                dbnode.childcount += len(newnodes)    
                self.database.session.commit()                
                
            #update node    
            else:  
                dbnode.response = response
                dbnode.querystatus=querystatus                
                dbnode.querytime=str(datetime.datetime.now())
                dbnode.querytype=options['querytype']
                self.database.session.commit()
                treenode.data=self.getItemData(dbnode)

            self.layoutChanged.emit()
        except Exception as e:
            self.mainWindow.logmessage(str(e))
                            
                                
    def columnCount(self, parent):
        return 4+len(self.customcolumns)    

    def rowCount(self, parent):
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()
                                             

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            captions=['Object ID','Query Status','Query Time','Query Type']+self.customcolumns                
            return captions[section] if section < len(captions) else ""

        return None

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()
        
          
    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

            
    def data(self, index, role):
        if not index.isValid():
            return None

        if role != Qt.DisplayRole:
            return None

        item = index.internalPointer()
        
        if index.column()==0:
            return item.data['objectid']
        elif index.column()==1:
            return item.data['querystatus']      
        elif index.column()==2:
            return item.data['querytime']      
        elif index.column()==3:
            return item.data['querytype']      
        else:            
            return getDictValue(item.data['response'],self.customcolumns[index.column()-4])
            

    def hasChildren(self, index):
        if not self.database.connected:
            return False
                
        if not index.isValid():
            item = self.rootItem
        else:
            item = index.internalPointer()                                
        
        return item.childCountAll() > 0               
            
        
            

    def getItemData(self,item):
        itemdata={}
        itemdata['level']=item.level
        itemdata['objectid']=item.objectid        
        itemdata['querystatus']=item.querystatus
        itemdata['querytime']=item.querytime
        itemdata['querytype']=item.querytype
        itemdata['response']=item.response     
        return itemdata   
        
    def canFetchMore(self, index):                           
        if not self.database.connected:
            return False
        
        if not index.isValid():
            item = self.rootItem
        else:
            item = index.internalPointer()    
                            
        return item.childCountAll() > item.childCount()
        
    def fetchMore(self, index):
        if not index.isValid():
            parent = self.rootItem
        else:
            parent = index.internalPointer()                       
        
        if parent.childCountAll() == parent.childCount():
            return False
                
        row=parent.childCount()        
        items = Node.query.filter(Node.parent_id == parent.id).offset(row).all()

        
        self.beginInsertRows(index,row,row+len(items)-1)

        for item in items:
            itemdata=self.getItemData(item)
            new=TreeItem(parent,item.id,itemdata)
            new._childcountall=item.childcount
            new._childcountallloaded=True                                                               
            parent.appendChild(new)
            self.createIndex(row, 0, index)
            row += 1
                                        
        self.endInsertRows()
        parent.loaded=parent.childCountAll()==parent.childCount()


                    
    

