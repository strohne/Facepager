import json
import os,sys,platform,time
from base64 import b64encode
from datetime import datetime
import re
import lxml
import lxml.html
import lxml.etree
import html
import urllib.parse
import tldextract
from collections import OrderedDict
from collections import Mapping
from xmljson import BadgerFish
import io
import pyjsparser

def getResourceFolder():
    if getattr(sys, 'frozen', False) and (platform.system() != 'Darwin'):
        folder = os.path.dirname(sys.executable)
    elif getattr(sys, 'frozen', False) and (platform.system() == 'Darwin'):
        folder = sys._MEIPASS
    else:
        folder = os.getcwd()

    return folder

def flattenList(items):
    value = []
    for item in items:
        if type(item) is list:
            value += item
        else:
            value.append(item)
    return value

def hasDictValue(data,multikey, piped=False):
    try:
        #multikey = multikey.split('|').pop(0) if piped else multikey
        name, multikey, pipeline = parseKey(multikey) if piped else (None,multikey,None)

        #keys=multikey.split('.',1)
        keys = tokenize_with_escape(multikey, escape='\\', separator='.')

        if isinstance(data, Mapping) and keys[0] != '':

            if len(keys) > 1:
                value = data.get(keys[0],"")
                value = hasDictValue(value,keys[1])
            else:
                value = keys[0] in data

            if (not value) and (keys[0] == '*'):
                if len(keys) == 1:
                    value = bool(data)

                else:
                    listkey = keys[1]
                    for elem in data:
                        value = hasDictValue(data[elem], listkey)
                        if value:
                            break

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

def extractNames(customcolumns = []):
    """Extract name contained in keys
    """
    names = []
    for column in customcolumns:
        name = tokenize_with_escape(str(column)).pop(0).split('=', 1)
        name = column if len(name) < 2 else name[0]
        names.append(name)
    return names

def parseKey(key):
    pipeline = tokenize_with_escape(key)
    key = pipeline.pop(0).split('=', 1)
    name = key.pop(0) if len(key) > 1 else None
    key = key[0]

    return (name, key, pipeline)


def hasValue(data,key):
    name, value = extractValue(data, key, False)
    if (value is None):
        return False
    elif (value == False):
        return False
    elif (type(value) is list) and (len(value) == 0):
        return False
    else:
        return True

def dict_generator(indict, pre=None):
    pre = pre[:] if pre else []
    if isinstance(indict, dict):
        for key, value in indict.items():
            if isinstance(value, dict):
                for d in dict_generator(value,  pre + [key]):
                    yield d
            elif isinstance(value, list) or isinstance(value, tuple):
                for k,v in enumerate(value):
                    for d in dict_generator(v, pre + [key] + [k]):
                        yield d
            else:
                yield pre + [key, value]
    else:
        yield indict

def jsGetValue(value):
    proptype = value.get('type')
    if proptype == 'Literal':
        return value.get('value')
    elif proptype == 'Identifier':
        return value.get('name')
    elif proptype == 'ObjectExpression':
        propvalues = value.get('properties', {})
        outvalue = {}
        for v in propvalues:
            v = jsGetValue(v)
            if isinstance(v, dict):
                outvalue.update(v)
        return outvalue
    elif proptype == 'ArrayExpression':
        propvalues = value.get('elements', {})
        return [jsGetValue(v) for v in propvalues]
    elif proptype == 'Property':
        propname = jsGetValue(value.get('key',{}))
        propvalue = jsGetValue(value.get('value', {}))
        return {propname: propvalue}
    else:
        return None

def jsWalkValues(indict, pre=None):
    pre = pre[:] if pre else []
    if isinstance(indict, dict):
        proptype = indict.get('type')
        if proptype == 'ObjectExpression':
            yield jsGetValue(indict)

        for key, value in indict.items():
            if isinstance(value, dict):
                for d in jsWalkValues(value,  pre + [key]):
                    yield d
            elif isinstance(value, list) or isinstance(value, tuple):
                for k, v in enumerate(value):
                    for d in jsWalkValues(v, pre + [key] + [k]):
                        yield d

def extractValue(data, key, dump=True, folder="", default=''):
    """Extract value from dict and pipe through modifiers
    :param data:
    :param multikey:
    :param dump:
    :return:
    """
    #global jsparser
    try:
        # Parse key
        name, key, pipeline = parseKey(key)

        # Input: dict. Output: string, number, list or dict
        value = getDictValue(data, key, dump, default)

        for idx, modifier in enumerate(pipeline):
            value = value if type(value) is list else [value]

            if modifier.startswith('js:'):
                # Input: list of strings.
                # Output if dump==True: list of strings
                # Output if dump==False: list of dict, list, string or number
                selector = modifier[3:]

                items = []
                for x in value:
                    try:
                        #x = x.replace('\\\\"', '\\"')

                        tree = pyjsparser.parse(x)
                        items += jsWalkValues(tree)
                    except Exception as e:
                        items.append({'error':str(e)})

                items = [getDictValue(x, selector, dump=dump, default=[]) for x in items]

                # Flatten list if not dumped
                if not dump:
                    value = flattenList(items)
                else:
                    value = items

            elif modifier.startswith('json:'):
                # Input: list of strings.
                # Output if dump==True: list of strings
                # Output if dump==False: list of dict, list, string or number
                selector = modifier[5:]
                items = [getDictValue(json.loads(x), selector, dump=dump) for x in value]

                # Flatten list if not dumped
                if not dump:
                    value = flattenList(items)
                else:
                    value = items

            elif modifier.startswith('not:'):
                selector = modifier[4:]
                check = [x == selector for x in value]
                value = not any(check)

            elif modifier.startswith('is:'):
                selector = modifier[3:]
                check = [x == selector for x in value]
                value = any(check)

            elif modifier.startswith('re:'):
                # Input: list of strings.
                # Output: list of strings
                selector = modifier[3:]
                items = [re.findall(selector,x) for x in value]

                # Flatten (first group in match if re.findall returns multiple groups)
                value = []
                for matches in items:
                    for match in matches:
                        if (type(match) is tuple):
                            value.append(match[0])
                        else:
                            value.append(match)

            # Example: encode:utf-8
            elif modifier.startswith('encode:'):
                # Input: list of strings.
                # Output: list of strings
                encoding = modifier[7:]
                value = [x.encode(encoding) for x in value]

            elif modifier.startswith('css:'):
                # Input: list of strings.
                # Output: list of strings
                selector = modifier[4:]
                value = [extractHtml(x, selector, type='css') for x in value]
                value = [y for x in value for y in x]
            elif modifier.startswith('xpath:'):
                # Input: list of strings.
                # Output: list of strings
                selector = modifier[6:]
                value = [extractHtml(x, selector, type='xpath') for x in value]
                value = [y for x in value for y in x]

            # Load file contents (using modifiers after a pipe symbol)
            elif modifier == 'file':
                value = value[0]
                with open(os.path.join(folder, value), 'rb') as file:
                    value = file.read()

            elif modifier == 'base64':
                value = value[0]
                value = b64encode(value.encode('utf-8')).decode('utf-8')

            elif modifier == 'length':
                value = len(value)
            elif modifier == "timestamp":
                value = [datetime.utcfromtimestamp(float(x)).isoformat() for x in value]
            elif modifier == "shortdate":
                value = [str(datetime.strptime(x, '%a %b %d %H:%M:%S %z %Y')) for x in value]

        # If modified in pipeline (otherwise already handled by getDictValue)...
        if dump and (type(value) is dict):
            value = json.dumps(value)
        if dump and (type(value) is list):
            value = ";".join(value)
        elif dump and (isinstance(value, int)):
            value = str(value)

        return (name, value)

    except Exception as e:
        return (None, default)

def findDictValues(data, multikey, dump=True, default=''):
    """
    Recursively searches for the multikey
    :param data:
    :param multikey:
    :param dump:
    :param default:
    :return:
    """
    if hasDictValue(data, multikey):
        return [getDictValue(data, multikey, dump, default)]
    elif isinstance(data, Mapping) and multikey != '':
        values = []
        for key, value in data,items():
            values.extend(findDictValues(value, multikey, dump, default))
        return values
    elif isinstance(data, list) and multikey != '':
        values = []
        for value in data:
            values.extend(findDictValues(value, multikey, dump, default))
        return values
    else:
        return [default]

def toDictListTuple(data, key=''):
    """Convert data to a list of tuples shaped (key, dict)."""

    if not (type(data) is list):
        subkey=0
        data = [data]
    else:
        subkey = key.split('|').pop(0).rsplit('.', 1)[0]
        key += '.*'

    data = [(key, n if isinstance(n, Mapping) else {subkey: n}) for n in data]

    return data

def sliceData(data, headers=None, options={}):
    """Filter response data and extract nodes"""
    if options['nodedata'] is None:
        nodes = toDictListTuple(data)
        offcut = None
    else:
        keys = options['nodedata'].split(',')
        nodes = []
        offcut = data

        for key in keys:
            if hasDictValue(data, key, piped=True):
                name, newnodes = extractValue(data, key, False)
                newnodes = toDictListTuple(newnodes,key)

                nodes.extend(newnodes)
                offcut = filterDictValue(offcut, key, False, piped=True) \
                    if options.get('offcut', True) else None

    #empty records
    if (len(nodes) == 0) and options.get('empty', True):
        empty = {}
    else:
        empty = None

    # offcut
    if not options.get('offcut', True):
        offcut = None
    elif options.get('fulloffcut', False):
        offcut = data


    # headers
    if not options.get('saveheaders', False):
        headers = None

    data={
        'nodes': nodes,
        'offcut': offcut,
        'empty': empty,
        'headers': headers
    }

    return data

def getDictValue(data, multikey, dump=True, default=''):
    """Extract value from dict
    :param data:
    :param multikey:
    :param dump:
    :param default:
    :return:
    """
    try:
        #keys=multikey.split('.',1)
        keys = tokenize_with_escape(multikey,escape ='\\',separator='.',n=1)

        if isinstance(data, Mapping) and keys[0] != '':
            try:
                value=data[keys[0]]
                if len(keys) > 1:
                    value = getDictValue(value,keys[1],dump, default)
            except:
                if keys[0] == '*':
                    listkey = keys[1] if len(keys) > 1 else ''
                    value=[]
                    for elem in data:
                        item = getDictValue(data[elem],listkey,dump, default)
                        if isinstance(item,list):
                            value.extend(item)
                        else:
                            value.append(item)

                elif keys[0] == '**':
                    listkey = keys[1] if len(keys) > 1 else ''
                    value = findDictValues(data, listkey, dump, default)
                else:
                    value = default

        elif type(data) is list and keys[0] != '':
            try:
                value=data[int(keys[0])]
                if len(keys) > 1:
                    value = getDictValue(value,keys[1],dump, default)
            except:
                if keys[0] == '**':
                    listkey = keys[1] if len(keys) > 1 else ''
                    value = findDictValues(data, listkey, dump, default)

                else:
                    if keys[0] == '*':
                        listkey = keys[1] if len(keys) > 1 else ''
                    else:
                        listkey = keys[0]

                    value=[]
                    for elem in data:
                        item = getDictValue(elem, listkey, dump, default)
                        if isinstance(item, list):
                            value.extend(item)
                        else:
                            value.append(item)


        elif keys[0] == '':
            value = data
        else:
            value = default

        if dump and (type(value) is dict):
            value = json.dumps(value)
        elif dump and (type(value) is list):
            value = ";".join(value)
        elif dump and (isinstance(value, int)):
            value = str(value)
        elif dump and (isinstance(value, float)):
            value = str(value)

        return value

    except Exception as e:
        return default

def getDictValueOrNone(data, key, dump = True):
    if (key is None) or (key == ''):
        return None
    elif not (isinstance(data, dict)):
        return None
    elif not hasDictValue(data, key, piped=True):
        return None
    else:
        name, value = extractValue(data, key, dump=dump, default=None)
        value = None if (value == "") else value
        return value

def filterDictValue(data, multikey, dump=True, piped=False):
    try:
        multikey = multikey.split('|').pop(0) if piped else multikey
        keys=multikey.split('.',1)

        if isinstance(data, Mapping) and keys[0] != '':
            value = { key: data[key] for key in list(data.keys()) if key != keys[0]}
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
    for key in value.keys():
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
                out['text'] = str(element.text).strip("\n\t ")
                
        attributes= {}
        if context:                
            for name, value in sorted(element.items()):
                attributes['@'+name] = value
        out.update(attributes)
                        
        children = []
        for child in element:
            if isinstance(child.tag, str):
                id = str(child.get('id',''))
                key = child.tag+'#'+id if id != '' else child.tag
                children.append({key:parseSoup(child)})
            else:
                value = str(child.text).strip("\n\t ")
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
            output.append(parseSoup(part,True))
    else:
        output = {soup.tag : parseSoup(soup,True)}

    return output


def elementToJson(element, context=True):
    out = {}
    if context:
        out['tag'] = element.tag
        out['text'] = element.text_content().strip("\r\n\t ")
        #if element.text is not None:
        #    out['text'] = str(element.text).strip("\n\t ")

    attributes = {}
    if context:
        for name, value in sorted(element.items()):
            attributes['@' + name] = value
    out.update(attributes)

    # children = []
    # for child in element:
    #     if isinstance(child.tag, str):
    #         id = str(child.get('id', ''))
    #         key = child.tag + '#' + id if id != '' else child.tag
    #         children.append({key: parseSoup(child)})
    #     else:
    #         value = str(child.text).strip("\n\t ")
    #         if value != '':
    #             children.append({'text': value})
    #
    # if len(children) > 0:
    #     out['items'] = children

    # simplify:
    # if len(children) == 0 and len(attributes) == 0:
    #     out = out.get('text', None)
    # elif len(children) > 0 and len(attributes) == 0 and out.get('text', None) is None:
    #     del out['items']
    #     out = children

    return out



def extractLinks(data,baseurl,parseurl=True):
    links = []
    soup = lxml.html.fromstring(data)

    base = soup.find('base')
    base = base.get('href') if base is not None else None
    baseurl = urllib.parse.urljoin(baseurl,base)

    for part in soup.cssselect('a'):
        link = elementToJson(part, True)
        if link.get('@href',None) is not None:
            link['url'] = urllib.parse.urljoin(baseurl, link.get('@href',None))
            if parseurl:
                parts = extractURLparts(link['url'],usecache=True)
                link.update(parts)
        links.append(link)

    return links, base

urlcache = {}
def extractURLparts(url_absolut,prefix="url_",usecache=False):
    cachekey = prefix + url_absolut
    if not usecache or (not cachekey in urlcache):
        item = {}
        # Domain etc. aus der absoluten URL rausziehen und im dict speichern
        try:
            parsed_uri = urllib.parse.urlparse(url_absolut)

            item[prefix + 'domain'] = parsed_uri.netloc
            item[prefix + 'scheme'] = parsed_uri.scheme
            item[prefix + 'path'] = parsed_uri.path
            item[prefix + 'params'] = parsed_uri.params
            item[prefix + 'query'] = parsed_uri.query
            item[prefix + 'fragment'] = parsed_uri.fragment
        except:
            pass

        # Parse domain
        try:
            domainparts = tldextract.extract(item[prefix + 'domain'])
            item[prefix + 'domain_subdomain'] = domainparts.subdomain
            item[prefix + 'domain_domain'] = domainparts.domain
            item[prefix + 'domain_suffix'] = domainparts.suffix

        except:
            pass

        # Normalize domain
        try:
            domainnormalized = re.sub("^www\.", "", parsed_uri.netloc).lower()
            domainnormalized = re.sub(":[0-9]+$", "", domainnormalized)
            item[prefix + 'domain_normalized'] = domainnormalized
        except Exception as e:
            pass

        urlcache[cachekey] = item

    return urlcache[cachekey]

def extractHtml(html, selector, type='css', dump=False):
    items = []

    if html.strip() != '':
        try:
            try:
                soup = lxml.html.fromstring(html)
            except ValueError:
                soup = lxml.html.fromstring(html.encode('utf-8'))

            if type == 'css':
                for item in soup.cssselect(selector):
                    item = lxml.etree.tostring(item).decode('utf-8').strip()
                    items.append(item)
            elif type == 'xpath':
                result = soup.xpath(selector)
                result = result if isinstance(result, list) else [result]
                for item in result:
                    if isinstance(item,lxml.etree._Element):
                        item = lxml.etree.tostring(item).decode('utf-8')
                    items.append(str(item).strip())

        except Exception as e:
            items.append('ERROR: '+str(e))

    return items

def xmlToJson(data):
    bf = BadgerFish(dict_type=OrderedDict)
    xml = lxml.html.fromstring(data.encode('utf-8'))
    data = bf.data(xml)
    return data

#' Create a new filename from an URL
def makefilename(url = None, foldername=None, filename=None, fileext=None, appendtime=False):  # Create file name
    url_filename, url_fileext = os.path.splitext(os.path.basename(url))
    if fileext is None:
        fileext = url_fileext
    if filename is None:
        filename = url_filename

    filename = re.sub(r'[^a-zA-Z0-9_.-]+', '_', filename.strip())
    fileext = re.sub(r'[^a-zA-Z0-9_.-]+', '', fileext)

    filetime = time.strftime("%Y-%m-%d-%H-%M-%S")
    filenumber = 0

    while True:
        newfilename = filename[:100]
        if appendtime:
            newfilename += '.' + filetime
        if filenumber > 0:
            newfilename += '-' + str(filenumber)

        newfilename += str(fileext)
        fullfilename = os.path.join(foldername, newfilename)

        if (os.path.isfile(fullfilename)):
            filenumber = filenumber + 1
        else:
            break

    return fullfilename


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

        if type(data) == str:
            data = data.encode()

        self._io = io.BytesIO(data)

    def __len__(self):
        return self._len
    
    def rewind(self):
        self._io.seek(0)
        
    def read(self, *args):
        chunk = self._io.read(*args)
        self._progress += int(len(chunk))
        if self._callback:
            try:
                self._callback(self._progress,self._len)
            except:
                raise CancelledError('The upload was cancelled.')

        return chunk

def wraptip(value):
    try:
        value = '<qt>{}</qt>'.format(html.escape(str(value))) if value is not None else value
    except:
        pass
    return value

def dictToTuples(value):
    tuples = []
    for n, v in value.items():
        if isinstance(v, list):
            tuples.extend([(n, s) for s in v])
        else:
            tuples.append((n, v))
    return tuples

def formatdict(data):
    def getdictvalues(data, parentkeys = []):
        out = []
        for key, value in data.items():
            if isinstance(value, Mapping):
                children = getdictvalues(value, parentkeys + [key])
                out.extend(children)
            else:
                child = ".".join(parentkeys + [key]) + " = " + str(value)
                child= "<p>"+wraptip(child)+"</p>"
                out.extend([child])
        return out

    return "\n".join(getdictvalues(data))



def tokenize_with_escape(a, escape='\\', separator='|', n = None):
    '''
        Tokenize a string with escape characters
        @n number of token to consume or None for all tokens
    '''
    result = []
    token = ''
    state = 0
    for i, c in enumerate(a):
        # Rest of string
        if state == 2:
            token += c

        # Next character (state 0: not in escape sequence)
        elif state == 0:
            # Swith to escape sequence state
            if (c == escape) and (i < len(a)-1) and (a[i+1] == separator):
                state = 1

            # Or tokenize
            elif c == separator:
                result.append(token)
                if (n is not None) and (len(result) == n):
                    state = 2

                token = ''

            # Or add to token
            else:
                token += c

        # Escaped character
        elif state == 1:
            token += c
            state = 0


    result.append(token)
    return result
