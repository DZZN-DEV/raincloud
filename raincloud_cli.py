import argparse
from raincloud import SCTrack, SCSet
import os
import urllib.request
import regex
import json

def fetch_clientid():
    agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 13_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.5 Mobile/15E148 Safari/604.1"
    headers = {"User-Agent": agent}
    req = urllib.request.Request("https://m.soundcloud.com", headers=headers)
    with urllib.request.urlopen(req) as response:
        html = response.read().decode()
    match = regex.search(r'"clientId":"([0-9a-zA-Z\-_]{32})",', html)
    if match:
        return match.group(1)
    else:
        raise ValueError("Unable to fetch client ID")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple SoundCloud downloader")
    parser.add_argument('sc_url', type=str, help="SoundCloud URL")
    parser.add_argument('--cid', type=str, default=None, help="SoundCloud client ID, can be obtained programmatically or set own")
    parser.add_argument('--nm', default=False, action='store_true', help='Just download mp3, no metadata')
    args = parser.parse_args()

    if args.cid is None:
        try:
            client_id = fetch_clientid()
        except ValueError as e:
            print(e)
            exit(1)
    else:
        client_id = args.cid

    os.makedirs('dls', exist_ok=True)
    try:
        sc = SCTrack(client_id, args.sc_url)
        stream_url = sc.stream_url
        sc.stream_download('dls', not args.nm)
    except AssertionError as e:
        print(e)
        cont = input('Playlist/set detected. Would you like to download all? (Y/n)')
        if cont.lower() == 'y':
            sc_set = SCSet(client_id, args.sc_url)
            for track in sc_set.tracks:
                track.stream_download('dls', not args.nm)
