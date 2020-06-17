from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import cgi
import actions

class Server(ThreadingHTTPServer):
    def __init__(self, port, actions):
        HandlerClass = self.requestHandlerFactory(actions)
        super(Server, self).__init__(('localhost', port), HandlerClass)

    def requestHandlerFactory(self, actions):
        """Factory method to pass parameters to request handler"""
        class CustomHandler(RequestHandler):
            def __init__(self, *args, **kwargs):
                self.actions = actions
                super(CustomHandler, self).__init__(*args, **kwargs)
        return CustomHandler


class RequestHandler(BaseHTTPRequestHandler):
    def set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def send_answer(self, content):
        self.set_headers()
        response = json.dumps(content)
        self.wfile.write(response.encode('utf-8'))

    def do_HEAD(self):
        self.set_headers()

    # GET sends back the database name
    def do_GET(self):
        response = {'database': self.actions.getDatabaseName()}
        self.send_answer(response)

    # POST echoes the message adding a JSON field
    def do_POST(self):
        ctype, pdict = cgi.parse_header(self.headers.get('content-type'))

        # refuse to receive non-json content
        if ctype != 'application/json':
            self.send_response(400)
            self.end_headers()
            return
        #self.get_payload
        # read the message and convert it into a python dictionary
        length = int(self.headers.get('content-length'))
        message = json.loads(self.rfile.read(length))
        response = {'database': self.actions.getDatabaseName()}

        if message.get('action') == 'addnodes':
            self.actions.addNodes(message.get('data'))


        self.send_answer(response)



