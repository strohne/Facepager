import facebook as fb
import sqlalchemy as sql
from sqlalchemy import Column, Integer, String,ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref,sessionmaker
from urllib import quote as quote
from calendar import Calendar as Cal
import pickle as pcl


#sql DB
engine = create_engine('sqlite:///./comments.db', echo=True)
Base = declarative_base(bind=engine)

session=sessionmaker()
session=session()

g=fb.GraphAPI('109906609107292|_3rxWMZ_v1UoRroMVkbGKs_ammI')


class Site(Base):

        __tablename__='Sites'
        category=Column(String)
        name=Column(String)
        founded=Column(String)
        company_overview=Column(String)
        username=Column(String)
        talking_about_count=Column(Integer)
        mission=Column(String)
        website=Column(String)
        phone=Column(String)
        link=Column(String)
        likes=Column(Integer)
        products=Column(String)
        general_info=Column(String)
        checkins=Column(Integer)
        id=Column(String,primary_key=True)
        description=Column(String)
        posts=relationship('Post')


	def __init__(self,site):
		self.__dict__.update(g.get_object(site))
                self.posts=[]

        def getPosts(self,n,since,until):
		plist=g.get_object(str(self.id+'/feed&limit='+str(n)+'&since='+since+'&until='+until))['data']
                print str(self.id+'/feed&limit='+str(n)+'&since='+since+'&until='+until)
		l=[self.posts.append(Post(i,site=self)) for i in plist if i.get("id") not in [x.id for x in self.posts]]

class Post(Base):

        __tablename__='Posts'
        id=Column(String,primary_key=True)
        site_id=Column(Integer,ForeignKey('Sites.id'))
        created_time=Column(String)
        author=Column(String)
        author_id=Column(String)
        title=Column(String)
        description=Column(String)
        message=Column(String)
        type=Column(String)
        link=Column(String)
        source=Column(String)
        comments=relationship('Comment')
        comments_count=Column(Integer)
        likes=Column(Integer)
        liker=Column(Integer)
        shares_count=Column(String)

	def __init__(self,post,site):
            self.description=post.get('description','NA')
            self.message=post.get('message','NA')
            self.id=post.get('id','NA')
            self.created_time=post.get('created_time','NA')
            self.link=post.get('link','NA')
            self.likes=post.get('likes',{'count':'0'}).get('count')
            self.comments_count=post.get('comments',{'count':0}).get('count')
            self.site_id=site.id
            self.comments=self.getComments()
            self.title=post.get('name','NA')
            self.type=post.get('type')
            self.author=post.get('from').get('name')
            self.author_id=post.get('from').get('id')
            self.source=post.get('source','NA')
            self.type=post.get('type','NA')
            self.shares_count=post.get('shares',{'count':0}).get('count')
            self.liker=999
                   
        def getComments(self):
            if self.comments_count!=0:
                try:
                    comments=g.get_object(str(self.id+'/comments?limit=500')) 
                    return [Comment(data=i,post=self) for i in comments['data']]
                except KeyError:
                    print "Comment(s) missing for %s"%self.id
                    return []
            else: 
                return []

        def getLikers(self):
            if self.likes!=0:
                    try:    
                        liker=g.get_object(str('/fql&q=select user_id from like where post_id="%s" and user_id=%s limit 500'%(self.id,self.site_id)))
                        if not liker.get("data"):
                            return 0
                        else:
                            return 1
                    except:
                        return 999 
            else:
                return 0

           
class Comment(Base):
    
        __tablename__='Comments'
        id=Column(String,primary_key=True)
        site_id=Column(Integer,ForeignKey('Sites.id'))
        post_id=Column(Integer,ForeignKey('Posts.id'))
        created_time=Column(String)
        author=Column(String)
        author_id=Column(String)
        message=Column(String)
        likes=Column(Integer)
        liker=Column(Integer)
        
        def __init__(self,data,post):
            self.__dict__.update(data)
            self.post_id=post.__dict__.get('id','NA')
            self.site_id=post.__dict__.get('site_id','NA')
            self.author=self.__dict__.get('from').get('name','NA')
            self.author_id=self.__dict__.get('from').get('id','NA')
            self.likes=self.__dict__.get('likes',0)
            self.liker=999

        def getLikers(self):
            if self.likes!=0:
                    try:
                        liker=g.get_object(str('/fql&q=select user_id from like where post_id="%s" and user_id=%s limit 500'%(self.id,self.site_id)))
                        if not liker.get("data"):
                            return 0
                        else:
                            return 1
                    except:
                        return 999
            else:
                return 0


Base.metadata.create_all()
file=open("dates2")
dates=pcl.loads(file.read())
