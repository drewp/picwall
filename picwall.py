from __future__ import division
from OpenGL import GLUT, GLU, GL
from OpenGL.GL import glClearColor
from OpenGL.GL import glEnable,  glEnd, glEndList, glPushMatrix, glTranslatef, glColor3f
from OpenGL.GL import glPopMatrix, glClear, glLoadIdentity,glDisable,glViewport,glBegin
from OpenGL.GL import glTexCoord2f,glVertex3f,glFrustum,glMatrixMode,glNewList,glGenLists,glScalef
from OpenGL.GL import glFlush,glBindTexture,glTexImage2D,glTexParameterf,glCallList,glRotate
from PIL import Image
import sys, pygame,time,random, os
from math import sin, sqrt

cardList = None

def openglSetup():
    global cardList
    GLUT.glutInit(sys.argv)

    glClearColor (0.0, 0.0, 0.0, 0.0)
    glEnable(GL.GL_DEPTH_TEST) 

    glViewport (0, 0, surf.get_width(), surf.get_height())
    glMatrixMode (GL.GL_PROJECTION)
    glLoadIdentity ()
    glFrustum (-1.0, 1.0, -1.0, 1.0, 1.5, 20.0)
    glMatrixMode (GL.GL_MODELVIEW)

    cardList = glGenLists(1)
    glNewList(cardList, GL.GL_COMPILE)
    glColor3f(1,1,1)
    glBegin(GL.GL_QUADS)
    glTexCoord2f(0.0, 1.0); glVertex3f(-1.0, -1.0,  1.0)
    glTexCoord2f(1.0, 1.0); glVertex3f( 1.0, -1.0,  1.0)
    glTexCoord2f(1.0, 0.0); glVertex3f( 1.0, 1.0,  1.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(-1.0, 1.0,  1.0)
    glEnd()
    glEndList()

_tex = {}
def imageCard(filename):
    """card facing +Z from -1<x<1 -1<y<1"""
    if filename not in _tex:
        img = Image.open(filename)
        _tex[filename] = img.resize((256, 256)).tostring()
    textureData = _tex[filename]

    glBindTexture(GL.GL_TEXTURE_2D, 0)
    glTexImage2D( GL.GL_TEXTURE_2D, 0, GL.GL_RGB,
                  256, #multiImage.size()[0],
                  256, #multiImage.size()[1],
                  0,
                  GL.GL_RGB, GL.GL_UNSIGNED_BYTE, textureData)
    glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
    glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)

    glCallList(cardList)

class Scene(object):
    """wall, photo cards

    camera position is constant, although the camera can look left/right
    """
    def __init__(self):
        self._wallX = -3 # left origin of wall
        self.lookX = 0 # camera look-at

    def wallX():
        def fset(self, x):
            self._wallX = min(3, max(-7*2.2, x))
        def fget(self):
            return self._wallX
        return locals()
    wallX = property(**wallX())

    def draw(self):
        t1 = time.time()
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        glLoadIdentity ()
        GLU.gluLookAt (0.0, 0.7, 8.0,
                       self.lookX, 0.5, 0.0,
                       0.0, 1.0, 0.0)

        #glRotate(self.rotY, 0, 1, 0)

        glEnable(GL.GL_TEXTURE_2D)
        glPushMatrix()
        if 1:
            glDisable(GL.GL_LIGHTING)

            #root = "/home/drewp/pic/digicam/dl-2008-04-19"
            root = "specnature-thumbs"
            pics = [os.path.join(root, f)
                    for f in os.listdir(root) if f.lower().endswith('.jpg')]


            for x in range(7):
                for y in range(3):
                    glPushMatrix()
                    if (x,y)==(1,1):
                        glTranslatef(0,0,.05)
                        glScalef(1.3, 1.3, 1)
                    glTranslatef(self.wallX + x * 2.2,
                                 y * 2.2 - .6,
                                 0)
                    imageCard(pics[(x * 3 + y) % len(pics)])
                    glPopMatrix()

            glEnable(GL.GL_LIGHTING)

        glPopMatrix()

        glFlush()
        pygame.display.flip()
        #print "draw", time.time() - t1

pygame.init()

surf = pygame.display.set_mode((800, 600),
                               pygame.OPENGL |
                               #pygame.FULLSCREEN | 
                               pygame.DOUBLEBUF |
                               0)
scene = Scene()
openglSetup()

def dist(p1, p2):
    return sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

class MainLoop(object):
    def __init__(self):
        self.buttons = None
        self.dx = 0 # "joystick" x pos
        self.rot = 0 # rotation due to move
        self.decel = 1 # 1..0 during decelleration
        while 1:
            try:
                self.update()
            except KeyboardInterrupt:
                break
            
    def update(self):
        event=pygame.event.poll ()

        if event.type is pygame.QUIT:
          sys.exit(0)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.buttons = 1
                self.buttonStartX = event.pos[0]
                self.dx = 0
                self.rot = 0
                self.clickPos = event.pos
                
        if event.type == pygame.MOUSEMOTION and self.buttons == 1:
            self.dx = event.pos[0] - self.buttonStartX
            self.rot = -self.dx / 50
            self.decel = min(1, self.decel + .05)

        if event.type == pygame.MOUSEBUTTONUP:
            self.buttons = None
            if dist(event.pos, self.clickPos) < 5:
                print "clicked", event.pos

        if self.buttons is None and self.decel > 0:
            self.decel = max(0, self.decel - .02)

        scene.wallX += self.dx / 1000 * self.decel
        scene.lookX = self.rot * (self.decel ** 1.2)

            
        if event.type is pygame.KEYDOWN:
          if event.key is pygame.K_ESCAPE:
            sys.exit(0)
          if event.key is pygame.K_1:
            direction2=2
            
        scene.draw()

MainLoop()
