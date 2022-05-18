"""
Authentication Setup
"""
import os
from warnings import warn

from flask_httpauth import HTTPTokenAuth

auth = HTTPTokenAuth(scheme="Bearer")
tokens = {
    os.getenv("INBOUND_CHECK_TOKEN"): "inbound-check-token",
}


@auth.verify_token
def verify_token(token):
    """Check if a valid inbound token was used"""
    if token in tokens:
        return tokens[token]
    else:
        warn("Incorrect Token or not authenticated")
