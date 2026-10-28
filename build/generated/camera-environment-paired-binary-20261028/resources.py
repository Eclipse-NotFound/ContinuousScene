"""Windows-only preflight and a memory limit on this Python process alone."""
import ctypes as C
from ctypes import wintypes as W
import os

MIB = 1024 ** 2
MINIMUM_COMMIT = 768 * MIB
PROCESS_LIMIT = 512 * MIB


class Performance(C.Structure):
    _fields_ = [('cb', W.DWORD)] + [(n, C.c_size_t) for n in (
        'CommitTotal', 'CommitLimit', 'CommitPeak', 'PhysicalTotal', 'PhysicalAvailable',
        'SystemCache', 'KernelTotal', 'KernelPaged', 'KernelNonpaged', 'PageSize')] + [
        ('HandleCount', W.DWORD), ('ProcessCount', W.DWORD), ('ThreadCount', W.DWORD)]


class Counters(C.Structure):
    _fields_ = [('cb', W.DWORD), ('PageFaultCount', W.DWORD)] + [(n, C.c_size_t) for n in (
        'PeakWorkingSetSize', 'WorkingSetSize', 'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage',
        'QuotaPeakNonPagedPoolUsage', 'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage')]


class BasicLimits(C.Structure):
    _fields_ = [('PerProcessUserTimeLimit', C.c_longlong), ('PerJobUserTimeLimit', C.c_longlong),
                ('LimitFlags', W.DWORD), ('MinimumWorkingSetSize', C.c_size_t),
                ('MaximumWorkingSetSize', C.c_size_t), ('ActiveProcessLimit', W.DWORD),
                ('Affinity', C.c_size_t), ('PriorityClass', W.DWORD), ('SchedulingClass', W.DWORD)]


class IO(C.Structure):
    _fields_ = [(n, C.c_ulonglong) for n in ('ReadOperationCount', 'WriteOperationCount',
                'OtherOperationCount', 'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]


class ExtendedLimits(C.Structure):
    _fields_ = [('BasicLimitInformation', BasicLimits), ('IoInfo', IO),
                ('ProcessMemoryLimit', C.c_size_t), ('JobMemoryLimit', C.c_size_t),
                ('PeakProcessMemoryUsed', C.c_size_t), ('PeakJobMemoryUsed', C.c_size_t)]


class ResourceGuard:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('This controlled build requires Windows memory accounting')
        self.k = C.WinDLL('kernel32', use_last_error=True)
        self.p = C.WinDLL('psapi', use_last_error=True)
        self.k.GetCurrentProcess.restype = W.HANDLE
        self.k.CreateJobObjectW.argtypes = [C.c_void_p, W.LPCWSTR]
        self.k.CreateJobObjectW.restype = W.HANDLE
        self.k.SetInformationJobObject.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD]
        self.k.SetInformationJobObject.restype = W.BOOL
        self.k.QueryInformationJobObject.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.c_void_p]
        self.k.QueryInformationJobObject.restype = W.BOOL
        self.k.AssignProcessToJobObject.argtypes = [W.HANDLE, W.HANDLE]
        self.k.AssignProcessToJobObject.restype = W.BOOL
        self.k.CloseHandle.argtypes = [W.HANDLE]
        self.k.CloseHandle.restype = W.BOOL
        self.p.GetPerformanceInfo.argtypes = [C.POINTER(Performance), W.DWORD]
        self.p.GetPerformanceInfo.restype = W.BOOL
        self.p.GetProcessMemoryInfo.argtypes = [W.HANDLE, C.POINTER(Counters), W.DWORD]
        self.p.GetProcessMemoryInfo.restype = W.BOOL
        self.process = self.k.GetCurrentProcess()
        self.job = None
        self.samples = []
        before = self.sample('before-job-limit')
        if before['availableCommit'] < MINIMUM_COMMIT:
            raise RuntimeError('Build requires at least 768 MiB available system commit: ' + str(before))
        self.job = self.k.CreateJobObjectW(None, None)
        if not self.job:
            raise C.WinError(C.get_last_error())
        limits = ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
        limits.ProcessMemoryLimit = PROCESS_LIMIT
        try:
            self.check(self.k.SetInformationJobObject(self.job, 9, C.byref(limits), C.sizeof(limits)))
            # New job, current Python only. No children, kill flag, global policy or foreign process.
            self.check(self.k.AssignProcessToJobObject(self.job, self.process))
            readback = ExtendedLimits()
            self.check(self.k.QueryInformationJobObject(self.job, 9, C.byref(readback), C.sizeof(readback), None))
            if not readback.BasicLimitInformation.LimitFlags & 0x100 or readback.ProcessMemoryLimit != PROCESS_LIMIT:
                raise RuntimeError('Process memory limit was not applied')
            self.sample('job-limit-applied')
        except BaseException:
            self.close()
            raise

    @staticmethod
    def check(ok):
        if not ok:
            raise C.WinError(C.get_last_error())

    def sample(self, phase):
        perf, proc = Performance(), Counters()
        perf.cb, proc.cb = C.sizeof(perf), C.sizeof(proc)
        self.check(self.p.GetPerformanceInfo(C.byref(perf), C.sizeof(perf)))
        self.check(self.p.GetProcessMemoryInfo(self.process, C.byref(proc), C.sizeof(proc)))
        row = dict(phase=phase, availableCommit=(perf.CommitLimit-perf.CommitTotal)*perf.PageSize,
                   availablePhysical=perf.PhysicalAvailable*perf.PageSize,
                   privateBytes=proc.PrivateUsage, peakPagefileUsage=proc.PeakPagefileUsage,
                   workingSetBytes=proc.WorkingSetSize)
        if row['privateBytes'] > PROCESS_LIMIT:
            raise RuntimeError('Own process private memory exceeds 512 MiB')
        self.samples.append(row)
        return row

    def receipt(self):
        peak = None
        if self.job:
            info = ExtendedLimits()
            self.check(self.k.QueryInformationJobObject(self.job, 9, C.byref(info), C.sizeof(info), None))
            peak = info.PeakProcessMemoryUsed
            if peak > PROCESS_LIMIT:
                raise RuntimeError('Own job reports process memory above configured limit')
        return dict(minimumAvailableCommit=MINIMUM_COMMIT, ownProcessMemoryLimit=PROCESS_LIMIT,
                    ownJobLimitApplied=bool(self.job), jobPeakProcessMemoryUsed=peak, samples=self.samples,
                    gameMemoryGateChanged=False, foreignProcessesChanged=False)

    def close(self):
        if self.job:
            self.k.CloseHandle(self.job)
            self.job = None
