from flask import Flask, render_template, request, redirect
from pymongo import MongoClient

mongo_client = MongoClient('mongo')
db = mongo_client['excaliber']
users = db['users']
counter = db["counter"]
counter.insert_one({"num_users": 0})
app = Flask(__name__)


# landing page; returns index.html (or redirects to home if logged in)
@app.get('/')
def landing():
    # check cookies; if logged in take to home page
    token = request.cookies.get("token")  # needs to be modified to find the id based on token
    user = users.find_one({"id": token})
    if not user:
        return render_template('index.html')
    return redirect('/home')


# route for creating new user, called in index.html
@app.post('/signup')
def new_user():
    username = request.form['new_username']
    email = request.form['new_email']
    user = users.find_one({"username": username})
    if user is not None:
        return "Username Taken"
    counter.update_one({}, {"$inc": {"num_users": 1}})
    users.insert_one({"id": counter.find_one()["num_users"], "username": username, "email": email})
    return redirect('/')


# checks for matching username/password pair, redirects to home and sets cookie
@app.post('/login')
def returning_user():
    # exit function if username is not a user
    username = request.form['username']
    user = users.find_one({"username": username})
    if not user:
        return "Invalid Username or Password"
    email = request.form['email']
    # exit function if password does not match
    if user["email"] != email:
        return "Invalid Username or Password"
    response = redirect('/home')
    response.set_cookie('token', str(user["id"]))  # needs to be modified to create unique token
    return response


# route to view user info by ID - returns plaintext for now
@app.get('/user/<user_id>')
def user_info(user_id):
    user = users.find_one({"id": int(user_id)})
    if user is not None:
        return str({"id": user["id"], "username": user["username"], "email": user["email"]})


# clears cookies and redirects to login page
@app.post('/logout')
def log_out():
    response = redirect("/")
    response.set_cookie("token", "", expires=0)
    return response


@app.get('/home')
def home():
    return render_template('home.html')


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
