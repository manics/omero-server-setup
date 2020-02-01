#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Wrap openssl to manage self-signed certificates
"""

import logging
import os
from .external import External

log = logging.getLogger(__name__)


class CreateConfig(object):
    def __init__(self, omerodir, args):
        self.dir = omerodir
        self.args = args
        if not os.path.exists(self.dir):
            raise Exception("%s does not exist!" % self.dir)
        self.external = External(self.dir)

    def choose_omero_data_home(self):
        # if os.path.exists('/OMERO'):
        #     return '/OMERO'
        parent = os.getenv('CONDA_PREFIX', os.getenv('HOME'))
        if not parent:
            raise Exception(
                'Unable to determine omero.data.dir. Pass --data-dir.')
        return os.path.join(parent, 'OMERO')

    def create_or_update_config(self):
        try:
            cfgmap = self.external.get_config()
        except Exception as e:
            log.warning('config.xml not found: %s', e)
            cfgmap = {}
        created = {}

        def update_value(cfgkey, argname, default=None):
            if cfgkey in cfgmap:
                created[cfgkey] = cfgmap[cfgkey]
            elif argname in self.args and getattr(
                    self.args, argname) is not None:
                created[cfgkey] = getattr(self.args, argname)
            elif default is None:
                raise Exception(
                    'No configuration value for {}'.format(cfgkey))
            else:
                created[cfgkey] = default
            log.debug('%s=%s', cfgkey, created[cfgkey])

        # OMERO database
        update_value('omero.db.name', 'dbname', 'omero')
        update_value('omero.db.host', 'dbhost', 'localhost')
        update_value('omero.db.user', 'dbuser', 'omero')
        update_value('omero.db.pass', 'dbpass', 'omero')

        update_value('omero.data.dir', 'data_dir', '/OMERO')
        if created['omero.data.dir'].lower() == 'auto':
            created['omero.data.dir'] = self.choose_omero_data_home()

        # PostgreSQL
        if self.args.manage_postgres:
            update_value('postgres.data.dir', '',
                         os.path.join(created['omero.data.dir'], 'pgdata'))
            update_value('omero.db.port', 'dbport', '15432')
            # TODO: Set to a random port?
            # created['omero.db.port'] = str(randint(30000, 60000))
        else:
            update_value('omero.db.port', 'dbport', '5432')

        # Certificates and websockets
        if self.args.certs:
            update_value('omero.glacier2.IceSSL.DefaultDir', '',
                         os.path.join(created['omero.data.dir'], 'certs'))
            update_value('ssl.certificate.commonname', '', 'localhost')
            update_value('ssl.certificate.owner', '',
                         '/L=OMERO/O=OMERO.server')
            update_value('ssl.certificate.key', '', 'server.key')
            update_value('omero.glacier2.IceSSL.CertFile', '', 'server.p12')
            update_value('omero.glacier2.IceSSL.CAs', '', 'server.pem')
            update_value('omero.glacier2.IceSSL.Password', '', 'secret')
            update_value('omero.glacier2.IceSSL.Ciphers', '', 'ADH:HIGH')

        if self.args.websockets:
            update_value('omero.client.icetransports', '', 'ssl,wss')

        if not self.args.dry_run:
            self.external.update_config(created)

        log.info('Configuration: %s', created)
        return created
