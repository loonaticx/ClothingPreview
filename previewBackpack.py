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

k = move backpack up
l (L) = move backpack down

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


class previewBackpack(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)
        self.fileName = "output" # Output file name
        self.fileFormat = ".png"
        self.midPointX = 0
        
        self.backpackModel = None
        self.backpackTex = None

        self.loadedTextures = [None]

        self.backpack = None
        base.cam.setPos(0, -7, 0.25)
        self.defaultCamPos = base.cam.getPos()
        base.camera.hide()
        self.i = 1
        self.defaultH = 180 # todo: hotkey to reset all transformations
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

        self.loadBackpack()
        self.loadGUI()

        """
        If you want to change the default outfit texture (not desat), you can either
        change the texture path of the egg model(s) itself, or, alternatively, you can
        directly call to load specific textures, e.g.:
            self.loadBackpackModel("path/to/texture.png")
        """

        self.accept('s', self.aspect2d.hide) # Hacky b/c hiding and showing in same method no work
        self.accept('s-up', self.saveScreenshot)
        self.accept('o', base.oobe)
        self.accept('b', self.toggleBFC)
        self.accept('r', self.reloadTextures)
        self.accept('e', self.defaultRotation)
        self.accept('wheel_up', self.zoomCamera, [0.1])
        self.accept('wheel_down', self.zoomCamera, [-0.1])
        self.accept('mouse2', self.defaultCam)
        self.accept('arrow_left', self.rotateBackpackH, [-5])
        self.accept('arrow_left-repeat', self.rotateBackpackH, [-5])
        self.accept('arrow_right', self.rotateBackpackH, [5])
        self.accept('arrow_right-repeat', self.rotateBackpackH, [5])
        
        self.accept('arrow_up', self.rotateBackpackP, [5])
        self.accept('arrow_up-repeat', self.rotateBackpackP, [5])
        self.accept('arrow_down', self.rotateBackpackP, [-5])
        self.accept('arrow_down-repeat', self.rotateBackpackP, [-5])
        
        self.accept('k', self.translateBackpackZ, [-0.1])
        self.accept('k-repeat', self.translateBackpackZ, [-0.1])
        self.accept('l', self.translateBackpackZ, [0.1])
        self.accept('l-repeat', self.translateBackpackZ, [0.1])

        self.accept('p', print, ["H = {}, P = {}".format(self.defaultH, self.defaultP)])
        self.accept('a', self.toggleAA)
        #self.accept('b', self.leg.showTightBounds)
        
        # most efficient color to use due to antialiasing. 
        base.setBackgroundColor(0, 0, 0, 0)
        
        
        
    def toggleAA(self):
        if self.enabledAA:
            render.setAntialias(AntialiasAttrib.MNone)
        else:
            render.setAntialias(AntialiasAttrib.MAuto)
        self.enabledAA = not self.enabledAA
        print(f"AA = {self.enabledAA}")
        
        
    def toggleBFC(self):
        self.enabledBFC = not self.enabledBFC
        render.setTwoSided(self.enabledBFC)



    def loadBackpack(self, path=None):
        self.clearBackpack()
        if path is None:
            self.backpack = loader.loadModel("assets/backpack.egg")
        else:
            self.backpack = loader.loadModel(path)
        self.backpack.reparentTo(render)

    def clearBackpack(self):
        if self.backpack is not None:
            self.backpack.removeNode()
            self.backpack = None

    def loadGUI(self):
        # Todo: figure out how to reposition buttons when window changes size
        #guiFrame = DirectFrame(frameColor=(0, 0, 0, 1),
        #              frameSize=(-1, 1, -1, 1),
        #              pos=(1, -1, -1))
        self.modelButton = DirectButton(text=("Change Backpack Model"),
                 scale=0.05, pos=(-1.6, 0, -0.4), command=self.openModel)
        self.texButton = DirectButton(text=("Change Backpack Texture"),
                 scale=0.05, pos=(-1.6, 0, -0.5), command=self.openTexture)


    def saveScreenshot(self):
        # intent: Image number would increment if the file already exists just so it doesn't overwrite
        self.newfileName = self.fileName
        if not (os.path.isfile(self.newfileName)): # wip
            self.newfileName = self.fileName+str(self.i)
            self.i +=1

        filename = self.newfileName +self.fileFormat
        base.win.saveScreenshot(Filename(filename))
        self.aspect2d.show()
        print("Screenshot saved! {}".format(filename))


    def reloadTextures(self):
        for tex in self.loadedTextures:
            if tex: tex.reload()

    # Rotate clothing

    def rotateBackpackH(self, value):
        self.currentH = self.backpack.getH() + value
        self.backpack.setH(self.currentH)


    def rotateBackpackP(self, value):
        self.currentP = self.backpack.getP() + value
        self.backpack.setP(self.currentP)

    def defaultRotation(self):
        self.currentH = self.defaultH
        self.backpack.setH(self.currentH)
        self.currentP = self.defaultP
        self.backpack.setP(self.currentP)
        
        
    def translateBackpackZ(self, value):
        self.currentZ = self.backpack.getZ() + value
        self.backpack.setZ(self.currentZ)

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

    def loadBackpackModel(self, file: str):
        self.backpackModel = file
        self.loadBackpack(self.backpackModel)


    def loadBackpackTexture(self, file: str):
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
            #if os.path.isfile(fileTex + '_a.rgb'):
            #    tex = loader.loadTexture(file, fileTex + '_a.rgb')
            #else:
            #    tex = loader.loadTexture(file)
        self.backpack.setTexture(tex, 1)
        self.backpackTex = file
        self.loadedTextures[0] = tex
        


    def openModel(self):
        filename = self.browseForModel()
        if str(filename) == ".":
            return
        try:
            self.loadBackpackModel(filename)
        except:
            print(str(filename) + " could not be loaded!")

    def openTexture(self):
        filename = self.browseForImage()
        if str(filename) == ".":
            return
        try:
            self.loadBackpackTexture(filename)
        except:
            print(str(filename) + " could not be loaded!")




app = previewBackpack()
app.run()
