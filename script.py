import math
from typing import List
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
                       Object,
                       Context
                       )
import bpy
import os
import json

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
        filename += ".rmmodel"
        filename = os.path.join(bpy.path.abspath("//"), filename)

    return filename


def tolist(inputarr, callback=None):
    arr = []
    for i in inputarr:
        if (callback != None):
            i = callback(i)
        arr.append(i)
    return arr


def processtransform(pos: List, rot: List, scale: List):
    outputjson = {
        "pos": tolist(pos, lambda x: math.fabs(x)),
        "rot": tolist(rot, lambda x: math.degrees(math.fabs(x))),
        "scale": tolist(scale, lambda x: math.fabs(x))
    }

    jsonpos = outputjson["pos"]
    outputjson["pos"] = [jsonpos[0], jsonpos[2], jsonpos[1]]

    return outputjson


def getjsonfromobject(obj: Object, animations=True, framespan=[0, 0]):
    # TODO: Make this work for parenting stuff too. This is just rough testing for now
    objjson = processtransform(obj.location, obj.rotation_euler, obj.scale)

    if (obj.material_slots):
        objjson["track"] = obj.material_slots[0].material.name
        if (len(obj.material_slots) > 1):
            objjson["color"] = tolist(
                obj.material_slots[1].material.node_tree.nodes["Principled BSDF"].inputs[0].default_value)

    return objjson


class BlenderToJSON(Operator):
    bl_label = "Export"
    bl_idname = "rm.exporter"
    bl_description = "Export to JSON"

    def execute(self, context):
        scene = context.scene
        paneldata = scene.paneldata
        filename = getabsfilename(scene.name, paneldata.filename)
        output = {
            "objects": []
        }

        objects = bpy.context.scene.objects

        if len(bpy.context.selected_objects) != 0:
            objects = bpy.context.selected_objects

        for obj in objects:
            objjson = getjsonfromobject(obj, paneldata.animations)
            output["objects"].append(objjson)

        file = open(filename, "w")
        file.write(json.dumps(output, indent=2))
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
