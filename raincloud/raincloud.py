'''
raincloud v2 api, contains SCTrack and SCSet classes with:
* resolve_url, which has loads of important metadata most importantly streaming url
* SCSet has tracks attribute which is a list of SCTracks
* SCTrack has stream_url attribute, with methods stream_download
 ／l、
（ﾟ､ ｡ ７
  l  ~ヽ
  じしf_,)ノ
'''

import requests
import os
import re
from mutagen.id3 import APIC
import mutagen
from tqdm import tqdm

class SCBase:
    # The base class for SC tracks, playlists. Attribute is resolved url, arguments client ID and URL
    def __init__(self, client_id: str, sc_url: str):
        self.client_id = client_id

        self.params = {
            "client_id" : client_id,
            "url" : sc_url
        } # parameters to make request to resolve URL

        self.default_headers = {
            "User-Agent" : "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
        } # anything works rly idk

        self.api_url = "https://api-v2.soundcloud.com" # resolve endpoint

        self._resolved = None

    @property
    def resolved(self) -> dict:
        # the resolved url, contains a whole bunch of metadata, most importantly the streaming URL for the track
        if self._resolved is None:
            response = requests.get(f"{self.api_url}/resolve", params = self.params, headers = self.default_headers)
            response.raise_for_status()
            self._resolved = response.json()

        return self._resolved

    @property
    def title(self) -> str:
        return self.resolved['title']

    @property
    def artist(self) -> str:
        return self.resolved['user']['username']

    @property
    def artwork_url(self) -> str:
        return self.resolved['artwork_url']

class SCTrack(SCBase):
    # A single track
    def __init__(self, client_id: str, sc_url: str):
        super().__init__(client_id, sc_url)

    @property
    def stream_url(self) -> str:
        assert self.resolved['kind'] == 'track'

        # progressive check should be up there
        # new function to get this url, return prog url if possible, else return mp3
        has_prog = False
        for tr in self.resolved['media']['transcodings']:
            if tr['format']['protocol'] == 'progressive':
                prog_url = tr['url']
                has_prog = True
        if has_prog == False:
            for tr in self.resolved['media']['transcodings']:
                if 'mp3' in tr['preset']:
                    hls_url = tr['url']
                if not hls_url:
                    print('No MP3 URL found, download is cooked sadly')

        if has_prog:
            result = requests.get(
                prog_url,
                params = {
                    "client_id" : self.client_id
                },
                headers = self.default_headers
            )
            stream_url = result.json()['url']
        else:
            result = requests.get(
                hls_url,
                params = {
                    "client_id" : self.client_id
                },
                headers = self.default_headers
            )
            stream_url = result.json()['url']
        return stream_url

    @property
    def progressive_streaming(self) -> bool:
        return not 'playlist' in self.stream_url # 'playlist' in M3U stream URLs

    def stream_download(self, dst_dir: str, metadata = True):
        filename = self.title + '.mp3' # title of track
        dst = os.path.join(dst_dir, filename) # output file
        response = requests.get(self.stream_url, stream=True)

        if self.progressive_streaming:
            total_size = int(response.headers.get('content-length', 0))
            if response.status_code == 200: # if it works...
                with open(dst, 'wb') as output:
                    # cooler progress bar
                    for chunk in tqdm(response.iter_content(chunk_size = 8192), total = total_size // 8192, unit = 'chunk', unit_scale = True, desc = 'Downloading Progressive'):
                        if chunk:
                            output.write(chunk)
                print(f'{dst} downloaded, size: {round(os.stat(dst).st_size / (1024*1024), 2)} MB.')

        else:
            print('HLS streaming, warning SLOW download')
            m3u_playlist = response.content.decode('utf-8')  # m3u8 file to string
            m3u_urls = re.findall(re.compile(r"http.*"), m3u_playlist)  # get the streaming links as a list

            # TODO: parallel processing possible?
            with open(dst, 'wb') as output:
                # download sequentially from m3u url, TQDM used for progress bar
                for i, url in enumerate(tqdm(m3u_urls, desc = 'Downloading HLS', unit = 'chunk')):
                    response = requests.get(url, stream = True)
                    for chunk in response.iter_content(chunk_size = 8192):
                        output.write(chunk)

        if metadata:
            cover_img = requests.get(self.artwork_url).content
            imgpath = "coverart.jpg"
            with open(imgpath, 'wb') as img:
                img.write(cover_img)

            # Add title and artist
            # add title and artist
            audio_ez = mutagen.File(dst, easy=True)

            if audio_ez.tags is None:
                audio_ez.add_tags()
            audio_ez['title'] = self.title
            audio_ez['artist'] = self.artist
            audio_ez.save()

            # add cover art - can't use easyID3

            audio = mutagen.File(dst)
            with open(imgpath, 'rb') as coverart:
                audio['APIC'] = APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc=u'Cover',
                    data=coverart.read()
                )
            audio.save()

            os.remove(imgpath)
            return audio_ez['title'], audio_ez['artist']

class SCSet(SCBase):
    # A single track
    def __init__(self, client_id: str, sc_url: str):
        super().__init__(client_id, sc_url)
    @property
    def tracks(self) -> list[SCTrack]:
        track_urls = []
        for t in self.resolved['tracks']:
            try:
                track_urls.append(t['permalink_url'])
            except KeyError:
                track_urls.append(
                    requests.get(
                        f"https://api-v2.soundcloud.com/tracks/{t['id']}",
                        params = {"client_id": self.client_id},
                        headers = self.default_headers
                        ).json()['permalink_url']
                    )
        l = []
        for url in track_urls:
            l.append(SCTrack(self.client_id, url))
        return l