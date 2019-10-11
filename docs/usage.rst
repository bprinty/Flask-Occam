
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



As you can see above, ...


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

In addition to request handling via classes, you can also create custom classes for special endpoint handling. By default, Flask-Occum comes with two additional handlers:

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

Above, we alluded to a custom url processor that automatically queries for ...


Using Blueprints
----------------

Flask-Occum is designed for seamless integration with Flask, without changing much of how the app is configured or structured.

...

Decorators
----------

``@validate``
+++++++++++++

With any large-scale web application, establishing a client-server contract for requests is incredibly important for keeping development organized and code clean. This extension provides a mechanism for ...


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
