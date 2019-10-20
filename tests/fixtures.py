# -*- coding: utf-8 -*-
#
# Fixtures for administration.
#
# ------------------------------------------------


# imports
# -------
import io
import pytest
import factory
import logging
from flask import Flask, request, jsonify
from werkzeug.exceptions import NotFound
from flask_sqlalchemy import SQLAlchemy
from flask_occam import Occam, ActionHandler, transactional, validate, optional, paginate
from wtforms import validators, BooleanField

from . import SANDBOX


# application
# -----------
class Config(object):
    ENV = 'testing'
    TESTING = True
    SQLALCHEMY_ECHO = False
    PROPAGATE_EXCEPTIONS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///{}/app.db'.format(SANDBOX)
    PLUGIN_DEFAULT_VARIABLE = True


logs = io.StringIO()
logger = logging.getLogger()
logger.setLevel(logging.INFO)
capture = logging.StreamHandler(logs)
app = Flask(__name__)
logger.addHandler(capture)
app.logger.addHandler(capture)
app.config.from_object(Config)
db = SQLAlchemy(app)
occam = Occam(app, db)


# validators
# ----------
boolean = BooleanField('Boolean', [
    validators.DataRequired(),
])


# endpoints
# ---------
@app.route('/items')
class Items(object):

    @paginate(limit=2, total=lambda: Item.count())
    def get(self):
        items = Item.all(
            limit=request.args['limit'],
            offset=request.args['offset']
        )
        return [x.json() for x in items], 200

    @validate(name=str)
    @transactional
    def post(self):
        item = Item.create(**request.json)
        return item.json(), 201


@app.route('/items/<id(Item):item>')
class ItemUpdates(object):
    def get(self, item):
        return item.json(), 200

    @validate(
        name=optional(str),
    )
    @transactional
    def put(self, item):
        item.update(**request.json)
        return item.json(), 200

    @transactional
    def delete(self, item):
        item.delete()
        return jsonify(msg='Deleted item'), 204


# models
# ------
class Item(db.Model):
    __tablename__ = 'item'

    # basic
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    archived = db.Column(db.Boolean)

    def json(self):
        return dict(
            id=self.id,
            name=self.name,
            archived=self.archived
        )


# factories
# ---------
class ItemFactory(factory.alchemy.SQLAlchemyModelFactory):

    id = factory.Sequence(lambda x: x + 100)
    name = factory.Faker('name')
    archived = False

    class Meta:
        model = Item
        sqlalchemy_session = db.session


# fixtures
# --------
@pytest.fixture(scope='session')
def items(client):

    # roles
    items = [
        ItemFactory.create(id=1, name='one'),
        ItemFactory.create(id=2, name='two'),
        ItemFactory.create(id=3, name='three')
    ]

    yield items

    return
