import requests
import json
import time
import os
import sys


API_URI = "https://api.hypixel.net"
HYPIXEL_API_KEY=os.environ['HYPIXEL_API_KEY']
DB_AUTH=os.environ['DB_AUTH']
UUID_ENDPOINT="https://api.mojang.com/users/profiles/minecraft/"
DATABASE_URL=os.environ["DB_URL"]
TRACKED_PLAYERS = [
    {"ign": "shiningshadow777","profile": "pineapple","profile_id": "5b22f04c-6eda-424d-837d-19cf46c61795"},
    {"ign": "TNTOJ","profile": "apple","profile_id": "8cddfad0-ad7d-4d8b-a37b-5e0230552f3c"},
    {"ign": "Splatingo","profile": "pear","profile_id": "4be44f73-119f-4592-9bac-d6ace167d412"},
    {"ign": "oAesthetic","profile": "kiwi","profile_id": "e480cc90-c910-4454-8b03-d20346b715bf"},
    {"ign": "Spooky_Possum","profile": "lemon","profile_id": "f7e6e24f-6c3e-45b1-89ca-f52921f2fa4f"},
    {"ign": "Iskipsecrets","profile": "papaya","profile_id": "8e7282e2-3e35-459c-b79f-d3547889d3e5"},
    {"ign": "GorillagirlSyzee","profile": "lemon","profile_id": "2e4cc63a-b5c5-4b97-9fd3-4d479e3caef8"},
    {"ign": "X1VK","profile": "kiwi","profile_id": "3409c1fa-21ad-4369-95ab-e03b256cbea7"},
    {"ign": "Genade","profile": "pomegranate","profile_id": "8e80245e-7c09-4d4d-8f8e-39321084b58b"}
]
DEFAULT_INTERVAL = 60*30 # half an hour
actual_interval = DEFAULT_INTERVAL
active_tries = 0

def stopInstance(): # sys.exit doesn't seem to work in certain environnements, but this should also work as it's a single thread program
    print("Exited instance")
    while True:
        time.sleep(60)

def HYPIXEL_API_REQ(path):
    return requests.get(API_URI+path,timeout=30,headers={"API-Key": HYPIXEL_API_KEY})

for player in TRACKED_PLAYERS:
    r = requests.get(UUID_ENDPOINT+player['ign'],timeout = 30,allow_redirects=False)
    if not r.ok:
        print("Req for UUID failed (" + str(r.status_code) + ": " + r.reason + "): " + r.text)
        stopInstance()
    res = json.loads(r.text)
    try:
        player['uuid'] = res["id"]
    except:
        print("Req for UUID failed: return doesn't have the 'id' property: " + r.text)
    r.close()

for player in TRACKED_PLAYERS:
    if "profile_id" in player:
        if player['profile_id'] != "":
            print("Already have profile id for " + player['ign'] + ": " + player['profile'])
            continue
    r = HYPIXEL_API_REQ("/skyblock/profiles?uuid=" + player["uuid"])
    if not r.ok:
        print("Req for profiles failed (" + str(r.status_code) + ": " + r.reason + "): " + r.text)
        stopInstance()
    res = json.loads(r.text)
    if not res['success']:
        print("Req for Profile id failed failed (" + str(r.status_code) + ": " + r.reason + "): " + r.text)
        stopInstance()
    for p in res['profiles']:
        if p['cute_name'].lower() == player['profile'].lower():
            player['profile_id'] = p['profile_id']
            break
    if "profile_id" not in player:
        print("Couldn't find profile '" + player['profile'] + "' for " + player['ign'])
        stopInstance()
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
    print("Successfully wrote the sent data to sent_data.json")
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

        
        
        sc = None
        
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
        stopInstance()
    if not fetch_data():
        active_tries+=1
        actual_interval = 300 # try again 5 minutes later
        print("Error fetching profile info, trying again in " + str(actual_interval) + " seconds")
    else:
        actual_interval = DEFAULT_INTERVAL
    print("---------------------------------------")
    time.sleep(actual_interval)
