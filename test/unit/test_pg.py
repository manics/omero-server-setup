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

from omero_database import external
from omero_server_setup.pg import PgAdmin


class TestDb(object):
    class Args(Namespace):
        def __init__(self, args):
            super().__init__(**args)

    class PartialMockPg(PgAdmin):
        def __init__(self, args, ext):
            self.args = args
            self.external = ext
            self.dir = "."

    def setup_method(self, method):
        self.mox = mox.Mox()

    def teardown_method(self, method):
        self.mox.UnsetStubs()

    @pytest.mark.parametrize(
        "userexists,dbexists", [(True, True), (True, False), (False, False)]
    )
    def test_create(self, userexists, dbexists):
        args = self.Args({"dry_run": False})
        pg = self.PartialMockPg(args, None)
        self.mox.StubOutWithMock(pg, "get_db_args_env")
        self.mox.StubOutWithMock(pg, "get_db_overrides")
        self.mox.StubOutWithMock(pg, "psql")
        pg.get_db_args_env().AndReturn(self.create_pg_test_params())
        dboverrides, envoverrides = self.create_pg_test_param_overrides()
        pg.get_db_overrides().AndReturn((dboverrides, envoverrides))

        pg.psql(
            "-c",
            "SELECT 1 FROM pg_roles WHERE rolname='user';",
            dboverrides=dboverrides,
            envoverrides=envoverrides,
        ).AndReturn("1\n" if userexists else "")
        if not userexists:
            pg.psql(
                "-c",
                "CREATE USER user WITH PASSWORD 'pass';",
                dboverrides=dboverrides,
                envoverrides=envoverrides,
            )

        pg.psql(
            "-c",
            "SELECT 1 FROM pg_database WHERE datname='name';",
            dboverrides=dboverrides,
            envoverrides=envoverrides,
        ).AndReturn("1\n" if dbexists else "")
        if not dbexists:
            pg.psql(
                "-c",
                "CREATE DATABASE name WITH OWNER user;",
                dboverrides=dboverrides,
                envoverrides=envoverrides,
            )

        pg.psql("-c", r"\conninfo")

        self.mox.ReplayAll()

        pg.create()
        self.mox.VerifyAll()

    def create_pg_test_params(self, prefix=""):
        db = {
            "name": "%sname" % prefix,
            "host": "%shost" % prefix,
            "port": str(5432 + sum(prefix.encode())),
            "user": "%suser" % prefix,
            "pass": "%spass" % prefix,
        }
        env = {"PGPASSWORD": "%spass" % prefix}
        return db, env

    def create_pg_test_param_overrides(self):
        return (
            {"user": "adminuser", "pass": "adminpass"},
            {"PGPASSWORD": "adminpass"},
        )

    @pytest.mark.parametrize("dbname", ["name", ""])
    @pytest.mark.parametrize("hasconfig", [True, False])
    @pytest.mark.parametrize("noconfig", [True, False])
    def test_get_db_args_env(self, dbname, hasconfig, noconfig):
        ext = self.mox.CreateMock(external.External)
        args = self.Args(
            {
                "dbhost": "host",
                "dbport": "5432",
                "dbname": dbname,
                "dbuser": "user",
                "dbpass": "pass",
                "adminuser": "adminuser",
                "adminpass": "adminpass",
                "no_db_config": noconfig,
            }
        )
        pg = self.PartialMockPg(args, ext)
        self.mox.StubOutWithMock(pg.external, "get_config")
        self.mox.StubOutWithMock(os.environ, "copy")

        if noconfig or not hasconfig:
            expecteddb, expectedenv = self.create_pg_test_params()
        else:
            expecteddb, expectedenv = self.create_pg_test_params("ext")

        if not noconfig:
            cfg = {}
            if hasconfig:
                cfg = {
                    "omero.db.host": "exthost",
                    "omero.db.port": "5769",
                    "omero.db.user": "extuser",
                    "omero.db.pass": "extpass",
                }
                if dbname:
                    cfg["omero.db.name"] = "extname"

                pg.external.get_config().AndReturn(cfg)
            else:
                pg.external.get_config().AndRaise(Exception())

        os.environ.copy().AndReturn({"PGPASSWORD": "incorrect"})

        self.mox.ReplayAll()
        if dbname:
            rcfg, renv = pg.get_db_args_env()
            assert rcfg == expecteddb
            assert renv == expectedenv
        else:
            with pytest.raises(Exception) as excinfo:
                pg.get_db_args_env()
            assert str(excinfo.value) == "Database name required"
