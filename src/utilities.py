import json

def getDictValue(data,multikey,dump=True):
    try:
        keys=multikey.split('.',1)
                    
        if type(data) is dict and keys[0] != '':
            value=data.get(keys[0],"")
            if len(keys) > 1:            
                value = getDictValue(value,keys[1],dump)  
                
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
        else:        
            return value
    except Exception as e:
        return ""


