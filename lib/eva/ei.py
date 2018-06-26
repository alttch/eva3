import eva.core
from eva.api import cp_api_404

import cherrypy
import jinja2


class EI_HTTP_Root:

    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect('/%s-ei/' % eva.core.product_code)


class EI():

    def __init__(self):
        j2_loader = jinja2.FileSystemLoader(searchpath=eva.core.dir_lib + '/ei')
        self.j2 = jinja2.Environment(loader=j2_loader)

    @cherrypy.expose
    def index(self):
        try:
            template = self.j2.get_template('%s.j2' % eva.core.product_code)
        except:
            raise cp_api_404()
        env = {
            'build': eva.core.product_build,
            'product_name': eva.core.product_name,
            'product_code': eva.core.product_code
        }
        return template.render(env)


cp_ei_root_config = {
    '/favicon.ico': {
        'tools.staticfile.on': True,
        'tools.staticfile.filename': eva.core.dir_eva + '/lib/eva/i/favicon.ico'
    }
}

cp_ei_config = {}

for u in ['css', 'fonts', 'i', 'js', 'lib']:
    cp_ei_config['/' + u] = {
        'tools.staticdir.dir': eva.core.dir_lib + '/ei/' + u,
        'tools.staticdir.on': True
    }


def start():
    cherrypy.tree.mount(EI_HTTP_Root(), '/', config=cp_ei_root_config)
    cherrypy.tree.mount(
        EI(), '/%s-ei' % eva.core.product_code, config=cp_ei_config)
