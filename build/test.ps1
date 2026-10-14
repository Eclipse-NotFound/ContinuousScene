param([int]$TimeoutSeconds=200,[string]$EvidenceName='latest',[switch]$Quick)
$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneDescriptor=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'runtime/application.xml')).Path
[xml]$sceneManifest=Get-Content -LiteralPath $sceneDescriptor -Raw
if($sceneManifest.application.id -ne 'remains.continuousscene.dev') { throw 'Refusing a non-isolated AIR id' }
$sceneLock=[IO.File]::Open((Join-Path $PSScriptRoot 'runtime/session.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
$sceneProcess=$null
$sceneTimedOut=$false
try {
if(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'runtime/manual.flag')) { throw 'Manual mode is enabled; remove manual.flag before automated tests' }
if($EvidenceName -notmatch '^[a-z0-9-]+$') { throw 'Invalid evidence directory name' }
$sceneEvidence=Join-Path $PSScriptRoot ('../knowledge/experiments/evidence/'+$EvidenceName)
New-Item -ItemType Directory -Force -Path $sceneEvidence | Out-Null
$sceneQuickFlag=Join-Path $PSScriptRoot 'runtime/quick.flag'
if($Quick) {[IO.File]::WriteAllText($sceneQuickFlag,'combat-only')} else {Remove-Item -LiteralPath $sceneQuickFlag -ErrorAction SilentlyContinue}
$sceneLogs=Join-Path $env:APPDATA 'remains.continuousscene.dev/Local Store'
$sceneStart=Get-Date
$sceneProcess=Start-Process -FilePath (Join-Path $sceneRoot 'adl64.exe') `
    -ArgumentList @('-runtime',('"'+(Join-Path $sceneRoot 'runtimes/air/win64')+'"'),('"'+$sceneDescriptor+'"')) `
    -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'runtime/adl-output.log') `
    -RedirectStandardError (Join-Path $PSScriptRoot 'runtime/adl-error.log')
Write-Output ('Isolated AIR PID '+$sceneProcess.Id)
if(-not $sceneProcess.WaitForExit($TimeoutSeconds*1000)) {
    # Process handle belongs exclusively to the child launched above.
    $sceneProcess.Kill()
    $sceneProcess.WaitForExit()
    $sceneTimedOut=$true
}
$sceneResultPath=Join-Path $sceneLogs 'result.json'
Get-ChildItem -LiteralPath $sceneLogs -File | Where-Object {$_.Extension -in '.json','.log','.png' -and $_.LastWriteTime -ge $sceneStart} | Copy-Item -Destination $sceneEvidence
Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'runtime/pfe.swf'),(Join-Path $PSScriptRoot 'runtime/drivers/ContinuousSceneMod.swf'),(Join-Path $PSScriptRoot 'runtime/scene.xml') | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $sceneEvidence 'build-hashes.json')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'generated/audit/bytecode-audit.json') -Destination $sceneEvidence
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
    $sceneLock.Dispose()
}
