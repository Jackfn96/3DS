import os, sys
import numpy as np
import pandas as pd
import cv2 as cv
import streamlit as st
from contextlib import contextmanager
from threading import current_thread
from io import StringIO
from PIL import Image
from DDDS.combined_df import CombinedDFs
from mtcnn import MTCNN
from DDDS.face import build_model, face_detect


FRAMES_PER_SECOND = 30
HRV_GRAPH_DURIATION = 100_000 #ms


### PAGE SETTINGS ###
st.set_page_config(layout='wide')

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
    video_path = os.path.abspath('data/2021-11-18 13-21-41 e99.flv')
    st.session_state.capture = cv.VideoCapture(video_path)

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
        st.session_state.df = dfs.combined_dfs[30]

if 'annotations' not in st.session_state:    
    # Select only annotations
    df = st.session_state.df
    annotations = df[- df['Instant'].isna()].reset_index().set_index('Instant')[['evenement']]
    seconds = pd.to_timedelta(annotations.index, unit='ms').seconds
    minutes = np.floor(seconds / 60)
    time = [f"{int(minute)}:{int(second)}" for minute, second in zip(minutes, seconds)]
    annotations['time_lapsed'] = time
    st.session_state.annotations = annotations
    
if 'hrv' not in st.session_state:
    data = dfs.hrv.get_RR_series('18_11_2021_13_19 e99')
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

KSS_columns = [str(x) for x in range(10)]
if 'KSS_probas' not in st.session_state or 'KSS_model' not in st.session_state:
    print('Loading Neural Network...')
    st.session_state.KSS_probas = pd.DataFrame([[0.2, 0.1, 0, 0, 0.4, 0, 0, 0.1, 0.2, 0]], columns=KSS_columns)
    st.session_state.KSS_model = build_model()
    st.session_state.MTCNN = MTCNN()


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

### SIDEBAR ###
skip_frames = st.sidebar.number_input('Skip frames', 1, 500, 29)
play = st.sidebar.checkbox('Play / pause')
st.sidebar.button('Reload', on_click=reload)



### TOP INFO DISPLAY ###
def instant_to_time(instant):
    td = pd.Timedelta(instant, unit='ms').components
    with instant_text:
        st.code(f"Time lapsed: {td.minutes}:{td.seconds}")

instant_text = st.empty()
instant_to_time(instant)


### TOP SECTION ###
columns_top = st.columns(2)

### LEFT SCREEN ###
with columns_top[1]:
    event_container = st.container()
    with event_container:
        for time_lapsed, event in st.session_state.events:
            st.code(f"{time_lapsed} | {event}")

### RIGHT SCREEN ###
with columns_top[0]:
    video = st.image(last_frame)


### BOTTOM SECTION ###
columns_bottom = st.columns(2)

### HRV GRAPH CONTAINER ###
def refresh_graph(instant, hrv, container):
            begin = instant - HRV_GRAPH_DURIATION
            if begin < 0:
                begin = 0
            end = instant
            container.line_chart(hrv['RR'].loc[begin:end])

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

    with kss_bar:
        st.progress(int(sum*10))
    
    with kss_label:
        if sum > 7.5:
            st.error('Drowsy')
        elif sum > 4.5:
            st.warning('Tired')
        elif sum > 3.0:
            st.info('Awake')
        else:
            st.success('Fully awake')

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
    
    if st.session_state.frame_no % skip_frames == 0:
        video.image(frame_image)

        # GRAPH CONTAINER
        refresh_graph(st.session_state.instant, st.session_state.hrv, graph_container)

        # KSS detection
        crop_frame = face_detect(frame, st.session_state.MTCNN)
        if crop_frame is None:
            continue
        KSS_probas = KSS_model.predict(np.expand_dims(crop_frame, axis=0))[0]
        # Add newest results and restrict to max 10 last measurements
        st.session_state.KSS_probas = pd.concat([st.session_state.KSS_probas, pd.DataFrame([KSS_probas], columns=KSS_columns)])\
                                        .tail(50)

        show_kss()
    
    with instant_text:
        instant_to_time(st.session_state.instant)

    annotations_to_display = annotations.loc[:st.session_state.instant]
    for row in annotations_to_display.iterrows():
        event = (row[1]['time_lapsed'], row[1]['evenement'])
        if event not in st.session_state.events:
            st.session_state.events.append(event)
            with event_container:
                st.code(f"{event[0]} | {event[1]}")
            


    st.session_state.last_frame = frame_image