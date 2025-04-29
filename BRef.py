
bl_info = {
    "name":        "BRef",
    "author":      "Kaan Soyler",
    "maintainer":  "Kaan Soyler",
    "version":     (1, 4, 0),
    "blender":     (4, 4, 0),
    "location":    "View 3D ▸ Sidebar ▸ BRef",
    "description": "Minimalistic Reference Addon in Blender! Add References in the viewport or directly in the 3‑D scene.",
    "doc_url":     "https://github.com/verlorengest/BRef",
    "category":    "UI",
}

# ─────────────────────────────────────────────────────────────────────────────
# Imports
# ─────────────────────────────────────────────────────────────────────────────
import bpy, gpu, os, blf, math
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

# ─────────────────────────────────────────────────────────────────────────────
# Globals
# ─────────────────────────────────────────────────────────────────────────────
_shader, _tex_cache, _handle = None, {}, None
_theme_colors = {}

DEFAULT_ORTHO_OFFSET = 30.0

_ORTHO_EMPTY_NAMES = {
    "FRONT":  "BRef_ORTHO_FRONT",
    "BACK":   "BRef_ORTHO_BACK",
    "LEFT":   "BRef_ORTHO_LEFT",
    "RIGHT":  "BRef_ORTHO_RIGHT",
    "UP":     "BRef_ORTHO_UP",
    "DOWN":   "BRef_ORTHO_DOWN",
}

# Euler XYZ rotations
_ORTHO_DATA = {
    "FRONT":  {"rot": (math.radians(90), 0, 0),                 "loc": lambda d: (0, -d, 0)},
    "BACK":   {"rot": (math.radians(90), 0, math.radians(180)), "loc": lambda d: (0,  d, 0)},
    "RIGHT":  {"rot": (math.radians(90), 0, math.radians(-90)), "loc": lambda d: (-d, 0, 0)},
    "LEFT":   {"rot": (math.radians(90), 0, math.radians(90)),  "loc": lambda d: ( d, 0, 0)},
    "UP":     {"rot": (0, 0, 0),                                "loc": lambda d: (0, 0,  d)},
    "DOWN":   {"rot": (math.radians(180), 0, 0),                "loc": lambda d: (0, 0, -d)},
}


# ── Per-view settings for ortho refs ───────────────────────────────────
class OrthoImageSettings(bpy.types.PropertyGroup):
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    alpha:    bpy.props.FloatProperty(name="Alpha", default=1.0, min=0.0, max=1.0)
    size:     bpy.props.FloatProperty(name="Size",  default=20.0, min=0.01)

# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def shader():
    global _shader
    if _shader is None:
        _shader = gpu.shader.from_builtin('IMAGE_COLOR')
    return _shader


def redraw(ctx):
    """Tag all 3‑D viewports for redraw"""
    for w in ctx.window_manager.windows:
        for a in w.screen.areas:
            if a.type == 'VIEW_3D':
                a.tag_redraw()


def get_theme_color(ctx, category, value):
    """Fetch a UI‑theme color once, then cache it"""
    key = f"{category}.{value}"
    if key not in _theme_colors:
        try:
            theme = ctx.preferences.themes[0]
            cat   = getattr(theme, category)
            _theme_colors[key] = getattr(cat, value)
        except Exception:
            _theme_colors[key] = (0.5, 0.5, 0.5, 1.0)  # Fallback grey
    return _theme_colors[key]

# ─────────────────────────────────────────────────────────────────────────────
# Property‑groups
# ─────────────────────────────────────────────────────────────────────────────

def _cb_size(self, ctx):
    if self.width and self.height:
        ratio = self.height / self.width
        self.width  = self.size
        self.height = self.size * ratio
        redraw(ctx)


def _cb_dims(self, ctx):
    redraw(ctx)


class DraggableImage(bpy.types.PropertyGroup):
    """Meta‑data for each viewport overlay image"""

    filepath: bpy.props.StringProperty(subtype='FILE_PATH', update=lambda s, c: redraw(c))
    x:        bpy.props.FloatProperty(default=100.0, update=lambda s, c: redraw(c))
    y:        bpy.props.FloatProperty(default=100.0, update=lambda s, c: redraw(c))
    size:     bpy.props.FloatProperty(name="Size",   default=200.0, min=10.0, update=_cb_size)
    width:    bpy.props.FloatProperty(default=200.0, min=10.0, update=_cb_dims)
    height:   bpy.props.FloatProperty(default=200.0, min=10.0, update=_cb_dims)
    maintain_aspect: bpy.props.BoolProperty(default=True)
    alpha:    bpy.props.FloatProperty(default=1.0, min=0.0, max=1.0, update=lambda s, c: redraw(c))
    layer:    bpy.props.IntProperty(default=0, update=lambda s, c: redraw(c))
    flip_x:   bpy.props.BoolProperty(default=False, update=lambda s, c: redraw(c))
    flip_y:   bpy.props.BoolProperty(default=False, update=lambda s, c: redraw(c))


# ── Property group for scene-level ortho refs ───────────────────────────
class OrthographicReferences(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(name="Enable Orthographic References", default=False)
    offset:  bpy.props.FloatProperty(name="Distance", default=DEFAULT_ORTHO_OFFSET, min=0.0)

    front:  bpy.props.PointerProperty(type=OrthoImageSettings)
    back:   bpy.props.PointerProperty(type=OrthoImageSettings)
    left:   bpy.props.PointerProperty(type=OrthoImageSettings)
    right:  bpy.props.PointerProperty(type=OrthoImageSettings)
    up:     bpy.props.PointerProperty(type=OrthoImageSettings)
    down:   bpy.props.PointerProperty(type=OrthoImageSettings)





# ─────────────────────────────────────────────────────────────────────────────
# Overlay helpers
# ─────────────────────────────────────────────────────────────────────────────

def _inside(p, it):
    return it.x <= p.x <= it.x + it.width and it.y <= p.y <= it.y + it.height


def _corner(p, it):
    corner_size = 30  # Size of the corner clickable area

    # Check all four corners
    # Bottom-right corner
    if (it.x + it.width - corner_size <= p.x <= it.x + it.width) and \
            (it.y + it.height - corner_size <= p.y <= it.y + it.height):
        return True

    # Bottom-left corner
    if (it.x <= p.x <= it.x + corner_size) and \
            (it.y + it.height - corner_size <= p.y <= it.y + it.height):
        return True

    # Top-right corner
    if (it.x + it.width - corner_size <= p.x <= it.x + it.width) and \
            (it.y <= p.y <= it.y + corner_size):
        return True

    # Top-left corner
    if (it.x <= p.x <= it.x + corner_size) and \
            (it.y <= p.y <= it.y + corner_size):
        return True

    return False

# ─────────────────────────────────────────────────────────────────────────────
# Orthographic Operators
# ─────────────────────────────────────────────────────────────────────────────



# ── Operator to spawn / update ortho refs ───────────────────────────────
class ORTHO_OT_spawn_references(bpy.types.Operator):
    bl_idname = "bref.spawn_ortho_refs"
    bl_label  = "Spawn / Update Ortho Refs"

    def execute(self, ctx):
        ortho = ctx.scene.ortho_refs
        if not ortho.enabled:
            self.report({'INFO'}, "Orthographic references are disabled.")
            return {'CANCELLED'}

        made = 0
        for key, obj_name in _ORTHO_EMPTY_NAMES.items():
            settings = getattr(ortho, key.lower())      # OrthoImageSettings
            if not settings.filepath:
                if (obj := bpy.data.objects.get(obj_name)):
                    bpy.data.objects.remove(obj, do_unlink=True)
                continue

            try:
                img = bpy.data.images.load(settings.filepath, check_existing=True)
            except Exception as e:
                self.report({'WARNING'}, f"Failed to load {settings.filepath}: {e}")
                continue

            # get or create empty
            obj = bpy.data.objects.get(obj_name) or bpy.data.objects.new(obj_name, None)
            if obj.name not in ctx.collection.objects:
                ctx.collection.objects.link(obj)

            obj.empty_display_type = 'IMAGE'
            obj.empty_image_depth  = 'FRONT'
            obj.data               = img
            obj.rotation_euler     = _ORTHO_DATA[key]["rot"]
            obj.location           = _ORTHO_DATA[key]["loc"](ortho.offset)
            obj.empty_display_size = settings.size

            if hasattr(obj, "empty_image_opacity"):
                obj.empty_image_opacity = settings.alpha
            else:
                obj.color = (1, 1, 1, settings.alpha)

            made += 1

        self.report({'INFO'}, f"{made} orthographic reference(s) active.")
        return {'FINISHED'}




class ORTHO_OT_clear_references(bpy.types.Operator):
    bl_idname      = "bref.clear_ortho_refs"
    bl_label       = "Clear Ortho Refs"
    bl_description = "Delete all orthographic reference empties created by BRef"

    def execute(self, _):
        removed = 0
        for name in _ORTHO_EMPTY_NAMES.values():
            obj = bpy.data.objects.get(name)
            if obj:
                bpy.data.objects.remove(obj, do_unlink=True)
                removed += 1
        self.report({'INFO'}, f"Removed {removed} orthographic reference(s).")
        return {'FINISHED'}

# ─────────────────────────────────────────────────────────────────────────────
# UIList – draggable overlay list
# ─────────────────────────────────────────────────────────────────────────────

class IMAGE_UL_draggable(bpy.types.UIList):
    def draw_item(self, _, layout, __, it, ___, ____, _____, ______):
        row = layout.row(align=True)
        row.prop(it, "layer", text="", emboss=True)
        row.prop(it, "alpha", text="", slider=True)
        filename = os.path.basename(it.filepath) or "⟡"
        row.label(text=filename, icon='IMAGE_DATA')

# ─────────────────────────────────────────────────────────────────────────────
# Overlay Operators
# ─────────────────────────────────────────────────────────────────────────────

class IMAGE_OT_add(bpy.types.Operator):
    bl_idname = "image.add_draggable"
    bl_label  = "Add Reference Image"
    filepath: bpy.props.StringProperty(subtype='FILE_PATH')

    def execute(self, ctx):
        col, it = ctx.scene.draggable_images, ctx.scene.draggable_images.add()
        it.filepath, it.layer = self.filepath, len(col) - 1
        try:
            img = bpy.data.images.load(self.filepath, check_existing=True)
            _tex_cache[self.filepath] = (img, gpu.texture.from_image(img))
            it.width, it.height = img.size[0] / 2, img.size[1] / 2    # ½-size
            it.size = max(it.width, it.height)
        except Exception as e:
            self.report({'ERROR'}, str(e)); col.remove(len(col) - 1)
            return {'CANCELLED'}
        ctx.scene.drag_img_index = len(col) - 1
        redraw(ctx); return {'FINISHED'}

    def invoke(self, ctx, _):
        ctx.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class IMAGE_OT_remove(bpy.types.Operator):
    bl_idname, bl_label = "image.remove_draggable", "Remove Image"
    @classmethod
    def poll(cls, ctx): return bool(ctx.scene.draggable_images)
    def execute(self, ctx):
        idx, col = ctx.scene.drag_img_index, ctx.scene.draggable_images
        if 0 <= idx < len(col):
            fp = col[idx].filepath
            if fp in _tex_cache:
                try: _tex_cache[fp][1].release()
                except: pass
                del _tex_cache[fp]
            col.remove(idx)
            ctx.scene.drag_img_index = max(0, min(idx, len(col) - 1))
            redraw(ctx)
        return {'FINISHED'}

class IMAGE_OT_move_layer(bpy.types.Operator):
    bl_idname, bl_label = "image.move_draggable_layer", "Move Layer"
    direction: bpy.props.EnumProperty(items=[("UP","Up",""),("DOWN","Down","")])
    @classmethod
    def poll(cls, ctx): return bool(ctx.scene.draggable_images)
    def execute(self, ctx):
        it = ctx.scene.draggable_images[ctx.scene.drag_img_index]
        it.layer = it.layer + 1 if self.direction == 'UP' else max(0, it.layer - 1)
        redraw(ctx); return {'FINISHED'}

class IMAGE_OT_reset_position(bpy.types.Operator):
    bl_idname, bl_label = "image.reset_draggable_position", "Center Image"
    @classmethod
    def poll(cls, ctx):
        return ctx.scene.draggable_images and 0 <= ctx.scene.drag_img_index < len(ctx.scene.draggable_images)
    def execute(self, ctx):
        reg = next((r for a in ctx.screen.areas if a.type == 'VIEW_3D'
                    for r in a.regions if r.type == 'WINDOW'), None)
        if reg:
            it = ctx.scene.draggable_images[ctx.scene.drag_img_index]
            it.x, it.y = reg.width / 2 - it.width / 2, reg.height / 2 - it.height / 2
            redraw(ctx)
        return {'FINISHED'}

# ─────────────────────────────────────────────────────────────────────────────
# Drag / resize modal
# ─────────────────────────────────────────────────────────────────────────────
class VIEW3D_OT_drag_images(bpy.types.Operator):
    bl_idname, bl_label = "view3d.drag_images", "Drag Images"
    bl_options = {'REGISTER', 'UNDO'}

    _active = False
    _idx = -1
    _resize, _k_hold = False, False
    _offset = Vector((0, 0))
    _sm = Vector((0, 0))
    _sw = _sh = _ratio = 0.0

    @classmethod
    def poll(cls, ctx):
        return not cls._active and ctx.area.type == 'VIEW_3D' and ctx.scene.draggable_images

    def modal(self, ctx, event):
        scn, col = ctx.scene, ctx.scene.draggable_images
        m = Vector((event.mouse_region_x, event.mouse_region_y))
        show_all = scn.bref_show_all_layers
        active_layer = col[scn.drag_img_index].layer if col and 0 <= scn.drag_img_index < len(col) else 0

        # Allow interaction with UI
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Check if mouse is over UI region
            for region in ctx.area.regions:
                if region.type == 'UI':
                    if (region.x <= event.mouse_x <= region.x + region.width and
                            region.y <= event.mouse_y <= region.y + region.height):
                        return {'PASS_THROUGH'}

        if event.type == 'K':
            self._k_hold = (event.value == 'PRESS')
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE' and self._idx != -1:
            it = col[self._idx]
            if self._resize:
                dx, dy = m.x - self._sm.x, m.y - self._sm.y
                w, h = self._sw + dx, self._sh + dy
                if it.maintain_aspect and self._ratio:
                    if abs(dx) > abs(dy):
                        h = w / self._ratio
                    else:
                        w = h * self._ratio
                it.width, it.height = max(10, w), max(10, h)
                it.size = max(it.width, it.height)
            else:
                it.x, it.y = m.x - self._offset.x, m.y - self._offset.y
            redraw(ctx)
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Filter items based on visibility settings
            visible_items = [
                (i, it) for i, it in enumerate(col)
                if show_all or it.layer == active_layer
            ]

            # Sort by layer so top layers get priority
            visible_items.sort(key=lambda x: x[1].layer, reverse=True)

            for i, it in visible_items:
                if _corner(m, it) or self._k_hold:
                    self._idx, self._resize = i, True
                    self._sm, self._sw, self._sh = m.copy(), it.width, it.height
                    self._ratio, scn.drag_img_index = it.width / it.height if it.height else 1, i
                    return {'RUNNING_MODAL'}
                if _inside(m, it):
                    self._idx, self._resize = i, False
                    self._offset = m - Vector((it.x, it.y))
                    scn.drag_img_index = i
                    return {'RUNNING_MODAL'}
            return {'PASS_THROUGH'}

        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            self._idx, self._resize = -1, False
            return {'RUNNING_MODAL'}

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.__class__._active = False
            return {'CANCELLED'}

        # Allow UI interaction for other events
        return {'PASS_THROUGH'}

    def invoke(self, ctx, _):
        self.__class__._active = True
        self._idx = -1
        self._resize = self._k_hold = False
        ctx.window_manager.modal_handler_add(self)
        self.report({'INFO'}, "Drag Mode — RMB/ESC exit • K resize • Drag corners to resize")
        return {'RUNNING_MODAL'}


# ─────────────────────────────────────────────────────────────────────────────
# Panel
# ─────────────────────────────────────────────────────────────────────────────

class VIEW3D_PT_bref_panel(bpy.types.Panel):
    bl_idname      = "VIEW3D_PT_bref_panel"
    bl_label       = "BRef"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category    = "BRef"
    bl_options     = {'DEFAULT_CLOSED'}

    def draw_header(self, _):
        self.layout.label(text="", icon='IMAGE_REFERENCE')

    def draw(self, ctx):
        lay, scn = self.layout, ctx.scene

        # ───── Overlay image manager  ─────

        header = lay.row(align=True)
        header.label(text="Reference Manager", icon='OUTLINER')
        header.label(text="v1.4.0", icon='INFO')

        # VISIBILITY TOGGLE
        vis_box = lay.box()
        vis_row = vis_box.row(align=True)
        vis_row.prop(scn, "bref_show_all_layers", text="Show All Layers", icon='RESTRICT_VIEW_OFF' if scn.bref_show_all_layers else 'RESTRICT_VIEW_ON')

        # IMAGE LIST
        list_box = lay.box()
        list_box.label(text="Viewport Reference Images", icon='IMAGE_DATA')
        row = list_box.row()
        row.template_list("IMAGE_UL_draggable", "", scn, "draggable_images", scn, "drag_img_index", rows=6)
        col = row.column(align=True)
        col.operator("image.add_draggable", icon='ADD', text="")
        col.operator("image.remove_draggable", icon='REMOVE', text="")
        col.separator()
        col.operator("image.move_draggable_layer", icon='TRIA_UP', text="").direction = "UP"
        col.operator("image.move_draggable_layer", icon='TRIA_DOWN', text="").direction = "DOWN"
        col.separator()
        col.operator("image.reset_draggable_position", icon='PIVOT_ACTIVE', text="")

        # DRAG MODE
        drag_box = lay.box()
        if VIEW3D_OT_drag_images._active:
            drag_row = drag_box.row(align=True)
            drag_row.alert = True
            drag_row.operator("view3d.drag_images", text="Exit Drag Mode", icon='CANCEL')
            instr_box = lay.box()
            instr_row = instr_box.row(align=True)
            instr_row.label(text="RMB/ESC: Exit", icon='MOUSE_RMB')
            instr_row.label(text="Resize: Hold K or Drag Top Right Corner",   icon='FULLSCREEN_ENTER')
        else:
            drag_box.operator("view3d.drag_images", text="Enter Drag Mode", icon='HAND')

        if scn.draggable_images and 0 <= scn.drag_img_index < len(scn.draggable_images):
            it = scn.draggable_images[scn.drag_img_index]
            box = lay.box()
            box.label(text="Selected Image", icon='BORDERMOVE')
            split = box.split(factor=0.5)
            size_col = split.column()
            size_col.label(text="Size", icon='FULLSCREEN_ENTER')
            size_col.prop(it, "size", text="")
            pos_col = split.column()
            pos_col.label(text="Position", icon='ORIENTATION_GLOBAL')
            pos_row = pos_col.row(align=True)
            pos_row.prop(it, "x", text="X")
            pos_row.prop(it, "y", text="Y")
            box.separator()
            dim_box = box.box()
            dim_box.label(text="Dimensions", icon='DRIVER_DISTANCE')
            dim_row = dim_box.row(align=True)
            dim_row.prop(it, "width", text="W")
            dim_row.prop(it, "height", text="H")
            dim_box.prop(it, "maintain_aspect", icon='LOOP_BACK')
            transform_box = box.box()
            transform_box.label(text="Transforms", icon='ORIENTATION_VIEW')
            flip_row = transform_box.row(align=True)
            flip_row.prop(it, "flip_x", text="Flip X", toggle=True, icon='MOD_MIRROR')
            flip_row.prop(it, "flip_y", text="Flip Y", toggle=True, icon='MOD_MIRROR')
            control_box = box.box()
            control_box.label(text="Appearance", icon='SETTINGS')
            control_box.prop(it, "alpha", slider=True, text="Opacity")
            box.separator()
            box.operator("image.reset_draggable_position", icon='PIVOT_ACTIVE', text="Center Image")

        # ───── ORTHOGRAPHIC  ─────
        ortho = scn.ortho_refs
        ortho_box = lay.box()
        ortho_box.label(text="Orthographic References", icon='AXIS_TOP')
        ortho_box.prop(ortho, "enabled", text="Enable", toggle=True)
        if ortho.enabled:
            # distance slider (± offset from origin)
            ortho_box.prop(ortho, "offset", text="Distance")

            # helper to draw one view’s controls
            def _draw_view(box, label, ref):
                row_box = box.box()
                row_box.label(text=label)
                row_box.prop(ref, "filepath", text="")
                r = row_box.row(align=True)
                r.prop(ref, "alpha", text="Alpha")
                r.prop(ref, "size",  text="Size")

            _draw_view(ortho_box, "Front",  ortho.front)
            _draw_view(ortho_box, "Back",   ortho.back)
            _draw_view(ortho_box, "Left",   ortho.left)
            _draw_view(ortho_box, "Right",  ortho.right)
            _draw_view(ortho_box, "Up",     ortho.up)
            _draw_view(ortho_box, "Down",   ortho.down)

            # existing buttons stay exactly as before
            op_row = ortho_box.row(align=True)
            op_row.operator("bref.spawn_ortho_refs", icon='IMAGE_REFERENCE')
            op_row.operator("bref.clear_ortho_refs", icon='TRASH')

# ─────────────────────────────────────────────────────────────────────────────
# Draw callback – viewport overlay images
# ─────────────────────────────────────────────────────────────────────────────


def draw_frame(x, y, w, h, color=(0.0, 1.0, 0.0, 0.8), thickness=2.0):
    """Draw a rectangular frame with the given parameters"""
    # Create vertices for the frame (as one continuous line)
    verts = [
        (x, y),  # Bottom-left
        (x + w, y),  # Bottom-right
        (x + w, y + h),  # Top-right
        (x, y + h),  # Top-left
        (x, y)  # Back to start
    ]

    # Create batch for line drawing
    line_shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
    batch = batch_for_shader(line_shader, 'LINE_STRIP', {"pos": verts})

    # Set line width and draw
    gpu.state.line_width_set(thickness)
    line_shader.bind()
    line_shader.uniform_float("color", color)
    batch.draw(line_shader)
    gpu.state.line_width_set(1.0)


def draw_corner_handle(x, y, size=20.0, color=(0.0, 1.0, 0.0, 1.0)):
    """Draw a visible corner resize handle"""
    # Draw a filled square for better visibility
    verts = [
        (x - size, y - size),  # Bottom-left
        (x, y - size),  # Bottom-right
        (x, y),  # Top-right
        (x - size, y)  # Top-left
    ]

    # Create batch for filled polygon
    fill_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(fill_shader, 'TRI_FAN', {"pos": verts})

    # Draw filled square
    fill_shader.bind()
    fill_shader.uniform_float("color", (color[0], color[1], color[2], 0.3))  # Semi-transparent
    batch.draw(fill_shader)

    # Draw outline
    line_verts = verts + [verts[0]]  # Close the loop
    line_shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
    line_batch = batch_for_shader(line_shader, 'LINE_STRIP', {"pos": line_verts})

    gpu.state.line_width_set(3.0)
    line_shader.bind()
    line_shader.uniform_float("color", color)
    line_batch.draw(line_shader)
    gpu.state.line_width_set(1.0)


# Then modify the draw_cb function to properly place the handles at each corner

def draw_cb():
    ctx = bpy.context
    scn, imgs = ctx.scene, ctx.scene.draggable_images
    if not imgs:
        return

    show_all = scn.bref_show_all_layers
    active_layer = imgs[scn.drag_img_index].layer if imgs and 0 <= scn.drag_img_index < len(imgs) else 0
    draw_list = [i for i in imgs if show_all or i.layer == active_layer]

    gpu.state.blend_set('ALPHA')
    for it in sorted(draw_list, key=lambda i: i.layer):
        fp = it.filepath
        if not fp:
            continue
        if fp not in _tex_cache:
            try:
                img = bpy.data.images.load(fp, check_existing=True)
            except Exception:
                continue
            _tex_cache[fp] = (img, gpu.texture.from_image(img))
        tex = _tex_cache[fp][1]

        x, y, w, h = it.x, it.y, it.width, it.height
        coords = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
        u0, u1 = (1, 0) if it.flip_x else (0, 1)
        v0, v1 = (1, 0) if it.flip_y else (0, 1)
        uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]

        batch = batch_for_shader(shader(), 'TRI_FAN', {"pos": coords, "texCoord": uvs})
        shader().bind()
        shader().uniform_float("color", (1, 1, 1, it.alpha))
        shader().uniform_sampler("image", tex)
        batch.draw(shader())

        # Draw frame and handles when in drag mode
        if VIEW3D_OT_drag_images._active:
            # Draw green frame
            draw_frame(x, y, w, h)

            # Draw corner handles at each corner
            draw_corner_handle(x + w, y + h)  # Bottom-right
            draw_corner_handle(x, y + h)  # Bottom-left
            draw_corner_handle(x + w, y)  # Top-right
            draw_corner_handle(x, y)  # Top-left

    gpu.state.blend_set('NONE')

    if VIEW3D_OT_drag_images._active:
        reg = ctx.region
        blf.size(0, 14, 72)
        blf.color(0, 0.0, 1.0, 0.0, 1.0)
        txt = "RMB / ESC exit • K resize • Drag green corners to resize"
        if not scn.bref_show_all_layers:
            txt += f" • Only layer {active_layer} visible"
        w, _ = blf.dimensions(0, txt)
        blf.position(0, reg.width - w - 15, 20, 0)
        blf.draw(0, txt)

# ─────────────────────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────────────────────

classes = (
    OrthoImageSettings,
    DraggableImage,
    OrthographicReferences,
    IMAGE_UL_draggable,

    IMAGE_OT_add,
    IMAGE_OT_remove,
    IMAGE_OT_move_layer,
    IMAGE_OT_reset_position,
    VIEW3D_OT_drag_images,

    ORTHO_OT_spawn_references,
    ORTHO_OT_clear_references,

    VIEW3D_PT_bref_panel,
)



def register():
    for c in classes:
        try:
            bpy.utils.register_class(c)
        except RuntimeError:
            pass

    bpy.types.Scene.draggable_images = bpy.props.CollectionProperty(type=DraggableImage)
    bpy.types.Scene.drag_img_index   = bpy.props.IntProperty()
    bpy.types.Scene.bref_show_all_layers = bpy.props.BoolProperty(
        name="Show All Layers",
        description="Display all layers instead of just the active one",
        default=True)

    bpy.types.Scene.ortho_refs = bpy.props.PointerProperty(type=OrthographicReferences)

    global _handle
    if _handle is None:
        _handle = bpy.types.SpaceView3D.draw_handler_add(draw_cb, (), 'WINDOW', 'POST_PIXEL')


def unregister():
    bpy.types.SpaceView3D.draw_handler_remove(_handle, 'WINDOW')
    for img, tex in _tex_cache.values():
        try:
            tex.release()
        except Exception:
            pass
    _tex_cache.clear()

    del bpy.types.Scene.draggable_images
    del bpy.types.Scene.drag_img_index
    del bpy.types.Scene.bref_show_all_layers
    del bpy.types.Scene.ortho_refs

    for c in reversed(classes):
        try:
            bpy.utils.unregister_class(c)
        except RuntimeError:
            pass


    for name in _ORTHO_EMPTY_NAMES.values():
        obj = bpy.data.objects.get(name)
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)


if __name__ == "__main__":
    register()

