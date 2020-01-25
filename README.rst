
|Build status| |Code coverage| |Maintenance yes| |GitHub license| |Documentation Status|

.. |Build status| image:: https://travis-ci.com/bprinty/Flask-Occam.png?branch=master
   :target: https://travis-ci.com/bprinty/Flask-Occam

.. |Code coverage| image:: https://codecov.io/gh/bprinty/Flask-Occam/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/bprinty/Flask-Occam

.. |Maintenance yes| image:: https://img.shields.io/badge/Maintained%3F-yes-green.svg
   :target: https://GitHub.com/Naereen/StrapDown.js/graphs/commit-activity

.. |GitHub license| image:: https://img.shields.io/github/license/Naereen/StrapDown.js.svg
   :target: https://github.com/bprinty/Flask-Occam/blob/master/LICENSE

.. |Documentation Status| image:: https://readthedocs.org/projects/flask-occam/badge/?version=latest
   :target: http://flask-occam.readthedocs.io/?badge=latest


============================
Flask-Occam
============================

Flask-Occam is a Flask extension that is designed to help developers create simple and easy to maintain REST APIs. It is a lightweight abstraction on top of Flask's existing tools, designed to simplify API development and reduce the amount of boilerplate needed to perform common operations. Using this extension also promotes better code readability and maintainability during the application development lifecycle.


Installation
============

To install the latest stable release via pip, run:

.. code-block:: bash

    $ pip install Flask-Occam


Alternatively with easy_install, run:

.. code-block:: bash

    $ easy_install Flask-Occam


To install the bleeding-edge version of the project (not recommended):

.. code-block:: bash

    $ git clone http://github.com/bprinty/Flask-Occam.git
    $ cd Flask-Occam
    $ python setup.py install


Usage
=====

Below is a minimal application configured to take advantage of some of the extension's core features:

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


Documentation
=============

For more detailed documentation, see the `Docs <https://Flask-Occam.readthedocs.io/en/latest/>`_.


Questions/Feedback
==================

File an issue in the `GitHub issue tracker <https://github.com/bprinty/Flask-Occam/issues>`_.
