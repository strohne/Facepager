
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