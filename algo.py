from math import sqrt
import Numeric as num

def dist(p1, p2):
    return sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def lerp(p1, p2, t):
    return num.array(p1) * (1 - t) + num.array(p2) * t
