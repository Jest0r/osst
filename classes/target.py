import math

# from PIL import Image, ImageDraw
import pygame

# import numpy
from . import lines

TARGET_BGCOL = "#ffffff"
TARGET_FGCOL = "#000000"

SPEED = 1

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

LG_RADIUS = [25, 275, 525, 775, 1025, 1275, 1525, 1775, 2025, 2275]
LG_BGCOL = [BLACK, BLACK, BLACK, BLACK, BLACK, BLACK, WHITE, WHITE, WHITE, WHITE]
LG_FGCOL = [WHITE, WHITE, WHITE, WHITE, WHITE, BLACK, BLACK, BLACK, BLACK, BLACK]
LG_TEXT = ["", "", "8", "7", "6", "5", "4", "3", "2", "1"]

LP_RADIUS = [250, 575, 1375, 2175, 2975, 3775, 4575, 5375, 6175, 6975, 7775]
LP_BGCOL = [BLACK, BLACK, BLACK, BLACK, BLACK, WHITE, WHITE, WHITE, WHITE, WHITE, WHITE]
LP_FGCOL = [WHITE, WHITE, WHITE, WHITE, BLACK, BLACK, BLACK, BLACK, BLACK, BLACK, BLACK]
LP_TEXT = ["", "", "9", "8", "7", "6", "5", "4", "3", "2", "1"]

SHOT_RADIUS = 225  # 4.5mm caliber

LG_SCALE = 0.15
LP_SCALE = 0.05

pygame.init()


class Target:
    def __init__(self, dimensions, disktype="lp"):
        self.width = dimensions
        self.height = dimensions
        self.center = dimensions // 2
        #        self.radius = 2000
        self.disktype = disktype

        #        self.screen = pygame.display.set_mode((self.width, self.height), depth=32)

        self.shots = []
#        self.scale_factor = 1

        if self.disktype == "lp":
            self.max_scale = LP_SCALE
            self.scale = LP_SCALE
            self.radius = LP_RADIUS
            self.fgcol = LP_FGCOL
            self.bgcol = LP_BGCOL
            self.text = LP_TEXT
        else:
            self.max_scale = self.width / LG_RADIUS[-1]
#            self.scale = self.width / LG_RADIUS[-1] / 2.5
            self.scale = self.width / LG_RADIUS[-1] / 4
            self.radius = LG_RADIUS
            self.fgcol = LG_FGCOL
            self.bgcol = LG_BGCOL
            self.text = LG_TEXT

    def _draw_shot(self, x, y, color):
        r = SHOT_RADIUS * self.scale
        # print(r)
        c = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(c, color, (r, r), r)
        pygame.draw.circle(c, (0, 0, 0), (r, r), r, width=1)
        self.surf.blit(
            c,
            (
                (x - SHOT_RADIUS) * self.scale + self.center,
                (y - SHOT_RADIUS) * self.scale + self.center,
            ),
        )

    def _draw_line(self, oldx, oldy, x, y, color, width):
        pygame.draw.line(
            self.surf,
            color,
            ((oldx * self.scale) + self.center, (oldy * self.scale) + self.center),
            ((x * self.scale) + self.center, (y * self.scale) + self.center),
            width,
        )

    def _draw_circle(self, radius, fgcolor, bgcolor, width):
        pygame.draw.circle(
            self.surf, bgcolor, (self.center, self.center), radius * self.scale
        )
        pygame.draw.circle(
            self.surf,
            fgcolor,
            (self.center, self.center),
            radius * self.scale,
            width=width,
        )

    def _draw_num(self, radius, radius2, fgcolor, mystring):
        if mystring == "":
            return
        #font = pygame.font.Font("freesansbold.ttf", 15)
        font = pygame.font.Font("freesansbold.ttf",  int(80 *self.scale))
        text_surf = font.render(mystring, True, fgcolor)
        w, h = text_surf.get_size()
        # right
        self.surf.blit(
            text_surf,
            (
                self.center + ((radius - ((radius - radius2) * 0.5)) * self.scale) - w,
                self.center - h // 2,
            ),
        )
        # left
        self.surf.blit(
            text_surf,
            (
                self.center - ((radius - ((radius - radius2) * 0.5)) * self.scale),
                self.center - h // 2,
            ),
        )
        # top
        self.surf.blit(
            text_surf,
            (
                self.center - w // 2,
                self.center
                - ((radius - ((radius - radius2) * 0.5)) * self.scale)
                - 0.5 * h,
            ),
        )
        # bottom
        self.surf.blit(
            text_surf,
            (
                self.center - w // 2,
                self.center
                + ((radius - ((radius - radius2) * 0.5)) * self.scale)
                - 0.5 * h,
            ),
        )
    
    def scale_out(self, stepsize=0.01):
        self.scale += stepsize
        print(self.scale)

    def scale_in(self, stepsize=0.01):
        self.scale = max(0, self.scale - stepsize)
        print(self.scale)


#    def set_scale_factor(self, factor):
#        self.scale_factor = factor
        
    def draw(self):
        self.surf = pygame.Surface((self.width, self.height))

        #self.scale = self.width / LG_RADIUS[-1] / 2.5

        self.surf.fill((255, 255, 255))

        for r in range(len(self.radius) - 1, -1, -1):
            self._draw_circle(self.radius[r], self.fgcol[r], self.bgcol[r], 2)
            self._draw_num(
                self.radius[r], self.radius[r - 1], self.fgcol[r - 1], self.text[r]
            )

        return self.surf

    def get_black_radius(self):
        r = 0
        if self.disktype == "lp":
            r = self.radius[4]
        else:
            r = self.radius[5]

        return self.width / LG_RADIUS[-1] * r / 2.5


    def draw_center(self, limit=0):
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
                #                print(color)
                self._draw_line(
                    oldx // i, oldy // i, x // (i + 1), y // (i + 1), color, 3
                )
                #                print(oldx//i, oldy//i, x//(i+1), y//(i+1), i)
                oldx = x
                oldy = y
            else:
                oldx = float(shot.shot["x"])
                oldy = float(shot.shot["y"])
            i += 1

    def draw_shots(self, sortme=False):
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
            pygame.time.wait(int(waittime))
            pygame.display.flip()
            x = float(shot.shot["x"])
            y = float(shot.shot["y"])
            color = SHOT_COLOR[shot.full()]
            self._draw_shot(x, y, color)
            n += 1
            self.draw_center(n)
            oldts = shot.date

    #            if max(x, y) > self.scale:
    #                self.scale = self.width/max(x,y)
    #                self.scale = max(x,y)
    #            self.scale = self.max_scale/LG_RADIUS[-1] /2.5

    def add_shot(self, shot):
        self.shots.append(shot)


def main():
    t = Target()

    t.draw()


if __name__ == "__main__":
    main()
