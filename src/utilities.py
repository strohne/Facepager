import json

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
