# OMERO server database management plugin
[![Build Status](https://travis-ci.com/manics/omero-cli-database.svg?branch=master)](https://travis-ci.com/manics/omero-cli-database)

Manage the OMERO.server PostgreSQL database.


## Usage

Set the `OMERODIR` environment variable to the location of OMERO.server.

To automagically setup or update the OMERO database run:
```
omero database justdoit
```

If you want more control see the full list of sub-commands:
```
omero database --help
```


## Developer notes

Commits up to https://github.com/manics/omero-server-setup/tree/82937434850a3585dc2b4140e446092277dd9a6b were extracted from https://github.com/ome/omego/tree/v0.7.0 using `git filter-branch`.

This repository uses [setuptools-scm](https://pypi.org/project/setuptools-scm/) so versions are automatically obtained from git tags.
