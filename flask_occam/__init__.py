# -*- coding: utf-8 -*-

__pkg__ = 'Flask-Occam'
__url__ = 'https://github.com/bprinty/Flask-Occam'
__info__ = 'Flask extension for simplifying REST API development.'
__author__ = 'Blake Printy'
__email__ = 'bprinty@gmail.com'
__version__ = '0.1.8'


from .plugin import Occam, Blueprint         ## noqa

from .decorators import optional             ## noqa
from .decorators import validate             ## noqa
from .decorators import transactional        ## noqa
from .decorators import paginate             ## noqa
from .decorators import log                  ## noqa

from .handlers import ActionHandler          ## noqa
from .handlers import QueryHandler           ## noqa
from .handlers import UpdateHandler          ## noqa

from .errors import ValidationError          ## noqa
