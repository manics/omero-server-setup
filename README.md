# OMERO setup and database management plugin
[![Build Status](https://travis-ci.com/manics/omero-cli-database.svg?branch=master)](https://travis-ci.com/manics/omero-cli-database)

Configure OMERO and manage a PostgreSQL database


## Usage

Set the `OMERODIR` environment variable to the location of OMERO.server.

### OMERO Configuration

If you are setting up a new OMERO.server run:
```
omero setup -vn createconfig --data-dir auto
```
If you do not have a running PostgreSQL server and would like this plugin to take care or starting one include the `--manage-postgres` flag.
A `pgdata` directory will be created inside you OMERO data directory for PostgreSQL data.
```
omero setup -vn createconfig --manage-postgres --data-dir auto
```


### PostgreSQL server

If you already have a PostgreSQL server skip this section.
If you selected the `--manage-postgres` when configuring OMERO and have not previously setup PostgreSQL run:
```
omero setup pginit
omero setup pgstart
```
To stop the PostgreSQL server later run
```
omero setup pgstop
```


### OMERO database setup

To magically "do the right thing" run:
```
omero setup justdoit --adminuser postgres
```

This will create, initialise or upgrade your OMERO database if necessary, otherwise it will do nothing.

If the PostgreSQL user or database do not exist you may need to pass admin credentials so the plugin can create them:
```
omero database justdoit --adminuser postgres-admin --adminpass secret
```

If you want more control see the help output for other sub-commands.


### Start OMERO

OMERO should be ready to start! Run:
```
omero admin start
```


## Developer notes

Commits up to https://github.com/manics/omero-cli-database/tree/82937434850a3585dc2b4140e446092277dd9a6b were extracted from https://github.com/ome/omego/tree/v0.7.0 using `git filter-branch`.

This repository uses [setuptools-scm](https://pypi.org/project/setuptools-scm/) so versions are automatically obtained from git tags.
