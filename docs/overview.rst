
Overview
========

Flask-Occam is a Flask extension that is designed to help developers create simple and easy to maintain REST APIs. It is a lightweight abstraction on top of Flask's existing tools, designed to simplify API development and reduce the amount of boilerplate needed to perform common operations. Using this extension also promotes better code readability and maintainability during the application development lifecycle.

There are quite a few packages designed to simplify the process of writing REST APIs:

    * `Flask-Restplus <https://flask-restplus.readthedocs.io>`_
    * `Flask-Restful <https://flask-restful.readthedocs.io>`_
    * `Flask-API <https://www.flaskapi.org/>`_
    * `Flask-Restless <https://flask-restless.readthedocs.io>`_

And all make different assumptions about how developers want to structure their APIs. This package is yet another take at solving the same problem, resulting in a slightly different development experience when working with Flask applications. The developers of this package recommend you check out these alternatives along with Flask-Occam to see if they fit your needs better.


A Minimal Application
---------------------

Setting up the flask application with extensions:

.. code-block:: python

    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    from flask_occam import Occam

    app = Flask(__name__)
    app.config.from_object(Config)
    db = SQLAlchemy(app)
    occam = Occam(app, db)


The following is a minimal application highlighting most of the major features provided by the extension:

.. code-block:: python

    from wtforms import validators
    from flask_occam import transactional, validate, paginate, log, optional

    # models
    class Item(db.Model):
        __tablename__ = 'item'

        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(255), nullable=False, unique=True, index=True)
        url = db.Column(db.String(255))

        def json(self):
            return dict(
                id=self.id,
                name=self.name,
                url=self.url
            )


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


There's quite a bit to unpack from the application detailed above, including:

    * Facilities for automatically resolving model identifiers into objects via url converters.
    * Automatic pagination (via response header) for requests.
    * Automatic database transaction support for endpoint handlers.
    * Tools for simpler logging of requests or API methods.
    * Automatic payload validation (with support for WTForms validators).
    * SQLAlchemy extensions for CRUD operations on models (providing a simpler API).


For more in-depth discussion on these (and more) topics, design considerations, and how to fully utilize the plugin, see the `User Guide <./usage.html>`_.
