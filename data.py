from pymongo import MongoClient
from helper import escape_html
from time import time
import json
import threading

# mongo_client = MongoClient('localhost')
mongo_client = MongoClient('mongo')
db = mongo_client['excaliber']
users = db['users']
counter = db["counter"]
if "counter" not in db.list_collection_names():
    counter.insert_one({"num_users": 0})
auction_counter = db["auction_counter"]
if "auction_counter" not in db.list_collection_names():
    auction_counter.insert_one({"count": 0})
auctions = db["auctions"]
tokens = db["tokens"]


def find_user_by_username(username):
    return users.find_one({"username": username}, {"_id": 0})


def new_user(username, password):
    users.insert_one({"id": counter.find_one()["num_users"],
                      "username": username, "password": password, "auctions": [], "purchased_auctions": []})
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
    users.find_one_and_update({"username": username}, {"$push": {"purchased_auctions": auction}})
    return 1 == auctions.update_one({"id": auction, "timeout": False, "highest_bid": {"$lt": bid}},
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

# Return all active auctions
def all_auctions():
    """Only returns all the active auctions now"""
    return list(auctions.find({"timeout": False}, {"_id": 0}))


# takes in a new user (callable the same way as a python dict)
# updates the username and/or password of the user(found by the id)
# user id cannot be changed
# returns new user
def update_user(user):
    return users.replace_one(
        {"id": user["id"]},
        {"id": user["id"], "username": user["username"], "password": user["password"], "auctions": user["auctions"], "purchased_auctions": user["purchased_auctions"]})


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


def create_auction_ending_thread(auction_id:int, duration:float):
    
    # since we can't pass function arguments into a function pointer, then we need a lambda
    end_auction_function =  lambda: end_auction(auction_id)
    auction_end_timer = threading.Timer(duration, end_auction_function)
    auction_end_timer.start()
    return

# To be called by the timer that controls ending auctions
# Returns True if successful and False if not
def end_auction(auction_id:int):
    # Import the sessions without having a circular import
    from sessions import Sessions
    # print("entered into the end auction function", flush=True) #Debug

    # Add timeout flag
    auction = auctions.find_one_and_update({"id": auction_id}, {"$set": {"timeout": True}})

    if auction is None: # Invalid auction_id
        return False
    
    # Insert won auction into user's list of won auctions
    users.update_one({"id": auction["highest_bidder"]}, {"$push": {"won_auctions": auction_id}})

    a = auctions.find_one({'id': auction_id})
    winningUsername = a.get('highest_bidder', '')
    message = {'messageType': 'endAuction', 'auction': auction_id, 'winner': winningUsername}
    # Send messages
    for connection in Sessions.web_sockets.values():
        connection.send(json.dumps(message))
    # print("should have send a message to all people", flush=True) #Debug
    return True

def change_username_all_auctions(old_username: str, new_username: str):
    """This function changes the username of the seller and highest bidder to the new username"""
    auctions.update_many({'username': old_username}, {'$set': {'username': new_username}})
    auctions.update_many({'highest_bidder': old_username}, {'$set': {'highest_bidder': new_username}})
    return

def give_me_all_living_auctions_ids():
    """Returns ids and durations of all auctions that aren't over yet.  This is run when a the 
       server is restarted and the threads for each living auction must be restarted."""
    all_auctions = auctions.find({})
    ids = []
    durations = []
    for a in all_auctions:
        t = a.get('time', -1)
        if t < time(): continue #skip over auctions that ended
        ids.append(a['id'])
        durations.append(t - time())
    return ids, durations