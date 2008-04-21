from __future__ import division
import Numeric as num
from OpenGL import GLUT, GLU, GL
from OpenGL.GL import glClearColor
from OpenGL.GL import glEnable,  glEnd, glEndList, glPushMatrix, glTranslatef, glColor3f
from OpenGL.GL import glPopMatrix, glClear, glLoadIdentity,glDisable,glViewport,glBegin
from OpenGL.GL import glTexCoord2f,glVertex3f,glFrustum,glMatrixMode,glNewList,glGenLists,glScalef
from OpenGL.GL import glFlush,glBindTexture,glTexImage2D,glTexParameterf,glCallList
from PIL import Image
import sys, pygame,time, os
from math import sqrt
from twisted.internet import reactor
import picrss

class Pt(object):
    """coordinate that smoothly changes, using various speed curves"""
    
    def __init__(self, x):
        self.x = x
        self.goal = x
        
    def goto(self, x, secs=None, expSecs=None):
        self.goal = x

    def step(self, dt):
        self.x += (self.goal - self.x) * dt

def dist(p1, p2):
    return sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def lerp(p1, p2, t):
    return num.array(p1) * (1 - t) + num.array(p2) * t

cardList = None

def openglSetup():
    global cardList
    GLUT.glutInit(sys.argv)

    glClearColor (0.0, 0.0, 0.0, 0.0)
    glEnable(GL.GL_DEPTH_TEST) 
    glEnable(GL.GL_COLOR_MATERIAL)

    glViewport (0, 0, surf.get_width(), surf.get_height())
    glMatrixMode (GL.GL_PROJECTION)
    glLoadIdentity ()
    glFrustum (-1.0, 1.0, -1.0, 1.0, 1.5, 20.0)
    glMatrixMode (GL.GL_MODELVIEW)

    cardList = glGenLists(1)
    glNewList(cardList, GL.GL_COMPILE)
    glColor3f(1,1,1)
    glBegin(GL.GL_QUADS)
    glTexCoord2f(0.0, 1.0); glVertex3f(-1.0, -1.0,  0.0)
    glTexCoord2f(1.0, 1.0); glVertex3f( 1.0, -1.0,  0.0)
    glTexCoord2f(1.0, 0.0); glVertex3f( 1.0, 1.0,  0.0)
    glTexCoord2f(0.0, 0.0); glVertex3f(-1.0, 1.0,  0.0)
    glEnd()
    glEndList()

cardZSlide = .1 # sec, roughly

class AllCards(object):
    """
    holds the ImageCards objs you can currently see on the wall, plus
    the current zoom/hover
    """
    def __init__(self):

        self.cards = []
        self.currentZoom = None
        self.currentRaise = None

        #root = "/home/drewp/pic/digicam/dl-2008-04-19"
        root = "specnature-thumbs"
#        pics = [os.path.join(root, f)
#                for f in os.listdir(root) if f.lower().endswith('.jpg')]
        pics = list(picrss.localDir(root))

        for x in range(12):
            for y in range(3):
                self.cards.append(ImageCard(pics[(x * 3 + y) % len(pics)],
                                       (x * 2.2 + .5,
                                        y * 2.2 - .6 + .5,
                                        0)))
    def cardAtPoint(self, pos):
        wx, wy, _ = pos
        for card in self.cards:
            cx, cy, _ = card.center
            if abs(cx - wx) < 1 and abs(cy - wy) < 1:
                return card
        raise ValueError

    def raiseAtPoint(self, pos):
        if self.currentRaise is not None and not self.currentRaise.zoom:
            self.currentRaise.goalZ = 0
        try:
            card = self.cardAtPoint(pos)
            if not card.zoom:
                card.goalZ = .6
            self.currentRaise = card
        except ValueError:
            self.currentRaise = None

    def zoomAtPoint(self, pos, centerFunc=lambda x: None):
        if self.currentZoom is not None:
            self.currentZoom.zoom = 0
            self.currentZoom = None
            return

        try:
            card = self.cardAtPoint(pos)
            print "zoom", card
            card.zoom = 1
            self.currentZoom = card
            centerFunc(card.center[0])
        except ValueError:
            pass

    def __iter__(self):
        return iter(self.cards)

class ImageCard(object):
    """the visible card object"""
    def __init__(self, thumbImage, center):
        self.center = center
        self.thumbImage = thumbImage
        self.goalZ = 0
        self.z = 0
        self.zoom = 0 # if 1, the card should fill the frame

    def step(self, dt):
        self.z += (self.goalZ - self.z) * dt / cardZSlide

    def draw(self, eyeX, horizonY):
        """draw the card in place """

        textureData = self.thumbImage.getData('thumb')
        if textureData is None:
            return

        glBindTexture(GL.GL_TEXTURE_2D, 0)
        glTexImage2D( GL.GL_TEXTURE_2D, 0, GL.GL_RGB,
                      256, #multiImage.size()[0],
                      256, #multiImage.size()[1],
                      0,
                      GL.GL_RGB, GL.GL_UNSIGNED_BYTE, textureData)
        glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER,
                        GL.GL_LINEAR)
        glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER,
                        GL.GL_LINEAR)

        glPushMatrix()
        if 1:
            pos = num.array(self.center)
            pos[2] += self.z
            if self.zoom:
                full = [eyeX, horizonY, 6.3]
                pos = lerp(pos, full, self.zoom)
            glTranslatef(*pos)

            # card facing +Z from -1<x<1 -1<y<1
            glCallList(cardList)
        glPopMatrix()

    def __repr__(self):
        return "Card(%r, %r)" % (self.thumbImage, self.center)


cards = AllCards()

class Scene(object):
    """wall, photo cards

    wall is static; camera moves
    """
    def __init__(self):
        self.eyeX = 0 # camera location
        self.lookX = 0 # camera look-at
        self.ball = [0,0,0] # reference pos
 
    def draw(self):
        t1 = time.time()
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        glLoadIdentity ()
        horizonY = 1 * 2.2 - .6 + .5
        GLU.gluLookAt (self.eyeX, horizonY, 8.0,
                       self.lookX, horizonY, 0.0,
                       0.0, 1.0, 0.0)

        glEnable(GL.GL_TEXTURE_2D)

        if 0:
            glPushMatrix()
            glColor3f(1,0,0)
            glTranslatef(*self.ball)
            glScalef(.2, .2, 1)
            imageCard("sample.jpg")
            glPopMatrix()

        glPushMatrix()
        if 1:
            glDisable(GL.GL_LIGHTING)

            for card in cards:
                card.draw(self.eyeX, horizonY)
                

            glEnable(GL.GL_LIGHTING)

        glPopMatrix()

        glFlush()
        pygame.display.flip()
        #print "draw", time.time() - t1

    def wallWidth(self):
        return 12 * 2.2

pygame.init()

surf = pygame.display.set_mode((800, 600),
                               pygame.OPENGL |
                               #pygame.FULLSCREEN | 
                               pygame.DOUBLEBUF |
                               0)
scene = Scene()
openglSetup()

goalXSpeed = 7 / 50 # units / sec per pixel
eyeCatchUp = 3 # du / sec. lower = more tilting
rampUp = .5 # sec to get to full speed
rampDown = .3 # sec to stop

class MainLoop(object):
    def __init__(self):
        self.buttons = None
        self.dx = 0 # "joystick" x pos
        self.goalX = 0 # wall center goal
        self.decel = 1 # 1..0 during decelleration
        self.lastUpdate = time.time()

        reactor.callLater(0, self.update)
            
    def update(self):
        t = time.time()
        dt = t - self.lastUpdate
        self.lastUpdate = t

        while 1:
            event = pygame.event.poll()
            if event.type == pygame.NOEVENT:
                break
            self.onEvent(event, dt)
        self.step(dt)
        scene.draw()
        reactor.callLater(0, self.update)

    def step(self, dt):
        if self.buttons is None and self.decel > 0:
            self.decel = max(0, self.decel - dt / rampDown)

        self.goalX += self.dx * goalXSpeed * dt * self.decel
        self.goalX = max(0, min(scene.wallWidth(), self.goalX))
        #scene.ball = [self.goalX, -.1, .1]
        
        # look can't be too fast, since I jump the goalX when you click an image
        scene.lookX += (self.goalX - scene.lookX) * dt * eyeCatchUp * 3

        scene.eyeX += (self.goalX - scene.eyeX) * dt * eyeCatchUp

        #sys.stdout.write("goal %s, eye %s, dx %s, decel %s        \r" %
        #                 (self.goalX, scene.eyeX, self.dx, self.decel))
        #sys.stdout.flush()

        for card in cards:
            card.step(dt)

    def onEvent(self, event, dt):
        if event.type is pygame.QUIT:
            reactor.stop()

        if event.type is pygame.KEYDOWN:
            if event.key is pygame.K_ESCAPE:
                reactor.stop()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.buttons = 1
                self.dx = 0
                self.clickPos = event.pos

        if event.type == pygame.MOUSEMOTION:
            if self.buttons == 1:
                self.dx = event.pos[0] - self.clickPos[0]
                self.decel = min(1, self.decel + dt / rampUp)

            cards.raiseAtPoint(self.cursorPosition(event.pos))
            scene.ball[2] = .001
            #scene.ball = [0,0,.01]
            #print scene.ball

        if event.type == pygame.MOUSEBUTTONUP:
            self.buttons = None
            print "up"
            if dist(event.pos, self.clickPos) < 5:
                def goto(x):
                    self.goalX = x
                cards.zoomAtPoint(self.cursorPosition(event.pos), goto)
                

    def cursorPosition(self, eventPos):
        """cursor coordinates on z=0 plane for the given screen pixel coord"""
        w, h = surf.get_size()
        sx, sy = eventPos
        # something's messed up with my projections. there shouldn't
        # be any estimated 5.3 multiplier in here
        wx, wy, _ = GLU.gluUnProject(w / 2 + (sx - w / 2) * 5.3,
                                     h / 2 - (sy - h / 2) * 5.3,
                                     0)
        return [wx, wy, 0]

ml = MainLoop()
reactor.run()
