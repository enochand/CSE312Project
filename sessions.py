from flask_bcrypt import Bcrypt
from secrets import token_urlsafe

"""
The Sessions class is used for managing bcrypt(used for encrypting passwords for mongodb) and 
for handling identifying tokens given to users. Intended for anything having to do with verification

The __user_tokens dict can(and most likely will) be modified to include functionality of XSRF tokens
"""


class Sessions:
    #key = token, value = socket connection
    web_sockets = {} #this will hold all the web sockets that are connected, for brodcast operation
    def __init__(self, app):
        self.__bcrypt = Bcrypt(app)
        self.__user_tokens = {}


    # returns a hashed version of the password(raw string)
    def pw_hash(self, password):
        return self.__bcrypt.generate_password_hash(password)

    # returns True if the 'stored' is equal to the hash of 'to_check'
    # inputs:
    #   stored = password from database(this should have been hashed on entry)
    #   to_check = raw string password
    def correct_pw(self, stored, to_check):
        return self.__bcrypt.check_password_hash(stored, to_check)

    def remove_token(self, user_token):
        self.__user_tokens.pop(user_token)

    def token_exists(self, user_token):
        return user_token in self.__user_tokens.keys()

    def id_from_token(self, user_token):
        if self.token_exists(user_token):
            return self.__user_tokens[user_token]
        return "-1"

    # returns UNIQUE token and adds token to user_tokens
    def generate_user_token(self, user_id):
        user_token = token_urlsafe(20)
        while user_token in self.__user_tokens.keys():
            user_token = token_urlsafe(20)
        self.__user_tokens[user_token] = user_id
        return user_token
