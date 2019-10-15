# -*- coding: utf-8 -*-
#
# Testing for pl
#
# ------------------------------------------------


# imports
# -------
from flask_occam import validate, optional
from wtforms import Form, StringField, PasswordField, validators

from .fixtures import ItemFactory


# validators
# ----------
@validate(
    one=str, two=float, three=optional(int),
    four=dict(
        foo=str,
        bar=str,
    ), five=[str]
)
def validate_types():
    pass

@validate(
    field=validators.BooleanField(),
    validator=StringField('Boolean', [
        validators.DataRequired(),
        validators.BooleanField(),
    ]),
    optional=optional(validators.BooleanField())
)
def validate_validators():
    pass


class ValidateForm(Form):
    boolean = StringField('Boolean', [
        validators.DataRequired(),
        validators.BooleanField(),
    ])

@validate(ValidateForm)
def validate_form():
    pass


# validation tests
# ----------------
class TestValidateHandler(object):

    def test_integration(self, client):
        item = ItemFactory.create(name='test')
        response = client.put('/items/{}'.format(item.id), json=dict(
            name=1,
            email='email@localhost.com'
        ))
        print(response.json)
        return

    # def test_validate_types(self, client, items):
    #     response = client.get('/items/{}'.format(items[0].id))
    #     assert response.status_code == 200
    #     assert response.json['name'] == items[0].name
    #     return

    # def test_query_new(self, client):
    #     # other open read permissions
    #     item = ItemFactory.create(name='test')
    #     response = client.get('/items/{}'.format(item.id))
    #     assert response.status_code == 200
    #     assert response.json['name'] == 'test'
    #     return
