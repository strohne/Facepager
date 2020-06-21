from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import cgi
from PySide2.QtCore import QObject, Signal
from urllib.parse import urlparse, parse_qs, unquote

class Server(ThreadingHTTPServer):

    def __init__(self, port, api, callback):
        HandlerClass = self.requestHandlerFactory(api, callback)
        super(Server, self).__init__(('localhost', port), HandlerClass)

    def requestHandlerFactory(self, api, callback):
        """Factory method to pass parameters to request handler"""
        class CustomHandler(RequestHandler):
            def __init__(self, *args, **kwargs):
                self.api = api
                self.action.connect(callback)
                super(CustomHandler, self).__init__(*args, **kwargs)


        return CustomHandler


class RequestHandler(BaseHTTPRequestHandler, QObject):
    action = Signal(str, str, dict)

    def __init__(self, *args, **kwargs):
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
        response['database'] = self.api.getDatabaseName()
        response['state'] = self.api.getState()
        self.send_answer(response)

    def do_POST(self):
        """
        Execute actions

        The first component of the URL path is the action name.
        The following components are parameters.
        Additional data ist provided in the payload.
        """

        action = self.parseAction()
        response = {}

        # Handle actions
        try:
            if action['action'] == "opendatabase":
                filename = action['query'].get('filename', []).pop()
                if not filename:
                    result = "Missing filename."
                else:
                    self.action.emit(action['action'], filename)
                    result = "Scheduled"

            elif action['action'] == "addnodes":
                nodes = action['body'].get('nodes',[])
                self.action.emit(action['action'], None, nodes)
                result = "Scheduled"

            elif action['action'] == "addcsv":
                filename = action['query'].get('filename', []).pop()
                if not filename:
                    result = "Missing filename."
                else:
                    self.action.emit(action['action'], filename)
                    result = "Scheduled"

            elif action['action'] == "loadpreset":
                filename = action['query'].get('filename', []).pop()
                if not filename:
                    result = "Missing filename."
                else:
                    self.action.emit(action['action'], filename)
                    result = "Scheduled"

            elif action['action'] == "fetchdata":
                self.action.emit(action['action'])
                result = "Scheduled"

            else:
                self.send_response(404, "No valid action!")
                self.end_headers()
                return False
        except Exception as e:
            self.send_response(500, "Server error!")
            self.end_headers()
            return False

        response['database'] = self.api.getDatabaseName()
        response['state'] = self.api.getState()
        response['result'] = result

        self.send_answer(response)
        return True

