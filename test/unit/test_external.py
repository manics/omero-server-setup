#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2014 University of Dundee & Open Microscopy Environment
# All Rights Reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import pytest
from mox3 import mox

import subprocess
import tempfile

from omero_server_setup import external


class TestRunException(object):

    def setup_method(self, method):
        self.ex = external.RunException(
            'Message', 'exe', ['arg1', 'arg2'], 1, b'out', b'err')

    def test_shortstr(self):
        s = 'Message\n  command: exe arg1 arg2\n  return code: 1'
        assert self.ex.shortstr() == s

    def test_fullstr(self):
        s = ('Message\n  command: exe arg1 arg2\n  return code: 1\n'
             '  stdout: out\n  stderr: err')
        assert self.ex.fullstr() == s


class TestExternal(object):

    def setup_method(self, method):
        self.ext = external.External(None)
        self.mox = mox.Mox()
        self.envfilename = 'test.env'

    def teardown_method(self, method):
        self.mox.UnsetStubs()

    @pytest.mark.xfail(reason='Not implemented')
    def test_get_config(self):
        assert False

    @pytest.mark.xfail(reason='Not implemented')
    def test_update_config(self):
        assert False

    def test_omero_cli(self):
        self.mox.StubOutWithMock(self.ext.cli, 'invoke')
        self.ext.cli.invoke(['arg1', 'arg2']).AndReturn(0)
        self.mox.ReplayAll()

        self.ext.omero_cli(['arg1', 'arg2'])
        self.mox.VerifyAll()

    @pytest.mark.parametrize('retcode', [0, 1])
    @pytest.mark.parametrize('capturestd', [True, False])
    def test_run(self, tmpdir, retcode, capturestd):
        env = {'TEST': 'test'}
        self.mox.StubOutWithMock(subprocess, 'call')
        self.mox.StubOutWithMock(tempfile, 'TemporaryFile')

        if capturestd:
            outfile = open(str(tmpdir.join('std.out')), 'wb+')
            outfile.write(b'out')
            errfile = open(str(tmpdir.join('std.err')), 'wb+')
            errfile.write(b'err')

            tempfile.TemporaryFile().AndReturn(outfile)
            tempfile.TemporaryFile().AndReturn(errfile)
            subprocess.call(
                ['test', 'arg1', 'arg2'], env=env,
                stdout=outfile, stderr=errfile).AndReturn(retcode)
        else:
            subprocess.call(
                ['test', 'arg1', 'arg2'], env=env,
                stdout=None, stderr=None).AndReturn(retcode)
        self.mox.ReplayAll()

        if retcode == 0:
            stdout, stderr = external.run(
                'test', ['arg1', 'arg2'], capturestd, env)
        else:
            with pytest.raises(external.RunException) as excinfo:
                external.run('test', ['arg1', 'arg2'], capturestd, env)
            exc = excinfo.value
            assert exc.r == 1
            assert exc.args[0] == 'Non-zero return code'
            stdout = exc.stdout
            stderr = exc.stderr

        if capturestd:
            assert stdout == b'out'
            assert stderr == b'err'
            outfile.close()
            errfile.close()
        else:
            assert stdout is None
            assert stderr is None

        self.mox.VerifyAll()
