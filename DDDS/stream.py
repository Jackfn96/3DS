import os, sys
import numpy as np
import pandas as pd
import cv2 as cv
import streamlit as st
from contextlib import contextmanager
from threading import current_thread
from io import StringIO
from collections import deque
from PIL import Image
from DDDS.annotations import Annotations
from DDDS.hrv import HRV

FRAMES_PER_SECOND = 30


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

@contextmanager
def st_stderr(dst):
    with st_redirect(sys.stderr, dst):
        yield

### SESSUIB STATE ###

if 'frame_no' not in st.session_state:
    # First time loading, frame number set to zero
    st.session_state.frame_no = 0
if 'instant' not in st.session_state:
    st.session_state.instant = 0
if 'capture' not in st.session_state:
    # If video has not been loaded yet
    video_path = os.path.abspath('data/2021-11-22 15-40-50 eb0.flv')
    st.session_state.capture = cv.VideoCapture(video_path)
if 'last_frame' not in st.session_state:
    # Load the first frame
    _, frame = st.session_state.capture.read()
    st.session_state.frame_no += 1
    st.session_state.last_frame = Image.fromarray(frame)
if 'annotations' not in st.session_state:
    with st_stdout('code'):
        annotations = Annotations()
    video_annotations = annotations.annotations[1].set_index('Instant')
    seconds = pd.to_timedelta(video_annotations.index, unit='ms').seconds
    minutes = np.floor(seconds / 60)
    seconds = seconds - minutes*60
    time = [f"{int(minute)}:{int(second)}" for minute, second in zip(minutes, seconds)]
    video_annotations['time_lapsed'] = time
    st.session_state.annotations = video_annotations
if 'events' not in st.session_state:
    st.session_state.events = []
if 'hrv' not in st.session_state:
    hrv = HRV()
    with st_stdout('code'):
        hrv.get_dataframes()
    data =  hrv.get_RR_series('22_11_2021_15_38 eb0')
    st.session_state.hrv = pd.DataFrame(data[0], index=data[1])
    

    
frame_no = st.session_state.frame_no
instant = st.session_state.instant
capture = st.session_state.capture
last_frame = st.session_state.last_frame
annotations = st.session_state.annotations

### SIDEBAR ###
skip_frames = st.sidebar.number_input('Skip frames', 1, 500, 29)
play = st.sidebar.checkbox('Play / pause')


### TOP INFO DISPLAY ###
frame_no_text = st.text(f"Frame number {frame_no}")
instant_text = st.text(f"Instant: {round(instant)}")


### LEFT SCREEN ###
columns = st.columns(2)
with columns[1]:
    
    event_container = st.container()
    with event_container:
        for time_lapsed, event in st.session_state.events:
            st.code(f"{time_lapsed} | {event}")

### RIGHT SCREEN ###
with columns[0]:
    video = st.image(last_frame)

### GRAPH CONTAINER ###
graph_container = st.container()
with graph_container:
    st.line_chart(st.session_state.hrv[0], use_container_width=True)

while play:
    play, frame = capture.read()
    frame_image = Image.fromarray(frame)
    st.session_state.frame_no += 1
    if st.session_state.frame_no % skip_frames == 0:
        video.image(frame_image)
    
    
    frame_no_text.text(f"Frame number {st.session_state.frame_no}")

    st.session_state.instant = st.session_state.frame_no * 1_000/FRAMES_PER_SECOND # 30fps so 1 frame is 1/30sec
    instant_text.text(f"Instant: {round(st.session_state.instant)}")

    annotations_to_display = annotations.loc[:st.session_state.instant]
    for row in annotations_to_display.iterrows():
        event = (row[1]['time_lapsed'], row[1]['evenement'])
        if event not in st.session_state.events:
            st.session_state.events.append(event)
            with event_container:
                st.code(f"{event[0]} | {event[1]}")
            

    st.session_state.last_frame = frame_image