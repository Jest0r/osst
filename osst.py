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
from classes import tracker
from classes.lines import vec2d

WEBCAM_INTERNAL = 0
WEBCAM_EXTERNAL = 4
WEBCAM_OSST_FIRST = 4
WEBCAM_OSST_SECOND = 6


# script version
VERSION = _version.__version__


# --------- CONFIGURATION ---------

# ------- Exit handling
EXIT_SUCCESS = 0
EXIT_NO_CAMERA = 1
EXIT_MSG = [None, "Cannot read from Camera. Camera ID ok?"]

# -- webcam stuff

WEBCAM_CROP_WIDTH = 700
WEBCAM_CROP_HEIGHT = 700

WEBCAM_SETTINGS_INTERNAL = [1920, 1680, 30, 1, "MJPG", 0, 32000]
WEBCAM_SETTINGS_EXTERNAL = [1920, 1680, 30, 1, "MJPG", 5, 32000]
WEBCAM_SETTINGS_OSST_DEV = [1280, 960, 30, 2, "MJPG", 8, 48000]

# SETTINGS - To change here
WEBCAM_ID = WEBCAM_EXTERNAL
WEBCAM_SETTINGS = WEBCAM_SETTINGS_EXTERNAL

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
# using a string to legacy reasons
# ToDo: change
TARGET_TYPE = "lg"  # lg / lp

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

        # set up target image
        win_width, win_height = pygame.display.get_surface().get_size()
        self.target = Target(win_height, TARGET_TYPE)
        self.target_center = None

        # draw target image
        self.target_frame = self.target.draw()

        self.keep_running = True
        self.pause_capture = False

        self.clock = pygame.time.Clock()
        self.starttime = datetime.now()

        self.crop = True
        self.fps = 0
        self.circles_per_second = 0
        self.fails_per_second = 0

        # 60 seconds times 30fps = 1800 values
        actual_fps = self.camera.get_fps()
        self.tracker = tracker.Tracker(HISTORY_SECONDS, int(actual_fps))

        # setting target scale for the  tracker
        self.tracker.set_target_scale(self.target.get_black_radius() / 2)

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
            1,
        )
        pygame.draw.line(
            frame,
            line_color,
            (x, y - line_len),
            (x, y + line_len),
            1,
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
        win_width, win_height = pygame.display.get_surface().get_size()

        # ---- MAIN TARGET WINDOW
        # target as background
        self.screen.blit(self.target_frame, (0, 0))

        # ---- CAM WINDOWS
        rsurf = self.get_scaled_surface(self.camera.raw_frame, (400, 400))
        tsurf = self.get_scaled_surface(self.camera.thresh_frame, (400, 400))
        gsurf = self.get_scaled_surface(
            cv2.cvtColor(self.camera.gray_frame, cv2.COLOR_GRAY2RGB), (400, 400)
        )

        # display circles
        pos, rad = self.camera.get_target()

        if pos is not None:
            x = int(pos[0] * 400 / WEBCAM_CROP_WIDTH)
            y = int(pos[1] * 400 / WEBCAM_CROP_WIDTH)
            rad = int(rad * 400 / WEBCAM_CROP_WIDTH)

            self.tracker.set_source_scale(rad)

            # circle color
            color = (255, 0, 0)
            if self.circles_per_second > 0:
                if self.fails_per_second / self.circles_per_second < 0.2:
                    # green
                    color = (0, 255, 0)
                elif self.fails_per_second / self.circles_per_second < 0.5:
                    # yelos
                    color = (255, 255, 0)

            pygame.draw.circle(tsurf, color, (x, y), rad, 2)

        # display center
        self.draw_center(tsurf, 400 / WEBCAM_CROP_WIDTH)

        # display camera windows
        self.screen.blit(
            gsurf,
            (1000, 0),
        )

        # only display the B/W frame if it actually exists
        if self.camera.thresh_frame is not None:
            self.screen.blit(
                tsurf,
                (1000, 400),
            )

        maxlen = win_height // 8

        # --- movements
        allpos = self.tracker.get_all_positions(scaled=True)
        if len(allpos) > 5:
            l = lines.Lines(allpos)
            # origin
            l.set_origin(vec2d(500, 500))
            # color
            l.set_line_len_color_gradient((0, 255, 0), (255, 0, 0), maxlen)

            # draw
            l.draw_lines(self.screen, thickness=3)
            # l.draw_curve(self.screen, thickness=3)

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
        pygame.transform.scale_by(min_max_target_surf, 400 / WEBCAM_CROP_WIDTH)
        self.screen.blit(min_max_target_surf, (1100, 900))

        # resolution
        if self.tracker.get_resolution() is not None:
            l = int(self.tracker.get_resolution() * self.target.scale)
            resolution_surf = pygame.Surface((l, l))
            resolution_surf.fill((0, 0, 200))
            self.screen.blit(resolution_surf, (1400, 900))

        # fps

        DEBUG_WINDOW_MIN_X = 1000
        DEBUG_WINDOW_MIN_Y = 800

        fps_surf = self.get_text_box(
            f"{round(self.fps)} fps | {self.fails_per_second}/{self.circles_per_second} det ko/ok  | {self.camera.hough_param1} H1 | gray_thres {self.camera.gray_threshold}\n resolution: {int(self.tracker.get_resolution())} mm/100 /pixel",
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
                elif event.key == pygame.K_KP7:
                    if self.camera.gray_threshold > 0:
                        self.camera.gray_threshold -= 5
                    if self.camera.canny_threshold1 > 0:
                        self.camera.canny_threshold1 -= 5
                elif event.key == pygame.K_KP9:
                    if self.camera.gray_threshold < 255:
                        self.camera.gray_threshold += 5
                    if self.camera.canny_threshold1 < 250:
                        self.camera.canny_threshold1 += 5
                # target size
                elif event.key == pygame.K_KP1:
                    if self.camera.target_min_radius > 5:
                        self.camera.target_min_radius -= 2
                        self.camera.target_max_radius -= 2
                elif event.key == pygame.K_KP3:
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
                # blur pre-processing
                elif event.key == pygame.K_b:
                    self.camera.blur = not self.camera.blur
                # detection method
                elif event.key == pygame.K_m:
                    self.camera.detect_method = 1 - self.camera.detect_method
            # mouse events
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # set offset to mouse pos
                pos = pygame.mouse.get_pos()
                offset_x = (pos[0] - 1000) * WEBCAM_CROP_WIDTH / 400
                offset_y = (pos[1] - 400) * WEBCAM_CROP_HEIGHT / 400
                self.target_center = [offset_x, offset_y]

                # set tracker offset if there was a shot already
                if self.camera.target_pos is not None:
                    new_offset = [
                        offset_x - self.camera.target_pos[0],
                        offset_y - self.camera.target_pos[1],
                    ]
                    print(f"new offset: {new_offset}")
                    self.tracker.offset = new_offset

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
                print("Shot detected!")

            # read cameras
            if not self.pause_capture:
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
                #                print(self.camera.target_pos)
                if self.target_center is not None:
                    x = self.target_center[0] - self.camera.target_pos[0]
                    y = self.target_center[1] - self.camera.target_pos[1]
                    #                    print(self.target_center, self.camera.target_pos, [x, y])
                    self.tracker.add_position([x, y])

                #                    print(self.tracker.get_current_position())
                detected_counter += 1
            else:
                fail_counter += 1

            # --- maintenance
            # draw
            self.draw()

            # update fps every full second
            self.clock.tick()
            if (datetime.now() - self.starttime).total_seconds() >= 1:
                self.starttime = datetime.now()
                self.fps = self.clock.get_fps()
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
