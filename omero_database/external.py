#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import logging
import os
import tempfile
import time

from omero.cli import CLI
from omero.config import ConfigXml

log = logging.getLogger(__name__)


class RunException(Exception):
    def __init__(self, msg, exe, exeargs, r, stdout, stderr):
        super(RunException, self).__init__(msg)
        self.exe = exe
        self.exeargs = exeargs
        self.r = r
        self.stdout = stdout
        self.stderr = stderr

    def fullstr(self):
        def format(std):
            if std:
                return std.decode(errors="replace")
            return ""

        return "%s\n  stdout: %s\n  stderr: %s" % (
            self.shortstr(),
            format(self.stdout),
            format(self.stderr),
        )

    def shortstr(self):
        return "%s\n  command: %s %s\n  return code: %d" % (
            super(RunException, self).__str__(),
            self.exe,
            " ".join(self.exeargs),
            self.r,
        )

    def __str__(self):
        return self.fullstr()


def run(exe, args, capturestd=False, env=None):
    """
    Runs an executable with an array of arguments, optionally in the
    specified environment.
    Returns stdout and stderr
    """
    command = [exe] + args
    if env:
        log.info("Executing [custom environment]: %s", " ".join(command))
    else:
        log.info("Executing : %s", " ".join(command))
    start = time.time()

    # Temp files will be automatically deleted on close()
    # If run() throws the garbage collector should call close(), so don't
    # bother with try-finally
    outfile = None
    errfile = None
    if capturestd:
        outfile = tempfile.TemporaryFile()
        errfile = tempfile.TemporaryFile()

    # Use call instead of Popen so that stdin is connected to the console,
    # in case user input is required
    # On Windows shell=True is needed otherwise the modified environment
    # PATH variable is ignored. On Unix this breaks things.
    r = subprocess.call(command, env=env, stdout=outfile, stderr=errfile)

    stdout = None
    stderr = None
    if capturestd:
        outfile.seek(0)
        stdout = outfile.read()
        outfile.close()
        errfile.seek(0)
        stderr = errfile.read()
        errfile.close()

    end = time.time()
    if r != 0:
        log.debug("Failed [%.3f s]", end - start)
        raise RunException(
            "Non-zero return code", exe, args, r, stdout, stderr
        )
    log.debug("Completed [%.3f s]", end - start)
    return stdout, stderr


class External(object):
    """
    Manages the execution of shell and OMERO CLI commands
    """

    def __init__(self, dir):
        """
        :param dir: The server directory, can be None if you are not
                    interacting with OMERO
        """
        self.cli = None
        self.dir = None
        if dir:
            self.dir = os.path.abspath(dir)
        self.cli = CLI()
        self.cli.loadplugins()

    def get_config(self, raise_missing=True):
        """
        Returns a dictionary of all OMERO config properties
        """
        configxml = os.path.join(self.dir, "etc", "grid", "config.xml")
        try:
            configobj = ConfigXml(configxml, read_only=True)
        except Exception as e:
            log.warning("config.xml not found: %s", e)
            if raise_missing:
                raise
            return {}
        cfgdict = configobj.as_map()
        configobj.close()
        return cfgdict

    def omero_cli(self, command):
        """
        Runs an OMERO CLI command
        """
        assert isinstance(command, list)
        log.info("Running omero: %s", " ".join(command))
        return self.cli.invoke(command)
        # TODO: capturestd=True
