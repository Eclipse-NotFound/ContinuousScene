param([ValidateSet('Check','Install','Rollback')][string]$Action='Check')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneFinal=Join-Path $PSScriptRoot 'candidate-v08-final'
$sceneEvidence=Join-Path $PSScriptRoot '../knowledge/experiments/evidence'
$sceneReceipt=Join-Path $PSScriptRoot '../state/deployment-v08.json'
$sceneFiles=@(
    @{relative='pfe.swf';before='2A4662488BA3B690EB23ACFE4B79ACA3F0D9AE114E5E2DEE7595AF3CABFFB3EA';after='A61EA4A30F0E4978173F2B92B5F33A02960098D706B810FC6196105278EFA73F'},
    @{relative='mods/ContinuousScene/release/ContinuousSceneMod.swf';before='70C06879A2CFFE85901E5C8E19FC1715028D5C38934975E970569468737309D5';after='B5E8110E11FE2DF8A748B223DFFA6E0EC42E4F61A931D4D4E065CC199EFA2F1B'},
    @{relative='mods/TDFC/release/TDFCMod.swf';before='99BFBAA68229635FBAA496EF9287A94BB9EA7C65D71339CEF3FDE65F47E30275';after='03243196C99D6C4F1A2BE081598DBAE9B5D89A414BCD48E1F860232BCFDDE1E5'},
    @{relative='mods/WallBlend/release/WallBlendMod.swf';before='DF9AA07265E2538E115A5F048D272B85FC1C34D00EC4BC81585CD40D96648F76';after='0BD209A1763D1C08BCEEAA6415DC768AB3D18AD99BAD377B4D8C188EBD48DE5A'}
)
$sceneChecks=@()
function Require([bool]$ok,[string]$name){
    $script:sceneChecks+=,[ordered]@{name=$name;passed=$ok}
    if(-not $ok){throw $name}
}
function Hash([string]$path){(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash}
function Read-Json([string]$path){Get-Content -LiteralPath $path -Raw|ConvertFrom-Json}
function Verify-Inputs([string]$name){
    $directory=Join-Path $script:sceneEvidence $name
    $result=Read-Json (Join-Path $directory 'result.json')
    Require ($result.ok -eq $true) ($name+' passed')
    $inputs=@(Read-Json (Join-Path $directory 'build-hashes.json'))
    foreach($file in $script:sceneFiles[0..1]){
        $path=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot ('runtime/'+$file.relative)))
        $rows=@($inputs|Where-Object {$_.Path -eq $path})
        Require ($rows.Count -eq 1 -and $rows[0].Hash -eq $file.after) ($name+' exact '+$file.relative)
    }
    foreach($row in (Read-Json (Join-Path $directory 'loaded-module-hashes.json'))){
        $prefix=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'runtime'))+[IO.Path]::DirectorySeparatorChar
        Require ($row.Path.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) ($name+' isolated input')
        $relative=$row.Path.Substring($prefix.Length)
        if($relative -eq 'mods\loader-manifest.txt' -or $relative -like 'mods\ContinuousSceneProbe\*'){continue}
        $target=@($script:sceneFiles|Where-Object {$_.relative.Replace('/','\') -eq $relative})
        $expected=if($target.Count){$target[0].after}else{Hash (Join-Path $script:sceneRoot $relative)}
        # These mechanical/native bitmap checks preceded the independent RV
        # update. Rendering/gameplay and timing additionally require RV 0.32.3.
        if($relative -eq 'mods\RealisticVision\release\RealisticVisionMod.swf' -and $name -in @('issues-v08-mechanics-release','native-v08-release-r2','factory-v08-release','issues-v08-wall-trim-release-r2')) {
            $expected='2E7150CF415355C2D7B809689AAC3C4CA0BACBB5F6D8770066A6E887D8907A10'
        }
        Require ($row.Hash -eq $expected) ($name+' exact dependency '+$relative)
    }
    return $result
}
if($Action -eq 'Rollback'){
    $receipt=Read-Json $sceneReceipt
    Require (@(Get-Process -Name adl64 -ErrorAction SilentlyContinue).Count -eq 0) 'No AIR during rollback'
    foreach($file in $receipt.files){
        Require ((Hash (Join-Path $sceneRoot $file.relative)) -eq $file.after) ('Refuse later update: '+$file.relative)
        Require ((Hash (Join-Path $receipt.backup $file.relative)) -eq $file.before) ('Verified backup '+$file.relative)
    }
    foreach($file in $receipt.files){Copy-Item -LiteralPath (Join-Path $receipt.backup $file.relative) -Destination (Join-Path $sceneRoot $file.relative) -Force}
    $receipt.status='rolled-back';$receipt|ConvertTo-Json -Depth 12|Set-Content -LiteralPath $sceneReceipt -Encoding utf8
    return
}
foreach($file in $sceneFiles){
    Require ((Hash (Join-Path $sceneRoot $file.relative)) -eq $file.before) ('Installed baseline '+$file.relative)
    Require ((Hash (Join-Path $sceneFinal (Split-Path $file.relative -Leaf))) -eq $file.after) ('Frozen candidate '+$file.relative)
}
$audit=Read-Json (Join-Path $sceneFinal 'pfe.audit.json')
Require ($audit.passed -and $audit.finalHostSHA256 -eq $sceneFiles[0].after -and $audit.sourceHostSHA256 -eq $sceneFiles[0].before -and
    $audit.unchangedNamedMethodsAndInitializers -eq 4665 -and $audit.unchangedClassLayouts -eq 1015 -and $audit.originalConstantPoolPreserved) 'Unrelated native code and loader preserved'
Require ((Hash (Join-Path $sceneRoot 'mods/loader-manifest.txt')) -eq '33DE189E1209FDD397E811A52E9AC67FF0DEDAEEAE5CFEFF4B7D15D4536EB133') 'Reviewed loader manifest: obsolete disabled ModSettings entry removed'
Require ((Hash (Join-Path $sceneRoot 'mods/RealisticVision/release/RealisticVisionMod.swf')) -eq '76314B819151FBA6F67F6D740B21030A9EEC8359AF4C9C9DDEB83D4CAF5C46B7') 'Preserve independently installed RV 0.32.3'
$productionEntries=@(Get-Content (Join-Path $sceneRoot 'mods/loader-manifest.txt')|Where-Object {$_ -match '^[^#]+\|[^|]+\|1\|'}|ForEach-Object {($_.Split('|')[0..1]) -join '|'})+@('ContinuousSceneProbe|ContinuousSceneProbe')
$testEntries=@(Get-Content (Join-Path $PSScriptRoot 'runtime/mods/loader-manifest.txt')|Where-Object {$_ -match '^[^#]+\|[^|]+\|1\|'}|ForEach-Object {($_.Split('|')[0..1]) -join '|'})
Require ($testEntries.Count -eq $productionEntries.Count -and @($testEntries|Sort-Object -Unique).Count -eq $testEntries.Count -and @(Compare-Object $productionEntries $testEntries).Count -eq 0) 'Exact enabled modules plus isolated probe'
Require ((Hash (Join-Path $sceneRoot 'mods/ContinuousScene/release/scene.xml')) -eq '1CEA74E218A55894D432E12CDFC544952D37CFFF5FF55B256B1B970573EB7A9E') 'Factory fixture unchanged'
$times=@()
foreach($i in 1..3){
    $name='loading-v08-rv323-'+$i;$result=Verify-Inputs $name
    $policy=Read-Json (Join-Path $sceneEvidence ($name+'/process-policy.json'))
    Require ($policy.performanceEligible -and -not $policy.diagnosticsOnly -and @($policy.otherAirProcessIds).Count -eq 0) ($name+' uncontended')
    Require ($result.nativeEntry -and $result.entryOnly -and -not $result.preload -and @($result.samples).Count -eq 1) ($name+' actual native entry')
    $sample=$result.samples[0];$times+=$sample.ms
    Require ($sample.ms -gt 0 -and $sample.ms -le 5000 -and $sample.units -ge 100 -and $sample.resident -gt 0 -and $sample.resident -lt 240) ($name+' full logical map within 5 seconds')
    Require (-not $result.PSObject.Properties['nativeProfile']) ($name+' no profiling host')
}
foreach($name in @('issues-v08-mechanics-release','native-v08-release-r2','factory-v08-release','experience-v08-rv323','upcoming-v08-rv323','issues-v08-combat-rv323','issues-v08-wall-trim-release-r2')){
    $result=Verify-Inputs $name
    if($name -eq 'upcoming-v08-rv323'){
        Require ($result.nativeEntry -and -not $result.preload -and $result.upcoming.emptyFrames -eq 0 -and @($result.upcoming.frames).Count -eq 600 -and $result.upcoming.misses -eq 0) 'Motion and zoom retain complete viewport'
        Require ($result.upcomingPixels.passed -and $result.upcomingPixels.surfaces -gt 0) 'Viewport matches full regional rendering'
    }else{Require (@($result.assertions).Count -ge 20 -and @($result.assertions|Where-Object {-not $_.ok}).Count -eq 0) ($name+' core assertions')}
    if($name -eq 'issues-v08-combat-rv323'){
        $policy=Read-Json (Join-Path $sceneEvidence ($name+'/process-policy.json'))
        Require ($policy.performanceEligible -and -not $policy.diagnosticsOnly -and @($policy.otherAirProcessIds).Count -eq 0) 'Combat sampling uncontended'
        Require (@($result.samples|Where-Object {$_.name -like '*-fire' -and $_.shots -gt 0}).Count -eq 2) 'Both native guns actually fired'
    }
    if($name -eq 'issues-v08-wall-trim-release-r2') {
        Require (@($result.wallTrim).Count -eq 8 -and @($result.assertions|Where-Object {$_.name -like 'wall-padding-visible-pixels-*' -and $_.ok}).Count -eq 6) 'Both wall styles retain exact visible pixels'
    }
}
$factory=Read-Json (Join-Path $sceneEvidence 'factory-v08-release/factory-audit.json')
Require ($factory.passed) 'Native factory contents and pixels'
$report=[ordered]@{version='0.8.0';status='checked';action=$Action;checkedAt=(Get-Date).ToString('o');passed=$true;entryMs=$times;files=$sceneFiles;checks=$sceneChecks;hostHash=$sceneFiles[0].after}
$report|ConvertTo-Json -Depth 12|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'generated/gate-v08.json') -Encoding utf8
if($Action -eq 'Check'){[pscustomobject]$report|Select-Object version,passed,entryMs;return}
Require (@(Get-Process -Name adl64 -ErrorAction SilentlyContinue).Count -eq 0) 'No AIR during deployment'
$backup=Join-Path $PSScriptRoot ('backups/upgrade-v08-'+(Get-Date -Format 'yyyyMMdd-HHmmssfff'))
Require (-not(Test-Path -LiteralPath $backup)) 'Unique backup'
foreach($file in $sceneFiles){
    $saved=Join-Path $backup $file.relative;New-Item -ItemType Directory -Path (Split-Path $saved) -Force|Out-Null
    Copy-Item -LiteralPath (Join-Path $sceneRoot $file.relative) -Destination $saved
    Require ((Hash $saved) -eq $file.before) ('Backup '+$file.relative)
}
$report.backup=$backup;$report.status='installing'
$report|ConvertTo-Json -Depth 12|Set-Content -LiteralPath $sceneReceipt -Encoding utf8
try{
    foreach($file in $sceneFiles){
        Require ((Hash (Join-Path $sceneRoot $file.relative)) -eq $file.before) ('Pre-replacement identity '+$file.relative)
        Copy-Item -LiteralPath (Join-Path $sceneFinal (Split-Path $file.relative -Leaf)) -Destination (Join-Path $sceneRoot $file.relative) -Force
        Require ((Hash (Join-Path $sceneRoot $file.relative)) -eq $file.after) ('Installed '+$file.relative)
    }
    & (Join-Path $PSScriptRoot 'installed-smoke.ps1') -Receipt '../state/deployment-v08.json' -SceneVersion '0.8.0' -VisionVersion 'v0.32.3' -WallVersion '0.5.8-scene' -LightVersion '0.3.1' -TdfcMarker 'scene-compat v0.6.4-scene1' -SceneRegistration 'registered 192x75 native land'
    $report.status='verified'
}catch{
    foreach($file in $sceneFiles){
        $now=Hash (Join-Path $sceneRoot $file.relative)
        if($now -eq $file.after){Copy-Item -LiteralPath (Join-Path $backup $file.relative) -Destination (Join-Path $sceneRoot $file.relative) -Force}
        elseif($now -ne $file.before){Write-Warning ('External update preserved: '+$file.relative)}
    }
    $report.status='installation-failed-rolled-back';throw
}finally{$report.checks=$sceneChecks;$report|ConvertTo-Json -Depth 12|Set-Content -LiteralPath $sceneReceipt -Encoding utf8}
[pscustomobject]$report|Select-Object version,status,entryMs,backup
