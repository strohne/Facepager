import json

def getDictValue(data,multikey):
    keys=multikey.split('.')                
    value=data
    for key in keys:
        if type(value) is dict:
            value=value.get(key,"")
        elif type(value) is list:
            valuelist=[]
            for elem in value:
                if key in elem:
                    valuelist.append(elem[key])
                else:
                    valuelist.append(elem)
            return ";".join(str(vlelem) for vlelem in valuelist)
        else:
            return ""
    if type(value) is dict:
        return json.dumps(value) 
    else:        
        return value   
