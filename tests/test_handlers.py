# -*- coding: utf-8 -*-
#
# Testing for url handling.
#
# ------------------------------------------------


# imports
# -------
import pytest
from flask import jsonify, request

from flask_occam import transactional, validate, ActionHandler, QueryHandler, UpdateHandler
from .fixtures import app, Item


# handlers
# --------
@app.route('/items/<id(Item):item>/<action>')
class ItemActions(ActionHandler):

    @transactional
    def archive(self, item):
        item.archived = True
        return jsonify(msg='Archived item'), 204

    @transactional
    def unarchive(self, item):
        item.archived = False
        return jsonify(msg='Unarchived item'), 204


@app.route('/items/<id(Item):item>/<resource>')
class ItemPropertyUpdates(UpdateHandler):

    @validate(data=str)
    @transactional
    def name(self, item):
        item.name = request.json['data']
        return jsonify(msg='Updated item name'), 204


@app.route('/items/<id(Item):item>/<query>')
class ItemQueries(QueryHandler):

    def status(self, item):
        return jsonify(archived=item.archived), 200


@app.route('/items/check/<check>')
class ItemCheck(object):
    def get(self, check):
        item = Item.get(id=check)
        if item is None:
            raise NotFound
        return jsonify(msg='Found Item'), 200


# tests
# -----
class TestCRUD(object):

    def test_create(self, client, items):
        # create it
        response = client.post('/items', json=dict(
            name='create'
        ))
        assert response.status_code == 201
        assert response.json['name'] == 'create'

        # read it back
        response = client.get('/items/{}'.format(response.json['id']))
        assert response.status_code == 200
        assert response.json['name'] == 'create'
        return

    def test_read(self, client, items):
        response = client.get('/items/{}'.format(items[0].id))
        assert response.status_code == 200
        assert response.json['name'] == items[0].name
        return

    def test_update(self, client):
        item = Item.create(name='update').commit()

        # update it
        response = client.put('/items/{}'.format(item.id), json=dict(
            name='not update'
        ))
        assert response.status_code == 200
        assert response.json['name'] == 'not update'

        # read it back
        response = client.get('/items/{}'.format(item.id))
        assert response.status_code == 200
        assert response.json['name'] == 'not update'
        return

    def test_delete(self, client):
        item = Item.create(name='delete').commit()

        # make sure it's there
        response = client.get('/items/{}'.format(item.id))
        assert response.status_code == 200
        assert response.json['name'] == 'delete'

        # drop it
        response = client.delete('/items/{}'.format(item.id))
        assert response.status_code == 204

        # check if it's still there
        response = client.get('/items/{}'.format(item.id))
        assert response.status_code == 404
        return


class TestHandlers(object):

    def test_action_handler(self, client, items):
        response = client.get('/items/{}'.format(items[0].id))
        assert response.json['archived'] is False

        response = client.post('/items/{}/archive'.format(items[0].id))
        assert response.status_code == 204

        response = client.get('/items/{}'.format(items[0].id))
        assert response.json['archived'] is True
        return

    def test_query_handler(self, client, items):
        response = client.get('/items/{}/status'.format(items[1].id))
        assert response.status_code == 200
        assert response.json['archived'] is False
        return

    def test_update_handler(self, client, items):
        item = Item.create(name='handler-update').commit()

        # update it
        response = client.put('/items/{}/name'.format(item.id), json=dict(
            data='not handler update'
        ))
        assert response.status_code == 204

        # read it back
        response = client.get('/items/{}'.format(item.id))
        assert response.status_code == 200
        assert response.json['name'] == 'not handler update'
        return

    def test_param_handler(self, client, items):
        response = client.get('/items/check/1')
        assert response.status_code == 200
        return


class TestAutoDocumentation(object):

    def test_get_doc(self, client, items):
        response = client.get('/docs/items')
        assert response.status_code == 200
        assert 'testing auto documentation' in response.data.decode('utf-8')

        response = client.get('/docs/items/1')
        assert response.status_code == 204
        return
