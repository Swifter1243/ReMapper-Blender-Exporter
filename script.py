from bpy.props import (StringProperty,
                       IntProperty,
                       FloatProperty,
                       PointerProperty,
                       EnumProperty,
                       BoolProperty,
                       )
from bpy.types import (Panel,
                       PropertyGroup,
                       Operator,
                       )
import bpy

bl_info = {
    "name": "ReMapper Exporter",
    "author": "Swifter",
    "version": "0.01",
    "blender": (2, 80, 0),
    "location": "View3d > Sidepanel",
    "description": "Blender Plugin to export scenes into models which are used by ReMapper."
}

# PANEL VARIABLES


class ExporterProperties(PropertyGroup):
    filename: StringProperty(
        name="File Name",
        description="The file to export this model to. Defaults to scene name.",
        default=""
    )

    animations: BoolProperty(
        name="Export Animations",
        description="Whether animations will be exported.",
        default=True
    )

# OPERATORS (Main Script)


def ShowMessageBox(message="", title="Message Box", icon='INFO'):
    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


class BlenderToJSON(Operator):
    bl_label = "Export"
    bl_idname = "rm.exporter"
    bl_description = "Export to JSON"

    def execute(self, context):
        ShowMessageBox("Export completed", "Export", 'EXPORT')
        return {'FINISHED'}

# PANEL


class ExporterPanel(Panel):
    bl_label = "ReMapper Blender Exporter"
    bl_idname = "OBJECT_PT_CustomPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool

        layout.prop(mytool, "filename")
        layout.prop(mytool, "animations")
        layout.operator("rm.exporter")


# REGISTRY


classes = (
    ExporterProperties,
    BlenderToJSON,
    ExporterPanel
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.my_tool = PointerProperty(type=ExporterProperties)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Scene.my_tool


if __name__ == "__main__":
    register()
