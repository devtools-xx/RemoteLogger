from google.appengine.ext import webapp 
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler 
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import mail

import logging
import string

from remotelogger import config

class Application(db.Model):
    emailSuscribers = db.StringListProperty(required=True)

class EmailSubscribtionHandler(InboundMailHandler):
    def receive(self, mail_message):
        if (
            not config.onlyDomain
            or mail_message.sender.find("@" + config.onlyDomain) != -1
            or mail_message.sender in config.whiteList
            ):
                messageData = string.split(mail_message.subject, ':')
                action = messageData[0]
                if len(messageData) > 1:
                    client_id = messageData[1]
                else:
                    client_id = None
                (logMessage, replySubject, replyBody) = self.processMessage(action.lower(), client_id, mail_message.sender)
                logging.info(logMessage)
                mail.send_mail(sender=config.suscribeEmail,
                        to=mail_message.sender,
                        subject=replySubject,
                        body=replyBody)
    
    def processMessage(self, action, client_id, sender):
        if client_id:
            app = Application.get_by_key_name(client_id)
            if not app:
                if client_id in config.allowedClientIds:
                    app = Application(key_name=client_id, emailSuscribers=[])
                    isSenderSuscribed = False
                else:
                    return ("clientId : '%s' is not allowed" % (client_id)  , "clientId : '%s' is not allowed" % (client_id), "clientId : '%s' is not allowed" % (client_id))
            else:
                isSenderSuscribed = sender in set(app.emailSuscribers)
            
            if action == "suscribe":
                logging.info("Received a subscribtion request for %s by %s : " % (client_id, sender))
                if isSenderSuscribed:
                    logMessage = "already in the suscribed list: " + sender
                    replySubject = "You are already in the suscribe list of %s" % (client_id)
                    replyBody = replySubject
                
                else:
                    app.emailSuscribers.append(sender)
                    app.put()
                    logMessage = "adding %s to the suscribed list of %s" % (sender, client_id)
                    replySubject = "You have been added to the suscribed list of %s" % (client_id)
                    replyBody = "You have been added to the suscribed list of %s, to unsuscribe, just send a message with subject: 'unsuscribe:%s'" % (client_id, client_id)
             
            elif action == "unsuscribe":
                logging.info("Received a request to unsuscribe for %s by %s : " % (client_id, sender))
                if isSenderSuscribed:
                    app.emailSuscribers.remove(sender)
                    app.put()
                    logMessage = "removing from the suscribed list: " + sender
                    replySubject = "You have been unsuscribed from %s" % (client_id)
                    replyBody = "You have been unsuscribed from %s, to suscribe again, just send a message with subject: 'suscribe:%s'" % (client_id, client_id)
                    
                else:
                    logMessage = "not on the suscribed list: " + sender
                    replySubject = "You are not in the suscribe list of %s" % (client_id)
                    replyBody = replySubject
                    
            else:
                logMessage = "message subject not recognized " + sender
                replySubject = "message subject not recognized"
                replyBody = "message subject not recognized\nset subject as 'suscribe:<client_id>' where client_id is the app string id sent along side the errors you want to suscribe to\nset subject as 'unsuscribe:<client_id>' to unsuscribe from the app specified"

                               
        else:
            logMessage = "message subject need to specify client_id " + sender
            replySubject = "message subject need to specify client_id"
            replyBody = "message subject need to specify client_id\nset subject as 'suscribe:<client_id>' where client_id is the app string id sent along side the errors you want to suscribe to\nset subject as 'unsuscribe:<client_id>' to unsuscribe from the app specified"
               
        return (logMessage, replySubject, replyBody)
                    
def main():
    application = webapp.WSGIApplication([EmailSubscribtionHandler.mapping()], debug=True)
    run_wsgi_app(application)
    
if __name__ == '__main__':
    main()
    
