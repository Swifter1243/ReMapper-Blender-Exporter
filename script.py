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
    "version": "0.01",
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

    pos = swapyz(tolist(pos, lambda x: x * RESIZEAMOUNT))
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

    if (obj.material_slots):
        objjson["track"] = obj.material_slots[0].material.name
        if (len(obj.material_slots) > 1):
            objjson["color"] = tolist(
                obj.material_slots[1].material.node_tree.nodes["Principled BSDF"].inputs[0].default_value)

    return objjson


def getobjects(context: Context):
    if len(context.selected_objects) != 0:
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
                print(time)

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
                            if (len(lookup["pos"]) == 0):
                                holdtime = gettime(startframe, framedur, startframe)
                            else:
                                holdtime = gettime(startframe, framedur, frame - 1)
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

        file = open(filename, "w")
        file.write(json.dumps(output))
        file.close()

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

        layout.prop(paneldata, "filename")
        layout.prop(paneldata, "animations")
        layout.prop(paneldata, "samplerate")
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
