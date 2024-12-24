#!/bin/bash

# Loop through all directories matching the pattern
for dir in takeout_files/instagram-junejasahab-*/; do
    echo "================="
    if [ -d "$dir" ]; then
        json_path="${dir}your_instagram_activity/saved/saved_collections.json"
        
        if [ -f "$json_path" ]; then
            echo "Processing: $json_path"
            python db.py add-new-posts --file $json_path
            
            # Your processing logic for the JSON file here
            # For example:
            # cat "$json_path"
            # or process it with jq, etc.
            
        else
            echo "No saved_collection.json in $dir"
        fi
    fi
done