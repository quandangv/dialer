from common import *
import traceback
import random

high_drop_percent = 10
critical_drop_percent = 20
high_wait = 120
critical_wait = 240
max_break = 1200
max_other = 600

prev_drop_percent = {}

def set_dial_ratio(campaign, value):
  name = campaign['campaignName']
  if value < 1.5 or value > 9:
    print('CRITICAL', 'Attempting to set dial ratio of', name, 'to', value)
    return True
  else:
    print('Setting dial ratio of', name, 'to', value)
    data = {
      "customerID":1,
      "userID":2,
      "campaignID":campaign["campaignID"],
      "name":name,
      "isLive":campaign['isLive'],
      "dialRatio":value,
      "algorithmType":campaign["algorithmType"],
      "autoStart":campaign["autoStart"]
    }
    request_json('Campaigns/UpdateCampaignProperties', 'POST', data=json.dumps(data))

#def get_base_result(*args, **kwargs):
#  response = request_json(*args, **kwargs)
#  if 'baseResult' in respose:
#    return response['baseResult']

from datetime import datetime
import time
def monitor(campaigns):
  campaign_set = set(campaigns)
  prev_agent_errors = {}
  prev_agent_login_errors = []
  sleep_time = 30
  campaign_check_interval = 900
  campaign_check_time = 0
  number_change_interval = 850
  number_change_rand = 100
  number_change_time = number_change_interval
  number_change_time = 0
  started = False

  first_campaign_id = request_json('Campaigns/GetAllCampaigns', 'POST', data='{"customerID":1,"userID":2,"campaignID":0}')
  first_campaign_id = str(next(campaign['id'] for campaign in first_campaign_id if campaign['name'] == campaigns[0]))
  if 'Nevada' in campaigns[0]:
    dclid_profiles = ['2121', '2125', '2129', '2133', '2136', '2140', '2144', '2145', '2148', '2152']
  elif 'California' in campaigns[0]:
    dclid_profiles = ['2211', '2212', '2215', '2217', '2220', '2221', '2223', '2226', '2229', '2232']
  elif 'Texas' in campaigns[0]:
    dclid_profiles = ['2233', '2236', '2238', '2241', '2242', '2245', '2247', '2250', '2251', '2253']
  else:
    raise Exception("Can't find dclid_profile for first campaign")
  dclid_index = request_json('Campaigns/GetCampaignbyID', 'POST', data='{"customerID":1,"userID":2,"campaignID":"'+first_campaign_id+'"}')
  dclid_index = dclid_index['baseResult']['dialSettings']['dclidProfileIDs']
  dclid_index = dclid_profiles.index(dclid_index)
  try:
    while True:
      something_wrong = False
      agent_errors = {}
      agent_login_errors = []

      def print_msg(critical, *args):
        if critical:
          nonlocal something_wrong
          something_wrong = True
          print('CRITICAL', *args)
        else:
          print(*args)

      agents = request_json('Agent/GetAllAgentStats', 'POST', data='{"customerID": "1", "userID": "2"}')['baseResult']
      raise_dial_ratio = False
      if agents:
        started = True
        for agent in agents:
          status = agent['agentStatus']
          name = agent['name']
          if status != 'TalkingToCustomer':
            duration = datetime.strptime(agent['lastStatusTime'], "%H:%M:%S")
            seconds = duration.hour*3600 + duration.minute*60 + duration.second
            wrong = False
            if status == 'Break' or agent['breakType'] != '':
              wrong = seconds > max_break
              status = 'Break'
            elif status == 'WaitingForCall':
              if seconds > critical_wait:
                wrong = True
              elif seconds > high_wait:
                print(name, 'is', status, 'for', agent['lastStatusTime'])
                raise_dial_ratio = True
            else:
              wrong = seconds > max_other
            if wrong:
              agent_errors[name] = status
              print_msg(status != prev_agent_errors.get(name), name + ' is ' + status + ' for ' + agent['lastStatusTime'])
      elif started:
        something_wrong = True
        print('CRITICAL', 'All agents are offline')

      if started:
        if number_change_time >= number_change_interval:
          dial_settings = request_json('Campaigns/GetCampaignbyID', 'POST', data='{"customerID":1,"userID":2,"campaignID":"'+first_campaign_id+'"}')['baseResult']['dialSettings']
          dclid_index = dial_settings['dclidProfileIDs']
          dclid_index = dclid_profiles.index(dclid_index)
          dclid_index = (dclid_index + 1) % len(dclid_profiles)
          dial_settings['dclidProfileIDs'] = str(dclid_profiles[dclid_index])
          result = request_json('Campaigns/UpdateCampaignDialSettings', 'POST', data=json.dumps({'campaignID':first_campaign_id, 'customerID':'1', 'userID':'2', 'settings':dial_settings}))['baseResult']
          if 'result' in result and result['result'] == 'Success':
            print('ALERT')
            print('ALERT')
            print('Changed numbers to id', dial_settings['dclidProfileIDs'])
            number_change_time = -random.randint(0, number_change_rand)
          else:
            print('ERROR attempt to change number returns result:', result)
          something_wrong = True
        number_change_time += sleep_time

      #if campaign_check_time >= campaign_check_interval:
      #  campaign_check_time = 0
      #  for agent in agents:
      #    logged_in = request_json('Users/GetAgentCampaignList', 'POST', data='{"customerID": "1", "userID": "2", "agentID": '+str(agent['userID'])+'}')['baseResult']
      #    if not campaign_set <= set(logged_in):
      #      agent_login_errors.append(name)
      #      print_msg(not name in prev_agent_login_errors, name, 'is only logged into', ', '.join(logged_in))
      #  prev_agent_login_errors = agent_login_errors

      for campaign in request_json('Campaigns/GetAllCampaignStats', 'POST', data='{"customerID":1,"userID":2}')['baseResult']:
        name = campaign['campaignName']
        if name == campaigns[0] and raise_dial_ratio:
          set_dial_ratio(campaign, campaign['dialRatio'] + 0.7)
        if name in campaign_set:
          drop_percent = float(campaign['campaignStats']['dropPercent'])
          if drop_percent > high_drop_percent:
            if drop_percent > prev_drop_percent.get(name, 0):
              print_msg(drop_percent > critical_drop_percent, name + ' have drop percent of ' + str(drop_percent))
              set_dial_ratio(campaign, campaign['dialRatio'] - 0.5)
            else:
              print(name + ' have drop percent of ' + str(drop_percent))
          status = campaign['campaignStatus']
          prev_drop_percent[name] = drop_percent
          if status != 'Executing':
            print('CRITICAL', name + ' is ' + status)
            something_wrong = True

      if something_wrong:
        grab_attention()
      elif not started:
        print('Not started yet')
      else:
        print(f'No serious issues, {len(agents)} online, {number_change_interval - number_change_time} secs until change')
      prev_agent_errors = agent_errors
      time.sleep(sleep_time)
      campaign_check_time += sleep_time
  except:
    traceback.print_exc()
    grab_attention()

if __name__ == "__main__":
  parser.add_argument('--ignore', nargs='*', default=[], help='ignored campaigns')
  parser.add_argument('campaigns', metavar='CAMPAIGN', nargs='+', help='name of campaigns that all agents have to log in')
  args = parse_args()
  playsound('ping.wav')
  monitor(args.campaigns)
