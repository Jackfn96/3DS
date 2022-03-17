import os, sys
import numpy as np
import pandas as pd
import cv2 as cv
import streamlit as st
import matplotlib.pyplot as plt
from contextlib import contextmanager
from threading import current_thread
from io import StringIO
from PIL import Image
from DDDS.combined_df import CombinedDFs
from mtcnn import MTCNN
from DDDS.face import FACE_IMG_SIZE, build_model, face_detect

### DATA SETTINGS ###
VIDEO_PATH = 'data/red_or_green_line.avi'#2021-11-18 13-21-41 e99.flv'
RR_SERIES_ID = '24_11_2021_15_34 e99'
DF_NUMBER = 7

### MODEL SELECTION ###
KSS_MODEL_VERSION = 'model_base.h5'#'vgg16_model_5.h5'
FACE_IMG_SIZE = (244, 244)

### SETTINGS ###
FRAMES_PER_SECOND = 30  # FPS of the original video. DO NOT CHANGE
HRV_GRAPH_DURIATION = 60_000 # Duration of heart rate graph history (ms)
HRV_GRAPH_YLIM = [500, 1500] # xLim of HRV graph
KSS_LIMITS = {  'red': 7.5, # By default label is green. Set thresholds to turn blue, yellow and red
                'yellow': 5.0,
                'blue': 3.0}
KSS_LABELS = ['Fully awake', 'Awake', 'Tired', 'Drowsy']    # Labels for KSS model display (correspond to colors)
DISPLAY_EVENTS = 16 # Number if annotations to be displayed on screen


### UTILITIES ###
def get_time(td):
    def double_digit(number):
        return '0'+str(number) if number < 10 else number
    
    return f"{double_digit(td.minutes)}:{double_digit(td.seconds)}   +{td.hours} hrs"


### PAGE SETTINGS ###
st.set_page_config(layout='wide')
plt.style.use("dark_background")

### HANDLING TERMINAL OUTPUT ### 
@contextmanager
def st_redirect(src, dst):
    placeholder = st.empty()
    output_func = getattr(placeholder, dst)

    with StringIO() as buffer:
        old_write = src.write
        
        def new_write(b):
            if getattr(current_thread(), 'streamlit_script_run_ctx', None):
                buffer.write(b)
                output_func(buffer.getvalue())
            else:
                old_write(b)
        
        try:
            src.write = new_write
            yield
        finally:
            src.write = old_write


@contextmanager
def st_stdout(dst):
    with st_redirect(sys.stdout, dst):
        yield

# @contextmanager
# def st_stderr(dst):
#     with st_redirect(sys.stderr, dst):
#         yield


### SESSION STATE ###

if 'frame_no' not in st.session_state:
    # First time loading, frame number set to zero
    st.session_state.frame_no = 0

if 'instant' not in st.session_state:
    st.session_state.instant = 0

if 'capture' not in st.session_state:
    # If video has not been loaded yet
    st.session_state.capture = cv.VideoCapture(os.path.abspath(VIDEO_PATH))

if 'last_frame' not in st.session_state:
    # Load the first frame
    _, frame = st.session_state.capture.read()
    st.session_state.frame_no += 1
    st.session_state.last_frame = Image.fromarray(frame)

if 'events' not in st.session_state:
    st.session_state.events = []

if 'df' not in st.session_state:
    with st_stdout('code'):
        dfs = CombinedDFs()
        st.session_state.df = dfs.combined_dfs[DF_NUMBER]

if 'annotations' not in st.session_state:    
    # Select only annotations
    df = st.session_state.df.copy()
    annotations = df[- df['Instant'].isna()].reset_index().set_index('Instant')[['evenement']]
    tds = pd.to_timedelta(annotations.index, unit='ms')
    time = [get_time(td.components) for td in tds]
    annotations['time_lapsed'] = time
    st.session_state.annotations = annotations
    
if 'hrv' not in st.session_state:
    data = dfs.hrv.get_RR_series(RR_SERIES_ID)
    data = pd.DataFrame({'RR':data[0], 'CumSum':data[1]})

    # Timestamp Google for instant=0
    ts_google = df[- df['Instant'].isna()].index[0]
    instant = df[- df['Instant'].isna()].iloc[0]['Instant']
    ts_google_zero = ts_google - pd.Timedelta(instant, unit='ms')

    # Calculating offset
    df = st.session_state.df
    ts_google_first = df[df['RR_rate'] != '[]'].index[0]
    offset = ts_google_zero - ts_google_first
    instant_offset = round(offset.total_seconds()*1_000)

    data['CumSum'] = data['CumSum'] - instant_offset
    st.session_state.hrv = data.set_index('CumSum').loc[0:]

KSS_columns = [str(x) for x in range(1, 11)]
if 'KSS_probas' not in st.session_state:
    st.session_state.KSS_probas = pd.DataFrame([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]], columns=KSS_columns)

if  'KSS_model' not in st.session_state:
    st.session_state.KSS_model = build_model(KSS_MODEL_VERSION)
    st.session_state.MTCNN = MTCNN()

if 'face_detected' not in st.session_state:
    st.session_state.face_detected = False

frame_no = st.session_state.frame_no
instant = st.session_state.instant
capture = st.session_state.capture
last_frame = st.session_state.last_frame
annotations = st.session_state.annotations
KSS_model = st.session_state.KSS_model

def reload():
    st.session_state.pop('frame_no')
    st.session_state.pop('instant')
    st.session_state.pop('capture')
    st.session_state.pop('last_frame')
    st.session_state.pop('KSS_probas')
    st.session_state.pop('KSS_model')
    st.session_state.pop('events')
    st.session_state.pop('face_detected')

### SIDEBAR ###
skip_frames = st.sidebar.number_input('Display every N frame:', 1, 500, FRAMES_PER_SECOND)
play = st.sidebar.checkbox('Play / pause')
fast_forward = st.sidebar.checkbox('Fast forward')
st.sidebar.write('---')
st.sidebar.button('Restart', on_click=reload)


### TOP INFO DISPLAY ###
columns_header = st.columns(2)
with columns_header[0]:
    def show_face_detection():
        with face_detect_indicator:
            if st.session_state.face_detected:
                st.success('Face detected')
            else:
                st.warning('No face detected')

    face_detect_indicator = st.empty()
    show_face_detection()

with columns_header[1]:
    def instant_to_time(instant):
        td = pd.Timedelta(instant, unit='ms').components
        with instant_text:
            st.code(f"Time lapsed: {get_time(td)}")

    instant_text = st.empty()
    instant_to_time(instant)


### TOP SECTION ###
columns_top = st.columns(2)

### VIDEO SCREEN ###
with columns_top[0]:
    video = st.image(last_frame)

### ANNOTATIONS SCREEN ###
def refresh_annotations(events, annotations):
    code = ""
    # Show last elements and reverse order
    for time_lapsed, event in events[-DISPLAY_EVENTS:][::-1]:
           code += f"{time_lapsed} | {event}\n"
    annotations.code(code)

with columns_top[1]:
    annotations_list = st.empty()
    refresh_annotations(st.session_state.events, annotations_list)


### BOTTOM SECTION ###
columns_bottom = st.columns(2)

### HRV GRAPH CONTAINER ###
def refresh_graph(instant, hrv, container):
        begin = instant - HRV_GRAPH_DURIATION
        if begin < 0:
            begin = 0
        end = instant
        data = hrv['RR'].loc[begin:end]

        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot(data)
        ax.set_title('Hear Rate Variability')
        ax.set_xticklabels([])
        ax.set_ylabel('Variability')
        ax.set_xlabel(f"Time [{int(HRV_GRAPH_DURIATION/1_000)} sec]")
        ax.set_ylim(HRV_GRAPH_YLIM)
        container.pyplot(fig)
        plt.close()

with columns_bottom[0]:
    graph_container = st.empty()
    refresh_graph(st.session_state.instant, st.session_state.hrv, graph_container)

### KSS CONTAINER ###
def show_kss():
    # Calculate weighted average of results
    average_scores = st.session_state.KSS_probas.mean(axis=0)
    sum=0
    for scale, score in average_scores.items():
        sum += int(scale)*score

    sum *= 1.1

    with kss_bar:
        st.progress(int(sum*10))
    
    with kss_label:
        if sum > KSS_LIMITS['red']:
            st.error(KSS_LABELS[3])
        elif sum > KSS_LIMITS['yellow']:
            st.warning(KSS_LABELS[2])
        elif sum > KSS_LIMITS['blue']:
            st.info(KSS_LABELS[1])
        else:
            st.success(KSS_LABELS[0])

with columns_bottom[1]:
    kss_label = st.empty()
    kss_bar = st.empty()
    show_kss()


### VIDEO PLAYING ###
while play:
    play, frame = capture.read()
    frame_image = Image.fromarray(frame)
    st.session_state.frame_no += 1
    st.session_state.instant = st.session_state.frame_no * 1_000/FRAMES_PER_SECOND # 30fps so 1 frame is 1/30sec
    
    if st.session_state.frame_no % skip_frames == 0 and not fast_forward:
        # Render frame
        
        video.image(frame_image)

        # GRAPH CONTAINER
        refresh_graph(st.session_state.instant, st.session_state.hrv, graph_container)

        # KSS detection
        crop_frame = face_detect(frame, st.session_state.MTCNN, FACE_IMG_SIZE)
        if crop_frame is None:
            st.session_state.face_detected = False
            continue
        st.session_state.face_detected = True

        KSS_probas = KSS_model.predict(np.expand_dims(crop_frame, axis=0))[0]
        # Add newest results and restrict to max 10 last measurements
        st.session_state.KSS_probas = pd.concat([st.session_state.KSS_probas, pd.DataFrame([KSS_probas], columns=KSS_columns)])\
                                        .tail(10)

        show_kss()
    show_face_detection()
    
    with instant_text:
        instant_to_time(st.session_state.instant)

    annotations_to_display = annotations.loc[:st.session_state.instant]
    for row in annotations_to_display.iterrows():
        event = (row[1]['time_lapsed'], row[1]['evenement'])
        if event not in st.session_state.events:
            st.session_state.events.append(event)
    
    refresh_annotations(st.session_state.events, annotations_list)
            
    st.session_state.last_frame = frame_image
