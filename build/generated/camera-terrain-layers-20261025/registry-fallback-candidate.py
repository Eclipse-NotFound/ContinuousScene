"""Proposed read-only PID-identity fallback. Not installed into shared tools.

The live registry fails closed when OpenProcess cannot read a reused system PID.
This candidate supplements identity evidence through Windows CIM. It never
stops a process, edits the registry, or treats a failed query as process exit.
"""
import json
import subprocess

PREFIX='cim-microseconds:'

def cim_token(pid):
    pid=int(pid)
    if pid<=0:return 'unknown'
    command=("$ErrorActionPreference='Stop'; "
             "$p=@(Get-CimInstance Win32_Process -Filter 'ProcessId="+str(pid)+"'); "
             "if($p.Count -ne 1 -or -not $p[0].CreationDate){throw 'No unique creation identity'}; "
             "[string]$p[0].CreationDate.ToUniversalTime().ToFileTimeUtc()")
    try:
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],
            text=True,capture_output=True,timeout=15,check=True,
            creationflags=subprocess.CREATE_NO_WINDOW)
        value=result.stdout.strip()
        if not value.isdecimal() or int(value)<=0:return 'unknown'
        # Win32_Process reports microseconds; native FILETIME has 100ns digits.
        return PREFIX+str(int(value)//10)
    except (OSError,ValueError,subprocess.SubprocessError):return 'unknown'

def microseconds(token):
    if not isinstance(token,str) or token=='unknown':return None
    value=token[len(PREFIX):] if token.startswith(PREFIX) else token
    if not value.isdecimal():return None
    return int(value) if token.startswith(PREFIX) else int(value)//10

def different_identity(before,after):
    a,b=microseconds(before),microseconds(after)
    return a is not None and b is not None and a!=b

if __name__=='__main__':
    before='134374159796693439'
    assert not different_identity(before,PREFIX+str(int(before)//10))
    assert not different_identity('unknown',PREFIX+'13437415979669343')
    assert not different_identity(before,'unknown')
    assert not different_identity(before,'malformed')
    assert different_identity(before,PREFIX+str(int(before)//10+1))
    actual=cim_token(63256)
    print(json.dumps(dict(candidateOnly=True,registryModified=False,pid=63256,
        recordedToken=before,currentToken=actual,different=different_identity(before,actual))))
