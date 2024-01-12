import math

# from PIL import Image, ImageDraw
import pygame

from gi.repository import Gdk, GdkPixbuf, cairo

# import numpy
from . import lines
from . import tracker

TARGET_BGCOL = "#ffffff"
TARGET_FGCOL = "#000000"

SPEED = 1
PI = 3.14159265359

R = 0
G = 1
B = 2
A = 3

# X and Y of a shot are in mm/100

SHOT_COLOR = [
    pygame.Color("#0000FF60"),
    pygame.Color("#0077FF60"),
    pygame.Color("#00FFFF60"),
    pygame.Color("#00AA00a0"),
    pygame.Color("#00CC00a0"),
    pygame.Color("#00FF00a0"),
    pygame.Color("#44FF00A0"),
    pygame.Color("#CCFF00A0"),
    pygame.Color("#FFFF00FF"),
    pygame.Color("#FFCC00FF"),
    pygame.Color("#FF0000FF"),
]

BLACK = pygame.Color("#000000ff")
WHITE = pygame.Color("#ffffffff")

# print(SHOT_COLOR[0])

# all sizes are in 1/100 mm

LG_RADIUS = [25, 275, 525, 775, 1025, 1275, 1525, 1775, 2025, 2275]
LG_BGCOL = [BLACK, BLACK, BLACK, BLACK, BLACK, BLACK, WHITE, WHITE, WHITE, WHITE]
LG_FGCOL = [WHITE, WHITE, WHITE, WHITE, WHITE, BLACK, BLACK, BLACK, BLACK, BLACK]
LG_TEXT = ["", "", "8", "7", "6", "5", "4", "3", "2", "1"]
LG_FONT_SIZE = 80
LG_SCALE = 0.15

LP_RADIUS = [250, 575, 1375, 2175, 2975, 3775, 4575, 5375, 6175, 6975, 7775]
LP_BGCOL = [BLACK, BLACK, BLACK, BLACK, BLACK, WHITE, WHITE, WHITE, WHITE, WHITE, WHITE]
LP_FGCOL = [WHITE, WHITE, WHITE, WHITE, BLACK, BLACK, BLACK, BLACK, BLACK, BLACK, BLACK]
LP_TEXT = ["", "", "9", "8", "7", "6", "5", "4", "3", "2", "1"]
LP_FONT_SIZE = 240
LP_SCALE = 0.05

LIGHTBOX_SIZE = 17000  # 17 cm

SHOT_RADIUS = 225  # 4.5mm caliber

DEFAULT_HISTORY_SECONDS = 10

DISKTYPE_LP = 0
DISKTYPE_LG = 1

LINESTYLE_LINES = 0
LINESTYLE_CURVE = 1

pygame.init()


class Target:
    def __init__(
        self,
        dimensions,
        disktype=DISKTYPE_LG,
        tracker_history_seconds=DEFAULT_HISTORY_SECONDS,
        tracker_fps=30,
    ):
        self.width = dimensions
        self.height = dimensions
        self.center = dimensions // 2

        self.shots = []

        self.max_scale = None
        self.scale = None
        self.radius = None
        self.fgcol = None
        self.bgcol = None
        self.text = None
        self.font_size = None

        self.set_disk_type(disktype)

        self.cairo_orig_offset_x = -LIGHTBOX_SIZE // 4
        self.cairo_orig_offset_y = -LIGHTBOX_SIZE // 4
        # self.cairo_offset_x = -LIGHTBOX_SIZE //4
        # self.cairo_offset_y = -LIGHTBOX_SIZE //4
        self.cairo_offset_x = 0
        self.cairo_offset_y = 0
        self.cairo_drag_start_x = 0
        self.cairo_drag_start_y = 0

        self.tracker = tracker.Tracker(tracker_history_seconds, tracker_fps)
        self.tracker.set_target_scale(self.get_black_radius())

        self.pixbuf = None

        self.line_style = LINESTYLE_LINES
        self.trail_fade = True

    def _draw_shot(self, c, x,y, color):
    
        c.move_to(x,y)
        c.set_source_rgb(0,1,1)
        r = SHOT_RADIUS 
        c.arc(x, y, r, 0, 2 * PI)
        c.stroke()


    #     # print(r)
    #     c = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    #     pygame.draw.circle(c, color, (r, r), r)
    #     pygame.draw.circle(c, (0, 0, 0), (r, r), r, width=1)
    #     self.surf.blit(
    #         c,
    #         (
    #             (x - SHOT_RADIUS) * self.scale + self.center,
    #             (y - SHOT_RADIUS) * self.scale + self.center,
    #         ),
    #     )

    def _draw_line(self, c, oldx, oldy, x, y, color, width):
#        print(f"line from {oldx}, {oldy} to {x}, {y}")
        c.move_to(oldx, oldy)
        c.set_source_rgba(1,1,0,1)
        c.line_to(x,y)
        c.stroke()

    #     pygame.draw.line(
    #         self.surf,
    #         color,
    #         ((oldx * self.scale) + self.center, (oldy * self.scale) + self.center),
    #         ((x * self.scale) + self.center, (y * self.scale) + self.center),
    #         width,
    #     )

    # def _draw_circle(self, radius, fgcolor, bgcolor, width):
    #     pygame.draw.circle(
    #         self.surf, bgcolor, (self.center, self.center), radius * self.scale
    #     )
    #     pygame.draw.circle(
    #         self.surf,
    #         fgcolor,
    #         (self.center, self.center),
    #         radius * self.scale,
    #         width=width,
    #     )

    # def _draw_num(self, radius, radius2, fgcolor, mystring):
    #     if mystring == "":
    #         return
    #     font = pygame.font.Font("freesansbold.ttf", int(40 * self.scale))
    #     text_surf = font.render(mystring, True, fgcolor)
    #     w, h = text_surf.get_size()
    #     # right
    #     self.surf.blit(
    #         text_surf,
    #         (
    #             self.center + ((radius - ((radius - radius2) * 0.5)) * self.scale) - w,
    #             self.center - h // 2,
    #         ),
    #     )
    #     # left
    #     self.surf.blit(
    #         text_surf,
    #         (
    #             self.center - ((radius - ((radius - radius2) * 0.5)) * self.scale),
    #             self.center - h // 2,
    #         ),
    #     )
    #     # top
    #     self.surf.blit(
    #         text_surf,
    #         (
    #             self.center - w // 2,
    #             self.center
    #             - ((radius - ((radius - radius2) * 0.5)) * self.scale)
    #             - 0.5 * h,
    #         ),
    #     )
    #     # bottom
    #     self.surf.blit(
    #         text_surf,
    #         (
    #             self.center - w // 2,
    #             self.center
    #             + ((radius - ((radius - radius2) * 0.5)) * self.scale)
    #             - 0.5 * h,
    #         ),
    #     )

    def set_disk_type(self, disktype):
        self.disktype = disktype

        if self.disktype == DISKTYPE_LP:
            self.max_scale = 0.02
            if self.scale is None:
                self.scale = LP_SCALE
            self.radius = LP_RADIUS
            self.fgcol = LP_FGCOL
            self.bgcol = LP_BGCOL
            self.text = LP_TEXT
            self.font_size = LP_FONT_SIZE
        else:
            self.max_scale = 0.02
            if self.scale is None:
                self.scale = self.width / LG_RADIUS[-1] / 4
            self.radius = LG_RADIUS
            self.fgcol = LG_FGCOL
            self.bgcol = LG_BGCOL
            self.text = LG_TEXT
            self.font_size = LG_FONT_SIZE

    def set_tracker_source_scale(self, rad):
        self.tracker.set_source_scale(rad)

    def set_tracker_source_offset(self, pos):
        # switch x/y
        self.tracker.set_offset_from_source(pos)

    def set_tracker_target_scale(self, rad):
        self.tracker.set_target_scale(rad)

    def set_trail_len(self, seconds):
        self.tracker.set_history_seconds(seconds)

    def get_tracker_resolution(self):
        return self.tracker.get_resolution()

    def get_tracker_offset(self):
        return self.tracker.get_offset()

    def add_position(self, pos):
        self.tracker.add_position(pos)

    def get_all_positions(self, scaled=True):
        return self.tracker.get_all_positions(scaled)

    def on_drag_start(self, startx, starty):
        self.cairo_drag_start_x = startx
        self.cairo_drag_start_y = starty

    def on_drag(self, x, y):
        self.cairo_offset_x = (
            self.cairo_orig_offset_x + self.cairo_drag_start_x + (x / self.scale)
        )
        self.cairo_offset_y = (
            self.cairo_orig_offset_y + self.cairo_drag_start_y + (y / self.scale)
        )

    def zoom(self, zoom_delta):
        """zoom target up to a maximum scale"""
        self.scale = max(self.max_scale, self.scale + zoom_delta * 0.01)

    def _set_col_from_rgba(self, context, rgba):
        if len(rgba) != 4:
            return False
        r, g, b, a = [chan / 255 for chan in rgba]
        context.set_source_rgba(r, g, b, a)

    def draw(self, area, c, w, h):
        col_black = (0, 0, 0)
        # a bit more neutral than the paper targets
        col_bg = (249, 247, 229, 255)
        #        bg_r, bg_g, bg_b = [x / 255 for x in col_bg]

        # get font
        c.select_font_face("sans")
        c.set_font_size(12 / self.scale)
        c.scale(self.scale, self.scale)

        # fill BG
        if self.pixbuf is not None:
            print("pixbuf exists")
            Gdk.cairo_set_source_pixbuf(c, self.pixbuf, 0, 0)
            c.rectangle(
                self.center - (LIGHTBOX_SIZE // 2),
                self.center - (LIGHTBOX_SIZE // 2),
                LIGHTBOX_SIZE,
                LIGHTBOX_SIZE,
            )
            c.fill()
        else:
            # set offset
            c.translate(
                w / 2 / self.scale + self.cairo_offset_x,
                h / 2 / self.scale + self.cairo_offset_y,
            )

            c.set_line_width(2 // self.scale)

            c.set_source_rgb(0.2, 0.2, 0.2)
            c.rectangle(
                -50_000,
                -50_000,
                100_000,
                100_000,
            )
            c.fill()
            #            c.set_source_rgb(bg_r, bg_g, bg_b)
            self._set_col_from_rgba(c, col_bg)
            c.rectangle(
                -LIGHTBOX_SIZE // 2,
                -LIGHTBOX_SIZE // 2,
                LIGHTBOX_SIZE,
                LIGHTBOX_SIZE,
            )
            c.fill()
            c.stroke()

            CENTERX = 0
            CENTERY = 0

            # spiegel

            c.set_source_rgb(0, 0, 0)
            c.arc(CENTERX, CENTERY, self.get_black_radius(), 0, 2 * PI)
            c.fill()
            c.stroke()

            # rings
            for r in range(len(self.radius) - 1, -1, -1):
                # colors
                color = self.fgcol[r][0] / 255
                textcol = self.fgcol[r - 1][0] / 255
                # text
                x_b, y_b, w, h = c.text_extents(self.text[r])[:4]
                radius = self.radius[r]
                radius2 = self.radius[r - 1]
                # ring
                c.set_source_rgb(color, color, color)
                c.arc(CENTERX, CENTERY, self.radius[r], 0, 2 * PI)
                c.stroke()
                # text
                c.set_source_rgb(textcol, textcol, textcol)
                # right text
                c.move_to(
                    CENTERX + radius - ((radius - radius2) / 2) - w / 2,
                    CENTERY + h / 2,
                )
                c.show_text(self.text[r])
                # left text
                c.move_to(
                    CENTERX - radius + ((radius - radius2) / 2) - w / 2,
                    CENTERY + h / 2,
                )
                c.show_text(self.text[r])
                # bottom text
                c.move_to(
                    CENTERX - w / 2,
                    CENTERY + radius - ((radius - radius2) / 2) + h / 2,
                )
                c.show_text(self.text[r])
                # top text
                c.move_to(
                    CENTERX - w / 2,
                    CENTERY - radius + ((radius - radius2) / 2) + h / 2,
                )
                c.show_text(self.text[r])
                # not sure why that's needed
                c.stroke()
        self._draw_trail(area, c, w, h, (CENTERX, CENTERY))
        self._draw_shots(area, c, w, h, (CENTERX, CENTERY))

    # # offsets everything
    # def draw(self, area, c, w, h, data):
    #     # def draw(self, draw_trail=True):
    #     self.surf = pygame.Surface((self.width, self.height))

    #     self.surf.fill((50, 50, 50))
    #     # draw the square
    #     pygame.draw.rect(
    #         self.surf,
    #         (255, 255, 255),
    #         (
    #             self.center - (LIGHTBOX_SIZE // 2) * self.scale,
    #             self.center - (LIGHTBOX_SIZE // 2) * self.scale,
    #             LIGHTBOX_SIZE * self.scale,
    #             LIGHTBOX_SIZE * self.scale,
    #         ),
    #         0,
    #     )

    #     # draw the target background
    #     for r in range(len(self.radius) - 1, -1, -1):
    #         self._draw_circle(self.radius[r], self.fgcol[r], self.bgcol[r], 2)
    #         self._draw_num(
    #             self.radius[r], self.radius[r - 1], self.fgcol[r - 1], self.text[r]
    #         )

    #     # draw the trail
    #     #        if draw_trail:
    #     #            self._draw_trail()
    #     print("draw_func")
    #     return self.surf

    # def _draw_trail(self):
    def _draw_trail(self, area, c, w, h, center):
        allpos = self.get_all_positions(scaled=True)

        # TODO: arbitrary - to be changed
        maxlen = 1000

        if len(allpos) > 2:
            l = lines.Lines(allpos)
            # origin
            l.set_origin(lines.vec2d(self.center, self.center))

            # color
            l.set_line_len_color_gradient((0, 1, 0), (1, 0, 0), maxlen)

            # draw
            if self.line_style == LINESTYLE_LINES:
                l.draw_lines(
                    area,
                    c,
                    w,
                    h,
                    center,
                    thickness=10,
                    scale=self.scale,
                    trail_fade=self.trail_fade,
                )
            else:
                l.draw_curve(
                    area,
                    c,
                    w,
                    h,
                    center,
                    thickness=10,
                    scale=self.scale,
                    trail_fade=self.trail_fade,
                )

    def set_line_style(self, style):
        if style == LINESTYLE_CURVE:
            self.line_style = LINESTYLE_CURVE
        else:
            self.line_style = LINESTYLE_LINES

    def set_trail_fade(self, state):
        self.trail_fade = state

    def get_black_radius(self):
        r = 0
        if self.disktype == DISKTYPE_LP:
            r = self.radius[4]
        else:
            r = self.radius[5]

        return r
        # return self.width / LG_RADIUS[-1] * r / 2.5

    def draw_center(self, c, limit=0):
        oldx = None
        oldy = None
        i = 0
        if limit != 0:
            shots = self.shots[:limit]
        else:
            shots = self.shots

        for shot in shots:
            if oldx is not None:
                x = oldx + float(shot.shot["x"])
                y = oldy + float(shot.shot["y"])
                color = (
                    "#00"
                    + hex(min(255, i))[2:].zfill(2)
                    + hex(max(0, 255 - i))[2:].zfill(2)
                )
                self._draw_line(c, 
                    oldx // i, oldy // i, x // (i + 1), y // (i + 1), color, 3
                )
                oldx = x
                oldy = y
            else:
                oldx = float(shot.shot["x"])
                oldy = float(shot.shot["y"])
            i += 1

#    def _draw_shots(self, sortme=False):
    def _draw_shots(self, area, c, w, h, center_pos, sortme=False):
        centerx, centery = center_pos

        # sort if needed, so the inner shots are on top        
        if sortme:
            sorted_shots = sorted(self.shots, key=lambda x: x.teiler(), reverse=True)
        else:
            sorted_shots = self.shots

        # for shot in self.shots:
        n = 0
        oldts = 0
        for shot in sorted_shots:
            if type(oldts) != int:
                waittime = min(500, (shot.date - oldts).total_seconds() * SPEED)
            else:
                waittime = 0
            #pygame.time.wait(int(waittime))
            #pygame.display.flip()
            x = float(shot.shot["x"])
            y = float(shot.shot["y"])
            color = SHOT_COLOR[shot.full()]
            self._draw_shot(c, x, y, color)
            n += 1
            self.draw_center(c, n)
            oldts = shot.date

    def add_shot(self, shot):
        self.shots.append(shot)


def main():
    t = Target()

    t.draw()


if __name__ == "__main__":
    main()
