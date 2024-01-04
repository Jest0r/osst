from gi.repository import Gdk
import numpy as np
from scipy import interpolate

X = 0
Y = 1
R = 0
G = 1
B = 2


class vec2d(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"vec2d({self.x}/{self.y})"

    def __add__(self, point):
        return vec2d(self.x + point.x, self.y + point.y)

    def __sub__(self, point):
        return vec2d(self.x - point.x, self.y - point.y)

    def __mul__(self, mult):
        return vec2d(self.x * mult, self.y * mult)

    def __truediv__(self, factor):
        return vec2d(self.x / factor, self.y / factor)

    def __floordiv__(self, factor):
        return vec2d(self.x // factor, self.y // factor)

    def __eq__(self, point):
        return point.x == self.x and point.y == self.y

    def __ne__(self, point):
        return point.x != self.x or point.y != self.y

    def distance(self, point):
        return int(((point.x - self.x) ** 2 + (point.y - self.y) ** 2) ** 0.5)

    def midpoint(self, point, midpoint=0.5):
        # return x,y of the mid poin between two points
        return vec2d((point.x + self.x) * midpoint, (point.y + self.y) * midpoint)


class Lines:
    def __init__(self, vertices):
        if type(vertices) != list:
            return False
        self.vertices = vertices[:]

        # max length for the gradient
        self.max_gradient_len = None

        # color for single colored line
        self.color = (0, 0, 0)
        # color for length dependent coloring
        self.min_col = None
        self.max_col = None
        # solid color or gradient
        self.gradient = False
        self.origin = vec2d(0, 0)

    def set_origin(self, pos):
        self.origin = pos

    def set_color(self, color):
        """settin single color"""
        self.color = color
        self.gradient = False

    def set_line_len_color_gradient(self, min_col, max_col, maxlen):
        """setting color gradient from min color to max col"""
        self.max_gradient_len = maxlen
        self.min_col = min_col
        self.max_col = max_col
        self.gradient = True

    def add(self, vertices):
        """add vertice(s)"""
        if type(vertices) != list:
            vertices = [vertices]
        self.vertices.extend(vertices)

    def get_color(self, x, y):
        if self.gradient:
            # get the percentage point of the gradient
            gradient_point = min(x.distance(y) / self.max_gradient_len, 1)

            # r g b absolute values
            r = (
                min(self.min_col[R], self.max_col[R])
                + gradient_point * max(self.min_col[R], self.max_col[R])
                - min(self.min_col[R], self.max_col[R])
            )
            g = (
                min(self.min_col[G], self.max_col[G])
                + gradient_point * max(self.min_col[G], self.max_col[G])
                - min(self.min_col[G], self.max_col[G])
            )
            b = (
                min(self.min_col[B], self.max_col[B])
                + gradient_point * max(self.min_col[B], self.max_col[B])
                - min(self.min_col[B], self.max_col[B])
            )

            # real values
            # ToDo - can that be done in the main calc?
            if self.min_col[R] > self.max_col[R]:
                r = 1 - r
            if self.min_col[G] > self.max_col[G]:
                g = 1 - g
            if self.min_col[B] > self.max_col[B]:
                b = 1 - b

            return (r, g, b)
        else:
            # invert color for debugging
            self.color = (1 - self.color[R], 1 - self.color[G], 1 - self.color[B])

            return self.color

    def num_vertices(self):
        return len(self.vertices)

    def draw_lines(
        self,
        area,
        c,
        width,
        height,
        center,
        vertices=None,
        thickness=3,
        scale=1,
        trail_fade=False,
    ):
        center = vec2d(center[0], center[1])
        if vertices is None:
            vertices = self.vertices

        #        c.set_source_rgb(1, 0, 0)
        c.move_to(vertices[0].x, vertices[0].y)
        oldv = vertices[0]
        for i, v in enumerate(vertices, start=1):
            r, g, b = self.get_color(oldv, v)
            if trail_fade:
                a = 1 - (i / len(vertices))
            else:
                a = 1
            c.set_source_rgba(r, g, b, a)
            pos = v - center
            c.line_to(pos.x, pos.y)
            oldv = v
            c.stroke()
            c.move_to(pos.x, pos.y)

    def draw_curve(
        self,
        area,
        c,
        width,
        height,
        center,
        vertices=None,
        num_points=None,
        thickness=1,
        scale=1,
        trail_fade=False,
    ):
        if vertices is None:
            vertices = self.vertices

        if num_points is None:
            num_points = len(vertices) * 20

        # hack to get a simple color
        if self.gradient == False:
            color = self.color
        else:
            color = self.min_col

        # bsplines can't deal with duplicate input points
        bspline_vertices = []
        for v in vertices:
            if v not in bspline_vertices:
                bspline_vertices.append(v)

        if len(bspline_vertices) < 5:
            return

        try:
            tck, uu = interpolate.splprep(
                [
                    [i.x for i in bspline_vertices],
                    [i.y for i in bspline_vertices],
                ],
                s=0,
            )
        except ValueError:
            #            print(bspline_vertices)
            raise

        u = np.linspace(0, 1, num=num_points)

        i_coords = interpolate.splev(u, tck)
        interpolated_vertices = [
            vec2d(i_coords[X][i], i_coords[Y][i]) for i in range(len(i_coords[0]))
        ]
        self.draw_lines(
            area,
            c,
            width,
            height,
            center,
            interpolated_vertices,
            thickness,
            scale,
            trail_fade=False,
        )


def main():
    import pygame

    pygame.init()
    screen = pygame.display.set_mode((1024, 768))

    ### Control points that are later used to calculate the curve
    control_points = [
        vec2d(100, 100),
        vec2d(150, 500),
        vec2d(450, 500),
        vec2d(400, 400),
        vec2d(500, 150),
        vec2d(400, 150),
        vec2d(250, 350),
    ]

    lines = Lines(control_points)
    lines.set_line_len_color_gradient((0, 1, 0), (1, 0, 0), 20)

    ### The currently selected point
    selected = None

    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type in (pygame.QUIT, pygame.KEYDOWN):
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for p in control_points:
                    if abs(p.x - event.pos[X]) < 10 and abs(p.y - event.pos[Y]) < 10:
                        selected = p
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                selected = None

        ### Draw stuff
        screen.fill((100, 100, 100))

        if selected is not None:
            selected.x, selected.y = pygame.mouse.get_pos()
            pygame.draw.circle(screen, (0, 255, 0), (selected.x, selected.y), 10)

        ### Draw control points
        for p in control_points:
            pygame.draw.circle(screen, (0, 0, 255), (int(p.x), int(p.y)), 4)

        ### Draw control "lines"
        lines.draw_lines(screen, thickness=1)

        lines.draw_curve(screen, thickness=1)

        ### Flip screen
        pygame.display.flip()
        clock.tick(100)


if __name__ == "__main__":
    main()
