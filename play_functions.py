import os
from subprocess import call


def play_untagged_non_collection_videos(favs_folder_location, reels_non_collection_location):
    """
    Plays all files in the reels_non_collection folder 
    that have not been categorized in the Favs folder yet
    """
    tagged_file_list = []
    for root, dirs, files in os.walk(favs_folder_location):
        for file in files:
            tagged_file_list.append(file)

    file_list = []
    for root, dirs, files in os.walk(reels_non_collection_location):
        for file in files:
            file_list.append(file)

    untagged_file_list = set(file_list) - set(tagged_file_list)

    untagged_file_list_location = [reels_non_collection_location + "/" + i for i in untagged_file_list]

    call(["vlc"] + untagged_file_list_location)



    

if __name__ == '__main__':
    favs_folder_location = "/home/namit/Downloads/ig_saved/Favs"
    reels_non_collection_location = "/home/namit/Downloads/ig_saved/reels_non_collection"

    a = play_untagged_non_collection_videos(favs_folder_location, reels_non_collection_location)
    print(a)