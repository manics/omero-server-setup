#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from subprocess import check_output
from uuid import uuid4

from omero_database import (
    DbAdmin,
    DB_INIT_NEEDED,
    DB_UPGRADE_NEEDED,
    DB_UPTODATE,
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
        self.omerodir = os.getenv('OMERODIR')
        self.omero531sql = os.path.join(
            os.path.dirname(__file__), '..', 'resources', 'OMERO5.3__1.sql')

    def teardown_method(self, method):
        self.psqlc("DROP DATABASE {0};")
        self.psqlc("DROP ROLE {0};")

    def psqlc(self, query, *args, admin=True):
        cmd = ['psql']
        if DB_HOST:
            cmd += ['-h', DB_HOST]
        if admin:
            cmd += ['-U', DB_ADMIN_USER]
        cmd += ['-At'] + list(args)
        if query:
            cmd += ['-c', query.format(self.dbid)]
        out = check_output(cmd)
        # print(cmd, out)
        return out

    def test_check(self):
        argscheck = Args(self.dbid, dry_run=True)
        db = DbAdmin(self.omerodir, None, argscheck, External(self.omerodir))
        assert db.check() == DB_INIT_NEEDED

        self.psqlc(None, '-d', self.dbid, '-f', self.omero531sql,
                   '-U', self.dbid, admin=False)
        assert db.check() == DB_UPGRADE_NEEDED

    def test_init(self):
        args = Args(self.dbid)
        DbAdmin(self.omerodir, 'init', args, External(self.omerodir))
        r = self.psqlc('SELECT currentversion, currentpatch FROM dbpatch '
                       'ORDER BY id DESC', '-d', self.dbid)
        assert r.splitlines() == [b'OMERO5.4|0']

        argscheck = Args(self.dbid, dry_run=True)
        db = DbAdmin(self.omerodir, None, argscheck, External(self.omerodir))
        assert db.check() == DB_UPTODATE

    def test_init_from_and_upgrade(self):
        args = Args(self.dbid, omerosql=self.omero531sql)
        DbAdmin(self.omerodir, 'init', args, External(self.omerodir))
        r = self.psqlc('SELECT currentversion, currentpatch FROM dbpatch '
                       'ORDER BY id ASC', '-d', self.dbid)
        assert r.splitlines() == [b'OMERO5.3|1', b'OMERO5.4|0']
        # Only the temporary omerosql file should be deleted
        assert os.path.exists(self.omero531sql)

        argscheck = Args(self.dbid, dry_run=True)
        db = DbAdmin(self.omerodir, None, argscheck, External(self.omerodir))
        assert db.check() == DB_UPTODATE
