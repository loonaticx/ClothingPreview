# Clothing Render / Previewer

## Usage
You can load in shirt, sleeve, and short/skirt textures and take transparent render screenshots
to use for graphic design/promotional purposes.

If you actually use this script, it might yell at you for missing textures. They don't really matter much.

## Instructions
In order to launch this script on Windows, you can just double-click "run.bat". Alternatively, you can run it using ``python preview.py``
You will need to have Panda3D installed in order to run this script.

If you get an error saying that a panda3d module cannot be found/loaded, you should probably edit the ``run.bat`` script and point the python.exe to Panda.
Ex:
Replace ``python preview.py`` with ``C:\Panda3D-1.11.0\python\python.exe preview.py``


## Cropping Images
Upon taking a screenshot, you will notice that there is a lot of leftover whitespace in the image.

``CropImages.bat`` is a handy  utility tool that you can use to automatically trim out all of the unused space in the renders.
In order to use this script, you will need to download the [ImageMagick SDK](https://imagemagick.org/) ([Mirror](https://github.com/ImageMagick/ImageMagick/releases))


## Controls

Key | Usage
------------ | -------------
s | Take screenshot
o | toggle oobe/free camera
r | reload loaded textures
e | reset rotation
1 | toggle shirt
2 | toggle bottoms
3 | load dogs body
4 | load dogm body
5 | load dogl body
mouse wheel up | zoom in
mouse wheel down | zoom out
mouse3 | reset zoom
left arrow | rotate negative heading
right arrow | rotate positive heading
up arrow | rotate positive pitch
down arrow | rotate negative pitch

## Todo

- Add onscreen text that displays the offset (camers zoom, clothing rotation, etc.) <-- will be hidden in screenshots