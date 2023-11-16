from dataclasses import dataclass
from pathlib import Path
from tkinter.filedialog import askopenfilename
import sys, os
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
        if self.bottomType == "shorts":
            return "skirt"
        return "shorts"


# Todo: Read from a config file
class CosmeticPreviewer(ShowBase):


    cosmeticName2Default = {
        "hat": "",
        "backpack": "",
        "shoes": "",
        "glasses": ""
    }

    def __init__(self):
        super().__init__(self)
        self.activeCosmetics = []
        self.bodyModels = dict()
        self.bodyGroup = render.attachNewNode("body_grp")
        self.accGroup = render.attachNewNode("acc_grp")

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
        self.accept('q', sys.exit)

        self.accept('1', self.applyClothingChange, extraArgs = ['torso-top'])
        self.accept('2', self.setActiveBody, extraArgs = ['m', 'shorts'])
        self.accept('3', self.previewClothing)

        self._loadBodyModels()
        self._loadAccessoryModels()
        self.setActiveBody('m', 'shorts')
        self.activeAccessory = None
        CosmeticPreviewerGUI(self, aspect2d)

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

    def _loadAccessoryModels(self):
        self.accessoryModels = {
            "hat": Accessory(loader.loadModel(f"assets/tt_m_chr_avt_acc_hat_baseball.egg")),
            "glasses": Accessory(loader.loadModel(f"assets/glasses.egg")),
            "backpack": Accessory(loader.loadModel(f"assets/backpack.egg")),
            "shoes": Accessory(loader.loadModel(f"assets/glasses.egg")),
        }
        for model in self.accessoryModels.values():
            model.reparentTo(self.accGroup)
            model.hide()

    def setupBodyPos(self, body):
        # Todo: Find good pos for long body
        body.setPos(-0.91, -4.9, -0.3)
        self.bodyGroup.setH(self.currentH)
        self.bodyGroup.setP(self.currentP)

    def setActiveBody(self, bodyType=None, bottomType=None, flipBottom=False):
        if self.activeBody:
            if not bodyType:
                bodyType = self.activeBody.bodyType
            if not bottomType:
                bottomType = self.activeBody.bottomType
        if flipBottom:
            bottomType = self.activeBody.otherBottomType

        self.viewBody(visible = False)
        self.activeBody = Body(bodyType, bottomType)
        bodyModel = self.bodyModels[self.activeBody]
        bodyModel.show()

    def applyNewAccessory(self, accType):
        newAccessory = self.loadAccessory()
        self.accessoryModels[accType] = newAccessory

    def setActiveAccessory(self, newAccessory):
        self.viewBody(visible = False)
        if self.activeAccessory and self.activeAccessory.accessoryType == newAccessory.accessoryType:
            self.activeAccessory.removeNode()
            self.activeAccessory = newAccessory
        self.accessoryModels[newAccessory.accessoryType] = newAccessory
        newAccessory.show()

    def viewBody(self, visible=False):
        if not self.activeBody:
            return
        activeBody = self.bodyModels[self.activeBody]
        if visible:
            activeBody.show()
        else:
            activeBody.hide()

    def toggleBodyControls(self, enable_controls=True):
        if enable_controls:
            self.accept('wheel_up', self.zoomCamera, [0.1])
            self.accept('wheel_down', self.zoomCamera, [-0.1])
        else:
            self.ignore('wheel_up')
            self.ignore('wheel_down')

    def viewAccessory(self, accType):
        print(f"type = {accType}")
        self.viewBody(visible=False)
        if self.activeAccessory:
            self.activeAccessory.hide()
        self.activeAccessory = self.accessoryModels[accType]  # default accessory model
        self.activeAccessory.show()

    def previewClothing(self):
        pass

    def browseForImage(self):
        path = Path(askopenfilename(filetypes = (
            ("Image Files", "*.jpg;*.jpeg;*.png;*.psd;*.tga"),
            ("JPEG", "*.jpg;*.jpeg"),
            ("PNG", "*.png"),
            ("Photoshop File", "*.psd"),
            ("Targa", "*.tga")
        )))

        return path

    def browseForModel(self):
        path = Path(askopenfilename(filetypes = (
            ("Panda3D Model Files", "*.egg;*.bam"),
        )))
        return path

    def loadAccessory(self):
        filename = self.browseForModel()
        if str(filename) == ".":
            return
        try:
            return Accessory(loader.loadModel(filename))
        except Exception as e:
            print(str(filename) + " could not be loaded!")
            print(f"Stack trace: {e}")
            return None


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

    def removeCosmetic(self, cosmetic):
        pass

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

    _marginX = 1
    _marginY = 1
    xAmt = -1
    yAmt = -1


    def refresh_ui(func, *args):
        def prep(self, *args):
            self.hideActiveGui()
            func(self, *args)

        return prep

    def __init__(self, previewer, parent, **kw):
        optiondefs = ()
        self.defineoptions(kw, optiondefs)
        super().__init__(parent, **kw)
        self.initialiseoptions(self.__class__)
        self.previewer = previewer
        self.activeGui = []
        self.cosmeticTypesGui = None
        self.menuGui = None
        self.clothingGuiEnabled = False
        self.accessoryGuiEnabled = False
        self.menuGuiVisible = False
        # self.toggleClothingGui()
        self.loadGui()
        self.toggleMenuGui()
        base.accept('4', self.toggleClothingGui)

    @property
    def marginX(self):
        self._marginX -= self.xAmt
        return self._marginX

    @marginX.setter
    def marginX(self, amt=0):
        self._marginX = amt

    @property
    def marginY(self):
        self._marginY -= self.yAmt
        return self._marginY

    # @marginY.setter
    # def marginY(self, amt=0):
    #     self._marginY = amt


    def loadGui(self):
        self.xAmt = 0
        self.yAmt = 0.8
        self.cosmeticTypesFrame = DirectFrame(
            parent = self,
            pos = (-1.55, 0, 0.8),
            scale = 0.15,
            frameColor = (40/255, 40/255, 40/255, 1),
            frameSize = (-1, 1, -3.5, 1),
        )

        self.cosmeticTypesGui = {
            "btn_clothing": DirectButton(
                parent = self.cosmeticTypesFrame,
                text = ("Clothing"),
                scale = 0.3, pos = (0, 0, self.marginY),
                command = self.toggleClothingGui,
            ),
            "btn_hat": DirectButton(
                parent = self.cosmeticTypesFrame,
                text = ("Hat"),
                scale = 0.3, pos = (0, 0, self.marginY),
                command = self.toggleAccessoryGui,
                extraArgs = ['hat']
            ),
            "btn_glasses": DirectButton(
                parent = self.cosmeticTypesFrame,
                text = ("Glasses"),
                scale = 0.3, pos = (0, 0, self.marginY),
                command = self.toggleAccessoryGui,
                extraArgs = ['glasses']
            ),
            "btn_backpack": DirectButton(
                parent = self.cosmeticTypesFrame,
                text = ("Backpack"),
                scale = 0.3, pos = (0, 0, self.marginY),
                command = self.toggleAccessoryGui,
                extraArgs = ['backpack']
            ),
            "btn_shoes": DirectButton(
                parent = self.cosmeticTypesFrame,
                text = ("Shoes"),
                scale = 0.3, pos = (0, 0, self.marginY),
                command = self.toggleAccessoryGui,
                extraArgs = ['hat']
            ),
        }
        # self.activeGui.append(self.menuGui)

        self.clothingMenuFrame = DirectFrame(
            parent = self,
            pos = (-1.55, 0, -0.5),
            # scale = 0.15,
            frameColor = (40 / 255, 40 / 255, 40 / 255, 1),
            frameSize = (-0.2, 0.2, -0.2, 0.3),
            sortOrder=-1
        )
        self.yAmt = 0.1
        self._marginY = 0.25
        self.clothingGui = (
            DirectButton(
                parent = self.clothingMenuFrame,
                text = ("Change Top"),
                scale = 0.05, pos = (0, 0, self.marginY),
                command = self.previewer.applyClothingChange,
                extraArgs = ['torso-top']
            ),
            DirectButton(
                parent = self.clothingMenuFrame,
                text = ("Change Sleeve"),
                scale = 0.05, pos = (0, 0, self.marginY),
                command = self.previewer.applyClothingChange,
                extraArgs = ['sleeves']
            ),
            DirectButton(
                parent = self.clothingMenuFrame,
                text = ("Change Bottoms"),
                scale = 0.05, pos = (0, 0, self.marginY),
                command = self.previewer.applyClothingChange,
                extraArgs = ['torso-bot']
            ), # frameColor
            DirectButton(
                text = ("dogs"),
                scale = 0.05, pos = (1.6, 0, -0.4),
                command = self.previewer.setActiveBody,
                extraArgs = ['s']
            ),
            DirectButton(
                text = ("dogm"),
                scale = 0.05, pos = (1.6, 0, -0.5),
                command = self.previewer.setActiveBody,
                extraArgs = ['m']
            ),
            DirectButton(
                text = ("dogl"),
                scale = 0.05, pos = (1.6, 0, -0.6),
                command = self.previewer.setActiveBody,
                extraArgs = ['l']
            ),
            DirectButton(
                text = ("Change gender"),
                scale = 0.05, pos = (1.6, 0, -0.7),
                command = self.previewer.setActiveBody,
                extraArgs = [None, None, True]
            ),
        )

        self.yAmt = 0.1
        self._marginY = 0.25
        self.accessoryGui = (
            DirectButton(
                parent = self.clothingMenuFrame,
                text = ("Load Accessory"),
                scale = 0.05, pos = (0, 0, self.marginY),
                command = self.previewer.applyClothingChange,
                extraArgs = ['torso-top']
            ),
        )
        self.activeGui.append(self.clothingGui)

        self.hideActiveGui()

    @refresh_ui
    def toggleClothingGui(self):
        if self.clothingGuiEnabled:
            # Hide everything
            for button in self.clothingGui:
                button.hide()
            self.cosmeticTypesGui["btn_clothing"]["frameColor"] = (0.8, 0.8, 0.8, 1)
            self.cosmeticTypesGui["btn_clothing"]["state"] = "normal"
        else:
            for button in self.clothingGui:
                button.show()
            self.activeGui.append(self.clothingGui)
            self.previewer.viewBody(True)
            # frameColor
            self.cosmeticTypesGui["btn_clothing"]["frameColor"] = (0.5, 0.5, 0.5, 1)
            self.cosmeticTypesGui["btn_clothing"]["state"] = "disabled"

        self.clothingGuiEnabled = not self.clothingGuiEnabled
        # ?
        self.menuGuiVisible = False

    # old
    @refresh_ui
    def toggleAccessoryGui(self, accType):
        if not accType:
            for button in self.accessoryGui:
                button.hide()
            self.accessoryGuiEnabled = False
        # Disable it
        if self.clothingGuiEnabled:
            self.toggleClothingGui()
        if not self.accessoryGuiEnabled:
            for button in self.accessoryGui:
                button.show()
            self.activeGui.append(self.accessoryGui)
        self.changeAccessoryGui(accType)
        self.accessoryGuiEnabled = True

    @refresh_ui
    def changeAccessoryGui(self, accType):
        # Change between different accessory menus
        if self.previewer.activeAccessory and accType != self.previewer.activeAccessory.accessoryType:
            # hide old buttons
            for button in self.accessoryGui:
                button.hide()
            pass
        for button in self.accessoryGui:
            button.show()
        self.activeGui.append(self.accessoryGui)
        self.previewer.viewAccessory(accType)

    @refresh_ui
    def toggleMenuGui(self):
        if not self.menuGui:
            return
        if self.menuGuiVisible:
            for button in self.menuGui:
                button.hide()
        else:
            for button in self.menuGui:
                button.show()
            self.activeGui.append(self.menuGui)
            self.previewer.viewBody(False)

        self.menuGuiVisible = not self.menuGuiVisible
        self.clothingGuiEnabled = False

    def hideActiveGui(self):
        for guiSet in self.activeGui:
            for guiElement in guiSet:
                guiElement.hide()
        self.activeGui = []


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


class Accessory(Cosmetic):
    def __init__(self, baseNode):
        super().__init__(baseNode)
        self.accessoryType = None



class Clothing(Cosmetic):

    def __init__(self, baseNode):
        # for the associated node we can do self.bodyGroup for clothing
        # so that we can affect all of them at once if need be
        super().__init__(baseNode)
        self._loadedTexture = None

    # loadTexture overriden
    def loadTexture(self, textureFile):
        tex = super().loadTexture(textureFile)
        self._loadedTexture = tex
        return tex

    def setPartTexture(self, part=None, texture=None):
        if not part:
            part = self.targetNode
        if not texture:
            texture = self._loadedTexture
        for node in self.findAllMatches(f"**/{part}"):
            node.setTexture(texture, 1)





if __name__ == "__main__":
    CosmeticPreviewer()
    base.run()
