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
from flask_occam import Occam, ActionHandler, transactional, validate
from wtforms import validators, StringField

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
app.config.from_object(Config)
db = SQLAlchemy(app)
occam = Occam(app)


# validators
# ----------
email = StringField('Email Address', [
    validators.DataRequired(),
    validators.Email(),
])


# endpoints
# ---------
@app.route('/items')
class Items(object):

    def get(self):
        items = Item.all()
        return jsonify([dict(id=x.id, name=x.name) for x in items]), 200

    @transactional
    def post(self):
        item = Item.create(**request.json)
        return jsonify(id=item.id, name=item.name), 200


@app.route('/items/<id(Item):item>')
class Item(object):
    def get(self, item):
        return jsonify(id=item.id, name=item.name), 200

    @validate(
        name=str,
        email=validators.email
    )
    @transactional
    def put(self, item):
        item.update(**request.json)
        return jsonify(id=item.id, name=item.name), 200

    @transactional
    def delete(self, item):
        item.delete()
        return


 @app.route('items/<id(Item):item>/<action>')
 class Item(ActionHandler):

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
    email = db.Column(db.String(255))
    archived = db.Column(db.Boolean)


# factories
# ---------
class ItemFactory(factory.alchemy.SQLAlchemyModelFactory):

    id = factory.Sequence(lambda x: x + 100)
    name = factory.Faker('name')

    class Meta:
        model = Item
        sqlalchemy_session = db.session


# fixtures
# --------
@pytest.fixture(scope='session')
def items(client):

    # roles
    items = [
        ItemFactory.create(name='one'),
        ItemFactory.create(name='two'),
        ItemFactory.create(name='three')
    ]

    yield items

    return
