#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
omero postgres management plugin
"""

import sys
from omero.cli import CLI
from omero_database.cli import PostgresControl

HELP = 'Manage a local PostgreSQL server'
try:
    register('postgres', PostgresControl, HELP) # noqa
except NameError:
    if __name__ == '__main__':
        cli = CLI()
        cli.register('postgres', PostgresControl, HELP)
        cli.invoke(sys.argv[1:])
