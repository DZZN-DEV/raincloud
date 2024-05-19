import argparse
from raincloud import SCTrack, SCSet
import os

client_id_filepath = 'client_id.txt'
with open(client_id_filepath, 'r') as client_id_txt:
    client_id = client_id_txt.read().strip()

assert(client_id != "PASTE SOUNDCLOUD CLIENT ID (AND NOTHING ELSE) HERE."), "brother please add your client ID to client_id.txt or use the command line argument"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = "simple soundcloud downloader")
    parser.add_argument('sc_url', type = str, help = "soundcloud URL")
    parser.add_argument('--cid', type = str, default = client_id, help = "soundcloud client ID, can be obtained via F12 on refresh.")
    parser.add_argument('--nm', default = False, action = 'store_true', help = 'just download mp3, no metadata')
    args = parser.parse_args()

    os.makedirs('dls', exist_ok = True)
    try:
        sc = SCTrack(args.cid, args.sc_url)
        stream_url = sc.stream_url
        sc.stream_download('dls', not args.nm)
    except AssertionError as e:
        print(e)
        cont = input('Playlist/set detected. Would you like to download all? (Y/n)')
