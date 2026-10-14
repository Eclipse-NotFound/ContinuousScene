param([string]$Receipt='upgrade-receipt.json')
$ErrorActionPreference='Stop'
$sceneReceipt=Get-Content -LiteralPath (Join-Path $PSScriptRoot $Receipt) -Raw | ConvertFrom-Json
if($sceneReceipt.version -ne '0.3.0') {throw 'Unexpected rollback version'}
foreach($sceneFile in $sceneReceipt.files) {
    if((Get-FileHash -LiteralPath $sceneFile.target).Hash -ne $sceneFile.after -or (Get-FileHash -LiteralPath $sceneFile.backup).Hash -ne $sceneFile.before) {throw ('File changed after upgrade; preserve it: '+$sceneFile.target)}
}
foreach($sceneFile in $sceneReceipt.files) {Copy-Item -LiteralPath $sceneFile.backup -Destination $sceneFile.target -Force}
Write-Output 'Restored ContinuousScene 0.2 / RV 0.30.3-scene / WallBlend 0.4.1. Shared manifest and saves were untouched. Restart to use restored files.'
