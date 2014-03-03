import json

with open("{0}.json".format(self.__class__.__name__),"r") as docfile:
    apidoc = []
    rawdoc = json.load(docfile)

    #Filter out everything besides get requests
    rawdoc = [endpoint for endpoint in rawdoc["application"]["endpoints"][0]["resources"] if endpoint["method"]["name"]=="GET"]

    for endpoint in rawdoc:
        #Prepare path
        pathname = endpoint["path"].split(".json")[0].lstrip("/").replace('{','<').replace('}','>')

        #Prepare documentation
        docstring = "<p>"+endpoint["method"]["doc"]["content"]+"</p>"

        #Prepare params
        params = []
        for param in endpoint["method"].get("params",[]):
            #Properties of param
            paramreq = param.get("required",False)
            paramname = param["name"]
            if param.get("style","query") == "template":
                paramname = '<'+paramname+'>'
                paramdefault = '<Object ID>'
            else:
                paramdefault = ''

            #Documentation of param
            paramdoc = param.get("doc",{}).get("content","No description found").encode("utf8")
            if paramreq:
                paramdoc = '<p style="color:#FF333D";">{0}</p><b>[Mandatory Parameter]</b>'.format(paramdoc)
            else:
                paramdoc = '<p>{0}</p>'.format(paramdoc)

            #Options of param
            paramoptions = [{'name':val.get("value","")} for val in param.get('options',[])]

            #Append param
            params.append({'name':paramname,
                           'doc':paramdoc,
                           'required':paramreq,
                           'default':paramdefault,
                           'options':paramoptions
                           })

        #Append data
        apidoc.append({'path': pathname,
                            'doc': docstring,
                            'params':params
                            })
    json.dump(apidoc, open(self.__class__.__name__+"_final.json","w"))