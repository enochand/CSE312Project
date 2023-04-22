from pymongo import MongoClient
from helper import escape_html
from time import time

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
    return users.find_one({"username": username}, {"_id": 0})


def new_user(username, password):
    users.insert_one({"id": counter.find_one()["num_users"],
                      "username": username, "password": password, "auctions": []})
    counter.update_one({}, {"$inc": {"num_users": 1}})

def get_username_by_id(id: int):
    results = find_user_by_id(id)
    return results.get('username', None)

# user_id can be a string or an int
def find_user_by_id(user_id):
    return users.find_one({"id": int(user_id)}, {"_id": 0})


def next_auction_id():
    return auction_counter.find_one_and_update({}, {"$inc": {"count": 1}})["count"]


# adds auction to auctions, and auction_id to auctions owned by user_id
def new_auction(auction, user_id, auction_id):
    auctions.insert_one(auction)
    users.update_one({"id": int(user_id)}, {"$push": {"auctions": int(auction_id)}})


# Returns True if bid was pushed, False otherwise
def push_bid(auction:int, username:str, bid:int):
    auction = find_auction_by_id(auction)
    if not auction or auction.get('time', -1) < time():#if id doesnt' exist or auction is over
        return 0
    return 1 == auctions.update_one({"id": auction, "highest_bid": {"$lt": bid}},
                                    {"$set": {"highest_bidder": username, "highest_bid": bid}}).modified_count


def find_auction_by_id(auction_id):
    return auctions.find_one({"id": int(auction_id)}, {"_id": 0})

def find_won_auctions_by_username(username: str):
    allWinning = auctions.find({"highest_bidder": username}, {"_id": 0})
    #return all auctions that are over where this person was highest bidder
    output = []
    for a in allWinning:
        if a.get('time', float('inf')) < time():
            output.append(a)
    return output

def find_posted_auctions_by_username(username):
    return list(auctions.find({"username": username}, {"_id": 0}))

def all_auctions():
    """Only returns all the active auctions now"""
    all = auctions.find({}, {"_id": 0})
    active_auctions = []#willl contain all the active auctions
    #only return the ones who's time isn't over
    for a in all:
        if a.get('time', -1) > time():
            active_auctions.append(a)
    return active_auctions


# takes in a new user (callable the same way as a python dict)
# updates the username and/or password of the user(found by the id)
# user id cannot be changed
# returns new user
def update_user(user):
    return users.replace_one(
        {"id": user["id"]},
        {"id": user["id"], "username": user["username"], "password": user["password"], "auctions": user["auctions"]})


def update_auction_by_id(auction_id, auction):
    # UPDATE IMAGES NOT IMPLEMENTED YET
    # if auction["image"] and auction["image"] != "":
    #     auctions.find_one_and_update({"id": auction_id}, {"$set": {"image": auction["image"]}})
    if auction["description"] and auction["description"] != "":
        auctions.find_one_and_update({"id": auction_id}, {"$set": {"description": auction["description"]}})
    if auction["highest_bidder"] and auction["highest_bidder"] != "":
        auctions.find_one_and_update({"id": auction_id}, {"$set": {"highest_bidder": auction["highest_bidder"]}})
    if auction["highest_bid"] and auction["highest_bid"] != "":
        auctions.find_one_and_update({"id": auction_id}, {"$set": {"highest_bid": auction["highest_bid"]}})


# To be called by the timer that controls ending auctions
# Returns user_id of whoever won
def end_auction(auction_id):
    pass