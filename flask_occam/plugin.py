# -*- coding: utf-8 -*-
#
# Plugin Setup
#
# ------------------------------------------------


# imports
# -------
from flask import Flask

from .converters import ModelConverter
from .mixins import ModelMixin


# plugin
# ------
class Occam(object):
    """
    Plugin for updating flask functions to handle class-based URL
    routing.
    """

    def __init__(self, app=None, db=None):
        
        # arg mismatch
        if app is not None and \
           db is None and \
           not isinstance(app, Flask):
            self.init_db(app)
            app = None

        # proper spec
        if db is not None:
            self.init_db(db)
        
        # app is specified properly
        if app is not None:
            self.init_app(app)
        return

    def init_app(self, app):
        self.app = app
        self.app.config.setdefault('OCCAM_LOG_USER_FORMAT', 'user')
        self.app.url_map.converters['id'] = ModelConverter
        return

    def init_db(self, db):
        self.db = db
        self.db.Model.__bases__ += (ModelMixin,)
        return
