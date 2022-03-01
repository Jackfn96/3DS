import numpy as np
import cv2 as cv
import streamlit as st
from collections import deque
from PIL import Image
import os


if 'frame_no' not in st.session_state:
    # First time loading, frame number set to zero
    st.session_state.frame_no = 0
if 'capture' not in st.session_state:
    # If video has not been loaded yet
    video_path = os.path.abspath('data/2021-10-25 10-31-58 c27.flv')
    st.session_state.capture = cv.VideoCapture(video_path)
if 'last_frame' not in st.session_state:
    # Load the first frame
    _, frame = st.session_state.capture.read()
    st.session_state.frame_no += 1
    st.session_state.last_frame = Image.fromarray(frame)

### SIDEBAR SETTINGS ###


# How many frames to be skipped
skip_frames = st.sidebar.number_input('Skip frames', 1, 500, 29)

play = st.sidebar.checkbox('Play / pause')

frame_no = st.empty()
frame_no.text(f"Frame number {st.session_state.frame_no}")
video = st.image(st.session_state.last_frame)

while play:
    play, frame = st.session_state.capture.read()
    frame_image = Image.fromarray(frame)
    if st.session_state.frame_no % skip_frames == 0:
        video.image(frame_image)
    st.session_state.frame_no += 1
    frame_no.text(f"Frame number {st.session_state.frame_no}")
    st.session_state.last_frame = frame_image