 
import bpy
import os
listObjName = ['ASPDA_TPa', 'IPA_TPa', 'LGA_TPa', 'LGEA_TPa', 'LHA_TPa', 'Omental_Br_TPa', 'PGA_TPa', 'RGA_TPa', 'RGEA_TPa', 'RHA_TPa', 'SGA_TPa', 'SMA_TPa', 'SupPolarA_TPa', 'ARCV_TPv', 'ASPDV_TPv', 'IPV_TPv', 'LGEV_TPv', 'LGV_TPv', 'RGEV_TPv', 'RGV_TPv', 'SGV_TPv']
outputPath = 'C:/Users/hutom/Desktop/jh_test/CommonPipelines/CommonPipeline_10_sco/CommonPipeline_10/output_stomach\01011ug_500\TPInfo\in'
for objName in listObjName :
    if objName in bpy.data.objects:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.objects[objName].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[objName]
        bpy.ops.export_mesh.stl(filepath=os.path.join(outputPath, objName + '.stl'), use_selection=True)
                