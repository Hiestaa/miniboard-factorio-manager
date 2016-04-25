# -*- coding: utf8 -*-

from __future__ import unicode_literals

import os
import subprocess
import time
import logging
from threading import Thread
import re

import cv2
from PIL import Image

from tools.utils import extends
from server import model
from conf import Conf

class Walker(Thread):
    """
    This object is dedicated to walk through all the files
    an perform some action on them
    """
    def __init__(self, progress={}, async=True):
        """
        Initialize a new walker that will recursively erun through
        the files of the data folders and perform actions on it.
        If `async` is set to True (default), the walker tasks
        will be performed on a separate thread
        The progress dict will be populated with 4 fields:
            `file`: the name of the current file being processed
            `step`: the processing step currently applied to this file
            `dones`: number of files processed
            `fileList`: list of files that have been processed. Each file is represented by an object with the fields:
                `fileName`, `success` and `error` (error message if success is false)
            `duration`: times spent on the process
            `finished`: False unless the whole walking process is finished.
        """
        super(Walker, self).__init__()
        logging.info("Initializing %s walker"
                     % ('new asynchroneous' if async else 'new'))
        self._progress = extends(
            progress, file='', step='Initializing', dones=0,
            duration=0.0, finished=False, fileList=[])
        self._async = async
        self._start_t = time.time()
        self._tags = []

    def start(self):
        if self._async:
            logging.info("Starting walker process asynchroneously")
            super(Walker, self).start()
        else:
            logging.info("Starting walker process")
            self.run()

    def run(self):
        # reinit progress informations
        self._start_t = time.time()
        self._progress['fileList'] = []
        self._progress['file'] = ''
        self._progress['step'] = 'Initializing'
        self._progress['dones'] = 0
        self._progress['duration'] = 0
        self._progress['finished'] = False

        self._tags = model.getService('tag').getAutoTags()

        self.walk(
            Conf['data']['videos']['rootFolder'],
            [self.__vid_exists,
             self.__generate_snapshots,
             self.__extract_vid_infos,
             self.__save_vid,
             self.__autotag_vid,
             self.__update_video_progress],
            Conf['data']['videos']['allowedTypes']
        )
        self.walk(
            Conf['data']['albums']['rootFolder'],
            [self.__find_album,
             self.__picture_exists,
             self.__update_album_infos,
             self.__save_album,
             self.__autotag_album,
             self.__update_album_progress],
            Conf['data']['albums']['allowedTypes']
        )

        self._progress['duration'] = time.time() - self._start_t
        self._progress['finished'] = True

    def __find_album(self, imgPath, data):
        """
        Find the album related to this picture.
        Create an 'album' entry the data dict containing the
        name of this album.
        """
        self._progress['step'] = 'Looking for related album'
        album = os.path.basename(os.path.abspath(os.path.join(imgPath, os.pardir)))
        logging.debug("Album of img: %s is %s" % (os.path.basename(imgPath), album))
        return extends(data, album=album)

    def __picture_exists(self, imgPath, data):
        """
        Check if the album already holds the current image.
        Create a 'picture_exist' and an 'album_exist' entry
        in the data dict.
        Will also create the album_id entry containing the id of the
        album document if it does exist.
        """
        logging.debug("Checking existence of the image.")
        logging.debug(">> data: %s" % unicode(data))
        self._progress['step'] = 'Checking existence'
        self._progress['file'] = data['album']
        found = model.getService('album').getByRealName(data['album'])
        if found is None:
            data = extends(data, album_exist=False, picture_exist=False, album_id=None)
        elif os.path.basename(imgPath) in found['pictures']:
            data = extends(data, album_exist=True, picture_exist=True, album_id=found['_id'])
        else:
            data = extends(data, album_exist=True, picture_exist=False, album_id=found['_id'])
        return data

    def __update_album_infos(self, imgPath, data):
        """
        Open the image to check the resolution, set of update the
        average resolution of the album as well as the picsNumber.
        If the picture does not exist yet, create the fields
        'picsNumber', 'averageWidth' and 'averageHeight' in the data dict.
        """
        logging.debug("Setting or Updating album infos")
        logging.debug(">> data: %s" % unicode(data))
        if data['album_exist'] and data['picture_exist']:
            return data
        self._progress['step'] = 'Retrieving image informations'

        try:
            f = Image.open(imgPath)
            w, h = f.size
        except:
            return extends(data, error="Unable to open image %s" % os.path.basename(imgPath))

        if data['album_exist']:
            found = model.getService('album').getByRealName(data['album'])
            avgW = float(found['averageWidth'])
            avgH = float(found['averageWidth'])
            nb = found['picsNumber']
            data = extends(
                data,
                averageWidth=((avgW * nb + w) / (nb + 1)),
                averageHeight=((avgH * nb + h) / (nb + 1)))
        else:
            data = extends(
                data,
                averageWidth=w,
                averageHeight=h)

        return data

    def __save_album(self, imgPath, data):
        """
        Insert or update the document matching the album of the current picture
        in the album collection.
        FIXME: do we manage subfolders ?
        """
        logging.debug("Updating albums collection.")
        logging.debug(">> data: %s" % unicode(data))
        if data['album_exist'] and data['picture_exist']:
            return data
        if 'error' in data and data['error']:
            return data

        self._progress['step'] = 'Saving or updating album data'
        if data['album_exist']:
            model.getService('album').set(
                _id=data['album_id'], field='averageWidth', value=data['averageWidth'])
            model.getService('album').set(
                _id=data['album_id'], field='averageHeight', value=data['averageHeight'])
            model.getService('album').addPicture(data['album_id'], os.path.basename(imgPath))
        else:
            _id = model.getService('album').insert(
                album=data['album'], fullPath=os.path.dirname(imgPath), pictures=[os.path.basename(imgPath)],
                averageWidth=data['averageWidth'], averageHeight=data['averageHeight'])
            data = extends(data, inserted_id=_id)

        return data

    def __autotag_album(self, imgPath, data):
        logging.debug("Auto-tagging album")
        logging.debug(">> data: %s" % unicode(data))
        # do only tag if the album did not exist yet
        if data['album_exist'] or not data['inserted_id']:
            return data

        self._progress['step'] = 'Auto-tagging album'
        tagged = [];
        for tag in self._tags:
            if re.search(tag['autotag'], imgPath, flags=re.I):
                logging.debug(
                    "ImgPath: %s matches autotag: %s for tag: %s - %s"
                    % (imgPath, tag['autotag'], tag['name'], tag['value']))
                tagged.append(tag)
                model.getService('album').addTag(data['inserted_id'], tag['_id'])
            else:
                logging.debug(
                    "ImgPath: %s does NOT match autotag: %s"
                    % (imgPath, tag['autotag']))

        if len(tagged) > 0:
            data['msg'] = 'Tagged as: ' + ', '.join(
                    map(lambda t: t['name'].title() + ' - ' + t['value'].title(), tagged))

        return extends(data, tagged=tagged)

    def __update_album_progress(self, imgPath, data):
        logging.debug("Updating progress.")
        # if the album already existed, ignore it
        if not data['album_exist']:
            self._progress['dones'] += 1
            if 'error' in data and data['error']:
                fileObj = {'fileName': data['album'], 'success': False, 'error': data['error']}
            elif 'msg' in data and data['msg']:
                fileObj = {'fileName': data['album'], 'success': True, 'error': data['msg']}
            else:
                fileObj = {'fileName': data['album'], 'success': True, 'error': None}
            if 'inserted_id' in data:
                fileObj['link'] = '/slideshow/albumId=' + data['inserted_id']
                fileObj['snapshot'] = '/download/album/' + data['inserted_id'] + '/0'
            self._progress['fileList'].append(fileObj)
        return data

    def __vid_exists(self, videoPath, data):
        """
        check that the video exist, create the field
        'exist' in the data dict and set it to True or False
        """
        logging.debug("Checking existence of the video")
        logging.debug(">> data: %s" % unicode(data))
        self._progress['step'] = 'Checking existence'
        videoPath = videoPath.replace('/', os.path.sep)
        videoPath = videoPath.replace('\\', os.path.sep)
        found = model.getService('video').getByPath(videoPath)
        if found is not None:
            logging.debug("Video does alread exist!")
            data = extends(data, exists=True)
        else:
            logging.debug("Video does not exist!")
            data = extends(data, exists=False)
        return data

    def __generate_snapshots(self, videoPath, data):
        """
        This will use ffmpeg to create a snapshot of the video.
        """
        # do not rerun the snapshot creation process if data already exists
        if data['exists']:
            return data
        logging.debug("Generating snapshots of video")
        logging.debug(">> Data: %s" % unicode(data))
        self._progress['step'] = 'Generating snapshots'
        spec = {
            'ffmpegpath': Conf['data']['ffmpeg']['exePath'],
            'videoPath': videoPath,
            'ssw': Conf['data']['ffmpeg']['snapshotDimensions'][0],  # width
            'ssh': Conf['data']['ffmpeg']['snapshotDimensions'][1],  # height
            'snapFolder': '.'.join(videoPath.split('.')[:-1]),  # same except trailing extension
            'frameRate': Conf['data']['ffmpeg']['frameRate']
        }
        return_code = 0
        # actual generation
        try:
            if not os.path.exists(spec['snapFolder']):
                os.mkdir(spec['snapFolder'])
                return_code = subprocess.call(
                    '{ffmpegpath} -i "{videoPath}" -f image2 -vf fps=fps={frameRate} -s {ssw}x{ssh} "{snapFolder}\\thumb%03d.png"'.format(**spec),
                    shell=True)
            else:
                data = extends(data, msg="Snapshot folder aldready existed.")
        except Exception as e:
            logging.warning("Unable to generate snapshots: %s." % repr(e).encode())
            return_code = 1
        # verifications
        if not os.path.exists(spec['snapFolder']) or len(os.listdir(spec['snapFolder'])) == 0:
            return extends(data, snapshotsError=True)

        if return_code == 0:
            return extends(data, snapshotsFolder=spec['snapFolder'], snapshotsError=False)
        else:
            return extends(data, snapshotsError=True)

    def __extract_vid_infos(self, videoPath, data):
        def error(data, msg):
            logging.warning(msg)
            return extends(data, cvError=True)
        if data['exists'] or data['snapshotsError']:
            return data
        logging.debug("Extracting informations from video")
        logging.debug(">> Data: %s" % unicode(data))
        self._progress['step'] = 'Extracting informations'
        try:
            cap = cv2.VideoCapture(videoPath)
        except Exception as e:
            logging.error("An exception occured: %s" % repr(e).encode())
            return error(data, "An exception occured while opening video: %s" % videoPath)
        if not cap.isOpened():
            return error(data, "Unable to open video: %s" % videoPath)

        length = float(int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT)))
        w = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.cv.CV_CAP_PROP_FPS))
        if length == 0:
            return error(data, "Unable to find video duration")
        if w == 0:
            return error(data, "Unable to find video width")
        if h == 0:
            return error(data, "Unable to find video height")
        if fps == 0:
            return error(data, "Unable to find video fps")

        return extends(
            data, videoDuration=length / fps, videoResolution=(w, h),
            videoFPS=fps, cvError=False)

    def __save_vid(self, videoPath, data):
        # ignore videos that resulted in a snapshot error or that were already existing
        # also ignore if an error occured while opening the video using openCV
        # unless the insertOnCVError configuration value is set to True
        if data['exists'] or data['snapshotsError'] or (
                data['cvError'] and not Conf['data']['videos']['insertOnCVError']):
            return extends(data, inserted=False)
        logging.debug("Saving video")
        logging.debug(">> Data: %s" % unicode(data))
        self._progress['step'] = 'Database saving'
        _id = model.getService('video').insert(
            filename=videoPath.split(os.path.sep)[-1],
            path=videoPath,
            description='', snapshotsFolder=data['snapshotsFolder'],
            display=0, seen=0, favorite=0,
            duration=data['videoDuration'], resolution=data['videoResolution'],
            fps=data['videoFPS'], tags=[],
            nbSnapshots=len([
                name for name in os.listdir(data['snapshotsFolder'])
                if os.path.isfile(os.path.join(
                    data['snapshotsFolder'], name))])
        )
        return extends(data, inserted=True, inserted_id=_id)

    def __autotag_vid(self, videoPath, data):
        logging.debug("Auto-tagging video")
        logging.debug(">> data: %s" % unicode(data))
        # do only tag if the album did not exist yet
        if data['exists'] or not data['inserted']:
            return data

        tagged = [];
        for tag in self._tags:
            if re.search(tag['autotag'], videoPath, flags=re.I):
                logging.debug(
                    "VideoPath: %s matches autotag: %s for tag: %s - %s"
                    % (videoPath, tag['autotag'], tag['name'], tag['value']))
                tagged.append(tag)
                model.getService('video').addTag(data['inserted_id'], tag['_id'])
            else:
                logging.debug(
                    "videoPath: %s does NOT match autotag: %s"
                    % (videoPath, tag['autotag']))

        if len(tagged) > 0:
            data['msg'] = 'Tagged as: ' + ', '.join(
                    map(lambda t: t['name'].title() + ' - ' + t['value'].title(), tagged))

        return extends(data, tagged=tagged)

    def __update_video_progress(self, videoPath, data):
        logging.debug("Updating progress.")
        # if the video already existed, ignore it
        if not data['exists']:
            self._progress['dones'] += 1
            if data['snapshotsError']:
                fileObj = {'fileName': os.path.basename(videoPath), 'success': False, 'error': 'Snapshot creation failure.'}
            elif data['cvError']:
                fileObj = {'fileName': os.path.basename(videoPath), 'success': False, 'error': 'OpenCV failure.'}
            elif not data['inserted']:
                fileObj = {'fileName': os.path.basename(videoPath), 'success': False, 'error': 'Unable to insert video in database.'}
            elif 'msg' in data and data['msg']:
                fileObj = {'fileName': os.path.basename(videoPath), 'success': True, 'error': data['msg']}
            else:
                fileObj = {'fileName': os.path.basename(videoPath), 'success': True, 'error': None}
            if 'inserted_id' in data:
                fileObj['link'] = '/videoplayer/videoId=' + data['inserted_id']
                fileObj['snapshot'] = '/download/snapshot/' + data['inserted_id'] + '/1'
            self._progress['fileList'].append(fileObj)
        return data

    def walk(self, root, callbacks, types=None):
        """
        This will call the given callbacks on any file contained in the given
        folder or its subfolders.
        types can be specified to call the callback only of the files with
        one of the given extensions. This is expected to be a list of strings.
        The prototype of the callbacks is expected to be:
        `function (videoPath, data)` where `videoPath` is the path of the
        current video, and data is the data returned by the previous callback
        for this video (or an empty dict for the first one.)
        """
        logging.info("Starting walking process from folder: %s" % root)
        for dirpath, dirnames, filenames in os.walk(root):
            dirpath = dirpath.replace('\\', os.path.sep)
            dirpath = dirpath.replace('/', os.path.sep)
            for f in filenames:
                if types is None or f.split('.')[-1] in types:
                    logging.info("Processing: %s" % os.path.join(dirpath, f))
                    self._progress['file'] = f
                    self._progress['duration'] = time.time() - self._start_t
                    res = {}
                    try:
                        for cb in callbacks:
                            res = cb(os.path.join(dirpath, f), res)
                    except Exception as e:
                        self._progress['fileList'].append({
                            'fileName': f,
                            'success': False,
                            'error': repr(e)
                        })
