#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OMERO setup and database management plugin
"""

import sys
from omero.cli import CLI
from omero_server_setup.cli import SetupControl

HELP = "Configure OMERO and a PostgreSQL database"
try:
    register("setup", SetupControl, HELP)  # noqa
except NameError:
    if __name__ == "__main__":
        cli = CLI()
        cli.register("setup", SetupControl, HELP)
        cli.invoke(sys.argv[1:])
