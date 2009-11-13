# -*- coding: utf-8 -*-
"""
    rater.scripts
    ~~~~~~~~~~~~~~

    Provides some setup.py commands.

    :copyright: (c) 2009 by Rater Team
                (c) 2009 by Plurk Inc., see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
# note on imports:  This module must not import anything from the
# rater package, so that the initial import happens in the commands.
from distutils.cmd import Command
from distutils.errors import DistutilsOptionError


class RunserverCommand(Command):
    description = 'runs the development server'
    user_options = [
        ('host=', 'h',
         'the host of the server, defaults to localhost'),
        ('port=', 'p',
         'the port of the server, defaults to 3000'),
        ('no-reloader', None,
         'disable the automatic reloader'),
        ('no-debugger', None,
         'disable the integrated debugger')
    ]
    boolean_options = ['no-reloader', 'no-debugger']

    def initialize_options(self):
        self.host = 'localhost'
        self.port = 3000
        self.no_reloader = False
        self.no_debugger = False

    def finalize_options(self):
        if not str(self.port).isdigit():
            raise DistutilsOptionError('port has to be numeric')

    def run(self):
        from werkzeug import run_simple
        def wsgi_app(*a):
            from rater.application import application
            return application(*a)

        # werkzeug restarts the interpreter with the same arguments
        # which would print "running runserver" a second time.  Because
        # of this we force distutils into quiet mode.
        import sys
        sys.argv.insert(1, '-q')

        run_simple(self.host, self.port, wsgi_app,
                   use_reloader=not self.no_reloader,
                   use_debugger=not self.no_debugger)
