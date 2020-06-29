from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import cgi
from PySide2.QtCore import QObject, Signal, Slot
from urllib.parse import urlparse, parse_qs, unquote

class Server(ThreadingHTTPServer, QObject):
    action = Signal(str, str, dict)

    def __init__(self, port, api):
        QObject.__init__(self)
        self.api = api
        HandlerClass = self.requestHandlerFactory(self.api.getState, self.actionCallback)
        ThreadingHTTPServer.__init__(self,('localhost', port), HandlerClass)
        self.action.connect(self.api.action)

    def actionCallback(self, action=None, param=None, payload=None):
        self.action.emit(action, param, payload)


    def requestHandlerFactory(self, stateCallback, actionCallback):
        """Factory method to pass parameters to request handler"""

        class CustomHandler(RequestHandler):
            def __init__(self, *args, **kwargs):
                self.stateCallback = stateCallback
                self.actionCallback = actionCallback
                super(RequestHandler, self).__init__(*args, **kwargs)

        return CustomHandler


class RequestHandler(BaseHTTPRequestHandler):


    def __init__(self, *args, **kwargs):
        #self.actionCallback = None
        #self.stateCallback = None
        super(RequestHandler, self).__init__(*args, **kwargs)

    def set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def send_answer(self, content, status=200):
        self.set_headers(status)
        response = json.dumps(content)
        self.wfile.write(response.encode('utf-8'))

    def parseAction(self):
        action = {}

        try:
            # Parse headers
            contenttype_value, contenttype_params = cgi.parse_header(self.headers.get('content-type',''))
            action['contenttype'] = contenttype_value

            # refuse to receive non-json content
            # if contenttype_value != 'application/json':
            #     self.send_response(400)
            #     self.end_headers()
            #     return

            # Parse path
            url = urlparse(self.path)
            action['path'] = url.path.strip("/").split("/")
            action['path'] = [unquote(x) for x in action['path']]
            action['action'] = action['path'].pop(0)
            action['query'] = parse_qs(url.query)

            # Read post data
            length = int(self.headers.get('content-length'))
            action['body'] = json.loads(self.rfile.read(length))
        except Exception as e:
            action['error'] = str(e)

        return action

    def do_HEAD(self):
        self.set_headers()

    # Sends back the state and database name
    def do_GET(self):
        response = {}
        response = self.stateCallback('options')
        self.send_answer(response)

    def do_POST(self):
        """
        Execute actions

        The first component of the URL path is the action name.
        The following components are parameters.
        Additional data ist provided in the payload.
        """

        action = self.parseAction()

        # Handle actions
        try:
            if action['action'] == "opendatabase":
                filename = action['query'].get('filename', []).pop()
                if not filename:
                    result = "Missing filename."
                else:
                    self.actionCallback(action['action'], filename)
                    result = "ok"

            elif action['action'] == "addnodes":
                nodes = action['body'].get('nodes',[])
                if not (type(nodes) is list):
                    nodes = [nodes]
                self.actionCallback(action['action'], None, nodes)
                result = "ok"

            elif action['action'] == "addcsv":
                filename = action['query'].get('filename', []).pop()
                if not filename:
                    result = "Missing filename."
                else:
                    self.actionCallback(action['action'], filename)
                    result = "ok"

            elif action['action'] == "loadpreset":
                filename = action['query'].get('filename', []).pop()
                if not filename:
                    result = "Missing filename."
                else:
                    self.actionCallback(action['action'], filename)
                    result = "ok"

            elif action['action'] == "fetchdata":
                self.actionCallback(action['action'])
                result = "ok"

            else:
                self.send_response(404, "No valid action!")
                self.end_headers()
                return False
        except Exception as e:
            self.send_response(500, "Server error!")
            self.end_headers()
            return False

        # Resonse
        response = self.stateCallback()
        response['result'] = result

        self.send_answer(response)
        return True
