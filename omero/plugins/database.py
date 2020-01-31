#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
omero database management plugin
"""

import sys
from omero.cli import CLI
from omero_database.cli import DatabaseControl

HELP = 'Manage the OMERO PostgreSQL database'
try:
    register("database", DatabaseControl, HELP) # noqa
except NameError:
    if __name__ == "__main__":
        cli = CLI()
        cli.register("database", DatabaseControl, HELP)
        cli.invoke(sys.argv[1:])
