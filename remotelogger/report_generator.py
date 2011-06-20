#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Generates and emails daily exception reports.

Valid query string arguments to the report_generator script include:
delete:   Set to 'false' to prevent deletion of exception records from the
          datastore after sending a report. Defaults to 'true'.
debug:    Set to 'true' to return the report in the response instead of
          emailing it.
date:     The date to generate the report for, in yyyy-mm-dd format. Defaults to
          yesterday's date. Useful for debugging.
          Can also use date=today to show today logs
max_results: Maximum number of entries to include in a report.
sender:   The email address to use as the sender. Must be an administrator.
to:       If specified, send reports to the addresses specified. 
          If not specified, get Application suscribers from the datastore
          if none all admins are sent the report.
"""

import itertools
import os
import re
from xml.sax import saxutils
import datetime

from google.appengine.dist import use_library

use_library('django', '1.2')

from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from remotelogger import ereporter
from remotelogger.logs_email import Application
from remotelogger import config

def isTrue(val):
  """Determines if a textual value represents 'true'.

  Args:
    val: A string, which may be 'true', 'yes', 't', '1' to indicate True.
  Returns:
    True or False
  """
  val = val.lower()
  return val == 'true' or val == 't' or val == '1' or val == 'yes'


class ReportGenerator(webapp.RequestHandler):
  """Handler class to generate and email an exception report."""

  DEFAULT_MAX_RESULTS = 1000

  def __init__(self, send_mail=mail.send_mail,
               mail_admins=mail.send_mail_to_admins):
    super(ReportGenerator, self).__init__()


    self.send_mail = send_mail
    self.send_mail_to_admins = mail_admins

  def GetQuery(self, order=None):
    """Creates a query object that will retrieve the appropriate exceptions.

    Returns:
      A query to retrieve the exceptions required.
    """
    q = ereporter.ClientErrorRecord.all()
    q.filter('reportDate =', self.yesterday).filter('clientId =', self.client_id)
    
    if order:
      q.order(order)
    return q

  def GenerateReport(self, exceptions):
    """Generates an HTML exception report.

    Args:
      exceptions: A list of ExceptionRecord objects. This argument will be
        modified by this function.
    Returns:
      An HTML exception report.
    """

    exceptions.sort(key=lambda e: (e.clientVersion, e.count), reverse=True)
    versions = [(minor, list(excs)) for minor, excs
                in itertools.groupby(exceptions, lambda e: e.clientVersion)]

    template_values = {
        'version_count': len(versions),

        'exception_count': sum(len(excs) for _, excs in versions),

        'occurrence_count': sum(y.count for x in versions for y in x[1]),
        'client_id': self.client_id,
        'reportDate': self.yesterday,
        'versions': versions,
    }
    path = os.path.join(os.path.dirname(__file__), 'templates', 'report.html')
    return template.render(path, template_values)

  def SendReport(self, report):
    """Emails an exception report.

    Args:
      report: A string containing the report to send.
    """
    subject = ('Daily exception report for "%s"' % (self.client_id))
    report_text = saxutils.unescape(re.sub('<[^>]+>', '', report))
    mail_args = {
        'sender': self.sender,
        'subject': subject,
        'body': report_text,
        'html': report,
    }
    if self.to:
      mail_args['to'] = self.to
      self.send_mail(**mail_args)
    else:
      ## get emaisl from the Suscribers list:
      app = Application.get_by_key_name(self.client_id)
      if app and len(app.emailSuscribers) > 0:
          mail_args['to'] = ",".join(app.emailSuscribers)
          self.send_mail(**mail_args)
      else:
          self.send_mail_to_admins(**mail_args)

  def get(self):
    ### mandatory :
    self.client_id = self.request.GET['client_id']
    #################################################
    
    self.sender = self.request.GET.get('sender', config.suscribeEmail)
    self.to = self.request.GET.get('to', None)
    report_date = self.request.GET.get('date', None)
    if report_date:
      if report_date == 'today':
          self.yesterday = datetime.date.today()
      else:
          self.yesterday = datetime.date(*[int(x) for x in report_date.split('-')])
    else:
      self.yesterday = datetime.date.today() - datetime.timedelta(days=1)
    self.max_results = int(self.request.GET.get('max_results', self.DEFAULT_MAX_RESULTS))
    self.debug = isTrue(self.request.GET.get('debug', 'false'))
    self.delete = isTrue(self.request.GET.get('delete', 'true'))

    exceptions = self.GetQuery().fetch(self.max_results)
    
    if exceptions:
      report = self.GenerateReport(exceptions)
      if self.debug:
        self.response.out.write(report)
      else:
        self.SendReport(report)


      if self.delete:
        db.delete(exceptions)


application = webapp.WSGIApplication([('.*', ReportGenerator)])


def main():
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
