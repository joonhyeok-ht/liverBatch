import sys
import os
import subprocess

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
fileAppPath = os.path.dirname(fileAbsPath)
fileToolPath = os.path.dirname(fileAppPath)
fileCommonPipelinePath = os.path.dirname(fileToolPath)

sys.path.append(fileAbsPath)
sys.path.append(fileAppPath)
sys.path.append(fileToolPath)
sys.path.append(fileCommonPipelinePath)

import Block.optionInfo as optionInfo
import data as data

# 옵션 경로 지정
optionPath = "C:/Users/hutom/Desktop/jh_test/CommonPipeline_10/CommonPipeline_10/option_liver_reg.json"
# .blender, result 폴더가 있는 recon result 경로 지정
resultPatientPath = "C:/Users/hutom/Desktop/jh_test/data/liver/SAMPLE123_out/SAMPLE123"
# processCL 이 있는 경로 지정
filePath = "C:/Users/hutom/Desktop/jh_test/CommonPipeline_10/CommonPipeline_10/processCL.py"


m_clInPath = resultPatientPath + "/SkelInfo/in"
m_clOutPath = resultPatientPath + "/SkelInfo/out"

m_optionInfo = optionInfo.COptionInfoSingle(optionPath)

DataInfo = optionInfo.CCLDataInfo()

DataInfo.OptionFullPath = optionPath
DataInfo.PatientPath = ""

clCnt = m_optionInfo.get_centerlineinfo_count()
if clCnt == 0 :
    #print("not found centerline info")
    pass
for clInx in range(0, clCnt) :
    clInfo = m_optionInfo.get_centerlineinfo(clInx)
    clParam = m_optionInfo.find_centerline_param(clInfo.CenterlineType)
    reconType = clInfo.get_input_recon_type()
    reconParam = m_optionInfo.find_recon_param(reconType)
    if reconParam is None :
        print(f"not found recon type : {reconType}")
        DataInfo.add_info(None, None, None)
    else :
        DataInfo.add_info(clInfo, clParam, reconParam)

print("-- Start Extraction Centerline --")
file = "clDataInfo.pkl"

for index in range(clCnt):
    pklFullPath = os.path.join(m_clInPath, file)

    data.CData.save_inst(pklFullPath, DataInfo)

    optionPath = os.path.dirname(DataInfo.OptionFullPath)
    shPath = os.path.join(optionPath, m_optionInfo.CL)
    print(f"clPath : {shPath}")
    print(f"pklFullPath : {pklFullPath}")
    print(f"--index : {str(index)}")

    args = [
        sys.executable,  
        filePath,
        "--file", pklFullPath,
        "--index", str(index)
    ]
    result = subprocess.run(args, capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    print("-- End Extraction Centerline --")    