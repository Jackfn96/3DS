import re
import pandas as pd
from DDDS.utils import Logs
from DDDS.drive import Drive

class Annotations(Logs):
    FILE_HEADERS = [
        ['Timestamp_Google', 'Timestamp_Device', 'Device_id', 'Heart_Rate', 'RR_rate']
        ['Timestamp_Google', 'Timestamp_Device', 'RR_rate']
        ['Timestamp_Google', 'Device_id', 'Heart_Rate', 'RR_rate']
    ]