import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from remotelogger.ereporter import ClientErrorHandler

reporter = ClientErrorHandler(3)

class MainPage(webapp.RequestHandler):
    def post(self):
        error = {'runtime':self.request.get('runtime'),
                'clientId':self.request.get('clientId'),
                'clientVersion':self.request.get('clientVersion'),
                'userId':self.request.get('userId'),
                'userName':self.request.get('userName'),
                'errorType':self.request.get('errorType'),
                'errorMessage':self.request.get('errorMessage'),
                'stacktrace':self.request.get('stacktrace')
                }
        
        if (error['runtime'] 
            and error['clientId'] 
            and error['clientVersion']
            and error['userId']
            and error['userName']
            and error['errorType']
            and error['errorMessage']
            and error['stacktrace']
            ):
            reporter.log(error)
            logMessage = "Client : %s (%s)\nUser : %s (%s)\nError : %s : %s\nstackTrace:\n%s" % (
                                        error['clientId'], error['clientVersion'],
                                        error['userName'], error['userId'],
                                        error['errorType'], error['errorMessage'], error['stacktrace'] 
                                        )
            logging.error(logMessage)

def main():
    logging.getLogger().setLevel(logging.DEBUG)
    application = webapp.WSGIApplication([('/', MainPage)], debug=True)
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
    
