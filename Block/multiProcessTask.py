import sys
import os
import multiprocessing
# import multiprocessing.util as mputil

fileAbsPath = os.path.abspath(os.path.dirname(__file__))
solutionPath = os.path.dirname(fileAbsPath)
sys.path.append(fileAbsPath)
sys.path.append(solutionPath)



class CMultiProcessTask : 
    def __init__(self) -> None :
        self.m_cpuCnt = multiprocessing.cpu_count()
        self.m_listTargetIndex = []
        self.m_sharedList = None
        #print(f"multi-process cpu count : {self.m_cpuCnt}")
    def process(self, task, listParam : list) :
        # mputil.log_to_stderr(None)  # 디버그 출력 비활성화
        processPool = multiprocessing.Pool(processes=self.m_cpuCnt)
        processPool.map(task, listParam)
        processPool.close()
        processPool.join()
    def clear(self) :
        self.m_cpuCnt = 0
        self.m_listTargetIndex.clear()
        self.m_sharedList = None


    def add_target_index(self, targetIndex : int) :
        self.m_listTargetIndex.append(targetIndex)
    def get_target_index(self, inx : int) -> int :
        return self.m_listTargetIndex[inx]
    def get_target_index_count(self) -> int :
        return len(self.m_listTargetIndex)
    def get_shared_list(self) -> list :
        return list(self.m_sharedList)
    

    # protected
    def _alloc_shared_list(self, iCnt : int) :
        manager = multiprocessing.Manager()
        self.m_sharedList = manager.list([None] * iCnt)




if __name__ == '__main__' :
    pass


# print ("ok ..")

