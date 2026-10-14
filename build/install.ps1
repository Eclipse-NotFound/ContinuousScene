param([string]$Evidence='release-v02-final',[Parameter(Mandatory=$true)][string]$WallEvidence)
$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneMod=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$sceneRuntime=Join-Path $PSScriptRoot 'runtime'
$sceneEvidence=Join-Path $sceneMod ('knowledge/experiments/evidence/'+$Evidence)
$sceneResult=Get-Content -LiteralPath (Join-Path $sceneEvidence 'result.json') -Raw | ConvertFrom-Json
if(-not $sceneResult.ok -or $sceneResult.mode -ne 'full' -or $sceneResult.assertions.Count -lt 44 -or @($sceneResult.assertions | Where-Object {-not $_.ok}).Count) {throw 'Full runtime gate is not green'}
$sceneWallResult=Get-Content -LiteralPath $WallEvidence -Raw | ConvertFrom-Json
if(-not $sceneWallResult.passed) {throw 'Original wall regression gate is not green'}
$sceneWallProvenance=Get-Content -LiteralPath (Join-Path (Split-Path $WallEvidence) 'provenance.json') -Raw | ConvertFrom-Json
if($sceneWallProvenance.ModSHA256 -ne (Get-FileHash -LiteralPath (Join-Path $sceneRuntime 'mods/WallBlend/release/WallBlendMod.swf')).Hash -or $sceneWallProvenance.GameSHA256 -ne (Get-FileHash -LiteralPath (Join-Path $sceneRuntime 'pfe.swf')).Hash) {throw 'Wall regression tested a different candidate'}
$sceneVisionChecks=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'generated/vision-checks/result.json') -Raw | ConvertFrom-Json
if(@($sceneVisionChecks).Count -ne 2 -or @($sceneVisionChecks | Where-Object {-not $_.passed}).Count) {throw 'Vision regression is not green'}
if((Get-FileHash -LiteralPath (Join-Path $sceneRuntime 'scene.xml')).Hash -ne (Get-FileHash -LiteralPath (Join-Path $sceneRuntime 'mods/ContinuousScene/release/scene.xml')).Hash) {throw 'Scene test and deployment files differ'}
$sceneAudit=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'generated/audit/bytecode-audit.json') -Raw | ConvertFrom-Json
if(-not $sceneAudit.passed) {throw 'Bytecode gate is not green'}
$sceneHashes=Get-Content -LiteralPath (Join-Path $sceneEvidence 'build-hashes.json') -Raw | ConvertFrom-Json
foreach($sceneHash in $sceneHashes) {
    if((Get-FileHash -LiteralPath $sceneHash.Path).Hash -ne $sceneHash.Hash) {throw 'A tested candidate changed'}
}
$sceneModuleHashes=Get-Content -LiteralPath (Join-Path $sceneEvidence 'loaded-module-hashes.json') -Raw | ConvertFrom-Json
foreach($sceneHash in $sceneModuleHashes) {
    if((Get-FileHash -LiteralPath $sceneHash.Path).Hash -ne $sceneHash.Hash) {throw 'A tested module changed'}
}
$sceneCompat=@(
    @{dir='RealisticVision';entry='RealisticVisionMod';baseline='D5E0468EE17C55F2B9FD14A10B2B8849F023ADE242A54D46028ADA60CFB450EE'},
    @{dir='WallBlend';entry='WallBlendMod';baseline='1BB9B65AF80A946F6758824A72EED941173D0AE40B8C09C084ECF12B92458820'}
)
foreach($sceneModule in $sceneCompat) {
    $sceneModule.target=Join-Path $sceneRoot ('mods/'+$sceneModule.dir+'/release/'+$sceneModule.entry+'.swf')
    if((Get-FileHash -LiteralPath $sceneModule.target).Hash -ne $sceneModule.baseline) {throw 'An installed compatibility module changed since review'}
}
$sceneHost=Join-Path $sceneRoot 'pfe.swf'
if((Get-FileHash -LiteralPath $sceneHost).Hash -ne 'C631CBF3511B6EE303F533D08D51511FE0EB702F43E5DB17F5241D8576C64867') {throw 'Production host changed since review'}
$sceneStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$sceneBackup=Join-Path $sceneRoot ('pfe_before_ContinuousScene_'+$sceneStamp+'.swf')
$sceneBackupDir=Join-Path $PSScriptRoot ('backups/install-'+$sceneStamp)
$sceneRelease=Join-Path $sceneMod 'release'
if((Test-Path -LiteralPath $sceneBackup) -or (Test-Path -LiteralPath (Join-Path $sceneRelease 'ContinuousSceneMod.swf'))) {throw 'Backup or previous deployment already exists; review before replacing'}
New-Item -ItemType Directory -Path $sceneBackupDir -Force | Out-Null
New-Item -ItemType Directory -Path $sceneRelease -Force | Out-Null
$sceneManifest=Join-Path $sceneRoot 'mods/loader-manifest.txt'
Copy-Item -LiteralPath $sceneHost -Destination $sceneBackup
Copy-Item -LiteralPath $sceneManifest -Destination (Join-Path $sceneBackupDir 'loader-manifest.txt')
foreach($sceneModule in $sceneCompat) {
    $sceneModule.backup=Join-Path $sceneBackupDir ($sceneModule.entry+'.swf')
    Copy-Item -LiteralPath $sceneModule.target -Destination $sceneModule.backup
}
$sceneLines=@(Get-Content -LiteralPath $sceneManifest -Encoding UTF8)
if($sceneLines -match '^ContinuousScene\|') {throw 'Manifest entry already exists'}
try {
    Copy-Item -LiteralPath (Join-Path $sceneRuntime 'mods/ContinuousScene/release/scene.xml') -Destination $sceneRelease
    Copy-Item -LiteralPath (Join-Path $sceneRuntime 'mods/ContinuousScene/release/ContinuousSceneMod.swf') -Destination $sceneRelease
    Copy-Item -LiteralPath (Join-Path $sceneRuntime 'pfe.swf') -Destination $sceneHost -Force
    foreach($sceneModule in $sceneCompat) {
        Copy-Item -LiteralPath (Join-Path $sceneRuntime ('mods/'+$sceneModule.dir+'/release/'+$sceneModule.entry+'.swf')) -Destination $sceneModule.target -Force
        $sceneModule.installedHash=(Get-FileHash -LiteralPath $sceneModule.target).Hash
    }
    [IO.File]::WriteAllLines($sceneManifest,($sceneLines+@('ContinuousScene|ContinuousSceneMod|1|0|0')),[Text.UTF8Encoding]::new($false))
    $sceneReceipt=[ordered]@{version='0.2.0';installed=(Get-Date).ToString('o');evidence=$Evidence;hostBackup=$sceneBackup;manifestBackup=(Join-Path $sceneBackupDir 'loader-manifest.txt');hostHash=(Get-FileHash -LiteralPath $sceneHost).Hash;manifestHash=(Get-FileHash -LiteralPath $sceneManifest).Hash;moduleHash=(Get-FileHash -LiteralPath (Join-Path $sceneRelease 'ContinuousSceneMod.swf')).Hash;sceneHash=(Get-FileHash -LiteralPath (Join-Path $sceneRelease 'scene.xml')).Hash}
    $sceneReceipt.compatibility=$sceneCompat
    $sceneReceipt.wallEvidence=$WallEvidence
    $sceneReceipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'install-receipt.json') -Encoding UTF8
    $sceneReceipt | ConvertTo-Json
} catch {
    Copy-Item -LiteralPath $sceneBackup -Destination $sceneHost -Force
    Copy-Item -LiteralPath (Join-Path $sceneBackupDir 'loader-manifest.txt') -Destination $sceneManifest -Force
    foreach($sceneModule in $sceneCompat) {Copy-Item -LiteralPath $sceneModule.backup -Destination $sceneModule.target -Force}
    $sceneFailedModule=Join-Path $sceneRelease 'ContinuousSceneMod.swf'
    if(Test-Path -LiteralPath $sceneFailedModule) {Remove-Item -LiteralPath $sceneFailedModule}
    throw
}
