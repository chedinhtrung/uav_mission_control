import hashlib
import math
import time
import requests
import random
from time import sleep
import xml.etree.ElementTree as ET
# Get current time in seconds since the epoch


AuthQop, username = "", ""
passwd = ""
GnCount = 1
Authrealm, Gnonce, nonce = None, None, None

session = requests.Session()

def getValue(authstr):
    arr = authstr.split('=')
    value_part = arr[1]
    value = value_part[1:value_part.index('"', 2)]
    return value

def getAuthType(url):
    headers = {
    'Expires': '-1',
    'Cache-Control': 'no-store, no-cache, must-revalidate',
    'Pragma': 'no-cache'
    }
    response = session.get(url, headers=headers)
    content = response.headers.get('WWW-Authenticate')
    return content

def authentication(url):
    headers = {
    'Authorization': getAuthHeader('GET'),
    'Expires': '-1',
    'Cache-Control': 'no-store, no-cache, must-revalidate',
    'Pragma': 'no-cache'
    }

# Make the GET request
    response = session.get(url, headers=headers)

# Get the response text
    content = response.text
    return content

def doLogin(username1, passwd1):
    global passwd, username, Authrealm, nonce, Gnonce, AuthQop
    url = "http://192.168.1.1/login.cgi"
    loginParam = getAuthType(url)
    if loginParam is not None:
        loginParamArray = loginParam.split(" ")
        if loginParamArray[0] == "Digest":
            Authrealm = getValue(loginParamArray[1]);
            nonce = getValue(loginParamArray[2]);
            AuthQop = getValue(loginParamArray[3]);

            print("nonce :" + nonce);
            print("AuthQop :" + AuthQop);
            print("Authrealm :" + Authrealm);

            username = username1
            passwd = passwd1
            rand, date, salt, strResponse = None, None, None, None

            Gnonce = nonce
            tmp, DigestRes = None, None
            HA1, HA2 = None, None

            HA1 = hashlib.md5((username + ":" + Authrealm + ":" + passwd).encode()).hexdigest()
            HA2 = hashlib.md5(("GET" + ":" + "/cgi/protected.cgi").encode()).hexdigest()

            rand = int(random.random() * 100001)
            date = int(time.time() * 1000)

            salt = str(rand) + "" + str(date)
            tmp = hashlib.md5(salt.encode()).hexdigest()
            AuthCnonce = tmp[:16]


            DigestRes = hashlib.md5((HA1 + ":" + nonce + ":" + "00000001" + ":" + AuthCnonce + ":" + AuthQop + ":" + HA2).encode()).hexdigest()

            url = "http://192.168.1.1/login.cgi?Action=Digest&username=" + username + "&realm=" + Authrealm + "&nonce=" + nonce + "&response=" + DigestRes + "&qop=" + AuthQop + "&cnonce=" + AuthCnonce + "&temp=asr"
            print(authentication(url)) 
            strResponse = "Digest username=\"" + username + "\", realm=\"" + Authrealm + "\", nonce=\"" + nonce + "\", uri=\"" + "/cgi/protected.cgi" + "\", response=\"" + DigestRes + "\", qop=" + AuthQop + ", nc=00000001" + ", cnonce=\"" + AuthCnonce + "\""

            return 1
            
    return -1
    
def Login():
    username = "admin"
    password = "admin"
    login_done = None

    if username == "" or password == "":
        login_done = 0

    else:
        login_done = doLogin(username, password)

    if login_done == 1:

        pass

def getAuthHeader(requestType):
    global GnCount
    rand, date, salt, strAuthHeader = None, None, None, None
    tmp, DigestRes, AuthCnonce_f = None,None, None
    HA1, HA2 = None, None



    HA1 = hashlib.md5((username + ":" + Authrealm + ":" + passwd).encode()).hexdigest()
    HA2 = hashlib.md5((requestType + ":" + "/cgi/xml_action.cgi").encode()).hexdigest()

    rand = int(random.random() * 100001)

# Convert seconds to milliseconds
    date = int(time.time() * 1000)

    salt = str(rand) + "" + str(date)
    tmp = hashlib.md5(salt.encode()).hexdigest()
    AuthCnonce_f = tmp[:16]

    strhex = hex(GnCount)
    temp = "0000000000" + strhex
    Authcount = temp[(len(temp) - 8):]
    DigestRes = hashlib.md5((HA1 + ":" + nonce + ":" + Authcount + ":" + AuthCnonce_f + ":" + AuthQop + ":" + HA2).encode()).hexdigest()
    GnCount += 1
    strAuthHeader = "Digest " + "username=\"" + username + "\", realm=\"" + Authrealm + "\", nonce=\"" + nonce + "\", uri=\"" + "/cgi/xml_action.cgi" + "\", response=\"" + DigestRes + "\", qop=" + AuthQop + ", nc=" + Authcount + ", cnonce=\"" + AuthCnonce_f + "\""
    return strAuthHeader


def getData():
    headers = {
    'Authorization': getAuthHeader('GET'),
    'Expires': '-1',
    'Cache-Control': 'no-store, no-cache, must-revalidate',
    'Pragma': 'no-cache'
    }
    response = session.get(url="http://192.168.1.1/xml_action.cgi?method=get&module=duster&file=status1", headers=headers).text
    root = ET.fromstring(response)
    mode = root.find('.//wan/sys_mode')
    if mode is not None:
        mode = mode.text
        if mode == "17":
            mode = "LTE"
        elif mode == "3":
            mode = "GSM"
        elif mode == "5":
            mode = "WCDMA"
        elif mode == "15":
            mode = "TD-SCDMA"
        elif mode == "0":
            mode = "NO SIM CARD"

    sim_stat = root.find('.//wan/cellular/sim_status')
    if sim_stat is not None:
        sim_stat = sim_stat.text
    if sim_stat == "1":
        sim_stat = "NO SIM CARD"
    elif sim_stat == "0":
        sim_stat = "OK"
    
    network_name = root.find('.//wan/network_name')
    if network_name is not None:
        network_name = network_name.text
    phone_number = root.find('.//wan/MSISDN')
    if phone_number is not None:
        phone_number = phone_number.text
    signal_qual = root.find('.//wan/cellular/rssi')
    if signal_qual is not None:
        signal_qual = signal_qual.text   
    # signal qual in range 0 - 25(x), 25-34 (!), 34-43 (!!!), 43-55 (!!!!), 55-97 (!!!!!) for LTE
    # 17-22, 22-27, 27-31, 31-96 for TD-SCDMA and WCDMA
    # 7-14, 14-19, 19-24, 24-63 for GSM 
    stats = {
        "sim_status": sim_stat,
        "mode": mode,
        "network_name": network_name,
        "phone_number": phone_number,
        "signal_qual": signal_qual
    }
    return stats

try:
    Login()
except Exception as e: 
    print(f"Error logging into router: {e}")

sleep(2)

if __name__ == "__main__":
    while True:
        print(getData())
        sleep(5)