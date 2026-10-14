$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneReceipt=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'install-receipt.json') -Raw | ConvertFrom-Json
$sceneHost=Join-Path $sceneRoot 'pfe.swf'
$sceneManifest=Join-Path $sceneRoot 'mods/loader-manifest.txt'
if((Get-FileHash -LiteralPath $sceneHost).Hash -ne $sceneReceipt.hostHash -or (Get-FileHash -LiteralPath $sceneManifest).Hash -ne $sceneReceipt.manifestHash) {throw 'Other changes were made after install; stop to preserve them'}
if((Get-FileHash -LiteralPath $sceneReceipt.hostBackup).Hash -ne 'C631CBF3511B6EE303F533D08D51511FE0EB702F43E5DB17F5241D8576C64867') {throw 'Backup fingerprint mismatch'}
foreach($sceneModule in $sceneReceipt.compatibility) {
    if((Get-FileHash -LiteralPath $sceneModule.target).Hash -ne $sceneModule.installedHash -or (Get-FileHash -LiteralPath $sceneModule.backup).Hash -ne $sceneModule.baseline) {throw 'Compatibility module changed after install'}
}
Copy-Item -LiteralPath $sceneReceipt.hostBackup -Destination $sceneHost -Force
Copy-Item -LiteralPath $sceneReceipt.manifestBackup -Destination $sceneManifest -Force
foreach($sceneModule in $sceneReceipt.compatibility) {Copy-Item -LiteralPath $sceneModule.backup -Destination $sceneModule.target -Force}
$sceneModule=Join-Path $PSScriptRoot '../release/ContinuousSceneMod.swf'
if((Get-FileHash -LiteralPath $sceneModule).Hash -eq $sceneReceipt.moduleHash) {Remove-Item -LiteralPath $sceneModule}
Write-Output 'Original game host and mod manifest restored. Restart the game.'
