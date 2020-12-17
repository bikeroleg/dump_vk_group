#!/usr/bin/python
import sys
import os
import vk_api
import json
from vkaudiotoken import supported_clients, get_kate_token
import requests
from urllib import parse
from urllib import request
from urllib.parse import unquote

require_photo = False
require_audio = False
require_messages = False
# parsing arguments
if len(sys.argv) > 1: # if args are specified
    if '--photo' in sys.argv:
        require_photo = True
    if '--audio' in sys.argv:
        require_audio = True
    if '--messages' in sys.argv:
        require_messages = True
else:   # default
    require_audio = True
    require_photo = True
    require_messages = True


config_file = open("config.txt", "r")

CONFIG = {
    'login': config_file.readline().strip(),
    'password': config_file.readline().strip(),
    'group': config_file.readline().strip(),
    'group_token': config_file.readline().strip()
}
config_file.close()

print("Getting VK API session...")
vk_session = vk_api.VkApi(CONFIG['login'], CONFIG['password'])
vk_session.auth()
vk = vk_session.get_api()
tools = vk_api.VkTools(vk_session)

# for downloading audio
if require_audio:
    print("Getting VK audio token...")
    token = get_kate_token(CONFIG['login'], CONFIG['password'])['token']

os.makedirs(CONFIG['group'], mode=0o777, exist_ok=True)
os.chdir(CONFIG['group'])
os.makedirs('attachments/audio', mode=0o777, exist_ok=True)
os.makedirs('attachments/photo', mode=0o777, exist_ok=True)


def __hack_audio_url(audio):
    # accepts array of audio objects, returns array of urls
    urls = []
    audios = []
    for k in audio:
        audios.append(str(k['owner_id'])+"_"+str(k['id']))

    audios_id = ",".join(audios)

    user_agent = supported_clients.KATE.user_agent

    sess = requests.session()
    sess.headers.update({'User-Agent': user_agent})
    response = json.loads(sess.get(
        "https://api.vk.com/method/audio.getById",
        params=[('access_token', token),
                ('audios', audios_id),
                ('v', '5.95')]
    ).content.decode('utf-8'))['response']

    for audio in response:
        urls.append(audio['url'].split('?')[0])

    return urls


def save_photo(url, post_id):
    print("[Saving photos...]")
    os.makedirs("attachments/photo/" + str(post_id), mode=0o777, exist_ok=True)
    os.chdir("attachments/photo/" + str(post_id))
    for photo in url:
        os.system("wget -q "+photo)
    os.chdir("../../..")
    print("==[Done]==")


def save_docs(names, url, post_id):
    os.makedirs("attachments/photo/" + str(post_id), mode=0o777, exist_ok=True)
    os.chdir("attachments/photo/" + str(post_id))
    for j in range(0, len(names)):
        with request.urlopen(url[j]) as response:
            with open(names[j], "wb") as f:
                f.write(response.read())
    os.chdir("../../..")


def save_audio(name, url, post_id):
    print("[Saving music... "+str(len(name))+" elements]")
    os.makedirs("attachments/audio/" + str(post_id), mode=0o777, exist_ok=True)
    os.chdir("attachments/audio/" + str(post_id))
    for j in range(0, len(name)):
        os.system("wget -q -O "+name[j]+" "+url[j])
    os.chdir("../../..")
    print("==[Done]==")


def attachments_handler(post):
    # collects photos and music from the post, saves into individual directory
    photos_url = []
    docs = []
    docs_titles = []
    music = []
    music_obj = []

    for i in post['attachments']:
        if i['type'] == "photo" and require_photo:
            highres = [] # get all possible variants of photo
            for x in i['photo']['sizes']:
                highres.append(x['type'])
            if "z" in highres: # get HD if possible
                for x in i['photo']['sizes']:
                    if x['type'] == 'z':
                        photos_url.append(x['url'])
            elif "y" in highres: # get 807px if possible
                for x in i['photo']['sizes']:
                    if x['type'] == 'y':
                        photos_url.append(x['url'])
            elif "r" in highres: # get 510 px if possible
                for x in i['photo']['sizes']:
                    if x['type'] == 'r':
                        photos_url.append(x['url'])

            elif "q" in highres: # at least get 320px, lower doesn't deserve downloading
                for x in i['photo']['sizes']:
                    if x['type'] == 'q':
                        photos_url.append(x['url'])

        if i['type'] == "audio" and require_audio:
            # create unix-friendly filename with no spaces in "artist--title.mp3" format
            name = i['audio']['artist'].replace(" ", "_") + "--" + i['audio']['title'].replace(" ", "_") + ".mp3"
            name = parse.quote_plus(name)
            music.append(name)
            music_obj.append(i['audio'])

        if require_photo and i['type'] == "doc" and (i['doc']['type'] == 3 or i['doc']['type'] == 4): #only pictures and gifs
            docs_titles.append(i['doc']['title'])
            docs.append(i['doc']['url'])

    if len(photos_url) > 0:
        save_photo(photos_url, post['id'])
    if len(docs) > 0:
        save_docs(docs_titles, docs, post['id'])
    if len(music) > 0:
        save_audio(music, __hack_audio_url(music_obj), post['id'])


if __name__ == '__main__':
    posts = tools.get_all('wall.get', 100, {'owner_id': -1 * int(CONFIG['group'])})
    out = open("wall.txt", "w")
    post = {}
    data = {}

    if require_messages:
        print("==[Getting the dialogs]==")
        group = vk_api.VkTools(vk_api.VkApi(token=CONFIG['group_token']))
        os.makedirs("messages/", mode=0o777, exist_ok=True)
        os.chdir("messages")
        c = group.get_all('messages.getConversations', 200, values={'group_id': CONFIG['group']})
        conv = c['items']
        ids = []
        for i in conv:
            ids.append(str(i['conversation']['peer']['id']))
        ids = ','.join(ids)
        profiles = vk.users.get(user_ids=ids)
        # getting a list of conversations
        # achieving chat history for every conversation
        for i in conv:
            with open(str(i['conversation']['peer']['id'])+'.txt', 'w') as f:
                name = ""
                surname = ""
                for q in profiles:
                    if str(q['id']) == str(i['conversation']['peer']['id']):
                        name = unquote(q['first_name'])
                        surname = unquote(q['last_name'])
                print(name)
                history = group.get_all('messages.getHistory', 200, {'group_id': CONFIG['group'], 'peer_id': i['conversation']['peer']['id'], 'rev': 1})['items']
                for message in history:
                    message['text'] = unquote(message['text'])
                chat = {
                    'peer_id': i['conversation']['peer']['id'],
                    'name': name,
                    'surname': surname,
                    'messages': history
                }
                json.dump(chat, f, indent=4, sort_keys=True)
        os.chdir("../")

    for i in range(int(posts['count'])-1, -1, -1):     # newest post is [0] so we go reverse, from oldest to newest
        post = posts['items'][i]
        print("\nProcessing post id "+str(post['id']))

        if "attachments" in post:
            attachments_handler(post)

        data[str(post['id'])] = {
            'unix_date': post['date'],
            'from': post['from_id'],
            'text': post['text'],
            'likes': post['likes']['count'],
            'reposts': post['reposts']['count'],
            'views': post['views']['count']
        }

    json.dump(data, out)
    out.close()
