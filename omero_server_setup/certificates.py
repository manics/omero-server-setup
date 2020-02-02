#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Wrap openssl to manage self-signed certificates
"""

import logging
import os
from .external import (
    run,
    RunException,
)

log = logging.getLogger(__name__)


def create_certificates(external):
    cfgmap = external.get_config()

    def getcfg(key):
        if key not in cfgmap or not cfgmap[key]:
            raise Exception('Property {} required'.format(key))
        log.debug('%s=%s', key, cfgmap[key])
        return cfgmap[key]

    enabled = getcfg('setup.omero.certs').lower()
    if enabled != 'true':
        log.warning('setup.omero.certs is false, not doing anything')
        return

    certdir = getcfg('omero.glacier2.IceSSL.DefaultDir')

    cn = getcfg('ssl.certificate.commonname')
    owner = getcfg('ssl.certificate.owner')
    days = '365'
    pkcs12path = os.path.join(
        certdir, getcfg('omero.glacier2.IceSSL.CertFile'))
    keypath = os.path.join(certdir, getcfg('ssl.certificate.key'))
    certpath = os.path.join(certdir, getcfg('omero.glacier2.IceSSL.CAs'))
    password = getcfg('omero.glacier2.IceSSL.Password')

    try:
        run('openssl', ['version'])
    except RunException as e:
        raise Exception(
            'Failed to run openssl, is it installed?:\n  {}'.format(e))

    os.makedirs(certdir, exist_ok=True)

    # Private key
    if os.path.exists(keypath):
        log.info('Using existing key: %s', keypath)
    else:
        log.info('Creating self-signed CA key: %s', keypath)
        run('openssl', ['genrsa', '-out', keypath, '2048'])
    # Self-signed certificate
    log.info('Creating self-signed certificate: %s', certpath)
    run('openssl', [
        'req', '-new', '-x509',
        '-subj', '{}/CN={}'.format(owner, cn),
        '-days', days,
        '-key', keypath, '-out', certpath,
        '-extensions', 'v3_ca',
    ])
    # PKCS12 format
    log.info('Creating PKCS12 bundle: %s', pkcs12path)
    run('openssl', [
        'pkcs12', '-export',
        '-out', pkcs12path,
        '-inkey', keypath,
        '-in', certpath,
        '-name', 'server',
        '-password', 'pass:{}'.format(password),
    ])
