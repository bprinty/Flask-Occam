
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

In addition, you can have Flask-Occum automatically serve REST-based documentation for your endpoints by enabling the ``OCCAM_AUTODOC_ENABLED`` configuration option. With that configuration option set to ``True``, you can retrieve endpoint documentation via request:

..  code-block:: bash

    ~$ curl -X GET http://localhost:5000/docs/items/:id
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

Above, we alluded to a custom url processor that automatically queries for objects of class ``Item``. Without this URL processor, querying for the item and checking if it exists creates boilerplate that permeates the entire codebase:

.. code-block:: python

    @app.route('/items/<int:ident>', methods=['GET'])
    def get_item(ident):
        item = db.session.query(Item)\                 ## boilerplate
                 .filter_by(id=ident).first()          ## boilerplate
        if not item:                                   ## boilerplate
            raise NotFound     
        return item.json()


With the URL processor included with this extension, all of the querying and raising ``NotFound`` errors is automatically managed when a request comes in:

.. code-block:: python

    @app.route('/items/<id(Item):item>')
    def get_item(item):
        return item.json()

When a request comes through, the ``item`` argument is automatically transformed into an ``Item`` object by the url processor, removing the need to always query the database and raise relevant errors. You can also do the same with any other object in the database. For example:

.. code-block:: python

    @app.route('/users/<id(User):user>/items/<id(Item):item>')
    def get_user_item(user, item):
        pass

Like before, ``user`` is transformed into is a ``User`` object, and ``item`` is transformed into an ``Item`` object. If neither object exists, a ``NotFound`` error will be raised.


Using Blueprints
----------------

Flask-Occum is designed for seamlessly integrating with Flask, without changing much of how the app is configured or structured. The only Flask-y convention that needs to be slightly altered is how ``Blueprints`` are used.

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

With any large-scale web application, establishing a client-server contract for requests is incredibly important for keeping development organized and code clean. This extension provides a mechanism for defining endpoint contracts in a declarative way, which increases developer awareness of what's happening in the application, and reduces the need for boilerplate code to validate payload data.

With the ``@validate`` decorator, you could make payload validation as simple as built-in types:

.. code-block:: python

    @api.route('/items', methods=['POST'])
    @validate(
        string_param=str,
        int_param=int,
        float_param=float
    )
    def create_item():
        pass

You can also use this decorator on API functions, if you want to structure your application so that request handling is dispatched to API functions. The ``@validate`` decorator will check all function arguments according to their expected contract:

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

    ValueError: Invalid arguments specified.

    Errors:

      float_param:
        - Invalid type. Expecting `<class 'float'>`.
      int_param:
        - Invalid type. Expecting `<class 'int'>`.


In addition to supporting built-in types, the ``@validate`` decorator also supports validators from the `WTForms <https://wtforms.readthedocs.io/en/stable/validators.html>`_ library. For example, to create custom validators for an email and password (with confirmation), you can do something like the following:

.. code-block:: python

    from wtforms import Form, StringField, PasswordField, validators

    # defining validators
    email = StringField('Email Address', [
        validators.DataRequired(),
        validators.Email(),
    ])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.Length(min=4, max=25),
        validators.EqualTo('confirm', message='Passwords must match.')
    ])
    confirm = PasswordField('Confirmation')

    # endpoint
    @validate(
        email=email,
        password=password,
        confirm=confirm
    )
    @app.route('/login', methods=['GET'])
    def login():
        pass


In this example, whenever the ``/login`` endpoint is hit with a payload, the ``@validate`` decorator will automatically check if the data contains a valid email, and a password between 4 and 25 characters with a matching confirmation. 

Finally, if you want to configure your form object separately, you can do so. Here's an example of using the ``@validate`` decorator with a ``Form`` object directly:

.. code-block:: python

    from wtforms import Form

    # form
    class LoginForm(Form):
        email = StringField('Email Address', [
            validators.DataRequired(),
            validators.Email(),
        ])
        password = PasswordField('Password', [
            validators.DataRequired(),
            validators.Length(min=4, max=25),
            validators.EqualTo('confirm', message='Passwords must match.')
        ])
        confirm = PasswordField('Confirmation')

    # endpoint
    @validate(LoginForm)
    @app.route('/login', methods=['GET'])
    def login():
        pass


And to really hammer in the point, here is an example with mixed types and validators, with nested validation:

.. code-block:: python

    from wtforms.validators import Email, NumberRange
    
    @validate(
        email=Email(),             # email address
        name=str,                  # string
        tags=optional([str]),      # optional list of strings
        info=dict(                 # dictionary with nested validation
            age=NumberRange(       # 0 < age < 120
                min=0,
                max=120
            ),
            nickname=optional(str) # optional string
        )
    )
    def create_user(email, name, tags=None, info=None):
        pass


As you can see above, optional validation can occur for parameters wrapped in with the ``optional`` function. This is useful for ``PUT`` requests where updates don't need to happen on every field during every request. To explicitly make all parameters in the validation block optional, you can use the ``@validate.optional`` decorator:

.. code-block:: python

    @validate.optional(
        name=str,        # optional string
        tags=[str],      # optional list of strings
    )
    def update_user(name=None, tags=None):
        pass


This will only perform validation if known keys are specified in the request payload.


``@log``
++++++++

Logging in flask is already dead-simple, and this decorator mainly just provides an orthogonal route to doing logging in a consistent way. With the ``@log`` decorator from this package, you can define high-level logging after an endpoint or API method is called, specifying the log information to the decorator:

.. code-block:: python

    @log.info('my_function was called')
    def my_function():
        pass


In addition, strings in logging are automatically formatted with function arguments and payload arguments, so you can include string formatting with keywords in the log directly:

.. code-block:: python

    @log.info("Created item with name {name}")
    def create_item(name):
        pass


If your application is configured to use ``Flask-Login``, you can include user information in the logs as well:

.. code-block:: python

    @log.debug("User {user.name} created item with name {name}")
    def create_item(name):
        pass



``@paginate``
+++++++++++++

Applications serving lots of data often need a mechanism for paginating requests, so that the server doesn't get overloaded with bulk requests. This plugin provides a decorator to automatically provide pagination information in the response header:

.. code-block:: python

    @app.route("/items", methods=['GET'])
    @paginate(limit=50, total=Item.count)
    def get_items():
        items = Item.all(
            limit=request.args['limit'],
            offset=request.args['offset']
        )
        return [item.json() for item in items], 200

Request arguments added automatically by the ``@paginate`` decorator are as follows:

    * **limit** - The number of elements to paginate by.
    * **total** - The total number of elements available in the database. This can be either a number or a ``callable``.


Behind the scenes, this decorator will automatically set ``limit`` and ``offset`` request arguments, which developers can use when constructing a response. In the example above, if a request is made to ``/items``, ``limit`` will be set to 50, and ``offset`` will be set to 0. Response headers detailing the next request to make for more data will also automatically be set. See below for an example:

.. code-block:: bash

    ~$ curl -v -X GET http://localhost:5000/items
    > GET /items HTTP/1.1
    > User-Agent: curl/7.16.4 (i386-apple-darwin9.0) libcurl/7.16.4 OpenSSL/0.9.7l zlib/1.2.3
    > Accept: */*
    > 
    < HTTP/1.1 206 Partial Content
    < Content-Type: application/json; charset=UTF-8
    < X-Total-Count: 540
    < Link: <http://localhost:5000/items?limit=50&offset=51>; rel="next"
            <http://localhost:5000/items?limit=50&offset=501>; rel="last"
    < 
    [
        {'id': 1, 'name': 'one'},
        {'id': 2, 'name': 'two'}
        ...
    ]

In addition to the ``X-Total-Count`` and ``Link`` header values, the decorator will also change the response code to ``206 Partial Content`` if the request is not the last request for retrieving data.   


``@transactional``
++++++++++++++++++

The ``@transactional`` decorator is a tool for automatically managing transactions as requests are processed. If the application produces any error during a response, ``db.session.rollback()`` is automatically called before the request finishes processing:

.. code-block:: python

    @transactional
    def do_something():
        item = Item(name='test')
        db.session.add(item)

        item.url = 1 / 0  ## raises error, forcing a database rollback
        return


After the function executes, the flushed changes will also automatically be committed via ``db.session.commit()``. In total, the decorator doesn't provide much on top of what SQLAlchemy already provides, but gives developers a nice wrapper to keep their transactional code clean.


SQLAlchemy Extensions
---------------------

Similarly to the ``@log`` decorator, this module simply provides an orthogonal mechanism for interacting with the database outside of heavily utilizing ``db.session`` from ``Flask-SQLAlchemy``. However, this type of usage is in no way required, and you can continue to use ``db.session`` if that's the way you prefer to interact with the database. Here are some examples of CRUD operations using the extensions:

.. code-block:: python


    ## Create 
    # without
    item = Item(
        name='test',
        url='http://localhost:5000/items/1'
    )
    db.session.add(item)

    # with
    item = Item.create(
        name='test'
        url='http://localhost:5000/items/1'
    )

    ## Read
    # without
    item = db.session.query(Item).filter_by(id=1).first()
    items = db.session.query(Item).limit(5).offset(5).all()

    # with
    item = Item.get(1)
    items = Item.all(limit=5, offset=5)

    ## Update
    # without
    item.name = 'test2'
    item.url = None
    db.session.add(item)

    # with
    item.update(name='test2', url=None)

    ## Delete 
    # without
    db.session.delete(item)

    # with
    item.delete()


To enable these extensions when using the plugin, developers must instantiate the ``Flask-Occum`` with a reference to the ``Flask-SQLAlchemy`` plugin. Here's an example of doing this:

.. code-block:: python

    app = Flask(__name__)
    app.config.from_object(Config)
    db = SQLAlchemy(app)
    occam = Occam(app, db)


However, as previously stated, passing in the Flask-SQLAlchemy plugin instance is not required to use the tools in this extension. 


Configuration
-------------

The following configuration values exist for Flask-Occam.
Flask-Occam loads these values from your main Flask config which can
be populated in various ways. Note that some of those cannot be modified
after the database engine was created so make sure to configure as early as
possible and to not modify them at runtime.

Configuration Keys
++++++++++++++++++

A list of configuration keys currently understood by the extension:

.. tabularcolumns:: |p{6.5cm}|p{10cm}|

================================== =========================================
``OCCAM_LOG_USER_FORMAT``          The name of the ``current_user`` available
                                   when using the ``@log`` decorator. Defaults
                                   to ``user``.

``OCCAM_AUTODOC_ENABLED``          Whether or not to enable the api auto-
                                   documentation feature.

``OCCAM_AUTODOC_PREFIX``           URL Prefix for auto-documentation entpoint.

``OCCAM_LOG_USER_FORMAT``          Name name for {user} formatter in @log
                                   decorator.

``OCCAM_LOG_DEFAULT_LEVEL``        Default log level for @log decorator.
================================== =========================================


.. Other Customizations
.. ++++++++++++++++++++

.. As detailed in the `Overview <./overview.html>`_ section of the documentation,
.. the plugin can be customized with specific triggers. The following detail
.. what can be customized:

.. * ``option`` - An option for the plugin.

.. The code below details how you can override all of these configuration options:

.. .. code-block:: python

..     from flask import Flask
..     from flask_occam import Occam

..     app = Flask(__name__)
..     occam = Occam(option=True)
..     occam.init_app(app)

..     # or, with model extensions
..     from flask_sqlalchemy import SQLAlchemy

..     app = Flask(__name__)
..     db = SQLAlchemy()
..     occam = Occam(db)
..     occam.init_app(app)


.. For even more in-depth information on the module and the tools it provides, see the `API <./api.html>`_ section of the documentation.
