
Overview
========

Flask-Occam is a Flask extension that is designed to help developers create simple and easy to maintain REST APIs. It is a lightweight abstraction on top of Flask's existing tools, designed to simplify API development and reduce the amount of boilerplate needed to do common operations. Using this extension also promotes better code readability and maintainability during the application development lifecycle.

There are quite a few packages designed to simplify the process of writing REST APIs:

    * `Flask-Restplus <https://flask-restplus.readthedocs.io>`_
    * `Flask-Restful <https://flask-restful.readthedocs.io>`_
    * `Flask-API <https://www.flaskapi.org/>`_
    * `Flask-Restless <https://flask-restless.readthedocs.io>`_

And all make different assumptions about how developers want to structure their APIs. This package is yet another take at solving the same problem, resulting in a slightly different development experience when working with Flask applications. The developers of this package recommend you check out these alternatives to see if they fit your needs better.


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

    # models
    class Item(db.Model):
        __tablename__ = 'item'

        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(255), nullable=False, unique=True, index=True)
        email = db.Column(db.String(255))


    # endpoints
    @app.route('/items')
    class Items(object):
        """
        With this extension, you can set up your routing in a
        class-based style, similar to Tornado, or other Flask plugins
        for REST API management.
        """

        @paginate(limit=50, total=Item.count)
        def get(self, limit, offset):
            """
            The `paginate` decorator automatically includes
            pagination information in the header for the response,
            depending on the length of what this method returns.
            """
            items = Item.all(limit=limit, offset=offset)
            return jsonify([dict(id=x.id, name=x.name) for x in items]), 200

    @app.route('/items/<id(Item):item>')
    class SingleItem(object):
        
        def get(self, item):
            """
            The `id` url processor in @app.route automatically
            searches for an `Item` object and raises NotFound
            if it doesn't exist. An existing result is returned
            as the `item` argument.
            """
            return jsonify(id=item.id, name=item.name), 200

        @validate(
            name=str,
            email=validators.Email()
        )
        @transactional
        @log.info('Changed metadata for item {item.name}')
        def put(self, item):
            """
            The `validate` decorator automatically does payload
            validation using the specified validators.

            The `transactional` decorator automatically commits a 
            database session once the response is successfully
            created, rolling back the session if there was an
            error.

            The `log` decorator automatically writes to
            the application log with string formatting from the
            method arguments.
            """
            item.update(**request.json)
            return jsonify(id=item.id, name=item.name), 200


There's quite a bit to unpack from the application detailed above, including:

    * Facilities for automatically querying models via url converters.
    * Automatic pagination (in response header) for requests.
    * Automatic database transaction support for endpoint handlers.
    * Tools for simpler logging of requests or API methods.
    * Automatic payload validation (with support for WTForms validators).

For more in-depth discussion on these (and more) topics, design considerations, and how to fully utilize the plugin, see the `User Guide <./usage.html>`_.
