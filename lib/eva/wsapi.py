__author__ = "Altertech Group, https://www.altertech.com/"
__copyright__ = "Copyright (C) 2012-2021 Altertech Group"
__license__ = "Apache License 2.0"
__version__ = "3.4.0"

import cherrypy
import eva.core
from eva import apikey
from eva.api import cp_forbidden_key
from eva.api import cp_client_key
from eva.api import http_real_ip
from eva.types import CT_JSON, CT_MSGPACK
from eva.notify import NWebSocket
from eva.notify import WSNotifier_Client

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool


class WS_API(object):

    @cherrypy.expose
    def default(self, k=None, c=CT_JSON, buf_ttl=0):
        _k = cp_client_key(k)
        if not apikey.check(_k, ip=http_real_ip()):
            raise cp_forbidden_key()
        handler = cherrypy.request.ws_handler
        token = k if isinstance(k, str) and k.startswith('token:') else None
        client = WSNotifier_Client('ws_' + eva.core.product.code + '_' + \
                cherrypy.request.remote.ip + '_' + \
                str(cherrypy.request.remote.port), _k, token, handler,
                ct=int(c), buf_ttl=float(buf_ttl))
        handler.notifier = client
        client.start()


def start():
    WebSocketPlugin(cherrypy.engine).subscribe()
    cherrypy.tools.websocket = WebSocketTool()
    config = {
        '/': {
            'tools.websocket.on': True,
            'tools.websocket.handler_cls': NWebSocket,
        }
    }
    cherrypy.tree.mount(WS_API(), '/ws', config=config)
