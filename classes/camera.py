# standard imports
import os
import numpy as np
import struct
import math
import subprocess
import re

# third party imports
# for image recognition
import cv2
from timeit import default_timer as timer


# for audio shot detection
import pyaudio
from . import camera_frame


GRAY_THRESHOLD = 150
CANNY_THRESHOLD1 = 50
CANNY_THRESHOLD2 = 100

HOUGH_MIN_DISTANCE = 500

TARGET_MIN_RADIUS = 30
TARGET_MAX_RADIUS = 60

TARGET_CIRCLE_WIDTH = 4

DETECTION_THRESHOLD = 0
DETECTION_EDGE = 1

USE_MIC = True
MIC_AUDIO_RATE = 48000
MIC_AUDIO_CHUNK = 1024
MIC_AUDIO_FORMAT = pyaudio.paInt16
MIC_NUM_CHANNELS = 1
MIC_SHORT_NORMALIZE = 1.0 / 32768.0
# auf stand 11 ca 0.70 - 0.79. Pistole auf Stand 3 wird nicht gehoert
# MIC_TRIGGER_VOLUME_THRESHOLD = 0.65
# less for triggering with a finger snap
MIC_TRIGGER_VOLUME_THRESHOLD = 0.15

VIDEO_BACKEND = cv2.CAP_V4L2
# VIDEO_BACKEND = cv2.CAP_FFMPEG

camconfig = {
    "default": {
        "name": "default",
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "zoom": 1,
        "codec": "MJPG",
        "mic_id": 0,
        "mic_sample_rate": 48000,
        "nickname": None,
        "bgr2rgb": True,
        "num_rot90": 1,
        "flip_horizontal": False,
        "flip_vertical": False,
        "crop_width": 0,
        "crop_height": 0,
    },
    "HD Pro Webcam C920": {
        "name": "HD Pro Webcam C920",
        "mic_id": 5,
        "mic_sample_rate": 32000,
        "num_rot90": 0,
        "crop_width": 1080,
        "crop_height": 1080,
    },
    "UVC Camera": {
        "name": "UVC Camera",
        "nickname": "OSST Cam",
        "mic_id": 5,
        "mic_sample_rate": 48000,
        "num_rot90": 0,
    },
    "Integrated_Webcam_HD: Integrate": {
        "name": "Integrated_Webcam_HD: Integrate",
        "nickname": "Laptop Internal",
        "mic_id": 5,
        "mic_sample_rate": 44100,
        "num_rot90": 0,
    },
}


class CamConfig:
    name = None
    nickname = None
    width = None
    height = None
    zoom = None
    fps = None
    codec = None
    mic_id = None
    mic_sample_rate = None
    crop_width = None
    crop_height = None

    def __init__(self):
        self.camconfig = camconfig
        self._load_default_config()

    def _load_named_config(self, config_name):
        if config_name not in self.camconfig.keys():
            return False
        cfg = self.camconfig[config_name]

        for key in self.camconfig["default"].keys():
            if key in cfg:
                self.__dict__[key] = cfg[key]

    def _load_default_config(self):
        return self._load_named_config("default")

    def load_config(self, cam_name, force=False):
        # if name didn't change, all good
        if cam_name == self.name and not force:
            return True

        # if name can't be found, all bad
        if cam_name not in self.camconfig.keys():
            return False

        # first, load the default config, to reset to a baseline
        if self._load_default_config() == False:
            return False

        return self._load_named_config(cam_name)


# TODO: get video device by name ("v4l2-ctl --list-devices")
class Camera:
    """handles USB camera video capture, object recognition and microphone"""

    def __init__(self, cam_name="default", cam_id=0):
        self.config = CamConfig()

        if cam_name != "default":
            self.config._load_named_config(cam_name)

        # microphone
        if USE_MIC:
            self.mic = CamMicrophone(self.config.mic_id, self.config.mic_sample_rate)
            print(self.mic.get_device_names())
        # raw image taken from cam
        self.raw_frame = None
        # grayscale version
        self.gray_frame = None
        # ToDo: change name
        # threshhold frame (also used for edge detection)
        self.thresh_frame = None
        self.edge_frame = None
        # detected hough circles
        self.circles = None

        self.width = self.config.width
        self.height = self.config.height

        #  --- InitVideoCapture
        self.cam = cv2.VideoCapture(cam_id, VIDEO_BACKEND)
        if self.width is not None and self.height is not None:
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cam.set(cv2.CAP_PROP_ZOOM, self.config.zoom)
        # set mode to MJPG for higher fpsG
        # workaround for the small Logi webcam
        self.cam.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*self.config.codec))
        self.cam.set(cv2.CAP_PROP_FPS, self.config.fps)
        # focus distance
        self.cam.set(cv2.CAP_PROP_FOCUS, 0)

        # radius and pos are None until detected
        self.target_pos = None
        self.target_radius = None

        # detection method
        self.detect_method = DETECTION_THRESHOLD
        # blur grey image (for both methods)
        #        self.blur = True
        self.blur_radius = 3
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

    def read(self):
        """read from camera, store in raw_frame"""
        ret, raw_frame = self.cam.read()
        if ret is False:
            return False

        # read from Cam and convert color to rgb
        self.raw_frame = camera_frame.CameraFrame(raw_frame, bgr2rgb=True)

        if self.config.crop_height > 0:
            self.raw_frame.center_crop(
                (self.config.crop_height, self.config.crop_width)
            )

        # flip and turn image as per camera config
        self.raw_frame.rotate_90deg(self.config.num_rot90)
        if self.config.flip_horizontal:
            self.raw_frame.flip_horizontal()
        if self.config.flip_vertical:
            self.raw_frame.flip_vertical()

        return True

    def get_frame_size(self):
        if self.raw_frame is None:
            return None
        return (self.raw_frame.get_width(), self.raw_frame.get_height())

    def get_crop_size(self):
        w = self.config.width
        h = self.config.height
        if self.config.crop_height > 0:
            h = self.config.crop_height
        if self.config.crop_width > 0:
            w = self.config.crop_width
        return [w, h]

    def check_and_update_target(self, pos, radius):
        """checks if the new positions are probable, and updates accordinly"""
        if self.target_pos is not None:
            xdist = abs(int(self.target_pos[0]) - int(pos[0]))
            ydist = abs(int(self.target_pos[1]) - int(pos[1]))
            if xdist + ydist > 400:
                return False
        #            print(f"target distance: {xdist} / {ydist} ({pos})")
        # currently - no check
        # ToDo: error correction, minimize wrong detections
        # (change in radius, sudden jumps in x/y)
        MAX_RAD_CHANGE = 20
        MAX_POS_CHANGE = 100
        if pos is None or radius is None or radius == 0:
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
        self.gray_frame = self.raw_frame.get_grayscale()
        self.gray_frame.blur(self.blur_radius)
        # set threshold and return black/white image

        # possible to switch between contour detection and threshold detection
        # so the better suitable one can be used
        if self.detect_method == DETECTION_THRESHOLD:
            ret, thresh_frame = cv2.threshold(
                self.gray_frame.get_frame(),
                self.gray_threshold,
                255,
                cv2.THRESH_BINARY,
            )
            self.thresh_frame = camera_frame.CameraFrame(thresh_frame)
            self.thresh_frame.blur(self.blur_radius)

            edge_frame = cv2.Canny(
                image=self.thresh_frame.get_frame(),
                threshold1=self.canny_threshold1,
                threshold2=self.canny_threshold2,
                L2gradient=True,
            )
            self.edge_frame = camera_frame.CameraFrame(edge_frame)
        else:
            edge_frame = cv2.Canny(
                image=self.gray_frame.get_frame(),
                threshold1=self.canny_threshold1,
                threshold2=self.canny_threshold2,
            )
            self.edge_frame = camera_frame.CameraFrame(edge_frame)

        #  detect circles
        self.circles = cv2.HoughCircles(
            self.edge_frame.get_frame(),
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
            x, y, r = self.circles[0][0]
            #            print(f"ORIGINAL circle details: ({x}, {y}), rad: {r}")
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
        self.last_call = timer()

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
        ms_since_last_call = timer() - self.last_call

        # read all frames since last call
        achunk = self.audio_stream.read(
            int(MIC_AUDIO_RATE * ms_since_last_call / 1000),
            exception_on_overflow=False,
        )
        # start timer immediatelyy after getting audio stream, so we don't miss any samples
        self.last_call = timer()

        # get mic threshold
        rms = self.get_rms(achunk)
        if rms > MIC_TRIGGER_VOLUME_THRESHOLD:
            print(rms)
            return True

        return False


def get_devices():
    try:
        ret = subprocess.run(["v4l2-ctl", "--list-devices"], capture_output=True)
        print(ret.stdout)
    except FileNotFoundError:
        print("Video For linux doesn't seem installed!")
        return False

    # list of lists with caminfo
    caminfo = {}
    raw_caminfo = [
        out.split("\n") for out in ret.stdout.decode("utf-8").split("\n\n") if out != ""
    ]
    for cam in raw_caminfo:
        camname = cam[0].split(" (")[0]
        device_name = cam[1].strip().split("\\")[-1]
        camid = re.search(r"\d+$", device_name)
        cam_device_id = int(camid.group(0))
        caminfo[cam_device_id] = camname

    #    print(caminfo)
    return caminfo
