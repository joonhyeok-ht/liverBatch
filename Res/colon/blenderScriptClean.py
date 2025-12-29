'''
'''
import bpy
import bmesh
from mathutils import Vector, bvhtree
from mathutils.kdtree import KDTree
import mathutils

import os, sys
import json
import re
import shutil
import math
import time

tmpPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(tmpPath)

import blenderScriptCleanUpMesh as clmsh


class COptionInfo :
    @staticmethod
    def generate_strings(input_str) :
        # 정규식을 사용하여 숫자 범위와 문자 부분 추출
        match = re.search(r'([a-zA-Z0-9_]+)\[(\d+),(\d+)\]', input_str)
        if match:
            prefix = match.group(1)  # 문자 부분 추출
            start = int(match.group(2))  # 시작 숫자
            end = int(match.group(3))    # 끝 숫자
            
            # 숫자 범위에 따른 문자열 생성
            result = [f"{prefix}{num}" for num in range(start, end + 1)]
            return result
        else:
            return None
        

    def __init__(self) :
        self.m_jsonData = None
        self.m_dataRootPath = ""
        self.m_dicDecimation = {}
        self.m_dicDecimationByRatio = {}
        self.m_dicRemesh = {}
        self.m_listMeshCleanup = []
        self.m_listMeshHealing = []
        self.m_listSamrtUV = []
    def process(self, fullPath : str) -> bool :
        if os.path.exists(fullPath) == False: 
            print(f"not valid Option_Path : {fullPath}")
            return False
        # json initialize 
        with open(fullPath, 'r') as fp :
            self.m_jsonData = json.load(fp)
        
        self.m_dataRootPath = self.m_jsonData["DataRootPath"]
        self.m_decimation = self.m_jsonData["Blender"]["Decimation"]
        self.m_decimationByRatio = self.m_jsonData["Blender"]["DecimationByRatio"]
        self.m_remesh = self.m_jsonData["Blender"]["Remesh"]
        self.m_meshCleanup = self.m_jsonData["Blender"]["MeshCleanUp"]
        self.m_meshHealing = self.m_jsonData["Blender"]["MeshHealing"]
        self.m_smartUV = self.m_jsonData["Blender"]["SmartUV"]

        self.m_centerlineInfo = self.m_jsonData["CenterlineInfo"]

        self.m_voxelSize = self.m_remesh["VoxelSize"]

        self._update_dictionary_type(self.m_dicDecimation, self.m_decimation)
        self._update_dictionary_type(self.m_dicDecimationByRatio, self.m_decimationByRatio)
        self._update_dictionary_type(self.m_dicRemesh, self.m_remesh["RemeshList"])
        self._update_list_type(self.m_listMeshCleanup, self.m_meshCleanup)
        self._update_list_type(self.m_listMeshHealing, self.m_meshHealing)
        self._update_list_type(self.m_listSamrtUV, self.m_smartUV)
        
        return True
    
    def _update_dictionary_type(self, outputDic : dict, srcDict : dict) :
        for key, value in srcDict.items() :
            listRet = COptionInfo.generate_strings(key)
            if listRet is None :
                outputDic[key] = value
            else :
                for subKey in listRet :
                    outputDic[subKey] = value
    def _update_list_type(self, outList : list, srcList : list) :
        for key in srcList :
            listRet = COptionInfo.generate_strings(key)
            if listRet is None :
                outList.append(key)
            else :
                for subKey in listRet :
                    outList.append(subKey)
    
    @property
    def DataRootPath(self) -> str :
        return self.m_dataRootPath
    @property
    def Decimation(self) -> dict :
        return self.m_dicDecimation
    @property
    def DecimationByRatio(self) -> dict :
        return self.m_dicDecimationByRatio
    @property
    def Remesh(self) -> dict :
        return self.m_dicRemesh
    @property
    def CleanUp(self) -> list :
        return self.m_listMeshCleanup
    @property
    def Healing(self) -> list :
        return self.m_listMeshHealing
    @property
    def SmartUV(self) -> list :
        return self.m_listSamrtUV
    @property
    def CenterlineInfo(self) -> list :
        return self.m_centerlineInfo
    @property
    def VoxelSize(self) :
        return self.m_voxelSize


class CBlenderScriptCutVesselAutoMarkSharp :
    ## Cutting된 혈관들의 절단면을 선택한 후 Mark Sharp 수행
    THRESHOLD = 1e-2  #important factor : 이 값이 너무 작으면 절단면의 일부가 선택안될수 있음.
    MIN_FACES = 7 #important factor : 이 값이 너무 크면 선택안되는 절단면이 있을 수 있음.
    @staticmethod
    def mark_sharp_custom(objList) :
        for objName in objList:
            obj = bpy.data.objects.get(objName)
            if obj and obj.type == 'MESH':
                CBlenderScriptCutVesselAutoMarkSharp._select_cut_face_and_mark_sharp(obj, min_faces=7) 
              
        bpy.ops.object.mode_set(mode='OBJECT')
    @staticmethod    
    def _vector_almost_equal(v1: Vector, v2: Vector, tol=THRESHOLD):
        return (v1 - v2).length < tol
    @staticmethod
    def _get_connected_normal_groups(bm, tol=THRESHOLD, min_faces=10):
        visited = set()
        groups = []

        def dfs(start_face, normal, group):
            stack = [start_face]
            while stack:
                face = stack.pop()
                if face in visited:
                    continue
                if not CBlenderScriptCutVesselAutoMarkSharp._vector_almost_equal(face.normal, normal, tol):
                    continue
                visited.add(face)
                group.append(face)
                for edge in face.edges:
                    for linked_face in edge.link_faces:
                        if linked_face not in visited:
                            stack.append(linked_face)

        for face in bm.faces:
            if face in visited:
                continue
            group = []
            dfs(face, face.normal, group)
            if len(group) > min_faces:
                groups.append(group)

        return groups
    @staticmethod
    def _are_groups_adjacent(group1, group2):
        # 두 그룹의 face가 edge를 공유하면 인접
        group1_faces = set(group1)
        for face in group2:
            for edge in face.edges:
                for linked_face in edge.link_faces:
                    if linked_face in group1_faces:
                        return True
        return False
    @staticmethod
    def _find_largest_groups_among_adjacent(groups):
        group_graph = []
        for i, g1 in enumerate(groups):
            adj = set()
            for j, g2 in enumerate(groups):
                if i != j and CBlenderScriptCutVesselAutoMarkSharp._are_groups_adjacent(g1, g2):
                    adj.add(j)
            group_graph.append(adj)

        visited = set()
        result_groups = []

        for i in range(len(groups)):
            if i in visited:
                continue
            component = [i]
            visited.add(i)
            stack = [i]

            # 연결된 그룹 전체 탐색
            while stack:
                current = stack.pop()
                for neighbor in group_graph[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        component.append(neighbor)
                        stack.append(neighbor)

            # 해당 컴포넌트 내 가장 큰 그룹만 선택
            largest_group_index = max(component, key=lambda idx: len(groups[idx]))
            result_groups.append(groups[largest_group_index])

        return result_groups
    @staticmethod
    def _select_cut_face_and_mark_sharp(obj, min_faces=10, tol=THRESHOLD):
    #    bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.mode_set(mode='OBJECT')  # 안정적으로 OBJECT → EDIT 전환
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        # 전체 face 선택 해제
        for f in bm.faces:
            f.select = False
                
        # clear sharp 모든 엣지를 부드럽게 설정 (Sharp 해제)
        for edge in bm.edges:
            edge.smooth = True  # Sharp가 아닌 상태

        # 1. 노멀 기준 연결된 그룹들 찾기
        normal_groups = CBlenderScriptCutVesselAutoMarkSharp._get_connected_normal_groups(bm, tol, 7)

        # 2. 붙어있는 그룹들 중 가장 큰 것만 선택
        largest_groups = CBlenderScriptCutVesselAutoMarkSharp._find_largest_groups_among_adjacent(normal_groups)

        # 3. 조건 만족한 그룹만 선택
        for group in largest_groups:
            if len(group) >= min_faces:
                for f in group:
                    f.select = True
                    #set mark sharp
                    for edge in f.edges:
                        edge.smooth = False  # mark sharp 상태
                        # print("edge.smooth : false")

        bmesh.update_edit_mesh(obj.data)


class CBlenderScriptClean :
    s_exceptFolder = "Result"

    @staticmethod
    def get_folder_list(path : str) -> list :
        return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
    @staticmethod    
    def __get_decimation_ratio(srcVerticesCnt : int, targetVerticesCnt : int) :
        return targetVerticesCnt / srcVerticesCnt
    

    def __init__(self, optionFullPath : str, inputPath : str, outputPath : str, saveName : str) -> None :
        self.m_optionPath = optionFullPath
        self.m_inputPath = inputPath
        self.m_outputPath = outputPath
        self.m_saveName = saveName

        self.m_resPath = os.path.dirname(self.m_optionPath)
        self.m_resPath = os.path.join(self.m_resPath, "Res")
        self.m_resPath = os.path.join(self.m_resPath, "colon")

        self.m_optionInfo = COptionInfo()

        self.m_listObjName = []
        self.m_listStlNameCleanUp = []
    def process(self) -> bool :
        if self.m_optionInfo.process(self.m_optionPath) == False :
            return False

        if self._import_folders() == False :
            print("failed import stl")
            return False
        
        self._init_cleanup(self.m_optionInfo.CleanUp)
        # self._decimation(self.m_optionInfo.Decimation, False)
        # self._decimation(self.m_optionInfo.DecimationByRatio, True)
        self._cleanup()

        # auto shade smoothing 수행 
        # self._auto_smoothing(30.0)
        # self._auto_sharp_edge()

        self._smartUV(self.m_optionInfo.SmartUV)

        self.process_colon_mapping()
        self._save_blender_with_patientID(self.m_outputPath, self.m_saveName)
        # bpy.ops.wm.quit_blender()
    def process_colon_mapping(self) :
        jsonData = self.m_optionInfo.m_jsonData

        if "ColonMergeInfo" not in jsonData :
            print("option invalid : not found ColonMergeInfo")
            return
        jsonData = jsonData["ColonMergeInfo"]
        if "MergeBlenderName" not in jsonData :
            print("option invalid : not found MergeBlenderName")
            return
        mergeBlenderName = jsonData["MergeBlenderName"]
        
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        if mergeBlenderName not in bpy.data.objects :
            print(f"not found {mergeBlenderName}")
            return
        
        if len(self.m_listObjName) == 0 :
            print(f"not found dummy colon")
            return
        
        listTex = [
            # "tex.png",
            # "texNormal.png",
            # "tex1.png",
            # "texNormal1.png",
            "tex2.png",
            "texNormal2.png",
            # "texEn.png",
            # "texNormalEn.png"
        ]
        listTexImg = []
        
        fullPath = os.path.join(self.m_resPath, listTex[0])
        listTexImg.append(self._load_texImg(fullPath))
        fullPath = os.path.join(self.m_resPath, listTex[1])
        listTexImg.append(self._load_texImg(fullPath))

        self._uv_transfer_nearest(self.m_listObjName[0], mergeBlenderName)
        self._attach_tex_normal_to_object(self.m_listObjName[0], listTexImg[0], listTexImg[1])
        self._attach_tex_normal_to_object_invert_y(mergeBlenderName, listTexImg[0], listTexImg[1])


    def _delete_all_object(self) :
        bpy.ops.object.select_all(action="SELECT")
        bpy.ops.object.delete()
    def _import_folders(self) -> bool :
        listFolder = CBlenderScriptClean.get_folder_list(self.m_inputPath)
        if CBlenderScriptClean.s_exceptFolder in listFolder :
            listFolder.remove(CBlenderScriptClean.s_exceptFolder)
        if len(listFolder) == 0 :
            print("not found folder list")
            return False
        
        for folderName in listFolder :
            self.__import_folder_stl(folderName)
            self.__import_folder_obj(folderName)

        return True
    def _init_cleanup(self, listCleanup : list) :
        for cleanupName in listCleanup :
            if cleanupName in bpy.data.objects :
                self.m_listStlNameCleanUp.append([cleanupName, 0])
    def _decimation(self, dicDeci : dict, bRatio : bool) :
        for deciName, triValue in dicDeci.items() : 
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')

            if deciName in bpy.data.objects :
                obj = bpy.data.objects[deciName]
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj

                if bRatio == False :
                    targetVertexCnt = triValue
                    srcVertexCnt =len(bpy.context.active_object.data.vertices)
                    decimationRatio = self.__get_decimation_ratio(srcVertexCnt, targetVertexCnt / 2)
                else :
                    decimationRatio = triValue / 100.0
                
                decimate_modifier = obj.modifiers.new(name="Decimate", type='DECIMATE')
                decimate_modifier.ratio = decimationRatio
                bpy.ops.object.modifier_apply(modifier=decimate_modifier.name)

                print(f"passed decimation : {deciName} : {triValue} : {decimationRatio}")
        print("passed decimation")
    def _cleanup(self) :
        count = sum(1 for item in self.m_listStlNameCleanUp if item[1] == 0)
        cnt = 0
        print(f"mesh clean cnt : {count}")
        # for cnt in range(0, 10) :
        while count > 0 :
            self.__clean_up_mesh(self.m_listStlNameCleanUp) 
            print(f"mesh clean step : {cnt}, {count}")
            count = sum(1 for item in self.m_listStlNameCleanUp if item[1] == 0)
            cnt += 1
        print("passed mesh clean")
    def _auto_smoothing(self, angle : float = 30.0) :
        radian = math.radians(angle)
        for obj in bpy.data.objects :
            if obj and obj.type == 'MESH':
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)

                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.shade_smooth()
                obj.data.use_auto_smooth = True
                obj.data.auto_smooth_angle = radian 
    def _auto_sharp_edge(self) :
        tpInfoPath = os.path.join("TPInfo", "out")
        tpInfoFullPath = os.path.join(self.m_inputPath, f"{tpInfoPath}")
        if os.path.exists(tpInfoFullPath) == False :
            print("not found TPInfoPath")
            return
        objList = [os.path.splitext(f)[0] for f in os.listdir(tpInfoFullPath) if f.lower().endswith(".stl")]
        CBlenderScriptCutVesselAutoMarkSharp.mark_sharp_custom(objList)
    def _smartUV(self, listSmartUV : list) :
        bpy.ops.object.select_all(action='DESELECT')
        for smartUVName in listSmartUV :
            if smartUVName in bpy.data.objects :
                obj = bpy.data.objects[smartUVName]
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj

                bpy.ops.object.editmode_toggle()
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.uv.smart_project(scale_to_bounds=True)
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.object.editmode_toggle()
                bpy.ops.object.select_all(action='DESELECT')
                print(f"check smartUV : {smartUVName }")
            else :
                print(f"not found smartUVName : {smartUVName}")
        print("passed smartUV")
    def _save_blender_with_patientID(self, outputPath : str, saveAs : str) :
        blenderPath = os.path.join(outputPath)
        blenderFullPath = os.path.join(blenderPath, saveAs)
        if os.path.exists(blenderFullPath):
            os.remove(blenderFullPath)
            
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.wm.save_as_mainfile(filepath=blenderFullPath)
        bpy.ops.object.select_all(action='DESELECT')
        print(f"Save Path : {blenderFullPath}")
    
    def _load_texImg(self, fullPath : str) :
        if os.path.exists(fullPath) == False :
            print(f"not found tex : {fullPath}")
            return None
        texImg = bpy.data.images.load(fullPath)
        return texImg
    def _attach_tex_normal_to_object(self, objName : str, texImg, texNormal) :
        bpy.ops.object.select_all(action='DESELECT')
        if objName not in bpy.data.objects :
            print(f"not found {objName}")
            return
        
        obj = bpy.data.objects[objName]
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='OBJECT')

        mat = bpy.data.materials.new(name="AutoMaterial")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        # 기존 노드 제거
        for node in nodes:
            nodes.remove(node)

        texNode = nodes.new(type='ShaderNodeTexImage')
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        output = nodes.new(type='ShaderNodeOutputMaterial')

        texNode.location = (-300, 300)
        bsdf.location = (0, 300)
        output.location = (300, 300)
        texNode.image = texImg

        texNormalNode = nodes.new(type='ShaderNodeTexImage')
        normalMapnode = nodes.new(type='ShaderNodeNormalMap')

        texNormalNode.image = texNormal
        texNormalNode.image.colorspace_settings.name = 'Non-Color'
        texNormalNode.location = (-500, 0)
        normalMapnode.location = (-200, 0)

        links.new(texNode.outputs['Color'], bsdf.inputs['Base Color'])
        links.new(texNormalNode.outputs['Color'], normalMapnode.inputs['Color'])
        links.new(normalMapnode.outputs['Normal'], bsdf.inputs['Normal'])
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

        if obj.data.materials :
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)
    def _attach_tex_normal_to_object_invert_y(self, objName : str, texImg, texNormal) :
        bpy.ops.object.select_all(action='DESELECT')
        if objName not in bpy.data.objects :
            print(f"not found {objName}")
            return
        
        obj = bpy.data.objects[objName]
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='OBJECT')

        mat = bpy.data.materials.new(name="AutoMaterial")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        # 기존 노드 제거
        for node in nodes:
            nodes.remove(node)

        texNode = nodes.new(type='ShaderNodeTexImage')
        bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
        output = nodes.new(type='ShaderNodeOutputMaterial')

        texNode.location = (-300, 300)
        bsdf.location = (0, 300)
        output.location = (300, 300)
        texNode.image = texImg

        texNormalNode = nodes.new(type='ShaderNodeTexImage')
        normalMapnode = nodes.new(type='ShaderNodeNormalMap')

        texNormalNode.image = texNormal
        texNormalNode.image.colorspace_settings.name = 'Non-Color'
        texNormalNode.location = (-500, 0)
        normalMapnode.location = (-200, 0)

        # RGB 분리/결합 + Y 반전
        separateRGBNode = nodes.new(type="ShaderNodeSeparateRGB")
        invertYNode = nodes.new(type="ShaderNodeMath")
        combineRGBNode = nodes.new(type="ShaderNodeCombineRGB")
        separateRGBNode.location = (-600, 0)
        invertYNode.location = (-400, -100)
        combineRGBNode.location = (-200, 0)

        invertYNode.operation = 'SUBTRACT'
        invertYNode.inputs[0].default_value = 1.0  # 1 - G

        links.new(texNode.outputs['Color'], bsdf.inputs['Base Color'])
        # links.new(texNormalNode.outputs['Color'], normalMapnode.inputs['Color'])
        links.new(texNormalNode.outputs['Color'], separateRGBNode.inputs['Image'])
        links.new(separateRGBNode.outputs['R'], combineRGBNode.inputs['R'])
        links.new(separateRGBNode.outputs['G'], invertYNode.inputs[1])
        links.new(invertYNode.outputs[0], combineRGBNode.inputs['G'])
        links.new(separateRGBNode.outputs['B'], combineRGBNode.inputs['B'])
        links.new(combineRGBNode.outputs['Image'], normalMapnode.inputs['Color'])
        links.new(normalMapnode.outputs['Normal'], bsdf.inputs['Normal'])
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

        if obj.data.materials :
            obj.data.materials[0] = mat
        else :
            obj.data.materials.append(mat)
    def _uv_transfer_nearest(self, src_name : str, tgt_name : str) :
        src_obj = bpy.data.objects[src_name]
        tgt_obj = bpy.data.objects[tgt_name]

        src_mesh = src_obj.data
        tgt_mesh = tgt_obj.data

        src_bm = bmesh.new()
        src_bm.from_mesh(src_mesh)
        src_bm.faces.ensure_lookup_table()

        src_uv_layer = src_bm.loops.layers.uv.active
        if src_uv_layer is None:
            print("Source mesh has no UV map!")
            return

        tgt_bm = bmesh.new()
        tgt_bm.from_mesh(tgt_mesh)
        tgt_bm.faces.ensure_lookup_table()

        tgt_uv_layer = tgt_bm.loops.layers.uv.verify()

        src_mat = src_obj.matrix_world
        tgt_mat = tgt_obj.matrix_world

        # BVH 트리 생성 (소스 메쉬)
        verts = [src_mat @ v.co for v in src_bm.verts]
        faces = [[v.index for v in f.verts] for f in src_bm.faces]
        bvh = mathutils.bvhtree.BVHTree.FromPolygons(verts, faces)

        for face in tgt_bm.faces:
            for loop in face.loops:
                vert = loop.vert
                vert_world_co = tgt_mat @ vert.co

                # 가장 가까운 점과 face index 얻기
                nearest = bvh.find_nearest(vert_world_co)
                if nearest is None:
                    continue
                hit_location, normal, face_index, dist = nearest

                src_face = src_bm.faces[face_index]
                loops = src_face.loops

                # 소스 face 좌표 (world space)
                a = src_mat @ src_face.verts[0].co
                b = src_mat @ src_face.verts[1].co
                c = src_mat @ src_face.verts[2].co

                bary = self.__barycentric_coords(hit_location, a, b, c)
                if bary is None:
                    continue
                u, v, w = bary

                uv0 = loops[0][src_uv_layer].uv.copy()
                uv1 = loops[1][src_uv_layer].uv.copy()
                uv2 = loops[2][src_uv_layer].uv.copy()

                uv = uv0 * u + uv1 * v + uv2 * w
                loop[tgt_uv_layer].uv = uv

        tgt_bm.to_mesh(tgt_mesh)
        tgt_bm.free()
        src_bm.free()

        print("UV transfer by nearest point done.")


    def __import_folder_stl(self, folderName : str) :
        folderPath = os.path.join(self.m_inputPath, folderName)
        if os.path.exists(folderPath) == False :
            print(f"not found {folderPath}")
            return
        folderOutPath = os.path.join(folderPath, "out")
        if os.path.exists(folderOutPath) == False :
            print(f"not found {folderOutPath}")
            return
        
        listStlName = [f for f in os.listdir(folderOutPath) if f.endswith(".stl")]
        for stlName in listStlName :
            # if stlName == ".DS_Store" : 
            #     continue

            # ext = stlName.split('.')[-1]
            # if ext != "stl" :
            #      continue
            stlFullPath = os.path.join(folderOutPath, stlName)
            if os.path.isdir(stlFullPath) == True :
                continue

            # 기존 object 삭제 
            objectName = os.path.splitext(stlName)[0]
            existingObject = bpy.data.objects.get(objectName)
            if existingObject:
                bpy.data.objects.remove(existingObject, do_unlink=True)
                print(f"Removed existing object: {objectName}")

            bpy.ops.import_mesh.stl(filepath=f"{stlFullPath}")
            print(f"imported {stlFullPath}")
    def __import_folder_obj(self, folderName : str) :
        folderPath = os.path.join(self.m_inputPath, folderName)
        if os.path.exists(folderPath) == False :
            print(f"not found {folderPath}")
            return
        folderOutPath = os.path.join(folderPath, "out")
        if os.path.exists(folderOutPath) == False :
            print(f"not found {folderOutPath}")
            return
        
        listObjName = [f for f in os.listdir(folderOutPath) if f.endswith(".obj")]
        for objName in listObjName :
            # if stlName == ".DS_Store" : 
            #     continue

            # ext = stlName.split('.')[-1]
            # if ext != "stl" :
            #      continue
            objFullPath = os.path.join(folderOutPath, objName)
            if os.path.isdir(objFullPath) == True :
                continue

            # 기존 object 삭제 
            objectName = os.path.splitext(objName)[0]
            existingObject = bpy.data.objects.get(objectName)
            if existingObject:
                bpy.data.objects.remove(existingObject, do_unlink=True)
                print(f"Removed existing object: {objectName}")
            
            self.m_listObjName.append(objectName)

            bpy.ops.import_scene.obj(filepath=f"{objFullPath}", axis_forward='Y', axis_up='Z')
            print(f"imported {objFullPath}")

            # import된 obj는 context에 추가됨
            obj = bpy.context.selected_objects[0]
            # Object 모드로 전환
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='OBJECT')
            mesh = obj.data
            # 기존 vertex normal 제거
            mesh.use_auto_smooth = False
            try:
                mesh.normals_split_custom_set_from_vertices([])
            except Exception:
                pass

            mesh.calc_normals()
            if mesh.uv_layers :
                mesh.calc_tangents()
    def __clean_up_mesh(self, name_and_flag_list) :
        if bpy.context.mode == 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='SELECT')
        
        for objinfo in name_and_flag_list :
            if objinfo[1] == 0: #해당 obj의 mesh error가 미해결 상태라면 clean-up 수행
                clmsh.clean_up_mesh(objinfo[0])
                meshErrStatus = clmsh.log_mesh_errors(objinfo[0])
                print(f"error : {meshErrStatus}")
                # [vol, vert, face, nm_len, i_f_len, zf_len, ze_len, nf_len]
                if meshErrStatus[3] == 0 and meshErrStatus[4] == 0 and meshErrStatus[5] == 0 and meshErrStatus[7] == 0 :
                    # print(f"completed clean-up : {objinfo[0]}")
                    objinfo[1] = 1
    def __barycentric_coords(self, p, a, b, c) :
        v0 = b - a
        v1 = c - a
        v2 = p - a
        d00 = v0.dot(v0)
        d01 = v0.dot(v1)
        d11 = v1.dot(v1)
        d20 = v2.dot(v0)
        d21 = v2.dot(v1)
        denom = d00 * d11 - d01 * d01
        if denom == 0 :
            return None
        v = (d11 * d20 - d01 * d21) / denom
        w = (d00 * d21 - d01 * d20) / denom
        u = 1 - v - w
        return (u, v, w)


def find_param(args : list, paramName : str) :
    try:
        inx = args.index(paramName)
        return args[inx + 1]
    except ValueError:
        print(f"not found param : {paramName}")
    return None
def exist_param(args : list, paramName : str) -> bool :
    try:
        inx = args.index(paramName)
        return True
    except ValueError:
        print(f"not found param : {paramName}")
    return False

if __name__=='__main__' :
    args = sys.argv

    if "--" in args :
        inx = args.index("--")
        scriptArgs = args[inx + 1 : ]

        optionFullPath = find_param(scriptArgs, "--optionFullPath")
        inputPath = find_param(scriptArgs, "--inputPath")
        outputPath = find_param(scriptArgs, "--outputPath")
        saveName = find_param(scriptArgs, "--saveName")

        if inputPath is None or outputPath is None or saveName is None :
            print(f"blender script : not found param")
        else :
            print("-" * 30)
            print(f"blender script : optionFullPath -> {optionFullPath}")
            print(f"blender script : inputPath -> {inputPath}")
            print(f"blender script : outputPath -> {outputPath}")
            print(f"blender script : saveName -> {saveName}")
            print("-" * 30)

            inst = CBlenderScriptClean(optionFullPath, inputPath, outputPath, saveName)
            inst.process()

