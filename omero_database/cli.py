#!/usr/bin/env python

from argparse import ArgumentParser
import logging
import os
from omero.cli import BaseControl
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
    omerodir = os.getenv("OMERODIR")
    if not omerodir or not os.path.isdir(omerodir):
        raise Stop(100, "OMERODIR not set")
    return omerodir


def _subparser(sub, name, func, parents, help, **kwargs):
    parser = sub.add_parser(name, parents=parents, help=help, description=help)
    parser.set_defaults(func=func, **kwargs)
    parser.set_defaults(command=name)
    return parser


class DatabaseControl(BaseControl):
    def _configure(self, parser):
        # Arguments common to multiple sub-parsers

        common_parser = ArgumentParser(add_help=False)
        common_parser.add_argument(
            "--verbose",
            "-v",
            action="count",
            default=0,
            help="Increase verbosity (can be used multiple times)",
        )

        db_parser = ArgumentParser(add_help=False)
        db_parser.add_argument(
            "--dbhost",
            default=None,
            help="Hostname of the OMERO database server",
        )
        db_parser.add_argument(
            "--dbport", default=None, help="Port of the OMERO database"
        )
        db_parser.add_argument(
            "--dbname", default=None, help="Name of the OMERO database"
        )
        db_parser.add_argument(
            "--dbuser",
            default=None,
            help="Username for connecting to the OMERO database",
        )
        db_parser.add_argument(
            "--dbpass",
            default=None,
            help="Password for connecting to the OMERO database",
        )
        db_parser.add_argument(
            "--no-db-config",
            action="store_true",
            help="Ignore the database settings in omero config",
        )
        db_parser.add_argument(
            "-n",
            "--dry-run",
            action="store_true",
            help=(
                "Simulation/check mode. In 'upgrade' mode exits with code "
                "{}:upgrade required "
                "{}:database isn't initialised "
                "{}:unable to connect to database "
                "{}:database is up-to-date.".format(
                    DB_UPGRADE_NEEDED,
                    DB_INIT_NEEDED,
                    DB_NO_CONNECTION,
                    DB_UPTODATE,
                )
            ),
        )

        omerosql_parser = ArgumentParser(add_help=False)
        omerosql_parser.add_argument(
            "--omerosql", help="OMERO database SQL initialisation file"
        )
        omerosql_parser.add_argument(
            "--rootpass", default="omero", help="OMERO admin password"
        )

        sub = parser.sub()

        _subparser(
            sub,
            "justdoit",
            self.execute,
            [common_parser, db_parser, omerosql_parser],
            "Initialise and/or upgrade a database if necessary",
        )

        _subparser(
            sub,
            "init",
            self.execute,
            [common_parser, db_parser, omerosql_parser],
            "Initialise an OMERO database",
        )

        _subparser(
            sub,
            "upgrade",
            self.execute,
            [common_parser, db_parser],
            "Upgrade an OMERO database",
        )

        parser_dump = _subparser(
            sub,
            "dump",
            self.execute,
            [common_parser, db_parser],
            "Dump an OMERO database",
        )
        parser_dump.add_argument("--dumpfile", help="Database dump file")

    def setup_logging(self, args):
        loglevel = max(DEFAULT_LOGLEVEL - 10 * args.verbose, 10)
        logging.getLogger("omero_database").setLevel(level=loglevel)

    def execute(self, args):
        self.setup_logging(args)

        # Is this the same as self.dir?
        omerodir = _omerodir()
        try:
            DbAdmin(omerodir, args.command, args)
        except Stop as e:
            self.ctx.die(e.args[0], e.args[1])
