from flask import Flask, render_template, redirect, request, flash, session
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import re

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///solo_projects2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "secrets"
db=SQLAlchemy(app)
migrate=Migrate(app, db)
bcrypt=Bcrypt(app)

likes_table=db.Table('likes',
    db.Column("ideas_id", db.Integer, db.ForeignKey("ideas.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column('created_at', db.DateTime, server_default=func.now())
)

followers_table=db.Table('followers',
    db.Column("follower_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("followed_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("created_at", db.DateTime, server_default=func.now())
)

class User(db.Model):
    __tablename__ = "users"
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(100))
    alias=db.Column(db.String(100))
    email=db.Column(db.String(200))
    password_hash=db.Column(db.String(100))
    liked_ideas=db.relationship("ideas", secondary=likes_table)
    followers=db.relationship("User", 
        secondary=followers_table, 
        primaryjoin=id==followers_table.c.followed_id, 
        secondaryjoin=id==followers_table.c.follower_id,
        backref="following")
    created_at=db.Column(db.DateTime, server_default=func.now())
    updated_at=db.Column(db.DateTime, server_default=func.now(),onupdate=func.now())

    def full_name(self):
        return "{} {}".format(self.name, self.alias)
    
    def like_idea(self, idea):
        if not self.has_liked_idea(idea):
            like = likes_table(user_id=self.id, idea_id=idea.id)
            db.session.add(like)

    def unlike_idea(self, idea):
        if self.has_liked_idea(idea):
            likes_table.query.filter_by(
                user_id=self.id,
                idea_id=idea.id).delete()

    def has_liked_idea(self, idea):
        return likes_table.query.filter(
            likes_table.user_id == self.id,
            likes.idea_id == idea.id).count() > 0
    @classmethod
    def add_new_user(cls,data):
        new_user = cls(
            name=data['name'],
            alias=data['alias'],
            email=data['email'],
            password_hash=bcrypt.generate_password_hash(data['password'])
        )
        db.session.add(new_user)
        db.session.commit()
        return new_user

    @classmethod
    def find_registration_errors(cls, form_data):
        errors=[]
        if len(form_data['name'])<3:
            errors.append("name is not long enough")
        if len(form_data['alias'])<3:
            errors.append("alias is not long enough")
        if not EMAIL_REGEX.match(form_data['email']):
            errors.append("invalid email")
        if form_data['password'] != request.form['confirm']:
            errors.append("password dont match")
        if len(form_data['password']) < 8:
            errors.append("password isn't long enough")
        return errors

    @classmethod
    def register_new_user(cls, form_data):
        errors = cls.find_registration_errors(form_data)
        valid = len(errors)==0
        data = cls.add_new_user(form_data) if valid else errors
        return {
            "status": "good" if valid else "bad",
            "data": data
        }


class ideas(db.Model):
    __tablename__="ideas"
    id=db.Column(db.Integer, primary_key=True)
    message=db.Column(db.String(140))
    author_id=db.Column(db.Integer,db.ForeignKey("users.id"))
    author=db.relationship("User", backref="ideas", cascade="all")
    likers=db.relationship("User", secondary=likes_table)
    created_at=db.Column(db.DateTime, server_default=func.now())
    updated_at=db.Column(db.DateTime, server_default=func.now(),onupdate=func.now())

    @classmethod
    def add_new_ideas(cls,ideas):
        db.session.add(ideas)
        db.session.commit()
        return ideas
    
    def age(self):
        return self.created_at
        return age

class Follow(db.Model):
    __tablename__="follows"
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer, db.ForeignKey("users.id"))
    user=db.relationship("User",backref="likes", cascade="all")
    user_id=db.Column(db.Integer, db.ForeignKey("users.id"))
    user=db.relationship("User",backref="likes", cascade="all")
    created_at=db.Column(db.DateTime, server_default=func.now())

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9.+_-]+@[a-zA-Z0-9._-]+\.[a-zA-Z]+$')

@app.route("/")
def main():
    return render_template("main.html")

@app.route("/register", methods=["POST"])
def register():
    result=User.register_new_user(request.form)
    if result['status']=="good":
        user=result['data']
        session['cur_user'] = {
            "first": user.name,
            "last": user.alias,
            "id": user.id,
            "email": user.email
        }
        return redirect("/ideas")
    else:
        errors=result['data']
        for error in errors:
            flash(error)
        return redirect("/")

@app.route("/ideas")
def dashboard():
    print("here")
    if "cur_user" not in session:
        flash("Please Log In")
        return redirect("/")
    cur_user=User.query.get(session['cur_user']['id'])
    approved_users_ids = [user.id for user in cur_user.following]+[cur_user.id]
    all_ideas=ideas.query.filter(ideas.author_id.in_(approved_users_ids)).all()
    return render_template("ideas.html", ideas=all_ideas)

    return render_template("ideas.html", ideas=all_ideas) if "cur_user" in session else not_logged_in()

@app.route("/ideas/<int:t_id>")
def dashboard_detail(t_id):
    if "cur_user" not in session:
        flash("Please Log In")
        return redirect("/")
    cur_user=User.query.get(session['cur_user']['id'])
    approved_users_ids = [user.id for user in cur_user.following]+[cur_user.id]
    idea = ideas.query.get(t_id)
    all_ideas=ideas.query.filter(ideas.author_id.in_(approved_users_ids)).all()
    return render_template("ideas_detail.html", ideas=all_ideas, idea=idea, idea_id=idea.id)

@app.route("/login", methods=['POST'])
def login():
    user=User.query.filter_by(email=request.form['email']).all()
    valid = True if len(user)==1 and bcrypt.check_password_hash(user[0].password_hash, request.form['password']) else False
    if valid:
        session['cur_user'] = {
            "first": user[0].name,
            "last": user[0].alias,
            "id": user[0].id,
            "email": user[0].email,
            "all": user[0]
        }
        return redirect("/ideas")
    else:
        flash("Invalid login credentials")
        return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/ideas", methods=["POST"])
def add_ideas():
    if "cur_user" not in session:
        flash("Please Log In")
        return redirect("/")
    new_ideas=ideas(
        message=request.form['ideas'],
        author_id=int(session['cur_user']['id'])
    )
    if len(new_ideas.message) > 0:
        ideas.add_new_ideas(new_ideas)
    else:
        flash("need more ideas length!")
    return redirect("/ideas")

@app.route("/ideas/<ideas_id>/delete", methods=['idea'])
def delete_ideas(ideas_id):
    if "cur_user" not in session:
        flash("Please Log In")
        return redirect("/")
    ideas_being_deleted=ideas.query.get(ideas_id)
    ideas_author=ideas_being_deleted.author
    ideas_author.ideas.remove(ideas_being_deleted)
    db.session.commit()
    return redirect("/ideas")

@app.route("/ideas/<ideas_id>/like", methods=["POST"])
def add_like(ideas_id):
    if "cur_user" not in session:
        flash("Please Log In")
        return redirect("/")
    liked_ideas=ideas.query.get(ideas_id)
    unliked_ideas=ideas.query.get(ideas_id)
    liker=User.query.get(session['cur_user']['id'])
    
    if liked_ideas not in liker.liked_ideas:
        liker.liked_ideas.append(liked_ideas)

    print(liker.liked_ideas)
    db.session.commit()
    return redirect(f"/ideas/{ideas_id}")

@app.route("/ideas/<ideas_id>/unlike", methods=["POST"])
def remove_like(ideas_id):
    # query = "DELETE FROM likes WHERE users_id = %(user_id)s AND ideas_id = %(tweet_id)s"
    if "cur_user" not in session:
        flash("Please Log In")
        return redirect("/")
    idea=ideas.query.get(ideas_id)
    liker=User.query.get(session['cur_user']['id'])
    print(idea)
    print(liker)
    print(liker.liked_ideas)
    liker.liked_ideas.remove(idea)
    db.session.commit()
    print(liker.liked_ideas)
    return redirect(f"/ideas/{ideas_id}")

@app.route("/ideas/<ideas_id>/edit")
def show_edit(ideas_id):
    if "cur_user" not in session:
        flash("Please Log In")
        return redirect("/")
    idea=ideas.query.get(ideas_id)
    return render_template("edit.html", ideas=idea)

@app.route("/ideas/<ideas_id>/update", methods=["POST"])
def update_ideas(ideas_id):
    if "cur_user" not in session:
        flash("Please Log In")
        return redirect("/")
    idea=ideas.query.get(ideas_id)
    if len(request.form['ideas'])>0:
        idea.message=request.form['ideas']
        db.session.commit()
        return redirect("/ideas")
    else:
        flash("need more ideas!")
        return render_template("edit.html", ideas=idea)

@app.route("/users")
def show_users():
    if "cur_user" not in session:
        flash("Please Log In")
        return redirect("/")
    users_list=User.query.all()
    return render_template("users.html", users=users_list)

@app.route("/follow/<user_id>")
def follow_user(user_id):
    if "cur_user" not in session:
        flash("Please Log In")
        return redirect("/")
    logged_in_user=User.query.get(session['cur_user']['id'])
    followed_user=User.query.get(user_id)
    followed_user.followers.append(logged_in_user)
    db.session.commit()
    return redirect("/users")

@app.route("/user_profile/<user_id>")
def render_user_profile(user_id):
    if "cur_user" not in session:
        flash("Please Log In")
        return redirect("/")
    users_list=User.query.all()
    cur_user=User.query.get(session['cur_user']['id'])
    approved_users_ids = [user.id for user in cur_user.following]+[cur_user.id]
    all_ideas=ideas.query.filter(ideas.author_id.in_(approved_users_ids)).all()
    user=User.query.get(user_id)
    return render_template("user_profile.html", ideas=all_ideas, user=user)

    return render_template("ideas.html", ideas=all_ideas) if "cur_user" in session else not_logged_in()

if __name__ == "__main__":
    app.run(debug=True)