import requests
import json
import time
import os
import sys


API_URI = "https://api.hypixel.net"
HYPIXEL_API_KEY=os.environ['HYPIXEL_API_KEY']
DB_AUTH=os.environ['DB_AUTH']
UUID_ENDPOINT="https://api.mojang.com/users/profiles/minecraft/"
DATABASE_URL="https://www.chassereau.fr/web/db.php"
TRACKED_PLAYERS = [
    {"ign": "shiningshadow777","profile": "Pineapple","profile_id": "5b22f04c-6eda-424d-837d-19cf46c61795"},
    {"ign": "","profile": ""},
    {"ign": "","profile": ""},
    {"ign": "","profile": ""},
    {"ign": "","profile": ""},
    {"ign": "","profile": ""},
    {"ign": "","profile": ""},
    {"ign": "","profile": ""},
]
DEFAULT_INTERVAL = 60*30 # half an hour
actual_interval = DEFAULT_INTERVAL
active_tries = 0

def HYPIXEL_API_REQ(path):
    return requests.get(API_URI+path,timeout=30,headers={"API-Key": HYPIXEL_API_KEY})

for player in TRACKED_PLAYERS:
    r = requests.get(UUID_ENDPOINT+player['ign'],timeout = 30,allow_redirects=False)
    if not r.ok:
        print("Req for UUID failed (" + str(r.status_code) + ": " + r.reason + "): " + r.text)
        sys.exit()
    res = json.loads(r.text)
    try:
        player['uuid'] = res["id"]
    except:
        print("Req for UUID failed: return doesn't have the 'id' property: " + r.text)
    r.close()

for player in TRACKED_PLAYERS:
    if "profile_id" in player:
        print("Already have profile id for " + player['ign'] + ": " + player['profile'])
        continue
    r = HYPIXEL_API_REQ("/skyblock/profiles?uuid=" + player["uuid"])
    if not r.ok:
        print("Req for profiles failed (" + str(r.status_code) + ": " + r.reason + "): " + r.text)
        sys.exit()
    res = json.loads(r.text)
    if not res['success']:
        print("Req for Profile id failed failed (" + str(r.status_code) + ": " + r.reason + "): " + r.text)
        sys.exit()
    for p in res['profiles']:
        if p['cute_name'].lower() == player['profile'].lower():
            player['profile_id'] = p['profile_id']
            break
    if "profile_id" not in player:
        print("Couldn't find profile '" + player['profile'] + "' for " + player['ign'])
        sys.exit()
    print("Found profile id for " + player['ign'] + ", it would be better to store it in the TRACKED_PLAYERS variable: " + player['profile_id'])

print("TRACKED_PLAYERS: ",json.dumps(TRACKED_PLAYERS,indent=4))
print("====================================================")
print("====================================================")
print("====================================================")

def send_data(data):
    xml = """<commands app_role="dungeons" module="skyblock_dungeons" php_session="1">
  <skyblock_dungeons.senddata json="true">""" + json.dumps(data) + """</skyblock_dungeons.senddata>
</commands>"""
    with open("sent_data.json", "w") as f:
        f.write(json.dumps(data,indent=4))
    r = requests.post(DATABASE_URL,data=xml,timeout=30,headers={"Authorization": DB_AUTH})
    if not r.ok:
        print("Req for sending data failed failed (" + str(r.status_code) + ": " + r.reason + "): " + r.text)
        return False
    print("Successfully sent all the data")
    return True

    
def fetch_data():
    url = API_URI + "/skyblock/profile"
    all_data = []
    for player in TRACKED_PLAYERS:
        print("Fetching data for: " + player['ign'])
        r = requests.get(url+"?profile="+player['profile_id'],timeout=30,headers={"API-Key": HYPIXEL_API_KEY})
        if not r.ok:
            print("Req for Profile data failed failed (" + str(r.status_code) + ": " + r.reason + "): " + r.text)
            return False
        res = json.loads(r.text)
        r.close()
        if not res['success']:
            print("Req for Profile data failed failed (" + str(r.status_code) + ": " + r.reason + "): " + r.text)
            return False

        sc = None # will eventually implement fetching secret data as well
        
        try:
            res = res['profile']['members'][player['uuid']]
            res = res['dungeons']
            data = {
                "player": player['ign'],
                "master_completions": res['dungeon_types']['master_catacombs']['tier_completions'],
                "normal_completions": res['dungeon_types']['catacombs']["tier_completions"],
                "experience": res['dungeon_types']['catacombs']['experience'],
                "classes": res['player_classes'],
                "secret_count": sc
            }
            print("Successfuly fetched data for: " + player['ign'])
            all_data.append(data)
        except Exception as error:
            print("Error reading the contents for profile data for " + player['ign'])
            print(error)
            return False
    return send_data(all_data)
        

while True:
    if active_tries >= 3:
        print("Ran out of tries!")
        sys.exit()
    if not fetch_data():
        active_tries+=1
        actual_interval = 300 # try again 5 minutes later
        print("Error fetching profile info")
    else:
        actual_interval = DEFAULT_INTERVAL
    print("---------------------------------------")
    time.sleep(actual_interval)
