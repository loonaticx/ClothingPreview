from direct.showbase.ShowBase import ShowBase
from pathlib import Path
from direct.actor.Actor import Actor

from tkinter.filedialog import askopenfilename
from panda3d.core import Filename, GraphicsOutput, WindowProperties, Texture, GraphicsPipe, FrameBufferProperties
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
        self.fileName = "output" # Output file name
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
        self.LshoesVisible = True # Boots
        self.leg = None
        self.legModel = None
        self.type = 'm' # Body type | s, m, l
        self.defaultCamPos = base.cam.getPos()
        base.camera.hide()
        self.i = 1
        self.defaultH = 180 # todo: hotkey to reset all transformations
        self.currentH = self.defaultH
        self.defaultP = 0
        self.currentP = self.defaultP

        # Just in case we have these enabled in the config...
        base.setFrameRateMeter(False)
        base.setSceneGraphAnalyzerMeter(False)

        base.disableMouse()

        self.loadBody()
        self.loadGUI()

        """
        If you want to change the default outfit texture (not desat), you can either
        change the texture path of the egg model(s) itself, or, alternatively, you can
        directly call to load specific textures, e.g.:
            self.loadTopTexture("path/to/texture.png")
        """

        self.accept('s', self.aspect2d.hide) # Hacky b/c hiding and showing in same method no work
        self.accept('s-up', self.saveScreenshot)
        self.accept('o', base.oobe)
        self.accept('r', self.reloadTextures)
        self.accept('e', self.defaultRotation)
        self.accept('wheel_up', self.zoomCamera, [0.1])
        self.accept('wheel_down', self.zoomCamera, [-0.1])
        self.accept('mouse2', self.defaultCam)
        self.accept('arrow_left', self.rotateClothingH, [-5])
        self.accept('arrow_left-repeat', self.rotateClothingH, [-5])
        self.accept('arrow_right', self.rotateClothingH, [5])
        self.accept('arrow_right-repeat', self.rotateClothingH, [5])
        self.accept('arrow_up', self.rotateClothingP, [5])
        self.accept('arrow_up-repeat', self.rotateClothingP, [5])
        self.accept('arrow_down', self.rotateClothingP, [-5])
        self.accept('arrow_down-repeat', self.rotateClothingP, [-5])
        self.accept('1', self.gotoShoes)
        self.accept('2', self.gotoMid)
        self.accept('3', self.gotoBoots)
        self.accept('4', self.loadBody, ['s'])
        self.accept('5', self.loadBody, ['m'])
        self.accept('6', self.loadBody, ['l'])
        self.accept('p', print, ["H = {}, P = {}".format(self.defaultH, self.defaultP)])
        #self.accept('b', self.leg.showTightBounds)


    """
    ("tt_a_chr_dgX_Y_leg_1000.egg")
    X = s, m, l
    Y = shorts, skirt
    """
    def loadBody(self, type='m'): # default: dogM_shorts
        self.clearBody()
        self.type = type
        self.legModel = Actor("assets/tt_a_chr_dg{}_shorts_legs_1000.egg".format(type), {
                        'neutral': "assets/tt_a_chr_dg{}_shorts_legs_neutral.egg".format(type)
                        })
        #self.legModel.pose('neutral', 24)
        #self.legModel.stop()
        self.legModel.reparentTo(render)
        self.leg = self.legModel.getChild(0)
        for node in self.leg.getChildren():
            if (node.getName() != 'shoes')\
            and (node.getName() != 'boots_short')\
            and (node.getName() != 'boots_long'):
                node.stash()
        if self.shoeTex is not None:
            self.leg.find('**/shoes').setTexture(self.loadedTextures[0], 1)
        if self.sBootTex is not None:
            self.leg.find('**/boots_short').setTexture(self.loadedTextures[1], 1)
        if self.lBootTex is not None:
            self.leg.find('**/boots_long').setTexture(self.loadedTextures[2], 1)
        self.leg.find('**/shoes').setX(self.leftMargin)
        self.leg.find('**/boots_short').setX(self.midPointX)
        self.leg.find('**/boots_long').setX(self.rightMargin)

        # note: Z-up
        self.leg.setPos(0.00, 4.69, -0.235)
        self.leg.setH(self.currentH)
        self.leg.setP(self.currentP)
        self.leg.setTwoSided(True)

    def clearBody(self):
        if self.leg is not None:
            self.leg.removeNode()
            self.leg = None
        if self.legModel is not None:
            self.legModel.cleanup()
            self.legModel = None

    def loadGUI(self):
        # Todo: figure out how to reposition buttons when window changes size
        #guiFrame = DirectFrame(frameColor=(0, 0, 0, 1),
        #              frameSize=(-1, 1, -1, 1),
        #              pos=(1, -1, -1))
        self.topButton = DirectButton(text=("Change Shoe Texture"),
                 scale=0.05, pos=(-1.6, 0, -0.4), command=self.openTop)
        self.sleeveButton = DirectButton(text=("Change Small Boots Texture"),
                 scale=0.05, pos=(-1.6, 0, -0.5), command=self.openSleeves)
        self.shortsButton = DirectButton(text=("Change Long Boots Texture"),
                 scale=0.05, pos=(-1.6, 0, -0.6), command=self.openBottom)

        self.loadSButton = DirectButton(text=("dogs"),
                 scale=0.05, pos=(1.6, 0, -0.4),  command=self.loadBody, extraArgs=['s'])
        self.loadMButton = DirectButton(text=("dogm"),
                 scale=0.05, pos=(1.6, 0, -0.5),  command=self.loadBody, extraArgs=['m'])
        self.loadLButton = DirectButton(text=("dogl"),
                 scale=0.05, pos=(1.6, 0, -0.6),  command=self.loadBody, extraArgs=['l'])


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

    def gotoShoes(self):
        base.cam.setX(self.leftMargin)
    
    def gotoMid(self):
        base.cam.setX(self.midPointX)
    
    def gotoBoots(self):
        base.cam.setX(self.rightMargin)

    # temporary until i have a better way to do this lol
    def toggleShoes(self):
        if self.leg is None:
            return
        if (self.SshoesVisible):
            self.leg.find('**/shoes').hide()
            self.leg.find('**/shoes').hide()
            self.SshoesVisible = False
        else:
            self.leg.find('**/shoes').show()
            self.leg.find('**/shoes').show()
            self.SshoesVisible = True

    def toggleSMBoots(self):
        if self.leg is None:
            return
        if (self.MshoesVisible):
            self.leg.find('**/boots_short').hide()
            self.leg.find('**/boots_short').hide()
            self.MshoesVisible = False
        else:
            self.leg.find('**/boots_short').show()
            self.leg.find('**/boots_short').show()
            self.MshoesVisible = True

    def toggleLBoots(self):
        if self.leg is None:
            return
        if (self.LshoesVisible):
            self.leg.find('**/boots_long').hide()
            self.leg.find('**/boots_long').hide()
            self.LshoesVisible = False
        else:
            self.leg.find('**/boots_long').show()
            self.leg.find('**/boots_long').show()
            self.LshoesVisible = True
            
    def hideAllVisible(self):
        if self.leg is None:
            return
        if (self.SshoesVisible):
            self.leg.find('**/shoes').hide()
            self.leg.find('**/shoes').hide()
            self.SshoesVisible = False
        if (self.MshoesVisible):
            self.leg.find('**/boots_short').hide()
            self.leg.find('**/boots_short').hide()
            self.MshoesVisible = False
        if (self.LshoesVisible):
            self.leg.find('**/boots_long').hide()
            self.leg.find('**/boots_long').hide()
            self.LshoesVisible = False


    # Rotate clothing

    def rotateClothingH(self, value):
        self.currentH = self.leg.getH() + value
        self.leg.setH(self.currentH)


    def rotateClothingP(self, value):
        self.currentP = self.leg.getP() + value
        self.leg.setP(self.currentP)

    def defaultRotation(self):
        self.currentH = self.defaultH
        self.leg.setH(self.currentH)
        self.currentP = self.defaultP
        self.leg.setP(self.currentP)

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

    def loadTopTexture(self, file: str):
        tex = loader.loadTexture(file)
        self.shoeTex = file
        self.loadedTextures[0] = tex
        self.leg.find('**/shoes').setTexture(tex, 1)

    def loadSleeveTexture(self, file: str):
        tex = loader.loadTexture(file)
        self.sBootTex = file
        self.loadedTextures[1] = tex
        self.leg.find('**/boots_short').setTexture(tex, 1)

    def loadBottomTexture(self, file: str):
        tex = loader.loadTexture(file)
        self.lBootTex = file
        self.loadedTextures[2] = tex
        self.leg.find('**/boots_long').setTexture(tex, 1)

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



app = previewShoes()
app.run()
