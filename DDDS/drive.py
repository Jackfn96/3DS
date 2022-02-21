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

        self.folders = None
        self.ids = []

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
            self.print(f'Unable to build Google Drive service connection: {error}', True)
            return
        
        try:
            self.folders = []
            self.get_partent_folder_id()
            self.get_children_folders_id()
            self.get_data_folder_id()
        except LookupError as error:
            self.print(f'An error occured: {error}', True)
            return
        


    def list(self, file_type, add_query=None, entire_drive=False):
        """
        Lists items of selected type
        Query as per instruction in https://developers.google.com/drive/api/v3/ref-search-terms
        entire_drive enables search in entire Google Drive, by default searches only in 'data' folder and
        in 'core simulateur' and it's child folders
        """
        mime = {'flv': 'video/flv',
                'csv': 'text/csv',
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'txt': 'text/plain',
                'folder': 'application/vnd.google-apps.folder'}
        
        if file_type not in mime.keys():
            self.print(f"Wrong file type - {file_type}!", True)
            return
        
        page_token = None
        records = []
        
        # Limit file type
        query = f"mimeType = '{mime[file_type]}'"

        # Limit search folders
        if not entire_drive:
            query += ' and ('
            query += ' or '.join([f"'{folder}' in parents" for folder in self.folders])
            query += ')'

        # Additional query, if any
        if add_query:
            query += f" and {add_query}"

        self.print(query, True)

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
    

    def get_partent_folder_id(self):
        """
        Searches for the main folder with project data
        """
        folder_list = self.list('folder', add_query="name = 'core simulateur'", entire_drive=True)

        if len(folder_list) != 1:
            raise LookupError('Unable to find Google Drive parent folder')
        
        self.folders.append(folder_list[0]['id'])
    

    def get_children_folders_id(self):
        """
        Searches for folders in self.parent_folder and adds them to self.children_folders
        """
        folder_list = self.list('folder', add_query=f"'{self.folders[0]}' in parents", entire_drive=True)

        if len(folder_list) < 1:
            raise LookupError('Unable to find Google Drive children folders')

        self.folders += [folder['id'] for folder in folder_list]

    def get_data_folder_id(self):
        """
        Searches for data folder in Google Drive
        This folder includes two sub-folders: 'annotations' and 'data non utilises'
        """
        folder_list = self.list('folder', add_query=f"name = 'data'", entire_drive=True)

        for folder in folder_list:
            sub_folders = self.list('folder', add_query=f"'{folder['id']}' in parents", entire_drive=True)
            sub_folders_names = [folder['name'] for folder in sub_folders]
            if len(sub_folders) == 2\
                and 'data non utilisés' in sub_folders_names\
                and 'annotations' in sub_folders_names:
                # found folder with correct sub-folders
                self.folders.append(folder['id'])
                return
        
        raise LookupError('Unable to find Google Drive data folder')


    def get_videos(self):
        """
        Returns a list of all videos in main folder
        """
        videos = self.list('flv')
        for video in videos:
            self.ids.append(video['name'].rstrip('.flv'))

    
    def get_video_data(self, id):
        """
        Searches for all files containing video ID
        """
        query = f"name contains '{id}'"

        annotations = self.list('csv', query)
        evaluations = self.list('xlsx', query)

        # HRV readings use different file name format
        id_split = id.split()
        if len(id_split) == 2:
            # add blank 'driver code'
            # TODO: find out what 'driver code' means
            id_split.append('_')
        date, time, code = id_split
        year, month, day = date.split('-')
        hour, minute, _ = time.split('-')
        hrv_datetime_query = f"name contains '{day}_{month}_{year}_{hour}'"
        if code != '_':
            hrv_code_query = f" and name contains '{code}'"
        hrv_query = hrv_datetime_query + hrv_code_query

        hrv_readings = self.list('txt', hrv_query)

        return annotations, evaluations, hrv_readings
    
    def download(self, file_id, return_bytes=False):
        """
        Downloads file from Google Drive
        by default returns string content
        return_bytes=True returns bytes file content (for non-text files)
        """
        request = self.service.files().get_media(fileId=file_id)
        with io.BytesIO() as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print("Download %d%%." % int(status.progress() * 100))
            
            if return_bytes:
                return fh.getvalue()

            return io.StringIO(fh.getvalue().decode())
    
    def save_locally(self, bytes_string, path):
        if isinstance(bytes_string, bytes):
            # if self.download return_bytes was set True
            mode = 'wb'
        else:
            # if self.download return_bytes was set False (default)
            # convert to string type
            mode = 'w'
            bytes_string = bytes_string.getvalue()

        file_path = os.path.abspath(os.path.join(__file__, '..', '..', 'data', path))
        with open(file_path, mode) as file_handler:
            file_handler.write(bytes_string)
        
        self.print(f"File saved to {file_path}")
        return file_path


if __name__ == '__main__':
    # enable commection to Google Drive
    drive = Drive()