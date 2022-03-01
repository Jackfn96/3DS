import os, glob
import pandas as pd
from DDDS.utils import Logs
from DDDS.drive import Drive

class HRV(Logs):
    def __init__(self, debug=False):
        super().__init__(debug)
        self.drive = Drive()

        list_hrv_files = self.get_files_list()
        self.dict_hrv_files = self.split_lists(list_hrv_files)

    
    def get_files_list(self):
        files_list = self.drive.list('txt')
        self.files_df = pd.DataFrame(files_list)
        return list(self.files_df.name)
    
    def split_lists(self, list_hrv_files):
        # Create two lists from the list of HRV files - 1 for simple sensor & 1 for garmin sensor
        list_hrv_files_simple_sensor = [elem for elem in list_hrv_files if elem.find('garmin') == -1]
        list_hrv_files_garmin = [elem for elem in list_hrv_files if elem.find('garmin') != -1]

        # Create a list that would be needed to split the simple sensor list into two lists
        # It is due to differences in the output of simple sensor files
        key_list = []
        for key in range(20,31):
            key_list.append(str(key) + '_10_2021')
    
        # Create the two lists from the simple sensor list
        list_hrv_files_simple_sensor_1 = []
        list_hrv_files_simple_sensor_2 = []
        for file in list_hrv_files_simple_sensor:
            if (file[:10] in key_list) and (file != '29_10_2021_13_32 982.txt'):
                list_hrv_files_simple_sensor_2.append(file)
            else:
                list_hrv_files_simple_sensor_1.append(file)
        
        # Create list of Headers for each type of HRV files
        headers_list_simple_sensor = ['Timestamp_Google', 'Timestamp_Device', 'Device_id', 'Heart_Rate', 'RR_rate']
        headers_list_garmin_sensor = ['Timestamp_Google', 'Timestamp_Device', 'RR_rate']
        headers_list_simple_sensor_2 = ['Timestamp_Google', 'Device_id', 'Heart_Rate', 'RR_rate']

        # Create a dictionary to match each HRV file with its associated Headers
        return {
            'sensors_list':[list_hrv_files_simple_sensor_1,list_hrv_files_simple_sensor_2,list_hrv_files_garmin],
            'headers_type':[headers_list_simple_sensor, headers_list_simple_sensor_2, headers_list_garmin_sensor]
        }
    

    def get_dataframes(self):
        df_list = {}
        index = 0

        files = []
        for sensor_list in self.dict_hrv_files['sensors_list']:
            for sensor in sensor_list:
                file_id = list(self.files_df[self.files_df.name == sensor].id)[0]
                files.append({'id': file_id, 'name': sensor, 'sensor_type': index})
            index += 1
        files_content = self.drive.download([file['id'] for file in files][:5])
        index = 0
        for file in files_content:
            df = pd.read_csv(file, sep=";", header=None, names=self.dict_hrv_files['headers_type'][files[index]['sensor_type']])
            if sensor.find('garmin') != -1:
                df['Garmin'] = 1
            else:
                df['Garmin'] = 0
            
            df = self.timestamp_formatting(df, "Timestamp_Google", "Timestamp_Device")
            df_list[files[index]['name'].rstrip('.txt')] = df
            index += 1

        self.dfataframes = df_list
        return self.dataframes
    

    def get_RR_series(self, ids):
        return_list = True
        #if only one ID provided
        if not isinstance(id, list):
            ids = [ids]
            return_list = False
        
        for id in ids:
            list_RR = []

            # Every value is string of 1) empty list, 2) list with one 3-digit number or 3) list of two 3-digit numbers
            # convert them to list of ints
            for i in self.df_list[id].RR_rate:
                if len(i) == 5:
                    list_RR.append(int(i[1:4]))
                elif len(i) == 10:
                    list_RR.append(int(i[1:4]))
                    list_RR.append(int(i[6:9]))
                elif len(i) == 2:
                    pass
                else:
                    raise ValueError('Value of RR_rate is not correct')
        


    ### FORMATTING ###

    def timestamp_formatting(self, df, *args):
        # Format the Timestamp features
        for timestamp in args:
            if timestamp in df.columns:
                df[timestamp] = df[timestamp].apply(lambda x: pd.Timestamp(x, unit="ms"))
        return df
    
    def drop_columns(self, df, *args):
        # Allow to drop useless columns
        for column in args:
            df.drop(column, axis=1, inplace=True)
        return df