#!/usr/bin/env python

from argparse import ArgumentParser
import logging
import os
from omero.cli import BaseControl
from .certificates import create_certificates
from .createconfig import CreateConfig
from .db import (
    DbAdmin,
    DB_INIT_NEEDED,
    DB_NO_CONNECTION,
    DB_UPGRADE_NEEDED,
    DB_UPTODATE,
    Stop,
)
from .external import External

DEFAULT_LOGLEVEL = logging.WARNING


def _omerodir():
    omerodir = os.getenv('OMERODIR')
    if not omerodir or not os.path.isdir(omerodir):
        raise Stop(100, 'OMERODIR not set')
    return omerodir


def _subparser(sub, name, func, parents, help, **kwargs):
    parser = sub.add_parser(
        name, parents=parents, help=help, description=help)
    parser.set_defaults(func=func, **kwargs)
    parser.set_defaults(command=name)
    return parser


class SetupControl(BaseControl):

    def _configure(self, parser):
        # Arguments common to multiple sub-parsers

        common_parser = ArgumentParser(add_help=False)
        common_parser.add_argument(
            '--verbose', '-v', action='count', default=0,
            help='Increase verbosity (can be used multiple times)')

        db_parser = ArgumentParser(add_help=False)
        db_parser.add_argument(
            '--dbhost', default=None,
            help="Hostname of the OMERO database server")
        db_parser.add_argument(
            '--dbport', default=None,
            help="Port of the OMERO database")
        db_parser.add_argument(
            '--dbname', default=None,
            help="Name of the OMERO database")
        db_parser.add_argument(
            '--dbuser', default=None,
            help="Username for connecting to the OMERO database")
        db_parser.add_argument(
            '--dbpass', default=None,
            help="Password for connecting to the OMERO database")
        db_parser.add_argument(
            "--no-db-config", action="store_true",
            help="Ignore the database settings in omero config")
        db_parser.add_argument(
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

        omerosql_parser = ArgumentParser(add_help=False)
        omerosql_parser.add_argument(
            "--omerosql", help="OMERO database SQL initialisation file")
        omerosql_parser.add_argument(
            '--rootpass', default='omero', help="OMERO admin password")

        pgadmin_parser = ArgumentParser(add_help=False)
        pgadmin_parser.add_argument(
            '--adminuser', help="PostgreSQL admin username")
        pgadmin_parser.add_argument(
            '--adminpass', help="PostgreSQL admin password")

        sub = parser.sub()

        parser_createconfig = _subparser(
            sub, 'createconfig', self.createconfig,
            [common_parser, db_parser, pgadmin_parser],
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
        parser_createconfig.add_argument(
            '--no-certificates', action='store_true',
            help='Disable self-signed certs, use anonymous DH instead')
        parser_createconfig.add_argument(
            '--no-websockets', action='store_true',
            help='Disable websockets and enable insecure connections')

        _subparser(
            sub, 'justdoit', self.execute,
            [common_parser, db_parser, omerosql_parser, pgadmin_parser],
            'Create, initialise and/or upgrade a database if necessary')

        _subparser(
            sub, 'create', self.execute,
            [common_parser, db_parser, pgadmin_parser],
            'Create a new PostgreSQL user and database if necessary')

        _subparser(
            sub, 'init', self.execute,
            [common_parser, db_parser, omerosql_parser],
            'Initialise a database')

        _subparser(
            sub, 'upgrade', self.execute, [common_parser, db_parser],
            'Upgrade a database')

        parser_dump = _subparser(
            sub, 'dump', self.execute, [common_parser, db_parser],
            'Dump a database')
        parser_dump.add_argument('--dumpfile', help='Database dump file')

        _subparser(
            sub, 'certificates', self.certificates, [common_parser],
            'Create and update self-signed server certificates')

        _subparser(
            sub, 'pginit', self.execute, [common_parser],
            'Initialise a new local PostgreSQL server')

        _subparser(
            sub, 'pgstart', self.execute, [common_parser],
            'Start a local PostgreSQL server')

        _subparser(
            sub, 'pgstop', self.execute, [common_parser],
            'Stop a local PostgreSQL server')

        _subparser(
            sub, 'start', self.omeroctl, [common_parser],
            'Start OMERO.server')

        _subparser(
            sub, 'stop', self.omeroctl, [common_parser],
            'Stop OMERO.server')

    def setup_logging(self, args):
        loglevel = max(DEFAULT_LOGLEVEL - 10 * args.verbose, 10)
        logging.getLogger('omero_server_setup').setLevel(level=loglevel)

    def createconfig(self, args):
        self.setup_logging(args)
        omerodir = _omerodir()
        try:
            c = CreateConfig(omerodir, args)
            created, changes = c.create_or_update_config()
            self.ctx.out('\n'.join(changes))
        except Stop as e:
            self.ctx.die(e.args[0], e.args[1])

    def certificates(self, args):
        self.setup_logging(args)
        omerodir = _omerodir()
        try:
            create_certificates(External(omerodir))
        except Stop as e:
            self.ctx.die(e.args[0], e.args[1])

    def execute(self, args):
        self.setup_logging(args)

        # Is this the same as self.dir?
        omerodir = _omerodir()
        try:
            DbAdmin(omerodir, args.command, args)
        except Stop as e:
            self.ctx.die(e.args[0], e.args[1])
            # self.ctx.set("last.upload.id", obj.id.val)
            # self.ctx.out("OriginalFile:%s" % obj_ids)

    def omeroctl(self, args):
        self.setup_logging(args)
        omerodir = _omerodir()
        cfg = CreateConfig(omerodir, args)
        if args.verbose:
            v = ' -' + ('v' * args.verbose)
        else:
            v = ''

        cmds = []
        if args.command == 'start':
            if cfg.certificates_enabled():
                cmds.append('setup certificates' + v)
            if cfg.postgres_enabled():
                cmds.append('setup pgstart' + v)
            cmds.append('setup justdoit' + v)
            cmds.append('admin start' + v)

        if args.command == 'stop':
            cmds.append('admin stop' + v)
            if cfg.postgres_enabled():
                cmds.append('setup pgstop' + v)

        for i, cmd in enumerate(cmds):
            self.ctx.invoke(cmd)
            if self.ctx.rv != 0:
                self.ctx.die(
                    self.ctx.rv, '**************************************\n'
                    'Error: {} exited with code {}\n'
                    'Try running these commands individually:\n  {}'.format(
                        cmd, self.ctx.rv, '\n  '.join(cmds[i:])))
