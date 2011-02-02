# !/usr/bin/env python
# coding: utf-8

import logging
import os

from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from google.appengine.ext import webapp
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

from django.conf import settings
# Force Django to reload settings
settings._target = None

from google.appengine.ext.webapp import util
from google.appengine.api import users
from django.utils import simplejson
from django.utils import translation

from util import I18NRequestHandler

openIdProviders = (
    'Google.com/accounts/o8/id',
    'Yahoo.com',
    'MySpace.com',
    'AOL.com',
    'MyOpenID.com',
    'flickr.com',
    'wordpress.com',
    'myvidoop.com',
    'pip.verisignlabs.com'
)

#class MainPage(webapp.RequestHandler):
class MainPage(I18NRequestHandler):
    def get(self):
        #imports
        from models import Class, Task, Book
        from datetime import date
        
        #get current User
        user = users.get_current_user()
        
        #Check if user wants to change the language
        cookie_django_language = self.request.get('language', '')
        if cookie_django_language:
            if cookie_django_language == 'unset':
                del self.request.COOKIES['django_language']
            else:
                self.request.COOKIES['django_language'] = cookie_django_language
            self.reset_language()

        if user:
            classes = Class.all().order("exam").filter('user ==',user).filter('exam >', date.today())
            logoutlink = users.create_logout_url(self.request.uri)
            books = Book.all().filter('user ==',user)
            inline = Task.all().order("enddate").filter('state ==','Offen').filter('user ==',user).filter('enddate >', date.today())
            urgent = Task.all().order("enddate").filter('state ==','Offen').filter('user ==',user).filter('enddate <=', date.today())
            template_values = {
                           'books' : books,
                           'title':'Task Management',
                           'user' : user.email(),
                           'tasks': inline,
                           'urgent': urgent,
                           'logout' : logoutlink,
                           'classes': classes
                           }
            path = os.path.join(os.path.dirname(__file__), 'templates', "index.html")
            self.response.out.write(template.render(path, template_values).decode('utf-8'))
        else:
            providers = []
            for p in openIdProviders:
                p_name = p.split('.')[0].lower()
                p_url = p.lower()
                providers.append([users.create_login_url(federated_identity=p_url), p_name])
            template_values = { 
                           'providers' : providers,
            }
            path = os.path.join(os.path.dirname(__file__), 'templates', "login.html")
            self.response.out.write(template.render(path, template_values).decode('utf-8'))
    
    def post(self):
        from datetime import datetime, date
        from models import Task, Book, Class
        user = users.get_current_user()
        from cgi import escape
        
        type = escape(self.request.get('type'))
        
        if type == 'task':
            if self.request.get('description'):
                beschreibung = self.request.get('description')
            else:
                beschreibung = _("Keine Beschreibung vorhanden")
            classname = escape(self.request.get('class'))
            if classname == "":
                color = 'gray'
                classname = 'None'
            else:
                colors = Class.all().filter('user ==',user).filter('name ==',self.request.get('class'))
                for c in colors:
                    color = c.color
            if self.request.get('homework') == "checked":
                home = True
            else:
                home = False
            try:
                enddate = datetime.strptime(self.request.get('enddate'),"%d.%m.%Y %H:%M")
            except:
                try:
                    enddate = datetime.strptime(self.request.get('enddate'),"%d.%m.%Y")
                except:
                    enddate = datetime.strptime("1.1.1970","%d.%m.%Y")

            entry = Task( 
                title = escape(self.request.get('name').replace('/','-')),
                classname = classname,
                color = color,
                homework = home,
                state = "Offen",
                user = user,
                text = beschreibung,
                enddate = enddate
            )
            entry.put()
            self.redirect('/')
        if type == 'class':
            if escape(self.request.get('preexam')) == "checked":
                preexam = True
            else:
                preexam = False
            try:
                examdate = datetime.strptime(escape(self.request.get('exam')),"%d.%m.%Y")
            except:
                try:
                    examdate = datetime.strptime(escape(self.request.get('exam')),"%d.%m.%Y %H:%M")
                except:
                    self.redirect('/')
                #better solution needed!
            entry = Class( 
                name = escape(self.request.get('name')),
                color = escape(self.request.get('color')),
                semester = int(escape(self.request.get('semester'))),
                preexam = preexam,
                user = user,
                exam = examdate
            )
            entry.put()
            self.redirect('/')
        if type == 'book':
            import re
            from models import Book, Chapter
            skentry = Book(
                            title = self.request.get('name'),
                            classname = self.request.get('class'),
                            user = user
                           )
            skentry.put()
            index = escape(self.request.get('index'))
            pfound = re.compile('(\d*(\.\d*)*)\s(.+?)(\.{2,}|\s|(\.\s)+)(\d+)')
            for line in index.split('\n'):
                found = pfound.search(line)
                try:
                    name = found.group(3)
                    number = found.group(1)
                    entry = Chapter(
                                title = name,
                                number = number,
                                user = user,
                                book = self.request.get('name'),
                                state = "offen"
                                )
                    entry.put()
                except:
                    pass
            self.redirect('/')
        self.redirect('/')

class RPCHandler(webapp.RequestHandler):
    """ Allows the functions defined in the RPCMethods class to be RPCed."""
    def __init__(self):
        webapp.RequestHandler.__init__(self)
        self.methods = RPCMethods()

    def post(self):
        args = simplejson.loads(self.request.body)
        func, args = args[0], args[1:]

        if func[0] == '_':
            self.error(403) # access denied
            return

        func = getattr(self.methods, func, None)
        if not func:
            self.error(404) # file not found
            return
        result = func(*args)
        self.response.out.write(simplejson.dumps(result))

class RPCMethods:
    """ Defines the methods that can be RPCed.
    NOTE: Do not allow remote callers access to private/protected "_*" methods.
    """
    def ShowTask(self, *args):
        from models import Task
        user = users.get_current_user()
        tasks = Task.all().filter('user ==',user).filter('title ==', args[0]).filter('classname ==', args[1])
        path = os.path.join(os.path.dirname(__file__), "templates","showtask.html")
        template_values = { 'tasks': tasks }
        code = template.render(path, template_values).decode('utf-8')
        return code

    def AddTask(self, *args):
        from datetime import date
        from models import Class
        user = users.get_current_user()
        classes = Class.all().order("exam").filter('user ==',user).filter('exam >', date.today())
        path = os.path.join(os.path.dirname(__file__), "templates","addtask.html")
        template_values = { 'classes': classes }
        code = template.render(path, template_values).decode('utf-8')
        return code
    
    def AddClass(self, *args):
        path = os.path.join(os.path.dirname(__file__), "templates", "addmodul.html")
        code = template.render(path, "").decode('utf-8')
        return code
    
    def AddBook(self, *args):
        path = os.path.join(os.path.dirname(__file__), "templates", "addbook.html")
        template_values = { 'classname' : args[0] }
        code = template.render(path, template_values).decode('utf-8')
        return code
    
    def ShowBook(self, *args):
        from models import Chapter
        user = users.get_current_user()
        chapters = Chapter.all().filter('user ==',user).filter('book ==',args[0]).order('number')
        done = Chapter.all().filter('user ==',user).filter('book ==',args[0]).filter('state =', "Fertig")
        
        try:
            percent = done.count() * 100 / chapters.count()
        except:
            percent = 0
        template_values = { 'classcolor': args[1],
                            'bookname' : args[0],
                            'percent' : percent,
                            'chapters' : chapters
                             }
        path = os.path.join(os.path.dirname(__file__), "templates", "showindex.html")
        code = template.render(path, template_values).decode('utf-8')
        return code
    
    def CheckChapter(self, *args):
        from models import Chapter
        bookname = args[0].replace('%20', ' ')
        chapter = args[1].replace('%20', ' ')
        user = users.get_current_user()
        q = Chapter.all().filter('user ==',user).filter('book ==',bookname).filter('title ==',chapter)
        results = q.fetch(1)
        if len(results) == 0:
            chapter = chapter+" "
            q = Chapter.all().filter('user ==',user).filter('book ==',bookname).filter('title ==',chapter)
            results = q.fetch(1)
        for result in results:
            result.state = "Fertig"
            result.put()
            break
        return self.ShowBook(bookname,args[2])
    
    def DeleteTask(self, *args):
        from google.appengine.ext import db
        from models import Task
        from google.appengine.api import users
        classname = args[0].replace('%20', ' ')
        taskname = args[1].replace('%20', ' ')
        user = users.get_current_user()
        q = Task.all().filter('user ==',user).filter('title ==',taskname).filter('classname ==',classname)
        results = q.fetch(1)
        for result in results:
            result.delete()
        return self.RefreshTasks()

    def DeleteClass(self, *args):
        from google.appengine.ext import db
        from models import Task, Class, Book, Chapter
        from google.appengine.api import users
        user = users.get_current_user()
        classname = args[0].replace('%20', ' ')
        #Deleting all Tasks for this Module
        q = Task.all().filter('user ==',user).filter('classname ==',classname)
        results = q.fetch(10)
        for result in results:
            result.delete()
        #Deleting all the Scripts and Chapters from this Module
        qq = Book.all().filter('user ==',user).filter('classname ==',classname)
        books = qq.fetch(10)
        for book in books:
            qqq = Chapter.all().filter('book ==', book.title).filter('user ==',user)
            for chapter in qqq:
                chapter.delete()
            book.delete()
        #Deleting the Module itself
        qqqq = Class.all().filter('user ==',user).filter('name ==',classname)
        results = qqqq.fetch(10)
        for result in results:
            result.delete()
        return self.RefreshClasses()
    
    def RefreshTasks(self):
        from models import Class, Task, Book
        from datetime import date
        user = users.get_current_user()
        inline = Task.all().order("enddate").filter('state ==','Offen').filter('user ==',user).filter('enddate >', date.today())
        urgent = Task.all().order("enddate").filter('state ==','Offen').filter('user ==',user).filter('enddate <=', date.today())
        template_values = { 
                           'tasks': inline,
                           'urgent': urgent,
                           }
        path = os.path.join(os.path.dirname(__file__), "templates", "tasklist.html")
        code = template.render(path, template_values).decode('utf-8')
        return code

    def RefreshClasses(self):
        from models import Class, Task, Book
        from datetime import date
        user = users.get_current_user()
        books = Book.all().filter('user ==',user)
        classes = Class.all().order("exam").filter('user ==',user).filter('exam >', date.today())
        template_values = {
                           'books' : books,
                           'classes': classes
                           }
        path = os.path.join(os.path.dirname(__file__), "templates", "listmoduls.html")
        code = template.render(path, template_values).decode('utf-8')
        return code
    
    def CheckTask(self, *args):
        from google.appengine.ext import db
        from models import Task, Book
        user = users.get_current_user()
        name = args[0].replace('%20', ' ')
        classname = args[1].replace('%20', ' ')
        q = Task.all().filter('user ==',user).filter('title ==',name).filter('classname ==',classname)
        results = q.fetch(10)
        for result in results:
            result.state = "Fertig"
            result.put()
        return self.RefreshTasks()

    def DeleteBook(self, *args):
        from google.appengine.ext import db
        from models import Class, Book, Chapter
        from google.appengine.api import users
        user = users.get_current_user()
        classname = args[0].replace('%20', ' ')
        bookname = args[1].replace('%20', ' ')
        qq = Book.all().filter('user ==',user).filter('classname ==',classname).filter('title ==',bookname)
        books = qq.fetch(10)
        for book in books:
            qqq = Chapter.all().filter('book ==', book.title).filter('user ==',user)
            for chapter in qqq:
                chapter.delete()
            book.delete()
            break
        return self.RefreshClasses()

def main():
    app = webapp.WSGIApplication([
        ('/', MainPage),
        ('/rpc', RPCHandler),
        ], debug=True)
    util.run_wsgi_app(app)

if __name__ == '__main__':
    main()