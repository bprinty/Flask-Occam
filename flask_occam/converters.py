
# imports
# -------
import re
from werkzeug.routing import BaseConverter
from werkzeug.exceptions import NotFound


# helpers
# -------
MODELS = dict()


def gather_models():
    """
    Inspect sqlalchemy models from current context and set global
    dictionary to be used in url conversion.
    """
    global MODELS

    from flask import current_app, has_app_context
    if not has_app_context():
        return
    if 'sqlalchemy' not in current_app.extensions:
        return

    # inspect current models and add to map
    db = current_app.extensions['sqlalchemy'].db
    for cls in db.Model._decl_class_registry.values():
        if isinstance(cls, type) and issubclass(cls, db.Model):

            # class name
            MODELS[cls.__name__] = cls

            # lowercase name
            MODELS[cls.__name__.lower()] = cls

            # snake_case name
            words = re.findall(r'([A-Z][0-9a-z]+)', cls.__name__)
            if len(words) > 1:
                alias = '_'.join(map(lambda x: x.lower(), words))
                MODELS[alias] = cls
    return


# converters
# ----------
class ModelConverter(BaseConverter):
    """
    For url inputs containing a model identifier, look
    up the model and return the object.

    This method simplifies a lot of the boilerplate needed
    to do model look ups in REST apis.

    Examples:

        .. code-block:: python

            @app.route('/users/<id(User):user>')
            def get_user(user):
                return jsonify(user.json())

    In addition, this class can be inherited and used
    for other custom parameter url converters. For instance,
    here is how you might use it to create a name converter:

    .. code-block:: python

        class NameConverter(ModelConverter):
            __param__ = 'name'

        app.url_map.converters['name'] = NameConverter

        # ... handlers ...

        @app.route('/users/<name(User):user>')
        def get_user(user):
            return jsonify(user.json())

    """
    __param__ = 'id'

    def __init__(self, map, model):
        self.model = model
        return

    @property
    def models(self):
        global MODELS
        if not MODELS:
            gather_models()
        return MODELS

    def to_python(self, value):
        mapper = self.models

        # make sure model exists
        if self.model not in mapper:
            raise AssertionError(
                'Specified model `{}` in url converter '
                'not part of application models.'.format(self.model))

        # set up class for conversion
        cls = mapper[self.model]

        # search for the object
        model = cls.get(**{self.__param__: value})
        if model is None:
            raise NotFound

        return model

    def to_url(self, value):
        return BaseConverter.to_url(getattr(value, self.__param__))
