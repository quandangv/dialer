
from playsound import playsound
from pytimedinput import timedKey
def grab_attention():
  while timedKey('Press any key to dismiss alarm.')[1]:
    playsound('ping.wav')

import pytz
import datetime
remote_timezone = pytz.timezone('US/Mountain')
today = datetime.date.today()
#today = datetime.date.fromisoformat('2022-06-09')
print(today)
day_start = datetime.datetime.combine(today, datetime.time(), pytz.utc).astimezone(remote_timezone).isoformat()[:19]+'Z'
day_end = datetime.datetime.combine(today, datetime.time(23, 59, 59), pytz.utc).astimezone(remote_timezone).isoformat()[:19]+'Z'

import argparse
parser = argparse.ArgumentParser(description='Download call recordings from Spitfire.')
parser.add_argument('--auth', help='authentication token')
def parse_args():
  args = parser.parse_args()
  global authorization
  authorization = args.auth or input('Authorization=? ')
  return args

import requests
import json
authorization = ''
api_base = 'https://ethicalenergyexperts.spitfireagent.com/DialServiceAPI/api/'
def request_json(url, method='GET', **kwargs):
  response = requests.request(method, api_base + url, headers={'authorization':authorization, 'content-type':'application/json'}, **kwargs).text
  try:
    return json.loads(response)
  except:
    raise Exception('Unexpected response: ' + response)
