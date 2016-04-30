# -*- coding: utf8 -*-

from __future__ import unicode_literals

"""
Implements helper functions related to factiorio saved games
"""

import os
import logging

from conf import Conf
from tools import utils


class SavesException(Exception):
    pass


def list():
    """
    Returns the list of saves found in Factorio's saves folder as a dict
    holding the following fields:
    * name: name of the save (filename stripped off of its .zip extension)
    * date: date of the save
    * size: size of the archive
    """
    # import ipdb; ipdb.set_trace()
    dirpath = '/' if Conf['factorio']['savesFolder'][0] == '/' else ''
    dirpath += os.path.join(*Conf['factorio']['savesFolder'].split('/'))
    try:
        files = os.listdir(dirpath)
    except Exception as e:
        logging.error(e)
        raise SavesException(
            "Unable to access folder `%s': %s" % (
                Conf['factorio']['savesFolder'], str(e)))
    savedGames = []
    for savedGame in files:
        if savedGame[-4:] == '.zip':
            data = {'name': savedGame[:-4]}
            stat = os.stat(os.path.join(
                Conf['factorio']['savesFolder'], savedGame))
            data['date'] = utils.dateFormat(stat.st_mtime)
            data['size'] = utils.sizeFormat(stat.st_size)
            savedGames.append(data)

    return savedGames
