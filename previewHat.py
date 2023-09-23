from direct.showbase.ShowBase import ShowBase
from pathlib import Path
from direct.actor.Actor import Actor

from tkinter.filedialog import askopenfilename
from panda3d.core import Filename, GraphicsOutput, WindowProperties, Texture, GraphicsPipe, FrameBufferProperties, AntialiasAttrib
from direct.gui.DirectGui import *
import sys, os

# We need to import the tkinter library to
# disable the tk window that pops up.
# We use tk for the file path selector.
import tkinter as tk

root = tk.Tk()
root.withdraw()

# Force high quality for our render
from panda3d.core import loadPrcFileData

loadPrcFileData('', 'default-antialias-enable 1')
loadPrcFileData('', 'framebuffer-multisample 1')
loadPrcFileData('', 'win-size 1920 1080')
loadPrcFileData('', 'model-path $RESOURCE_DIR')

"""
Controls:
s = Take screenshot
o = toggle oobe/free camera
r = reload loaded textures
e = reset rotation
b = toggle backface culling

k = move hat up
l (L) = move hat down

mouse wheel up = zoom in
mouse wheel down = zoom out
mouse3(middle mouse click) = reset zoom

left arrow = rotate negative heading
right arrow = rotate positive heading
up arrow = rotate positive pitch
down arrow = rotate negative pitch

"""

"""
Todo:
Add onscreen text that displays the offset (camers zoom, clothing rotation, etc.) <-- will be hidden in screenshots
"""


class previewHat(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)
        self.fileName = "output"  # Output file name
        self.fileFormat = ".png"
        self.midPointX = 0

        self.hatModel = None
        self.hatTex = None

        self.loadedTextures = [None]

        self.hat = None
        base.cam.setPos(0, -7, 0.25)
        self.defaultCamPos = base.cam.getPos()
        base.camera.hide()
        self.i = 1
        self.defaultH = 180  # todo: hotkey to reset all transformations
        self.currentH = self.defaultH
        self.defaultP = 0
        self.currentP = self.defaultP
        self.defaultY = -7
        self.currentY = self.defaultY

        self.defaultZ = 0.25  # note: negative goes up, positive goes down
        self.currentZ = self.defaultZ

        self.enabledAA = True
        self.enabledBFC = False

        # Just in case we have these enabled in the config...
        base.setFrameRateMeter(False)
        base.setSceneGraphAnalyzerMeter(False)

        base.disableMouse()

        self.loadHat()
        self.loadGUI()

        """
        If you want to change the default outfit texture (not desat), you can either
        change the texture path of the egg model(s) itself, or, alternatively, you can
        directly call to load specific textures, e.g.:
            self.loadHatModel("path/to/texture.png")
        """

        self.accept('s', self.aspect2d.hide)  # Hacky b/c hiding and showing in same method no work
        self.accept('s-up', self.saveScreenshot)
        self.accept('o', base.oobe)
        self.accept('b', self.toggleBFC)
        self.accept('r', self.reloadTextures)
        self.accept('e', self.defaultRotation)
        self.accept('wheel_up', self.zoomCamera, [0.1])
        self.accept('wheel_down', self.zoomCamera, [-0.1])
        self.accept('mouse2', self.defaultCam)
        self.accept('arrow_left', self.rotateHatH, [-5])
        self.accept('arrow_left-repeat', self.rotateHatH, [-5])
        self.accept('arrow_right', self.rotateHatH, [5])
        self.accept('arrow_right-repeat', self.rotateHatH, [5])

        self.accept('arrow_up', self.rotateHatP, [5])
        self.accept('arrow_up-repeat', self.rotateHatP, [5])
        self.accept('arrow_down', self.rotateHatP, [-5])
        self.accept('arrow_down-repeat', self.rotateHatP, [-5])

        self.accept('k', self.translateHatZ, [-0.1])
        self.accept('k-repeat', self.translateHatZ, [-0.1])
        self.accept('l', self.translateHatZ, [0.1])
        self.accept('l-repeat', self.translateHatZ, [0.1])

        self.accept('p', print, ["H = {}, P = {}".format(self.defaultH, self.defaultP)])
        self.accept('a', self.toggleAA)
        # self.accept('b', self.leg.showTightBounds)

        # most efficient color to use due to antialiasing.
        base.setBackgroundColor(0, 0, 0, 0)

    def toggleAA(self):
        if self.enabledAA:
            render.setAntialias(AntialiasAttrib.MNone)
        else:
            render.setAntialias(AntialiasAttrib.MAuto)
        self.enabledAA = not self.enabledAA
        # print(f"AA = {self.enabledAA}")

    def toggleBFC(self):
        self.enabledBFC = not self.enabledBFC
        render.setTwoSided(self.enabledBFC)

    def loadHat(self, path=None):
        self.clearHat()
        if path is None:
            self.hat = loader.loadModel("assets/tt_m_chr_avt_acc_hat_baseball.egg")
        else:
            self.hat = loader.loadModel(path)
        self.hat.reparentTo(render)

    def clearHat(self):
        if self.hat is not None:
            self.hat.removeNode()
            self.hat = None

    def loadGUI(self):
        # Todo: figure out how to reposition buttons when window changes size
        # guiFrame = DirectFrame(frameColor=(0, 0, 0, 1),
        #              frameSize=(-1, 1, -1, 1),
        #              pos=(1, -1, -1))
        self.modelButton = DirectButton(text = ("Change Hat Model"),
                                        scale = 0.05, pos = (-1.6, 0, -0.4), command = self.openModel)
        self.texButton = DirectButton(text = ("Change Hat Texture"),
                                      scale = 0.05, pos = (-1.6, 0, -0.5), command = self.openTexture)

    def saveScreenshot(self):
        # intent: Image number would increment if the file already exists just so it doesn't overwrite
        self.newfileName = self.fileName
        if not (os.path.isfile(self.newfileName)):  # wip
            self.newfileName = self.fileName + str(self.i)
            self.i += 1

        filename = self.newfileName + self.fileFormat
        base.win.saveScreenshot(Filename(filename))
        self.aspect2d.show()
        print("Screenshot saved! {}".format(filename))

    def reloadTextures(self):
        for tex in self.loadedTextures:
            if tex:
                tex.reload()

    # Rotate clothing

    def rotateHatH(self, value):
        self.currentH = self.hat.getH() + value
        self.hat.setH(self.currentH)

    def rotateHatP(self, value):
        self.currentP = self.hat.getP() + value
        self.hat.setP(self.currentP)

    def defaultRotation(self):
        self.currentH = self.defaultH
        self.hat.setH(self.currentH)
        self.currentP = self.defaultP
        self.hat.setP(self.currentP)

    def translateHatZ(self, value):
        self.currentZ = self.hat.getZ() + value
        self.hat.setZ(self.currentZ)

    # Camera Modifiers
    def defaultCam(self):
        base.cam.setPos(self.defaultCamPos)

    def zoomCamera(self, value):
        base.cam.setPos(base.cam.getX(), base.cam.getY() + value, base.cam.getZ())

    ###

    def browseForImage(self):
        path = Path(askopenfilename(filetypes = (
            ("Image Files", "*.jpg;*.jpeg;*.png;*.psd;*.tga"),
            ("JPEG", "*.jpg;*.jpeg"),
            ("PNG", "*.png"),
            ("Photoshop File", "*.psd"),
            ("Targa", "*.tga"))))
        return path

    def browseForModel(self):
        path = Path(askopenfilename(filetypes = (
            ("Panda3D Model Files", "*.egg;*.bam"),
            ("EGG", "*.egg"),
            ("BAM", "*.bam"))))
        return path

    def loadHatModel(self, file: str):
        self.hatModel = file
        self.loadHat(self.hatModel)

    def loadHatTexture(self, file: str):
        # File is an absolute path
        # So let's be compatible with both JPG+RGB and PNG variants of textures.
        fileExt = os.path.splitext(file)[1]
        fileTex = os.path.splitext(file)[0]
        if fileExt == '.png':
            # No special calls needed
            tex = loader.loadTexture(file)
        else:
            # todo: panda doesn't like loading _a.rgb like seen below
            # For now let's just only check for an a_rgb if not PNG
            tex = loader.loadTexture(file)
            # if os.path.isfile(fileTex + '_a.rgb'):
            #    tex = loader.loadTexture(file, fileTex + '_a.rgb')
            # else:
            #    tex = loader.loadTexture(file)
        self.hat.setTexture(tex, 1)
        self.hatTex = file
        self.loadedTextures[0] = tex

    def openModel(self):
        filename = self.browseForModel()
        if str(filename) == ".":
            return
        try:
            self.loadHatModel(filename)
        except:
            print(str(filename) + " could not be loaded!")

    def openTexture(self):
        filename = self.browseForImage()
        if str(filename) == ".":
            return
        try:
            self.loadHatTexture(filename)
        except:
            print(str(filename) + " could not be loaded!")


app = previewHat()
app.run()
