param([ValidateSet('Check','Install','Rollback')][string]$Action='Check',
      [string]$FactoryEvidence='factory-v04-release',[string]$LabEvidence='factory-v04-lab-release')
$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneRuntime=Join-Path $PSScriptRoot 'runtime'
$sceneReceiptPath=Join-Path $PSScriptRoot 'upgrade-v04-receipt.json'
if($Action -eq 'Rollback') {
    $sceneReceipt=Get-Content -LiteralPath $sceneReceiptPath -Raw | ConvertFrom-Json
    if($sceneReceipt.version -ne '0.4.0') {throw 'Unexpected rollback receipt'}
    foreach($sceneFile in $sceneReceipt.files) {
        if((Get-FileHash -LiteralPath $sceneFile.target).Hash -ne $sceneFile.after -or
           (Get-FileHash -LiteralPath $sceneFile.backup).Hash -ne $sceneFile.before) {throw 'Installed file or backup changed; preserve it'}
    }
    foreach($sceneFile in $sceneReceipt.files) {
        Copy-Item -LiteralPath $sceneFile.backup -Destination $sceneFile.target -Force
        if((Get-FileHash -LiteralPath $sceneFile.target).Hash -ne $sceneFile.before) {throw 'Rollback hash mismatch'}
    }
    Write-Output 'Restored pre-0.4 host, ContinuousScene entry and lab XML. Other modules, manifest and saves unchanged. Restart to load.'
    return
}
foreach($sceneName in @($FactoryEvidence,$LabEvidence)) {
    if($sceneName -notmatch '^[a-z0-9-]+$') {throw 'Invalid evidence name'}
    $sceneDir=Join-Path $PSScriptRoot ('../knowledge/experiments/evidence/'+$sceneName)
    $sceneResult=Get-Content -LiteralPath (Join-Path $sceneDir 'result.json') -Raw | ConvertFrom-Json
    if(-not $sceneResult.ok -or -not $sceneResult.preload -or @($sceneResult.assertions | Where-Object {-not $_.ok}).Count) {throw ('Runtime gate failed: '+$sceneName)}
    $sceneChecks=if($sceneName -eq $FactoryEvidence) {
        @('factory-12-original-regions','factory-decorations-loaded','factory-all-240-surfaces-preloaded',
          'factory-exploration-keeps-preloaded-map','factory-player-walks-original-passage',
          'factory-bullet-crosses-passage-and-hits','factory-enemy-chases-across-passage',
          'factory-return-base','factory-reentry','factory-native-save-load')
    } else {
        @('travel-respects-noAct','travel-respects-other-pause','travel-respects-story','travel-respects-injury','travel-respects-weight',
          'projectile-destroys-tile','distant-raster-untouched-by-local-combat','older-slot-retains-undamaged-terrain','resaved-slot-retains-damage')
    }
    foreach($sceneCheck in $sceneChecks) {
        if(-not @($sceneResult.assertions | Where-Object {$_.name -eq $sceneCheck -and $_.ok}).Count) {throw ('Missing gate '+$sceneCheck)}
    }
    $sceneHashes=@(Get-Content -LiteralPath (Join-Path $sceneDir 'build-hashes.json') -Raw | ConvertFrom-Json)+
        @(Get-Content -LiteralPath (Join-Path $sceneDir 'loaded-module-hashes.json') -Raw | ConvertFrom-Json)
    foreach($sceneHash in $sceneHashes) {
        # Each suite uses a different XML fixture, preserved with that evidence.
        $scenePath=if((Split-Path $sceneHash.Path -Leaf) -eq 'scene.xml') {Join-Path $sceneDir 'scene.xml'} else {$sceneHash.Path}
        if((Get-FileHash -LiteralPath $scenePath).Hash -ne $sceneHash.Hash) {throw ('Tested bytes changed: '+$scenePath)}
    }
}
$sceneFactoryDir=Join-Path $PSScriptRoot ('../knowledge/experiments/evidence/'+$FactoryEvidence)
$sceneFactoryAudit=Get-Content -LiteralPath (Join-Path $sceneFactoryDir 'factory-audit.json') -Raw | ConvertFrom-Json
if(-not $sceneFactoryAudit.passed -or @($sceneFactoryAudit.checks).Count -ne 10) {throw 'Native factory content/raster audit failed'}
if((Get-FileHash -LiteralPath (Join-Path $sceneRoot 'Rooms/rooms_plant.xml')).Hash -ne $sceneFactoryAudit.sourceSHA256) {throw 'Original factory source changed'}
$sceneAudit=Get-Content -LiteralPath (Join-Path $sceneFactoryDir 'bytecode-audit.json') -Raw | ConvertFrom-Json
if(-not $sceneAudit.passed -or $sceneAudit.unchangedNamedMethodsAndInitializers -ne 4665) {throw 'Unrelated bytecode audit failed'}
$sceneManifest=Join-Path $sceneRoot 'mods/loader-manifest.txt'
# This patch targets 1.02. Changes to the other-version enable flags are not a
# changed 1.02 module set; preserve those shared flags without certifying DLC.
$sceneRows=@(Get-Content -LiteralPath $sceneManifest | Where-Object {$_ -match '^[^#]+\|[^|]+\|1\|'} | ForEach-Object {($_.Split('|')[0..1]) -join '|'})
$sceneTestRows=@(Get-Content -LiteralPath (Join-Path $sceneRuntime 'mods/loader-manifest.txt') | Where-Object {$_ -match '^[^#]+\|[^|]+\|1\|' -and $_ -notmatch '^ContinuousSceneProbe\|'} | ForEach-Object {($_.Split('|')[0..1]) -join '|'})
if(@(Compare-Object $sceneRows $sceneTestRows).Count) {throw 'Installed module set differs from tested set'}
foreach($sceneLine in $sceneRows) {
    $sceneFields=$sceneLine.Split('|')
    if($sceneFields[0] -eq 'ContinuousScene') {continue}
    $sceneRelative='mods/'+$sceneFields[0]+'/release/'+$sceneFields[1]+'.swf'
    if((Get-FileHash -LiteralPath (Join-Path $sceneRoot $sceneRelative)).Hash -ne
       (Get-FileHash -LiteralPath (Join-Path $sceneRuntime $sceneRelative)).Hash) {throw ('Another module changed: '+$sceneFields[0])}
}
$sceneFiles=@(
    @{relative='pfe.swf';before='838D8F02E844C19D7985B99C27907C93811140866B34B79144B7934F09B4943D'},
    @{relative='mods/ContinuousScene/release/ContinuousSceneMod.swf';before='76877E2E50CD0163674868A133699EF2734D00B911873461530D0BE6846A3B6C'},
    @{relative='mods/ContinuousScene/release/scene.xml';before='8BF1794609AAA3C776566835F87EDFEA8E929BF509A44E797F8B6289E70E59B9'}
)
foreach($sceneFile in $sceneFiles) {
    $sceneFile.target=Join-Path $sceneRoot $sceneFile.relative
    $sceneFile.source=if($sceneFile.relative.EndsWith('scene.xml')) {Join-Path $sceneRuntime 'scene-factory.xml'} else {Join-Path $sceneRuntime $sceneFile.relative}
    if((Get-FileHash -LiteralPath $sceneFile.target).Hash -ne $sceneFile.before) {throw ('Production baseline changed: '+$sceneFile.relative)}
    $sceneFile.after=(Get-FileHash -LiteralPath $sceneFile.source).Hash
}
if($sceneFiles[2].after -ne $sceneFactoryAudit.sceneSHA256) {throw 'Factory XML differs from tested content'}
if($Action -eq 'Check') {Write-Output 'All 0.4 factory, compatibility, bytecode and current-install checks passed.';return}
$sceneStamp=Get-Date -Format 'yyyyMMdd-HHmmss'
$sceneBackupDir=Join-Path $PSScriptRoot ('backups/upgrade-v04-'+$sceneStamp)
if(Test-Path -LiteralPath $sceneBackupDir) {throw 'Backup already exists'}
New-Item -ItemType Directory -Path $sceneBackupDir | Out-Null
foreach($sceneFile in $sceneFiles) {
    $sceneFile.backup=if($sceneFile.relative -eq 'pfe.swf') {Join-Path $sceneRoot ('pfe_before_ContinuousScene_v04_'+$sceneStamp+'.swf')} else {Join-Path $sceneBackupDir (Split-Path $sceneFile.target -Leaf)}
    if(Test-Path -LiteralPath $sceneFile.backup) {throw 'Refusing to overwrite backup'}
    Copy-Item -LiteralPath $sceneFile.target -Destination $sceneFile.backup
    if((Get-FileHash -LiteralPath $sceneFile.backup).Hash -ne $sceneFile.before) {throw 'Backup validation failed'}
}
$sceneManifestHash=(Get-FileHash -LiteralPath $sceneManifest).Hash
try {
    foreach($sceneFile in $sceneFiles) {
        Copy-Item -LiteralPath $sceneFile.source -Destination $sceneFile.target -Force
        if((Get-FileHash -LiteralPath $sceneFile.target).Hash -ne $sceneFile.after) {throw 'Deployment hash mismatch'}
    }
    if((Get-FileHash -LiteralPath $sceneManifest).Hash -ne $sceneManifestHash) {throw 'Manifest changed during upgrade'}
    $sceneReceipt=[ordered]@{version='0.4.0';installed=(Get-Date).ToString('o');factoryEvidence=$FactoryEvidence;labEvidence=$LabEvidence;hostHash=$sceneFiles[0].after;manifestHash=$sceneManifestHash;files=$sceneFiles}
    $sceneReceipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $sceneReceiptPath -Encoding UTF8
    $sceneReceipt | ConvertTo-Json -Depth 5
} catch {
    foreach($sceneFile in $sceneFiles) {Copy-Item -LiteralPath $sceneFile.backup -Destination $sceneFile.target -Force}
    throw
}
