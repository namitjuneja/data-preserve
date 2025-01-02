#!/bin/bash

# Loop through all directories matching the pattern
for dir in takeout_files/instagram-junejasahab-*/; do
    echo "================="
    if [ -d "$dir" ]; then
        # Look for the saved_collections.json and run python file if found
        json_collection_path="${dir}your_instagram_activity/saved/saved_collections.json"
        
        if [ -f "$json_collection_path" ]; then
            echo "Processing Collections file : $json_collection_path"
            python db.py add-new-posts --file $json_collection_path       
        else
            echo "No saved_collections.json in $dir"
        fi
        
        # Look for the saved_posts.json file and run the python file if found.
        json_non_collection_path="${dir}your_instagram_activity/saved/saved_posts.json"

        if [ -f "$json_non_collection_path" ]; then
            echo "Processing NON Collections file : $json_non_collection_path"
            python db.py add-new-posts --file $json_non_collection_path 
        else
            echo "No saved_posts.json in $dir"
        fi
    fi
done