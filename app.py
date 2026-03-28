print("APP VERSION 2 LOADED")
import os

from exa_py import Exa
from dotenv import load_dotenv

load_dotenv()

exa = Exa(api_key=os.getenv("EXA_API_KEY"))
from flask import Flask, flash, redirect, render_template, request, session
from cs50 import SQL
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, apology

# Configure application
app = Flask(__name__)



# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///mini_x.db")


@app.route("/")
@login_required
def index():

    posts = db.execute("""
        SELECT posts.*, users.username
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY timestamp DESC
    """)

    # Add like info to each post
    for post in posts:

        # Like count
        count = db.execute(
            "SELECT COUNT(*) AS total FROM likes WHERE post_id = ?",
            post["id"]
        )

        post["likes"] = count[0]["total"]

        # Did current user like?
        liked = db.execute(
            "SELECT * FROM likes WHERE user_id = ? AND post_id = ?",
            session["user_id"],
            post["id"]
        )

        post["liked"] = len(liked) > 0

    return render_template("index.html", posts=posts)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["total_value"] = 0

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("username")

        # checking if name and password are filled
        if not name:
            return apology("must provide username", 400)
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        # checking if both password are same
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match", 400)

        password = generate_password_hash(request.form.get("password"))

        # checkling if user alredy exists
        user = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if user:
            return apology("user already exist")

        # adding new users in database
        db.execute('INSERT INTO users ("username", "hash") VALUES(?, ?)', name, password)

        # adding cookie to the user
        rows = db.execute("SELECT * FROM users WHERE username = ?", name)
        session["user_id"] = rows[0]["id"]

        return redirect("/")
    else:
        return render_template("register.html")

@app.route("/post", methods=["GET","POST"])
@login_required
def post():

    if request.method == "POST":

        content = request.form.get("content")

        if not content:
            return apology("cannot post empty", 404)

        db.execute(
            "INSERT INTO posts (user_id, content) VALUES (?, ?)",
            session["user_id"],
            content
        )

        return redirect("/")

    else:
        return render_template("post.html")


@app.route("/users")
@login_required
def users():

    users = db.execute(
        "SELECT id, username FROM users WHERE id != ?",
        session["user_id"]
    )

    following = db.execute(
        "SELECT following_id FROM followers WHERE follower_id = ?",
        session["user_id"]
    )

    following_ids = [f["following_id"] for f in following]

    return render_template(
        "users.html",
        users=users,
        following_ids=following_ids
    )

@app.route("/follow/<int:user_id>", methods=["POST"])
@login_required
def follow(user_id):

    print("FOLLOW CLICKED", user_id) 

    db.execute("""
INSERT OR IGNORE INTO followers 
(follower_id, following_id)
VALUES (?, ?)
""", session["user_id"], user_id)

    return redirect("/users")

@app.route("/unfollow/<int:user_id>", methods=["POST"])
@login_required
def unfollow(user_id):

    db.execute("""
        DELETE FROM followers
        WHERE follower_id = ? AND following_id = ?
    """, session["user_id"], user_id)

    return redirect("/users")

@app.route("/profile/<int:user_id>")
@login_required
def profile(user_id):

    # Get user
    user = db.execute(
        "SELECT * FROM users WHERE id = ?",
        user_id
    )

    if len(user) == 0:
        return apology("User not found", 404)

    # Get posts
    posts = db.execute(
        "SELECT * FROM posts WHERE user_id = ? ORDER BY timestamp DESC",
        user_id
    )

    # Counts
    posts_count = db.execute(
        "SELECT COUNT(*) AS count FROM posts WHERE user_id = ?",
        user_id
    )[0]["count"]

    followers_count = db.execute(
        "SELECT COUNT(*) AS count FROM followers WHERE following_id = ?",
        user_id
    )[0]["count"]

    following_count = db.execute(
        "SELECT COUNT(*) AS count FROM followers WHERE follower_id = ?",
        user_id
    )[0]["count"]

    # Follow status
    is_following = db.execute(
        "SELECT * FROM followers WHERE follower_id = ? AND following_id = ?",
        session["user_id"],
        user_id
    )

    return render_template(
        "profile.html",
        user=user[0],
        posts=posts,
        posts_count=posts_count,
        followers_count=followers_count,
        following_count=following_count,
        is_following=len(is_following) > 0
    )

@app.route("/delete/<int:post_id>", methods=["POST"])
@login_required

def delete(post_id):

    post = db.execute(
        "SELECT * FROM posts WHERE id = ?",
        post_id
    )

    if len(post) == 0:
        return "Post not found"

    # Security check
    if post[0]["user_id"] != session["user_id"]:
        return "Not allowed"

    db.execute(
        "DELETE FROM posts WHERE id = ?",
        post_id
    )

    return redirect(f"/profile/{session['user_id']}")

@app.route("/like/<int:post_id>", methods=["POST"])
@login_required
def like(post_id):

    # Check if already liked
    like = db.execute(
        "SELECT * FROM likes WHERE user_id = ? AND post_id = ?",
        session["user_id"],
        post_id
    )

    # If liked → remove like
    if len(like) > 0:

        db.execute(
            "DELETE FROM likes WHERE user_id = ? AND post_id = ?",
            session["user_id"],
            post_id
        )

    # Otherwise add like
    else:

        db.execute(
            "INSERT INTO likes (user_id, post_id) VALUES (?, ?)",
            session["user_id"],
            post_id
        )

    return redirect(request.referrer)

@app.route("/explore")
@login_required
def explore():

    # Get people current user follows
    following = db.execute(
        "SELECT following_id FROM followers WHERE follower_id = ?",
        session["user_id"]
    )

    # Extract ids
    following_ids = [f["following_id"] for f in following]

    # If not following anyone
    if not following_ids:
        return render_template("explore.html", topics=[])

    # Get their latest posts
    posts = db.execute(
        f"SELECT content FROM posts WHERE user_id IN ({','.join(['?']*len(following_ids))}) ORDER BY timestamp DESC LIMIT 5",
        *following_ids
    )

    # Combine text
    query = " ".join([p["content"] for p in posts])

    if not query:
        query = "programming technology"

    # AI search
    results = exa.search_and_contents(

        query,

        type="auto",

        num_results=5,

        highlights={"max_characters":300}

    )

    topics = []

    for r in results.results:

        topics.append({

            "title": r.title,

            "url": r.url

        })

    return render_template("explore.html", topics=topics)

if __name__ == "__main__":
    app.run(debug=True)