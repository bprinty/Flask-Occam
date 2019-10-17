# -*- coding: utf-8 -*-
#
# Testing for pl
#
# ------------------------------------------------


# imports
# -------
import pytest
from .fixtures import ItemFactory


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
        item = ItemFactory.create(name='update')
        
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
        item = ItemFactory.create(name='delete')

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
