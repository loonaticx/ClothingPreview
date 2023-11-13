from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from tkinter.filedialog import askopenfilename

from direct.gui.DirectButton import DirectButton
from direct.gui.DirectFrame import DirectFrame
from direct.showbase.ShowBase import ShowBase
from panda3d.core import *

# We need to import the tkinter library to
# disable the tk window that pops up.
# We use tk for the file path selector.
import tkinter as tk

root = tk.Tk()
root.withdraw()

# Force high quality for our render
loadPrcFileData('', 'default-antialias-enable 1')
loadPrcFileData('', 'framebuffer-multisample 1')
loadPrcFileData('', 'win-size 1600 900')

asset_dir = "assets/"

# Clash introduced slightly higher quality Toon bodies. Set below to True to enable the bodies to be used instead.
USE_CLASH_BODY = True
if USE_CLASH_BODY:
    asset_dir += "clash/"


@dataclass
class Body:
    def __hash__(self):
        return hash(f"{self.bodyType}_{self.bottomType}")

    bodyType: str
    _bottomType: str

    @property
    def bottomType(self):
        return self._bottomType

    @bottomType.setter
    def bottomType(self, type):
        self._bottomType = type

    @property
    def otherBottomType(self):
        print(f"bottom type rn is {self.bottomType}")
        if self.bottomType == "shorts":
            return "skirt"
        return "shorts"

    def getOtherBottomType(self):
        return self.otherBottomType


# Todo: Read from a config file
class CosmeticPreviewer(ShowBase):
    def __init__(self):
        super().__init__(self)
        self.activeCosmetics = []
        self.bodyModels = dict()
        self.bodyGroup = render.attachNewNode("body_grp")
        self.clothing = Clothing(self.bodyGroup)
        self.activeBody = None  # ['m', 'shorts']
        self.defaultH = 190
        self.currentH = self.defaultH
        self.defaultP = 0
        self.currentP = self.defaultP

        self.defaultCamPos = base.cam.getPos()
        # base.camera.hide()

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

        base.disableMouse()

        self.accept('shift-l', render.ls)
        self.accept('shift-a', render.analyze)
        self.accept('o', base.oobe)

        self.accept('1', self.applyClothingChange, extraArgs = ['torso-top'])
        self.accept('2', self.setActiveBody, extraArgs = ['m', 'shorts'])
        self.accept('3', self.previewClothing)

        self._loadBodyModels()
        self.setActiveBody('m', 'shorts')

    def _loadBodyModels(self):  # default: dogM_shorts
        for bodyType in ('m', 's', 'l'):
            for bottomType in ('shorts', 'skirt'):
                bodyAttrs = Body(bodyType, bottomType)
                bodyModel = loader.loadModel(f"{asset_dir}tt_a_chr_dg{bodyType}_{bottomType}_torso_1000.egg")
                body = bodyModel.getChild(0)
                body.reparentTo(self.bodyGroup)
                body.setTwoSided(True)
                for node in body.getChildren():
                    if node.getName() not in ("torso-top", "torso-bot", "sleeves"):
                        node.stash()
                self.setupBodyPos(body)
                self.bodyModels[bodyAttrs] = body
                body.hide()

    def setupBodyPos(self, body):
        body.setPos(-0.91, -4.9, -0.3)

        self.bodyGroup.setH(self.currentH)
        self.bodyGroup.setP(self.currentP)

    def setActiveBody(self, bodyType=None, bottomType=None, flipBottom=False):
        print(f"bottomType = {bottomType}")

        if self.activeBody:
            if not bodyType:
                bodyType = self.activeBody.bodyType
            if not bottomType:
                bottomType = self.activeBody.bottomType
        if flipBottom:
            bottomType = self.activeBody.otherBottomType

        self.hideBody()
        self.activeBody = Body(bodyType, bottomType)
        bodyModel = self.bodyModels[self.activeBody]
        bodyModel.show()

    def hideBody(self):
        if not self.activeBody:
            return
        activeBody = self.bodyModels[self.activeBody]
        activeBody.hide()

    def previewHats(self):
        pass

    def previewClothing(self):
        CosmeticPreviewerGUI(self, base.aspect2d)

    def browseForImage(self):
        path = Path(askopenfilename(filetypes = (
            ("Image Files", "*.jpg;*.jpeg;*.png;*.psd;*.tga"),
            ("JPEG", "*.jpg;*.jpeg"),
            ("PNG", "*.png"),
            ("Photoshop File", "*.psd"),
            ("Targa", "*.tga")
        )))

        return path

    def loadCosmeticTexture(self, cosmetic):
        filename = self.browseForImage()
        if str(filename) == ".":
            return
        try:
            return cosmetic.loadTexture(filename)
        except Exception as e:
            print(str(filename) + " could not be loaded!")
            print(f"Stack trace: {e}")
            return None

    def getBodyPartNode(self, body, part):
        bodyModel = self.bodyModels[body]
        return bodyModel.find(f"**/{part}")

    def applyClothingChange(self, part_name):
        clothing = self.clothing
        tex = self.loadCosmeticTexture(clothing)
        if tex:
            clothing.setPartTexture(part_name, tex)

    # Camera Modifiers
    def defaultCam(self):
        base.cam.setPos(self.defaultCamPos)
        self.orthoLens.setFilmSize(self.filmSizeX_BASE, self.filmSizeY_BASE)

    def zoomCamera(self, value):
        self.filmSizeX, self.filmSizeY = self.orthoLens.getFilmSize()
        self.orthoLens.setFilmSize(
            self.filmSizeX + (value * self.filmSizeX_BASE / 2),
            self.filmSizeY + (value * self.filmSizeY_BASE / 2)
        )
        base.cam.setPos(base.cam.getX(), base.cam.getY() + value, base.cam.getZ())


class CosmeticPreviewerGUI(DirectFrame):
    def __init__(self, previewer, parent, **kw):
        optiondefs = ()
        self.defineoptions(kw, optiondefs)
        super().__init__(parent, **kw)
        self.initialiseoptions(self.__class__)
        self.previewer = previewer
        self.activeGui = []
        self.loadClothingGUI()

    def loadClothingGUI(self):
        self.topButton = DirectButton(
            parent = self,
            text = ("Change Top"),
            scale = 0.05, pos = (-1.6, 0, -0.4),
            command = self.previewer.applyClothingChange,
            extraArgs = ['torso-top']
        )
        self.sleeveButton = DirectButton(
            text = ("Change Sleeve"),
            scale = 0.05, pos = (-1.6, 0, -0.5),
            command = self.previewer.applyClothingChange,
            extraArgs = ['sleeves']
        )
        self.shortsButton = DirectButton(
            text = ("Change Bottoms"),
            scale = 0.05, pos = (-1.6, 0, -0.6),
            command = self.previewer.applyClothingChange,
            extraArgs = ['torso-bot']
        )
        #
        self.loadSButton = DirectButton(
            text = ("dogs"),
            scale = 0.05, pos = (1.6, 0, -0.4),
            command = self.previewer.setActiveBody,
            extraArgs = ['s']
        )
        self.loadMButton = DirectButton(
            text = ("dogm"),
            scale = 0.05, pos = (1.6, 0, -0.5),
            command = self.previewer.setActiveBody,
            extraArgs = ['m']
        )
        self.loadLButton = DirectButton(
            text = ("dogl"),
            scale = 0.05, pos = (1.6, 0, -0.6),
            command = self.previewer.setActiveBody,
            extraArgs = ['l']
        )
        self.changeGenderButton = DirectButton(
            text = ("Change gender"),
            scale = 0.05, pos = (1.6, 0, -0.7),
            command = self.previewer.setActiveBody,
            extraArgs = [None, None, True]

        )

    def unloadClothingGUI(self):
        pass


class Cosmetic(NodePath):
    def __init__(self, baseNode):
        super().__init__(baseNode)
        self.modelPath = ""
        self.visible = False
        self.texturePaths = []
        self.loadedTextures = []
        self.targetNode = ""

    def setTexture(self, texture):
        pass

    def loadTexture(self, file: str):
        # self.sleeveTexFilepath = Filename.fromOsSpecific(str(file)).getDirname()
        # self.textureFilepathKey[self.lastSelectedFilepath] = self.sleeveTexFilepath
        tex = loader.loadTexture(file)
        partNode = super().find(f'**/{self.targetNode}')
        if partNode:
            partNode.setTexture(tex, 1)
        return tex

    def toggleVisibility(self):
        self.visible = not self.visible
        if self.visible:
            super().hide()
        else:
            super().show()


class Clothing(Cosmetic):

    class BottomTypes(IntEnum):
        SHORTS = 1
        SKIRT = 2

    def __init__(self, baseNode):
        # for the associated node we can do self.bodyGroup for clothing
        # so that we can affect all of them at once if need be
        super().__init__(baseNode)
        self.skirtTexture = ""
        self.shortsTexture = ""
        self.topTexture = ""
        self.sleeveTexture = ""
        self.parts2texture = {
            "torso-bot": "",
            "sleeves": "",
            "torso-top": "",
        }
        self._loadedTexture = None

    def loadTexture(self, textureFile):
        tex = super().loadTexture(textureFile)
        self._loadedTexture = tex
        return tex

    def setPartTexture(self, part=None, texture=None):
        if not part:
            part = self.targetNode
        if not texture:
            texture = self._loadedTexture
        print(f"part - {texture}")
        for node in self.findAllMatches(f"**/{part}"):
            node.setTexture(texture, 1)

    # loadTexture overriden


class Hat(Cosmetic):
    pass


if __name__ == "__main__":
    CosmeticPreviewer()
    base.run()
