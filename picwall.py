from OpenGL import GLUT, GLU, GL
from OpenGL.GL import glClearColor, glShadeModel
from OpenGL.GL import glEnable, glLightfv, glEnd, glEndList, glPushMatrix, glTranslatef, glColor3f
from OpenGL.GL import glPopMatrix, glClear, glLoadIdentity,glDisable,glLightModelfv,glViewport,glBegin
from OpenGL.GL import glTexCoord2f,glVertex3f,glFrustum,glMatrixMode,glNewList,glGenLists,glScalef
from OpenGL.GL import glFlush,glBindTexture,glTexImage2D,glTexParameterf,glCallList,glRotate
from PIL import Image
import sys, pygame,time
from math import sin

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


def draw():
    t1 = time.time()
    glClearColor(0.0, 0.0, 0.0, 0.0)
    glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
    glLoadIdentity ()
    GLU.gluLookAt (0.0, 0.7, 8.0,
                   0.0, 0.5, 0.0,
                   0.0, 1.0, 0.0)
    
    glRotate(sin(t1 * .7) * 40,0,1,0)
    
    glEnable(GL.GL_TEXTURE_2D)
    matching = False
    glPushMatrix()
    if 1:
        
        glDisable(GL.GL_LIGHTING)

        for x in range(10):
            for y in range(3):
                glPushMatrix()
                if (x,y)==(1,1):
                    glTranslatef(0,0,.2)
                    glScalef(1.3, 1.3, 1)
                glTranslatef(-3 + x * 2.2, y * 2.2 - .6, 0)
                imageCard("sample.jpg")
                glPopMatrix()

        glEnable(GL.GL_LIGHTING)

    glPopMatrix()
    
    glFlush()
    pygame.display.flip()
    #print "draw", time.time() - t1

pygame.init()

surf = pygame.display.set_mode((1200, 600),
                               pygame.OPENGL |
                               #pygame.FULLSCREEN | 
                               pygame.DOUBLEBUF |
                               0)

openglSetup()

def loop():
    while 1:
        try:
            event=pygame.event.poll ()

            if event.type is pygame.QUIT:
              sys.exit(0)

            draw()

            if event.type is pygame.KEYDOWN:
              if event.key is pygame.K_ESCAPE:
                sys.exit(0)
              if event.key is pygame.K_1:
                direction2=2
        except KeyboardInterrupt:
            break

loop()
