@echo off
setlocal enabledelayedexpansion
set img=none
for %%x in (*.png) do (
    set img=%%~x
    echo !img!
    magick convert !img! -trim  !img!
)

