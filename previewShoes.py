from direct.showbase.ShowBase import ShowBase
from pathlib import Path
from direct.actor.Actor import Actor

from tkinter.filedialog import askopenfilename
from panda3d.core import Filename, OrthographicLens, GraphicsOutput, WindowProperties, Texture, GraphicsPipe, FrameBufferProperties
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
loadPrcFileData('', 'win-size 1600 900')

"""
Controls:
s = Take screenshot
o = toggle oobe/free camera
r = reload loaded textures
e = reset rotation
1 = toggle shirt
2 = toggle bottoms
3 = load dogs body
4 = load dogm body
5 = load dogl body
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


class previewShoes(ShowBase):

    def __init__(self):
        ShowBase.__init__(self)
        self.fileName = "output"  # Output file name
        self.fileFormat = ".png"
        self.midPointX = 0
        self.leftMargin = self.midPointX - 5
        self.rightMargin = self.midPointX + 5
        self.shoeTex = None
        self.sBootTex = None
        self.lBootTex = None
        self.loadedTextures = [None, None, None]
        self.SshoesVisible = True
        self.MshoesVisible = True
        self.LshoesVisible = True  # Boots
        self.shoeModels = None
        self.shoeModelsModel = None
        self.hiddenLeftShoe = False
        self.hiddenRightShoe = False
        self.type = 'm'  # Body type | s, m, l
        self.defaultCamPos = base.cam.getPos()
        base.camera.hide()
        self.i = 1
        self.defaultH = 180  # todo: hotkey to reset all transformations
        self.currentH = self.defaultH
        self.defaultP = 0
        self.currentP = self.defaultP
        
        # Camera
        # 16 : 9 aspect ratio default
        scaleMultiplier = 0.25
        self.filmSizeX_BASE = 16 * scaleMultiplier
        self.filmSizeY_BASE = 9 * scaleMultiplier
        
        self.filmSizeX = 16
        self.filmSizeY = 9
        
        self.orthoLens = OrthographicLens()
        self.orthoLens.setFilmSize(self.filmSizeX, self.filmSizeY)
        self.isOrthoView = False
        self.defaultLens = base.cam.node().getLens()

        # Just in case we have these enabled in the config...
        base.setFrameRateMeter(False)
        base.setSceneGraphAnalyzerMeter(False)

        base.disableMouse()

        self.loadShoes()
        self.loadGUI()

        """
        If you want to change the default outfit texture (not desat), you can either
        change the texture path of the egg model(s) itself, or, alternatively, you can
        directly call to load specific textures, e.g.:
            self.loadTopTexture("path/to/texture.png")
        """

        self.accept('s', self.aspect2d.hide)  # Hacky b/c hiding and showing in same method no work
        self.accept('s-up', self.saveScreenshot)
        self.accept('o', base.oobe)
        self.accept('r', self.reloadTextures)
        self.accept('e', self.defaultRotation)
        self.accept('c', self.toggleOrthoView)
        self.accept('wheel_up', self.zoomCamera, [0.1])
        self.accept('wheel_down', self.zoomCamera, [-0.1])
        self.accept('mouse2', self.defaultCam)
        self.accept('arrow_left', self.rotateShoesH, [-5])
        self.accept('arrow_left-repeat', self.rotateShoesH, [-5])
        self.accept('arrow_right', self.rotateShoesH, [5])
        self.accept('arrow_right-repeat', self.rotateShoesH, [5])
        self.accept('arrow_up', self.rotateShoesP, [5])
        self.accept('arrow_up-repeat', self.rotateShoesP, [5])
        self.accept('arrow_down', self.rotateShoesP, [-5])
        self.accept('arrow_down-repeat', self.rotateShoesP, [-5])
        self.accept('1', self.gotoShoes)
        self.accept('2', self.gotoMid)
        self.accept('3', self.gotoBoots)
        self.accept('4', self.toggleLeftShoe)
        self.accept('5', self.toggleRightShoe)
        self.accept('p', print, ["H = {}, P = {}".format(self.defaultH, self.defaultP)])
        # self.accept('b', self.shoeModels.showTightBounds)

        # most efficient color to use due to antialiasing. 
        base.setBackgroundColor(0, 0, 0, 0)

    def loadShoes(self):  # default: dogM_shorts
        self.clearShoes()
        self.shoeModels = loader.loadModel("assets/shoes_distanced.egg")
        self.shoeModels.reparentTo(render)

        self.shoeSmall = self.shoeModels.find("**/shoes_distanced_sm")
        self.shoeMedium = self.shoeModels.find("**/shoes_distanced_md")
        self.shoeLarge = self.shoeModels.find("**/shoes_distanced_lg")

        if self.shoeTex is not None:
            self.shoeSmall.setTexture(self.loadedTextures[0], 1)
        if self.sBootTex is not None:
            self.shoeMedium.setTexture(self.loadedTextures[1], 1)
        if self.lBootTex is not None:
            self.shoeLarge.setTexture(self.loadedTextures[2], 1)
        self.shoeSmall.setX(self.leftMargin)
        self.shoeMedium.setX(self.midPointX)
        self.shoeLarge.setX(self.rightMargin)

        # note: Z-up
        self.shoeModels.setPos(0.00, 4.69, -0.235)
        self.shoeModels.setH(self.currentH)
        self.shoeModels.setP(self.currentP)
        self.shoeModels.setTwoSided(True)

    def clearShoes(self):
        if self.shoeModels:
            self.shoeModels.removeNode()
            self.shoeModels = None

    def loadGUI(self):
        # Todo: figure out how to reposition buttons when window changes size
        # guiFrame = DirectFrame(frameColor=(0, 0, 0, 1),
        #              frameSize=(-1, 1, -1, 1),
        #              pos=(1, -1, -1))
        self.topButton = DirectButton(text = ("Change Shoe Texture"),
                                      scale = 0.05, pos = (-1.4, 0, -0.4), command = self.openTop)
        self.sleeveButton = DirectButton(text = ("Change Small Boots Texture"),
                                         scale = 0.05, pos = (-1.4, 0, -0.5), command = self.openSleeves)
        self.shortsButton = DirectButton(text = ("Change Long Boots Texture"),
                                         scale = 0.05, pos = (-1.4, 0, -0.6), command = self.openBottom)

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

    def toggleLeftShoe(self):
        if not self.hiddenLeftShoe:
            for shoe in self.shoeModels.findAllMatches("**/shoe_left"):
                shoe.hide()
        else:
            for shoe in self.shoeModels.findAllMatches("**/shoe_left"):
                shoe.show()
        self.hiddenLeftShoe = not self.hiddenLeftShoe

    def toggleRightShoe(self):
        if not self.hiddenRightShoe:
            for shoe in self.shoeModels.findAllMatches("**/shoe_right"):
                shoe.hide()
        else:
            for shoe in self.shoeModels.findAllMatches("**/shoe_right"):
                shoe.show()
        self.hiddenRightShoe = not self.hiddenRightShoe

    def gotoShoes(self):
        base.cam.setX(self.rightMargin)

    def gotoMid(self):
        base.cam.setX(self.midPointX)

    def gotoBoots(self):
        base.cam.setX(self.leftMargin)

    # temporary until i have a better way to do this lol
    def toggleShoes(self):
        if self.shoeModels is None:
            return
        if (self.SshoesVisible):
            self.shoeSmall.hide()
            self.shoeSmall.hide()
            self.SshoesVisible = False
        else:
            self.shoeSmall.show()
            self.shoeSmall.show()
            self.SshoesVisible = True

    def toggleSMBoots(self):
        if self.shoeModels is None:
            return
        if (self.MshoesVisible):
            self.shoeMedium.hide()
            self.shoeMedium.hide()
            self.MshoesVisible = False
        else:
            self.shoeMedium.show()
            self.shoeMedium.show()
            self.MshoesVisible = True

    def toggleLBoots(self):
        if self.shoeModels is None:
            return
        if (self.LshoesVisible):
            self.shoeLarge.hide()
            self.shoeLarge.hide()
            self.LshoesVisible = False
        else:
            self.shoeLarge.show()
            self.shoeLarge.show()
            self.LshoesVisible = True

    def hideAllVisible(self):
        if self.shoeModels is None:
            return
        if (self.SshoesVisible):
            self.shoeSmall.hide()
            self.shoeSmall.hide()
            self.SshoesVisible = False
        if (self.MshoesVisible):
            self.shoeMedium.hide()
            self.shoeMedium.hide()
            self.MshoesVisible = False
        if (self.LshoesVisible):
            self.shoeLarge.hide()
            self.shoeLarge.hide()
            self.LshoesVisible = False

    # Rotate clothing

    def rotateShoesH(self, value):
        self.currentH = self.shoeSmall.getH() + value
        self.shoeSmall.setH(self.currentH)
        self.shoeMedium.setH(self.currentH)
        self.shoeLarge.setH(self.currentH)

    def rotateShoesP(self, value):
        self.currentP = self.shoeSmall.getP() + value
        self.shoeSmall.setP(self.currentP)
        self.shoeMedium.setP(self.currentP)
        self.shoeLarge.setP(self.currentP)

    def defaultRotation(self):
        self.currentH = self.defaultH
        self.shoeSmall.setH(self.currentH)
        self.shoeMedium.setH(self.currentH)
        self.shoeLarge.setH(self.currentH)
        self.currentP = self.defaultP
        self.shoeSmall.setP(self.currentP)
        self.shoeMedium.setP(self.currentP)
        self.shoeLarge.setP(self.currentP)

    # Camera Modifiers
    def defaultCam(self):
        base.cam.setPos(self.defaultCamPos)
        self.orthoLens.setFilmSize(self.filmSizeX_BASE, self.filmSizeY_BASE)

    def zoomCamera(self, value):
        self.filmSizeX, self.filmSizeY = self.orthoLens.getFilmSize()
        self.orthoLens.setFilmSize(self.filmSizeX + (value * self.filmSizeX_BASE/2), self.filmSizeY+ (value* self.filmSizeY_BASE/2))
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

    def loadTopTexture(self, file: str):
        tex = loader.loadTexture(file)
        self.shoeTex = file
        self.loadedTextures[0] = tex
        self.shoeSmall.setTexture(tex, 1)

    def loadSleeveTexture(self, file: str):
        tex = loader.loadTexture(file)
        self.sBootTex = file
        self.loadedTextures[1] = tex
        self.shoeMedium.setTexture(tex, 1)

    def loadBottomTexture(self, file: str):
        tex = loader.loadTexture(file)
        self.lBootTex = file
        self.loadedTextures[2] = tex
        self.shoeLarge.setTexture(tex, 1)

    def openTop(self):
        filename = self.browseForImage()
        if str(filename) == ".":
            return
        try:
            self.loadTopTexture(filename)
        except:
            print(str(filename) + " could not be loaded!")

    def openSleeves(self):
        filename = self.browseForImage()
        if str(filename) == ".":
            return
        try:
            self.loadSleeveTexture(filename)
        except:
            print(str(filename) + " could not be loaded!")

    def openBottom(self):
        filename = self.browseForImage()
        if str(filename) == ".":
            return
        try:
            self.loadBottomTexture(filename)
        except:
            print(str(filename) + " could not be loaded!")

    def toggleOrthoView(self):
        self.isOrthoView = not self.isOrthoView
        if self.isOrthoView:
            base.cam.node().setLens(self.orthoLens)
        else:
            base.cam.node().setLens(self.defaultLens)


app = previewShoes()
app.run()
