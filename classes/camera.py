# standard imports
import os
import numpy as np
import struct
import math

# third party imports
# for image recognition
import cv2

# from pygame import time

# for audio shot detection
import pyaudio


GRAY_THRESHOLD = 150
CANNY_THRESHOLD1 = 50
CANNY_THRESHOLD2 = 100

HOUGH_MIN_DISTANCE = 500

TARGET_MIN_RADIUS = 30
TARGET_MAX_RADIUS = 60

TARGET_CIRCLE_WIDTH = 4

DETECTION_THRESHOLD = 0
DETECTION_EDGE = 1

USE_MIC = False
MIC_AUDIO_RATE = 48000
MIC_AUDIO_CHUNK = 1024
MIC_AUDIO_FORMAT = pyaudio.paInt16
MIC_NUM_CHANNELS = 1
MIC_SHORT_NORMALIZE = 1.0 / 32768.0
# auf stand 11 ca 0.70 - 0.79. Pistole auf Stand 3 wird nicht gehoert
MIC_TRIGGER_VOLUME_THRESHOLD = 0.65


# TODO: get video device by name ("v4l2-ctl --list-devices")
class Camera:
    """handles USB camera video capture, object recognition and microphone"""

    def __init__(
        self,
        webcam_id=0,
        video_backend=cv2.CAP_ANY,
        width=None,
        height=None,
        zoom_factor=1,
        fps=30,
        codec="MJPG",
        mic_id=0,
        mic_sample_rate=MIC_AUDIO_RATE,
    ):
        # microphone
        if USE_MIC:
            self.mic = CamMicrophone(mic_id, mic_sample_rate)
            print(self.mic.get_device_names())
        # raw image taken from cam
        self.raw_frame = None
        # grayscale version
        self.gray_frame = None
        # ToDo: change name
        # threshhold frame (also used for edge detection)
        self.thresh_frame = None
        # detected hough circles
        self.circles = None

        self.width = width
        self.height = height

        #  --- InitVideoCapture
        self.cam = cv2.VideoCapture(webcam_id, video_backend)
        if width is not None and height is not None:
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cam.set(cv2.CAP_PROP_ZOOM, zoom_factor)
        # set mode to MJPG for higher fpsG
        # workaround for the small Logi webcam
        self.cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*codec))
        self.cam.set(cv2.CAP_PROP_FPS, fps)
        # focus distance
        self.cam.set(cv2.CAP_PROP_FOCUS, 0)

        # radius and pos are None until detected
        self.target_pos = None
        self.target_radius = None

        # detection method
        self.detect_method = DETECTION_THRESHOLD
        # blur grey image (for both methods)
        self.blur = True
        # threshold stuff
        self.gray_threshold = GRAY_THRESHOLD
        self.canny_threshold1 = CANNY_THRESHOLD1
        self.canny_threshold2 = CANNY_THRESHOLD2
        # hough detection parameters
        # min/max circle radius
        self.target_min_radius = TARGET_MIN_RADIUS
        self.target_max_radius = TARGET_MAX_RADIUS
        # fault tolerance
        self.hough_param1 = 40
        self.hough_param2 = 60

    def get_fps(self):
        """get real fps from camera"""
        return self.cam.get(cv2.CAP_PROP_FPS)

    def quit(self):
        """close camera object"""
        # let's see if that helps with the defunct usb devices on abort
        self.cam.release()

    def read(self, crop_size=None):
        """read from camera, store in raw_frame"""
        ret, self.raw_frame = self.cam.read()
        if ret is False:
            return False

        if crop_size is not None:
            self.raw_frame = self.crop_frame(self.raw_frame, crop_size)

        self.raw_frame = cv2.cvtColor(self.raw_frame, cv2.COLOR_BGR2RGB)
        self.raw_frame = np.rot90(self.raw_frame, 3)
        self.raw_frame = np.flip(self.raw_frame, 1)
        return True

    def crop_frame(self, frame, crop_size):
        """crop frame centrally to a certain size"""
        height, width, depth = np.shape(frame)
        start_x = (width - crop_size[0]) // 2
        start_y = (height - crop_size[1]) // 2
        # crop the image (be aware of the x/y sequence)
        newframe = frame[
            start_y : (start_y + crop_size[1]), start_x : (start_x + crop_size[0])
        ]
        return newframe

    def check_and_update_target(self, pos, radius):
        """checks if the new positions are probable, and updates accordinly"""
        # currently - no check
        # ToDo: error correction, minimize wrong detections
        # (change in radius, sudden jumps in x/y)
        MAX_RAD_CHANGE = 20
        MAX_POS_CHANGE = 100
        if pos is None or radius is None or radius == 0:
            print("1")
            return False
        else:
            self.target_pos = pos
            # we should go with the radius that's mostly detected over the last second or so
            # and maybe if the radius is off, x/y will be off as well.
            self.target_radius = radius
            return True

    def get_target(self):
        """get detected target pos and size"""
        return self.target_pos, self.target_radius

    def detect_circles(self):
        """detect the target on ine grabbed image"""
        # ToDo: rename?
        # convert img to grayscale
        self.gray_frame = cv2.cvtColor(self.raw_frame, cv2.COLOR_RGB2GRAY)
        if self.blur:
            self.gray_frame = cv2.GaussianBlur(self.gray_frame, (3, 3), 0)

        # set threshold and return black/white image

        # possible to switch between contour detection and threshold detection
        # so the better suitable one can be used
        if self.detect_method == DETECTION_THRESHOLD:
            ret, self.thresh_frame = cv2.threshold(
                self.gray_frame,
                self.gray_threshold,
                255,
                cv2.THRESH_BINARY,
            )
            if self.blur:
                self.thresh_frame = cv2.GaussianBlur(self.thresh_frame, (3, 3), 0)
            self.thresh_frame = cv2.Canny(
                image=self.thresh_frame,
                threshold1=self.canny_threshold1,
                threshold2=self.canny_threshold2,
                L2gradient=True,
            )
        else:
            self.thresh_frame = cv2.Canny(
                image=self.gray_frame,
                threshold1=self.canny_threshold1,
                threshold2=self.canny_threshold2,
            )

        #  detect circles
        self.circles = cv2.HoughCircles(
            self.thresh_frame,
            cv2.HOUGH_GRADIENT,
            2,
            HOUGH_MIN_DISTANCE,
            param1=self.hough_param1,
            param2=self.hough_param2,
            minRadius=self.target_min_radius,
            maxRadius=self.target_max_radius,
        )

        # convert the circle parameters a, b and r to integers
        if self.circles is not None:
            self.circles = np.uint16(np.around(self.circles))
            y, x, r = self.circles[0][0]
            print(f"ORIGINAL circle details: ({x}, {y}), rad: {r}")
            return self.check_and_update_target([x, y], r)
        #            return True

        return False

    def detect_shot_triggered(self):
        """listen to the microphone and return True if a shot is thought to be fired"""
        if USE_MIC:
            return self.mic.shot_detected()
        return False


class CamMicrophone:
    """access camera microphone"""

    # ToDo: Everything, doesn't work well at all

    def __init__(self, mic_id=0, sample_rate=MIC_AUDIO_RATE):
        # this throws errors on STDERR.
        self.mic = pyaudio.PyAudio()
        self.get_device_names()
        print(mic_id, MIC_NUM_CHANNELS)
        self.audio_stream = self.mic.open(
            format=MIC_AUDIO_FORMAT,
            channels=MIC_NUM_CHANNELS,
            rate=sample_rate,
            input=True,
            frames_per_buffer=MIC_AUDIO_CHUNK,
            input_device_index=mic_id,
        )
        self.last_call = time.get_ticks()

    def get_device_names(self):
        """get audio device names"""
        # assuming host_api=0 as default (should be ALSA)
        host_api_id = 0

        num_devices = self.mic.get_device_count()
        print("Host Api info:")

        for i in range(num_devices):
            # if input is possible
            if (
                self.mic.get_device_info_by_host_api_device_index(host_api_id, i).get(
                    "maxInputChannels"
                )
            ) > 0:
                print(
                    i, self.mic.get_device_info_by_host_api_device_index(host_api_id, i)
                )

    # https://stackoverflow.com/questions/36413567/pyaudio-convert-stream-read-into-int-to-get-amplitude
    def get_rms(self, block):
        """getr root mean square of the amplitude for all given block"""

        # todo: reset history regularly
        count = len(block) // 2
        shorts = struct.unpack("%dh" % (count), block)
        sum_squares = 0.0
        for sample in shorts:
            n = sample * MIC_SHORT_NORMALIZE
            sum_squares += n * n

        rms = math.sqrt(sum_squares / count)

        return rms

    def shot_detected(self):
        """returns true if the microphone detects a noise over given threshold since last call"""
        # measure time since last call
        ms_since_last_call = time.get_ticks() - self.last_call

        # read all frames since last call
        achunk = self.audio_stream.read(
            int(MIC_AUDIO_RATE * ms_since_last_call / 1000),
            exception_on_overflow=False,
        )
        # start timer immediatelyy after getting audio stream, so we don't miss any samples
        self.last_call = time.get_ticks()

        # get mic threshold
        rms = self.get_rms(achunk)
        if rms > MIC_TRIGGER_VOLUME_THRESHOLD:
            print(rms)
            return True

        return False
