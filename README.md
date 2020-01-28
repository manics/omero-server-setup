# OMERO database management plugin
[![Build Status](https://travis-ci.com/manics/omero-cli-database.svg?branch=master)](https://travis-ci.com/manics/omero-cli-database)

Create, initialise and upgrade OMERO databases.


## Usage

Set the `OMERODIR` environment variable to the location of OMERO.server.

If you have configured OMERO.server with the database configuration details this plugin will use them, otherwise you can pass all parameters on the command line (see `omero database --help` for the list of parameters).

To magically "do the right thing" run:
```
omero database justdoit
```

This will create, initialise or upgrade your OMERO database if necessary, otherwise it will do nothing.

If the PostgreSQL user or database do not exist you may need to pass admin credentials so the plugin can create them:
```
omero database --adminuser postgres-admin --adminpass secret justdoit
```

If you want more control see the help output for other sub-commands.


## Developer notes

Commits up to https://github.com/manics/omero-cli-database/tree/82937434850a3585dc2b4140e446092277dd9a6b were extracted from https://github.com/ome/omego/tree/v0.7.0 using `git filter-branch`.

This repository uses [setuptools-scm](https://pypi.org/project/setuptools-scm/) so versions are automatically obtained from git tags.
