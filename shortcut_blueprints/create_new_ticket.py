import argparse
import sys
from datetime import datetime
from ast import literal_eval
import re
import requests
from requests.auth import HTTPBasicAuth
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
    parser.add_argument('--name', dest='name', required=True)
    parser.add_argument('--description', dest='description', required=True)
    parser.add_argument('--project-id', dest='project_id', required=True)
    parser.add_argument('--deadline', dest='deadline', required=False)
    parser.add_argument('--estimate', dest='estimate', required=False)
    parser.add_argument('--created-at', dest='created_at', required=False)
    parser.add_argument('--external-id', dest='external_id', required=False)
    parser.add_argument('--external-links', dest='external_links', required=False)
    parser.add_argument('--labels', dest='labels', required=False)
    parser.add_argument('--owners', dest='owners', required=False) 
    parser.add_argument('--custom-json', dest='custom_json', required=False)
    parser.add_argument('--issue-type', 
                        dest='issue_type', 
                        required=True,
                        choices={'bug', 'chore', 'feature'})
    parser.add_argument(
        '--source-file-name',
        dest='source_file_name',
        required=False)
    parser.add_argument(
        '--source-folder-name',
        dest='source_folder_name',
        default='',
        required=False)
    parser.add_argument('--source-file-name-match-type',
                        dest='source_file_name_match_type',
                        choices={'exact_match', 'regex_match'},
                        default='exact_match',
                        required=False)
    args = parser.parse_args()
    return args



def convert_date_to_shortcut(shipyard_date):
    """Converts date from shipyard input MM/DD/YYYY to 
    ISO 8086 date.
    """ 
    str_as_date = datetime.strptime(shipyard_date, '%m/%d/%Y')
    shortcut_date = str_as_date.isoformat() + "Z"
    return shortcut_date


def create_story(token, name, description, issue_type, query_data):
    """ Triggers the Create Story API and adds a new story to shortcut
    see: https://shortcut.com/api/rest/v3#Create-Story
    """
    
    create_story_endpoint = "https://api.app.shortcut.com/api/v3/stories"

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
    payload.update(query_data)

    response = requests.post(create_story_endpoint, 
                             headers=headers, 
                             json=payload
                             )

    if response.status_code == 201: # created successfuly
        new_story_url =  response.json()['app_url']
        print(f"Story created successfully at: {new_story_url}")
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


def upload_file_attachment(token, file_path):
    """ Uploads files to Shortcut API """

    upload_endpoint = "https://api.app.shortcut.com/api/v3/files"

    headers = {
      'Content-Type': 'multipart/form-data',
      "Shortcut-Token": token
    }
    file_payload = {
        "file": (file_path, open(file_path, "rb"), "application-type")
    }
    response = requests.post(upload_endpoint,
                             headers=headers,
                             files=file_payload)

    if response.status_code == 200:
        print(f'{file_path} was successfully uploaded to Shortcut')
    return response.json()


def get_label_ids_by_names(token, label_names):
    """Get a list of label ids associated with a name """
    labels_endpoint = "https://api.app.shortcut.com/api/v3/labels"

    headers = {
      'Content-Type': 'application/json',
      "Shortcut-Token": token
    }

    response = requests.get(labels_endpoint,
                             headers=headers
                            )

    if response.status_code == 200:
        labels_data = response.json()
        label_ids = [
            label['id'] for label in labels_data
            if label['name'] in label_names
        ]
        return label_ids


def main():
    args = get_args()
    access_token = args.access_token
    name = args.name
    description = args.description
    issue_type = args.issue_type
    source_file_name = args.source_file_name
    source_folder_name = args.source_folder_name
    source_file_name_match_type = args.source_file_name_match_type

    # query payload
    query_data = {}
    if args.estimate:
        query_data["estimate"] = args.estimate

    if args.deadline:
        query_data["deadline"] = convert_date_to_shortcut(args.deadline)

    if args.created_at:
        query_data['created_at'] = convert_date_to_shortcut(args.created_at)

    if args.external_links:
        query_data['external_links'] = literal_eval(args.external_links)

    if args.project_id:
        query_data["project_id"] = args.project_id

    if args.custom_json:
        query_data['custom_fields'] = args.custom_json
    
    # add attachments
    file_ids = []
    if source_file_name_match_type == 'regex_match':
        all_local_files = shipyard.files.find_all_local_file_names(
            source_folder_name)
        matching_file_names = shipyard.files.find_all_file_matches(
            all_local_files, re.compile(source_file_name))
        for index, file_name in enumerate(matching_file_names):
            file_data = upload_file_attachment(access_token,
                                file_name)
            file_id = file_data[0]['id']
            file_ids.append(file_id)
    else:
        source_file_path = shipyard.files.combine_folder_and_file_name(
            source_folder_name, source_file_name)
        file_data = upload_file_attachment(access_token,
                            source_file_path)
        file_id = file_data[0]['id']
        file_ids.append(file_id)
    
    if file_ids:
        query_data['file_ids'] = file_ids
    
    story_data = create_story(access_token, name, description, issue_type, 
                query_data)

    story_id = story_data['id']
    
    # save issue to responses
    issue_data_filename = shipyard.files.combine_folder_and_file_name(
        artifact_subfolder_paths['responses'],
        f'create_story_{story_id}_response.json')
    shipyard.files.write_json_to_file(story_data, issue_data_filename)

    

if __name__ == "__main__":
    main()