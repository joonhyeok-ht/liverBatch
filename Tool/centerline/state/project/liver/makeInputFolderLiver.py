'''
File : makeInputFolder.py
Version : 2025_03_27
'''
# 24.11.01 : add Lung
# 25.03.27 : 25'3월 기준으로 output 폴더구조 변경, nifti파일만 따로 zip으로 묶는기능 추가

import datetime as dt
import os
import shutil
import sys
from distutils.dir_util import copy_tree

tmpPath = os.path.abspath(os.path.dirname(__file__))
sys.path.append(tmpPath)


class CMakeInputFolder :
    TAG = "[MakeInputFolder] "
    eMode_Stomach = 1
    eMode_Kidney = 2
    eMode_Lung = 3
    eMode_Liver = 4
    sZip_Dicom = "DICOM.zip" #"1.zip"
    sZip_EAP_Nifti = "AP.zip" #"2.zip"
    sZip_AP_Nifti = "AP.zip" #"2.zip"
    sZip_PP_Nifti = "PP.zip" #"3.zip"
    sZip_DP_Nifti = "DP.zip" #"4.zip"
    sZip_HVP_Nifti = "HVP.zip" #"4.zip"
    sZip_MR_Nifti = "MR.zip" #"4.zip"

    def __init__(self) -> None:
        self.m_patientID = ""
        self.m_zipPath = ""
        self.m_mode = ""

        self.m_dicomEAPPath = ""
        self.m_dicomAPPath = ""
        self.m_dicomPPPath = ""
        self.m_dicomHVPPath = ""
        self.m_dicomMRPath = ""

        self.m_outputFullPath = "" # DataRootPath

    def _clear(self) :
        self.m_patientID = ""
        self.m_zipPath = ""
        self.m_mode = ""

        self.m_dicomEAPPath = ""
        self.m_dicomAPPath = ""
        self.m_dicomPPPath = ""
        self.m_dicomHVPPath = ""
        self.m_dicomMRPath = ""

    def process(self) -> bool :
        files = os.listdir(self.m_zipPath)
        zipfiles = [file for file in files if file.endswith(".zip")]
        if len(zipfiles) == 0 :
            print(self.TAG, "ERROR - not found zip files.")
            return False
      
        ## create output folders by mode
        post_fix = "stomach"
        if self.m_mode == self.eMode_Kidney:
            post_fix = "kidney"
        elif self.m_mode == self.eMode_Lung:
            post_fix = "lung"
        elif self.m_mode == self.eMode_Liver:
            post_fix = "liver"
        # parentdir = os.path.dirname(self.m_zipPath)
        # outfolder_root = os.path.join(parentdir, f"{os.path.basename(self.m_zipPath)}_{post_fix}")
        nowdate = dt.datetime.now()
        timestr = nowdate.strftime("%m%d_%H%M%S")
        huid = os.path.basename(self.m_zipPath)
        outfolder_root = os.path.join(self.m_zipPath, f"dataRoot_{post_fix}_{timestr}", huid)
        if not os.path.exists(outfolder_root) :
            os.mkdir(os.path.join(self.m_zipPath, f"dataRoot_{post_fix}_{timestr}")) #중간디렉토리생성
            os.mkdir(outfolder_root)
        
        self.m_patientID = huid
        self.m_outputFullPath = outfolder_root

        ## 폴더 구조 생성
        if self.m_mode == self.eMode_Kidney :
            self._create_folders_kidney(outfolder_root)
        elif self.m_mode == self.eMode_Stomach :
            self._create_folders_stomach(outfolder_root)
        elif self.m_mode == self.eMode_Lung :
            self._create_folders_lung(outfolder_root)
        elif self.m_mode == self.eMode_Liver:
            self._create_folders_liver(outfolder_root)
        
        
        ## Unzip and Copy DICOM files
        dicom_zip_path = os.path.join(self.m_zipPath, self.sZip_Dicom)
        if os.path.exists(dicom_zip_path) :
            shutil.unpack_archive(os.path.join(self.m_zipPath, self.sZip_Dicom), 
                                os.path.join(self.m_zipPath, "unzip"),
                                    "zip")
            folderlist = os.listdir(os.path.join(self.m_zipPath, "unzip"))
            for folder in folderlist :
                # copy Dicoms
                copy_tree(os.path.join(self.m_zipPath,"unzip",folder),
                    os.path.join(outfolder_root, "01_DICOM", folder))
            # # copy Dicoms            
            # # copy zipPath/unzip/ap/*  to  out_root/01_DICOM/AP/
            # copy_tree(os.path.join(self.m_zipPath,"unzip","ap"),
            #         os.path.join(outfolder_root, "01_DICOM", "AP"))
            
            # if self.m_mode == self.eMode_Kidney or self.m_mode == self.eMode_Stomach:
            # # copy zipPath/unzip/pp/*  to  out_root/01_DICOM/PP/
            #     copy_tree(os.path.join(self.m_zipPath,"unzip","pp"),
            #             os.path.join(outfolder_root, "01_DICOM", "PP"))
            
            # if self.m_mode == self.eMode_Kidney:
            #     # copy zipPath/unzip/dp/*  to  out_root/01_DICOM/DP/
            #     copy_tree(os.path.join(self.m_zipPath,"unzip","dp"),
            #             os.path.join(outfolder_root, "01_DICOM", "DP"))
        
        
            # delete zipPath/unzip/*
            shutil.rmtree(os.path.join(self.m_zipPath, "unzip"))

        
        nifti_folders = []
        ## Unzip and Copy Nifti files
        # AP
        ap_nifti_zip_path = os.path.join(self.m_zipPath, self.sZip_AP_Nifti)
        if os.path.exists(ap_nifti_zip_path) :
            # unzip AP.zip to out_root/02_SAVE/01_Mask/AP
            dst_ap_path = os.path.join(outfolder_root, "02_SAVE", "01_MASK", "Mask_AP")
            shutil.unpack_archive(ap_nifti_zip_path, dst_ap_path, "zip")
            nifti_folders.append(dst_ap_path)
        # PP
        pp_nifti_zip_path = os.path.join(self.m_zipPath, self.sZip_PP_Nifti)
        if os.path.exists(pp_nifti_zip_path) :
            # unzip PP.zip to out_root/02_SAVE/01_Mask/PP
            dst_pp_path = os.path.join(outfolder_root, "02_SAVE", "01_MASK", "Mask_PP")
            shutil.unpack_archive(pp_nifti_zip_path, dst_pp_path, "zip")
            nifti_folders.append(dst_pp_path)
        # DP    
        if self.m_mode == self.eMode_Kidney:
            dp_nifti_zip_path = os.path.join(self.m_zipPath, self.sZip_DP_Nifti)
            if os.path.exists(dp_nifti_zip_path) : 
                # unzip DP.zip to out_root/02_SAVE/01_Mask/DP
                dst_dp_path = os.path.join(outfolder_root, "02_SAVE", "01_MASK", "Mask_DP")
                shutil.unpack_archive(dp_nifti_zip_path, dst_dp_path, "zip")
                nifti_folders.append(dst_dp_path)
        elif self.m_mode == self.eMode_Liver:
            hvp_nifti_zip_path = os.path.join(self.m_zipPath, self.sZip_HVP_Nifti)
            if os.path.exists(hvp_nifti_zip_path) : 
                # unzip hvp.zip to out_root/02_SAVE/01_Mask/HVP
                dst_hvp_path = os.path.join(outfolder_root, "02_SAVE", "01_MASK", "Mask_HVP")
                shutil.unpack_archive(hvp_nifti_zip_path, dst_hvp_path, "zip")
                nifti_folders.append(dst_hvp_path)
                
            mr_nifti_zip_path = os.path.join(self.m_zipPath, self.sZip_MR_Nifti)
            if os.path.exists(mr_nifti_zip_path) : 
                dst_mr_path = os.path.join(outfolder_root, "02_SAVE", "01_MASK", "Mask_MR")
                shutil.unpack_archive(mr_nifti_zip_path, dst_mr_path, "zip")
                nifti_folders.append(dst_mr_path)

        ## nifti 파일들만 모아서 재압축하여 zip 으로 생성하기
        data_root_path = os.path.dirname(self.m_outputFullPath)
        zip_name = os.path.join(data_root_path, f"{huid}_mask_miop")
        dir_tmp = os.path.join(data_root_path, "dir_tmp")
        os.makedirs(dir_tmp, exist_ok=True)
        # copy mask folder to dir_tmp
        for folder in nifti_folders:
            shutil.copytree(folder, os.path.join(dir_tmp, os.path.basename(folder)))
        # make zip
        shutil.make_archive(zip_name, 'zip', dir_tmp)
        # remove temporary folder
        shutil.rmtree(dir_tmp)
        print(self.TAG, f"{zip_name}.zip is created.")

        ## recon을 위해 각 마스크를 Mask폴더에 복사하기 (Recon Process 안에서 하기로 함.)
        # if self.m_mode == self.eMode_Lung :
        #     files = os.listdir(dst_ap_path)
        #     for file_name in files :
        #         source_file = os.path.join(dst_ap_path, file_name)
        #         destination_file = os.path.join(self.m_maskCpyPath, file_name)

        #         # 파일인지 확인 후 복사
        #         if os.path.isfile(source_file):
        #             shutil.copy2(source_file, destination_file)
        return True
    
    def get_data_root_path(self) -> str:
        return os.path.dirname(self.m_outputFullPath)
    
    def _create_folders_lung(self, out_root) -> bool :
        self.m_dicomEAPPath = os.path.join(out_root, "01_DICOM", "AP")
        os.makedirs(self.m_dicomEAPPath, exist_ok=True)

        save_path = os.path.join(out_root, "02_SAVE")
        os.makedirs(save_path, exist_ok=True)
        
        mask_path = os.path.join(save_path, "01_MASK", "AP")
        os.makedirs(mask_path, exist_ok=True)
        blender_path = os.path.join(save_path, "02_BLENDER_SAVE")
        os.makedirs(blender_path, exist_ok=True)
        # auto01_path = os.path.join(blender_path, "Auto01_Recon")
        # os.makedirs(auto01_path, exist_ok=True)
        # auto02_path = os.path.join(blender_path, "Auto02_Mesh_Cleanup")
        # os.makedirs(auto02_path, exist_ok=True)

        pneumo_path = os.path.join(save_path, "03_PNEUMO_SAVE")
        os.makedirs(pneumo_path, exist_ok=True)

        # recon을 위해 huid 아래에 Mask 폴더를 만들어 마스크를 복사 (=>Recon 단계에서 하기로함.)
        # self.m_maskCpyPath = os.path.join(out_root, "Mask")
        # os.makedirs(self.m_maskCpyPath, exist_ok=True)
           
        return True
    
    def _create_folders_liver(self, out_root) -> bool :
        self.m_dicomAPPath = os.path.join(out_root, "01_DICOM", "AP")
        os.makedirs(self.m_dicomAPPath, exist_ok=True)
        self.m_dicomPPPath = os.path.join(out_root, "01_DICOM", "PP")
        os.makedirs(self.m_dicomPPPath, exist_ok=True)    
        self.m_dicomHVPPath = os.path.join(out_root, "01_DICOM", "HVP")
        os.makedirs(self.m_dicomHVPPath, exist_ok=True)    
        self.m_dicomMRPath = os.path.join(out_root, "01_DICOM", "MR")
        os.makedirs(self.m_dicomMRPath, exist_ok=True)  

        save_path = os.path.join(out_root, "02_SAVE")
        os.makedirs(save_path, exist_ok=True)
        
        mask_path = os.path.join(save_path, "01_MASK", "Mask_AP")
        os.makedirs(mask_path, exist_ok=True)
        mask_path = os.path.join(save_path, "01_MASK", "Mask_PP")
        os.makedirs(mask_path, exist_ok=True)
        mask_path = os.path.join(save_path, "01_MASK", "Mask_HVP")
        os.makedirs(mask_path, exist_ok=True)
        mask_path = os.path.join(save_path, "01_MASK", "Mask_MR")
        os.makedirs(mask_path, exist_ok=True)
        blender_path = os.path.join(save_path, "02_BLENDER_SAVE")
        os.makedirs(blender_path, exist_ok=True)
        auto01_path = os.path.join(blender_path, "Auto01_Recon")
        os.makedirs(auto01_path, exist_ok=True)
        auto02_path = os.path.join(blender_path, "Auto02_Overlap")
        os.makedirs(auto02_path, exist_ok=True)
        auto03_path = os.path.join(blender_path, "Auto03_Separate_Cleanup")
        os.makedirs(auto03_path, exist_ok=True)

        pneumo_path = os.path.join(save_path, "03_PNEUMO_SAVE")
        os.makedirs(pneumo_path, exist_ok=True)
        return True
    
    def _create_folders_stomach(self, out_root) -> bool :
        self.m_dicomEAPPath = os.path.join(out_root, "01_DICOM", "AP")
        os.makedirs(self.m_dicomEAPPath, exist_ok=True)
        self.m_dicomPPPath = os.path.join(out_root, "01_DICOM", "PP")
        os.makedirs(self.m_dicomPPPath, exist_ok=True)    

        save_path = os.path.join(out_root, "02_SAVE")
        os.makedirs(save_path, exist_ok=True)
        
        mask_path = os.path.join(save_path, "01_MASK", "Mask_AP")
        os.makedirs(mask_path, exist_ok=True)
        mask_path = os.path.join(save_path, "01_MASK", "Mask_PP")
        os.makedirs(mask_path, exist_ok=True)
        blender_path = os.path.join(save_path, "02_BLENDER_SAVE")
        os.makedirs(blender_path, exist_ok=True)
        auto01_path = os.path.join(blender_path, "Auto01_Recon")
        os.makedirs(auto01_path, exist_ok=True)
        auto02_path = os.path.join(blender_path, "Auto02_Overlap")
        os.makedirs(auto02_path, exist_ok=True)
        auto03_path = os.path.join(blender_path, "Auto03_MeshClean")
        os.makedirs(auto03_path, exist_ok=True)

        pneumo_path = os.path.join(save_path, "03_PNEUMO_SAVE")
        os.makedirs(pneumo_path, exist_ok=True)
           
        return True
    
    def _create_folders_kidney(self, out_root) -> bool :
        self.m_dicomAPPath = os.path.join(out_root, "01_DICOM", "AP")
        os.makedirs(self.m_dicomAPPath, exist_ok=True)
        self.m_dicomPPPath = os.path.join(out_root, "01_DICOM", "PP")
        os.makedirs(self.m_dicomPPPath, exist_ok=True)    
        self.m_dicomHVPPath = os.path.join(out_root, "01_DICOM", "DP")
        os.makedirs(self.m_dicomHVPPath, exist_ok=True)    

        save_path = os.path.join(out_root, "02_SAVE")
        os.makedirs(save_path, exist_ok=True)
        
        mask_path = os.path.join(save_path, "01_MASK", "Mask_AP")
        os.makedirs(mask_path, exist_ok=True)
        mask_path = os.path.join(save_path, "01_MASK", "Mask_PP")
        os.makedirs(mask_path, exist_ok=True)
        mask_path = os.path.join(save_path, "01_MASK", "Mask_DP")
        os.makedirs(mask_path, exist_ok=True)
        blender_path = os.path.join(save_path, "02_BLENDER_SAVE")
        os.makedirs(blender_path, exist_ok=True)
        auto01_path = os.path.join(blender_path, "Auto01_Recon")
        os.makedirs(auto01_path, exist_ok=True)
        auto02_path = os.path.join(blender_path, "Auto02_Overlap")
        os.makedirs(auto02_path, exist_ok=True)
        auto03_path = os.path.join(blender_path, "Auto03_Separate_Cleanup")
        os.makedirs(auto03_path, exist_ok=True)

        pneumo_path = os.path.join(save_path, "03_PNEUMO_SAVE")
        os.makedirs(pneumo_path, exist_ok=True)
        return True
    
    @property
    def PatientID(self) :
        return self.m_patientID
    @PatientID.setter
    def PatientID(self, patientID : str) :
        self.m_patientID = patientID
    @property
    def ZipPath(self) :
        return self.m_zipPath
    @ZipPath.setter
    def ZipPath(self, zipPath : str) :
        self.m_zipPath = zipPath
    @property
    def FolderMode(self) :
        return self.m_mode
    @FolderMode.setter
    def FolderMode(self, mode : str) :
        self.m_mode = mode

if __name__ == "__main__" :
    test = CMakeInputFolder()
    test.ZipPath = "D:\\jys\\StomachKidney_newfolder\\zippath" #01014urk_4input"
    test.FolderMode = test.eMode_Kidney #test.eMode_Kidney  #test.eMode_Stomach
    test.process()

    

    