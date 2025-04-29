# BRef — Minimalistic Reference Addon for Blender 4.4

**BRef** is a clean and lightweight addon for managing reference images directly inside the 3D viewport or the scene itself.  
Simple, fast, and built for Blender 4.4+.

[Overview](https://www.youtube.com/watch?v=AuOg3q7NcFc)

## Features

**Viewport Overlay Images**
- Add any image into the 3D Viewport, floating on top of everything else.
- Drag images freely with mouse in "Drag Mode."
- Resize easily while dragging (hold `K` key to resize).
- Lock aspect ratio if needed.
- Organize images by layers. Choose to view only the active layer or all layers.
- Adjust each image's opacity.
- Flip images horizontally or vertically.
- Quickly center images with one click.
- Manage images through a clean list inside the Sidebar.

**Orthographic Scene References**
- Load images into the 3D scene using Blender Empties.
- Automatically place references for Front, Back, Left, Right, Top, and Bottom views.
- Adjust size, distance from origin, and transparency per view.
- Update or clear all ortho references with one button.
- No manual positioning needed — BRef handles rotation and placement automatically.

**UI**
- Fully integrated into the Sidebar under the "BRef" tab.
- Minimal and clean panels, easy to understand at a glance.
- "Drag Mode" toggle with helpful instructions at the bottom.

---

## Controls

| Action                | Shortcut |
|------------------------|----------|
| Enter/Exit Drag Mode   | Click "Enter Drag Mode" or use Right Mouse / ESC |
| Move Image             | Left Click and Drag |
| Resize Image           | Hold `K` key while dragging |
| Center Selected Image  | Button in Sidebar |

---

## Installation

1. Download the `bref.py` file.
2. Open Blender, go to **Edit > Preferences > Add-ons**.
3. Click **Install**, select the `bref.py` file.
4. Enable "BRef" in the Add-ons list.
5. Open the Sidebar (press `N` in 3D Viewport), and find the **BRef** tab.

---

## Requirements

- Blender **4.4.0** or newer.

---

## Notes

- Orthographic references are scene objects and will be saved with your `.blend` file.
- Viewport overlays are temporary and meant mainly for workflow, not final renders.
- Works best with Image Editor-friendly formats like PNG or JPEG.
  
## Support

If you find BRef useful, you can support its development here:

- [Buy Me a Coffee](https://www.buymeacoffee.com/verlorengest)
- [Gumroad - BRef](https://kaansoyler.gumroad.com/l/BRef)

Thanks for your support!

