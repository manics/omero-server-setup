# OMERO server setup and database management plugin
[![Build Status](https://travis-ci.com/manics/omero-server-setup.svg?branch=master)](https://travis-ci.com/manics/omero-cli-database)

Configure OMERO.server and manage a PostgreSQL database


## Usage

Set the `OMERODIR` environment variable to the location of OMERO.server.

If you already have a configured OMERO.server and just want to initialise or upgrade the OMERO database jump to **Managing the OMERO database on existing servers**.
Otherwise follow these instructions to setup a new server.


### OMERO Configuration

To setup a new OMERO.server run:
```
omero setup createconfig --data-dir auto
```
This will automatically set a path for the OMERO data directory as well as enabling self-signed certificates and websockets.

If you do not have a running PostgreSQL server and would like this plugin to take care of starting one include the `--manage-postgres` flag.
A `pgdata` directory will be created inside your OMERO data directory for PostgreSQL data.
```
omero setup createconfig --manage-postgres --data-dir auto
```

If you need to overwrite an existing configuration first delete it:
```
omero config drop default
```


### PostgreSQL server

If you already have a PostgreSQL server skip this section.

If you selected `--manage-postgres` during the configuration step and have not previously setup PostgreSQL run:
```
omero setup pginit
```


### Start OMERO

OMERO should be ready to start! Run:
```
omero setup start
```
This will generate certificates and start PostgreSQL if enabled before starting OMERO.server.


### Stop OMERO

```
omero setup stop
```
This will stop OMERO.server and PostgreSQL if enabled.


## Managing the OMERO database on existing servers

To automagically setup or update the OMERO database run:
```
omero setup justdoit
```


## Additional control

If you want more control see the full list of sub-commands:
```
omero setup --help
```


## Developer notes

Commits up to https://github.com/manics/omero-cli-database/tree/82937434850a3585dc2b4140e446092277dd9a6b were extracted from https://github.com/ome/omego/tree/v0.7.0 using `git filter-branch`.

This repository uses [setuptools-scm](https://pypi.org/project/setuptools-scm/) so versions are automatically obtained from git tags.
