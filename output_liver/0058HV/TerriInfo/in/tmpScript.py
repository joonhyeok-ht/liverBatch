 
import bpy
import os
listObjName = ['Liver_PP']
outputPath = 'C:/Users/hutom/Desktop/jh_test/CommonPipelines/CommonPipeline_10_sco/CommonPipeline_10/output_liver\0058HV\TerriInfo\in'
for objName in listObjName :
    if objName in bpy.data.objects:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.objects[objName].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[objName]
        bpy.ops.export_mesh.stl(filepath=os.path.join(outputPath, objName + '.stl'), use_selection=True)
                