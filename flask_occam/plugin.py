# -*- coding: utf-8 -*-
#
# Plugin Setup
#
# ------------------------------------------------


# imports
# -------
from .converters import ModelConverter


# plugin
# ------
class Occam(object):
    """
    Plugin for updating flask functions to handle class-based URL
    routing.
    """

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)
        return

    def init_app(self, app):
        self.app = app
        self.app.config.setdefault('OCCAM_LOG_USER_FORMAT', 'user')
        self.app.url_map.converters['id'] = ModelConverter
        return
