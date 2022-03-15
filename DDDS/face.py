import os, cv2
import pandas as pd
from mtcnn import MTCNN # via conda-forge mtccn, via pip mtcnn_cv2

from tensorflow.keras.models import load_model
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import keras
from keras.preprocessing import image   # for preprocessing the images
from keras.utils import np_utils
from keras.models import Sequential
from keras.applications.vgg16 import VGG16
from keras.layers import Dense, InputLayer, Dropout, Flatten
from keras.layers import Conv2D, MaxPooling2D, GlobalMaxPooling2D
from keras.preprocessing import image
from keras.models import Sequential
from keras.layers import Conv2D, MaxPooling2D
from keras.layers import Activation, Dropout, Flatten, Dense
from keras.regularizers import l2
from keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array, load_img
from sklearn.model_selection import train_test_split
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import VGG16
from tensorflow.keras.layers import Dropout, Flatten, Dense, Input
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import SGD

# coordiante of the face (approximately center)
FACE_CENTER = (1100, 200)
MODEL_PATH = os.path.abspath(os.path.join(__file__, '..', '..', 'models'))
FACE_IMG_SIZE = (244, 244)


def bounding_box_check(faces, x, y):
    OFFSET = 100
    
    for face in faces:
        bounding_box = face['box']
        if (bounding_box[1] < 0):
            bounding_box[1] = 0
        if (bounding_box[0] < 0):
            bounding_box[0] = 0
        if (bounding_box[0] - OFFSET > x
                or bounding_box[0] + bounding_box[2] + OFFSET < x):
            # print('change person from')
            # print(bounding_box)
            # print('to')
            continue
        if (bounding_box[1] - OFFSET > y
                or bounding_box[1] + bounding_box[3] + OFFSET < y):
            # print('change person from')
            # print(bounding_box)
            # print('to')
            continue
        return bounding_box


def face_detect(frame, mtcnn):
    x, y = FACE_CENTER
    faces = mtcnn.detect_faces(frame)
    # check if detected faces
    if (len(faces) == 0):
        return
    bounding_box = bounding_box_check(faces, x, y)
    if (bounding_box == None):
        # print('face is not related to given coord')
        return
    crop_img = frame[bounding_box[1]:bounding_box[1] + bounding_box[3],
                   bounding_box[0]:bounding_box[0] + bounding_box[2]]
    crop_img = cv2.resize(crop_img, FACE_IMG_SIZE)
    return crop_img



def build_model(model = 'model_base.h5'):
    # model_base = Sequential()

    # model_base.add(Conv2D(32, (3, 3), activation='relu',
    #                     kernel_initializer='he_uniform', kernel_regularizer=l2(0.01), 
    #                     padding='same', input_shape=(244, 244, 3)))
    # model_base.add(Conv2D(32, (3, 3), activation='relu', kernel_initializer='he_uniform', 
    #                     kernel_regularizer=l2(0.01), padding='same'))
    # model_base.add(MaxPooling2D((2, 2)))

    # model_base.add(Conv2D(64, (3, 3), activation='relu',kernel_initializer='he_uniform', 
    #                     kernel_regularizer=l2(0.01), padding='same'))
    # model_base.add(Conv2D(64, (3, 3), activation='relu',kernel_initializer='he_uniform',
    #                     kernel_regularizer=l2(0.01), padding='same'))
    # model_base.add(MaxPooling2D((2, 2)))

    # # flattenign the 3D features
    # # example output part of the model
    # model_base.add(Flatten())
    # model_base.add(Dense(128, activation='relu', kernel_initializer='he_uniform',
    #                 kernel_regularizer=l2(0.01)))
    # model_base.add(Dense(10, activation='softmax', kernel_regularizer=l2(0.01)))
    # model_base.compile(loss='categorical_crossentropy',
    # #               optimizer='rmsprop',
    #             optimizer='adam',
    #             metrics=['accuracy'])
    
    model_file = os.path.join(MODEL_PATH, model)
    if not os.path.exists(model_file):
        raise FileExistsError(f"Model file {model_file} doesn't exists")
    
    model_base = load_model()
    return model_base