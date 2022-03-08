import pandas as pd
from DDDS.utils import Logs
from DDDS.annotations import Annotations
from DDDS.hrv import HRV

class CombinedDFs(Logs):
    def __init__(self, debug=False):
        super().__init__(debug)

        # Create instances of both classes
        self.print('-- Loading annotations --')
        annotations = Annotations()
        self.print('-- Loading HRV --')
        hrv = HRV()
        self.hrv_dfs = hrv.get_dataframes()

        # Get a list of HRV keys corresponding to Annotation DF
        keys = []
        for date, driver in annotations.dates_drivers:
            keys.append(self.get_hrv_id(date, driver))
        self.hrv_dfs_ordered = [hrv.dataframes[key] for key in keys]

        # Combine
        self.combined_dfs = []
        for hrv, annot in zip(self.hrv_dfs_ordered, annotations.annotations):
            df = pd.concat([hrv, annot], ignore_index=True)
            df = df.sort_values('Timestamp_Google')
            df = df.reset_index()
            df = df.drop(columns=['index', 'Timestamp_Device'], errors='ignore')
            df = df.set_index('Timestamp_Google')
            self.combined_dfs.append(df)
        
        self.print('-- DONE --')
    
    def get_hrv_id(self, date, driver):
        """
        Returns key in hrv.dataframes dictionary corresponding to date and driver
        """
        for key in self.hrv_dfs.keys():
            if date in key and driver in key:
                return key
    