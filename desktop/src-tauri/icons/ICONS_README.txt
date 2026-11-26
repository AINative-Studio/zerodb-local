ZeroDB Desktop Icons
====================

This directory contains application icons for all platforms.

Files:

  app-icon-1024.png - 1024x1024 master, the real ZeroDB brand mark (the
                      block-letter Z from the brand system, Signal Cyan
                      on a dark tile -- same path data as IconMark in
                      ZeroDB.AINative.Studio's src/components/ZeroDBLogo.tsx
                      and the website's own app-icon route at src/app/icon.tsx)
  icon.png          - 512x512 PNG, used as the base icon and tray icon on Linux/macOS
  32x32.png         - 32x32 PNG, referenced in tauri.conf.json bundle.icon array
  128x128.png       - 128x128 PNG
  128x128@2x.png    - 256x256 PNG (2x DPI)
  icon.ico          - Windows multi-resolution ICO (16/32/48/256 px)
  icon.icns         - macOS ICNS bundle (29/40/58/76/80/87/128/256/512/1024 px)

Regenerating icons from the master PNG
---------------------------------------
If the brand mark changes, regenerate every size with the Tauri CLI icon
generator, run from desktop/:

  npx @tauri-apps/cli icon src-tauri/icons/app-icon-1024.png -o src-tauri/icons

This reads the 1024x1024 master and overwrites every size in this directory.
