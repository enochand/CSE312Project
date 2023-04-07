from flask import Flask, render_template, request, redirect, send_from_directory, jsonify
from time import time, sleep
from sessions import Sessions
import data
from flask_sock import Sock, ConnectionClosed
import json


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
    pw_hash = ss.pw_hash(password)
    data.new_user(username, pw_hash)

    user = data.find_user_by_username(username)
    return login_response(user)


# checks for matching username/password pair, redirects to home and sets cookie
@app.post('/login')
def returning_user():
    # exit function if username is not a user
    username = request.form['username']
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
@app.get('/user/<user_id>')
def user_info(user_id):
    token = request.cookies.get("token")
    if not is_logged_in(token):
        return redirect('/')
    user = data.find_user_by_id(user_id)
    if user is not None:
        return str({"id": user["id"], "username": user["username"], "password": user["password"]})


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


# Create new auction if logged in
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
    
    # Verify numeric elements are not negative
    if duration < 0:
        return "Duration must not be negative"
    
    if price < 0:
        return "Price must not be negative"
    
    # Verify file is of an allowed file extension
    allowed_auction_image(file.filename)
    extension = "." + file.filename.rsplit('.', 1)[1].lower()

    # Get next auction id
    auction_id = data.next_auction_id()

    # Save image
    filename = "item" + str(auction_id) + extension
    file.save("item/" + filename)

    # Create auction
    auction = {"id": auction_id, "user": user["id"], "image": filename, "description": description,
               "time": int(time()) + duration}
    bid = {"user": user["id"], "bid": price}
    auction["bids"] = [bid]
    # Insert auction into database
    data.new_auction(auction, user['id'], auction_id)
    # Redirect to auction display page
    return redirect("/auctions")


# Get auction JSON by id:
# "id" = int id
# "user" = user id of auction creator
# "image" = image filename without path
# "description" = description text
# "time" = end date timestamp
# "bids" = list of bids:
#   "user" = user id of bidder
#   "bid" = bid amount
@app.get('/auction/<int:auction_id>')
def auction_info(auction_id):
    token = request.cookies.get("token")
    if not is_logged_in(token):
        return redirect('/')
    auction = data.find_auction_by_id(auction_id)
    if auction is not None:
        return jsonify(auction)


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
    # check cookies; if logged in take to home page
    # user_token = request.cookies.get("token")
    # user = is_logged_in(user_token)
    # if not user:
    #     return render_template("index.html")
    return render_template("auctions_page.html")

#send js for auctions_page
@app.get("/js/<path:filename>")
def returnJSFiles(filename):
    filename = filename.replace('/', '')# making it so sender can't leave directory they requested
    response = send_from_directory("JavaScript", filename)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response



@sock.route('/websockets')
def websockets(sock):
    """This function adds the client to the Sessions.web_sockets list, and keeps the the TCP connection alive
       until the client closes the connection.  If multiple clients with the same user_token attempt to connect
       this function trows and Exception."""
    user_token = request.cookies.get("token")
    if Sessions.web_sockets.get(user_token, None) != None:
        print('Token alredy in dictionary')
        raise Exception('Multiple people with the same token tried to join websockets')
    Sessions.web_sockets[user_token] = sock
    print(f'{user_token} joined websockets!')
    print(Sessions.web_sockets)
    while True:
        try: 
            data = sock.receive()
        except ConnectionClosed:
            Sessions.web_sockets.pop(user_token, None)
            print(f'{user_token} left websockets!')
            break
        for sock in Sessions.web_sockets.values():
            sock.send(data)



def allowed_auction_image(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {"png", "jpg", "jpeg"}


# returns user if the user is logged in
def is_logged_in(user_token):
    user_id = ss.id_from_token(user_token)  # -1 if user_token does not exist
    return data.find_user_by_id(user_id)  # none if user user_id does not exist


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
