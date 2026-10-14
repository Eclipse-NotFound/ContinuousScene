param([int]$TimeoutSeconds=200,[string]$EvidenceName='latest',[switch]$Quick,[switch]$Benchmark,[switch]$Preload,[switch]$HighQoS,[switch]$Cull,[switch]$Streaming)
$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneDescriptor=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'runtime/application.xml')).Path
[xml]$sceneManifest=Get-Content -LiteralPath $sceneDescriptor -Raw
if($sceneManifest.application.id -ne 'pfe-modsettings-continuous-scene') { throw 'Refusing a non-isolated AIR id' }
$sceneLock=[IO.File]::Open((Join-Path $PSScriptRoot 'runtime/session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
$sceneProcess=$null
$sceneTimedOut=$false
if($HighQoS) {. (Join-Path $PSScriptRoot 'test-process.ps1')}
try {
if(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'runtime/manual.flag')) { throw 'Manual mode is enabled; remove manual.flag before automated tests' }
if($EvidenceName -notmatch '^[a-z0-9-]+$') { throw 'Invalid evidence directory name' }
$sceneEvidence=Join-Path $PSScriptRoot ('../knowledge/experiments/evidence/'+$EvidenceName)
New-Item -ItemType Directory -Force -Path $sceneEvidence | Out-Null
$sceneQuickFlag=Join-Path $PSScriptRoot 'runtime/quick.flag'
$sceneBenchmarkFlag=Join-Path $PSScriptRoot 'runtime/benchmark.flag'
$scenePreloadFlag=Join-Path $PSScriptRoot 'runtime/preload.flag'
$sceneCullFlag=Join-Path $PSScriptRoot 'runtime/cull.flag'
if($Cull) {[IO.File]::WriteAllText($sceneCullFlag,'hide-offscreen-rasters-only')} else {Remove-Item -LiteralPath $sceneCullFlag -ErrorAction SilentlyContinue}
if($Preload -or -not $Streaming) {[IO.File]::WriteAllText($scenePreloadFlag,'all-scene-surfaces')} else {Remove-Item -LiteralPath $scenePreloadFlag -ErrorAction SilentlyContinue}
if($Benchmark) {[IO.File]::WriteAllText($sceneBenchmarkFlag,'walk-360-frames')} else {Remove-Item -LiteralPath $sceneBenchmarkFlag -ErrorAction SilentlyContinue}
if($Quick) {[IO.File]::WriteAllText($sceneQuickFlag,'combat-only')} else {Remove-Item -LiteralPath $sceneQuickFlag -ErrorAction SilentlyContinue}
$sceneLogs=Join-Path $env:APPDATA 'pfe-modsettings-continuous-scene/Local Store'
$sceneStart=Get-Date
$sceneProcess=Start-Process -FilePath (Join-Path $sceneRoot 'adl64.exe') `
    -ArgumentList @('-runtime',('"'+(Join-Path $sceneRoot 'runtimes/air/win64')+'"'),('"'+$sceneDescriptor+'"')) `
    -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'runtime/adl-output.log') `
    -RedirectStandardError (Join-Path $PSScriptRoot 'runtime/adl-error.log')
Write-Output ('Isolated AIR PID '+$sceneProcess.Id)
$scenePolicy=@{highQoS=[bool]$HighQoS;pid=$sceneProcess.Id;peakWorkingSetMB=0;peakPrivateMB=0}
if($HighQoS) {
    $sceneOriginalPolicy=[ContinuousSceneTest.Power]::Read($sceneProcess)
    $scenePolicy.original=$sceneOriginalPolicy
    $scenePolicy.applied=[ContinuousSceneTest.Power]::Responsive($sceneProcess)
}
while(-not $sceneProcess.WaitForExit(1000) -and ((Get-Date)-$sceneStart).TotalSeconds -lt $TimeoutSeconds) {
    $sceneProcess.Refresh()
    $scenePolicy.peakWorkingSetMB=[Math]::Max($scenePolicy.peakWorkingSetMB,$sceneProcess.WorkingSet64/1MB)
    $scenePolicy.peakPrivateMB=[Math]::Max($scenePolicy.peakPrivateMB,$sceneProcess.PrivateMemorySize64/1MB)
}
$scenePolicy | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $sceneEvidence 'process-policy.json')
if(-not $sceneProcess.HasExited) {
    # Process handle belongs exclusively to the child launched above.
    $sceneProcess.Kill()
    $sceneProcess.WaitForExit()
    $sceneTimedOut=$true
}
$sceneResultPath=Join-Path $sceneLogs 'result.json'
Get-ChildItem -LiteralPath $sceneLogs -File | Where-Object {$_.Extension -in '.json','.log','.png' -and $_.LastWriteTime -ge $sceneStart} | Copy-Item -Destination $sceneEvidence
Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'runtime/pfe.swf'),(Join-Path $PSScriptRoot 'runtime/mods/ContinuousScene/release/ContinuousSceneMod.swf'),(Join-Path $PSScriptRoot 'runtime/mods/ContinuousSceneProbe/release/ContinuousSceneProbe.swf'),(Join-Path $PSScriptRoot 'runtime/scene.xml') | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $sceneEvidence 'build-hashes.json')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'generated/audit/bytecode-audit.json') -Destination $sceneEvidence
$sceneLoadedFiles=@((Join-Path $PSScriptRoot 'runtime/mods/loader-manifest.txt'))
foreach($sceneLine in Get-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime/mods/loader-manifest.txt')) {
    $sceneFields=$sceneLine.Split('|')
    if($sceneFields.Length -eq 5 -and $sceneFields[2] -eq '1') {$sceneLoadedFiles+=Join-Path $PSScriptRoot ('runtime/mods/'+$sceneFields[0]+'/release/'+$sceneFields[1]+'.swf')}
}
Get-FileHash -LiteralPath $sceneLoadedFiles | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $sceneEvidence 'loaded-module-hashes.json')
if($sceneTimedOut) {throw 'Isolated AIR test timed out; partial evidence preserved'}
if(-not(Test-Path -LiteralPath $sceneResultPath) -or (Get-Item -LiteralPath $sceneResultPath).LastWriteTime -lt $sceneStart) {
    Get-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime/adl-output.log') -Tail 40
    throw 'No fresh test result'
}
$sceneResult=Get-Content -LiteralPath $sceneResultPath -Raw | ConvertFrom-Json
$sceneResult | Select-Object ok,elapsedMs,memoryMB,error | ConvertTo-Json -Depth 6
if(-not $sceneResult.ok) { throw 'Runtime assertions failed; inspect evidence' }
}
finally {
    if($sceneProcess -and -not $sceneProcess.HasExited) {$sceneProcess.Kill()}
    if($sceneQuickFlag) {Remove-Item -LiteralPath $sceneQuickFlag -ErrorAction SilentlyContinue}
    if($sceneBenchmarkFlag) {Remove-Item -LiteralPath $sceneBenchmarkFlag -ErrorAction SilentlyContinue}
    if($scenePreloadFlag) {Remove-Item -LiteralPath $scenePreloadFlag -ErrorAction SilentlyContinue}
    if($sceneCullFlag) {Remove-Item -LiteralPath $sceneCullFlag -ErrorAction SilentlyContinue}
    $sceneLock.Dispose()
}
