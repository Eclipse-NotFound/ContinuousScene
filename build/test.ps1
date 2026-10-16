param([int]$TimeoutSeconds=200,[string]$EvidenceName='latest',[switch]$Quick,[switch]$Benchmark,[switch]$Preload,[switch]$HighQoS,[switch]$Cull,[switch]$Streaming,[switch]$Factory,[switch]$Perf,[switch]$Experience,[switch]$DecalOnly,[switch]$Loading,[switch]$NativeMap,[switch]$LoadNative,[switch]$EntryOnly,[switch]$DiagnosticsOnly,[switch]$Progressive)
$ErrorActionPreference='Stop'
if(($Perf -or $Loading) -and @(Get-Process -Name adl64 -ErrorAction SilentlyContinue).Count) {
    throw 'Performance sampling requires no other AIR instances; existing processes were left untouched'
}
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneDescriptor=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'runtime/application.xml')).Path
[xml]$sceneManifest=Get-Content -LiteralPath $sceneDescriptor -Raw
if($sceneManifest.application.id -ne 'pfe-modsettings-continuous-scene') { throw 'Refusing a non-isolated AIR id' }
if($DecalOnly -and (-not $Experience -or -not $Factory)) {throw 'DecalOnly requires the isolated factory Experience probe'}
if($Loading -and (-not $Factory -or $Experience -or $Perf -or $Streaming)) {throw 'Loading requires the fully preloaded factory and cannot combine with another probe mode'}
if(($LoadNative -or $EntryOnly) -and -not $Loading) {throw 'LoadNative and EntryOnly require Loading'}
if($DiagnosticsOnly -and (-not $Loading -or $EntryOnly)) {throw 'DiagnosticsOnly requires the pixel oracle, never an entry benchmark'}
if($NativeMap -and ($Loading -or $Experience -or $Perf -or $Streaming)) {throw 'NativeMap requires its own fully preloaded probe'}
$sceneLock=[IO.File]::Open((Join-Path $PSScriptRoot 'runtime/session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
$sceneProcess=$null
$sceneTimedOut=$false
if($HighQoS) {. (Join-Path $PSScriptRoot 'test-process.ps1')}
try {
if(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'runtime/manual.flag')) { throw 'Manual mode is enabled; remove manual.flag before automated tests' }
    $sceneFixture=Join-Path $PSScriptRoot $(if($Factory) {'runtime/scene-factory.xml'} else {'runtime/scene-lab.xml'})
    if(-not(Test-Path -LiteralPath $sceneFixture)) {throw 'Rebuild the selected scene fixture first'}
    Copy-Item -LiteralPath $sceneFixture -Destination (Join-Path $PSScriptRoot 'runtime/scene.xml') -Force
    Copy-Item -LiteralPath $sceneFixture -Destination (Join-Path $PSScriptRoot 'runtime/mods/ContinuousScene/release/scene.xml') -Force
if($EvidenceName -notmatch '^[a-z0-9-]+$') { throw 'Invalid evidence directory name' }
$sceneEvidence=Join-Path $PSScriptRoot ('../knowledge/experiments/evidence/'+$EvidenceName)
New-Item -ItemType Directory -Force -Path $sceneEvidence | Out-Null
$sceneQuickFlag=Join-Path $PSScriptRoot 'runtime/quick.flag'
$sceneBenchmarkFlag=Join-Path $PSScriptRoot 'runtime/benchmark.flag'
$scenePreloadFlag=Join-Path $PSScriptRoot 'runtime/preload.flag'
$sceneCullFlag=Join-Path $PSScriptRoot 'runtime/cull.flag'
$sceneFactoryFlag=Join-Path $PSScriptRoot 'runtime/factory.flag'
$scenePerfFlag=Join-Path $PSScriptRoot 'runtime/perf.flag'
$sceneExperienceFlag=Join-Path $PSScriptRoot 'runtime/experience.flag'
$sceneDecalFlag=Join-Path $PSScriptRoot 'runtime/decal-only.flag'
$sceneLoadingFlag=Join-Path $PSScriptRoot 'runtime/loading.flag'
$sceneLoadNativeFlag=Join-Path $PSScriptRoot 'runtime/load-native.flag'
$sceneEntryOnlyFlag=Join-Path $PSScriptRoot 'runtime/entry-only.flag'
if($LoadNative) {[IO.File]::WriteAllText($sceneLoadNativeFlag,'actual-native-factory-generation')} else {Remove-Item -LiteralPath $sceneLoadNativeFlag -ErrorAction SilentlyContinue}
if($EntryOnly) {[IO.File]::WriteAllText($sceneEntryOnlyFlag,'entry-only-without-repaint')} else {Remove-Item -LiteralPath $sceneEntryOnlyFlag -ErrorAction SilentlyContinue}
$sceneNativeFlag=Join-Path $PSScriptRoot 'runtime/native.flag'
if($NativeMap) {[IO.File]::WriteAllText($sceneNativeFlag,'native-map-mode-regression')} else {Remove-Item -LiteralPath $sceneNativeFlag -ErrorAction SilentlyContinue}
if($Loading) {[IO.File]::WriteAllText($sceneLoadingFlag,'isolated-loading-measurement')} else {Remove-Item -LiteralPath $sceneLoadingFlag -ErrorAction SilentlyContinue}
if($DecalOnly) {[IO.File]::WriteAllText($sceneDecalFlag,'terminal-pixel-diagnostic')} else {Remove-Item -LiteralPath $sceneDecalFlag -ErrorAction SilentlyContinue}
if($Experience) {[IO.File]::WriteAllText($sceneExperienceFlag,'native-gameplay-regression')} else {Remove-Item -LiteralPath $sceneExperienceFlag -ErrorAction SilentlyContinue}
if($Perf) {[IO.File]::WriteAllText($scenePerfFlag,'actual-frame-benchmark')} else {Remove-Item -LiteralPath $scenePerfFlag -ErrorAction SilentlyContinue}
if($Factory) {[IO.File]::WriteAllText($sceneFactoryFlag,'native-factory-regression')} else {Remove-Item -LiteralPath $sceneFactoryFlag -ErrorAction SilentlyContinue}
if($Cull) {[IO.File]::WriteAllText($sceneCullFlag,'hide-offscreen-rasters-only')} else {Remove-Item -LiteralPath $sceneCullFlag -ErrorAction SilentlyContinue}
if($Preload -or (-not $Streaming -and -not $Progressive)) {[IO.File]::WriteAllText($scenePreloadFlag,'all-scene-surfaces')} else {Remove-Item -LiteralPath $scenePreloadFlag -ErrorAction SilentlyContinue}
if($Benchmark) {[IO.File]::WriteAllText($sceneBenchmarkFlag,'walk-360-frames')} else {Remove-Item -LiteralPath $sceneBenchmarkFlag -ErrorAction SilentlyContinue}
if($Quick) {[IO.File]::WriteAllText($sceneQuickFlag,'combat-only')} else {Remove-Item -LiteralPath $sceneQuickFlag -ErrorAction SilentlyContinue}
$sceneLogs=Join-Path $env:APPDATA 'pfe-modsettings-continuous-scene/Local Store'
$sceneStart=Get-Date
$sceneProcess=Start-Process -FilePath (Join-Path $sceneRoot 'adl64.exe') `
    -ArgumentList @('-runtime',('"'+(Join-Path $sceneRoot 'runtimes/air/win64')+'"'),('"'+$sceneDescriptor+'"')) `
    -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'runtime/adl-output.log') `
    -RedirectStandardError (Join-Path $PSScriptRoot 'runtime/adl-error.log')
Write-Output ('Isolated AIR PID '+$sceneProcess.Id)
$scenePolicy=@{highQoS=[bool]$HighQoS;pid=$sceneProcess.Id;peakWorkingSetMB=0;peakPrivateMB=0;diagnosticsOnly=[bool]$DiagnosticsOnly;performanceEligible=(-not $DiagnosticsOnly)}
if($Perf -or $Loading) {$scenePolicy.otherAirProcessIds=@()}
if($HighQoS) {
    $sceneOriginalPolicy=[ContinuousSceneTest.Power]::Read($sceneProcess)
    $scenePolicy.original=$sceneOriginalPolicy
    $scenePolicy.applied=[ContinuousSceneTest.Power]::Responsive($sceneProcess)
}
while(-not $sceneProcess.WaitForExit(1000) -and ((Get-Date)-$sceneStart).TotalSeconds -lt $TimeoutSeconds) {
    $sceneProcess.Refresh()
    $scenePolicy.peakWorkingSetMB=[Math]::Max($scenePolicy.peakWorkingSetMB,$sceneProcess.WorkingSet64/1MB)
    $scenePolicy.peakPrivateMB=[Math]::Max($scenePolicy.peakPrivateMB,$sceneProcess.PrivateMemorySize64/1MB)
    if($Perf -or $Loading) {
        $others=@(Get-Process -Name adl64 -ErrorAction SilentlyContinue | Where-Object {$_.Id -ne $sceneProcess.Id} | ForEach-Object {$_.Id})
        $scenePolicy.otherAirProcessIds=@(@($scenePolicy.otherAirProcessIds)+$others | Select-Object -Unique)
        if($others.Count) {
            $scenePolicy.performanceEligible=$false
            if(-not $DiagnosticsOnly) {break} # Functional pixels may finish; timings are never accepted.
        }
    }
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
$sceneAudit=Join-Path $PSScriptRoot 'runtime/renderer-audit.json'
if((Test-Path -LiteralPath $sceneAudit) -and (Get-Content -LiteralPath $sceneAudit -Raw|ConvertFrom-Json).finalHostSHA256 -eq (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'runtime/pfe.swf')).Hash) {
    Copy-Item -LiteralPath $sceneAudit -Destination $sceneEvidence
}
$sceneLoadedFiles=@((Join-Path $PSScriptRoot 'runtime/mods/loader-manifest.txt'))
foreach($sceneLine in Get-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime/mods/loader-manifest.txt')) {
    $sceneFields=$sceneLine.Split('|')
    if($sceneFields.Length -eq 5 -and $sceneFields[2] -eq '1') {$sceneLoadedFiles+=Join-Path $PSScriptRoot ('runtime/mods/'+$sceneFields[0]+'/release/'+$sceneFields[1]+'.swf')}
}
Get-FileHash -LiteralPath $sceneLoadedFiles | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $sceneEvidence 'loaded-module-hashes.json')
Copy-Item -LiteralPath $sceneFixture -Destination (Join-Path $sceneEvidence 'scene.xml')
if(($Perf -or $Loading) -and -not $DiagnosticsOnly -and $scenePolicy.otherAirProcessIds.Count) {throw 'Performance evidence overlapped other AIR instances; partial evidence preserved; resample when quiet'}
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
    if($sceneFactoryFlag) {Remove-Item -LiteralPath $sceneFactoryFlag -ErrorAction SilentlyContinue}
    if($scenePerfFlag) {Remove-Item -LiteralPath $scenePerfFlag -ErrorAction SilentlyContinue}
    if($sceneExperienceFlag) {Remove-Item -LiteralPath $sceneExperienceFlag -ErrorAction SilentlyContinue}
    if($sceneDecalFlag) {Remove-Item -LiteralPath $sceneDecalFlag -ErrorAction SilentlyContinue}
    if($sceneLoadingFlag) {Remove-Item -LiteralPath $sceneLoadingFlag -ErrorAction SilentlyContinue}
    if($sceneLoadNativeFlag) {Remove-Item -LiteralPath $sceneLoadNativeFlag -ErrorAction SilentlyContinue}
    if($sceneEntryOnlyFlag) {Remove-Item -LiteralPath $sceneEntryOnlyFlag -ErrorAction SilentlyContinue}
    if($sceneNativeFlag) {Remove-Item -LiteralPath $sceneNativeFlag -ErrorAction SilentlyContinue}
    $sceneLock.Dispose()
}
