# -*- coding: utf-8 -*-
"""
    rater.urls
    ~~~~~~~~~~~
    :copyright: (c) 2009 by Rater Team, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""
from werkzeug.routing import Map, Rule as RuleBase


class Rule(RuleBase):

    def __gt__(self, endpoint):
        self.endpoint = endpoint
        return self


url_map = Map([
    # core pages
    Rule('/') > 'core.home',
    Rule('/about') > 'core.about',

    # Build only stuff
    Rule('/_static/<file>', build_only=True) > 'static',
])
