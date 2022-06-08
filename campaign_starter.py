from common import *
import traceback
import time

playsound('ping.wav')
parser.add_argument('hour', help='the hour to start the campaigns')
parser.add_argument('campaigns', metavar='CAMPAIGN', nargs='+', help='name of campaigns to start')
args = parse_args()

def get_campaign_ids(names):
  return [str(campaign['id']) for campaign in request_json('Campaigns/GetAllCampaigns', 'POST', data='{"customerID": "1", "userID": "2"}') if campaign['name'] in names]

def start_campaign(id):
  try:
    response = request_json('Campaigns/StartCampaign', 'POST', data='{"customerID": "1", "userID": "2", "campaignID":'+id+'}')
    print(response)
    if response['baseResult']['result'] == 'Error':
      print('Got error: ' + response['message'])
    else:
      print('Started ' + id)
  except Exception:
    traceback.print_exc()

campaign_ids = get_campaign_ids(args.campaigns)
args.hour = int(args.hour)
current_hour = lambda: (datetime.datetime.now() + datetime.timedelta(minutes=20)).hour
while current_hour() != args.hour:
  print('Current hour:', current_hour(), args.hour)
  time.sleep(60)

for id in campaign_ids:
  start_campaign(id)
grab_attention()
