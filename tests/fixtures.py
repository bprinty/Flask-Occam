# -*- coding: utf-8 -*-
#
# Fixtures for administration.
#
# ------------------------------------------------


# imports
# -------
import pytest
import factory
from flask import Flask, request, jsonify
from werkzeug.exceptions import NotFound
from flask_sqlalchemy import SQLAlchemy
from flask_occam import Occam, ActionHandler, transactional, validate, optional
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


app = Flask(__name__)
print(app.route)
app.config.from_object(Config)
db = SQLAlchemy(app)
occam = Occam(app, db)
print(app.route)


# validators
# ----------
boolean = BooleanField('Boolean', [
    validators.DataRequired(),
])


# endpoints
# ---------
@app.route('/items')
class Items(object):

    def get(self):
        items = Item.all()
        return jsonify([dict(id=x.id, name=x.name) for x in items]), 200

    @validate(name=str)
    @transactional
    def post(self):
        item = Item.create(**request.json)
        return jsonify(id=item.id, name=item.name), 201


@app.route('/items/<id(Item):item>')
class ItemUpdates(object):
    def get(self, item):
        return jsonify(id=item.id, name=item.name), 200

    @validate(
        name=optional(str),
        ok=optional(boolean)
    )
    @transactional
    def put(self, item):
        item.update(**request.json)
        return jsonify(id=item.id, name=item.name), 200

    @transactional
    def delete(self, item):
        item.delete()
        return jsonify(msg='Deleted item'), 204


@app.route('/items/<id(Item):item>/<action>')
class ItemActions(ActionHandler):

    @transactional
    def archive(self):
        item.archived = True
        return

    @transactional
    def unarchive(self):
        item.archived = False
        return


# models
# ------
class Item(db.Model):
    __tablename__ = 'item'

    # basic
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    ok = db.Column(db.Boolean)


# factories
# ---------
class ItemFactory(factory.alchemy.SQLAlchemyModelFactory):

    id = factory.Sequence(lambda x: x + 100)
    name = factory.Faker('name')
    ok = True

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
