#!/usr/bin/env python3
# open sport shooting (target) tracker

# coordinates
# 0-> X
# |
# V  Y

# ------- IMPORTS -------
# standard library imports
from datetime import datetime
from signal import signal, SIGINT, SIGABRT, SIGTERM
import argparse
import numpy as np
import os
import sys
import math

# third party imports
import cv2
import pygame

# local imports
import _version
from classes.target import *
from classes import camera

# from classes import tracker
from classes.lines import vec2d
from classes.shots import Shot, Shots
from classes import disag

WEBCAM_INTERNAL = 0
WEBCAM_EXTERNAL = 4
WEBCAM_OSST_FIRST = 4
WEBCAM_OSST_SECOND = 6

USE_DISAG = True


# script version
VERSION = _version.__version__


# --------- CONFIGURATION ---------

# ------- Exit handling
EXIT_SUCCESS = 0
EXIT_NO_CAMERA = 1
EXIT_MSG = [None, "Cannot read from Camera. Camera ID ok?"]

# -- webcam stuff

WEBCAM_CROP_WIDTH = 1000
WEBCAM_CROP_HEIGHT = 700
SIDEPANEL_WIDTH = 400

WEBCAM_SETTINGS_INTERNAL = [1920, 1680, 30, 1, "MJPG", 0, 32000]
WEBCAM_SETTINGS_EXTERNAL = [1920, 1680, 30, 1, "MJPG", 5, 32000]
WEBCAM_SETTINGS_OSST_DEV = [1280, 960, 30, 2, "MJPG", 5, 48000]
# WEBCAM_SETTINGS_OSST_DEV = [960, 720, 30, 2, "MJPG", 8, 48000]

# SETTINGS - To change here
WEBCAM_ID = 4
WEBCAM_SETTINGS = WEBCAM_SETTINGS_OSST_DEV


# webcam settings indexes
CAM_SETTINGS_WIDTH = 0
CAM_SETTINGS_HEIGHT = 1
CAM_SETTINGS_FPS = 2
CAM_SETTINGS_ZOOM = 3
CAM_SETTINGS_CODEC = 4
CAM_SETTINGS_MIC_ID = 5
CAM_SETTINGS_MIC_SAMPLE_RATE = 6

# --- cv2 stuff
CV2_VIDEO_BACKEND = cv2.CAP_V4L2

# --- target
TARGET_TYPE = DISKTYPE_LG

# radius of the black area of the target (in mm/100)
# ToDo: get that from target
BLACK_RAD_LP = 2975
BLACK_RAD_LG = 1275

# --- behaviour
HISTORY_SECONDS = 10

# initial window dimensions
WINDOW_DIMENSIONS = (1640, 1000)


class Osst:
    """
    Main object and busiess logic
    """

    def __init__(self):
        # graceful exit when killed
        signal(SIGTERM, self._catch_signal)
        signal(SIGINT, self._catch_signal)
        signal(SIGABRT, self._catch_signal)

        # webcam settings: width/height/fps/zoom
        # ToDo: Find a better way to do this
        # self._cam_settings = [
        #     [1920, 1680, 30, 1, "MJPG", 0],
        #     None,
        #     None,
        #     None,
        #     [1920, 1680, 30, 1, "MJPG", 2],
        #     None,
        #     [1280, 960, 30, 2, "MJPG", 8],
        # ]

        self.exit_reason = EXIT_SUCCESS

        # init pygame and open the window
        pygame.init()
        pygame.display.set_caption("Open Sport Shooting Tracker")
        self.screen = pygame.display.set_mode(WINDOW_DIMENSIONS)

        # set up camera
        # ToDo: should that go into the Camera object instead?

        self.camera = camera.Camera(
            WEBCAM_ID,
            cv2.CAP_V4L2,
            WEBCAM_SETTINGS[CAM_SETTINGS_WIDTH],
            WEBCAM_SETTINGS[CAM_SETTINGS_HEIGHT],
            WEBCAM_SETTINGS[CAM_SETTINGS_ZOOM],
            WEBCAM_SETTINGS[CAM_SETTINGS_FPS],
            WEBCAM_SETTINGS[CAM_SETTINGS_CODEC],
            WEBCAM_SETTINGS[CAM_SETTINGS_MIC_ID],
            WEBCAM_SETTINGS[CAM_SETTINGS_MIC_SAMPLE_RATE],
        )

        # start disag UDP broadcast listener
        self.disag_server = disag.DisagServer()
        self.disag_server.listen()

        # TODO: change layout to allow a Shot to be fed by json,
        #       instead have to go the roundtrip through Shots()
#        self.shots = Shots()

        self.keep_running = True
        self.pause_capture = False

        self.starttime = datetime.now()

        self.crop = True
        self.fps = 0
        self.framecount = 0
        self.circles_per_second = 0
        self.fails_per_second = 0

        # 60 seconds times 30fps = 1800 values
        actual_fps = self.camera.get_fps()

        # set up the target
        win_width, win_height = pygame.display.get_surface().get_size()
        self.target = Target(win_height, TARGET_TYPE, HISTORY_SECONDS, int(actual_fps))
        self.target_center = None

    def _catch_signal(self, sig, frame):
        """
        makes sure the script exits gracefully when killed
        """
        if sig == SIGINT:
            self.quit(0)
        elif sig == SIGTERM:
            self.quit(0)
        else:
            self.quit(0)

    def quit(self, retval=0):
        """graceful exit"""
        self.disag_server.end()
        self.camera.quit()
        pygame.quit()
        sys.exit(0)

    def get_text_box(self, mystring, font_size=20, color=(255, 0, 255)):
        """return text"""
        font = pygame.font.Font("freesansbold.ttf", font_size)
        text_surf = font.render(mystring, True, color)
        return text_surf

    def get_scaled_surface(self, frame, dimensions):
        """scale and return surface"""
        pygame_frame = pygame.surfarray.make_surface(frame)
        return pygame.transform.scale(pygame_frame, dimensions)

    def draw_center(self, frame, scale=1):
        """display the logical center point of the camera"""
        if self.target_center is None:
            return
        x, y = self.target_center
        x *= scale
        y *= scale

        line_len = 9
        line_color = pygame.Color(0, 255, 255)
        line_thickness = 1

        pygame.draw.line(
            frame,
            line_color,
            (x - line_len, y),
            (x + line_len, y),
            line_thickness,
        )
        pygame.draw.line(
            frame,
            line_color,
            (x, y - line_len),
            (x, y + line_len),
            line_thickness,
        )
        return frame

    def draw(self):
        """Draw routine, executed on every frame"""
        #
        # +----...----+---...---+
        # |    ...    | camwin1 |
        # |   main    |         |
        # |  target   +---...---+
        # |  window   | camwin2 |
        # |    ...    |         |
        # |    ...    +---...---+
        # |    ...    | dbg info|
        # +----...----+---...---+

        # get window size
        w, h = self.screen.get_size()

        # new_* is the size of the debug camera views - needs renaming
        new_width = w - 1000
        aspect = WEBCAM_CROP_WIDTH / WEBCAM_CROP_HEIGHT
        new_height = int(new_width / aspect)

        scale = new_width / WEBCAM_CROP_WIDTH  # < 0!

        # ---- CAM WINDOWS
        rsurf = self.get_scaled_surface(self.camera.raw_frame, (new_width, new_height))
        tsurf = self.get_scaled_surface(
            self.camera.thresh_frame, (new_width, new_height)
        )
        gsurf = self.get_scaled_surface(
            cv2.cvtColor(self.camera.gray_frame, cv2.COLOR_GRAY2RGB),
            (new_width, new_height),
        )

        # display circles
        pos, rad = self.camera.get_target()
        # print(f"rad from get_target(): {rad}")

        if pos is not None:
            # adjust source scale from camera target radius
            self.target.set_tracker_source_scale(rad)

            # scaled pos and radii for display
            scaled_x = int(pos[0] * scale)
            scaled_y = int(pos[1] * scale)
            scaled_rad = int(rad * scale)

            min_rad = int(self.camera.target_min_radius * scale)
            max_rad = int(self.camera.target_max_radius * scale)

            # circle color
            center_color = (255, 0, 0)
            min_rad_color = (0, 150, 0)
            max_rad_color = (0, 150, 0)
            if self.circles_per_second > 0:
                if self.fails_per_second / self.circles_per_second < 0.2:
                    # green
                    center_color = (0, 255, 0)
                elif self.fails_per_second / self.circles_per_second < 0.5:
                    # yellow
                    center_color = (255, 255, 0)

            # draw min and max radius
            pygame.draw.circle(tsurf, min_rad_color, (scaled_x, scaled_y), min_rad, 1)
            pygame.draw.circle(tsurf, max_rad_color, (scaled_x, scaled_y), max_rad, 1)
            # draw actual circle
            pygame.draw.circle(tsurf, center_color, (scaled_x, scaled_y), scaled_rad, 2)

        # display center
        self.draw_center(tsurf, scale)

        # display camera windows
        self.screen.blit(
            gsurf,
            (1000, 0),
        )

        # only display the B/W frame if it actually exists
        if self.camera.thresh_frame is not None:
            self.screen.blit(
                tsurf,
                (1000, new_height),
            )

        # ---- MAIN TARGET WINDOW
        self.target_frame = self.target.draw(draw_shots=True)
        self.screen.blit(
            self.target_frame,
            (0, 0),
        )

        # ---- DEBUG WINDOW
        # clean background winddow - quick and expensive hack, surface should be done cheaper and more efficient
        self.screen.blit(pygame.Surface((640, 200)), (1000, 800))

        # target sizes in debug area
        min_max_target_surf = pygame.Surface(
            (self.camera.target_max_radius * 2, self.camera.target_max_radius * 2)
        )
        pygame.draw.circle(
            min_max_target_surf,
            (255, 0, 0),
            (self.camera.target_max_radius, self.camera.target_max_radius),
            self.camera.target_max_radius,
        )
        pygame.draw.circle(
            min_max_target_surf,
            (0, 0, 0),
            (self.camera.target_max_radius, self.camera.target_max_radius),
            self.camera.target_min_radius,
        )
        pygame.transform.scale_by(
            min_max_target_surf,
            new_width / WEBCAM_CROP_WIDTH,
        )
        self.screen.blit(min_max_target_surf, (1100, 900))

        # resolution
        if self.target.get_tracker_resolution() is not None:
            l = int(self.target.get_tracker_resolution() * self.target.scale)
            resolution_surf = pygame.Surface((l, l))
            resolution_surf.fill((0, 0, 200))
            self.screen.blit(resolution_surf, (1400, 900))

        # fps
        DEBUG_WINDOW_MIN_X = 1000
        DEBUG_WINDOW_MIN_Y = 800

        fps_surf = self.get_text_box(
            f"{round(self.fps)} fps | {self.fails_per_second}/{self.circles_per_second} det ko/ok | {self.target_center} |  resolution: {int(self.target.get_tracker_resolution())} mm/100 /pixel",
            15,
        )
        self.screen.blit(fps_surf, (DEBUG_WINDOW_MIN_X + 10, DEBUG_WINDOW_MIN_Y + 30))

        pygame.display.update()

    def prep_exit(self, retval=0):
        """exit mainloop with certain return value and message"""
        if retval > 0:
            print(f"ERROR: {EXIT_MSG[retval]}")
        self.exit_reason = retval
        self.keep_running = False

    def handle_events(self):
        """event handler"""
        for event in pygame.event.get():
            # key events
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    self.keep_running = False
                # gray / canny threshold
                elif event.key == pygame.K_u:
                    if self.camera.gray_threshold > 0:
                        self.camera.gray_threshold -= 5
                    if self.camera.canny_threshold1 > 0:
                        self.camera.canny_threshold1 -= 5
                elif event.key == pygame.K_o:
                    if self.camera.gray_threshold < 255:
                        self.camera.gray_threshold += 5
                    if self.camera.canny_threshold1 < 250:
                        self.camera.canny_threshold1 += 5
                # target size
                elif event.key == pygame.K_j:
                    if self.camera.target_min_radius > 5:
                        self.camera.target_min_radius -= 2
                        self.camera.target_max_radius -= 2
                elif event.key == pygame.K_l:
                    if self.camera.target_max_radius < 100:
                        self.camera.target_min_radius += 2
                        self.camera.target_max_radius += 2
                # hough param 1
                elif event.key == pygame.K_KP4:
                    if self.camera.hough_param1 > 1:
                        self.camera.hough_param1 -= 2
                elif event.key == pygame.K_KP6:
                    if self.camera.hough_param1 < 100:
                        self.camera.hough_param1 += 2
                # reset camera
                elif event.key == pygame.K_SPACE:
                    # self.tracker.reset()
                    self.pause_capture = not self.pause_capture
                elif event.key == pygame.K_r:
                    self.target.reset_trail()
                # blur pre-processing
                elif event.key == pygame.K_b:
                    self.camera.blur = not self.camera.blur
                # detection method
                elif event.key == pygame.K_m:
                    self.camera.detect_method = 1 - self.camera.detect_method
            # mouse events
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # only act on main button presses so far, else, continue
                if not pygame.mouse.get_pressed()[0]:
                    continue
                # TODO: This is a nightmare!
                # set offset to mouse pos
                pos = pygame.mouse.get_pos()

                win_width, win_height = pygame.display.get_surface().get_size()
                width = win_width - self.target.width
                scale = width / WEBCAM_CROP_WIDTH

                aspect_ratio = WEBCAM_CROP_WIDTH / WEBCAM_CROP_HEIGHT
                scaled_offset_x = self.target.width  # / scale
                scaled_offset_y = width / aspect_ratio

                # scaled back
                self.target_center = [
                    (pos[0] - scaled_offset_x) / scale,
                    (pos[1] - scaled_offset_y) / scale,
                ]

                # set tracker offset if there was a shot already
                if self.camera.target_pos is not None:
                    print(
                        f"Mouse pos: {pos} -  win offset: {scaled_offset_x}, {scaled_offset_y} - Target center: {self.target_center}"
                    )

            elif event.type == pygame.MOUSEWHEEL:
                if event.y > 0:
                    self.target.scale_out()
                elif event.y < 0:
                    self.target.scale_in()
            # window closing
            elif event.type == pygame.QUIT:
                self.keep_running = False

    def mainloop(self):
        # circles detected?
        detected_counter = 0
        fail_counter = 0

        while self.keep_running:
            # --- event handling
            self.handle_events()

            # --- main business logic
            # ---- detect a triggered shot.

            if self.camera.detect_shot_triggered():
                print("Shot detected by camera!")
            if USE_DISAG and self.disag_server.data_received():
                d = self.disag_server.get_data()
                print("Shot broadcast from DISAG Server!")
                shot = Shot(d, json=True)
                self.target.add_shot(shot)
                # TODO: switch?
                x,y = shot.pos()
                #TODO: Center is currently pixel in image, so it can't be easily set by DISAG
#                self.target_center = [x,y]

                print(shot.pos())
#                res = self.shots.add_json_shot(d)
#                print(res, self.shots.shots)
#                self.target.add_shot(self.shots.shots[-1])


            # read cameras
            if self.pause_capture is False:
                if self.crop:
                    cam_read_success = self.camera.read(
                        (WEBCAM_CROP_WIDTH, WEBCAM_CROP_HEIGHT)
                    )
                else:
                    cam_read_success = self.camera.read()

                if not cam_read_success:
                    self.prep_exit(EXIT_NO_CAMERA)
                    break

                # detect circles
                circle_found = self.camera.detect_circles()
                if circle_found:
                    if self.target_center is not None:
                        x = self.target_center[0] - self.camera.target_pos[0]
                        y = self.target_center[1] - self.camera.target_pos[1]
                        # print(
                        #     f"Target center: {self.target_center}, current pos: {self.camera.target_pos}, relative: [{x}, {y}]"
                        # )
                        self.target.add_position([x, y])
                    detected_counter += 1
                else:
                    fail_counter += 1

            # --- maintenance
            self.draw()

            # update fps every full second
            self.framecount += 1
            if (datetime.now() - self.starttime).total_seconds() >= 1:
                self.starttime = datetime.now()
                self.fps = self.framecount
                self.framecount = 0
                self.circles_per_second = detected_counter
                detected_counter = 0
                self.fails_per_second = fail_counter
                fail_counter = 0

        self.quit()


def parse_args():
    """parse command line arguments"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""Open Sports Shooting Tracker""",
    )

    parser.add_argument(
        "--virtualenv",
        action="store",
        help="specify a custom different virtual environment.",
        default="./venv",
    )

    parser.add_argument(
        "-V",
        "--version",
        action="store_true",
    )

    args = parser.parse_args()

    # print version and exit
    if args.version:
        print(f"version {VERSION}")
        sys.exit(0)

    return args


def main():
    # get cmd line args
    args = parse_args()
    if args.version:
        print(f"OSST version {VERSION}")

    # init main object
    osst = Osst()
    osst.mainloop()

    # mainloop should exit gracefully


if __name__ == "__main__":
    main()
