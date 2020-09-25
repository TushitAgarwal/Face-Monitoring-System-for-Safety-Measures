import cv2
import sys
import numpy as np
from PyQt5 import QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import MainWindow_gui
import dlib
from imutils import face_utils
import tensorflow as tf

import tarfile
import urllib 
import os
from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as vis_util


class FaceSecurityML(QMainWindow, MainWindow_gui.Ui_MainWindow):

    # serialWrite = QtCore.pyqtSignal(object)

    def __init__(self):
        super(FaceSecurityML, self).__init__()

        self.setupUi(self)

        # What model to download.
        MODEL_NAME = 'ssd_mobilenet_v1_coco_2017_11_17'
        MODEL_FILE = MODEL_NAME + '.tar.gz'
        DOWNLOAD_BASE = 'http://download.tensorflow.org/models/object_detection/'

        # Path to frozen detection graph. This is the actual model that is used for the object detection.
        PATH_TO_CKPT = MODEL_NAME + '/frozen_inference_graph.pb'

        # List of the strings that is used to add correct label for each box.
        PATH_TO_LABELS = os.path.join('data', 'mscoco_label_map.pbtxt')

        NUM_CLASSES = 90
        #opener = urllib.request.URLopener()
        #opener.retrieve(DOWNLOAD_BASE + MODEL_FILE, MODEL_FILE)
        tar_file = tarfile.open(MODEL_FILE)
        for file in tar_file.getmembers():
            file_name = os.path.basename(file.name)
            if 'frozen_inference_graph.pb' in file_name:
                tar_file.extract(file, os.getcwd())
        self.detection_graph = tf.Graph()
        with self.detection_graph.as_default():
            od_graph_def = tf.GraphDef()
            with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
                serialized_graph = fid.read()
                od_graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(od_graph_def, name='')
        label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
        categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=NUM_CLASSES,
                                                                    use_display_name=True)
        self.category_index = label_map_util.create_category_index(categories)
        self.sess = tf.Session(graph=self.detection_graph)

        self.openCameraButton.clicked.connect(self.openCameraClicked)
        self.stopCameraButton.clicked.connect(self.stopCameraClicked)
        self.startDetectionButton.clicked.connect(self.startAllDetection)
        self.stopDetectionButton.clicked.connect(self.stopAllDetection)
        self.exitButton.clicked.connect(self.exitClicked)

        print("[INFO] loading facial landmark predictor...")
        self.faceCascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        self.predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')

        # grab the indexes of the facial landmarks for the left and
        # right eye, respectively

        (self.lStart, self.lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
        (self.rStart, self.rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]
        (self.mStart, self.mEnd) = face_utils.FACIAL_LANDMARKS_IDXS["mouth"]

        self.EYE_AR_THRESH = 0.3
        self.EYE_AR_CONSEC_FRAMES = 20
        self.COUNTER = 0
        self.YAWN_COUNTER = 0
        self.FACE_COUNTER = 0
        self.ALARM_ON = False
        self.start_detection_Flag = False
        self.frequency = 3500
        self.duration = 1000
        # self.speak = wincl.Dispatch("SAPI.SpVoice")
        self.systemStatusFlag = False

    @pyqtSlot(bool)
    def updateSystemStatus(self, status):
        self.systemStatusFlag = status

    @pyqtSlot()
    def startAllDetection(self):
        self.start_detection_Flag = True
        # self.SerialThread.start()

    @pyqtSlot()
    def stopAllDetection(self):
        self.start_detection_Flag = False
        # if (self.SerialThread.isRunning()):
        #     self.SerialThread.terminate()

    def blinkDetector(self, img):

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        rects = self.faceCascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30),
                                                  flags=cv2.CASCADE_SCALE_IMAGE)
        # import the necessary packages
        # Definite input and output Tensors for detection_graph
        image_tensor = self.detection_graph.get_tensor_by_name('image_tensor:0')
        # Each box represents a part of the image where a particular object was detected.
        detection_boxes = self.detection_graph.get_tensor_by_name('detection_boxes:0')
        # Each score represent how level of confidence for each of the objects.
        # Score is shown on the result image, together with the class label.
        detection_scores = self.detection_graph.get_tensor_by_name('detection_scores:0')
        detection_classes = self.detection_graph.get_tensor_by_name('detection_classes:0')
        num_detections = self.detection_graph.get_tensor_by_name('num_detections:0')

        # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
        image_np_expanded = np.expand_dims(img, axis=0)

        # Actual detection.
        (boxes, scores, classes, num) = self.sess.run(
            [detection_boxes, detection_scores, detection_classes, num_detections],
            feed_dict={image_tensor: image_np_expanded})
        # print(classes)
        # cat_util.

        # Visualization of the results of a detection.

        list_output = vis_util.visualize_boxes_and_labels_on_image_array(
            img,
            np.squeeze(boxes),
            np.squeeze(classes).astype(np.int32),
            np.squeeze(scores),
            self.category_index,
            use_normalized_coordinates=True,
            line_thickness=8)
        #print(list_output)
        if list_output.__contains__('cell phone') or list_output.__contains__('toothbrush') or list_output.__contains__(
                'remote') or list_output.__contains__('remote'):
            cv2.putText(img, "Be Alert!!", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            print('\a')


        # else:

        # self.DisplayImage(img, 1)

        if len(rects) is not 0:
            self.FACE_COUNTER = 0

            for (x, y, w, h) in rects:
                rect = dlib.rectangle(int(x), int(y), int(x + w), int(y + h))
                shape = self.predictor(gray, rect)
                shape = face_utils.shape_to_np(shape)

                leftEye = shape[self.lStart:self.lEnd]
                rightEye = shape[self.rStart:self.rEnd]
                leftEAR = self.eye_aspect_ratio(leftEye)
                rightEAR = self.eye_aspect_ratio(rightEye)

                mouthshape = shape[self.mStart:self.mEnd]
                mouthOpenDistance = self.euclidean_dist(mouthshape[18], mouthshape[14])
                # print(mouthOpenDistance)

                ear = (leftEAR + rightEAR) / 2.0

                leftEyeHull = cv2.convexHull(leftEye)
                rightEyeHull = cv2.convexHull(rightEye)
                cv2.drawContours(img, [leftEyeHull], -1, (0, 255, 0), 1)
                cv2.drawContours(img, [rightEyeHull], -1, (0, 255, 0), 1)

                if ear < self.EYE_AR_THRESH:
                    self.COUNTER += 1
                    # print('Counter:',self.COUNTER)

                    # if the eyes were closed for a sufficient number of
                    # frames, then sound the alarm
                    if self.COUNTER >= self.EYE_AR_CONSEC_FRAMES:
                        # if the alarm is not on, turn it on
                        if not self.ALARM_ON:
                            self.ALARM_ON = True
                            print("ALARM_ON")
                            # os.system("beep -f 555 -l 460")
                            print('\a')
                            # winsound.Beep(self.frequency, self.duration)
                            # self.sendData('a')

                        # draw an alarm on the frame
                        cv2.putText(img, "DROWSINESS ALERT!", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                        self.DisplayImage(img, 1)

                    # otherwise, the eye aspect ratio is not below the blink
                    # threshold, so reset the counter and alarm
                else:
                    self.COUNTER = 0
                    self.ALARM_ON = False
                    # self.sendData('x')

                if mouthOpenDistance > 6:
                    self.YAWN_COUNTER += 1

                    if self.YAWN_COUNTER >= 15:
                        print('Driver is Yawning !')
                        print('\a')
                        if not self.ALARM_ON:
                            self.ALARM_ON = True
                            # print("ALARM_ON")
                            # winsound.Beep(self.frequency, self.duration)

                            # self.speak.Speak("you are feeling sleepy, please refrain from driving and refresh yourself")
                            # self.sendData('a')

                            # draw an alarm on the frame
                            cv2.putText(img, "Yawning ALERT!", (100, 30),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                            self.DisplayImage(img, 1)

                else:
                    self.YAWN_COUNTER = 0
                    self.ALARM_ON = False
                    # self.sendData('x')

                    # draw the computed eye aspect ratio on the frame to help
                    # with debugging and setting the correct eye aspect ratio
                    # thresholds and frame counters
                cv2.putText(img, "EAR: {:.3f}".format(ear), (500, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                self.DisplayImage(img, 1)

        else:
            self.FACE_COUNTER += 1

            if self.FACE_COUNTER >= 15:
                print('Driver Not AWAKE !')
                # self.speak.Speak("Wake UP")
                # self.sendData('s')
                print('\a')
                cv2.putText(img, "Driver Not AWAKE !", (100, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                self.DisplayImage(img, 1)

    def parse_Serial_data(self):
        pass

    def euclidean_dist(self, ptA, ptB):
        # compute and return the euclidean distance between the two
        # points
        return np.linalg.norm(ptA - ptB)

    def eye_aspect_ratio(self, eye):
        # compute the euclidean distances between the two sets of
        # vertical eye landmarks (x, y)-coordinates

        A = self.euclidean_dist(eye[1], eye[5])
        B = self.euclidean_dist(eye[2], eye[4])

        # compute the euclidean distance between the horizontal
        # eye landmark (x, y)-coordinates
        C = self.euclidean_dist(eye[0], eye[3])

        # compute the eye aspect ratio
        ear = (A + B) / (2.0 * C)

        # return the eye aspect ratio
        return ear

    @pyqtSlot()
    def openCameraClicked(self):
        self.capture = cv2.VideoCapture(0 + cv2.CAP_DSHOW)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 600)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 800)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(0.1)

    def update_frame(self):
        ret, self.image = self.capture.read()
        self.image = cv2.flip(self.image, 1)
        if (self.start_detection_Flag == True):
            self.blinkDetector(self.image)
        else:
            self.DisplayImage(self.image, 1)

    @pyqtSlot()
    def stopCameraClicked(self):
        self.timer.stop()
        self.capture.release()

    def DisplayImage(self, img, window=1):
        qformat = QImage.Format_Indexed8
        if len(img.shape) == 3:
            if (img.shape[2]) == 4:
                qformat = QImage.Format_RGBA8888
            else:
                qformat = QImage.Format_RGB888

        outImg = QImage(img, img.shape[1], img.shape[0], img.strides[0], qformat)

        outImg = outImg.rgbSwapped()

        if window == 1:
            self.imgLabel.setPixmap(QPixmap.fromImage(outImg))
            self.imgLabel.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
            self.imgLabel.setScaledContents(True)

    @pyqtSlot()
    def exitClicked(self):
        # self.SerialThread.Close_Serial()
        QApplication.instance().quit()


app = QApplication(sys.argv)
window = FaceSecurityML()
window.show()
app.exec_()
