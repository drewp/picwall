from __future__ import division, with_statement
import Numeric as num
from OpenGL import GLU, GL
from OpenGL.GL import glClearColor,glNewList,glGenLists,glScalef
from OpenGL.GL import glEnable, glEndList, glTranslatef, glColor3f
from OpenGL.GL import glClear, glLoadIdentity, glViewport,glCallList
from OpenGL.GL import glTexCoord2f,glVertex3f,glFrustum,glMatrixMode
from OpenGL.GL import glFlush,glBindTexture,glTexImage2D,glTexParameterf
import pygame, time, sys
from twisted.internet import reactor
import picrss
from glsyntax import pushMatrix, mode, begin
from algo import dist, lerp

class AnimParam:
    cardZSlide = .1 # sec, roughly
    goalXSpeed = 7 / 50 # units / sec per pixel
    eyeCatchUp = 3 # du / sec. lower = more tilting
    rampUp = .5 # sec to get to full speed
    rampDown = .3 # sec to stop

class Pt(object):
    """coordinate that smoothly changes, using various speed curves"""

    allPts = []

    @staticmethod
    def stepAll(dt):
        for p in Pt.allPts:
            p.step(dt)
    
    def __init__(self, x):
        self.allPts.append(self)
        self.x = x
        self.goal = x
        self.expSecs = 0
        
    def goto(self, x, secs=None, expSecs=None):
        self.goal = x
        self.expSecs = expSecs

    def step(self, dt):
        self.x += (self.goal - self.x) * dt * self.expSecs


class AllCards(object):
    """
    holds the ImageCards objs you can currently see on the wall, plus
    the current zoom/hover
    """
    def __init__(self, images):
        """images is an iterable of ThumbImage objs"""
        self.cards = []
        self.currentZoom = None
        self.currentRaise = None

        #root = "/home/drewp/pic/digicam/dl-2008-04-19"

#        pics = [os.path.join(root, f)
#                for f in os.listdir(root) if f.lower().endswith('.jpg')]
        pics = list(images)

        for x in range(12):
            for y in range(3):
                self.cards.append(ImageCard(pics[(x * 3 + y) % len(pics)],
                                       (x * 2.2 + .5,
                                        y * 2.2 - .6 + .5,
                                        0)))

    def wallWidth(self):
        return 12 * 2.2

    def cardAtPoint(self, pos):
        wx, wy, _ = pos
        for card in self.cards:
            cx, cy, _ = card.center
            if abs(cx - wx) < 1 and abs(cy - wy) < 1:
                return card
        raise ValueError

    def raiseAtPoint(self, pos):
        if self.currentRaise is not None and not self.currentRaise.zoom:
            self.currentRaise.z.goto(0, expSecs=1 / AnimParam.cardZSlide)
        try:
            card = self.cardAtPoint(pos)
            if not card.zoom:
                card.z.goto(.6, expSecs=1 / AnimParam.cardZSlide)
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
        """center is the 3d position of the normal center of this card
        (when it isn't zoomed)"""
        self.center = center
        self.thumbImage = thumbImage
        self.z = Pt(0)
        
        self.zoom = 0 # if 1, the card should fill the frame

#    def step(self, dt):
#        self.z += (self.goalZ - self.z) * dt / AnimParam.cardZSlide

    def draw(self, eyeX, horizonY, cardList):
        """draw the card in place, using small/large image data as needed """

        with pushMatrix():
            pos = num.array(self.center)
            pos[2] += self.z.x
            if self.zoom:
                full = [eyeX, horizonY, 6.3]
                pos = lerp(pos, full, self.zoom)
            glTranslatef(*pos)

            layers = [('thumb', 1, self.thumbImage.getData('thumb'))]
            if self.zoom:
                data = self.thumbImage.getData('full')
                if data is not None:
                    layers.append(('full', 1, data))
                    # once opacity is fadable, and it's at 1, then we
                    # can remove the thumb layer from the list.

                    layers.reverse() # fix opengl draw order so hires is on top

                    

            for size, opacity, imgData in layers:
                if imgData is None:
                    # need to unset tx here!
                    glCallList(cardList)
                    # or draw a blank border, maybe some load status
                    # indication
                else:
                    (w,h), textureData = imgData
                    glBindTexture(GL.GL_TEXTURE_2D, 0)
                    glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGB,
                                 w,
                                 h,
                                 0,
                                 GL.GL_RGB, GL.GL_UNSIGNED_BYTE, textureData)
                    glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER,
                                    GL.GL_LINEAR)
                    glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER,
                                    GL.GL_LINEAR)

                    # card facing +Z from -1<x<1 -1<y<1
                    glCallList(cardList)

        # if it's a bottom-row image, draw the reflection here

    def __repr__(self):
        return "Card(%r, %r)" % (self.thumbImage, self.center)


class Scene(object):
    """Rendering of wall and photo cards. No animation code in here.

    wall is static; camera moves
    """
    def __init__(self, surf, cards):
        self.surf = surf
        self.cards = cards
        
        self.eyeX = Pt(0) # camera location
        self.eyeX.expSecs = AnimParam.eyeCatchUp
        
        self.lookX = Pt(0) # camera look-at
        # look has to be faster than eyeX, to make the camera look
        # ahead of where it is.
        self.lookX.expSecs = AnimParam.eyeCatchUp * 3
        
        self.ball = [0,0,0] # a reference pos for debugging

    def openglSetup(self):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glEnable(GL.GL_DEPTH_TEST) 
        glEnable(GL.GL_COLOR_MATERIAL)

        glViewport (0, 0, self.surf.get_width(), self.surf.get_height())
        glMatrixMode (GL.GL_PROJECTION)
        glLoadIdentity ()
        glFrustum (-1.0, 1.0, -1.0, 1.0, 1.5, 20.0)
        glMatrixMode (GL.GL_MODELVIEW)

        self.cardList = glGenLists(1)
        glNewList(self.cardList, GL.GL_COMPILE)
        glColor3f(1,1,1)
        with begin(GL.GL_QUADS):
            glTexCoord2f(0.0, 1.0); glVertex3f(-1.0, -1.0,  0.0)
            glTexCoord2f(1.0, 1.0); glVertex3f( 1.0, -1.0,  0.0)
            glTexCoord2f(1.0, 0.0); glVertex3f( 1.0, 1.0,  0.0)
            glTexCoord2f(0.0, 0.0); glVertex3f(-1.0, 1.0,  0.0)
        glEndList()
 
    def draw(self):
        t1 = time.time()
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        glLoadIdentity ()
        horizonY = 1 * 2.2 - .6 + .5
        GLU.gluLookAt(self.eyeX.x, horizonY, 8.0,
                      self.lookX.x, horizonY, 0.0,
                      0.0, 1.0, 0.0)

        glEnable(GL.GL_TEXTURE_2D)

        if 0:
            with pushMatrix():
                glColor3f(1,0,0)
                glTranslatef(*self.ball)
                glScalef(.2, .2, 1)
                imageCard("sample.jpg")

        with pushMatrix():
            with mode(disable=[GL.GL_LIGHTING]):
                for card in self.cards:
                    card.draw(self.eyeX.x, horizonY, self.cardList)

        glFlush()
        pygame.display.flip()
        #print "draw", time.time() - t1

class MainLoop(object):
    """
    animation control, user input
    """
    def __init__(self, cards, scene):
        self.cards, self.scene = cards, scene
        self.buttons = None
        self.dx = 0 # "joystick" x pos

        self.goalX = Pt(0) # wall center goal

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
        self.scene.draw()
        reactor.callLater(0, self.update)

    def step(self, dt):
        """advance all animation by one time step. dt should be the
        seconds since the last step call"""
        scene = self.scene

        if self.buttons is None and self.decel > 0:
            self.decel = max(0, self.decel - dt / AnimParam.rampDown)

        self.goalX.x += self.dx * AnimParam.goalXSpeed * dt * self.decel
        self.goalX.x = max(0, min(self.cards.wallWidth(), self.goalX.x))

        scene.lookX.goal = self.goalX.x
        scene.eyeX.goal = self.goalX.x
        #scene.ball = [self.goalX.x, -.1, .1]

        Pt.stepAll(dt)

        #sys.stdout.write("goal %s, eye %s, dx %s, decel %s        \r" %
        #                 (self.goalX.x, scene.eyeX, self.dx, self.decel))
        #sys.stdout.flush()


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
                self.decel = min(1, self.decel + dt / AnimParam.rampUp)

            self.cards.raiseAtPoint(self.cursorPosition(event.pos))
            self.scene.ball[2] = .001
            #self.scene.ball = [0,0,.01]
            #print self.scene.ball

        if event.type == pygame.MOUSEBUTTONUP:
            self.buttons = None
            print "up"
            if dist(event.pos, self.clickPos) < 5:
                def goto(x):
                    self.goalX.x = x
                self.cards.zoomAtPoint(self.cursorPosition(event.pos), goto)
                

    def cursorPosition(self, eventPos):
        """cursor coordinates on z=0 plane for the given screen pixel coord"""
        w, h = self.scene.surf.get_size()
        sx, sy = eventPos
        # something's messed up with my projections. there shouldn't
        # be any estimated 5.3 multiplier in here
        wx, wy, _ = GLU.gluUnProject(w / 2 + (sx - w / 2) * 5.3,
                                     h / 2 - (sy - h / 2) * 5.3,
                                     0)
        return [wx, wy, 0]

def main():
    pygame.init()

    surf = pygame.display.set_mode((800, 600),
                                   pygame.OPENGL |
                                   #pygame.FULLSCREEN | 
                                   pygame.DOUBLEBUF |
                                   0)
    arg = sys.argv[1]
    print repr(arg)
    if arg.startswith(('http:', 'file:')):
        imgs = picrss.flickrImages(sys.argv[1])
    else:
        imgs = picrss.localDir(sys.argv[1])
    cards = AllCards(imgs)
    scene = Scene(surf, cards)
    scene.openglSetup()

    ml = MainLoop(cards, scene)
    reactor.run()
main()
