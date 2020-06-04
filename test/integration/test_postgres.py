#!/usr/bin/env python
# -*- coding: utf-8 -*-

from argparse import Namespace
import os
from subprocess import check_output
from uuid import uuid4

from omero_database import (
    DB_INIT_NEEDED,
    DB_UPTODATE,
    DB_NO_CONNECTION,
)
from omero_server_setup import PgAdmin


DB_ADMIN_USER = os.getenv('POSTGRES_USER', 'postgres')
# Can be None if trust auth is setup
DB_ADMIN_PASSWORD = os.getenv("POSTGRES_PASSWORD", None)
DB_HOST, _, DB_PORT = os.getenv(
    'POSTGRES_HOST', 'localhost:5432').partition(':')


class Args(Namespace):
    def __init__(self, dbid, **kwargs):
        args = dict(
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
            adminpass=DB_ADMIN_PASSWORD,
        )
        args.update(kwargs)
        super().__init__(**args)


class TestPgAdmin(object):

    def setup_method(self, method):
        self.dbid = 'x' + str(uuid4()).replace('-', '')
        self.omerodir = os.getenv('OMERODIR')

    def teardown_method(self, method):
        self.psqlc("DROP DATABASE IF EXISTS {0};")
        self.psqlc("DROP ROLE IF EXISTS {0};")

    def psqlc(self, query, *args):
        env = os.environ.copy()
        cmd = ["psql"]
        if DB_HOST:
            cmd += ["-h", DB_HOST]
        if DB_PORT:
            cmd += ["-p", DB_PORT]
        cmd += ["-U", DB_ADMIN_USER]
        if DB_ADMIN_PASSWORD is not None:
            env["PGPASSWORD"] = DB_ADMIN_PASSWORD

        cmd += ["-At"] + list(args)
        if query:
            cmd += ["-c", query.format(self.dbid)]
        out = check_output(cmd, env=env)
        # print(cmd, out)
        return out

    def test_create(self):
        args = Args(self.dbid)

        pg = PgAdmin(self.omerodir, None, args)
        assert pg.check() == DB_NO_CONNECTION

        pg = PgAdmin(self.omerodir, 'create', args)
        assert pg.check() == DB_INIT_NEEDED

        user = self.psqlc("SELECT 1 FROM pg_roles WHERE rolname='{}';".format(
                          self.dbid))
        assert user.strip() == b'1'
        db = self.psqlc("SELECT 1 FROM pg_database WHERE datname='{}';".format(
                        self.dbid))
        assert db.strip() == b'1'

    def test_justdoit(self):
        args = Args(self.dbid)
        PgAdmin(self.omerodir, 'justdoit', args)
        r = self.psqlc('SELECT currentversion, currentpatch FROM dbpatch '
                       'ORDER BY id DESC', '-d', self.dbid)
        assert r.splitlines() == [b'OMERO5.4|0']

        argscheck = Args(self.dbid, dry_run=True)
        db = PgAdmin(self.omerodir, None, argscheck)
        assert db.check() == DB_UPTODATE
