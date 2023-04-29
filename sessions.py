from flask_bcrypt import Bcrypt
from secrets import token_urlsafe
from data import tokens
from hashlib import sha256

"""
The Sessions class is used for managing bcrypt(used for encrypting passwords for mongodb) and 
for handling identifying tokens given to users. Intended for anything having to do with verification

The __user_tokens dict can(and most likely will) be modified to include functionality of XSRF tokens
"""


def token_exists(user_token):
    user = tokens.find_one({"token": sha256(user_token.encode()).hexdigest()})
    if user_token != "":
        return user
    return None


def remove_token(user_token):
    tokens.update_one({"token": sha256(user_token.encode()).hexdigest()}, {"$set": {"token": ""}})


def id_from_token(user_token):
    try:
        return token_exists(user_token)["id"]
    except:
        return "-1"


def generate_user_token(user_id):
    user_token = token_urlsafe(20)
    while token_exists(user_token):
        user_token = token_urlsafe(20)
    tokens.insert_one({"token": sha256(user_token.encode()).hexdigest(), "id": str(user_id)})
    return user_token


class Sessions:
    def __init__(self, app):
        self.__bcrypt = Bcrypt(app)

    # returns a hashed version of the password(raw string)
    def pw_hash(self, password):
        return self.__bcrypt.generate_password_hash(password)

    # returns True if the 'stored' is equal to the hash of 'to_check'
    # inputs:
    #   stored = password from database(this should have been hashed on entry)
    #   to_check = raw string password
    def correct_pw(self, stored, to_check):
        return self.__bcrypt.check_password_hash(stored, to_check)

    # returns UNIQUE token and adds token to user_tokens
