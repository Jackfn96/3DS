"""
Reading data from Google Drive
"""

import os.path
import io
from DDDS.logs import Logs
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

class Drive(Logs):
    # Defines the level of access to Google Drive
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

    def __init__(self, debug=False):
        """
        Authentication to Google Drive
        """
        # init of Logs class
        super().__init__(debug)

        self.parent = None

        # set file paths
        token_path = os.path.abspath(os.path.join(__file__, '..', '..', 'token.json'))
        api_key_path = os.path.abspath(os.path.join(__file__, '..', '..', '3ds_gcloud_api.json'))

        # Check for local authentication token
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    api_key_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        # Build drive service connection
        try:
            service = build('drive', 'v3', credentials=creds)
            self.print('Connected successfully!')
            self.service = service
        except HttpError as error:
            # TODO - Improve error handling
            self.print(f'Unable to build Google Drive service connection: {error}')
            return
        
        try:
            self.get_partent_id()
        except LookupError as error:
            self.print(f'Ann error occured: {error}')
            return
        



    def list(self, file_type, query=None):
        """
        Lists items of selected type
        Query as per instruction in https://developers.google.com/drive/api/v3/ref-search-terms
        """
        mime = {'flv': 'video/flv',
                'csv': 'text/csv',
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'txt': 'text/plain',
                'folder': 'application/vnd.google-apps.folder'}
        
        if file_type not in mime.keys():
            self.print(f"Wrong file type - {file_type}!")
            return
        
        page_token = None
        records = []
        
        if query:
            query = f"mimeType = '{mime[file_type]}' and " + query
        else:
            query = f"mimeType = '{mime[file_type]}'"

        while True:
            response = self.service.files().list(q=query,
                                                spaces='drive',
                                                fields='nextPageToken, files(id, name)',
                                                pageToken=page_token).execute()
            for file in response.get('files', []):
                records.append(file)
                
            page_token = response.get('nextPageToken', None)
            
            if page_token is None:
                break
        
        return records
    
    def get_partent_id(self):
        folder_list = self.list('folder', query="name = 'core simulateur'")

        if len(folder_list) != 1:
            raise LookupError('Unable to find Google Drive parent folder')
        
        self.parent = folder_list[0]['id']