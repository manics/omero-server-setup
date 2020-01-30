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
    DB_NO_CONNECTION,
    # Stop,
)
from omero_database.external import External


DB_ADMIN_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_HOST, _, DB_PORT = os.getenv(
    'POSTGRES_HOST', 'localhost:5432').partition(':')


class Args(object):
    def __init__(self, dbid, **kwargs):
        default_args = dict(
            dbcommand=None,
            # Ignore config.xml, use our test credentials
            no_db_config=True,
            dry_run=False,
            omerosql=None,
            rootpass='omero',
            dbname=dbid,
            dbport=DB_PORT,
            dbuser=dbid,
            dbhost=DB_HOST,
            dbpass=dbid,
            adminuser=DB_ADMIN_USER,
            adminpass=DB_ADMIN_USER,
        )

        for k, v in default_args.items():
            setattr(self, k, v)
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestDbAdmin(object):

    def setup_method(self, method):
        self.dbid = 'x' + str(uuid4()).replace('-', '')
        self.omerodir = os.getenv('OMERODIR')
        self.omero440sql = os.path.join(
            os.path.dirname(__file__), '..', 'resources', 'OMERO4.4__0.sql')

    def teardown_method(self, method):
        self.psqlc("DROP DATABASE IF EXISTS {0};")
        self.psqlc("DROP ROLE IF EXISTS {0};")

    def create_db(self):
        self.psqlc("CREATE USER {0} WITH PASSWORD '{0}';")
        self.psqlc("CREATE DATABASE {0} WITH OWNER {0};")

    def psqlc(self, query, *args, admin=True):
        cmd = ['psql']
        if DB_HOST:
            cmd += ['-h', DB_HOST]
        if DB_PORT:
            cmd += ['-p', DB_PORT]
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

        assert db.check() == DB_NO_CONNECTION

        self.create_db()
        assert db.check() == DB_INIT_NEEDED

        self.psqlc(None, '-d', self.dbid, '-f', self.omero440sql,
                   '-U', self.dbid, admin=False)
        assert db.check() == DB_UPGRADE_NEEDED

    def test_create(self):
        args = Args(self.dbid)
        db = DbAdmin(self.omerodir, 'create', args, External(self.omerodir))
        assert db.check() == DB_INIT_NEEDED

        user = self.psqlc("SELECT 1 FROM pg_roles WHERE rolname='{}';".format(
                          self.dbid))
        assert user.strip() == b'1'
        db = self.psqlc("SELECT 1 FROM pg_database WHERE datname='{}';".format(
                        self.dbid))
        assert db.strip() == b'1'

    def test_init(self):
        self.create_db()
        args = Args(self.dbid)
        DbAdmin(self.omerodir, 'init', args, External(self.omerodir))
        r = self.psqlc('SELECT currentversion, currentpatch FROM dbpatch '
                       'ORDER BY id DESC', '-d', self.dbid)
        assert r.splitlines() == [b'OMERO5.4|0']

        argscheck = Args(self.dbid, dry_run=True)
        db = DbAdmin(self.omerodir, None, argscheck, External(self.omerodir))
        assert db.check() == DB_UPTODATE

    def test_init_from_and_upgrade(self):
        self.create_db()
        args = Args(self.dbid, omerosql=self.omero440sql)
        DbAdmin(self.omerodir, 'init', args, External(self.omerodir))
        r = self.psqlc('SELECT currentversion, currentpatch FROM dbpatch '
                       'ORDER BY id ASC', '-d', self.dbid)
        assert r.splitlines() == [
            b'OMERO4.4|0',
            b'OMERO5.0|0',
            b'OMERO5.1|1',
            b'OMERO5.2|0',
            b'OMERO5.3|0',
            b'OMERO5.4|0',
        ]
        # Only the temporary omerosql file should be deleted
        assert os.path.exists(self.omero440sql)

        argscheck = Args(self.dbid, dry_run=True)
        db = DbAdmin(self.omerodir, None, argscheck, External(self.omerodir))
        assert db.check() == DB_UPTODATE

    def test_justdoit(self):
        args = Args(self.dbid)
        DbAdmin(self.omerodir, 'justdoit', args, External(self.omerodir))
        r = self.psqlc('SELECT currentversion, currentpatch FROM dbpatch '
                       'ORDER BY id DESC', '-d', self.dbid)
        assert r.splitlines() == [b'OMERO5.4|0']

        argscheck = Args(self.dbid, dry_run=True)
        db = DbAdmin(self.omerodir, None, argscheck, External(self.omerodir))
        assert db.check() == DB_UPTODATE

    def test_dump(self, tmpdir):
        dumpfile = str(tmpdir.join('test.pgdump'))
        self.create_db()
        args = Args(self.dbid, dumpfile=dumpfile)
        DbAdmin(self.omerodir, 'dump', args, External(self.omerodir))
        with open(dumpfile, 'rb') as f:
            assert f.read(5) == b'PGDMP'
