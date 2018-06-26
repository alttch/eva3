__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2018 Altertech Group"
__license__ = "https://www.eva-ics.com/license"
__version__ = "3.1.0"

import cherrypy
import eva.core
from eva import apikey
from eva.api import cp_forbidden_key
from eva.api import cp_client_key
from eva.api import session_timeout
from eva.api import http_real_ip
from eva.notify import NWebSocket
from eva.notify import WSNotifier_Client

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool


class WS_API(object):

    @cherrypy.expose
    def default(self, k=None):
        _k = cp_client_key(k)
        if not apikey.check(_k, ip=http_real_ip()): raise cp_forbidden_key()
        handler = cherrypy.request.ws_handler
        client = WSNotifier_Client('ws_' + eva.core.product_code + '_' + \
                cherrypy.request.remote.ip + '_' + \
                str(cherrypy.request.remote.port), _k, handler)
        handler.notifier = client


def start():
    WebSocketPlugin(cherrypy.engine).subscribe()
    cherrypy.tools.websocket = WebSocketTool()
    cherrypy.tree.mount(
        WS_API(),
        '/ws',
        config={
            '/': {
                'tools.websocket.on': True,
                'tools.websocket.handler_cls': NWebSocket,
                'tools.sessions.on': True,
                'tools.sessions.timeout': session_timeout
            }
        })
