# -*- coding: utf8 -*-

from __future__ import unicode_literals

import logging
import netifaces


def getIpWindows(adapteridx):
    try:
        import wmi
    except:
        logging.error("You must need Win32com (win32 extensions for python)")
        raise

    adapters = wmi.WMI().Win32_NetworkAdapter()
    wlan_int_id = adapters[adapteridx].Index
    adaptername = adapters[adapteridx].NetConnectionID

    ip = ''
    for nic in wmi.WMI().Win32_NetworkAdapterConfiguration(IPEnabled=1):
        if nic.Index == wlan_int_id:
            ip = nic.IPAddress[0]
    logging.info("[Windows] Showing IP for adapter %d (%s): %s",
                 adapteridx, adaptername, ip)
    return ip


def filtre(addrInfo):
    for typ, addrList in addrInfo.iteritems():
        if len(addrList) == 0:
            continue
        for addrDetails in addrList:
            if len(addrDetails.get('addr', '').split('.')) != 4:
                continue
            if not addrDetails.get('addr').startswith('192.168') and\
                    addrDetails.get('addr') != '127.0.0.1' and not \
                    addrDetails.get('addr').startswith('0'):
                return addrDetails.get('addr')


def getIp(adapteridx):
    adapters = netifaces.interfaces()
    addrInfo = [netifaces.ifaddresses(a) for a in adapters]
    addrInfo = [filtre(info) for info in addrInfo]
    addrInfo = [info for info in addrInfo if info is not None]
    return addrInfo[adapteridx % len(addrInfo)]


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
        'ip': '',
        'assets': {
            'minifiedCleanups': [
                'http/assets/custom/css/',
                'http/assets/custom/js/'
            ],
            'minifyOnDebug': False
        },
    }
}
