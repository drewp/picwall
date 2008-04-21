"""playing with 'with' statement for GL blocks"""
from __future__ import with_statement
from OpenGL.GL import (glPushMatrix, glPopMatrix, glEnable, glDisable,
                       glBegin, glEnd)

# probably incorrect use of the methods
class pushMatrix(object):
    def __init__(self):
        pass
    def __enter__(self):
        glPushMatrix()
    def __exit__(self, *exc_info):
        glPopMatrix()

class mode(object):
    def __init__(self, enable=None, disable=None):
        """pass lists of glEnable or glDisable constants"""
        self.enable, self.disable = enable or [], disable or []
    def __enter__(self):
        for mode in self.enable:
            glEnable(mode)
        for mode in self.disable:
            glDisable(mode)
    def __exit__(self, *exc_info):
        # not correct- they should be restored to what they were before
        for mode in self.enable:
            glDisable(mode)
        for mode in self.disable:
            glEnable(mode)

class begin(object):
    def __init__(self, arg):
        self.arg = arg
    def __enter__(self):
        glBegin(self.arg)
    def __exit__(self, *exc_info):
        glEnd()
