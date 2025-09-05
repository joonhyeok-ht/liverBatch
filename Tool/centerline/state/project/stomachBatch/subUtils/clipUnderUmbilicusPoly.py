'''
File : clipUnderUmbilicusPoly.py
Version : 2024_04_16
created by jys
'''
import sys

import json
import SimpleITK as sitk
import os 
import vtk

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileStatePath = os.path.dirname(os.path.dirname(os.path.dirname(fileAbsPath)))
fileAppPath = os.path.dirname(fileStatePath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileStatePath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

from Algorithm.scoReg import CRegTransform
import Algorithm.scoUtil as scoUtil
import Block.niftiContainer as niftiContainer
import Block.optionInfo as optionInfo
import AlgUtil.algImage as algImage


'''
Name
    - ClipUnderUmbilicusPolyBlock  
Input
    - "InputStlPath"        : the folder including Skin or Abdominal Wall recon(STL) files
    - "InputSliceID"        : slice id(nifti) of 10 centimeters below the umbilicus
    - "InputPhyInfo"        : physical info json path of nifti files 

'''

class CClipUnderUmbilicusPoly() :
    m_maskSkinName = "Skin"
    m_stlSkinName = "anatomy_skin"
    m_maskAbdWallName = "Abdominal_wall"
    m_stlAbdWallName = "anatomy_abdominal"
    TAG = "CClipUnderUmbilicusPoly"

    def __init__(self) -> None :
        self.m_inputStlPath = ""
        self.m_inputSliceID = 0
        self.m_inputPhyInfo = ""
        self.m_inputNiftiContainer = None
        self.m_json = None


    def process(self) -> bool:
        # json loading
        if self.InputPhyInfo != "" :
            if os.path.exists(self.InputPhyInfo) == True :
                with open(self.InputPhyInfo, 'r') as fp :
                    self.m_json = json.load(fp)
            else:
                print(f"{self.TAG}-ERROR : {self.InputPhyInfo} Not Exist.")
                return False

        if self.m_inputSliceID > 0:
            
            listNiftiInfo = self.InputNiftiContainer.find_nifti_info_list_by_name(self.m_maskSkinName)
            if listNiftiInfo is None :
                return False

            niftiInfo = listNiftiInfo[0]
            phase = niftiInfo.MaskInfo.Phase
            phaseInfo = self.InputNiftiContainer.find_phase_info(phase)
            
            z_offset = phaseInfo.Offset.flatten()[2]
            
            skinNiftiInfoList = self.InputNiftiContainer.find_nifti_info_list_by_name(self.m_maskSkinName)
            if skinNiftiInfoList == None:
                return False
            #skinPath = os.path.join(self.InputStlPath, f"{self.m_stlSkinName}.stl")
            skinMaskPath = skinNiftiInfoList[0].FullPath
            if os.path.exists(skinMaskPath) :
                self._clip_under_umbilicus(skinMaskPath, self.m_stlSkinName, z_offset)
            else:
                print(f"{self.TAG}-ERROR : {skinMaskPath} Not Exist.")
                return False
            
            abdwallNiftiInfoList = self.InputNiftiContainer.find_nifti_info_list_by_name(self.m_maskAbdWallName)
            if abdwallNiftiInfoList == None:
                return False
            abdWallMaskPath = abdwallNiftiInfoList[0].FullPath
            #abdwallPath = os.path.join(self.InputStlPath, f"{self.m_stlAbdWallName}.stl")
            if os.path.exists(abdWallMaskPath) :
                self._clip_under_umbilicus(abdWallMaskPath, self.m_stlAbdWallName, z_offset)
            else:
                print(f"{self.TAG}-ERROR : {abdWallMaskPath} Not Exist.")
                return False
        return True                    

    def clear(self) :
        self.m_inputStlPath = ""
        self.m_inputSliceID = 0  
        self.m_inputPhyInfo = ""
        self.m_inputNiftiContainer = None
        if self.m_json != None :
            self.m_json.clear()

    def _clip_under_umbilicus(self, MaskPath : str, stlName : str, offset : float) -> bool :
        inputSTL = os.path.join(self.InputStlPath, f"{stlName}.stl")
        
        outputSTL = inputSTL
        #outputSTL = stlPath
        inputSliceID = self.InputSliceID

        reader = vtk.vtkSTLReader()
        reader.SetFileName(inputSTL)
        reader.Update()
        polydata = reader  #vtkPolyData object

        # print(f"polydata center : {polydata.GetOutput().GetCenter()}")

        sitkImg = scoUtil.CScoUtilSimpleITK.load_image(MaskPath, None)
        mask = CRegTransform.create_buffer3d(sitkImg)
        
        # dim_z = self.m_json["NiftiList"][f"{stlName}.nii.gz"]["shape"][2]
        # spacing_z = self.m_json["NiftiList"][f"{stlName}.nii.gz"]["spacing"][2]
        
        dim_z = mask.Shape[2]
        origin_z = sitkImg.GetOrigin()[2]
        spacing_z = sitkImg.GetSpacing()[2]
        
        _origin = [0.0, 0.0, 0.0]
        _normal = [0.0, 0.0, -1.0] # case z-flip obj
        #_normal = [0.0, 0.0, 1.0] # case no-flip obj

        # spacing_z = 0.7999999
        # dim_z = 588
        # print(f"dim_z : {dim_z}")
        # print(f"spacing_z : {spacing_z}")
        
        #_origin[2] = ((inputSliceID * spacing_z) - (dim_z/2 * spacing_z))  # case z-flip obj
        _origin[2] = -origin_z - (inputSliceID * spacing_z) - offset
        #_origin[2] = (dim_z/2 - inputSliceID) * spacing_z  # case no-flip obj
        # print(f"_origin[2]new = {_origin[2]}")

        plane = vtk.vtkPlane()
        plane.SetOrigin(_origin[0],_origin[1],_origin[2])
        plane.SetNormal(_normal[0],_normal[1],_normal[2])
        clipper = vtk.vtkClipPolyData()
        clipper.SetInputData(polydata.GetOutput())
        clipper.SetClipFunction(plane)
        clipper.SetValue(0) #new add
        clipper.Update()

        writer = vtk.vtkSTLWriter()
        writer.SetInputData(clipper.GetOutput())
        writer.SetFileTypeToBinary()
        writer.SetFileName(f'{outputSTL}') # ---> !!!!!!!!!!!!!!!!!!!!! 0 체크해야함
        writer.Write()
        clipper.GetOutput().ReleaseData()
        writer = None
        
        return True

    @property
    def InputStlPath(self) :
        return self.m_inputStlPath
    @InputStlPath.setter
    def InputStlPath(self, inputStlPath : str) :
        self.m_inputStlPath = inputStlPath
    @property
    def InputPhyInfo(self) :
        return self.m_inputPhyInfo
    @InputPhyInfo.setter
    def InputPhyInfo(self, inputPhyInfo : str) :
        self.m_inputPhyInfo = inputPhyInfo
    @property
    def InputSliceID(self) :
        return self.m_inputSliceID
    @InputSliceID.setter
    def InputSliceID(self, inputSliceID : int) :
        self.m_inputSliceID = inputSliceID
    @property
    def InputNiftiContainer(self) -> niftiContainer.CNiftiContainer :
        return self.m_inputNiftiContainer
    @InputNiftiContainer.setter
    def InputNiftiContainer(self, inputNiftiContainer : niftiContainer.CNiftiContainer) :
        self.m_inputNiftiContainer = inputNiftiContainer

if __name__=='__main__' :
    
    option_path = "C:/Users/hutom/Desktop/jh_test/CommonPipelines/CommonPipeline_10_0509_lungkidney/CommonPipeline_10_0509_lungkidney/option.json"
    outputMaskPath = "C:/Users/hutom/Desktop/jh_test/data/stomach/01011ug_129/OutTemp/01011ug_129/Mask"
    
    m_option_info = optionInfo.COptionInfoSingle(option_path)
    
    niftiContainerBlock = niftiContainer.CNiftiContainerTerritory()
    niftiContainerBlock.InputOptionInfo = m_option_info
    niftiContainerBlock.InputPath = outputMaskPath 
    niftiContainerBlock.process()
    
    clippingCls = CClipUnderUmbilicusPoly()
    clippingCls.InputStlPath = "C:/Users/hutom/Desktop/jh_test/data/stomach/01011ug_129/OutTemp/01011ug_129/Result"
    clippingCls.InputNiftiContainer = niftiContainerBlock
    clippingCls.InputSliceID = 453
    clippingCls.process()
    
    print("!!!!!!!!!!done!!!!!!!!!!!!!!!!!!!!!!!!!!!!")