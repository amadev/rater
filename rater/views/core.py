# -*- coding: utf-8 -*-
"""
    rater.views.core
    ~~~~~~~~~~~~~~~~~

    This module implements the core views.  These are usually language
    independent view functions such as the overall index page.

    :copyright: (c) 2009 by Rater Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from werkzeug import redirect, Response
from werkzeug.exceptions import NotFound, MethodNotAllowed

from rater.application import url_for, json_response
from rater.templating import render_template

def home(request):
    """Shows the home page."""
    return render_template('core/home.html')

def about(request):
    """Just shows a simple about page that explains the system."""
    return render_template('core/about.html')


def not_found(request):
    """Shows a not found page."""
    return Response(render_template('core/not_found.html'), status=404,
                    mimetype='text/html')

def bad_request(request):
    """Shows a "bad request" page."""
    return Response(render_template('core/bad_request.html'),
                    status=400, mimetype='text/html')


def forbidden(request):
    """Shows a forbidden page."""
    return Response(render_template('core/forbidden.html'),
                    status=401, mimetype='text/html')
