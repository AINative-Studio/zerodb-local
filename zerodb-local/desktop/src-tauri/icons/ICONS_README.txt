ZeroDB Desktop Icons
====================

This directory contains application icons for all platforms.

Required files (replace with real branding before shipping):

  icon.png          - 512x512 PNG, used as the base icon and tray icon on Linux/macOS
  32x32.png         - 32x32 PNG, referenced in tauri.conf.json bundle.icon array
  128x128.png       - 128x128 PNG
  128x128@2x.png    - 256x256 PNG (2x DPI)
  icon.ico          - Windows multi-resolution ICO (16/32/48/256 px)
  icon.icns         - macOS ICNS bundle (29/40/58/76/80/87/128/256/512/1024 px)

Generating icons from a master PNG
-----------------------------------
Install the Tauri CLI icon generator:

  npx @tauri-apps/cli icon icon-source-1024.png

This command reads a 1024x1024 PNG and writes all required sizes to this
directory automatically.

Placeholder generation (development only):
  brew install imagemagick
  magick -size 512x512 xc:'#0e1117' -fill '#22c55e' \
    -draw 'ellipse 256,180 160,50 0,360' \
    -draw 'path "M96,180 Q96,240 256,260 Q416,240 416,180"' \
    -draw 'path "M96,240 Q96,300 256,320 Q416,300 416,240"' \
    -draw 'path "M96,300 Q96,360 256,380 Q416,360 416,300"' \
    icon.png
