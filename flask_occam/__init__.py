# -*- coding: utf-8 -*-

__pkg__ = 'Flask-Occam'
__url__ = 'https://github.com/bprinty/Flask-Occam'
__info__ = 'Flask extension for simplifying REST API development.'
__author__ = 'Blake Printy'
__email__ = 'bprinty@gmail.com'
__version__ = '0.1.0'


from .mixins import ExampleMixin             ## noqa
from .plugin import Occam                    ## noqa
from .decorators import validate, optional   ## noqa
from .decorators import transactional
from .decorators import paginate
from .decorators import log
from .handlers import ActionHandler, QueryHandler
