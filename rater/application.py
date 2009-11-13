# -*- coding: utf-8 -*-
"""
    rater.application
    ~~~~~~~~~~~~~~~~~~

    The WSGI application for Rater.

    :copyright: (c) 2009 by Rater Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
import os
from urlparse import urlparse, urlsplit, urljoin
from fnmatch import fnmatch
from functools import update_wrapper
from simplejson import dumps

from werkzeug import Request as RequestBase, Response, cached_property, \
     import_string, redirect, SharedDataMiddleware, url_quote, \
     url_decode 
from werkzeug.exceptions import HTTPException, NotFound, BadRequest, Forbidden
from werkzeug.routing import BuildError, RequestRedirect
from werkzeug.contrib.securecookie import SecureCookie

from rater.utils.ctxlocal import local, LocalProperty

# already resolved and imported views
_resolved_views = {}


class Request(RequestBase):
    """The request class."""

    #: each request might transmit up to four megs of payload that
    #: is stored in memory.  If more is transmitted, Werkzeug will
    #: abort the request with an appropriate status code.  This should
    #: not happen unless someone really tempers with the data.
    max_form_memory_size = 4 * 1024 * 1024

    def __init__(self, environ):
        RequestBase.__init__(self, environ)
        before_request_init.emit()
        self.url_adapter = url_map.bind_to_environ(self.environ)
        self.match_exception = None
        try:
            self.endpoint, self.view_arguments = self.url_adapter.match()
        except HTTPException, e:
            self.endpoint = self.view_arguments = None
            self.match_exception = e
        self.db_queries = []
        local.request = self
        after_request_init.emit(request=self)

    current = LocalProperty('request')

    def dispatch(self):
        """Where do we want to go today?"""
        before_request_dispatch.emit(request=self)
        try:
            if self.match_exception is not None:
                raise self.match_exception
            rv = self.view(self, **self.view_arguments)
        except NotFound, e:
            rv = get_view('core.not_found')(self)
        rv = self.process_view_result(rv)
        after_request_dispatch.emit(request=self, response=rv)
        return rv

    def process_view_result(self, rv):
        """Processes a view's return value and ensures it's a response
        object.  This is automatically called by the dispatch function
        but is also handy for view decorators.
        """
        if isinstance(rv, basestring):
            rv = Response(rv, mimetype='text/html')
        elif not isinstance(rv, Response):
            rv = Response.force_type(rv, self.environ)
        return rv

    @cached_property
    def view(self):
        """The view function."""
        return get_view(self.endpoint)

    @cached_property
    def session(self):
        """The active session."""
        return SecureCookie.load_cookie(self, settings.COOKIE_NAME,
                                        settings.SECRET_KEY)

    @property
    def is_behind_proxy(self):
        """Are we behind a proxy?  Accessed by Werkzeug when needed."""
        return settings.IS_BEHIND_PROXY

    def list_languages(self):
        """Lists all languages."""
        return [dict(
            name=locale.display_name,
            key=key,
            selected=self.locale == locale,
            select_url=url_for('core.set_language', locale=key),
            section_url=url_for('kb.overview', lang_code=key)
        ) for key, locale in list_languages()]

    def flash(self, message, error=False):
        """Flashes a message."""
        type = error and 'error' or 'info'
        self.session.setdefault('flashes', []).append((type, message))

    def pull_flash_messages(self):
        """Returns all flash messages.  They will be removed from the
        session at the same time.  This also pulls the messages from
        the database that are queued for the user.
        """
        msgs = self._pulled_flash_messages or []
        if self.user is not None:
            to_delete = set()
            for msg in UserMessage.query.filter_by(user=self.user).all():
                msgs.append((msg.type, msg.text))
                to_delete.add(msg.id)
            if to_delete:
                UserMessage.query.filter(UserMessage.id.in_(to_delete)).delete()
                session.commit()
        if 'flashes' in self.session:
            msgs += self.session.pop('flashes')
            self._pulled_flash_messages = msgs
        return msgs


def get_view(endpoint):
    """Returns the view for the endpoint.  It will cache both positive and
    negative hits, so never pass untrusted values to it.  If a view does
    not exist, `None` is returned.
    """
    view = _resolved_views.get(endpoint)
    if view is not None:
        return view
    try:
        view = import_string('rater.views.' + endpoint)
    except (ImportError, AttributeError):
        view = import_string(endpoint, silent=True)
    _resolved_views[endpoint] = view
    return view


def json_response(message=None, html=None, error=False, login_could_fix=False,
                  **extra):
    """Returns a JSON response for the JavaScript code.  The "wire protocoll"
    is basically just a JSON object with some common attributes that are
    checked by the success callback in the JavaScript code before the handler
    processes it.

    The `error` and `login_could_fix` keys are internally used by the flashing
    system on the client.
    """
    extra.update(message=message, html=html, error=error,
                 login_could_fix=login_could_fix)
    for key, value in extra.iteritems():
        extra[key] = remote_export_primitive(value)
    return Response(dumps(extra), mimetype='application/json')


def not_logged_in_json_response():
    """Standard response that the user is not logged in."""
    return json_response(message=_(u'You have to login in order to '
                                   u'visit this page.'),
                         error=True, login_could_fix=True)


def require_admin(f):
    """Decorates a view function so that it requires a user that is
    logged in.
    """
    def decorated(request, **kwargs):
        if not request.user.is_admin:
            message = _(u'You cannot access this resource.')
            if request.is_xhr:
                return json_response(message=message, error=True)
            raise Forbidden(message)
        return f(request, **kwargs)
    return require_login(update_wrapper(decorated, f))


def require_login(f):
    """Decorates a view function so that it requires a user that is
    logged in.
    """
    def decorated(request, **kwargs):
        if not request.is_logged_in:
            if request.is_xhr:
                return not_logged_in_json_response()
            request.flash(_(u'You have to login in order to visit this page.'))
            return redirect(url_for('core.login', next=request.url))
        return f(request, **kwargs)
    return update_wrapper(decorated, f)


def iter_endpoint_choices(new, current=None):
    """Iterate over all possibilities for URL generation."""
    yield new
    if current is not None and '.' in current:
        yield current.rsplit('.', 1)[0] + '.' + new


def inject_lang_code(request, endpoint, values):
    """Returns a dict with the values for the given endpoint.  You must not alter
    the dict because it might be shared.  If the given endpoint does not exist
    `None` is returned.
    """
    rv = values
    if 'lang_code' not in rv:
        try:
            if request.url_adapter.map.is_endpoint_expecting(
                    endpoint, 'lang_code'):
                rv = values.copy()
                rv['lang_code'] = request.view_lang or str(request.locale)
        except KeyError:
            return
    return rv


def url_for(endpoint, **values):
    """Returns a URL for a given endpoint with some interpolation."""
    external = values.pop('_external', False)
    if hasattr(endpoint, 'get_url_values'):
        endpoint, values = endpoint.get_url_values(**values)
    request = Request.current
    anchor = values.pop('_anchor', None)
    assert request is not None, 'no active request'
    for endpoint_choice in iter_endpoint_choices(endpoint, request.endpoint):
        real_values = inject_lang_code(request, endpoint_choice, values)
        if real_values is None:
            continue
        try:
            url = request.url_adapter.build(endpoint_choice, real_values,
                                            force_external=external)
        except BuildError:
            continue
        view = get_view(endpoint)
        if is_exchange_token_protected(view):
            xt = get_exchange_token(request)
            url = '%s%s_xt=%s' % (url, '?' in url and '&' or '?', xt)
        if anchor is not None:
            url += '#' + url_quote(anchor)
        return url
    raise BuildError(endpoint, values, 'GET')


def save_session(request, response):
    """Saves the session to the response.  Called automatically at
    the end of a request.
    """
    if request.session.should_save:
        request.session.save_cookie(response, settings.COOKIE_NAME)


def finalize_response(request, response):
    """Finalizes the response.  Applies common response processors."""
    if not isinstance(response, Response):
        response = Response.force_type(response, request.environ)
    if response.status == 200:
        response.add_etag()
        response = response.make_conditional(request)
    before_response_sent.emit(request=request, response=response)
    return response


@Request.application
def application(request):
    """The WSGI application.  The majority of the handling here happens
    in the :meth:`Request.dispatch` method and the functions that are
    connected to the request signals.
    """
    try:
        try:
            response = request.dispatch()
        except HTTPException, e:
            response = e.get_response(request.environ)
        return finalize_response(request, response)
    finally:
        after_request_shutdown.emit()


application = SharedDataMiddleware(application, {
    '/_static':     os.path.join(os.path.dirname(__file__), 'static')
})


# imported here because of possible circular dependencies
from rater import settings
from rater.urls import url_map

from rater.signals import before_request_init, after_request_init, \
     before_request_dispatch, after_request_dispatch, \
     after_request_shutdown, before_response_sent

# remember to save the session
before_response_sent.connect(save_session)
