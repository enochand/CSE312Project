from flask import Flask, render_template, request
from pymongo import MongoClient


mongo_client = MongoClient('mongo')
db = mongo_client['excaliber']
users = db['users']
counter = db["counter"]
counter.insert_one({"num_users": 0})
app = Flask(__name__)


# landing page; returns index.html
@app.get('/')
def landing():
    return render_template('index.html')


# route for creating new user, called in index.html
@app.post('/signup')
def new_user():
    username = request.form['new_username']
    email = request.form['new_email']
    counter.update_one({}, {"$inc": {"num_users": 1}})
    users.insert_one({"id": counter.find_one()["num_users"], "username": username, "email": email})
    return f"User {username} registered successfully"


# route to view user info by ID - returns plaintext for now
@app.get('/user/<user_id>')
def user_info(user_id):
    user = users.find_one({"id": int(user_id)})
    if user is not None:
        return str({"id": user["id"], "username": user["username"], "email": user["email"]})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
