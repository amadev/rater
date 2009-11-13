# -*- coding: utf-8 -*-
"""
    rater.templating
    ~~~~~~~~~~~~~~~~~

    Very simple bridge to Jinja2.

    :copyright: (c) 2009 by Rater Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from __future__ import with_statement
from os import path
from werkzeug import escape
from werkzeug.exceptions import NotFound
from jinja2 import Environment, PackageLoader, BaseLoader, TemplateNotFound

jinja_env = Environment(loader=PackageLoader('rater'),
                        extensions=['jinja2.ext.i18n'])


def render_template(template_name, **context):
    """Renders a template into a string."""
    template = jinja_env.get_template(template_name)
    context['request'] = Request.current
    return template.render(context)


def get_macro(template_name, macro_name):
    """Return a macro from a template."""
    template = jinja_env.get_template(template_name)
    return getattr(template.module, macro_name)


def datetimeformat_filter(obj, html=True, prefixed=True):
    rv = format_datetime(obj)
    if prefixed:
        rv = _(u'on %s') % rv
    if html:
        rv = u'<span class="datetime" title="%s">%s</span>' % (
            obj.strftime('%Y-%m-%dT%H:%M:%SZ'),
            escape(rv)
        )
    return rv


from rater import settings
from rater.application import Request, url_for
jinja_env.globals.update(
    url_for=url_for,
    settings=settings
)
jinja_env.filters.update(
    datetimeformat=datetimeformat_filter
)
