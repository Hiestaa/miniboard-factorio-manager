#!/usr/bin/python

# -*- coding: utf8 -*-

from __future__ import unicode_literals

from tornado.web import RequestHandler, HTTPError

import logging

from conf import Conf


class TemplatesHandler(RequestHandler):
    """Handle the requests of the root page"""
    def get(self, filename=None):
        templateRoutes = {
            'join': 'join.html',
            'manage': 'base.html',
            'saves': 'base.html',
            'monitor': 'base.html'
        }
        fullWidth = ['']
        if filename is None or not filename:
            self.render(
                'join.html', currentPage='home', fullWidth=False,
                port=Conf['server']['port'], ip=Conf['server']['ip'])
        elif filename in templateRoutes:
            self.render(templateRoutes[filename],
                        currentPage=filename,
                        debug=Conf['state'] == 'DEBUG',
                        port=Conf['server']['port'], ip=Conf['server']['ip'],
                        fullWidth=filename in fullWidth)
        elif filename.split('/')[0] in templateRoutes:
            splitted = filename.split('/')
            filename, args = splitted[0], splitted[1:]
            kwtargs = {
                arg.split('=')[0]: arg.split('=')[1]
                for arg in args if len(arg.split('=')) > 1
            }
            self.render(
                templateRoutes[filename],
                currentPage=filename, debug=Conf['state'] == 'DEBUG',
                port=Conf['server']['port'], ip=Conf['server']['ip'],
                fullWidth=filename in fullWidth,
                **kwtargs)
        else:
            logging.error("Unable to find item %s" % filename)
            raise HTTPError(404)
