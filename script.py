import math
from typing import List
from bpy.props import (StringProperty,
                       PointerProperty,
                       BoolProperty,
                       IntProperty
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

from mathutils import Euler, Matrix

bl_info = {
    "name": "ReMapper Exporter",
    "author": "Swifter",
    "version": "0.03",
    "blender": (2, 80, 0),
    "location": "View3d > Sidepanel",
    "description": "Blender Plugin to export scenes into models which are used by ReMapper."
}

# PANEL VARIABLES


class ExporterProperties(PropertyGroup):
    filename: StringProperty(
        name="File Name",
        description="The file to export this model to. Defaults to scene name",
        default=""
    )

    selected: BoolProperty(
        name="Only Selected",
        description="Export only selected objects.",
        default=False
    )

    animations: BoolProperty(
        name="Export Animations",
        description="Whether animations will be exported",
        default=True
    )

    samplerate: IntProperty(
        name="Sample Rate",
        description="The step of keyframe sampling",
        default=1,
        min=1
    )

# OPERATORS (Main Script)


def getabsfilename(default: str, path: str):
    filename = default
    if (path != ""):
        filename = path

    if (os.path.splitext(filename)[1] == ""):
        filename += ".rmmodel"

    if (os.path.abspath(filename)):
        filename = bpy.path.abspath("//") + filename

    return filename


def tolist(inputarr, callback=None):
    arr = []
    for i in inputarr:
        if (callback != None):
            i = callback(i)
        arr.append(i)
    return arr


def swapyz(arr: List):
    return [arr[0], arr[2], arr[1]]


RESIZEAMOUNT = 2


def processtransform(matrix: Matrix):
    transform = matrix.decompose()
    pos = transform[0]
    rot = transform[1]
    scale = transform[2]

    eul = Euler([0, 0, 0], "YXZ")
    eul.rotate(rot)
    rot = [eul.x, eul.y, eul.z]

    pos = swapyz(tolist(pos))
    rot = swapyz(tolist(rot, lambda x: -math.degrees(x)))
    scale = swapyz(tolist(scale, lambda x: math.fabs(x) * RESIZEAMOUNT))

    outputjson = {
        "pos": pos,
        "rot": rot,
        "scale": scale
    }

    return outputjson


def getjsonfromobject(obj: Object):
    objjson = processtransform(obj.matrix_world)

    objjson["color"] = tolist(obj.color)

    if (obj.material_slots):
        if (obj.material_slots[0] != None):
            if (obj.material_slots[0].material != None):
                objjson["track"] = obj.material_slots[0].material.name

    return objjson


def getobjects(context: Context):
    if context.scene.paneldata.selected:
        objects = context.selected_objects
    else:
        invisible: List[Object] = []

        for obj in context.scene.objects:
            if (obj.hide_get()):
                invisible.append(obj)
                obj.hide_set(False)

        objects = context.visible_objects

        for obj in invisible:
            obj.hide_set(True)

    filteredobjects: List[Object] = []

    for obj in objects:
        obj: Object
        if (obj.type == "MESH"):
            filteredobjects.append(obj)

    return filteredobjects


def gettime(start, dur, frame):
    return (frame - start) / dur


def pushkeyframe(matrix, time, lookup):
    transform = processtransform(matrix)

    transform["pos"].append(time)
    transform["rot"].append(time)
    transform["scale"].append(time)

    lookup["pos"].append(transform["pos"])
    lookup["rot"].append(transform["rot"])
    lookup["scale"].append(transform["scale"])

class ShowObjectColor(Operator):
    bl_label = "Show Object Color"
    bl_idname = "rm.showcolor"
    bl_description = "Switch displayed color to object. This is how the exporter exports colors"

    def execute(self, context):
        context.space_data.shading.color_type = "OBJECT"
        return {'FINISHED'}

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

        objects = getobjects(context)

        if (paneldata.animations):
            returnframe = scene.frame_current
            startframe = scene.frame_start
            endframe = scene.frame_end
            framedur = endframe - startframe

            objlookup = {}

            frame = startframe
            while (frame <= endframe):
                scene.frame_set(frame)
                time = gettime(startframe, framedur, frame)

                for obj in objects:
                    if (obj.name not in objlookup.keys()):
                        objlookup[obj.name] = {
                            "lastmatrix": obj.matrix_world.copy(),
                            "hasrested": False,
                            "data": getjsonfromobject(obj),
                            "pos": [],
                            "rot": [],
                            "scale": []
                        }

                    lookup = objlookup[obj.name]

                    if (lookup["lastmatrix"] == obj.matrix_world):
                        lookup["hasrested"] = True
                    else:
                        if (lookup["hasrested"]):
                            holdtime = gettime(
                                startframe, framedur, frame - 1)
                            pushkeyframe(
                                lookup["lastmatrix"], holdtime, lookup)

                        pushkeyframe(obj.matrix_world.copy(), time, lookup)

                        lookup["lastmatrix"] = obj.matrix_world.copy()
                        lookup["hasrested"] = False

                if (frame == endframe):
                    break
                frame += paneldata.samplerate
                if (frame > endframe):
                    frame = endframe

            for lookup in objlookup.values():
                objjson = lookup["data"]

                if (len(lookup["pos"]) > 0):
                    objjson["pos"] = lookup["pos"]
                    objjson["rot"] = lookup["rot"]
                    objjson["scale"] = lookup["scale"]

                output["objects"].append(objjson)

            scene.frame_set(returnframe)
        else:
            for obj in objects:
                objjson = getjsonfromobject(obj)
                output["objects"].append(objjson)

        modelfile = open(filename, "w")
        modelfile.write(json.dumps(output))
        modelfile.close()

        self.report({"INFO"}, "Exported {} objects to \"{}\""
                    .format(len(objects), os.path.basename(filename)))
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

        layout.operator("rm.showcolor")
        layout.prop(paneldata, "filename")
        layout.prop(paneldata, "selected")
        layout.prop(paneldata, "animations")
        layout.prop(paneldata, "samplerate")
        layout.operator("rm.exporter")


# REGISTRY


classes = (
    ExporterProperties,
    BlenderToJSON,
    ShowObjectColor,
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
