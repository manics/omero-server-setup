#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from glob import glob
import os
import logging
import re

from omero.config import ConfigXml
from . import external

log = logging.getLogger(__name__)

HELP = """Manage an OMERO PostgreSQL database"""

# Regular expression identifying a SQL schema
SQL_SCHEMA_REGEXP = re.compile(r'.*OMERO(\d+)(\.|A)?(\d*)([A-Z]*)__(\d+)$')

# Exit codes for db upgrade --dry-run (also used internally)
DB_UPTODATE = 0
DB_UPGRADE_NEEDED = 2
DB_INIT_NEEDED = 3
DB_NO_CONNECTION = 4


class Stop(Exception):
    def __init__(self, code, message):
        super().__init__(code, message)
        self.rc = code
        self.msg = message

    def __str__(self):
        return 'ERROR [{}] {}'.format(self.args[0], self.args[1])


def timestamp_filename(basename, ext=None):
    """
    Return a string of the form [basename-TIMESTAMP.ext]
    where TIMESTAMP is of the form YYYYMMDD-HHMMSS-MILSEC
    """
    dt = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    if ext:
        return '%s-%s.%s' % (basename, dt, ext)
    return '%s-%s' % (basename, dt)


##########

def is_schema(s):
    """Return true if the string is a valid SQL schema"""
    return SQL_SCHEMA_REGEXP.match(s) is not None


def sort_schemas(schemas):
    """Sort a list of SQL schemas in order"""
    def keyfun(v):
        x = SQL_SCHEMA_REGEXP.match(v).groups()
        # x3: 'DEV' should come before ''
        return (int(x[0]), x[1] if x[1] else '', int(x[2]) if x[2] else '',
                x[3] if x[3] else 'zzz', int(x[4]))

    return sorted(schemas, key=keyfun)


def parse_schema_files(files):
    """
    Parse a list of SQL files and return a dictionary of valid schema
    files where each key is a valid schema file and the corresponding value is
    a tuple containing the source and the target schema.
    """
    f_dict = {}
    for f in files:
        root, ext = os.path.splitext(f)
        if ext != ".sql":
            continue
        vto, vfrom = os.path.split(root)
        vto = os.path.split(vto)[1]
        if is_schema(vto) and is_schema(vfrom):
            f_dict[f] = (vfrom, vto)
    return f_dict


def get_db_args_env(self, ext=None, args=None, admin=False):
    """
    Get a dictionary of database connection parameters, and create an
    environment for running postgres commands.
    Falls back to omero defaults.
    """
    if args:
        db = {
            'name': self.args.dbname,
            'host': self.args.dbhost,
            'port': self.args.dbport or '5432',
            'user': self.args.dbuser,
            'pass': self.args.dbpass
        }
    else:
        if self.args.no_db_config:
            raise Exception('omero config.xml required')
        db = {
            'name': None,
            'host': None,
            'port': None,
            'user': None,
            'pass': None,
        }

    try:
        c = ext.get_config()
    except Exception as e:
        log.warning('config.xml not found: %s', e)
        c = {}

    for k in db:
        try:
            db[k] = c['omero.db.%s' % k]
        except KeyError:
            log.info(
                'Failed to lookup parameter omero.db.%s, using %s',
                k, db[k])

    for k in db:
        if not db[k]:
            raise Exception('Database {} required'.format(k))

    try:
        db['pgdata'] = c['postgres.data.dir']
    except KeyError:
        db['pgdata'] = None

    env = os.environ.copy()
    env['PGPASSWORD'] = db['pass']

    if admin:
        if self.args.adminuser:
            db['user'] = self.args.adminuser
        if self.args.adminpass:
            db['pass'] = self.args.adminpass
            env['PGPASSWORD'] = self.args.adminpass
    return db, env


class DbAdmin(object):

    def __init__(self, dir, command, args, external):

        self.dir = dir
        self.args = args
        log.info("%s: DbAdmin %s ...", self.__class__.__name__, dir)

        # TODO: If the server has already been configured we should use the
        # OMERO db credentials if not explicitly provided in args

        # Server directory
        if not os.path.exists(dir):
            raise Exception("%s does not exist!" % dir)

        self.external = external

        psqlv = self.psql(version=True)
        log.info('psql version: %s', psqlv)

        if command in (
            'createconfig',

            'create',
            'dump',
            'init',
            'justdoit',
            'upgrade',

            'pginit',
            'pgstart',
            'pgstop',
            'pgrestart',
        ):
            getattr(self, command)()
        elif command is not None:
            raise Stop(10, 'Invalid db command: %s' % command)

    def check_connection(self):
        try:
            self.psql('-c', r'\conninfo')
        except external.RunException as e:
            log.error(e)
            raise Stop(DB_NO_CONNECTION, 'Database connection check failed')

    def choose_omero_data_home(self):
        # if os.path.exists('/OMERO'):
        #     return '/OMERO'
        parent = os.getenv('CONDA_PREFIX', os.getenv('HOME'))
        if not parent:
            raise Exception(
                'Unable to determine omero.data.dir. Pass --data-dir.')
        return os.path.join(parent, 'OMERO')

    def init(self):
        self.check_connection()
        omerosql = self.args.omerosql
        autoupgrade = False
        if not omerosql:
            omerosql = timestamp_filename('omero', 'sql')
            log.info('Creating SQL: %s', omerosql)
            if not self.args.dry_run:
                self.external.omero_cli(
                    ["db", "script", "-f", omerosql, "", "",
                     self.args.rootpass])
        elif os.path.exists(omerosql):
            log.info('Using existing SQL: %s', omerosql)
            autoupgrade = True
        else:
            log.error('SQL file not found: %s', omerosql)
            raise Stop(40, 'SQL file not found')

        log.info('Creating database using %s', omerosql)
        if not self.args.dry_run:
            self.psql('-f', omerosql)

        if autoupgrade:
            self.upgrade()

        # If this is a temporary sql file delete it
        if not self.args.omerosql and not self.args.dry_run:
            os.remove(omerosql)

    def sort_schema(self, versions):
        return sort_schemas(versions)

    def sql_version_matrix(self):
        # Parse all schema files
        files = glob(os.path.join(
            self.dir, 'sql', 'psql', 'OMERO*', 'OMERO*.sql'))
        f_dict = parse_schema_files(files)

        # Create a set of unique schema versions
        versions = set()
        for v in list(f_dict.values()):
            versions.update(v)
        versions = sort_schemas(versions)
        n = len(versions)
        versionsrev = dict(vi for vi in zip(versions, range(n)))

        # M(from,to) = upgrade script for this pair or None
        M = [[None for b in range(n)] for a in range(n)]
        for key, value in list(f_dict.items()):
            vfrom, vto = value
            M[versionsrev[vfrom]][versionsrev[vto]] = key

        return M, versions

    def sql_version_resolve(self, M, versions, vfrom):
        def resolve_index(M, ifrom, ito):
            n = len(M)
            for p in range(n - 1, 0, -1):
                if M[ifrom][p]:
                    if p == ito:
                        return [M[ifrom][p]]
                    try:
                        p2 = resolve_index(M, p, ito)
                        return [M[ifrom][p]] + p2
                    except Exception:
                        continue
            raise Exception('No upgrade path found from %s to %s' % (
                versions[ifrom], versions[ito]))

        ugpath = resolve_index(M, versions.index(vfrom), len(versions) - 1)
        return ugpath

    def check(self):
        return self.upgrade(check=True)

    def upgrade(self, check=False):
        try:
            self.check_connection()
        except Stop as e:
            if check:
                return e.rc
            raise e
        try:
            currentsqlv = '%s__%s' % self.get_current_db_version()
        except external.RunException as e:
            log.error(e)
            if check:
                return DB_INIT_NEEDED
            raise Stop(DB_INIT_NEEDED, 'Unable to get database version')

        M, versions = self.sql_version_matrix()
        latestsqlv = versions[-1]

        if latestsqlv == currentsqlv:
            log.info('Database is already at %s', latestsqlv)
            if check:
                return DB_UPTODATE
        else:
            ugpath = self.sql_version_resolve(M, versions, currentsqlv)
            log.debug('Database upgrade path: %s', ugpath)
            if check:
                return DB_UPGRADE_NEEDED
            if self.args.dry_run:
                raise Stop(
                    DB_UPGRADE_NEEDED, 'Database upgrade required %s->%s' % (
                        currentsqlv, latestsqlv))
            for upgradesql in ugpath:
                log.info('Upgrading database using %s', upgradesql)
                self.psql('-f', upgradesql)

    def justdoit(self):
        """
        Attempt to do everything necessary to ensure the database is created
        and up-to-date
        """
        status = self.upgrade(check=True)
        if status in (DB_NO_CONNECTION,):
            self.create()

        if status in (DB_NO_CONNECTION, DB_INIT_NEEDED):
            self.init()

        if status in (DB_UPGRADE_NEEDED,):
            self.upgrade()

    def createconfig(self):
        created = self.get_or_create_config(write=not self.args.dry_run,
                                            postgres=self.args.manage_postgres)
        log.info('Database configuration: {}'.format(created))

    def create(self):
        db, env = self.get_db_args_env()

        userexists = self.psql(
            '-c', "SELECT 1 FROM pg_roles WHERE rolname='{}';".format(
                db['user']), admin=True)
        if userexists.strip() == '1':
            log.info('Database user exists: %s', db['user'])
        else:
            log.info('Creating database user: %s', db['user'])
            if not self.args.dry_run:
                self.psql('-c', "CREATE USER {} WITH PASSWORD '{}';".format(
                    db['user'], db['pass']), admin=True)

        dbexists = self.psql(
            '-c', "SELECT 1 FROM pg_database WHERE datname='{}';".format(
                db['name']), admin=True)
        if dbexists.strip() == '1':
            log.info('Database exists: %s', db['name'])
        else:
            log.info('Creating database: %s', db['name'])
            if not self.args.dry_run:
                self.psql('-c', "CREATE DATABASE {} WITH OWNER {};".format(
                    db['name'], db['user']), admin=True)

        if not self.args.dry_run:
            self.check_connection()

    def get_current_db_version(self):
        q = ('SELECT currentversion, currentpatch FROM dbpatch '
             'ORDER BY id DESC LIMIT 1')
        log.debug('Executing query: %s', q)
        result = self.psql('-c', q)
        # Ignore empty string
        result = [r for r in result.split(os.linesep) if r]
        if len(result) != 1:
            raise Exception('Got %d rows, expected 1', len(result))
        v = tuple(result[0].split('|'))
        log.info('Current omero db version: %s', v)
        return v

    def dump(self):
        """
        Dump the database using the postgres custom format
        """
        self.check_connection()
        dumpfile = self.args.dumpfile
        if not dumpfile:
            db, env = self.get_db_args_env()
            dumpfile = timestamp_filename(
                'omero-database-%s' % db['name'], 'pgdump')

        log.info('Dumping database to %s', dumpfile)
        if not self.args.dry_run:
            self.pgdump('-Fc', '-f', dumpfile)

    def get_or_create_config(self, write, postgres):
        if self.args.no_db_config:
            cfgmap = {}
        else:
            try:
                cfgmap = self.external.get_config()
            except Exception as e:
                log.warning('config.xml not found: %s', e)
                cfgmap = {}
        created = {}

        def update_value(cfgkey, argname, default=None):
            if cfgkey in cfgmap:
                created[cfgkey] = cfgmap[cfgkey]
            elif argname in self.args and getattr(
                    self.args, argname) is not None:
                created[cfgkey] = getattr(self.args, argname)
            elif default is None:
                raise Exception(
                    'No configuration value for {}'.format(cfgkey))
            else:
                created[cfgkey] = default
            log.debug('%s=%s', cfgkey, created[cfgkey])

        update_value('omero.db.name', 'dbname', 'omero')
        update_value('omero.db.host', 'dbhost', 'localhost')
        update_value('omero.db.port', 'dbport', '5432')
        update_value('omero.db.user', 'dbuser', 'omero')
        update_value('omero.db.pass', 'dbpass', 'omero')

        update_value('omero.data.dir', 'data_dir', '/OMERO')
        if created['omero.data.dir'].lower() == 'auto':
            created['omero.data.dir'] = self.choose_omero_data_home()

        if postgres:
            update_value('postgres.data.dir', '',
                         os.path.join(created['omero.data.dir'], 'pgdata'))

        # TODO: Set to a non-standard port if we're controlling postgres?
        # if created.get('postgres.data.dir'):
        #     created['omero.db.port'] = str(randint(30000, 60000))

        if write:
            # TODO: Move to external.save_config()
            cfg = ConfigXml(os.path.join(
                self.dir, 'etc', 'grid', 'config.xml'))
            for k, v in created.items():
                cfg[k] = v
            cfg.close()

        return created

    def get_db_args_env(self, admin=False):
        """
        Get a dictionary of database connection parameters, and create an
        environment for running postgres commands.
        Falls back to omero defaults.
        """

        cfg = self.get_or_create_config(write=False, postgres=False)
        db = {}
        for k in ('name', 'host', 'port', 'user', 'pass'):
            db[k] = cfg['omero.db.%s' % k]
        if not db['name']:
            raise Exception('Database name required')

        env = os.environ.copy()
        env['PGPASSWORD'] = db['pass']

        if admin:
            if self.args.adminuser:
                db['user'] = self.args.adminuser
            if self.args.adminpass:
                db['pass'] = self.args.adminpass
                env['PGPASSWORD'] = self.args.adminpass
        return db, env

    def psql(self, *psqlargs, admin=False, version=False):
        """
        Run a psql command
        """
        if version:
            stdout, stderr = external.run(
                'psql', ['--version'], capturestd=True)
            if stderr:
                log.warning('stderr: %s', stderr)
            log.debug('stdout: %s', stdout)
            return stdout.decode()

        db, env = self.get_db_args_env(admin=admin)

        args = [
            '-v', 'ON_ERROR_STOP=on',
            '-w', '-A', '-t',
            '-h', db['host'],
            '-p', db['port'],
            '-U', db['user'],
        ]
        if admin:
            args += ['-d', 'postgres']
        if not admin:
            args += ['-d', db['name']]
        args += list(psqlargs)
        stdout, stderr = external.run('psql', args, capturestd=True, env=env)
        if stderr:
            log.warning('stderr: %s', stderr)
        log.debug('stdout: %s', stdout)
        return stdout.decode()

    def pgdump(self, *pgdumpargs):
        """
        Run a pg_dump command
        """
        db, env = self.get_db_args_env()

        args = ['-d', db['name'], '-h', db['host'], '-U', db['user'], '-w'
                ] + list(pgdumpargs)
        stdout, stderr = external.run(
            'pg_dump', args, capturestd=True, env=env)
        if stderr:
            log.warning('stderr: %s', stderr)
        log.debug('stdout: %s', stdout)
        return stdout.decode()

    # PostgreSQL management

    def get_and_check_config(self):
        cfgmap = self.external.get_config()
        for required in (
            'postgres.data.dir',
            'omero.db.name',
            'omero.db.host',
            'omero.db.port',
            'omero.db.user',
            'omero.db.pass',
        ):
            if required not in cfgmap or not cfgmap[required]:
                raise Exception('Property {} required'.format(required))
        return cfgmap

    def pginit(self):
        self.pg_ctl(
            'initdb',
            '-o', '--encoding=UTF-8',
            '-o', '--username=postgres',
        )

    def pgstart(self, restart=False):
        cfg = self.get_and_check_config()
        logfile = os.path.join(cfg['postgres.data.dir'], 'postgres.log')
        self.pg_ctl(
            'restart' if restart else 'start',
            '--log={}'.format(logfile),
            '-o', '-p {}'.format(cfg['omero.db.port'])
        )

    def pgstop(self):
        self.pg_ctl('stop')

    def pgrestart(self):
        self.start(restart=True)

    def pg_ctl(self, *args, capturestd=False):
        cfg = self.get_and_check_config()
        pgdata = '--pgdata={}'.format(cfg['postgres.data.dir'])
        try:
            stdout, stderr = external.run(
                'pg_ctl', [pgdata] + list(args), capturestd=capturestd)
        except external.RunException as e:
            log.fatal(e)
            raise Stop(10, 'Failed to run pg_ctl {}'.format(args))
        if capturestd:
            if stderr:
                log.warning('stderr: %s', stderr)
            log.debug('stdout: %s', stdout)
            return stdout.decode()
