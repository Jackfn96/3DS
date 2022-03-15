import re
from DDDS.hrv import HRV
from cv2 import add
import pandas as pd
from DDDS.utils import Logs, printProgressBar
from DDDS.drive import Drive

class Annotations(Logs):

    def __init__(self, debug=False, drive=None):
        super().__init__(debug=debug)

        self.drive = drive if drive else Drive()

        # List folders and select 'Video validations'
        # This folder includes video annotation files which have been validated
        folders = self.drive.list('folder')
        validations_folder = [folder['id'] for folder in folders if folder['name'] == 'Video validations'][0]
        validated_videos = self.drive.list('csv', add_query=f"'{validations_folder}' in parents")

        # Get the ID of files to obtain sync and hrv files
        self.dates_drivers = []
        for video in validated_videos:
            date_time_id = self.get_date_time_id(video['name'])
            self.dates_drivers.append(self.get_hrv_format_date_id(date_time_id))
        
        # Get sync files
        sync_files = []
        i = 0
        max = len(self.dates_drivers)
        printProgressBar(0, max, prefix="Searching files...", suffix="Complete", length=50)
        for date_driver in self.dates_drivers:
            i += 1
            printProgressBar(i, max, prefix="Searching sync files...", suffix="Completed", length=50)

            query = f"(name contains 'annotation_{date_driver[0]}' and name contains '{date_driver[1]}')"
            sync_files += self.drive.list('csv', add_query=query)

        # Download sync files and get timestamps list
        self.print('Downloading sync files')
        sync_files_content = self.drive.download([file['id'] for file in sync_files])
        self.exp_start_timestamps = []
        for file in sync_files_content:
            df = pd.read_csv(file, index_col=[0])
            # Get 'exp_start' first column
            # usually it's timestamp_goole but sometimes timetamp
            self.exp_start_timestamps.append(df.loc['exp_start'][df.columns[0]])
        
        # Download annotation files
        self.print('Downloading annotation files')
        annotation_content = self.drive.download([video['id'] for video in validated_videos])
        self.annotations = []
        i=0
        for file in annotation_content:
            # Read CSV and drop useless columns
            df = pd.read_csv(file).drop(columns=['timestamp_lena', 'Unnamed: 0'])
            # Select only confirmed events
            df = df[df['validation'] == 1]
            df['Aligned_instant'] = df['Instant'] - df.iloc[0]['Instant']
            df['Timestamp_Google'] = pd.to_timedelta(df['Aligned_instant'], unit='ms') + pd.Timestamp(self.exp_start_timestamps[i], unit='ms')
            self.annotations.append(df)
            i += 1
        
        self.print('Done!')

    
    def get_date_time_id(self, file_name):
        """
        Takes validated annotation name as an argument (files in 'Video validations' folder)
        Returns tuple of year, month, day, hour, minute, driver_id
        """
        space_split = file_name.split(' ')
        date_split = space_split[0].split('-')
        time_split = space_split[1].split('-')
        driver_id = space_split[-1].split('.')
        # year, month, day, hour, minute, driver_id
        return (date_split[1], date_split[2], date_split[3], time_split[0], time_split[1], driver_id[0])
    
    def get_hrv_format_date_id(self, date_time_id):
        """
        Takes result of get_date_time_id as argument
        Returns tuple of date in HRV format and driver id
        """
        return f"{date_time_id[2]}_{date_time_id[1]}_{date_time_id[0]}", date_time_id[5]
    
    ### !!! NEED TO ADD THESE 2 FUNCTIONS IN TO THE MODULE

    # def get_hrv_id(self, date, driver):
    #     """
    #     Returns key in hrv.dataframes dictionary corresponding to date and driver
    #     """
    #     for key in HRV.dataframes.keys():
    #         if date in key and driver in key:
    #             return key
    
    # def get_combined_dfs(self):
    #     self.keys = []
    #     for i in range(len(self.dates_drivers)):
    #         self.keys.append(self.get_hrv_id(*self.dates_drivers[i]))
        
    #     self.hrv_dataframes = [self.dataframes[key] for key in self.keys]

    #     self.annotation_dataframes = []
    #     for i in range(len(self.annotations)):
    #         self.annotation_dataframes.append(self.annotations[i])

    #     self.combined_dfs = []

    #     for hrv, annot in zip(self.hrv_dataframes, self.annotation_dataframes):
    #         df = pd.concat([hrv, annot], ignore_index=True)
    #         df = df.sort_values('Timestamp_Google')
    #         df = df.reset_index()
    #         df = df.drop(columns=['index', 'Timestamp_Device'], errors='ignore')
    #         self.combined_dfs.append(df)
        
    #     return self.combined_dfs
    
