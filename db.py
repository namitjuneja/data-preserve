from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Enum, and_, or_, select
import enum
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

from datetime import datetime
import json
import shortuuid
from random import randint
from time import sleep
import argparse
from subprocess import call
import os
import shutil
import pyperclip

from utils import *

# Define enum classes
class PostType(enum.Enum):
    POST = 'post'
    REEL = 'reel'
    TV = 'tv'
    OTHER = 'other'

# Create the base class for declarative models
Base = declarative_base()

# Define example models
class Post(Base):
    __tablename__ = 'posts'

    id = Column(String(4), primary_key=True)
    account = Column(String(50), unique=False)
    url = Column(String(120), unique=False)
    date_saved = Column(DateTime)
    collection = Column(String(50))
    post_type = Column(Enum(PostType))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_downloaded = Column(Boolean, default=False)
    last_download_failed = Column(Boolean, default=False)
    

    def __repr__(self):
        return f"<Post id:{self.id}, | account:{self.account}, | collection: {self.collection}, | url: {self.url}, | Downloaded: {self.is_downloaded}>"



def init_db():
    """Initialize the database, create tables"""
    # Create SQLite database engine
    # Use ':memory:' for in-memory database, or 'sqlite:///your_db.sqlite' for file-based
    engine = create_engine('sqlite:///reels.sqlite', echo=True)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session factory
    Session = sessionmaker(bind=engine)
    
    return Session()

def get_session():
    """Creates a session attached to an existing sqlite file based db"""
    # Create SQLite database engine
    engine = create_engine('sqlite:///reels.sqlite')

    # Create session factory
    Session = sessionmaker(bind=engine)

    print("Connected to existing database, \"reels.sqlite\"")

    return engine, Session()


def add_new_posts(session, file):

    # open the takout file
    with open(file) as f:
        new_saved_posts_raw = json.load(f)

    file_type = detect_file_type(file)
    
    if file_type == "collection":
        # convert takeout from insta format to a dictionary of collections
        new_saved_posts = parse_saved_posts(new_saved_posts_raw)
    elif file_type == "non_collection":
        # it is a list of posts that do not belong to a collection
        new_saved_posts = parse_non_collection_saved_posts(new_saved_posts_raw)
    

    if file_type == "collection":
        # for each post check
        # - same uuid doesn't already exist
        # - the same post url - collection combination does not exist
        # (same post can exist multiple times but with different collection)
        for collection_name in new_saved_posts.keys():
            for p in new_saved_posts[collection_name]:
                assert collection_name == p['collection']
                # check uuid collision
                # query all rows with the same uuid
                # if found, keep assigning new uuids until no row is found with the same uuid
                post_uuid = p['id']
                posts_with_same_uuid = session.query(Post).filter(Post.id==post_uuid).count()
                while posts_with_same_uuid > 0:
                    print(f"UUID Collision Detected for id [{post_uuid}]. \n Assigning new UUID")
                    post_uuid = shortuuid.ShortUUID().random(length=4)
                    posts_with_same_uuid = session.query(Post).filter(Post.id==post_uuid).count()

                # look for another row with the same post url - collection pair
                duplicate_entry_count = session.query(Post)\
                    .filter(
                        and_(
                            Post.url == p['url'],
                            Post.collection == p['collection']
                        )
                    )\
                    .count()
                if duplicate_entry_count > 0:
                    # print("Post Being Skipped: ", p)
                    continue

                new_post = Post(
                    id=post_uuid,
                    account=p['account'],
                    url=p['url'],
                    date_saved=p['date_saved'],
                    collection=p['collection'],
                    post_type=PostType(p['post_type']))
                
                print(new_post)
                session.add(new_post)
        session.commit()
    elif file_type == "non_collection":
        # for each post check
        # - same uuid doesn't already exist
        # - same url doesn't already exist
        for p in new_saved_posts:
            # check uuid collision
            # query all rows with the same uuid
            # if found, keep assigning new uuids until no row is found with the same uuid
            post_uuid = p['id']
            posts_with_same_uuid = session.query(Post).filter(Post.id==post_uuid).count()
            while posts_with_same_uuid > 0:
                print(f"UUID Collision Detected for id [{post_uuid}]. \n Assigning new UUID")
                post_uuid = shortuuid.ShortUUID().random(length=4)
                posts_with_same_uuid = session.query(Post).filter(Post.id==post_uuid).count()

            # query all the rows for the same url 
            # if found skip it because 
            # if it is a pre-existing collection row then it has no business beng a non-collection row
            # if it is a pre-existing non-collection row then it will lead to duplication
            # insta is sending bad quality data
            post_url = p['url']
            posts_with_same_url = session.query(Post).filter(Post.url==post_url).all()
            if len(posts_with_same_url) > 0:
                print(f"Skipping. Existing post(s) IDs: ")
                [print(f"ID: {duplicate_post.id} | account: {duplicate_post.account}") for duplicate_post in posts_with_same_url]
                print("X"*50)
                continue

            new_post = Post(
                id=post_uuid,
                account=p['account'],
                url=p['url'],
                date_saved=p['date_saved'],
                collection=p['collection'],
                post_type=PostType(p['post_type']))
            
            print(new_post)
            session.add(new_post)
        session.commit()

    # confirm non collission hash
    # add to db

def download_new_posts(session):
    # Print total posts remaining to be downloaded - just to get an idea
    total_undownloaded_collection_posts = session.query(Post)\
        .filter(
            and_(
                Post.is_downloaded == False,
                Post.last_download_failed == False,
                Post.post_type == "REEL",
                Post.collection != None
            )
        ).count()
    total_undownloaded_non_collection_posts = session.query(Post)\
        .filter(
            and_(
                Post.is_downloaded == False,
                Post.last_download_failed == False,
                Post.post_type == "REEL",
                Post.collection == None
            )
        ).count()
    print("Total un-downloaded collection posts: ", total_undownloaded_collection_posts)
    print("Total un-downloaded non-collection posts: ", total_undownloaded_non_collection_posts)
    print("Total un-downloaded posts: ", total_undownloaded_collection_posts + total_undownloaded_non_collection_posts)



    # query posts where is_downloaded is 0 and last_download_failed is 0
    posts = session.query(Post)\
        .filter(
            and_(
                Post.is_downloaded == False,
                Post.last_download_failed == False,
                Post.post_type == "REEL"
            )
        )\
        .order_by(Post.date_saved.asc())\
        .limit(10)
    
    post_count = len(posts.all()) # this is inefficient and should not be done for long queries
    print(f"Found {post_count} posts to download.\n")

    # pick 5 posts download them with wait timer of 5
    for idx, p in enumerate(posts):
        print(f"\n===========Downloading ({idx+1}/{post_count})===========")
        print("ID: ", p.id)
        print("ACCOUNT: ", p.account)
        print("URL: ", p.url)
        print("COLLECTION: ", p.collection)
        print(">>-<<")

        # check if it is a collection post or a non collection post
        # this is used to decide what folder is the reel downloaded in
        is_collection = p.collection is not None
        is_reel = p.post_type == PostType.REEL
        try:
            download(p.url, p.id, is_collection, is_reel)
            p.is_downloaded = True
        except Exception as e:
            p.last_download_failed = True
            print(e)
        session.commit()

        print("=========================================\n")

        # Add a random wait time
        random_waiting_time = randint(10,15)
        print(f"Waiting for {random_waiting_time/60} minutes...")
        #sleep(random_waiting_time)
        print("Waiting over.")

def play_videos(collection=None):

    collection = None if collection == "None" else collection # figure out a cleaner way to do this
    collection = "flirt"

    posts = session.query(Post)\
        .filter(
            and_(
                Post.is_downloaded == True,
                Post.post_type == "REEL",
                Post.collection == collection
            )
        )\
        .order_by(Post.date_saved.asc())

    # which folder to fetch the files from
    if collection and collection.lower() != "None":
        folder_prefix = "/home/namit/Downloads/ig_saved/reels/"
    else:
        folder_prefix = "/home/namit/Downloads/ig_saved/reels_non_collection/"

    post_list = []
    for p in posts:
        post_address = folder_prefix + p.id + ".mp4"
        post_list.append(post_address)

    print("\n\n")
    print("="*50)
    print(f"Playing collection \"{collection}\" with {len(post_list)} videos.")
    print("="*50)
    print("\n\n")

    # launch vlc with the list of posts
    call(["vlc"] + post_list)
    



def sync_download_status(session):
    # query all posts where is_downloaded is False 
    # and check if that file exists
    # sometimes files are added manually
    posts = session.query(Post).filter(Post.is_downloaded==False)

    for p in posts:
        if file_exists(p.id):
            p.is_downloaded = True
            print("updating: ", p)
    
    session.commit()

def remove_duplicates(session):
    """
    look for posts that exist in both non_collection and collection
    this happens when I re tag a non-collection post into a particular collection
    in that case I do not want to redownload the video, simply move it
    for every post that is 
    - in collection and in non-collection
    
    If found: 
    We have 2 types of rows:
    A: Non-collection row. This is the entry that was retagged into one or many collection rows. There should be only one of these. 
    B: Collection row(s). The row with the same url that is now a collection row. There can be many collection rows with the same URL. 
        e.g. same reel can belong to flirt and sociality. 


    What do we do?
    if A.is_downloaded == True:
        copy file from non_collection_reels to collection reel. 
        The name of the file should be the same as B.id. 
        Do this for every B file found that has the same URL as A. 
        Update B.is_downloaded = True after copying successfuly. 
        The above steps should be performed only if A.is_downloaded == True i.e. the file is downloaded. 
        Delete the A record. 
    """

    # Subquery to find URLs with NULL collections
    # Create proper select statements for subqueries
    null_collection_query = select(Post.url).where(Post.collection == None)
    notnull_collection_query = select(Post.url).where(Post.collection != None)
    
    # Find URLs that exist in both queries using EXISTS
    result = session.query(Post.url).distinct().filter(
        and_(
            Post.url.in_(null_collection_query),
            Post.url.in_(notnull_collection_query)
        )
    ).all()
    
    # Extract URLs from result tuples
    urls = [r[0] for r in result]

    for i in urls:
        non_collection_rows = session.query(Post).filter(
                and_(
                    Post.url == i,
                    Post.collection == None
                )
            ).all()
        assert len(non_collection_rows)==1, "There should be only one non-collection post while removing duplicates"

        non_collection_id = non_collection_rows[0].id
        non_collection_is_downloaded = non_collection_rows[0].is_downloaded
        non_collection_last_download_failed = non_collection_rows[0].last_download_failed

        collection_rows = session.query(Post).filter(
                and_(
                    Post.url == i,
                    Post.collection != None
                )
            ).all()
        
        for collection_row in collection_rows:
            if non_collection_is_downloaded:
                # copy file
                source_folder = "/home/namit/Downloads/ig_saved/reels_non_collection"
                destination_folder = "/home/namit/Downloads/ig_saved/reels"
                source_file = non_collection_id + ".mp4"
                destination_file = collection_row.id + ".mp4"
                source_path = os.path.join(source_folder, source_file)
                destination_path = os.path.join(destination_folder, destination_file)
                
                
                # Copy the file
                try:
                    shutil.copy2(source_path, destination_path)
                    print(f"Successfully copied {source_path} to {destination_path}")
                except Exception as e:
                    print(f"Error copying file: {e}")
                    return False

                # copy is downloaded status
                collection_row.is_downloaded = non_collection_is_downloaded
                collection_row.last_download_failed = non_collection_last_download_failed

        # delete non_collection video file only when everything happened successfully
        os.remove(source_path)
        print(f"Successfully deleted: {source_path}")

        # delete non_collection_row
        session.delete(non_collection_rows[0])
        print(f"Successfully deleted: {non_collection_rows[0]}")
        session.commit()


        print("="*25)

def find_link(session, id):
    """
    Given a post ID, return the instagram URL of the post 
    """
    result = session.query(Post).filter(Post.id==id).first()
    if result:
        print(result.url)
        pyperclip.copy(result.url)
        print("Copied to clipboard!")
    else:
        print(f"No post found with id: {id}")


if __name__ == '__main__':
    # Initialize database and get session 
    # (only run first time when setting up the db)
    # session = init_db()

    # Connect to an existing sqlite db
    engine, session = get_session()


    parser = argparse.ArgumentParser(description='Instagram Post Management Tool')
    # add a command line positional argument called action
    # action can have only 3 valid values
    parser.add_argument('action', 
                        choices=['download', 'sync-download-status', 'add-new-posts', 'play', 'remove-duplicates', 'find-link'],
                        help='Action to execute: \
                              download (download new posts), \
                              sync-download-status (sync downloaded status for manually downloaded posts), \
                              add-new-posts (add new posts from the instagram takeout file)\
                              play (play downloaded videos from a particular collection, "None" for no collection),\
                              remove-duplicates (remove reels that exist in both collection and non-collection),\
                              find-link (print IG URL for a given 4 charachter post ID)')
    # Add file path argument for add-new-posts command
    parser.add_argument('--file', type=str,
                      help='Path to the JSON file (required for add-posts command)')
    # Add collection name to play command
    parser.add_argument('--collection_name', type=str,
                      help='Name of the collection whose videos you want to play (required for the play command)')
    # Add post ID argument for the find_link argument
    parser.add_argument('--id', type=str,
                      help='4 charachter ID used to identify a post in the database')
    args = parser.parse_args()

    try:
        # Execute the requested command
        if args.action == 'download':
            download_new_posts(session)
        elif args.action == 'sync-download-status':
            sync_download_status(session)
        elif args.action == 'add-new-posts':
            if not args.file:
                parser.error("sync-posts command requires --file argument")
            add_new_posts(session, args.file)
        elif args.action == 'play':
            if not args.collection_name:
                parser.error("play command requires --collection_name argument")
            play_videos(args.collection_name)
        elif args.action == 'remove-duplicates':
            remove_duplicates(session)
        elif args.action == 'find-link':
            if not args.id:
                parser.error("find-link command requires --id argument")
            find_link(session, args.id)
    finally:
        # Clean up
        session.close()
        engine.dispose()
