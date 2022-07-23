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
import bpy, os, json

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

    selected: BoolProperty(
        name="Only Selected",
        description="Whether to only export selected objects.",
        default=False
    )

# OPERATORS (Main Script)


def showmessagebox(message="", title="Message Box", icon='INFO'):
    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def getabsfilename(default: str, path: str):
    filename = default

    if (os.path.isabs(path)):
        filename = path
    else:
        if (path != ""):
            filename = path
        filename += ".json"
        filename = os.path.join(bpy.path.abspath("//"), filename)

    return filename


class BlenderToJSON(Operator):
    bl_label = "Export"
    bl_idname = "rm.exporter"
    bl_description = "Export to JSON"

    def execute(self, context):
        scene = context.scene
        paneldata = scene.paneldata
        filename = getabsfilename(scene.name, paneldata.filename)
        output = {
            "cubes": []
        }

        if (paneldata.selected == False):
            bpy.ops.object.select_all(action='SELECT')

        selection = bpy.context.selected_objects
        
        for obj in selection:
            cube = {}
            cube["name"] = obj.name

            output["cubes"].append(cube)

        file = open(filename, "w")
        file.write(json.dumps(output))
        file.close()

        showmessagebox("Export completed", "Export", 'EXPORT')
        return {'FINISHED'}

# PANEL


class ExporterPanel(Panel):
    bl_label = "ReMapper Blender Exporter"
    bl_idname = "OBJECT_PT_CustomPanel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "RM Exporter"

    @classmethod
    def poll(self, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        paneldata = scene.paneldata

        layout.prop(paneldata, "filename")
        layout.prop(paneldata, "animations")
        layout.prop(paneldata, "selected")
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

    bpy.types.Scene.paneldata = PointerProperty(type=ExporterProperties)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Scene.paneldata


if __name__ == "__main__":
    register()