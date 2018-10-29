import json
import os,sys,platform

import lxml
import lxml.html

import StringIO

def getResourceFolder():
    if getattr(sys, 'frozen', False) and (platform.system() != 'Darwin'):
        folder = os.path.dirname(sys.executable)
    elif getattr(sys, 'frozen', False) and (platform.system() == 'Darwin'):
        folder = sys._MEIPASS
    else:
        folder = os.getcwd()

    return folder

def hasDictValue(data,multikey):
    try:
        keys=multikey.split('.',1)

        if type(data) is dict and keys[0] != '':
            if len(keys) > 1:
                value=data.get(keys[0],"")
                value = hasDictValue(value,keys[1])
            else:
                value = keys[0] in data
        elif type(data) is list and keys[0] == '*':
            if len(keys) > 1 and len(data) > 0:
                value = data[0]
                value = hasDictValue(value,keys[1])
            else:
                value = len(data) > 0
        elif type(data) is list and keys[0].isnumeric():
            no = int(keys[0])
            if len(keys) > 1 and len(data) > no:
                value = data[no]
                value = hasDictValue(value,keys[1])
            else:
                value = len(data) > no

        else:
            value = False

        return value
    except Exception as e:
        return False

def getDictValue(data,multikey,dump=True):
    try:
        keys=multikey.split('.',1)

        if type(data) is dict and keys[0] != '':
            #value=data.get(keys[0],"")

            try:
                value=data[keys[0]]
                if len(keys) > 1:
                    value = getDictValue(value,keys[1],dump)
            except:
                if keys[0] == '*' and len(keys) > 1:
                    listkey = keys[1]
                elif keys[0] == '*':
                    listkey = ''
                else:
                    listkey = None

                if listkey is not None:
                    valuelist=[]
                    for elem in data:
                        valuelist.append(getDictValue(data[elem],listkey,dump))
                    value = ";".join(valuelist)
                else:
                    value = ''

        elif type(data) is list and keys[0] != '':
            try:
                value=data[int(keys[0])]
                if len(keys) > 1:
                    value = getDictValue(value,keys[1],dump)
            except:
                if keys[0] == '*' and len(keys) > 1:
                    listkey = keys[1]
                elif keys[0] == '*':
                    listkey = ''
                else:
                    listkey = keys[0]

                valuelist=[]
                for elem in data:
                    valuelist.append(getDictValue(elem,listkey,dump))
                value = ";".join(valuelist)

        else:
            value = data

        if dump and (type(value) is dict or type(value) is list):
            return json.dumps(value)
        elif dump and (isinstance(value, (int, long))):
            return str(value)
        else:
            return value
    except Exception as e:
        return ""

def filterDictValue(data,multikey,dump=True):
    try:
        keys=multikey.split('.',1)

        if type(data) is dict and keys[0] != '':
            value = { key: data[key] for key in data.keys() if key != keys[0]}
            if len(keys) > 1:
                value[keys[0]] = filterDictValue(data[keys[0]],keys[1],False)
            if not len(value):
                value = None

        elif type(data) is list and keys[0] != '':
            try:
                value=data
                if len(keys) > 1:
                    value[int(keys[0])] = getDictValue(value[int(keys[0])],keys[1],False)
                else:
                    value[int(keys[0])] = ''
            except:
                if keys[0] == '*' and len(keys) > 1:
                    listkey = keys[1]
                elif keys[0] == '*':
                    listkey = ''
                else:
                    listkey = keys[0]

                valuelist=[]
                for elem in data:
                    valuelist.append(filterDictValue(elem,listkey,False))
                value = valuelist

        else:
            value = ''


        if dump and (type(value) is dict or type(value) is list):
            return json.dumps(value)
        else:
            return value

    except Exception as e:
        return ""

def recursiveIterKeys(value,prefix=None):
    for key in value.iterkeys():
        if type(value[key]) is dict:
            for subkey in recursiveIterKeys(value[key],key):
                fullkey = subkey if prefix is None else ".".join([prefix,subkey])
                yield fullkey
        else:
            fullkey = key if prefix is None else ".".join([prefix,key])
            yield fullkey

def htmlToJson(data,csskey=None,type='lxml'):
    #type='html5'
    soup = lxml.html.fromstring(data)

    def parseSoup(element,context = True):
        out = {}
        if context:
            #out['name'] = element.tag
            if element.text is not None:
                out['text'] = unicode(element.text).strip("\n\t ")
                
        attributes= {}
        if context:                
            for name, value in sorted(element.items()):
                attributes['@'+name] = value
        out.update(attributes)
                        
        children = []
        for child in element:
            if isinstance(child.tag, basestring):
                id = str(child.get('id',''))
                key = child.tag+'#'+id if id != '' else child.tag
                children.append({key:parseSoup(child)})
            else:
                value = unicode(child.text).strip("\n\t ")
                if value != '':
                    children.append({'text':value})

        if len(children) > 0:
            out['items'] = children
        
        #simplify:
        if len(children) == 0 and len(attributes) ==0:
            out = out.get('text',None)
        elif len(children) > 0 and len(attributes) ==0 and out.get('text',None) is None:
            del out['items']
            out = children
            
        return out

    output = []
    if csskey is not None:
        for part in soup.cssselect(csskey):
            output.extend(parseSoup(part,True))
    else:
        output = {soup.tag : parseSoup(soup,True)}

    return output

# See http://foobarnbaz.com/2012/12/31/file-upload-progressbar-in-pyqt/
# See http://code.activestate.com/recipes/578669-wrap-a-string-in-a-file-like-object-that-calls-a-u/
class CancelledError(Exception):
    """Error denoting user interruption.
    """
    def __init__(self, msg):
        self.msg = msg
        Exception.__init__(self, msg)

    def __str__(self):
        return self.msg

    __repr__ = __str__


class BufferReader():
    """StringIO with a callback.
    """
    def __init__(self, data='',callback=None):
        self._callback = callback
        self._progress = 0
        self._len = int(len(data))
        self._io = StringIO.StringIO(data)

    def __len__(self):
        return self._len
    
    def read(self, *args):
        chunk = self._io.read(*args)
        self._progress += int(len(chunk))
        if self._callback:
            try:
                self._callback(self._progress,self._len)
            except:
                raise CancelledError('The upload was cancelled.')

        return chunk