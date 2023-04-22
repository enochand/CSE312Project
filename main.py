from flask import Flask, render_template, request, redirect, send_from_directory, jsonify, escape
from time import time, sleep
from sessions import Sessions
import data
from flask_sock import Sock, ConnectionClosed
import json
import helper


app = Flask(__name__)
sock = Sock(app)
ss = Sessions(app)  # refer to session.py
app.config["MAX_CONTENT_PATH"] = 1000000  # 1 MB


# landing page; returns index.html (or redirects to home if logged in)
@app.get('/')
def landing():
    # check cookies; if logged in take to home page
    user_token = request.cookies.get("token")
    user = is_logged_in(user_token)
    if not user:
        return render_template("index.html")
    return redirect("/home")


# route for creating new user, called in index.html
@app.post('/signup')
def new_user():
    username = request.form['new_username']
    password = request.form['new_password']
    user = data.find_user_by_username(username)
    if user is not None:
        return "Username Taken"
    if not helper.valid_username(username):
        return "Username must be alphanumeric and between 3-20 characters long"
    if not helper.valid_password(password):
        return "Password must be 8-20 characters long"
    pw_hash = ss.pw_hash(password)
    data.new_user(username, pw_hash)
    user = data.find_user_by_username(username)
    return login_response(user)


# checks for matching username/password pair, redirects to home and sets cookie
@app.post('/login')
def returning_user():
    # exit function if username is not a user
    username = escape(request.form['username'])
    user = data.find_user_by_username(username)

    if not user:
        return "Invalid Username or Password"
    password = request.form['password']
    # exit function if password does not match
    if not ss.correct_pw(user['password'], password):
        return "Invalid Username or Password"

    # log out of current account
    user_token = request.cookies.get("token")
    if is_logged_in(user_token):
        ss.remove_token(user_token)

    return login_response(user)


def login_response(user):
    response = redirect('/home')
    new_token = ss.generate_user_token(str(user["id"]))
    response.set_cookie('token', new_token)
    return response


# route to view user info by ID - returns plaintext for now
@app.get('/user/<int:user_id>')
def user_info(user_id):
    token = request.cookies.get("token")
    if not is_logged_in(token):
        return redirect('/')
    is_user = is_visited_user(token, user_id)  # returns false if no user found
    user = data.find_user_by_id(user_id)
    if user:
        user_template = render_template('profile.html', is_user=is_user,
                                        username=user["username"],
                                        posted_auctions=user["auctions"])
        return user_template
    return "User not found"


# clears cookies and redirects to login page
@app.post('/logout')
def log_out():
    response = redirect("/")
    user_token = request.cookies.get("token")
    response.set_cookie("token", "", expires=0)
    ss.remove_token(user_token)
    return response


# checks if user is logged in, takes them to home page
@app.get('/home')
def home():
    user_token = request.cookies.get("token")
    if is_logged_in(user_token):
        return render_template('home.html')
    return redirect('/')


# Send html of create auction form if logged in
@app.get('/create')
def create_auction_page():
    # Redirect to login page if not logged in
    user = is_logged_in(request.cookies.get("token"))
    if user is None:  # Not logged in
        return redirect("/")

    return render_template("create_auction.html")


# Create new auction if logged in:
# "id" = int id
# "user" = user id of auction creator
# "image" = image filename without path
# "description" = description text
# "time" = end date timestamp
# "highest_bidder" = user id of highest bidder, will be creator if no one bids
# "highest_bid" = highest bid (starts at starting price)
# "timeout" = false by default, true if auction is ended
@app.post('/create')
def create_auction():
    # Redirect to login page if not logged in
    user = is_logged_in(request.cookies.get("token"))
    if user is None:  # Not logged in
        return redirect("/")

    # Verify form elements are present
    elements = ["description", "duration", "price"]
    for e in elements:
        if e not in request.form:
            return "Missing form elements"

    if "image" not in request.files:
        return "Missing image element"

    file = request.files["image"]
    if file.filename == "":
        return "No selected file"

    # Verify the description is not empty
    description = request.form["description"]
    if description == "":
        return "Description must not be empty"

    # Verify the description is not too long
    if len(description) > 100:
        return "Description must not be greater than 100 characters"

    # Verify numeric elements are numeric
    try:
        duration = int(request.form["duration"])
    except ValueError:
        return "Duration is not an integer"

    try:
        price = int(request.form["price"])
    except ValueError:
        return "Price is not an integer"

    # Verify numeric elements are within range
    if duration < 10 or duration > 3600:
        return "Duration must be between 10 and 3600 seconds"

    if price < 0 or price > 999999: 
        return "Price must be between 0 and 999999"

    # Verify file is of an allowed file extension
    helper.allowed_auction_image(file.filename)
    extension = "." + file.filename.rsplit('.', 1)[1].lower()

    # Get next auction id
    auction_id = data.next_auction_id()

    # Save image
    filename = "item" + str(auction_id) + extension
    file.save("item/" + filename)

    #get username
    username = data.get_username_by_id(user["id"])

    # Create auction
    auction = {"id": auction_id,        # id: ID of the auction
        "user": user["id"],             # user: The id for the user who made the auction 
        "username": username,           # username of person who made the auction
        "image": filename,              # image: The image for the item up for auction
        "description": escape(description),     # description: The description of the item up for auction
        "time": int(time()) + duration,  # time: The time the auction is set to end
        "highest_bidder": username, 
        "highest_bid": price,
        "timeout": False}               # timeout: True/False if auction is ended
    #removing keeping track of all all bids for now
    # bid = {"user": user["id"], "bid": price}
    # auction["bids"] = [bid]

    #send auction to everyone with a WS connection
    message = {'messageType': 'newAuction', 'auction': auction}
    for connection in ss.web_sockets.values():
        connection.send(json.dumps(message))

    # Insert auction into database
    data.new_auction(auction, user['id'], auction_id)

    # Redirect to auction display page
    return redirect("/auctions_page")


# Get auction JSON by id
@app.get('/auction/<int:auction_id>')
def auction_info(auction_id):
    token = request.cookies.get("token")
    if not is_logged_in(token):
        return redirect('/')
    auction = data.find_auction_by_id(auction_id)
    if auction is not None:
        return jsonify(auction)
    return "Auction Not Found"


# JSON list of all auctions
@app.get('/auctions')
def auction_list():
    token = request.cookies.get("token")
    if not is_logged_in(token):
        return redirect('/')
    return jsonify(list(data.all_auctions()))


# Get an image
@app.get("/item/<path:filename>")
def item_image(filename):
    token = request.cookies.get("token")
    if not is_logged_in(token):
        return redirect('/')
    response = send_from_directory("item", filename)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

#This is the auctions page that will have a WS connection
@app.get('/auctions_page')
def returnAuctionsPage():
    user_token = request.cookies.get("token")
    user = is_logged_in(user_token)
    if not user:
        return redirect('/')
    return render_template("auctions_page.html")

#send js for auctions_page
@app.get("/js/<path:filename>")
def returnJSFiles(filename):
    filename = filename.replace('/', '')# making it so sender can't leave directory they requested
    response = send_from_directory("JavaScript", filename)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response

@app.get("/find_won_auctions")
def findWonAuctions():
    user_token = request.cookies.get("token")
    if not is_logged_in(user_token):
        return redirect('/')
    #find all the auctions this user has won
    user_id = ss.id_from_token(user_token) # We use this to verify the user over websockets
    user = data.find_user_by_id(user_id)
    username = user.get('username', None)
    won = data.find_won_auctions_by_username(username)
    won = json.dumps(won)
    return won#returns a list of all won auctions

@app.get("/find_posted_auctions")
def findPostedAuctions():
    user_token = request.cookies.get("token")
    if not is_logged_in(user_token):
        return redirect('/')
    #find all the auctions this user has won
    user_id = ss.id_from_token(user_token) # We use this to verify the user over websockets
    user = data.find_user_by_id(user_id)
    username = user.get('username', None)
    postedAuctions = data.find_posted_auctions_by_username(username)
    postedAuctions = json.dumps(postedAuctions)
    return postedAuctions#returns a list of all won auctions

@sock.route('/websockets')
def websockets(sock):
    """This function adds the client to the Sessions.web_sockets list, and keeps the the TCP connection alive
       until the client closes the connection.  If multiple clients with the same user_token attempt to connect
       this function trows and Exception."""
    user_token = request.cookies.get("token")
    user_id = ss.id_from_token(user_token) # We use this to verify the user over websockets
    user = data.find_user_by_id(user_id)
    username = user.get('username', None)
    
    #adding socket connection to web_sockets
    Sessions.web_sockets[user_id] = sock
    
    #sending all the current auctions
    auctions = list(data.all_auctions())
    message = {'messageType': 'auctionsList', 'auctions': auctions}
    message = json.dumps(message)
    sock.send(message)
    
    # enter while true for persistent socket connection
    while True:
        try: 
            WSmessage = sock.receive()
            WSmessage = json.loads(WSmessage)
        except:
            Sessions.web_sockets.pop(user_id, None)
            print(f'{username} id: {user_id} left websockets!')
            break  # break out of infinite while loop
        messageType = WSmessage.get('messageType', None)
        
        if messageType == 'identifyMe':
            message = {'messageType': 'identity', 'id': user_id, 'username': username}
            sock.send(json.dumps(message))
        
        elif messageType == 'bid':
            incoming_id = WSmessage.get('user_id', None)
            if not incoming_id == user_id:# handle someone sends bids with another person's username
                print('someone tried to bid as someone else')
                message = {'messageType': 'illegalAction'}
                sock.send(json.dumps(message))
            else:
                from_username = WSmessage.get('username', None)
                auctionID = int(WSmessage.get('auctionID', None))#make in int
                bidPrice = verifyNumber(WSmessage.get('bid', float('-inf')))
                if bidPrice == -1:#invalid input, ignore
                    continue

                pushed = data.push_bid(auctionID, from_username, bidPrice)#pushed == true if updates winning bid
                if pushed:
                    #if this runs, the client is the current highest bidder
                    WSmessage['messageType'] = 'updateBid'#change message type
                    message = json.dumps(WSmessage)#will just foreward this message to everyone
                    #send this update to everyone
                    for connection in ss.web_sockets.values():
                        connection.send(message)


def verifyNumber(num):
    """This function is used to verify that the number sent in a bid is a number"""
    if num == float('-inf'):
        return -1
    try:
        num = float(num)
    except:
        return -1
    return num



# changes the username of a user
# has to be requested by that user, and user has to be logged in
@app.post("/change_username")
def change_username():
    token = request.cookies.get("token")
    user = is_logged_in(token)
    if not user:
        return redirect("/")
    user["username"] = escape(request.form["new_username"])
    if data.find_user_by_username(user["username"]):
        return "Username Taken"
    elif not helper.valid_username(user["username"]):
        return "Invalid Username"
    data.update_user(user)
    return "Username Updated"


# updates all auction info. if you don't want to update something, leave it as an empty string or None
@app.post("/update_auction")
def update_auction():
    token = request.cookies.get("token")
    user = is_logged_in(token)
    if not user:
        return redirect("/")
    auction_id = request.form["auction_id"]
    if auction_id not in user["auctions"]:
        return "You do not have permissions to edit other people's auctions"
    image = request.files.get("image")
    description = request.form.get("description")
    highest_bidder = request.form.get("highest_bidder")
    highest_bid = request.form.get("highest_bid")
    auction = {"image": image, "description": escape(description), "highest_bidder": highest_bidder, "highest_bid": highest_bid}
    data.update_auction_by_id(auction_id, auction)


# returns user if the user is logged in
def is_logged_in(user_token):
    user_id = ss.id_from_token(user_token)  # -1 if user_token does not exist
    return data.find_user_by_id(user_id)  # none if user user_id does not exist


# returns true if the token of the user matches the token of the visited user page
def is_visited_user(user_token, visited_user):
    return is_logged_in(user_token)["id"] == visited_user  # true if the token matches

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)