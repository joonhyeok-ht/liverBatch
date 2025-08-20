import sys
import os
import glob
import shutil
import numpy as np
import multiprocessing

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAlgorithmPath = os.path.join(fileAbsPath, "Algorithm") 
fileAlgUtilPath = os.path.join(fileAbsPath, "AlgUtil")
fileBlockPath = os.path.join(fileAbsPath, "Block")
sys.path.append(fileAbsPath)
sys.path.append(fileAlgorithmPath)
sys.path.append(fileAlgUtilPath)
sys.path.append(fileBlockPath)


import Block.optionInfo as optionInfo
import Block.niftiContainer as niftiContainer
import Block.originOffset as originOffset
import Block.removeStricture as removeStricture
import Block.registration as registration
import Block.reconstruction as reconstruction
import Block.meshHealing as meshHealing
import Block.meshBoolean as meshBoolean
import Block.territory as territory


class CCommonPipelineTerritory() :
    def __init__(self) -> None:
        try:
        # PyInstaller로 패키징된 실행 파일의 경우
            self.fileAbsPath = sys._MEIPASS
            self.fileAbsPath = "."
        except AttributeError:
            # 개발 환경에서
            self.fileAbsPath = os.path.abspath(os.path.dirname(__file__))

    # override
    def init(self) :
        jsonPath = os.path.join(self.fileAbsPath, "option.json")
        self.m_optionInfo = optionInfo.COptionInfoSingle(jsonPath)
    def process(self) :
        if self.m_optionInfo.Ready == False :
            print("not found option.json")
            return
        
        dataRootPath = self.m_optionInfo.DataRootPath

        listPatientID = os.listdir(dataRootPath)
        for patientID in listPatientID :
            fullPath = os.path.join(dataRootPath, patientID)
            if os.path.isdir(fullPath) == False :
                continue
            if patientID == ".DS_Store" : 
                continue
            self._patient_pipeline(patientID)
    def clear(self) :
        # input your code 
        print("visited clear")


    def _patient_pipeline(self, patientID : str) :
        passInst = self.m_optionInfo.find_pass(optionInfo.COptionInfo.s_processTerriName)
        if passInst is None :
            print(f"not found pass : {optionInfo.COptionInfo.s_processTerriName}")
            return 
        
        patientFullPath = os.path.join(self.m_optionInfo.DataRootPath, patientID)
        self.m_maskFullPath = os.path.join(patientFullPath, "Mask")
        outputDataRoot = os.path.join(self.fileAbsPath, os.path.basename(self.m_optionInfo.DataRootPath))
        outputPatientFullPath = os.path.join(outputDataRoot, patientID)
        phaseInfoFileName = "phaseInfo"
        self.m_patientBlenderFullPath = os.path.join(outputPatientFullPath, optionInfo.COptionInfo.get_blender_name(passInst.In, patientID))

        if os.path.exists(self.m_patientBlenderFullPath) == False :
            print(f"not found blender file : {self.m_patientBlenderFullPath}")
            return

        self.__init_territory(outputDataRoot, outputPatientFullPath, patientID)

        niftiContainerBlock = niftiContainer.CNiftiContainerTerritory()
        niftiContainerBlock.InputOptionInfo = self.m_optionInfo
        niftiContainerBlock.InputPath = self.m_maskFullPath
        niftiContainerBlock.process()

        fileLoadPhaseInfoBlock = niftiContainer.CFileLoadPhaseInfo()
        fileLoadPhaseInfoBlock.InputNiftiContainer = niftiContainerBlock
        fileLoadPhaseInfoBlock.InputPath = outputPatientFullPath
        fileLoadPhaseInfoBlock.InputFileName = phaseInfoFileName
        fileLoadPhaseInfoBlock.process()

        iSegInfoCnt = self.m_optionInfo.get_segmentinfo_count()
        for inx in range(0, iSegInfoCnt) :
            segInfo = self.m_optionInfo.get_segmentinfo(inx)
            if segInfo.Type == "mask" :
                territoryBlock = territory.CTerritoryMask()
                territoryBlock.InputPath = self.m_territoryInPath
                territoryBlock.InputNiftiContainer = niftiContainerBlock
                territoryBlock.InputOptionInfo = self.m_optionInfo
                territoryBlock.InputSegInx = inx
                territoryBlock.OutputPath = self.m_territoryOutPath
                territoryBlock.process()
                territoryBlock.clear()
            elif segInfo.Type == "blender" :
                territoryBlock = territory.CTerritory()
                territoryBlock.InputPath = self.m_territoryInPath
                territoryBlock.InputNiftiContainer = niftiContainerBlock
                territoryBlock.InputOptionInfo = self.m_optionInfo
                territoryBlock.InputSegInx = inx
                territoryBlock.OutputPath = self.m_territoryOutPath
                territoryBlock.process()
                territoryBlock.clear()
            elif segInfo.Type == "centerline" :
                pass
            else :
                print("invalid segInfo Type : must be mask or blender or centerline")


        niftiContainerBlock.clear()
        fileLoadPhaseInfoBlock.clear()

        self.__end_territory(passInst, outputDataRoot, outputPatientFullPath, patientID)



        
    # private
    def __init_territory(self, outputDataRoot : str, outputPatientFullPath : str, patientID : str) :
        '''
        ret : (territoryPath, territoryInPath, territoryOutPath)
        '''
        self.m_territoryInPath = optionInfo.COptionInfo.pass_in_path(optionInfo.COptionInfo.s_processTerriName)
        self.m_territoryInPath = os.path.join(outputPatientFullPath, self.m_territoryInPath)
        self.m_territoryOutPath = optionInfo.COptionInfo.pass_out_path(optionInfo.COptionInfo.s_processTerriName)
        self.m_territoryOutPath = os.path.join(outputPatientFullPath, self.m_territoryOutPath)

        if os.path.exists(self.m_territoryInPath) == False :
            os.makedirs(self.m_territoryInPath)
        if os.path.exists(self.m_territoryOutPath) == False :
            os.makedirs(self.m_territoryOutPath)

        iSegCnt = self.m_optionInfo.get_segmentinfo_count()
        for inx in range(0, iSegCnt) :
            segInfo = self.m_optionInfo.get_segmentinfo(inx)
            if segInfo.Type == "mask" :
                self.__init_territory_mask(inx)
            elif segInfo.Type == "blender" :
                self.__init_territory_blender(inx)
            elif segInfo.Type == "centerline" :
                self.__init_territory_centerline(inx)
    def __end_territory(self, passInst : optionInfo.CPass, outputDataRoot : str, outputPatientFullPath : str, patientID : str) :
        '''
        ret : (territoryPath, territoryInPath, territoryOutPath)
        '''
        saveAs = optionInfo.COptionInfo.get_blender_name(optionInfo.COptionInfo.s_processTerriName, patientID)
        patientBlenderFullPath = os.path.join(outputPatientFullPath, saveAs)

        if os.path.exists(self.m_territoryOutPath) == False :
            print(f"not found territory out path : {patientID}")
            return
        
        shutil.copy(self.m_patientBlenderFullPath, patientBlenderFullPath)

        stlPath = optionInfo.COptionInfo.pass_out_path(optionInfo.COptionInfo.s_processTerriName)
        option = ""
        if passInst.TriOpt == 1 :
            option += "--triOpt"

        # blender background 실행
        cmd = f"{self.m_optionInfo.BlenderExe} -b {patientBlenderFullPath} --python {os.path.join(self.fileAbsPath, 'blenderScriptCommonPipeline.py')} -- --patientID {patientID} --path {stlPath} --saveAs {saveAs} {option}"
        os.system(cmd)


    def __init_territory_mask(self, segInfoInx : int) :
        segInfo = self.m_optionInfo.get_segmentinfo(segInfoInx)

        organName = segInfo.Organ
        maskInfo = self.m_optionInfo.find_maskinfo_by_blender_name(organName)
        if maskInfo is None :
            print(f"not found maskInfo : {organName}")
            return
        organMaskPath = f"{maskInfo.Name}.nii.gz"
        organMaskFullPath = os.path.join(self.m_maskFullPath, organMaskPath)
        if os.path.exists(organMaskFullPath) == False :
            print(f"not found organ mask : {organMaskPath}")
            return
        
        shutil.copy(organMaskFullPath, os.path.join(self.m_territoryInPath, organMaskPath))
        
        
        iVesselCnt = segInfo.get_vesselinfo_count()
        for iVesselInx in range(0, iVesselCnt) :
            wholeVesselName = segInfo.get_vesselinfo_whole_vessel(iVesselInx)
            maskInfo = self.m_optionInfo.find_maskinfo_by_blender_name(wholeVesselName)
            if maskInfo is None :
                print(f"not found maskInfo : {wholeVesselName}")
                return
            wholeVesselMaskPath = f"{maskInfo.Name}.nii.gz"
            wholeVesselMaskFullPath = os.path.join(self.m_maskFullPath, wholeVesselMaskPath)
            if os.path.exists(wholeVesselMaskFullPath) == False :
                print(f"not found wholeVessel mask : {wholeVesselMaskPath}")
                return
            
            shutil.copy(wholeVesselMaskFullPath, os.path.join(self.m_territoryInPath, wholeVesselMaskPath))
            
            iStartInx = segInfo.get_vesselinfo_child_start(iVesselInx)
            iEndInx = segInfo.get_vesselinfo_child_end(iVesselInx)
            for iChildInx in range(iStartInx, iEndInx + 1) :
                subVesselMaskPath = f"{maskInfo.Name}{iChildInx}.nii.gz"
                subVesselMaskFullPath = os.path.join(self.m_maskFullPath, subVesselMaskPath)
                shutil.copy(subVesselMaskFullPath, os.path.join(self.m_territoryInPath, subVesselMaskPath))
                



    def __init_territory_blender(self, segInfoInx : int) :
        segInfo = self.m_optionInfo.get_segmentinfo(segInfoInx)
        scriptFullPath = os.path.join(self.m_territoryInPath, f"tmpScript.py")

        organName = segInfo.Organ
        tmpStr = f"'{organName}'"

        iVesselCnt = segInfo.get_vesselinfo_count()
        for iVesselInx in range(0, iVesselCnt) :
            wholeVesselName = segInfo.get_vesselinfo_whole_vessel(iVesselInx)
            tmpStr = self.__attach_str(tmpStr, wholeVesselName)

            iStartInx = segInfo.get_vesselinfo_child_start(iVesselInx)
            iEndInx = segInfo.get_vesselinfo_child_end(iVesselInx)
            for iChildInx in range(iStartInx, iEndInx + 1) :
                tmpStr = self.__attach_str(tmpStr, f"{wholeVesselName}{iChildInx}")


        # Blender 스크립트를 Python 파일로 작성
        with open(scriptFullPath, 'w') as scriptFp:
            scriptFp.write(f""" 
import bpy
import os
listObjName = [{tmpStr}]
outputPath = '{self.m_territoryInPath}'
for objName in listObjName :
    if objName in bpy.data.objects:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.objects[objName].select_set(True)
        bpy.context.view_layer.objects.active = bpy.data.objects[objName]
        bpy.ops.export_mesh.stl(filepath=os.path.join(outputPath, objName + '.stl'), use_selection=True)
            """)

        cmd = f"{self.m_optionInfo.BlenderExe} -b {self.m_patientBlenderFullPath} --python {scriptFullPath}"
        os.system(cmd)
        # os.remove(scriptFullPathPath)
    def __init_territory_centerline(self, segInfoInx : int) :
        pass


    def __attach_str(self, target : str, src : str) -> str :
        tmpStr = f", '{src}'"
        target += tmpStr
        return target
        


if __name__ == '__main__' :
    multiprocessing.freeze_support()
    app = CCommonPipelineTerritory()
    app.init()
    app.process()
    app.clear()


print ("ok ..")

