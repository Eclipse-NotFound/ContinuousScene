param([ValidateSet('Install','Rollback')][string]$Action='Install',[string]$Evidence='entry-v031-final')
$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneRuntime=Join-Path $PSScriptRoot 'runtime'
$sceneRelative='mods/ContinuousScene/release/ContinuousSceneMod.swf'
$sceneTarget=Join-Path $sceneRoot $sceneRelative
$sceneReceiptPath=Join-Path $PSScriptRoot 'hotfix-v031-receipt.json'
$sceneBefore='CE279FE569A671594C934B408CEB50B2E9D9B17B0D58532638674FD891F07824'
if($Action -eq 'Rollback') {
    $sceneReceipt=Get-Content -LiteralPath $sceneReceiptPath -Raw | ConvertFrom-Json
    if($sceneReceipt.version -ne '0.3.1' -or $sceneReceipt.before -ne $sceneBefore) {throw 'Unexpected rollback receipt'}
    if((Get-FileHash -LiteralPath $sceneTarget).Hash -ne $sceneReceipt.after -or (Get-FileHash -LiteralPath $sceneReceipt.backup).Hash -ne $sceneBefore) {throw 'Installed file or backup changed; preserve it'}
    Copy-Item -LiteralPath $sceneReceipt.backup -Destination $sceneTarget -Force
    if((Get-FileHash -LiteralPath $sceneTarget).Hash -ne $sceneBefore) {throw 'Rollback hash mismatch'}
    Write-Output 'Restored ContinuousScene 0.3.0 only. Restart to load it.'
    return
}
if($Evidence -notmatch '^[a-z0-9-]+$') {throw 'Invalid evidence name'}
$sceneEvidence=Join-Path $PSScriptRoot ('../knowledge/experiments/evidence/'+$Evidence)
$sceneResult=Get-Content -LiteralPath (Join-Path $sceneEvidence 'result.json') -Raw | ConvertFrom-Json
if(-not $sceneResult.ok -or $sceneResult.version -ne '0.3.1' -or -not $sceneResult.preload -or @($sceneResult.assertions | Where-Object {-not $_.ok}).Count) {throw 'Runtime gate is not green'}
foreach($sceneCheck in @('travel-respects-noAct','travel-respects-other-pause','travel-respects-story','travel-respects-injury','travel-respects-weight','whole-map-ready-before-play','resaved-slot-retains-damage')) {
    if(-not @($sceneResult.assertions | Where-Object {$_.name -eq $sceneCheck -and $_.ok}).Count) {throw ('Missing gate '+$sceneCheck)}
}
foreach($sceneCheck in @('menu-settled-before-click','settled-menu-travel-requested','travel-closes-menu','duplicate-click-keeps-travel')) {
    if(@($sceneResult.assertions | Where-Object {$_.name -eq $sceneCheck -and $_.ok}).Count -ne 3) {throw ('Missing enter/return/reenter gate '+$sceneCheck)}
}
$sceneHashes=@(Get-Content -LiteralPath (Join-Path $sceneEvidence 'build-hashes.json') -Raw | ConvertFrom-Json)+@(Get-Content -LiteralPath (Join-Path $sceneEvidence 'loaded-module-hashes.json') -Raw | ConvertFrom-Json)
foreach($sceneHash in $sceneHashes) {
    if((Get-FileHash -LiteralPath $sceneHash.Path).Hash -ne $sceneHash.Hash) {throw ('Tested bytes changed: '+$sceneHash.Path)}
}
$sceneManifest=Join-Path $sceneRoot 'mods/loader-manifest.txt'
# Only the active 1.02 entries matter; preserve the shared multi-version manifest verbatim.
$sceneRows=@(Get-Content -LiteralPath $sceneManifest | Where-Object {$_ -match '^[^#]+\|[^|]+\|1\|'} | ForEach-Object {($_.Split('|')[0..1]) -join '|'})
$sceneTestRows=@(Get-Content -LiteralPath (Join-Path $sceneRuntime 'mods/loader-manifest.txt') | Where-Object {$_ -match '^[^#]+\|[^|]+\|1\|' -and $_ -notmatch '^ContinuousSceneProbe\|'} | ForEach-Object {($_.Split('|')[0..1]) -join '|'})
if(@(Compare-Object $sceneRows $sceneTestRows).Count) {throw 'Enabled 1.02 module set changed'}
foreach($sceneRow in $sceneRows) {
    $sceneFields=$sceneRow.Split('|')
    if($sceneFields[0] -eq 'ContinuousScene') {continue}
    $sceneOther='mods/'+$sceneFields[0]+'/release/'+$sceneFields[1]+'.swf'
    if((Get-FileHash -LiteralPath (Join-Path $sceneRoot $sceneOther)).Hash -ne (Get-FileHash -LiteralPath (Join-Path $sceneRuntime $sceneOther)).Hash) {throw ('Installed module differs from test: '+$sceneOther)}
}
$sceneHostHash=(Get-FileHash -LiteralPath (Join-Path $sceneRoot 'pfe.swf')).Hash
if($sceneHostHash -ne (Get-FileHash -LiteralPath (Join-Path $sceneRuntime 'pfe.swf')).Hash) {throw 'Host differs from test'}
if((Get-FileHash -LiteralPath (Join-Path $sceneRoot 'mods/ContinuousScene/release/scene.xml')).Hash -ne (Get-FileHash -LiteralPath (Join-Path $sceneRuntime 'mods/ContinuousScene/release/scene.xml')).Hash) {throw 'Scene definition differs from test'}
if((Get-FileHash -LiteralPath $sceneTarget).Hash -ne $sceneBefore) {throw 'Production module baseline changed'}
$sceneSource=Join-Path $sceneRuntime $sceneRelative
$sceneAfter=(Get-FileHash -LiteralPath $sceneSource).Hash
$sceneManifestHash=(Get-FileHash -LiteralPath $sceneManifest).Hash
$sceneBackup=Join-Path $PSScriptRoot ('backups/ContinuousSceneMod-before-v031-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.swf')
if(Test-Path -LiteralPath $sceneBackup) {throw 'Backup already exists'}
Copy-Item -LiteralPath $sceneTarget -Destination $sceneBackup
if((Get-FileHash -LiteralPath $sceneBackup).Hash -ne $sceneBefore) {throw 'Backup hash mismatch'}
try {
    Copy-Item -LiteralPath $sceneSource -Destination $sceneTarget -Force
    if((Get-FileHash -LiteralPath $sceneTarget).Hash -ne $sceneAfter) {throw 'Install hash mismatch'}
    if((Get-FileHash -LiteralPath $sceneManifest).Hash -ne $sceneManifestHash) {throw 'Shared manifest changed during install'}
    $sceneReceipt=[ordered]@{version='0.3.1';installed=(Get-Date).ToString('o');evidence=$Evidence;hostHash=$sceneHostHash;manifestHash=$sceneManifestHash;before=$sceneBefore;after=$sceneAfter;backup=$sceneBackup}
    $sceneReceipt | ConvertTo-Json | Set-Content -LiteralPath $sceneReceiptPath -Encoding UTF8
    $sceneReceipt | ConvertTo-Json
} catch {
    Copy-Item -LiteralPath $sceneBackup -Destination $sceneTarget -Force
    throw
}
