import urllib,urllib2
import datetime

# Find a JSON parser
try:
    import simplejson as json
except ImportError:
    try:
        from django.utils import simplejson as json
    except ImportError:
        import json
_parse_json = json.loads



#Notcie: RequesterError und Requester enthalten Code aus facebook-sdk, das unter Apache 2.0 licence steht
class RequesterError(Exception):
    def __init__(self, result):
        #Exception.__init__(self, message)
        #self.type = type
        self.result = result
        try:
            self.type = result["error_code"]
        except:
            self.type = ""

        # OAuth 2.0 Draft 10
        try:
            self.message = result["error_description"]
        except:
            # OAuth 2.0 Draft 00
            try:
                self.message = result["error"]["message"]
            except:
                # REST server style
                try:
                    self.message = result["error_msg"]
                except:
                    self.message = result

        Exception.__init__(self, self.message)
        
class ApiRequester(object):
    def __init__(self,mainWindow):
        self.timeout=None
        self.mainWindow=mainWindow
            
    def idtostr(self,id):
        try:
            return str(id)
        except UnicodeEncodeError as e:
            return id.encode('utf-8')     
        
    def request_generic(self,nodedata,options):
                 
        if(options['urlfield']=='<Object ID>'): 
            queryterm=self.idtostr(nodedata['objectid'])
        elif((options['urlfield']=='<None>') | (options['urlfield']=='')):
            queryterm=''
        else:    
            queryterm=nodedata[options['urlfield']]
                        
                 
        urlpath = options["prefix"]+queryterm+options["suffix"]        
        
        self.mainWindow.loglist.append(str(datetime.datetime.now())+" Fetching data for "+self.idtostr(nodedata['objectid'])+" from "+urlpath)    
        return self.request(urlpath)
    
                   
    def request_twitter(self,nodedata,options):
                 
        urlpath = "https://api.twitter.com/1/"+options["querytype"]+".json"        
        urlparams= {options["objectidparam"]:self.idtostr(nodedata['objectid'])}
        
        self.mainWindow.loglist.append(str(datetime.datetime.now())+" Fetching data for "+nodedata['objectid']+" from "+urlpath+" with params "+json.dumps(urlparams))    
        return self.request(urlpath,urlparams)
    
       
        
                
    def request_facebook(self,nodedata,options):
        if (options['accesstoken'] == ""): raise RequesterError("Access token is missing")

        if nodedata['objectid']==None:
            raise RequesterError("Empty object id")
            
        #build url        
        if options['relation']=='<self>':
            urlpath=self.idtostr(nodedata['objectid'])
            urlparams={'metadata':'1'}

        elif options['relation']=='<search>':
            urlpath='search'
            urlparams={'q':self.idtostr(nodedata['objectid']),'type':'page'}
        
        else:
            urlpath=self.idtostr(nodedata['objectid'])+'/'+options['relation']            
            urlparams= { key: options[key] for key in ['limit','offset','since','until'] }                   
                
        urlparams["access_token"] =   options['accesstoken']         
        urlpath = "https://graph.facebook.com/" + urlpath
        
        self.mainWindow.loglist.append(str(datetime.datetime.now())+" Fetching data for "+nodedata['objectid']+" from "+urlpath+" with params "+json.dumps(urlparams))   
        return self.request(urlpath,urlparams)        


    def request(self, path, args=None):
        
        path=path + "?" +urllib.urlencode(args) if args else path
        post_data = None
        try:
            file = urllib2.urlopen(path, post_data, timeout=self.timeout)
        except urllib2.HTTPError, e:
            response = _parse_json(e.read())
            raise RequesterError(response)
        except TypeError:
            # Timeout support for Python <2.6
            if self.timeout:
                socket.setdefaulttimeout(self.timeout)
            file = urllib2.urlopen(path, post_data)
        try:
            fileInfo = file.info()
            if fileInfo.maintype == 'text':
                content=file.read()
                
                #f = open('D:/temp/log.txt', 'w')
                #f.write(content)
                #f.close()
                 
                response = _parse_json(content)
            elif fileInfo.maintype == 'image':
                mimetype = fileInfo['content-type']
                response = {
                    "data": file.read(),
                    "mime-type": mimetype,
                    "url": file.url,
                }
            elif fileInfo.maintype == 'application':
                response = {"data": _parse_json(file.read())}                
            else:
                raise RequesterError('Maintype was not text or image')
        finally:
            file.close()
        if response and isinstance(response, dict) and response.get("error"):
            raise RequesterError(response["error"]["type"],
                                response["error"]["message"])
        return response    
    