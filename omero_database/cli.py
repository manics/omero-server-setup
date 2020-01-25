#!/usr/bin/env python

import logging
import os
from omero.cli import BaseControl
from .external import External
from .db import (
    DbAdmin,
    DB_INIT_NEEDED,
    DB_UPGRADE_NEEDED,
    DB_UPTODATE,
    Stop,
)

HELP = 'Manage the OMERO PostgreSQL database'
DEFAULT_LOGLEVEL = logging.WARNING


class DatabaseControl(BaseControl):

    def _configure(self, parser):
        parser.add_argument(
            '--dbhost', default='localhost',
            help="Hostname of the OMERO database server")
        # No default dbname to prevent inadvertent upgrading of databases
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
        # TODO Admin credentials: dbauser, dbapass

        parser.add_argument(
            '--verbose', '-v', action='count', default=0,
            help='Increae verbosity (can be used multiple times)')

        parser.add_argument(
            '-n', '--dry-run', action='store_true', help=(
                "Simulation/check mode. In 'upgrade' mode exits with code {} "
                "if an upgrade is required, {} if database isn't initialised, "
                "{} if database is up-to-date.".format(
                    DB_UPGRADE_NEEDED, DB_INIT_NEEDED, DB_UPTODATE)))

        sub = parser.sub()

        parser_init = parser.add(
            sub, self.init, 'Initialise a database')
        parser_init.add_argument(
            "--omerosql",
            help="OMERO database SQL initialisation file")
        parser_init.add_argument(
            '--rootpass', default='omero',
            help="OMERO admin password")
        parser_init.set_defaults(dbcommand='init')

        parser_upgrade = parser.add(
            sub, self.upgrade, 'Upgrade a database')
        parser_upgrade.set_defaults(dbcommand='upgrade')

        parser_dump = parser.add(
            sub, self.dump, 'Dump a database')
        parser_dump.add_argument('--dumpfile', help='Database dump file')
        parser_dump.set_defaults(dbcommand='dump')

    def init(self, args):
        return self.execute(args)

    def upgrade(self, args):
        return self.execute(args)

    def dump(self, args):
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
