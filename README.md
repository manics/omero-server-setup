# OMERO server setup and database management plugin
[![Build Status](https://travis-ci.com/manics/omero-cli-database.svg?branch=master)](https://travis-ci.com/manics/omero-cli-database)

Configure OMERO.server and manage a PostgreSQL database


## Usage

Set the `OMERODIR` environment variable to the location of OMERO.server.


### OMERO Configuration

If you are setting up a new OMERO.server run:
```
omero setup -v createconfig --data-dir auto
```
This will automatically set a path for the OMERO data directory as well as enabling self-signed certificates adn websockets.

If you do not have a running PostgreSQL server and would like this plugin to take care of starting one include the `--manage-postgres` flag.
A `pgdata` directory will be created inside your OMERO data directory for PostgreSQL data.
```
omero setup -v createconfig --manage-postgres --data-dir auto
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

Start PostgreSQL:
```
omero setup pgstart
```


### OMERO setup

To automagically setup or update the OMERO database run:
```
omero setup justdoit --adminuser postgres
```

This will create, initialise or upgrade your OMERO database if necessary, otherwise it will do nothing.

You can omit the `--adminuser` argument if the default user is an admin, or if the database already exists.
If a password is required for the admin account: `--adminpass secret`.

If you want more control see the help output for other sub-commands.

Generate self-signed certificates by running:
```
omero setup certificates
```


### Start OMERO

OMERO should be ready to start! Run:
```
omero admin start
```


### Stop OMERO

```
omero admin stop
```

If you enabled `--manage-postgres` stop the PostgreSQL server by running:
```
omero setup pgstop
```


## Developer notes

Commits up to https://github.com/manics/omero-cli-database/tree/82937434850a3585dc2b4140e446092277dd9a6b were extracted from https://github.com/ome/omego/tree/v0.7.0 using `git filter-branch`.

This repository uses [setuptools-scm](https://pypi.org/project/setuptools-scm/) so versions are automatically obtained from git tags.
