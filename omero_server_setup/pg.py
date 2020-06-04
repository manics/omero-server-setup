#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging

from omero_database import Stop, DbAdmin, DB_NO_CONNECTION
from omero_database.external import run, RunException

log = logging.getLogger(__name__)

HELP = """Manage an OMERO PostgreSQL server"""


class PgAdmin(DbAdmin):
    def __init__(self, omerodir, command, args):
        super().__init__(omerodir, None, args)
        if command in ("create", "justdoit", "pginit", "pgstart", "pgstop",):
            getattr(self, command)()
        elif command is not None:
            raise Stop(10, "Invalid pg command: %s" % command)

    def choose_omero_data_home(self):
        # if os.path.exists('/OMERO'):
        #     return '/OMERO'
        parent = os.getenv("CONDA_PREFIX", os.getenv("HOME"))
        if not parent:
            raise Exception(
                "Unable to determine omero.data.dir. Pass --data-dir."
            )
        return os.path.join(parent, "OMERO")

    def justdoit(self):
        """
        Attempt to do everything necessary to ensure the database is created
        and up-to-date
        """
        status = self.upgrade(check=True)
        if status in (DB_NO_CONNECTION,):
            self.create()
        super().justdoit()

    def create(self):
        db, env = self.get_db_args_env()
        admindb, adminenv = self.get_db_overrides()
        overrides = {
            "dboverrides": admindb,
            "envoverrides": adminenv,
        }

        userexists = self.psql(
            "-c",
            "SELECT 1 FROM pg_roles WHERE rolname='{}';".format(db["user"]),
            **overrides,
        )
        if userexists.strip() == "1":
            log.info("Database user exists: %s", db["user"])
        else:
            log.info("Creating database user: %s", db["user"])
            if not self.args.dry_run:
                self.psql(
                    "-c",
                    "CREATE USER {} WITH PASSWORD '{}';".format(
                        db["user"], db["pass"]
                    ),
                    **overrides,
                )

        dbexists = self.psql(
            "-c",
            "SELECT 1 FROM pg_database WHERE datname='{}';".format(db["name"]),
            **overrides,
        )
        if dbexists.strip() == "1":
            log.info("Database exists: %s", db["name"])
        else:
            log.info("Creating database: %s", db["name"])
            if not self.args.dry_run:
                self.psql(
                    "-c",
                    "CREATE DATABASE {} WITH OWNER {};".format(
                        db["name"], db["user"]
                    ),
                    **overrides,
                )

        if not self.args.dry_run:
            self.check_connection()

    def get_config_with_defaults(self):
        if self.args.no_db_config:
            cfgmap = {}
        else:
            try:
                cfgmap = self.external.get_config()
            except Exception as e:
                log.warning("config.xml not found: %s", e)
                cfgmap = {}
        created = {}

        def update_value(cfgkey, argname, default=None):
            if cfgkey in cfgmap:
                created[cfgkey] = cfgmap[cfgkey]
            elif (
                argname in self.args
                and getattr(self.args, argname) is not None
            ):
                created[cfgkey] = getattr(self.args, argname)
            elif default is None:
                raise Exception("No configuration value for {}".format(cfgkey))
            else:
                created[cfgkey] = default
            log.debug("%s=%s", cfgkey, created[cfgkey])

        update_value("omero.db.name", "dbname", "omero")
        update_value("omero.db.host", "dbhost", "localhost")
        update_value("omero.db.port", "dbport", "5432")
        update_value("omero.db.user", "dbuser", "omero")
        update_value("omero.db.pass", "dbpass", "omero")
        update_value("postgres.admin.user", "adminuser", "postgres")

        return created

    # def get_db_args_env(self):
    def get_db_overrides(self):
        """
        Get a dictionary of database connection parameters, and create an
        environment for running postgres commands.
        """
        cfg = self.get_config_with_defaults()
        db = {}
        env = {}
        db["user"] = cfg["postgres.admin.user"]
        db["name"] = "postgres"
        if self.args.adminpass:
            db["pass"] = self.args.adminpass
            env["PGPASSWORD"] = self.args.adminpass
        return db, env

    # PostgreSQL management

    def get_and_check_config(self):
        cfgmap = self.external.get_config()
        for required in (
            "postgres.data.dir",
            "omero.db.name",
            "omero.db.host",
            "omero.db.port",
            "omero.db.user",
            "omero.db.pass",
        ):
            if required not in cfgmap or not cfgmap[required]:
                raise Exception("Property {} required".format(required))
        return cfgmap

    def pginit(self):
        self.pg_ctl(
            "initdb", "-o", "--encoding=UTF-8", "-o", "--username=postgres",
        )

    def pgstart(self):
        cfg = self.get_and_check_config()
        if self.pgisrunning():
            log.info("PostgreSQL server already running, restarting")
            cmd = "restart"
        else:
            log.info("Starting PostgreSQL server")
            cmd = "start"
        logfile = os.path.join(cfg["postgres.data.dir"], "postgres.log")
        self.pg_ctl(
            cmd,
            "--log={}".format(logfile),
            "-o",
            "-p {}".format(cfg["omero.db.port"]),
        )

    def pgstop(self):
        if not self.pgisrunning():
            log.info("PostgreSQL server already stopped")
        else:
            log.info("Stopping PostgreSQL server")
            self.pg_ctl("stop")

    def pg_ctl(self, *args, capturestd=False, stop_error=True):
        cfg = self.get_and_check_config()
        pgdata = "--pgdata={}".format(cfg["postgres.data.dir"])
        try:
            stdout, stderr = run(
                "pg_ctl", [pgdata] + list(args), capturestd=capturestd
            )
        except RunException as e:
            if stop_error:
                log.fatal(e)
                raise Stop(e.r, "Failed to run pg_ctl {}".format(args))
            else:
                raise
        if capturestd:
            if stderr:
                log.warning("stderr: %s", stderr)
            log.debug("stdout: %s", stdout)
            return stdout.decode()

    def pgisrunning(self):
        # Exit code: 0=>running, 3=>not running
        try:
            self.pg_ctl("status", capturestd=True, stop_error=False)
            return True
        except RunException as e:
            if e.r == 3:
                return False
            else:
                raise
