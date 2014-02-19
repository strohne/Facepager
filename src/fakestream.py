#!/usr/bin/env python

import gevent
import gevent.monkey
from gevent.pywsgi import WSGIServer


from flask import Flask, request, Response, render_template, jsonify

app = Flask(__name__)

def event_stream():
    count = 0
    while True:
        gevent.sleep(1)
        yield '{"data":1}\n\n'

@app.route('/fakestream')
def sse_request():
    return Response(
            event_stream(),mimetype="text/html", status=420)

if __name__ == '__main__':
    http_server = WSGIServer(('127.0.0.1', 8001), app)
    http_server.serve_forever()