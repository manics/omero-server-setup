#!/usr/bin/env python

import logging
import os
from omero.cli import BaseControl
from .external import External
from .db import (
    DbAdmin,
    DB_INIT_NEEDED,
    DB_NO_CONNECTION,
    DB_UPGRADE_NEEDED,
    DB_UPTODATE,
    Stop,
)

DEFAULT_LOGLEVEL = logging.WARNING


class DatabaseControl(BaseControl):

    def _configure(self, parser):
        parser.add_argument(
            '--dbhost', default='localhost',
            help="Hostname of the OMERO database server")
        parser.add_argument(
            '--dbport', default='5432',
            help="Port of the OMERO database")
        parser.add_argument(
            '--dbname', default='omero',
            help="Name of the OMERO database")
        parser.add_argument(
            '--dbuser', default='omero',
            help="Username for connecting to the OMERO database")
        parser.add_argument(
            '--dbpass', default='omero',
            help="Password for connecting to the OMERO database")
        parser.add_argument(
            "--no-db-config", action="store_true",
            help="Ignore the database settings in omero config")

        parser.add_argument(
            '--verbose', '-v', action='count', default=0,
            help='Increae verbosity (can be used multiple times)')

        parser.add_argument(
            '-n', '--dry-run', action='store_true', help=(
                "Simulation/check mode. In 'upgrade' mode exits with code "
                "{}:upgrade required "
                "{}:database isn't initialised "
                "{}:unable to connect to database "
                "{}:database is up-to-date.".format(
                    DB_UPGRADE_NEEDED,
                    DB_INIT_NEEDED,
                    DB_NO_CONNECTION,
                    DB_UPTODATE)))

        sub = parser.sub()

        # parser.add uses the name of the second argument in the help text,
        # so it's not possible to use the same wrapper function

        parser_createconfig = parser.add(
            sub, self.createconfig,
            'Generate an OMERO database configuration file. '
            'Pass --manage-postgres to also also manage the PostgreSQL'
            'server.')
        parser_createconfig.add_argument(
            '--manage-postgres', action='store_true',
            help='Manage a local PostgreSQL server for OMERO only')
        parser_createconfig.add_argument(
            '--data-dir', help='OMERO data directory')
        parser_createconfig.set_defaults(dbcommand='createconfig')

        parser_justdoit = parser.add(
            sub, self.justdoit,
            'Create, initialise and/or upgrade a database if necessary')
        parser_justdoit.set_defaults(dbcommand='justdoit')

        parser_create = parser.add(
            sub, self.create,
            'Create a new PostgreSQL user and database if necessary')
        parser_create.set_defaults(dbcommand='create')

        parser_init = parser.add(
            sub, self.init, 'Initialise a database')

        parser_init.set_defaults(dbcommand='init')

        parser_upgrade = parser.add(
            sub, self.upgrade, 'Upgrade a database')
        parser_upgrade.set_defaults(dbcommand='upgrade')

        parser_upgrade = parser.add(
            sub, self.upgrade, 'Upgrade a database')
        parser_upgrade.set_defaults(dbcommand='upgrade')

        parser_dump = parser.add(
            sub, self.dump, 'Dump a database')
        parser_dump.add_argument('--dumpfile', help='Database dump file')
        parser_dump.set_defaults(dbcommand='dump')

        # Arguments common to multiple sub-parsers

        for subp in (parser_init, parser_justdoit):
            subp.add_argument(
                "--omerosql",
                help="OMERO database SQL initialisation file")
            subp.add_argument(
                '--rootpass', default='omero',
                help="OMERO admin password")

        for subp in (parser_create, parser_justdoit):
            subp.add_argument(
                '--adminuser',
                help="PostgreSQL admin username")
            subp.add_argument(
                '--adminpass',
                help="PostgreSQL admin password")

    def createconfig(self, args):
        return self.execute(args)

    def create(self, args):
        return self.execute(args)

    def init(self, args):
        return self.execute(args)

    def upgrade(self, args):
        return self.execute(args)

    def dump(self, args):
        return self.execute(args)

    def justdoit(self, args):
        return self.execute(args)

    def execute(self, args):

        loglevel = max(DEFAULT_LOGLEVEL - 10 * args.verbose, 10)
        logging.getLogger('omero_database').setLevel(level=loglevel)

        # Is this the same as self.dir?
        omerodir = os.getenv('OMERODIR')
        try:
            DbAdmin(omerodir, args.dbcommand, args, External(omerodir))
        except Stop as e:
            # client = self.ctx.conn(args)
            self.ctx.die(e.args[0], e.args[1])
            # self.ctx.set("last.upload.id", obj.id.val)
            # self.ctx.out("OriginalFile:%s" % obj_ids)


class PostgresControl(BaseControl):

    def _configure(self, parser):
        parser.add_argument(
            '--verbose', '-v', action='count', default=0,
            help='Increae verbosity (can be used multiple times)')

        sub = parser.sub()

        # parser.add uses the name of the second argument in the help text,
        # so it's not possible to use the same wrapper function

        parser_initdb = parser.add(
            sub, self.initdb,
            'Initialise a new local PostgreSQL server')
        parser_initdb.set_defaults(dbcommand='pg_initdb')

        parser_start = parser.add(
            sub, self.start,
            'Start a local PostgreSQL server')
        parser_start.set_defaults(dbcommand='pg_start')

        parser_stop = parser.add(
            sub, self.stop,
            'Stop a local PostgreSQL server')
        parser_stop.set_defaults(dbcommand='pg_stop')

        parser_restart = parser.add(
            sub, self.restart,
            'Restart a local PostgreSQL server')
        parser_restart.set_defaults(dbcommand='pg_restart')

    def initdb(self, args):
        return self.execute(args)

    def start(self, args):
        return self.execute(args)

    def stop(self, args):
        return self.execute(args)

    def restart(self, args):
        return self.execute(args)

    def execute(self, args):

        loglevel = max(DEFAULT_LOGLEVEL - 10 * args.verbose, 10)
        logging.getLogger('omero_database').setLevel(level=loglevel)

        # Is this the same as self.dir?
        omerodir = os.getenv('OMERODIR')
        try:
            DbAdmin(omerodir, args.dbcommand, args, External(omerodir))
        except Stop as e:
            self.ctx.die(e.args[0], e.args[1])
