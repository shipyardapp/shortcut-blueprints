import argparse
import sys
import requests
import shipyard_utils as shipyard
try:
    import exit_codes
except BaseException:
    from . import exit_codes


# create Artifacts folder paths
base_folder_name = shipyard.logs.determine_base_artifact_folder('shortcut')
artifact_subfolder_paths = shipyard.logs.determine_artifact_subfolders(
    base_folder_name)
shipyard.logs.create_artifacts_folders(artifact_subfolder_paths)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--access-token', dest='access_token', required=True)
    parser.add_argument('--story-public-id', dest='story_public_id', required=True)
    parser.add_argument('--name', dest='name', required=True)
    parser.add_argument('--description', dest='description', required=True)
    parser.add_argument('--issue-type', dest='issue_type', required=True)
    parser.add_argument('--deadline', dest='deadline', required=False)
    parser.add_argument('--estimate', dest='estimate', required=False)
    parser.add_argument('--custom-json', dest='custom_json', required=False)
    args = parser.parse_args()
    return args




def update_story(token, story_id, name, description, issue_type, estimate=None,
                deadline=None, epic_id=None, custom_fields=None):
    """ Triggers the Update Story API to update Story properties.
    see: https://shortcut.com/api/rest/v3#Update-Story
    
    story_id: the story-public-id (The unique identifier of this story.)
    """
    
    update_api = f"https://api.app.shortcut.com/api/v3/stories/{story_id}"

    headers = {
      'Content-Type': 'application/json',
      "Shortcut-Token": token
    }

    payload = {
        "archived": True, 
        "description": description,
        "move_to": "first", 
        "name": name, 
        "story_type": issue_type
    }
    if estimate:
        payload["estimate"] = estimate

    if deadline:
        payload["deadline"] = deadline

    if custom_fields:
        payload['custom_fields'] = custom_fields

    response = requests.post(update_api, 
                             headers=headers, 
                             json=payload
                             )

    if response.status_code == 200: # updated successfuly
        print(f"Story {story_id} updated successfully")
        return response.json()

    elif response.status_code == 401: # Permissions Error
        print("You do not have the required permissions to create an issue in ",
              "this project")
        sys.exit(exit_codes.INVALID_CREDENTIALS)

    elif response.status_code == 400: # Bad Request
        print("Shortcut responded with Bad Request Error. ",
              f"Response message: {response.text}")
        sys.exit(exit_codes.BAD_REQUEST)

    elif response.status_code == 404: # Resource does not exist
        print("Shortcut responded with Resource does not exist Error. ",
              f"Response message: {response.text}")
        sys.exit(exit_codes.RESOURCE_DOES_NOT_EXIT)

    elif response.status_code == 422: # Unprocessable
        print("Shortcut responded with Unprocessable Error. ",
              f"Response message: {response.text}")
        sys.exit(exit_codes.UNPROCESSABLE_ERROR)

    else: # Some other error
        print(
            f"an Unknown HTTP Status {response.status_code} and response occurred when attempting your request: ",
            f"{response.text}"
        )
        sys.exit(exit_codes.UNKNOWN_ERROR)
    

def main():
    args = get_args()
    access_token = args.access_token
    story_public_id = args.story_public_id
    custom_json = args.custom_json
    deadline = args.deadline
    name = args.name
    description = args.description
    issue_type = args.issue_type

    story_data = update_story(access_token, story_public_id ,name, description, 
                              issue_type, deadline, custom_json)

    story_id = story_data['id']
    
    # save response
    issue_data_filename = shipyard.files.combine_folder_and_file_name(
        artifact_subfolder_paths['responses'],
        f'create_story_{story_id}_response.json')
    shipyard.files.write_json_to_file(story_data, issue_data_filename)

    

if __name__ == "__main__":
    main()