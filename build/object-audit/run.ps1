param([ValidateSet('random_mane','random_plant')][string]$Map='random_plant',[ValidateSet('baseline','candidate')][string]$Variant='baseline',[string]$EvidenceName,[int]$TimeoutSeconds=240,[int]$WaitForIdleSeconds=0,[switch]$AllowOtherTests)
$ErrorActionPreference='Stop'
$objectMod=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$objectRoot=(Resolve-Path -LiteralPath (Join-Path $objectMod '../..')).Path
$objectOut=Join-Path $objectMod 'build/generated/object-audit-20261019'
$objectRuntime=Join-Path $objectOut 'runtime'
if(-not $EvidenceName){$EvidenceName='objects-'+$Variant+'-'+$Map.Replace('_','-')+'-'+(Get-Date -Format 'HHmmss')}
if($EvidenceName -notmatch '^[a-z0-9-]+$'){throw 'Invalid evidence name'}
$objectEvidence=Join-Path $objectMod ('knowledge/experiments/evidence/'+$EvidenceName)
if(Test-Path -LiteralPath $objectEvidence){throw 'Evidence already exists'}
$objectDescriptor=Join-Path $objectRuntime 'application.xml'
[xml]$objectXml=Get-Content -LiteralPath $objectDescriptor -Raw
if($objectXml.application.id -ne 'pfe-modsettings-continuous-objects-01a151d4'){throw 'Invalid isolation ID'}
$objectIdleStart=Get-Date
$objectOtherPids=@()
while(@(Get-Process -Name adl64 -ErrorAction SilentlyContinue).Count){
    if($AllowOtherTests){
        $objectOthers=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'adl64.exe'})
        # Functional-only coexistence with independently isolated RConnect labs.
        # Never coexist with a user's game or the other ContinuousScene performance probe.
        $objectUnexpected=@($objectOthers | Where-Object {$_.CommandLine -notlike ('*'+$objectRoot+'\mods\RConnect\build\*\coop.xml*')})
        if($objectOthers.Count -gt 0 -and $objectUnexpected.Count -eq 0){$objectOtherPids=@($objectOthers.ProcessId);break}
    }
    if(((Get-Date)-$objectIdleStart).TotalSeconds -ge $WaitForIdleSeconds){throw 'Other AIR active; did not launch or stop any process'}
    Start-Sleep -Seconds 5
}
$objectLock=[IO.File]::Open((Join-Path $objectRuntime 'objects.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
$objectProcess=$null
try {
    $objectChosen=Join-Path $objectOut ($Variant+'-ContinuousSceneMod.swf')
    Copy-Item -LiteralPath $objectChosen -Destination (Join-Path $objectRuntime 'mods/ContinuousScene/release/ContinuousSceneMod.swf') -Force
    [IO.File]::WriteAllText((Join-Path $objectRuntime 'object-map.txt'),$Map,[Text.UTF8Encoding]::new($false))
    New-Item -ItemType Directory -Path $objectEvidence | Out-Null
    $objectStart=Get-Date
    $objectLogs=Join-Path $env:APPDATA 'pfe-modsettings-continuous-objects-01a151d4/Local Store'
    $objectProcess=Start-Process -FilePath (Join-Path $objectRoot 'adl64.exe') -ArgumentList @('-runtime',('"'+(Join-Path $objectRoot 'runtimes/air/win64')+'"'),('"'+$objectDescriptor+'"')) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $objectEvidence 'stdout.log') -RedirectStandardError (Join-Path $objectEvidence 'stderr.log')
    Write-Output ('Object audit AIR PID '+$objectProcess.Id)
    while(-not $objectProcess.WaitForExit(1000) -and ((Get-Date)-$objectStart).TotalSeconds -lt $TimeoutSeconds){}
    $objectTimeout=-not $objectProcess.HasExited
    if($objectTimeout){$objectProcess.Kill();$objectProcess.WaitForExit()}
    if(Test-Path -LiteralPath $objectLogs){Get-ChildItem -LiteralPath $objectLogs -File | Where-Object {$_.LastWriteTime -ge $objectStart -and $_.Extension -in '.json','.log','.png'} | Copy-Item -Destination $objectEvidence}
    $objectPaths=@((Join-Path $objectRuntime 'pfe.swf'),(Join-Path $objectRuntime 'mods/loader-manifest.txt'))
    foreach($objectLine in Get-Content -LiteralPath (Join-Path $objectRuntime 'mods/loader-manifest.txt')){
        $objectFields=$objectLine.Split('|');if($objectFields.Length -eq 5 -and $objectFields[2] -eq '1'){$objectPaths+=Join-Path $objectRuntime ('mods/'+$objectFields[0]+'/release/'+$objectFields[1]+'.swf')}
    }
    Get-FileHash -LiteralPath $objectPaths|Select-Object Path,Hash|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $objectEvidence 'hashes.json')
    @{pid=$objectProcess.Id;map=$Map;variant=$Variant;timedOut=$objectTimeout;purpose='functional-only';otherAirAtStart=$objectOtherPids;performanceEligible=$false;started=$objectStart.ToString('o');exitCode=$objectProcess.ExitCode}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $objectEvidence 'run.json')
    if($objectTimeout){throw 'Object audit timeout; evidence preserved'}
    $objectResult=Get-Content -LiteralPath (Join-Path $objectEvidence 'result.json') -Raw|ConvertFrom-Json
    $objectResult|Select-Object ok,map,sceneVersion,error,entry,interactions|ConvertTo-Json -Depth 7
    Write-Output ('Evidence: '+$objectEvidence)
} finally {
    if($objectProcess -and -not $objectProcess.HasExited){$objectProcess.Kill();$objectProcess.WaitForExit()}
    $objectLock.Dispose()
}
