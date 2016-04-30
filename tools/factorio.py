# -*- coding: utf8 -*-

from __future__ import unicode_literals

"""
Implements helper functions related to factorio server instances
"""

import subprocess
import time
import os
import signal
import platform
import shutil
from multiprocessing import Process, Value, Queue
from Queue import Empty
from fcntl import fcntl, F_GETFL, F_SETFL
from os import O_NONBLOCK, read

from conf import Conf


class FactorioException(Exception):
    pass


configFolder = os.path.join(*Conf['factorio']['configFolder'].split('/'))
savesFolder = os.path.join(*Conf['factorio']['savesFolder'].split('/'))
binary = os.path.join(*Conf['factorio']['binary'].split('/'))
PIDFILE = os.path.join('db', 'pidfile.txt')
SAVE_INTERVAL = Conf['factorio']['autosaveInterval']


class Instance(Process):
    """Wrapper to start and kill factorio instances."""
    def __init__(self, listeningPort, save, _id):
        super(Instance, self).__init__()
        self.port = str(listeningPort)
        self.saveFile = os.path.join(savesFolder, '%s.zip' % save)
        self.logQueue = Queue()
        self.killed = Value('b')
        self.killed.value = 0
        self.lastSave = time.time()
        self.waitForPID = None
        self.subpid = Value('I')
        self._id = _id

    def ensureConfigExists(self):
        """
        Make sure that the config file for the instance port is existing.
        Create itt otherwise.
        """
        try:
            # check that config exist for this port
            f = open(os.path.join(
                configFolder,
                'config.%s.ini' % self.port), 'r')
            f.close()
        except IOError:
            # config does not exist - create it
            with open(os.path.join(
                    configFolder,
                    'config.%s.ini' % self.port), 'w') as newConfig:
                with open(os.path.join(
                        configFolder,
                        'config.ini' % self.port), 'r') as defaultConfig:
                    for line in defaultConfig:
                        try:
                            k, v = line.split('=')
                            if k == 'port':
                                v = self.port + '\n'
                            newConfig.write('%s=%s\n' % (k, v))
                        except ValueError:
                            newConfig.write(line)

    def findMostRecentAutosave(self):
        """
        Find and return the path to the most recent auto-save file.
        """
        autosaves = []
        for file in os.listdir(savesFolder):
            if file.startswith('_autosave'):
                stat = os.stat(os.path.join(savesFolder, file))
                autosaves.append(
                    (os.path.join(savesFolder, file), stat.st_mtime))

        return sorted(autosaves, key=lambda itm: itm[1], reverse=True)[0][0]

    def backupSave(self):
        """
        Backup the autosave, overriding initial save file and creating a backup
        of the data.
        """
        src = self.findMostRecentAutosave()
        dst1 = self.saveFile
        dst2 = self.saveFile + '_back.zip'
        shutil.copyfile(src, dst1)
        shutil.copyfile(src, dst2)

    def execFactorioWindows(self):
        self.ensureConfigExists()
        command = [
            binary, '--config',
            os.path.join(configFolder, 'config.%s.ini' % self.port),
            '--start-server', self.saveFile,
            '--autosave-interval', SAVE_INTERVAL]
        if self.waitForPID is not None:
            command += ['--wait-to-close', self.waitForPID]
        p = subprocess.Popen(
            command,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)

        with open(PIDFILE, 'w') as f:
            f.write(p.pid + ' ' * 10)
        self.subpid.value = p.pid

        # set the O_NONBLOCK flag of p.stdout file descriptor:
        flags = fcntl(p.stdout, F_GETFL)  # get current p.stdout flags
        fcntl(p.stdout, F_SETFL, flags | O_NONBLOCK)

        while not self.killed.value:
            try:
                self.logQueue.put(read(p.stdout.fileno(), 1024))
            except OSError:
                # the os throws an exception if there is no data
                self.logQueue.get('[No more data]')
                break
            time.sleep(1)
            # SAVE_INTERVAL is in minutes
            if time.time() - self.lastSave > SAVE_INTERVAL * 60:
                self.lastSave = time.time()
                self.backupSave()

        os.kill(self.subpid.value, signal.CTRL_C_EVENT)
        time.sleep(2)
        self.backupSave()
        # os.kill(pid, signal.SIGINT)
        # os.kill(pid, signal.SIGHUP)
        # os.kill(pid, signal.SIGKILL)

    def execFactorioMacOS(self):
        raise FactorioException(
            "Factorio execution is not supported on MacOS.")

    def execFactorioLinux(self):
        raise FactorioException(
            "Factorio execution is not supported on Linux.")

    if platform.system() == 'Windows':
        execFactorio = execFactorioWindows
    if platform.system() == 'Linux':
        execFactorio = execFactorioLinux
    else:  # macos?
        execFactorio = execFactorioMacOS

    def run(self):
        try:
            with open(PIDFILE, 'r') as f:
                pid = f.read().strip()
            self.logQueue.put("Found a running factorio instance, killing it.")
            os.kill(pid, signal.CTRL_C_EVENT)
            self.waitForPID = pid
            time.sleep(2)
            # os.kill(pid, signal.SIGINT)
            # os.kill(pid, signal.SIGHUP)
            # os.kill(pid, signal.SIGKILL)
        except IOError:
            pass  # couldn't kill the running instance, maybe it is not running
        # TODO: test this code in an environment that can run the process
        try:
            self.execFactorio()
        except Exception as e:
            self.logQueue.put('[ERROR] ' + str(e))
        self.killed.value = 1

    def read(self):
        """
        From the main process, read from the log queue and return whatever was
        read.
        Return None if nothing was read.
        """
        try:
            return self.logQueue.get()
        except Empty:
            return None

    def kill(self):
        """ Expected to be called from the main process """
        self.killed.value = 1
