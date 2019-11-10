# -*- coding: utf-8 -*-
#
# Testing for sqlalchemy extensions
#
# ------------------------------------------------


# imports
# -------
import os
from . import RESOURCES
from .fixtures import db, Item


# tests
# -----
class TestModelMixin(object):

    def test_utils(self, client, items):
        # json
        data = items[0].json()
        assert 'id' in data
        assert 'name' in data
        assert 'archived' in data

        # count
        count = Item.count()
        assert count > 0
        return

    def test_crud(self, client, items):
        # create
        item = Item.create(name='mixin-crud', archived=False).commit()

        # upsert
        items = Item.upsert([
            dict(name='mixin-crud', archived=True),
            dict(name='mixin-crud-new', archived=False)
        ])
        db.session.commit()
        updated = Item.find(name='mixin-crud')
        assert len(updated) == 1
        assert updated[0].archived is True
        created = Item.get(name='mixin-crud-new')
        assert created is not None

        # get
        ident = item.id
        item = Item.get(ident)
        assert item.name == 'mixin-crud'

        # get with alternate filter
        item = Item.get(name='mixin-crud')
        assert item.id == ident
        return

        # find
        items = Item.find(archived=False)
        assert len(items) > 3
        assert all([not x.archived for x in items])

        # update
        item = Item.get(name='mixin-crud')
        item.update(name='mixin-crud-update', archived=True).commit()
        updated = Item.get(name='mixin-crud-update')
        assert updated.id == item.id

        # delete
        item.delete()
        item = Item.get(item.id)
        assert item is None
        return

    def test_load(self, client):
        # simple action function
        def act(x):
            x.test = 'test'
            return

        # single model
        items = Item.load(os.path.join(RESOURCES, 'items.yml'), action=act)
        assert len(items) == 2
        assert isinstance(items[0], Item)
        assert items[0].id is not None
        assert items[0].test == 'test'

        # overwrite with different entrypoint
        items = db.load.items(os.path.join(RESOURCES, 'items.yml'), action=act)
        assert len(items) == 2
        assert isinstance(items[0], Item)
        assert items[0].id is not None
        assert items[0].test == 'test'

        # multiple models
        created = db.load(os.path.join(RESOURCES, 'seed.yml'), action=act)
        items = created['Item']
        assert len(items) == 2
        assert isinstance(items[0], Item)
        assert items[0].id is not None
        assert items[0].test == 'test'
        return
