# -*- coding: utf-8 -*-
"""
Rater
========
Site where you can rate anything you like (or not like)

"""
from setuptools import setup

extra = {}

try:
    from rater import scripts
except ImportError:
    pass
else:
    extra['cmdclass'] = {
        'runserver':        scripts.RunserverCommand
    }

setup(
    name='Rater',
    version='0.1',
    license='BSD',
    author='Rater Team',
    author_email='radev@bk.ru',
    description='Rating site',
    long_description=__doc__,
    packages=['rater', 'rater.views', 'rater.utils'],
    zip_safe=False,
    platforms='any',
    install_requires=[
        'Werkzeug>=0.5.1',
        'Jinja2',
        'simplejson',
        'pymongo',
        'webdepcompress'
    ],
    **extra
)
