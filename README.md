# BRef — Minimalistic Reference Addon for Blender 4.4

**BRef** is a clean and lightweight addon for managing reference images directly inside the 3D viewport or the scene itself.  
Simple, fast, and built for Blender 4.4+.

[Overview](https://www.youtube.com/watch?v=AuOg3q7NcFc)

## Features

### 🖼️ Viewport Overlay Reference Images
- Add image references as draggable overlays directly in the 3D viewport.
- Support for multiple images with independent:
  - Size
  - Position (X, Y)
  - Opacity (Alpha)
  - Flip (X/Y)
  - Maintain aspect ratio
- Drag and resize interactively in **"Drag Mode"** (K key to resize or corner handles).
- Layer system to organize references.
- Show all layers toggle.
- Smart Arrange tool to auto-layout images cleanly.
- Center selected image to viewport.
- Grid snapping (with customizable grid size and color).

---

### 🧭 Orthographic Reference Images
- Enable reference images in 6 orthographic directions:
  - Front / Back / Left / Right / Up / Down
- Each with individual:
  - File path
  - Size
  - Opacity
- Automatically placed as `Empty` objects in 3D view.
- Spawn or clear all orthographic references with one click.

---

### 🧰 UI Integration & Custom Panel
- Custom **"BRef"** tab in the 3D View Sidebar.
- Organized sections for overlay and orthographic images.
- Interactive list UI for managing references.
- Fully integrated with Blender's property and operator system.

---

## Controls

| Action                | Shortcut |
|------------------------|----------|
| Enter/Exit Drag Mode   | Click "Enter Drag Mode" or use Right Mouse / ESC |
| Move Image             | Left Click and Drag |
| Resize Image           | Drag the Image from Right Top Corner or K |
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

