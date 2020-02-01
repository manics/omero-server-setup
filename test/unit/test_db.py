#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2014 University of Dundee & Open Microscopy Environment
# All Rights Reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import pytest
from mox3 import mox

from argparse import Namespace
import os
import re

from omero_server_setup import external
import omero_server_setup.db
from omero_server_setup.db import (
    DbAdmin,
    is_schema,
    sort_schemas,
    parse_schema_files,
    Stop,
    timestamp_filename,
)


@pytest.mark.parametrize('version,expected', [
    ('OMERO3__0', True), ('OMERO3A__10', True), ('OMERO4.4__0', True),
    ('OMERO5.1DEV__2', True), ('OMERO5.1DEV__10', True),
    ('OMERO100.100__100', True), ('OMERO-precheck.sql', False),
    ('OMERO5.2__precheck.sql', False)])
def test_is_schema(version, expected):
    assert is_schema(version) == expected


def test_sort_schemas():
    ordered = ['OMERO3__0', 'OMERO3A__10', 'OMERO4__0', 'OMERO4.4__0',
               'OMERO5.0__0', 'OMERO5.1DEV__0', 'OMERO5.1DEV__1',
               'OMERO5.1DEV__2', 'OMERO5.1DEV__10',
               'OMERO5.1__0']

    ps = [5, 3, 7, 9, 2, 6, 0, 1, 8, 4]
    permuted = [ordered[p] for p in ps]

    assert sort_schemas(permuted) == ordered


def test_parse_schema_files():
    files = [
        # Parsed schema files
        'psql/OMERO5.2__0/OMERO5.1__0.sql',
        'OMERO5.2__0/OMERO5.1__0.sql',
        'OMERO5.3DEV__3/OMERO5.2__0.sql',
        'OMERO5.3DEV__3/OMERO5.3DEV__2.sql',
        # Unparsed schema files
        'OMERO5.2__0/OMERO5.1__0.txt',
        'OMERO4.2__0/omero-4.1-all-public.sql',
        'OMERO5.2__0/data.sql',
        'OMERO5.2__0/OMERO5.1-precheck.sql',
        'OMERO5.2__0/OMERO5.1__precheck.sql',
        'OMERO5.2/OMERO5.1__0.sql',
        ]
    d = {}
    d['psql/OMERO5.2__0/OMERO5.1__0.sql'] = ('OMERO5.1__0', 'OMERO5.2__0')
    d['OMERO5.2__0/OMERO5.1__0.sql'] = ('OMERO5.1__0', 'OMERO5.2__0')
    d['OMERO5.3DEV__3/OMERO5.2__0.sql'] = ('OMERO5.2__0', 'OMERO5.3DEV__3')
    d['OMERO5.3DEV__3/OMERO5.3DEV__2.sql'] = (
        'OMERO5.3DEV__2', 'OMERO5.3DEV__3')

    assert parse_schema_files(files) == d


class TestDb(object):

    class Args(Namespace):
        def __init__(self, args):
            super().__init__(**args)

    class PartialMockDb(DbAdmin):

        def __init__(self, args, ext):
            self.args = args
            self.external = ext
            self.dir = '.'

    def setup_method(self, method):
        self.mox = mox.Mox()

    def teardown_method(self, method):
        self.mox.UnsetStubs()

    @pytest.mark.parametrize('ext', [True, False])
    def test_timestamp_filename(self, ext):
        if ext:
            s = timestamp_filename('name', 'test')
            assert re.match(r'^name-\d{8}-\d{6}-\d{6}\.test$', s)
        else:
            s = timestamp_filename('name')
            assert re.match(r'^name-\d{8}-\d{6}-\d{6}$', s)

    @pytest.mark.parametrize('connected', [True, False])
    def test_check_connection(self, connected):
        db = self.PartialMockDb(None, None)
        self.mox.StubOutWithMock(db, 'psql')

        if connected:
            db.psql('-c', r'\conninfo')
        else:
            db.psql('-c', r'\conninfo').AndRaise(
                external.RunException('', '', [], 1, '', ''))
        self.mox.ReplayAll()

        if connected:
            db.check_connection()
        else:
            with pytest.raises(Stop) as excinfo:
                db.check_connection()
            assert excinfo.value.msg == 'Database connection check failed'

        self.mox.VerifyAll()

    @pytest.mark.parametrize('sqlfile', ['exists', 'missing', 'notprovided'])
    @pytest.mark.parametrize('dryrun', [True, False])
    def test_init(self, sqlfile, dryrun):
        ext = self.mox.CreateMock(external.External)
        if sqlfile != 'notprovided':
            omerosql = 'omero.sql'
        else:
            omerosql = None
        args = self.Args({'omerosql': omerosql, 'rootpass': 'rootpass',
                          'dry_run': dryrun})
        db = self.PartialMockDb(args, ext)
        self.mox.StubOutWithMock(db, 'psql')
        self.mox.StubOutWithMock(omero_server_setup.db, 'timestamp_filename')
        self.mox.StubOutWithMock(os.path, 'exists')
        self.mox.StubOutWithMock(db, 'check_connection')
        self.mox.StubOutWithMock(db, 'upgrade')
        self.mox.StubOutWithMock(os, 'remove')

        db.check_connection()
        if sqlfile == 'notprovided':
            omerosql = 'omero-00000000-000000-000000.sql'
            omero_server_setup.db.timestamp_filename('omero', 'sql').AndReturn(
                omerosql)
        else:
            os.path.exists(omerosql).AndReturn(sqlfile == 'exists')

        if sqlfile == 'notprovided' and not dryrun:
            ext.omero_cli([
                'db', 'script', '-f', omerosql, '', '', args.rootpass])

        if sqlfile == 'exists':
            db.upgrade()

        if sqlfile != 'missing' and not dryrun:
            db.psql('-f', omerosql)

        if sqlfile == 'notprovided' and not dryrun:
            os.remove('omero-00000000-000000-000000.sql')

        self.mox.ReplayAll()

        if sqlfile == 'missing':
            with pytest.raises(Stop) as excinfo:
                db.init()
            assert excinfo.value.msg == 'SQL file not found'
        else:
            db.init()
        self.mox.VerifyAll()

    def test_sql_version_matrix(self):
        self.mox.StubOutWithMock(omero_server_setup.db, 'glob')
        omero_server_setup.db.glob(
            os.path.join('.', 'sql', 'psql', 'OMERO*', 'OMERO*.sql')
            ).AndReturn(['./sql/psql/OMERO5.0__0/OMERO4.4__0.sql',
                         './sql/psql/OMERO5.1__0/OMERO5.0__0.sql'])
        self.mox.ReplayAll()

        db = self.PartialMockDb(None, None)
        M, versions = db.sql_version_matrix()
        assert versions == ['OMERO4.4__0', 'OMERO5.0__0', 'OMERO5.1__0']
        assert M == [[None, './sql/psql/OMERO5.0__0/OMERO4.4__0.sql', None],
                     [None, None, './sql/psql/OMERO5.1__0/OMERO5.0__0.sql'],
                     [None, None, None]]
        self.mox.VerifyAll()

    @pytest.mark.parametrize('vfrom', ['', '', ''])
    def test_sql_version_resolve(self, vfrom):
        db = self.PartialMockDb(None, None)

        versions = ['3.0', '4.0', '4.4', '5.0', '5.1']
        M = [[None, '4.0/3.0', '4.4/3.0', None, None],
             [None, None, '4.4/4.0', '5.0/4.0', None],
             [None, None, None, '5.0/4.4', None],
             [None, None, None, None, '5.1/5.0'],
             [None, None, None, None, None]]

        assert db.sql_version_resolve(M, versions, '5.0') == ['5.1/5.0']
        assert db.sql_version_resolve(M, versions, '4.0') == [
            '5.0/4.0', '5.1/5.0']
        assert db.sql_version_resolve(M, versions, '3.0') == [
            '4.4/3.0', '5.0/4.4', '5.1/5.0']

        self.mox.VerifyAll()

    @pytest.mark.parametrize('userexists,dbexists', [
        (True, True),
        (True, False),
        (False, False),
    ])
    def test_create(self, userexists, dbexists):
        args = self.Args({'dry_run': False})
        db = self.PartialMockDb(args, None)
        self.mox.StubOutWithMock(db, 'get_db_args_env')
        self.mox.StubOutWithMock(db, 'psql')
        db.get_db_args_env().AndReturn(self.create_db_test_params())

        db.psql('-c', "SELECT 1 FROM pg_roles WHERE rolname='user';",
                admin=True).AndReturn('1\n' if userexists else '')
        if not userexists:
            db.psql('-c', "CREATE USER user WITH PASSWORD 'pass';",
                    admin=True)

        db.psql('-c', "SELECT 1 FROM pg_database WHERE datname='name';",
                admin=True).AndReturn('1\n' if dbexists else '')
        if not dbexists:
            db.psql('-c', "CREATE DATABASE name WITH OWNER user;",
                    admin=True)

        db.psql('-c', r'\conninfo')

        self.mox.ReplayAll()

        db.create()
        self.mox.VerifyAll()

    @pytest.mark.parametrize('needupdate', [True, False])
    def test_upgrade(self, needupdate):
        args = self.Args({'dry_run': False})
        db = self.PartialMockDb(args, None)
        self.mox.StubOutWithMock(db, 'get_current_db_version')
        self.mox.StubOutWithMock(db, 'sql_version_matrix')
        self.mox.StubOutWithMock(db, 'sql_version_resolve')
        self.mox.StubOutWithMock(db, 'check_connection')
        self.mox.StubOutWithMock(db, 'psql')

        db.check_connection()

        versions = ['OMERO3.0__0', 'OMERO4.4__0', 'OMERO5.0__0']
        if needupdate:
            db.get_current_db_version().AndReturn(('OMERO3.0', '0'))
            db.sql_version_matrix().AndReturn(([], versions))
            db.sql_version_resolve([], versions, versions[0]).AndReturn(
                ['./sql/psql/OMERO4.4__0/OMERO3.0__0.sql',
                 './sql/psql/OMERO5.0__0/OMERO4.4__0.sql'])
            db.psql('-f', './sql/psql/OMERO4.4__0/OMERO3.0__0.sql')
            db.psql('-f', './sql/psql/OMERO5.0__0/OMERO4.4__0.sql')
        else:
            db.get_current_db_version().AndReturn(('OMERO5.0', '0'))
            db.sql_version_matrix().AndReturn(([], versions))

        self.mox.ReplayAll()

        db.upgrade()
        self.mox.VerifyAll()

    @pytest.mark.parametrize('needupdate', [True, False])
    def test_upgrade_dryrun(self, needupdate):
        args = self.Args({'dry_run': True})
        db = self.PartialMockDb(args, None)
        self.mox.StubOutWithMock(db, 'get_current_db_version')
        self.mox.StubOutWithMock(db, 'sql_version_matrix')
        self.mox.StubOutWithMock(db, 'sql_version_resolve')
        self.mox.StubOutWithMock(db, 'check_connection')
        # Stub out to ensure it's NOT called
        self.mox.StubOutWithMock(db, 'psql')

        db.check_connection()

        versions = ['OMERO4.4__0', 'OMERO5.0__0']
        if needupdate:
            db.get_current_db_version().AndReturn(('OMERO4.4', '0'))
            db.sql_version_matrix().AndReturn(([], versions))
            db.sql_version_resolve([], versions, versions[0]).AndReturn(
                ['./sql/psql/OMERO5.0__0/OMERO4.4__0.sql'])
        else:
            db.get_current_db_version().AndReturn(('OMERO5.0', '0'))
            db.sql_version_matrix().AndReturn(([], versions))

        self.mox.ReplayAll()

        if needupdate:
            with pytest.raises(Stop) as excinfo:
                db.upgrade()
            assert excinfo.value.rc == 2
            assert excinfo.value.msg == (
                'Database upgrade required OMERO4.4__0->OMERO5.0__0')
        else:
            db.upgrade()
        self.mox.VerifyAll()

    @pytest.mark.parametrize('dryrun', [True, False])
    def test_upgrade_not_initialised(self, dryrun):
        args = self.Args({'dry_run': dryrun})
        db = self.PartialMockDb(args, None)
        self.mox.StubOutWithMock(db, 'get_current_db_version')
        self.mox.StubOutWithMock(db, 'check_connection')

        db.check_connection()
        exc = external.RunException(
            'test psql failure', 'psql', [], -1, '', '')
        db.get_current_db_version().AndRaise(exc)

        self.mox.ReplayAll()

        with pytest.raises(Stop) as excinfo:
            db.upgrade()
        assert excinfo.value.rc == 3
        assert excinfo.value.msg == 'Unable to get database version'
        self.mox.VerifyAll()

    def test_get_current_db_version(self):
        db = self.PartialMockDb(None, None)
        self.mox.StubOutWithMock(db, 'psql')

        db.psql('-c', 'SELECT currentversion, currentpatch FROM dbpatch '
                'ORDER BY id DESC LIMIT 1').AndReturn('OMERO4.4|0')
        self.mox.ReplayAll()

        assert db.get_current_db_version() == ('OMERO4.4', '0')
        self.mox.VerifyAll()

    @pytest.mark.parametrize('dumpfile', ['test.pgdump', None])
    @pytest.mark.parametrize('dryrun', [True, False])
    def test_dump(self, dumpfile, dryrun):
        args = self.Args({'dry_run': dryrun, 'dumpfile': dumpfile})
        db = self.PartialMockDb(args, None)
        self.mox.StubOutWithMock(omero_server_setup.db, 'timestamp_filename')
        self.mox.StubOutWithMock(db, 'get_db_args_env')
        self.mox.StubOutWithMock(db, 'pgdump')
        self.mox.StubOutWithMock(db, 'check_connection')

        db.check_connection()
        if not dumpfile:
            db.get_db_args_env().AndReturn(self.create_db_test_params())

            dumpfile = 'omero-database-name-00000000-000000-000000.pgdump'
            omero_server_setup.db.timestamp_filename(
                'omero-database-name', 'pgdump').AndReturn(dumpfile)

        if not dryrun:
            db.pgdump('-Fc', '-f', dumpfile).AndReturn('')

        self.mox.ReplayAll()

        db.dump()
        self.mox.VerifyAll()

    def create_db_test_params(self, prefix=''):
        db = {
            'name': '%sname' % prefix,
            'host': '%shost' % prefix,
            'port': str(5432 + sum(prefix.encode())),
            'user': '%suser' % prefix,
            'pass': '%spass' % prefix,
        }
        env = {'PGPASSWORD': '%spass' % prefix}
        return db, env

    @pytest.mark.parametrize('dbname', ['name', ''])
    @pytest.mark.parametrize('hasconfig', [True, False])
    @pytest.mark.parametrize('noconfig', [True, False])
    def test_get_db_args_env(self, dbname, hasconfig, noconfig):
        ext = self.mox.CreateMock(external.External)
        args = self.Args({
            'dbhost': 'host',
            'dbport': '5432',
            'dbname': dbname,
            'dbuser': 'user',
            'dbpass': 'pass',
            'no_db_config': noconfig
        })
        db = self.PartialMockDb(args, ext)
        self.mox.StubOutWithMock(db.external, 'get_config')
        self.mox.StubOutWithMock(os.environ, 'copy')

        if noconfig or not hasconfig:
            expecteddb, expectedenv = self.create_db_test_params()
        else:
            expecteddb, expectedenv = self.create_db_test_params('ext')

        if not noconfig:
            cfg = {}
            if hasconfig:
                cfg = {
                    'omero.db.host': 'exthost',
                    'omero.db.port': '5769',
                    'omero.db.user': 'extuser',
                    'omero.db.pass': 'extpass',
                }
                if dbname:
                    cfg['omero.db.name'] = 'extname'

                db.external.get_config().AndReturn(cfg)
            else:
                db.external.get_config().AndRaise(Exception())

        os.environ.copy().AndReturn({'PGPASSWORD': 'incorrect'})

        self.mox.ReplayAll()
        if dbname:
            rcfg, renv = db.get_db_args_env()
            assert rcfg == expecteddb
            assert renv == expectedenv
        else:
            with pytest.raises(Exception) as excinfo:
                db.get_db_args_env()
            assert str(excinfo.value) == 'Database name required'

    def test_psql(self):
        db = self.PartialMockDb(None, None)
        self.mox.StubOutWithMock(db, 'get_db_args_env')
        self.mox.StubOutWithMock(omero_server_setup.db, 'run')

        psqlargs = [
            '-v', 'ON_ERROR_STOP=on',
            '-w', '-A', '-t',
            '-h', 'host',
            '-p', '5432',
            '-U', 'user',
            '-d', 'name',
            'arg1', 'arg2']
        db.get_db_args_env(admin=False).AndReturn(self.create_db_test_params())
        omero_server_setup.db.run(
            'psql', psqlargs, capturestd=True,
            env={'PGPASSWORD': 'pass'}).AndReturn((b'', b''))
        self.mox.ReplayAll()

        db.psql('arg1', 'arg2')
        self.mox.VerifyAll()

    def test_pgdump(self):
        db = self.PartialMockDb(None, None)
        self.mox.StubOutWithMock(db, 'get_db_args_env')
        self.mox.StubOutWithMock(omero_server_setup.db, 'run')

        pgdumpargs = ['-d', 'name', '-h', 'host', '-U', 'user',
                      '-w', 'arg1', 'arg2']
        db.get_db_args_env().AndReturn(self.create_db_test_params())
        omero_server_setup.db.run(
            'pg_dump', pgdumpargs, capturestd=True,
            env={'PGPASSWORD': 'pass'}).AndReturn((b'', b''))
        self.mox.ReplayAll()

        db.pgdump('arg1', 'arg2')
        self.mox.VerifyAll()
