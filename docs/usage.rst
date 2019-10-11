
Usage
=====

The sections below detail how to fully use this module, along with context for design decisions made during development of the plugin.


In the beginning ...
--------------------

There was only Flask. Well, really ... Werkzeug.

For context, let's use a toy Flask application to illustrate some of the principles throughout the documentation. First, we're going to define our application using normal Flask conventions. We're also going to highlight some of the potential boilerplate that this approach requires:

.. code-block:: python

    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from flask_occam import Occam


    app = Flask(__name__)
    app.config.from_object(Config)
    db = SQLAlchemy(app)


    class Item(db.Model):
        __tablename__ = 'item'

        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(255), nullable=False, unique=True, index=True)
        email = db.Column(db.String(255))


    @app.route('/items', methods=['GET'])
    def all_items():
        if request.method == 'GET':                    ## boilerplate
            items = db.session.query(Item).all()
            return jsonify([
                dict(id=x.id, name=x.name)
                for x in items
            ])

        elif request.method == 'POST':                 ## boilerplate
            email = request.json['email']              ## boilerplate
            if not re.match(email, r".+@.+"):          ## boilerplate
                raise BadRequest                       ## boilerplate
            item = Item(**request.json)
            db.session.add(item)
            db.session.commit()                        ## boilerplate
            return jsonify(
                id=item.id,
                name=item.name
            )


    @app.route('/items/<int:ident>', methods=['GET', 'PUT', 'DELETE'])
    def single_item(ident):
        item = db.session.query(Item)\                 ## boilerplate
                 .filter_by(id=ident).first()          ## boilerplate
        if not item:                                   ## boilerplate
            raise NotFound                             ## boilerplate
        
        if request.method == 'GET':                    ## boilerplate
            return jsonify(
                id=item.id,
                name=item.name
            )
        
        elif request.method == 'PUT':                  ## boilerplate
            for key, value in request.json.items():
                if key == 'email':                     ## boilerplate
                    if not re.match(value, r".+@.+"):  ## boilerplate
                        raise BadRequest               ## boilerplate
                setattr(item, key, value)
            db.session.commit()                        ## boilerplate
            return jsonify(
                id=item.id,
                name=item.name
            )

        elif request.method == 'DELETE':               ## boilerplate
            db.session.delete(item)
            db.session.commit()                        ## boilerplate
            return jsonfify(msg='Deleted item')


A Cleaner Approach
------------------

Now, let's use ``Flask-Occum`` to clean up some of the boilerplate: 

.. code-block:: python
    
    from wtforms import validators
    from flask_occum import Occum
    from flask_occum import transactional, validate, log, paginate

    # initialize plugin
    occum = Occum(app, db)

    # endpoints
    @app.route('/items')
    class Items(object):

        @paginate(limit=50, total=Item.count)
        def get(self, limit, offset):
            """
            GET /items
            """
            items = Item.all(limit=limit, offset=offset)
            return [x.json() for x in items], 200

        @validate(name=str)
        @transactional
        @log.info('Created new user with name {name}')
        def post(self):
            """
            POST /items
            """
            item = Item.create(**request.json)
            return item.json(), 201


    @app.route('/items/<id(Item):item>')
    class SingleItem(object):
        
        def get(self, item):
            """
            GET /items/:id
            """
            return item.json(), 200

        @validate(
            name=optional(str),
            url=optional(validators.URL())
        )
        @transactional
        @log.info('Changed metadata for item {item.name}')
        def put(self, item):
            """
            PUT /items/:id
            """
            item.update(**request.json)
            return item.json(), 200

        @transactional
        def delete(self, item):
            """
            DELETE /items/:id
            """
            item.delete()
            return jsonify(msg='Deleted item'), 204



As you can see above, a good deal of the original boilerplate was removed, and although there is a similar number of lines of code, the readability (and by extension maintainability) is much better. The Occam example also includes additional utilities like payload validation, request action logging, and automatic pagination, which the original example didn't provide (and would require a lot of code to produce).

Each of the utilities shown above are explained in greater detail throughout the documentation. This is example is mainly meant to give readers a *feel* for how application development changes with the extension.


Endpoint Documentation
----------------------

Another benefit of using a class-based approach to request processing is that it enables you to include clear and concise documentation for your endpoints in the docstrings for each request method. This allows developers to easily generate API documentation for their application using the sphinx ``autodoc`` functionality. Here's a docstring-ified version of the example provided in the overview section of the documentation:


.. code-block:: python

    @app.route('/items')
    class Items(object):

        @paginate(limit=50, total=Item.count)
        def get(self, limit, offset):
            """
            GET /items

            Query for existing item in application database.

            Parameters:
                limit (str): (optional) Return limit for query.
                offset (str): (optional) Offset for querying results.

            Response:
                List of item objects. See GET /items/:id for
                information on return payloads.

            Status:
                Success: 200 Created
                Missing: 404 Not Found
            """
            items = Item.all(limit=limit, offset=offset)
            return [x.json() for x in items], 200

        @validate(name=str)
        @transactional
        @log.info('Created new user {name}')
        def post(self):
            """
            POST /items

            Query for existing item in application database.

            Arguments:
                id (int): Identifier for item.

            Parameters:
                name (str): Name for item

            Response:
                id (int): Identifier for item.
                name (str): Item name.
                url (str): Item URL.

            Status:
                Success: 201 Created
                Missing: 404 Not Found
                Failure: 422 Invalid Request
            """
            item = Item.create(**request.json)
            return item.json(), 201


    @app.route('/items/<id(Item):item>')
    class SingleItem(object):
        
        def get(self, item):
            """
            GET /items/:id

            Query for existing item in application database.

            Arguments:
                id (int): Identifier for item.

            Response:
                id (int): Identifier for item.
                name (str): Item name.

            Status:
                Success: 200 OK
                Missing: 404 Not Found
            """
            return jsonify(id=item.id, name=item.name), 200

        @validate(
            name=optional(str),
            url=optional(validators.URL())
        )
        @transactional
        @log.info('Changed metadata for item {item.name}')
        def put(self, item):
            """
            PUT /items/:id

            Update existing item in application database.

            Arguments:
                id (int): Identifier for item.

            Parameters:
                name (str): (optional) Name for item 
                url (str): (optional) URL for item 

            Response:
                id (int): Identifier for item.
                name (str): Item name.
                url (str): Item url.

            Status:
                Success: 200 OK
                Missing: 404 Not Found
                Failure: 422 Invalid Request
            """
            item.update(**request.json)
            return item.json(), 200

        @transactional
        def delete(self, item):
            """
            DELETE /items/:id

            Delete existing item in application database.

            Arguments:
                id (int): Identifier for item.

            Status:
                Success: 204 No Content
                Missing: 404 Not Found
            """
            item.delete()
            return jsonify(msg='Deleted item'), 204


Nice, right? Defining your APIs like the above helps with code clarity, and forces developers to develop good habits when working on new endpoints. Sphinx can automatically generate html documentation from these docstrings using the ``autodoc`` extension. Here's an example of how to include auto-documentation for API handlers in your sphinx docs:

.. code-block:: python
    
    .. autoclass:: app.models.Item
       :members:

In addition, you can have Flask-Occum automatically serve REST-based documentation for your endpoints by enabling the ``OCCUM_DOCS_BLUEPRINT`` configuration option. With that blueprint, you can retrieve endpoint documentation via request:

..  code-block:: bash

    ~$ curl -X GET http://localhost:5000/docs/items/1
    <pre>
        GET /items/:id

        Query for existing item in application database.

        Arguments:
            id (int): Identifier for item.

        Response:
            id (int): Identifier for item.
            name (str): Item name.

        Status:
            Success: 200 OK
            Missing: 404 Not Found
    </pre>


Custom Request Handlers
-----------------------

Along with class-based request handling, you can also create custom classes for special endpoint handling. By default, Flask-Occum comes with two additional handlers:

* **ActionHandler** - Dispatch actions encoded in a URL (``POST /api/item/:id/:action``) to specific class methods. This is particularly useful for actions like ``archive`` or other model-specific functionality that needs to take place.
* **QueryHandler** - Dispatch nested sub-queries encoded in a URL (``GET /api/item/:id/:query``) to specific lass melthods. This is useful for queries like ``status`` or other model specific querying that needs to be available.

Here's an example of using the **ActionHandler** helper class for processing endpoints that submit specific server-side actions (**QueryHandler** uses a very similar API):

.. code-block:: python

    from flask_occum import ActionHandler
    
    @app.route('/items/<id(Item):item>/<action>')
    class ItemActions(ActionHandler):

        def archive(self, item):
            # code to archive item whenever
            # POST /items/:id/archive is submitted.
            return

        def unarchive(self, item):
            # code to unarchive item whenever
            # POST /items/:id/unarchive is submitted.
            return


URL Processors
--------------

Above, we alluded to a custom url processor that automatically queries for objects of class ``Item``. This section will cover that functionality with additional context.

Without this URL processor, querying for the item and checking if it exists creates boilerplate that permeates the entire codebase:

.. code-block:: python

    @app.route('/items/<int:ident>', methods=['GET'])
    def get_item(ident):
        item = db.session.query(Item)\                 ## boilerplate
                 .filter_by(id=ident).first()          ## boilerplate
        if not item:                                   ## boilerplate
            raise NotFound     
        return item.json()

With the URL processor, all of the querying and raising ``NotFound`` errors is automatically managed when a request comes in:

.. code-block:: python

    @app.route('/items/<id(Item):item>')
    def get_item(item):
        # the ``item`` argument is automatically transformed
        # into an ``Item`` object when an identifier is passed into
        # the URL like before 
        return item.json()

You can also do the same with any other object in the database. For example:

.. code-block:: python

    @app.route('/users/<id(User):user>/items/<id(Item):item>')
    def get_user_item(user, item):
        # Like before, ``user`` is a ``User`` object, and
        # ``item`` is an ``Item`` object.
        pass


Using Blueprints
----------------

Flask-Occum is designed for seamless integration with Flask, without changing much of how the app is configured or structured. The only Flask-y convention that needs to be slightly altered is how ``Blueprints`` are used.

Instead of:

.. code-block:: python

    from flask import Blueprint

    blueprint = Blueprint('blueprint_page', __name__, template_folder='templates'))

    @blueprint.route('/test')
    def test():
        pass

You just import ``Blueprint`` from ``flask_occam``:

.. code-block:: python

    from flask_occam import Blueprint

    blueprint = Blueprint('blueprint_page', __name__, template_folder='templates'))

    @blueprint.route('/test')
    def test():
        pass

Otherwise, the developer experience is the exact same.


Decorators
----------

``@validate``
+++++++++++++

With any large-scale web application, establishing a client-server contract for requests is incredibly important for keeping development organized and code clean. This extension provides a mechanism for ...


You could make payload validation as simple as types:

.. code-block:: python

    @api.route()
    @validate(
        string_param=str,
        int_param=int,
        float_param=float
    )
    def get_item():
        pass

You can also use this decorator on API functions, if you want to structure your application to dispatch to specific functions instead of including processing logic in the request handler. The ``@validate`` decorator will check all function arguments according to their expected contract:

.. code-block:: python

    @validate(
        string_param=str,
        int_param=int,
        float_param=float
    )
    def process_item(string_param, int_param, float_param):
        pass


When calling this function, if the inputs aren't specified according to the validation rules, and explicit error will be raised:

.. code-block:: python

    >>> process_item('test', 'test', 'test')
    Invalid arguments specified. Errors:

        INCLUDE ERRORS HERE




``@log``
++++++++




``@paginate``
+++++++++++++


``@transactional``
++++++++++++++++++


SQLAlchemy Extensions
---------------------


Configuration
-------------

The following configuration values exist for Flask-Authorize.
Flask-Authorize loads these values from your main Flask config which can
be populated in various ways. Note that some of those cannot be modified
after the database engine was created so make sure to configure as early as
possible and to not modify them at runtime.

Configuration Keys
++++++++++++++++++

A list of configuration keys currently understood by the extension:

.. tabularcolumns:: |p{6.5cm}|p{10cm}|

================================== =========================================
``PLUGIN_DEFAULT_VARIABLE``        A variable used in the plugin for
                                   something important.
================================== =========================================


Other Customizations
++++++++++++++++++++

As detailed in the `Overview <./overview.html>`_ section of the documentation,
the plugin can be customized with specific triggers. The following detail
what can be customized:

* ``option`` - An option for the plugin.

The code below details how you can override all of these configuration options:

.. code-block:: python

    from flask import Flask
    from flask_plugin import Plugin
    from werkzeug.exceptions import HTTPException

    app = Flask(__name__)
    plugin = Plugin(option=True)
    plugin.init_app(app)


For even more in-depth information on the module and the tools it provides, see the `API <./api.html>`_ section of the documentation.
