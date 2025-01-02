import os
import instaloader
from instaloader import Post
import requests
import re
from datetime import datetime
import json
import shortuuid

def get_post_type(url):
    url = url.lower()
    url = url.split('?')[0].rstrip('/')

    if '/reel/' in url:
        return 'reel'

    elif '/tv/' in url:
        return 'tv'
    
    elif '/p/' in url:
        return 'post'
        
    return 'other'

def file_exists(id):
    # Todo it should make sure the file exists in the correct folder too
    if os.path.exists("reels_non_collection/"+id+".mp4"):
        return True
    elif os.path.exists("reels/"+id+".mp4"):
        return True
    else:
        return False

# function that downloads a reel
def extract_instagram_id(url):
    # Pattern to match the ID after /p/
    pattern = r'/(p|reel)/([^/]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(2)
    else:
        print("Video ID not found in url: ", url)
    return None

def download(video_url, filename, is_collection):


    


    try:
        download_folder = "reels" if is_collection else "reels_non_collection"
        L = instaloader.Instaloader()
        video_id = extract_instagram_id(video_url)
        post = Post.from_shortcode(L.context, video_id)
        url = post.video_url
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(download_folder + "/" + filename + '.mp4', 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
            print("--- Download Success ---")
            print("Response: ", response)
        else:
            print("X"*12 + "Download Failed" + "X"*12)
            print("Status Code: ", response.status_code)
            print("Response: ", response)
            raise Exception("Non 200 response code")
    except Exception as e:
        print("X"*12 + "Download Failed" + "X"*12)
        print("Exception: ", e)
        raise

def parse_saved_posts(saved_posts_raw):
    saved_posts = {}
    for p in saved_posts_raw['saved_saved_collections']:
        # check if it is a title entry or a post
        if 'title' in p.keys():
            current_collection_title = p['string_map_data']['Name']['value']

            # create a new key in saved posts if it doesnt exist already
            if current_collection_title not in saved_posts:
                saved_posts[current_collection_title] = []

        else:
            reel = {
                'id':shortuuid.ShortUUID().random(length=4),
                'account':p['string_map_data']['Name']['value'] if 'value' in p['string_map_data']['Name'] else None,
                'url':p['string_map_data']['Name']['href'],
                'date_saved':datetime.fromtimestamp(p['string_map_data']['Added Time']['timestamp']),
                'collection':current_collection_title,
                'post_type':get_post_type(p['string_map_data']['Name']['href'])
            }
            saved_posts[current_collection_title].append(reel)
    return saved_posts


"""
#Code for transfering saved posts pickle to db
# read pickle file containing parsed posts
with open('saved_posts.pkl', 'rb') as file:
    # Deserialize the object from the file
    saved_posts = pickle.load(file)

for collection_name in saved_posts.keys():
    for post in saved_posts[collection_name]:
        new_post = Post(
            id=post['uuid'],
            account=post['account_name'],
            url=post['url'],
            date_saved=datetime.fromtimestamp(post['aded_timestamp']),
            collection=collection_name,
            post_type=PostType(get_post_type(post['url']))
        )
        session.add(new_post)
session.commit()
"""

"""
#Code for transfering saved posts non collection pickle to db
for post in posts[:1]:
    new_post = Post(
        id=post['uuid'],
        account=post['account_name'],
        url=post['url'],
        date_saved=datetime.fromtimestamp(post['aded_timestamp']),
        collection=None,
        post_type=PostType(get_post_type(post['url']))
    )
    try:
        session.add(new_post)
        session.commit()
    finally:
        session.close()
        engine.dispose()
"""
