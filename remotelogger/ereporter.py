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

"""A client logger that records information about unique exceptions

'Unique' in this case is defined as a given (exception class, location) tuple.
Unique exceptions are logged to the datastore with an example stacktrace and an
approximate count of occurrences, grouped by day and application version.

A cron handler, report_generator, constructs
and emails a report based on the previous day's exceptions.

Example usage:

In your handler script(s), add:

  from clientloggerreporter.ereporter import ClientErrorHandler
  reporter = ClientErrorHandler(3)
  
  then use it this way:
  reporter.log(error)
  where error is a dictionary containing the error information

In your app.yaml, add:

  handlers:
  - url: /_ereporter/.*
    script: clientloggerreporter/report_generator.py
    login: admin

In your cron.yaml, add:

  cron:
  - description: Daily exception report
    url: /_ereporter?sender=you@yourdomain.com
    schedule: every day 00:00

This will cause a daily exception report to be generated and emailed to all
admins, with exception traces grouped by version. For other valid query string
arguments, see report_generator.py.


"""

import datetime
import sha

import copy

from google.appengine.api import memcache
from google.appengine.ext import db

from remotelogger import config

MAX_SIGNATURE_LENGTH = 256

def getTodayDate():
    now = datetime.datetime.utcnow()
    if now.hour < config.dayStartingHour: # SHOULD ultimately deal with timezone and DST
        today = datetime.date.today() - datetime.timedelta(days=1)
    else:    
        today = datetime.date.today()
    return today

class ClientErrorRecord(db.Model):
  """Datastore model for a record of a unique exception."""

  signature = db.StringProperty(required=True)
  
  runtime = db.StringProperty(required=True)
  clientId = db.StringProperty(required=True)
  clientVersion = db.StringProperty(required=True)
  
  userId = db.StringProperty(required=True)
  userName = db.StringProperty(required=True)
  
  errorType = db.StringProperty(required=True)
  errorMessage = db.StringProperty(required=True)
  stacktrace = db.TextProperty(required=True)
  
  reportDate = db.DateProperty(required=True)
  actualDateTime = db.DateTimeProperty(required=True)
  
  count = db.IntegerProperty(required=True, default=0)


  @classmethod
  def get_key_name(cls, signature, version, date=None):
    """Generates a key name for an exception record.

    Args:
      signature: A signature representing the exception and its site.
      version: The major/minor version of the app the exception occurred in.
      date: The date the exception occurred.

    Returns:
      The unique key name for this exception record.
    """
    if not date:
      date = getTodayDate()
    return '%s@%s:%s' % (signature, date, version)

class ClientErrorHandler:
  def __init__(self, log_interval=10):
      """
      Constructs a new ExceptionRecordingHandler.
      Args:
      log_interval: The minimum interval at which we will log an individual
        exception. This is a per-exception timeout, so doesn't affect the
        aggregate rate of exception logging, only the rate at which we record
        ocurrences of a single exception, to prevent datastore contention.
      """
      self.log_interval = log_interval
    
  @classmethod
  def __GetSignature(cls, error):
      
      errorEssence = copy.copy(error)
      # do not care about :
      #errorEssence['userId']=''
      #errorEssence['userName']=''
      errorEssence['clientVersion'] = ''
      
      errorEssence = errorEssence.__repr__()
      return 'hash:%s' % sha.new(errorEssence).hexdigest()
    
  def log(self, error):
    """Log an error to the datastore, if applicable.
    """
    signature = self.__GetSignature(error)

    if not memcache.add(signature, None, self.log_interval):
      return

    db.run_in_transaction_custom_retries(1, self.__EmitTx, signature, error)
      
  def __EmitTx(self, signature, error):
    """Run in a transaction to insert or update the record for this transaction.

    Args:
      signature: The signature for this exception.
      exc_info: The exception info record.
    """
    key_name = ClientErrorRecord.get_key_name(signature, error['clientVersion'])

    exrecord = ClientErrorRecord.get_by_key_name(key_name)
    if not exrecord:
      exrecord = ClientErrorRecord(
          key_name=key_name,
          signature=signature,
          runtime=error['runtime'],
          clientId=error['clientId'],
          clientVersion=error['clientVersion'],
          userId=error['userId'],
          userName=error['userName'],
          errorType=error['errorType'],
          errorMessage=error['errorMessage'],
          stacktrace=error['stacktrace'],
          reportDate=getTodayDate(),
          actualDateTime=datetime.datetime.now()
          )

    exrecord.count += 1
    exrecord.put()

