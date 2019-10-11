# -*- coding: utf-8 -*-
#
# Custom exceptions used throughout application
#
# ------------------------------------------------


# imports
# -------
from werkzeug.exceptions import HTTPException
from flask import jsonify


# errors
# ------
class ValidationError(HTTPException):
    """
    Custom error handler to manage request
    validation reporting.

    Args:
        message (str): String with error message.
        errors (dict): Dictionary with validation errors.
    """
    code = 422
    description = 'Unprocessable Entity'

    def __init__(self, message=None, errors=None):
        self.message = message if message is not None else self.description
        self.errors = errors
        return

    @staticmethod
    def handler(error):
        return jsonify({
            'msg': error.message,
            'errors': error.errors
        }), error.code
