from pymongo import MongoClient

mongo_client = MongoClient('localhost')
# mongo_client = MongoClient('mongo')
db = mongo_client['excaliber']
users = db['users']
counter = db["counter"]
counter.insert_one({"num_users": 0})
auction_counter = db["auction_counter"]
if "auction_counter" not in db.list_collection_names():
    auction_counter.insert_one({"count": 0})
auctions = db["auctions"]


def find_user_by_username(username):
    return users.find_one({"username": username})


def new_user(username, password):
    counter.update_one({}, {"$inc": {"num_users": 1}})
    users.insert_one({"id": counter.find_one()["num_users"], "username": username, "password": password})


# user_id can be a string or an int
def find_user_by_id(user_id):
    return users.find_one({"id": int(user_id)})


def next_auction_id():
    return auction_counter.find_one_and_update({}, {"$inc": {"count": 1}})["count"]


# adds auction to auctions, and auction_id to auctions owned by user_id
def new_auction(auction, user_id, auction_id):
    auctions.insert_one(auction)
    users.update_one({"id": int(user_id)}, {"$push": {"auctions": int(auction_id)}})


def find_auction_by_id(auction_id):
    return auctions.find_one({"id": int(auction_id)}, {"_id": 0})


def all_auctions():
    return auctions.find({}, {"_id": 0})
