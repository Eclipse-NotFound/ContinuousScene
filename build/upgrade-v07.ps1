param([ValidateSet('Check','Install','Rollback')][string]$Action='Check',[string[]]$WallEvidence=@())
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneFinal=Join-Path $PSScriptRoot 'candidate-v07-final'
$sceneEvidence=Join-Path $PSScriptRoot '../knowledge/experiments/evidence'
$sceneReceipt=Join-Path $PSScriptRoot '../state/deployment-v07.json'
$sceneFiles=@(
    @{relative='pfe.swf';before='08A96759720C7A2AA489FCEEDB209C6E704500FDE7B1A4A49146BD578E99A8BC';after='2A4662488BA3B690EB23ACFE4B79ACA3F0D9AE114E5E2DEE7595AF3CABFFB3EA'},
    @{relative='mods/ContinuousScene/release/ContinuousSceneMod.swf';before='F6ED93AFF2BFB76B4AE8CA2A2E01B84BBE4D24A8DD59EB4DE720847C8457D8D2';after='70C06879A2CFFE85901E5C8E19FC1715028D5C38934975E970569468737309D5'},
    @{relative='mods/WallBlend/release/WallBlendMod.swf';before='3B1B40A65D7C57E4711C3861463B3470B0DFC086A8C8C01870C91A2F413DA96F';after='DF9AA07265E2538E115A5F048D272B85FC1C34D00EC4BC81585CD40D96648F76'}
)
$sceneChecks=@()
function Require([bool]$ok,[string]$name) {
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
        Require ($row.Path.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) ($name+' input inside isolated runtime')
        $relative=$row.Path.Substring($prefix.Length)
        if($relative -eq 'mods\loader-manifest.txt' -or $relative -like 'mods\ContinuousSceneProbe\*'){continue}
        $target=@($script:sceneFiles|Where-Object {$_.relative.Replace('/','\') -eq $relative})
        $expected=if($target.Count){$target[0].after}else{Hash (Join-Path $script:sceneRoot $relative)}
        Require ($row.Hash -eq $expected) ($name+' exact dependency '+$relative)
    }
    return $result
}
if($Action -eq 'Rollback'){
    Require (Test-Path -LiteralPath $sceneReceipt) 'Saved v07 receipt exists'
    $receipt=Read-Json $sceneReceipt
    Require (@(Get-Process -Name adl64 -ErrorAction SilentlyContinue).Count -eq 0) 'No AIR during rollback'
    foreach($file in $receipt.files){Require ((Hash (Join-Path $sceneRoot $file.relative)) -eq $file.after) ('Rollback refuses later updates: '+$file.relative)}
    foreach($file in $receipt.files){
        $saved=Join-Path $receipt.backup $file.relative
        Require ((Hash $saved) -eq $file.before) ('Backup verified: '+$file.relative)
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
    $audit.unchangedNamedMethodsAndInitializers -eq 4671 -and $audit.unchangedClassLayouts -eq 1015 -and $audit.originalConstantPoolPreserved) 'Unrelated native code and layouts preserved'
$sceneManifest='778B8D1E551E69F4A16B3F4131141FBE4B1E35E9E9EFF2F360593182B5C07D6C'
Require ((Hash (Join-Path $sceneRoot 'mods/loader-manifest.txt')) -eq $sceneManifest) 'Production loader manifest unchanged'
$production=@(Get-Content (Join-Path $sceneRoot 'mods/loader-manifest.txt')|Where-Object {$_ -match '^[^#]+\|[^|]+\|1\|'})
$testManifest=@(Get-Content (Join-Path $PSScriptRoot 'runtime/mods/loader-manifest.txt'))
# The isolated generator puts CS/probe last and disables their DLC columns.
# This release targets 1.02; compare enabled directory/class identities and
# multiplicity, then Verify-Inputs binds every binary to its production bytes.
$productionEntries=@($production|ForEach-Object {($_.Split('|')[0..1]) -join '|'})+@('ContinuousSceneProbe|ContinuousSceneProbe')
$testEntries=@($testManifest|Where-Object {$_ -match '^[^#]+\|[^|]+\|1\|'}|ForEach-Object {($_.Split('|')[0..1]) -join '|'})
Require ($testEntries.Count -eq $productionEntries.Count -and @($testEntries|Sort-Object -Unique).Count -eq $testEntries.Count -and
    @(Compare-Object $productionEntries $testEntries).Count -eq 0) 'Tests load the exact enabled 1.02 modules plus isolated probe'
Require ((Hash (Join-Path $sceneRoot 'mods/ContinuousScene/release/scene.xml')) -eq '1CEA74E218A55894D432E12CDFC544952D37CFFF5FF55B256B1B970573EB7A9E') 'Factory fixture unchanged'
$times=@()
foreach($i in 1..3){
    $name='loading-v07-final2-'+$i
    $result=Verify-Inputs $name
    $policy=Read-Json (Join-Path $sceneEvidence ($name+'/process-policy.json'))
    Require ($policy.performanceEligible -and -not $policy.diagnosticsOnly -and @($policy.otherAirProcessIds).Count -eq 0) ($name+' uncontended')
    Require ($result.nativeEntry -and $result.entryOnly -and -not $result.preload -and @($result.samples).Count -eq 1) ($name+' actual native entry, progressive rendering')
    $sample=$result.samples[0];$times+=$sample.ms
    Require ($sample.ms -gt 0 -and $sample.ms -le 5000 -and $sample.units -ge 100 -and $sample.resident -gt 0 -and $sample.resident -lt 240) ($name+' full logical world ready within 5 seconds')
    Require (-not $result.PSObject.Properties['nativeProfile']) ($name+' no diagnostic host')
}
foreach($name in @('native-v07-final','factory-v07-final','experience-v07-final','upcoming-v07-final')){
    $result=Verify-Inputs $name
    if($name -eq 'upcoming-v07-final'){
        Require ($result.nativeEntry -and -not $result.preload) 'Motion regression uses actual native progressive scene'
        Require ($result.upcoming.emptyFrames -eq 0 -and @($result.upcoming.frames).Count -eq 600) 'Continuous motion and zoom retain complete viewport'
        Require ($result.upcomingPixels.passed -and $result.upcomingPixels.surfaces -gt 0) 'Initial viewport pixels match full regional rendering'
        Require ($result.upcoming.misses -eq 0) 'Upcoming preparation avoids synchronous missing-surface fills during tested motion'
    }else{Require (@($result.assertions).Count -ge 30 -and @($result.assertions|Where-Object {-not $_.ok}).Count -eq 0) ($name+' complete passing assertions')}
}
$factory=Read-Json (Join-Path $sceneEvidence 'factory-v07-final/factory-audit.json')
Require ($factory.passed) 'Native factory content and pixels verified'
Require ($WallEvidence.Count -eq 3) 'Three frozen WallBlend suites supplied'
$kinds=@()
foreach($name in $WallEvidence){
    Require ($name -match '^[a-z0-9-]+$') 'Safe WallBlend evidence name'
    $base=Join-Path $sceneEvidence $name
    $provenance=Read-Json (Join-Path $base 'provenance.json')
    $result=Read-Json (Join-Path $base 'result.json')
    Require ($provenance.HostSHA256 -eq $sceneFiles[0].after -and $provenance.ModSHA256 -eq $sceneFiles[2].after) ($name+' exact host and wall candidate')
    Require ($result.passed -and @($result.assertions|Where-Object {-not $_.passed}).Count -eq 0) ($name+' passed')
    $kinds+=$provenance.Kind
}
Require (@(Compare-Object @('Harness','Coverage','Destruction') @($kinds|Sort-Object -Unique)).Count -eq 0) 'Wall historical modes, catalogue and destruction covered'
$report=[ordered]@{version='0.7.0';status='checked';action=$Action;checkedAt=(Get-Date).ToString('o');passed=$true;entryMs=$times;files=$sceneFiles;checks=$sceneChecks;wallEvidence=$WallEvidence;hostHash=$sceneFiles[0].after}
$report|ConvertTo-Json -Depth 12|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'generated/gate-v07.json') -Encoding utf8
if($Action -eq 'Check'){[pscustomobject]$report|Select-Object version,passed,entryMs;return}
Require (@(Get-Process -Name adl64 -ErrorAction SilentlyContinue).Count -eq 0) 'No AIR during deployment'
$backup=Join-Path $PSScriptRoot ('backups/upgrade-v07-'+(Get-Date -Format 'yyyyMMdd-HHmmssfff'))
Require (-not(Test-Path -LiteralPath $backup)) 'Unique deployment backup'
foreach($file in $sceneFiles){
    $saved=Join-Path $backup $file.relative
    New-Item -ItemType Directory -Path (Split-Path $saved) -Force|Out-Null
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
    $report.status='installed-pending-smoke'
}catch{
    foreach($file in $sceneFiles){
        $now=Hash (Join-Path $sceneRoot $file.relative)
        if($now -eq $file.after){Copy-Item -LiteralPath (Join-Path $backup $file.relative) -Destination (Join-Path $sceneRoot $file.relative) -Force}
        elseif($now -ne $file.before){Write-Warning ('External update preserved: '+$file.relative)}
    }
    $report.status='installation-failed';throw
}finally{$report.checks=$sceneChecks;$report|ConvertTo-Json -Depth 12|Set-Content -LiteralPath $sceneReceipt -Encoding utf8}
[pscustomobject]$report|Select-Object version,status,entryMs,backup
