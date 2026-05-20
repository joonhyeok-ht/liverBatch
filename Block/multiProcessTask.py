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
        print(f"multi-process cpu count : {self.m_cpuCnt}")
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


class CMultiProcessTaskProgress:
    def __init__(self) -> None:
        self.m_cpuCnt = multiprocessing.cpu_count()
        self.m_listTargetIndex = []
        self.m_sharedList = None

    def process(self, task, listParam: list,
                progress_callback=None,          # (percent:int, status:str) or (percent:int)
                is_interrupted=None,             # callable -> bool
                status_prefix="",
                chunksize=1):
        """
        기존과 동일하게 호출 가능:
            super().process(self._task, listParam)
        progress가 필요하면:
            super().process(task, listParam, progress_callback=..., is_interrupted=..., status_prefix="...")
        """
        total = len(listParam)
        if total == 0:
            if progress_callback:
                try:
                    progress_callback(100, f"{status_prefix}")
                except TypeError:
                    progress_callback(100)
            return True

        ctx = multiprocessing.get_context("spawn")  # Windows 안정
        pool = ctx.Pool(processes=self.m_cpuCnt)

        done = 0
        try:
            for _ in pool.imap_unordered(task, listParam, chunksize=chunksize):
                done += 1

                if progress_callback:
                    percent = int(done * 100 / total)
                    # progress_callback 시그니처가 (value) 인지 (value, status)인지 둘 다 대응
                    try:
                        progress_callback(percent, f"{status_prefix}")
                    except TypeError:
                        progress_callback(percent)

                if is_interrupted and is_interrupted():
                    pool.terminate()
                    pool.join()
                    return False

            pool.close()
            pool.join()
            return True

        except Exception:
            pool.terminate()
            pool.join()
            raise

    # protected
    def _alloc_shared_list(self, iCnt : int) :
        manager = multiprocessing.Manager()
        self.m_sharedList = manager.list([None] * iCnt)

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


if __name__ == '__main__' :
    pass


# print ("ok ..")

