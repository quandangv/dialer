from common import *
import concurrent.futures
import requests

parser.add_argument('campaigns', metavar='CAMPAIGN', nargs='+', help='name of campaigns to pull recordings')
args = parse_args()

### CHANGE: custom start and end time
end_day = datetime.date.today() - datetime.timedelta(days=0)
start_day = datetime.date.today() - datetime.timedelta(days=20)
day_start = datetime.datetime.combine(start_day, datetime.time(), pytz.utc).astimezone(remote_timezone).isoformat()[:19]+'Z'
day_end = datetime.datetime.combine(end_day, datetime.time(23, 59, 59), pytz.utc).astimezone(remote_timezone).isoformat()[:19]+'Z'

### CHANGE: specific agent name
def get_all_agent_ids():
  return [str(agent['id']) for agent in request_json('Users/GetAllAgents') if agent['firstName'] == 'Eli']

import warnings
def find_campaign_ids(names):
  result = []
  name_hits = []
  response = request_json('Campaigns/GetAllCampaigns', 'POST', data='{"customerID": "1", "userID": "2"}')
  for campaign in response:
    if campaign['name'] in names:
      name_hits.append(campaign['name'])
      result.append(str(campaign['id']))
  for name in names:
    if not name in name_hits:
      warnings.warn('Found no hit for campaign: ' + name)
  return result

agents_str = ','.join(get_all_agent_ids())
campaigns_str = ','.join(find_campaign_ids(args.campaigns))
def get_history(dispositions):
  page_number = 1
  while True:
    data = '{"selectedCampaignIDs":"'+campaigns_str+'","startDate":"'+day_start+'","endDate":"'+day_end+'","pageSize":25,"pageNumber":'+str(page_number)+',"selectedListsIDs":"","selectedDispositionIDs":"'+dispositions+'","selectedUserIDs":"'+agents_str+'","name":"","voicePhone":"","firstName":"","lastName":"","company":"","hasRecordings":true}'
    response = request_json('History/GetHistoryByPage', 'POST', data=data)
    yield from response['results']
    page_number += 1
    if page_number > response['pageCount']:
      break

import pathlib
import shutil
print('Deleting old records')
root_dir = 'recordings/' + today.strftime('%m-%d-%Y')
shutil.rmtree(root_dir, ignore_errors=True)
pathlib.Path(root_dir + '/appointments').mkdir(parents=True, exist_ok=True)
pathlib.Path(root_dir + '/ambassadors').mkdir(exist_ok=True)

names = {}
def download_record(record, prefix):
  format_name = lambda name: name.lower().replace(' and ', '&').replace(' ', '')
  name = format_name(record['firstName']) + '-' + format_name(record['lastName'])
  if name == '-':
    name = record['name'].lower().replace(' ', '-')
  if name in names:
    names[name] += 1
    name += '-' + names[name]
  else:
    names[name] = 1
  print('Downloading ' + name)
  with open(prefix+name+'.wav', "wb") as f:
    f.write(requests.get(record['recordingUrl']).content)

appointment_dispositions = '31,32'
ambassador_disposition = '30'
longcall_dispositions = '45,46,24,19,50,41,17'

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
  futures = []
  def add_recording_source(path, dispositions, min_length = None):
    new_futures = [executor.submit(download_record, record, root_dir + path) for record in get_history(dispositions) if min_length == None or int(record['callLength']) >= min_length]
    print(len(new_futures), 'in', path)
    global futures
    futures += new_futures
  add_recording_source('/appointments/', appointment_dispositions)
  add_recording_source('/ambassadors/', ambassador_disposition)
  add_recording_source('/', longcall_dispositions, 200)

  for future in concurrent.futures.as_completed(futures):
    future.result()
