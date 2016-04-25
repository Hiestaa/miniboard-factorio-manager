# -*- coding: utf8 -*-

from __future__ import unicode_literals

import logging


Conf = {
    'state': 'DEBUG',
    'log': {
        'fileLevel': logging.WARNING
    },
    'database': {
        'name': 'db/miniboard-factorio.db'
    },
    'server': {
        'port': 6666,
        'assets': {
            'minifiedCleanups': [
                'http/assets/custom/css/',
                'http/assets/custom/js/'
            ],
            'minifyOnDebug': False
        },
    }
}
