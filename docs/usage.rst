
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

    # initialize plugin
    occum = Occum(app, db)

    # endpoints
    @app.route('/items')
    class Items:
        def get(self):
            return jsonify([
                dict(id=x.id, name=x.name)
                for x in Item.all()
            ])

        @validate(
            name=str
            email=email=validators.Email()
        )
        @transactional
        def post(self):
            item = Item.create(**request.json
            return jsonify(id=item.id, name=item.name)


    @app.route('/items/<id(Item):item>')
    class Item:
        def get(self, item):
            return jsonify(
                id=item.id,
                name=item.name
            )

        @validate(
            name=str,
            email=validators.Email()
        )
        @transactional
        def put(self, item):
            item.update(**request.json)
            return jsonify(
                id=item.id,
                name=item.name
            )

        @transactional
        def delete(self, item):
            item.delete()
            return jsonify(msg='Deleted user')



As you can see above, ...


Endpoint Documentation
----------------------

Another benefit of using a class-based approach to request processing is ...


.. code-block:: python

    @app.route('/items/<id(Item):item>')
    class Item:
        def get(self, item):
            """
            GET /items/:id

            Query for existing items in application database.

            Arguments:
                id (int): Identifier for user.

            Response:
                id (int): Identifier for item.
                name (str): Item name.
                email (str): Item email.

            Status:
                Success: 200 Created
                Missing: 404 Not Found
            """
            return jsonify(
                id=item.id,
                name=item.name
            )


... talk about sphinx support


Custom Request Handlers
-----------------------


URL Processors
--------------

Above, we alluded to a custom url processor that automatically queries for ...


Decorators
----------

``@validate``
+++++++++++++


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
