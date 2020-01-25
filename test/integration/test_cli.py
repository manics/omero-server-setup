#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from subprocess import check_output
from uuid import uuid4

from omero_database.db import (
    DbAdmin,
    # Stop,
)
from omero_database.external import External


DB_ADMIN_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')


class Args(object):
    def __init__(self, dbid, **kwargs):
        default_args = dict(
            dbcommand=None,
            no_db_config=False,
            dry_run=False,
            omerosql=None,
            rootpass='omero',
            dbname=dbid,
            dbuser=dbid,
            dbhost=DB_HOST,
            dbpass=dbid,
        )

        for k, v in default_args.items():
            setattr(self, k, v)
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestDbAdmin(object):

    def setup_method(self, method):
        self.dbid = 'x' + str(uuid4()).replace('-', '')
        self.psqlc("CREATE USER {0} WITH PASSWORD '{0}';")
        self.psqlc("CREATE DATABASE {0} WITH OWNER {0};")

    def teardown_method(self, method):
        self.psqlc("DROP DATABASE {0};")
        self.psqlc("DROP ROLE {0};")

    def psqlc(self, query, *args):
        cmd = ['psql']
        if DB_HOST:
            cmd += ['-h', DB_HOST]
        cmd += ['-U', DB_ADMIN_USER, '-c', query.format(self.dbid), '-At'
                ] + list(args)
        # print(cmd)
        out = check_output(cmd)
        # print(out)
        return out

    def test_init(self):
        omerodir = os.getenv('OMERODIR')
        args = Args(self.dbid)
        DbAdmin(omerodir, 'init', args, External(omerodir))
        r = self.psqlc('SELECT currentversion, currentpatch FROM dbpatch '
                       'ORDER BY id DESC', '-d', self.dbid)
        assert r.splitlines() == [b'OMERO5.4|0']

    def test_init_from_and_upgrade(self):
        omerodir = os.getenv('OMERODIR')
        omerosql = os.path.join(
            os.path.dirname(__file__), '..', 'resources', 'OMERO5.3__1.sql')
        args = Args(self.dbid, omerosql=omerosql)
        DbAdmin(omerodir, 'init', args, External(omerodir))
        r = self.psqlc('SELECT currentversion, currentpatch FROM dbpatch '
                       'ORDER BY id ASC', '-d', self.dbid)
        assert r.splitlines() == [b'OMERO5.3|1', b'OMERO5.4|0']
        # Only the temporary omerosql file should be deleted
        assert os.path.exists(omerosql)
