import eva.core
import eva.sfa.controller
import eva.api

from eva.api import cp_api_404

import cherrypy
import jinja2


class CloudManager():

    def __init__(self):
        j2_loader = jinja2.FileSystemLoader(searchpath=eva.core.dir_lib +
                                            '/cloudmanager')
        self.j2 = jinja2.Environment(loader=j2_loader)

    @cherrypy.expose
    def index(self):
        try:
            template = self.j2.get_template('cm.j2')
        except:
            raise cp_api_404()
        env = {'build': eva.core.product_build}
        if eva.core.development:
            env['development'] = True
        return template.render(env)


cp_cm_config = {}

for u in ['css', 'fonts', 'i', 'images', 'js', 'lib']:
    cp_cm_config['/' + u] = {
        'tools.staticdir.dir': eva.core.dir_lib + '/cloudmanager/' + u,
        'tools.staticdir.on': True
    }


def start():
    return
    if not eva.sfa.controller.config.cloud_manager: return
    cherrypy.tree.mount(
        CloudManager(), '/cloudmanager', config=cp_cm_config)
