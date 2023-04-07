from flask import Flask, render_template, request, redirect, send_from_directory, jsonify, escape
from time import time
from sessions import Sessions
import data
import helper


app = Flask(__name__)
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
    username = escape(request.form['new_username'])
    password = escape(request.form['new_password'])
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
    password = escape(request.form['password'])
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
    is_user = is_visited_user(token, user_id) # returns false if no user found
    user_id = data.find_user_by_id(user_id)
    posted_auctions = user_id["auctions"]
    if user_id is not None:
        user_template = render_template('profile.html', is_user=is_user, 
                                                        username=user_id["username"],
                                                        posted_auctions=user_id["auctions"])
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

    # HTML escape description
    description = escape(description)

    # Create auction
    auction = {"id": auction_id, "user": user["id"], "image": filename, "description": description,
               "time": int(time()) + duration, "highest_bidder": user["id"], "highest_bid": price}
    # Insert auction into database
    data.new_auction(auction, user['id'], auction_id)
    # Redirect to auction display page
    return redirect("/auctions")


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


# changes the username of a user
# has to be requested by that user, and user has to be logged in
@app.post("/change_username")
def change_username():
    token = request.cookies.get("token")
    user = is_logged_in(token)
    if not user:
        return redirect("/")
    user["username"] = request.form["new_username"]
    if data.find_user_by_username(user["username"]):
        return "Username Taken"
    data.update_user_by_id(user)
    return "Username Updated"


def allowed_auction_image(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in {"png", "jpg", "jpeg"}


# returns user if the user is logged in
def is_logged_in(user_token):
    user_id = ss.id_from_token(user_token)  # -1 if user_token does not exist
    return data.find_user_by_id(user_id)  # none if user user_id does not exist

# returns true if the token of the user matches the token of the visited user page
def is_visited_user(user_token, visited_user):
    user_id = ss.id_from_token(user_token)  # -1 if user_token does not exist
    return data.find_user_by_id(user_id)["id"] == visited_user  # true if the token matches

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8080)
