from flask import Blueprint

main = Blueprint("main", __name__)

from . import auth, config, inbound, internal, tools
