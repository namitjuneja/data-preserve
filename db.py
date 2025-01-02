from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Enum, and_, or_
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

from utils import get_post_type, file_exists, download, parse_saved_posts

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
        return f"<Post id:{self.id}, | account:{self.account}, | collection: {self.collection}, | url:{self.url}>"



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
    engine = create_engine('sqlite:////home/namit/Downloads/ig_saved/reels.sqlite')

    # Create session factory
    Session = sessionmaker(bind=engine)

    print("Connected to existing database, \"reels.sqlite\"")

    return engine, Session()


def add_new_posts(session, file):

    # open the takout file
    with open(file) as f:
        new_saved_posts_raw = json.load(f)
    
    # convert takeout from insta format to a dictionary of collections
    new_saved_posts = parse_saved_posts(new_saved_posts_raw)

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
                # print("Duplicate Entry Post found")
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


    # confirm non collission hash
    # add to db

def download_new_posts(session):
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
        .limit(30)
    
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
        try:
            download(p.url, p.id, is_collection)
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

    print(f"Playing collection \"{collection}\" with {len(post_list)} videos.")

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
                        choices=['download', 'sync-download-status', 'add-new-posts', 'play'],
                        help='Action to execute: \
                              download (download new posts), \
                              sync-download-status (sync downloaded status for manually downloaded posts), \
                              add-new-posts (add new posts from the instagram takeout file)\
                              play (play downloaded videos from a particular collection, "None" for no collection)')
    # Add file path argument for add-new-posts command
    parser.add_argument('--file', type=str,
                      help='Path to the JSON file (required for add-posts command)')
    # Add collection name to play command
    parser.add_argument('--collection_name', type=str,
                      help='Name of the collection whose videos you want to play (required for the play command)')
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
    finally:
        # Clean up
        session.close()
        engine.dispose()

    # loop through saved posts and commit them to the db

    # repeat for non collection_posts
    
    
