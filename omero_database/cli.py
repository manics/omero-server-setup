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


def _omerodir():
    omerodir = os.getenv('OMERODIR')
    if not omerodir or not os.path.isdir(omerodir):
        raise Stop(100, 'OMERODIR not set')
    return omerodir


def _add_db_arguments(parser):
    parser.add_argument(
        '--dbhost', default=None,
        help="Hostname of the OMERO database server")
    parser.add_argument(
        '--dbport', default=None,
        help="Port of the OMERO database")
    parser.add_argument(
        '--dbname', default=None,
        help="Name of the OMERO database")
    parser.add_argument(
        '--dbuser', default=None,
        help="Username for connecting to the OMERO database")
    parser.add_argument(
        '--dbpass', default=None,
        help="Password for connecting to the OMERO database")


def _subparser(sub, name, func, help, **kwargs):
    parser = sub.add_parser(
        name, help=help, description=help)
    parser.set_defaults(func=func, **kwargs)
    parser.set_defaults(command=name)
    return parser


class SetupControl(BaseControl):

    def _configure(self, parser):
        _add_db_arguments(parser)

        parser.add_argument(
            "--no-db-config", action="store_true",
            help="Ignore the database settings in omero config")

        parser.add_argument(
            '--verbose', '-v', action='count', default=0,
            help='Increase verbosity (can be used multiple times)')

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

        parser_createconfig = _subparser(
            sub, 'createconfig', self.execute,
            'Update the OMERO configuration file. See --help for options. '
            'This will NOT modify existing configuration keys. '
            'To create a clean configuration first delete etc/grid/config.xml '
            'from your OMERO.server directory.')
        parser_createconfig.add_argument(
            '--manage-postgres', action='store_true',
            help='Manage a local PostgreSQL server for OMERO only')
        parser_createconfig.add_argument(
            '--data-dir', default=None, help=(
                'OMERO data directory, use "auto" to use $CONDA_PREFIX/OMERO '
                'when running in Conda, $HOME/OMERO if not'))

        parser_justdoit = _subparser(
            sub, 'justdoit', self.execute,
            'Create, initialise and/or upgrade a database if necessary')

        parser_create = _subparser(
            sub, 'create', self.execute,
            'Create a new PostgreSQL user and database if necessary')

        parser_init = _subparser(
            sub, 'init', self.execute, 'Initialise a database')

        _subparser(
            sub, 'upgrade', self.execute, 'Upgrade a database')

        parser_dump = _subparser(
            sub, 'dump', self.execute, 'Dump a database')
        parser_dump.add_argument('--dumpfile', help='Database dump file')

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

        _subparser(
            sub, 'pginit', self.execute,
            'Initialise a new local PostgreSQL server')

        _subparser(
            sub, 'pgstart', self.execute,
            'Start a local PostgreSQL server')

        _subparser(
            sub, 'pgstop', self.execute,
            'Stop a local PostgreSQL server')

        _subparser(
            sub, 'pgrestart', self.execute,
            'Restart a local PostgreSQL server')

    def execute(self, args):

        loglevel = max(DEFAULT_LOGLEVEL - 10 * args.verbose, 10)
        logging.getLogger('omero_database').setLevel(level=loglevel)

        # Is this the same as self.dir?
        omerodir = _omerodir()
        try:
            DbAdmin(omerodir, args.command, args, External(omerodir))
        except Stop as e:
            # client = self.ctx.conn(args)
            self.ctx.die(e.args[0], e.args[1])
            # self.ctx.set("last.upload.id", obj.id.val)
            # self.ctx.out("OriginalFile:%s" % obj_ids)
