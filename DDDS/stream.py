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
if 'annots_module' not in st.session_state:
    with st_stdout('code'):
        annotations = Annotations()
    video_annotations = annotations.annotations[1].set_index('Instant')
    seconds = pd.to_timedelta(video_annotations.index, unit='ms').seconds
    minutes = np.floor(seconds / 60)
    seconds = seconds - minutes*60
    time = [f"{int(minute)}:{int(second)}" for minute, second in zip(minutes, seconds)]
    video_annotations['time_lapsed'] = time
    st.session_state.annots_module = video_annotations
    
    
### SIDEBAR SETTINGS ###

# How many frames to be skipped
skip_frames = st.sidebar.number_input('Skip frames', 1, 500, 29)

play = st.sidebar.checkbox('Play / pause')

### DISPLAY SECTION ###
DISPLAY_ANNOTS = 20_000 #ms


frame_no = st.empty()
frame_no.text(f"Frame number {st.session_state.frame_no}")

instant = st.empty()
instant.text(f"Instant: {round(st.session_state.instant)}")

video_annotations = st.session_state.annots_module
annot_container = st.empty()

video = st.image(st.session_state.last_frame)



while play:
    play, frame = st.session_state.capture.read()
    frame_image = Image.fromarray(frame)
    if st.session_state.frame_no % skip_frames == 0:
        video.image(frame_image)
    
    st.session_state.frame_no += 1
    frame_no.text(f"Frame number {st.session_state.frame_no}")

    st.session_state.instant = st.session_state.frame_no * 1_000/FRAMES_PER_SECOND # 30fps so 1 frame is 1/30sec
    instant.text(f"Instant: {round(st.session_state.instant)}")

    new_annotations = video_annotations.loc[st.session_state.instant-DISPLAY_ANNOTS:st.session_state.instant][['time_lapsed', 'evenement']]
    if len(new_annotations)>0:
        time, event = new_annotations.iloc[0]
        annot_container.code(f"{time} | {event}")
    else:
        annot_container.empty()

    st.session_state.last_frame = frame_image