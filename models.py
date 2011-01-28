from google.appengine.ext import db

class Class(db.Model):
    name = db.StringProperty(required=True)
    semester = db.IntegerProperty(required=True)
    exam = db.DateTimeProperty(required=True)
    preexam = db.BooleanProperty(required=True)
    color = db.StringProperty(required=False)
    user = db.UserProperty(required=True)

class Task(db.Model):
    title = db.StringProperty(required=True)
    text = db.TextProperty(required=True)
    classname = db.StringProperty(required=True)
    enddate = db.DateTimeProperty(required=True)
    state = db.StringProperty(required=False)
    homework = db.BooleanProperty(required=False)
    color = db.StringProperty(required=False)
    user = db.UserProperty(required=True)

class Book(db.Model):
    title = db.StringProperty(required=True)
    classname = db.StringProperty(required=True)
    user = db.UserProperty(required=True)

class Chapter(db.Model):
    title = db.StringProperty(required=True)
    number = db.StringProperty(required=True)
    book = db.StringProperty(required=True)
    state = db.StringProperty(required=True)
    user = db.UserProperty(required=True)

class Event(db.Model):
    title = db.StringProperty(required=True)
    user = db.UserProperty(required=True)
    datetime = db.DateTimeProperty(required=True)
    classname = db.StringProperty(required=False)
    place = db.StringProperty(required=False)
    text = db.TextProperty(required=False)