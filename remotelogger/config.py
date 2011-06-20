
onlyDomain = None # if set to a domain name, only email address ending with @<domain name> are allowed to suscribe

whiteList = set([]) ##set(["<email address>", "<email address>"]) # allow extra emails

allowedClientIds = set([]) # set which clientId user can suscribe to

dayStartingHour = 9 # set the hour of teh day where the day start regarding daily report generation (UTC)

suscribeEmail = "logs@test.appspotmail.com" ## set which email to send message to suscribe (need to end with @<app id>.appspotmail.com
# it is also the default sender for the reports
