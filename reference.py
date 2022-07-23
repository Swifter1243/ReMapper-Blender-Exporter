bl_info = {
    "name": "Export cube data to JSON",
    "author": "wobbleorange",
    "version": "0.07",
    "blender": (2, 80, 0),
    "location": "View3d > Sidepanel",
    "description": "Exports cube loc, rot, & scl data, offset per environment"}


import bpy, os, json, copy
from math import degrees, radians, pi
from mathutils import Matrix, Vector, Euler

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

# ------------------------------------------------------------------------

def ShowMessageBox(message = "", title = "Message Box", icon = 'INFO'):

    def draw(self, context):
        self.layout.label(text=message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

# ------------------------------------------------------------------------
#    Scene Properties
# ------------------------------------------------------------------------

class MyProperties(PropertyGroup):

    track: StringProperty(
        name="Track",
        description="-",
        default="",
        maxlen=24,
        )

    beat: IntProperty(
        name="Beat",
        description="-",
        default = 0,
        min = 0,
        max = 1000
        )

    dur: IntProperty(
        name="Duration",
        description="-",
        default = 0,
        min = 0,
        max = 1000
        )

    thick: FloatProperty(
        name="Wall Thickness",
        description="-",
        default = 0.5,
        min = 0.5,
        max = 12,
        precision = 2,
        step = 10
        )

    f_begin: IntProperty(
        name="Begin Frame",
        description="-",
        default = 1,
        min = 1,
        max = 1000
        )

    f_end: IntProperty(
        name="End Frame",
        description="-",
        default = 1,
        min = 1,
        max = 1000
        )

    alphaOverride: BoolProperty(
        name="Wall alpha override",
        description="Override blender alpha (ie, -1 for 12 thickness walls)",
        default = False
        )

    alpha: IntProperty(
        name="Alpha",
        description="-",
        default = -1,
        min = -1000,
        max = 1000
        )

    keysOnly: BoolProperty(
        name="Keyframes only",
        description="Export keyframes only. Note, this will require keyframes at the Being and End frames.",
        default = False
        )

    selectOnly: BoolProperty(
        name="Selection only",
        description="Export selected cubes only.",
        default = True
        )

    opEnv: EnumProperty(
        items=[("walls", "Walls", "Export for Obstacles"),("notes", "Notes", "Export for Notes\n(also disables arrow, look and gravity)"),("enviro", "Environment", "Export for Environment")],
        #items=[("walls", "Walls", "Export for Obstacles"),("notes", "Notes", "Export for Notes\n(also disables arrow, look and gravity)"),("bts", "BTS", "Export for BTS Environment"),("billie", "Billie", "Export for Billie Environment"),("gaga", "Gaga", "Export for Gaga Environment"),("enviro", "Environment", "Export for Environment")],
        name="Output",
        description=":",
        default=None,
        )


# ------------------------------------------------------------------------
#    Operators  --  Script goes here
# ------------------------------------------------------------------------

class WM_OT_Blend2JSON(Operator):
    bl_label = "Export"
    bl_idname = "wm.blend2json"
    bl_description = "Export to JSON"

    def execute(self, context):

        scene = context.scene
        mytool = scene.my_tool
        alphaOverride = mytool.alphaOverride
        alpha = mytool.alpha
        if mytool.opEnv == "notes":
            thick = 1.25
        else:
            thick = mytool.thick
        scaleAnimExist = False
        colorAnimExist = False
        bpy.context.scene.frame_set(mytool.f_begin)
        selection = bpy.context.selected_objects
        
        #material, [vector, Xdelta, Zdelta]
        #bts
        pillarMat = [(0, 0, 1),0,0]
        pillarwithlaserMat = [(0, 0, 1),0,0]
        laserMat = [(0, 0, -1),0,0]
        #gaga
        backcubeMat = [(0, 1, 1),0,0]
        #billie
        leftfarrailMat = [(0, -1, 0),0,0]

        if mytool.opEnv == "walls":
            Voffset = Vector((0, -1, -1))
            Xdelta = 1
            Zdelta = 0

        if mytool.opEnv == "notes":
            Voffset = Vector((0, 0, 0))
            Xdelta = 1.5
            Zdelta = -1.25
            NJSOffset = mytool.dur / 2

        # print the values to the console
        print("Exporting to JSON ...")
        if mytool.track != "":
            print("track:", mytool.track)        
        print("time:", mytool.beat)
        print("output:", mytool.opEnv)
        #print("offset:", Voffset)
        #print("X:", Xdelta)


        # get path of the blend file (file should have been saved at least once)
        tempFolder = bpy.path.abspath("//")
        # make a filename
        filename = os.path.join (tempFolder, "cube.Locations.json")
        # open a file to write to
        file = open(filename, "w")   # a is for appending  w writes new

        # initialize
        #result = "{\n"
        result = "["

        defPosJson = ""
        locRotJson = ""
        scalJson = ""

        #bpy.context.object.rotation_mode = 'YXZ'

        if mytool.selectOnly == False:
            bpy.ops.object.select_all(action='SELECT')

        # loop through selected objects
        for sel in selection:
            cube = "{"
            defPos = "\"_definitePosition\":["
            locRot = "\"_localRotation\":["
            scal = "\"_scale\":["
            colr = "\"_color\":["

            #object data check
            if (sel.animation_data is not None) and (sel.animation_data.action is not None):
                objAnimExist = True
                for fc in sel.animation_data.action.fcurves :
                    if fc.data_path.endswith(('scale')):
                        scaleAnimExist = True
            else:
                objAnimExist = False
                print("no loc/rot/scl key frames")

            #material color data check
            if mytool.opEnv == "notes" or mytool.opEnv == "walls":
                if (sel.active_material is not None) and (sel.active_material.animation_data is not None) and (sel.active_material.animation_data.action is not None):
                    colorExist = True
                    colorAnimExist = True
                elif (sel.active_material is not None):
                    colorExist = True
                    colorAnimExist = False
                    print("no color anim data")
                else:
                    colorExist = False
                    colorAnimExist = False
                    print("no color data")

            #get keyframe data, if keysOnly.
            if mytool.keysOnly == True:
                frames = [mytool.f_begin,mytool.f_end]
                #get obj keyframe data
                if objAnimExist == True:
                    for fc in sel.animation_data.action.fcurves :
                        if fc.data_path.endswith(('location','rotation_euler','scale')):
                            for key in fc.keyframe_points :
                                if key.co[0] not in frames:
                                    frames += [key.co[0]]

                #get color keyframe data
                if colorAnimExist == True:
                    for fc in sel.active_material.animation_data.action.fcurves :
                        if fc.data_path.endswith(('diffuse_color')):
                            for key in fc.keyframe_points :
                                if key.co[0] not in frames:
                                    frames += [key.co[0]]

            if mytool.opEnv == "enviro":
                #get environment material, else default to BTS pillar
                if len(sel.data.materials) > 1:
                    obMat = sel.material_slots[1].name
                    
                    if obMat == "pillar":
                        Voffset = Vector(pillarMat[0])
                        Xdelta = pillarMat[1]
                        Zdelta = pillarMat[2]
                    elif obMat == "laser":
                        Voffset = Vector(laserMat[0])
                        Xdelta = laserMat[1]
                        Zdelta = laserMat[2]
                    elif obMat == "pillarwithlaser":
                        Voffset = Vector(pillarwithlaserMat[0])
                        Xdelta = pillarwithlaserMat[1]
                        Zdelta = pillarwithlaserMat[2]
                    elif obMat == "backcube":
                        Voffset = Vector(backcubeMat[0])
                        Xdelta = backcubeMat[1]
                        Zdelta = backcubeMat[2]
                    elif obMat == "leftfarrail":
                        Voffset = Vector(leftfarrailMat[0])
                        Xdelta = leftfarrailMat[1]
                        Zdelta = leftfarrailMat[2]
                else:
                    obMat = "pillar"
                    Voffset = Vector(pillarMat[0])
                    Xdelta = pillarMat[1]
                    Zdelta = pillarMat[2]


            # if??? "_interactable":false,"_fake":true,

            if mytool.opEnv == "notes":
                cube = "{\"_time\":" + str(mytool.beat+NJSOffset) + ",\"_lineIndex\":0,\"_lineLayer\":0,\"_type\":1,\"_cutDirection\":8,\"_customData\":{\"_disableNoteGravity\":true,\"_disableNoteLook\":true,\"_interactable\":false,\"_fake\":true,\"_noteJumpStartBeatOffset\":" + str(NJSOffset) +","
            elif mytool.opEnv == "walls":
                cube = "{\"_time\":" + str(mytool.beat) + ",\"_lineIndex\":0,\"_type\":0,\"_duration\":" + str(mytool.dur) + ",\"_width\":0,\"_customData\":{\"_interactable\":false,\"_fake\":true,"
            else: # environment
                cube = "{\"_time\":" + str(mytool.beat) + ",\"_customData\":{"

            if mytool.track != "":
                cube += "\"_track\":\"" + mytool.track + "\","

            if mytool.opEnv == "notes" or mytool.opEnv == "walls":
                if colorExist == True:
                    bpy.context.object.active_material_index = 0    # set active slot
                    dcolor = sel.active_material.diffuse_color
                    if alphaOverride == True:
                        cube += "\"_color\":[" + str(round(dcolor[0],4)) +"," + str(round(dcolor[1],4)) +"," + str(round(dcolor[2],4)) +"," + str(alpha) +"],"
                    else:
                        cube += "\"_color\":[" + str(round(dcolor[0],4)) +"," + str(round(dcolor[1],4)) +"," + str(round(dcolor[2],4)) +"," + str(round(dcolor[3],4)) +"],"
  
            if mytool.opEnv == "walls":
                if scaleAnimExist == True or thick != 0.5:
                    cube += "\"_scale\":[" + str(round(1/thick,4)) +"," + str(round(1/thick,4)) +"," + str(round(1/thick,4)) +"],"
                else:
                    cube += "\"_scale\":[" + str(sel.scale.x*2) +"," + str(sel.scale.z*2) +"," + str(sel.scale.y*2) + "],"

            if mytool.opEnv == "notes":
                cube += "\"_animation\":{\"_dissolveArrow\":[[0,0]],"
            else:
                cube += "\"_animation\":{"

            for frame in range(mytool.f_begin, mytool.f_end+1):
                #keyframes only
                if mytool.keysOnly == True:
                    if frame in frames:
                        bpy.context.scene.frame_set(frame)
                        
                        oloc = copy.copy(sel.location)
                        rot = sel.rotation_euler
                        scl = sel.scale
                        if mytool.opEnv == "notes":
                            offset = sel.location
                        else:
                            offset = copy.copy(Voffset)
                            offset.x *= scl.x
                            offset.y *= scl.y
                            offset.z *= scl.z
                            eul = Euler(rot, 'YXZ')
                            offset.rotate(eul)
                            offset += oloc
                        
                        if mytool.f_end == mytool.f_begin:
                            tt = 0
                        else:
                            tt = (frame-mytool.f_begin) / (mytool.f_end-mytool.f_begin)
                            
                        defPosJson = round(offset.x+Xdelta,6),round(offset.z+Zdelta,6),round(offset.y,6),round(tt,4)
                        defPos += json.dumps(defPosJson) + ','
                        locRotJson = round(degrees(-rot.x),6),round(degrees(-rot.z),6),round(degrees(-rot.y),6),round(tt,4)
                        locRot += json.dumps(locRotJson) + ','

                        if scaleAnimExist == True or thick != 0.5 or mytool.opEnv == "notes":
                            scalJson = round(scl.x*2*thick,6),round(scl.z*2*thick,6),round(scl.y*2*thick,6),round(tt,4)
                            scal+= json.dumps(scalJson) + ','
                        else:
                            scalJson = round(scl.x,6),round(scl.z,6),round(scl.y,6),round(tt,4)
                            scal+= json.dumps(scalJson) + ','

                        if colorAnimExist == True:
                            bpy.context.object.active_material_index = 0    # set active slot
                            dcolor = sel.active_material.diffuse_color
                            if alphaOverride == True:
                                viewcolor = round(dcolor[0],4), round(dcolor[1],4), round(dcolor[2],4), alpha, round(tt,4)
                            else:
                                viewcolor = round(dcolor[0],4), round(dcolor[1],4), round(dcolor[2],4), round(dcolor[3],4), round(tt,4)
                            colr += json.dumps(viewcolor) + ','

                #all frames
                else:
                    bpy.context.scene.frame_set(frame)
                    
                    oloc = copy.copy(sel.location)
                    rot = sel.rotation_euler
                    scl = sel.scale
                    if mytool.opEnv == "notes":
                            offset = sel.location
                    else:
                        offset = copy.copy(Voffset)
                        offset.x *= scl.x
                        offset.y *= scl.y
                        offset.z *= scl.z
                        eul = Euler(rot, 'YXZ')
                        offset.rotate(eul)
                        offset += oloc
                    
                    if mytool.f_end == mytool.f_begin:
                        tt = 0
                    else:
                        tt = (frame-mytool.f_begin) / (mytool.f_end-mytool.f_begin)
                        
                    defPosJson = round(offset.x+Xdelta,6),round(offset.z+Zdelta,6),round(offset.y,6),round(tt,4)
                    defPos += json.dumps(defPosJson) + ','
                    locRotJson = round(degrees(-rot.x),6),round(degrees(-rot.z),6),round(degrees(-rot.y),6),round(tt,4)
                    locRot += json.dumps(locRotJson) + ','

                    if scaleAnimExist == True or thick != 0.5 or mytool.opEnv == "notes":
                        scalJson = round(scl.x*2*thick,6),round(scl.z*2*thick,6),round(scl.y*2*thick,6),round(tt,4)
                        scal += json.dumps(scalJson) + ','
                    else:
                        scalJson = round(scl.x,6),round(scl.z,6),round(scl.y,6),round(tt,4)
                        scal+= json.dumps(scalJson) + ','

                    # get color data
                    if colorAnimExist == True:
                        bpy.context.object.active_material_index = 0    # set active slot
                        dcolor = sel.active_material.diffuse_color
                        if alphaOverride == True:
                            viewcolor = round(dcolor[0],4), round(dcolor[1],4), round(dcolor[2],4), alpha, round(tt,4)
                        else:
                            viewcolor = round(dcolor[0],4), round(dcolor[1],4), round(dcolor[2],4), round(dcolor[3],4), round(tt,4)
                        colr += json.dumps(viewcolor) + ','

 
            defPos = defPos[:-1] +']'
            locRot = locRot[:-1] +']'
            scal = scal[:-1] +']'
            colr = colr[:-1] +']'                                 

            if mytool.opEnv == "notes" or mytool.opEnv == "walls":
                if colorAnimExist == True:
                    cube += colr +','
                if scaleAnimExist == True or thick != 0.5 or mytool.opEnv == "notes":
                    cube += scal +','+ defPos +','+ locRot + '}'
                else:
                    cube += scal +','+ defPos +','+ locRot + '},"_scale":[2,2,2]'
            else:
                cube += scal +','+ defPos +','+ locRot +'},\"_material\":\"' + obMat + '\"'

            result += cube + '}},\n'



        result = result[:-2] + "]" # remove last comma from joined string objects
        #result = result +'\n}'
        file.write(result)
        file.close()


        print("Export completed")
        ShowMessageBox("Export completed", "JSON Export", 'EXPORT')




        return {'FINISHED'}

# ------------------------------------------------------------------------
#    Panel in Object Mode
# ------------------------------------------------------------------------

class OBJECT_PT_CustomPanel(Panel):
    bl_label = "JSON export"
    bl_idname = "OBJECT_PT_custom_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "JSON Export Tool"
    bl_context = "objectmode"   

    @classmethod
    def poll(self,context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool

        layout.prop(mytool, "track")
        layout.prop(mytool, "beat")
        layout.prop(mytool, "dur")
        layout.prop(mytool, "thick")
        layout.prop(mytool, "alphaOverride")
        layout.prop(mytool, "alpha")
        layout.separator()
        layout.prop(mytool, "f_begin")
        layout.prop(mytool, "f_end")
        layout.prop(mytool, "keysOnly")
        layout.prop(mytool, "selectOnly")
        layout.separator()
        layout.prop(mytool, "opEnv")
        layout.operator("wm.blend2json")


# ------------------------------------------------------------------------
#    Registration
# ------------------------------------------------------------------------

classes = (
    MyProperties,
    WM_OT_Blend2JSON,
    OBJECT_PT_CustomPanel
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.Scene.my_tool = PointerProperty(type=MyProperties)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    del bpy.types.Scene.my_tool


if __name__ == "__main__":
    register()