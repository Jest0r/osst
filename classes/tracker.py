import numpy as np
from . import lines


#  source is X pixels radius
#  this corresponds to Y mm/1000
#  => resolution = Y/X (mm/100 / pixel)

X = 0
Y = 1


class Tracker:
    """pos should be recorded in mm/100"""

    def __init__(self, seconds, fps):
        self.num_elements = seconds * fps
        self.reset()

        self.target_scale = 1
        self.source_scale = 1
        self.pixel_to_pos = 1
        self.offset = [0, 0]

    def _pixel_to_pos(self, pixelpos):
        if self.target_scale is None or self.source_scale is None:
            return
        pos_x = (pixelpos[X] + self.offset[X]) * (self.target_scale / self.source_scale)
        pos_y = (pixelpos[Y] + self.offset[Y]) * (self.target_scale / self.source_scale)
        #        print(f"Pixelpos: {pixelpos} {[pos_x, pos_y]}, offset: {self.offset}")
        #return [pos_x, pos_y]
        return lines.vec2d(pos_x, pos_y)

    def reset(self):
        """reset to a fresh start"""
#        self.pos = [[0, 0] for i in range(self.num_elements)]
        self.pos = [lines.vec2d(0,0) for i in range(self.num_elements)]
        self.pos_index = -1
        self.num_recorded = 0

    def add_position(self, pixelpos):
        """in pixel, from the camera"""

        # advance index
        # convert pixelpos to real pos and add it
        self.pos_index = (self.pos_index + 1) % len(self.pos)
        self.pos[self.pos_index] = self._pixel_to_pos(pixelpos)
        # increase counter, until all pos are filled
        # (we stop there to circumvent overflow on long running sesions)
        if self.num_recorded < len(self.pos):
            self.num_recorded += 1

    #        print(f"Index: {self.pos_index} - recorded: {self.num_recorded}")

    def get_all_positions(self, scaled=False):
        #        print(self.num_recorded)

        allpos = (self.pos[self.pos_index :: -1] + self.pos[: self.pos_index : -1])[
            : self.num_recorded
        ]

        # if not scaled:
        #     allpos = [
        #         [x[0] / self.target_scale, x[1] / self.target_scale] for x in allpos
        #     ]

        return allpos

    def get_current_position(self):
        return self.pos[self.pos_index]

    def set_target_scale(self, scale):
        """ "Spiegel" size in mm/1000"""
        self.target_scale = scale

    def set_source_scale(self, scale):
        """radius of "Spiegel" in camera - in pixels"""
        self.source_scale = scale

    def set_offset_from_source(self, pos):
        """offset pos of absolute zero - in pixels"""
        self.offset = pos

    def get_resolution(self):
        return self.target_scale / self.source_scale
