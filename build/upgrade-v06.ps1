param(
    [ValidateSet('Check','Install','Rollback')][string]$Action='Check',
    [string]$FactoryEvidence='factory-v06-final',
    [string]$LabEvidence='lab-v06-final',
    [string]$ExperienceEvidence='experience-v06-final',
    [string]$PerfEvidence='perf-v06-final',
    [string]$NativeEvidence='native-v06-final',
    [string[]]$WallEvidence=@(),
    [string[]]$LightEvidence=@()
)
# Check is read-only. Install is an explicit, separate invocation after review.
# This release replaces exactly four SWFs; neither fixture XML nor manifest is copied.
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneRuntime=Join-Path $PSScriptRoot 'runtime'
$sceneReceiptPath=Join-Path $PSScriptRoot 'upgrade-v06-receipt.json'
$sceneSceneHash='1CEA74E218A55894D432E12CDFC544952D37CFFF5FF55B256B1B970573EB7A9E'
$sceneManifestHash='35A1A1764B730C6DA1899EB9B2D622916E98FCBA27BD4FB0D973C3B67109E1F2'
$sceneOriginalHash='C631CBF3511B6EE303F533D08D51511FE0EB702F43E5DB17F5241D8576C64867'
$sceneMap1Hash='BEBEEA8B3F40A7DB3E7B1BE6F3530D5AF9EA7A3299DECB164BF0DAE107D4011F'
$sceneLandHash='B1727E83FBEC9863A267B07B5428853CB734C442572D747D592922E8B1EBC060'
$sceneFiles=@(
    [ordered]@{relative='pfe.swf';before='9987C696BEBBEB0626D8F73DA775CF867B2CED4FF626137FD9F161264270F938'},
    [ordered]@{relative='mods/ContinuousScene/release/ContinuousSceneMod.swf';before='E977168ED9F1B21FA27A01361E18483D83AAF0808B1A657838F06F6284A81928'},
    [ordered]@{relative='mods/WallBlend/release/WallBlendMod.swf';before='8EAC7B08BABF2631A1897C988C36416BA8B6CF204788256B46F436CACB319BB3'},
    [ordered]@{relative='mods/LightAndDarkness/release/LightAndDarknessMod.swf';before='01767319A54AC88961B2BA40391F0FA79359486EE5591E6A22D90AD49F84537C'}
)
$sceneReport=[ordered]@{version='0.6.0';action=$Action;checkedAt=(Get-Date).ToString('o');passed=$false;checks=@();evidence=@();files=$sceneFiles}

function Test-Gate([bool]$Condition,[string]$Name,$Detail=$null) {
    $script:sceneReport.checks+=,[ordered]@{name=$Name;passed=$Condition;detail=$Detail}
    if(-not $Condition) {throw $Name}
}
function Read-Json([string]$Path) {Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json}
function File-Hash([string]$Path) {(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash}
function Full-Path([string]$Path) {[IO.Path]::GetFullPath($Path)}
function Require-Hash([string]$Path,[string]$Expected,[string]$Name) {
    Test-Gate ($Expected -match '^[a-fA-F0-9]{64}$') ($Name+' has a complete SHA256')
    $actual=File-Hash $Path
    Test-Gate ($actual -eq $Expected) $Name @{path=$Path;expected=$Expected;actual=$actual}
}
function Require-Assertions($Result,[string[]]$Names,[string]$Suite) {
    foreach($name in $Names) {
        $rows=@($Result.assertions | Where-Object {$_.name -eq $name})
        Test-Gate ($rows.Count -gt 0 -and @($rows | Where-Object {$_.ok -ne $true}).Count -eq 0) ($Suite+': '+$name)
    }
}
function Hash-Index($Rows,[string[]]$ExpectedPaths,[string]$Label) {
    $index=@{}
    foreach($row in $Rows) {
        $path=Full-Path $row.Path
        Test-Gate (-not $index.ContainsKey($path)) ($Label+': unique hash entry '+$path)
        Test-Gate ($row.Algorithm -eq 'SHA256' -and $row.Hash -match '^[a-fA-F0-9]{64}$') ($Label+': SHA256 '+$path)
        $index[$path]=[string]$row.Hash
    }
    $expected=@($ExpectedPaths | ForEach-Object {Full-Path $_})
    Test-Gate (@(Compare-Object @($index.Keys) $expected).Count -eq 0) ($Label+': complete file set')
    return $index
}
function Enabled-Rows([string]$Path) {
    $rows=@();$seen=@{}
    foreach($line in Get-Content -LiteralPath $Path) {
        if([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) {continue}
        $fields=$line.Split('|')
        Test-Gate ($fields.Count -eq 5 -and $fields[0] -match '^[A-Za-z0-9_&-]+$' -and $fields[1] -match '^[A-Za-z0-9_]+$') ('Valid loader row: '+$line)
        if($fields[2] -ne '1') {continue}
        $key=$fields[0]+'|'+$fields[1]
        Test-Gate (-not $seen.ContainsKey($key)) ('Unique enabled loader: '+$key)
        $seen[$key]=$true;$rows+=,$key
    }
    return $rows
}
function Percentile($Values,[double]$Fraction) {
    $sorted=@($Values | Sort-Object)
    # Match perf-summary.py and the preserved baseline: ordinary median,
    # upper empirical quantile at floor(n*f) for P95/P99, clamped at the end.
    if($Fraction -eq .5) {
        $mid=[int][Math]::Floor($sorted.Count/2)
        if($sorted.Count%2 -eq 0) {return ([double]$sorted[$mid-1]+[double]$sorted[$mid])/2}
        return $sorted[$mid]
    }
    return $sorted[[Math]::Min($sorted.Count-1,[Math]::Max(0,[int][Math]::Floor($sorted.Count*$Fraction)))]
}
function Require-Perf($Result) {
    $summary=@()
    foreach($world in @('native','large')) {
        $entry=@($Result.samples | Where-Object {$_.world -eq $world -and $_.PSObject.Properties['entryMs']})
        Test-Gate ($entry.Count -eq 1 -and $entry[0].entryMs -gt 0) ('Perf '+$world+' entry measured')
        if($world -eq 'large') {Test-Gate ($entry[0].resident -eq 240) 'Perf all 240 surfaces resident'}
        $names=if($world -eq 'native') {@('idle','fire','idle-after')} else {@('idle','fire','idle-after','culled-fire','no-lad-fire','no-lad-wall-fire','no-lad-wall-rv-fire')}
        foreach($name in $names) {
            $rows=@($Result.samples | Where-Object {$_.world -eq $world -and $_.PSObject.Properties['name'] -and $_.name -eq $name})
            Test-Gate ($rows.Count -eq 1) ('Perf unique case '+$world+'/'+$name)
            $row=$rows[0]
            Test-Gate (@($row.frames).Count -eq 120 -and @($row.script).Count -eq 120 -and
                @($row.frames | Where-Object {$_ -lt 0 -or [double]::IsNaN([double]$_) -or [double]::IsInfinity([double]$_)}).Count -eq 0 -and
                @($row.script | Where-Object {$_ -lt 0 -or [double]::IsNaN([double]$_) -or [double]::IsInfinity([double]$_)}).Count -eq 0) ('Perf complete finite samples '+$world+'/'+$name)
            Test-Gate (-not $row.PSObject.Properties['visionProfile']) ('Perf without diagnostic profiler '+$world+'/'+$name)
            Test-Gate ($row.redrawsStart -eq $row.redrawsEnd) ('Perf no terrain redraw '+$world+'/'+$name)
            if($name.Contains('fire')) {Test-Gate ($row.shots -gt 0) ('Perf actual weapon fired '+$world+'/'+$name)}
            if($world -eq 'large' -and $name.Contains('fire')) {Test-Gate ($row.dirtyMax -gt 0 -and $row.dirtyMax -lt 240) ('Perf impacts remain local '+$name)}
            $summary+=,[ordered]@{world=$world;case=$name;entryMs=$entry[0].entryMs;frames=@($row.frames).Count;shots=$row.shots;p50Ms=(Percentile $row.frames .5);p95Ms=(Percentile $row.frames .95);maxMs=(Percentile $row.frames 1);dirtyMax=$row.dirtyMax}
        }
    }
    Test-Gate (@($Result.samples).Count -eq 12) 'Perf complete native and large scenario set'
    # These are measurement/completeness gates, not an invented FPS acceptance budget.
    $script:sceneReport.performance=$summary
}
function Write-Receipt($Receipt,[bool]$Create=$false) {
    $json=$Receipt | ConvertTo-Json -Depth 12
    $bytes=[Text.UTF8Encoding]::new($false).GetBytes($json)
    $mode=if($Create) {[IO.FileMode]::CreateNew} else {[IO.FileMode]::Create}
    $stream=[IO.File]::Open($script:sceneReceiptPath,$mode,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try {$stream.Write($bytes,0,$bytes.Length);$stream.Flush()} finally {$stream.Dispose()}
    # The rollback data is also retained alongside this release's independent backups.
    [IO.File]::WriteAllText((Join-Path $Receipt.backupDirectory 'receipt.json'),$json,[Text.UTF8Encoding]::new($false))
}
function Replace-Checked([string]$Source,[string]$Target,[string]$Before,[string]$After) {
    Require-Hash $Source $After ('Replacement source unchanged: '+$Source)
    Require-Hash $Target $Before ('Replacement target unchanged: '+$Target)
    $stage=$Target+'.cs-v06-'+[Guid]::NewGuid().ToString('N')+'.stage'
    $ownedStage=$false
    try {
        [IO.File]::Copy($Source,$stage,$false)
        $ownedStage=$true
        Require-Hash $stage $After ('Staged replacement verified: '+$Target)
        Require-Hash $Target $Before ('Final target recheck: '+$Target)
        # PowerShell coerces ordinary $null to String.Empty for this overload.
        # A real null means no extra OS backup (our hashed backups already exist).
        [IO.File]::Replace($stage,$Target,[NullString]::Value)
        Require-Hash $Target $After ('Replacement verified: '+$Target)
    } finally {
        if($ownedStage -and (Test-Path -LiteralPath $stage)) {Remove-Item -LiteralPath $stage}
    }
}

try {
    foreach($file in $sceneFiles) {$file.target=Join-Path $sceneRoot $file.relative;$file.source=Join-Path $sceneRuntime $file.relative}
    $manifest=Join-Path $sceneRoot 'mods/loader-manifest.txt'
    $sceneXML=Join-Path $sceneRoot 'mods/ContinuousScene/release/scene.xml'
    if($Action -eq 'Rollback') {
        $receipt=Read-Json $sceneReceiptPath
        Test-Gate ($receipt.version -eq '0.6.0' -and $receipt.status -in @('installed','prepared','install-failed','rolling-back')) 'Recognized 0.6 rollback receipt'
        Test-Gate (@($receipt.files).Count -eq 4) 'Rollback replaces exactly four files'
        $backupDir=Full-Path $receipt.backupDirectory
        $backupRoot=(Full-Path (Join-Path $PSScriptRoot 'backups'))+[IO.Path]::DirectorySeparatorChar
        Test-Gate ($backupDir.StartsWith($backupRoot,[StringComparison]::OrdinalIgnoreCase) -and (Split-Path $backupDir -Leaf) -match '^upgrade-v06-[0-9-]+-[a-f0-9]{8}$') 'Rollback directory belongs to this release'
        Require-Hash $manifest $receipt.manifestHash 'Rollback preserves unchanged manifest'
        Require-Hash $sceneXML $sceneSceneHash 'Rollback preserves factory XML'
        # These files are outside the rollback write set. Later independent
        # releases are recorded and preserved, never used to block a safe
        # restore of the four still-matching targets below.
        $sceneReport.rollbackPreservedModules=@($receipt.unchangedModules | ForEach-Object {
            $currentModuleHash=File-Hash (Join-Path $sceneRoot $_.relative)
            [ordered]@{relative=$_.relative;installedHash=$_.hash;currentHash=$currentModuleHash;changedSinceInstall=$currentModuleHash -ne $_.hash}
        })
        foreach($file in $sceneFiles) {
            $matches=@($receipt.files | Where-Object {$_.relative -eq $file.relative})
            Test-Gate ($matches.Count -eq 1) ('Rollback unique file: '+$file.relative)
            $saved=$matches[0]
            $expectedBackup=Join-Path $backupDir (Split-Path $file.target -Leaf)
            Test-Gate ((Full-Path $saved.target) -eq (Full-Path $file.target) -and (Full-Path $saved.backup) -eq (Full-Path $expectedBackup) -and $saved.before -eq $file.before -and $saved.after -match '^[a-fA-F0-9]{64}$') ('Rollback trusted paths and hashes: '+$file.relative)
            Require-Hash $saved.backup $file.before ('Rollback backup intact: '+$file.relative)
            $current=File-Hash $file.target
            $permitted=($current -eq $saved.after) -or ($receipt.status -ne 'installed' -and $current -eq $file.before)
            Test-Gate $permitted ('Rollback refuses later edits: '+$file.relative) @{actual=$current;installed=$saved.after;before=$file.before}
            $file.after=$saved.after;$file.backup=$saved.backup;$file.current=$current
        }
        # Validate every target before restoring any one of them. A resumed
        # interrupted rollback accepts only its own before/after bytes.
        $receipt.status='rolling-back';Write-Receipt $receipt
        foreach($file in $sceneFiles) {
            if($file.current -ne $file.before) {Replace-Checked $file.backup $file.target $file.after $file.before}
        }
        Require-Hash $manifest $receipt.manifestHash 'Manifest untouched after rollback'
        Require-Hash $sceneXML $sceneSceneHash 'Scene XML untouched after rollback'
        $receipt.status='rolled-back';$receipt | Add-Member -NotePropertyName rolledBackAt -NotePropertyValue (Get-Date).ToString('o') -Force
        Write-Receipt $receipt
        $sceneReport.passed=$true;$sceneReport.message='Restored the four pre-0.6 SWFs. Manifest, factory XML and other modules were preserved. Restart is required.'
        $sceneReport | ConvertTo-Json -Depth 12
        return
    }

    # Constants above are corroborated by published receipts, never learned from
    # whichever bytes happen to be installed when this script is invoked.
    $rc=Read-Json (Join-Path $sceneRoot 'mods/RConnect/build/m52/a22-map-only-03/deployment.json')
    Test-Gate ($rc.status -eq 'deployed-smoke-passed' -and $rc.version -eq '0.2.22-map1' -and $rc.proof.candidate_game_sha256 -eq $sceneMap1Hash) 'Published RConnect Map1 host receipt'
    $v05=Read-Json (Join-Path $PSScriptRoot 'upgrade-v05-receipt.json')
    Test-Gate ($v05.status -eq 'installed' -and $v05.version -eq '0.5.0') 'Published CS 0.5 receipt'
    foreach($file in $sceneFiles[0..2]) {
        $rows=@($v05.files | Where-Object {$_.relative -eq $file.relative})
        Test-Gate ($rows.Count -eq 1 -and $rows[0].after -eq $file.before) ('Published baseline receipt: '+$file.relative)
    }
    $lad=Read-Json (Join-Path $sceneRoot 'mods/LightAndDarkness/build/backups/atmosphere-20261015-193655-513/receipt.json')
    Test-Gate ($lad.status -eq 'deployed-smoke-passed' -and $lad.version -eq '0.2.0' -and $lad.candidateSHA256 -eq $sceneFiles[3].before) 'Published LightAndDarkness 0.2 receipt'
    foreach($file in $sceneFiles) {
        Require-Hash $file.target $file.before ('Known production baseline: '+$file.relative)
        $file.after=File-Hash $file.source
        Test-Gate ($file.after -ne $file.before) ('New candidate bytes: '+$file.relative)
    }
    Require-Hash $manifest $sceneManifestHash 'Known production manifest'
    Require-Hash $sceneXML $sceneSceneHash 'Unchanged production factory XML'
    Require-Hash (Join-Path $sceneRuntime 'scene-factory.xml') $sceneSceneHash 'Unchanged candidate factory fixture'
    [xml]$descriptor=Get-Content -LiteralPath (Join-Path $sceneRoot 'application.xml') -Raw
    Test-Gate ($descriptor.application.initialWindow.content -eq 'pfe.swf') 'Production launch targets root pfe.swf'

    $baseline=Read-Json (Join-Path $PSScriptRoot 'generated/baseline.json')
    Test-Gate ($baseline.source_sha256 -eq $sceneOriginalHash -and $baseline.merge_source_sha256 -eq $sceneMap1Hash -and $baseline.land_source_sha256 -eq $sceneLandHash) 'Reviewed original plus Map1 merge provenance'
    Require-Hash (Join-Path $sceneRoot 'mods/RConnect/build/m52/a22-map-only-03/native/pfe.swf') $sceneMap1Hash 'Map1 merge source remains intact'
    $auditPath=Join-Path $PSScriptRoot 'generated/audit/bytecode-audit.json'
    $audit=Read-Json $auditPath
    $requiredMethods=@('fe.inter.Camera::0:1:calc','fe.inter.Camera::0:1:setZoom','fe.loc.Box::0:1:addVisual','fe.loc.Box::0:1:runVis','fe.loc.Game::0:1:save','fe.loc.Land::0:1:createMap','fe.loc.Location::<init>','fe.unit.Unit::0:1:setVisPos','fe.unit.UnitPlayer::0:1:actions','fe.unit.UnitPlayer::0:1:crackAction','fe.loc.Area::0:1:damTiles','fe.loc.Area::0:1:setLift','fe.loc.Game::0:1:enterToCurLand','fe.loc.Land::0:1:gotoLoc','fe.loc.Land::0:1:gotoProb','fe.loc.Land::0:1:setGGToSpawnPoint','fe.loc.Location::0:1:step')
    Test-Gate ($audit.passed -eq $true -and $audit.chunkRendererPresent -eq $true -and $audit.rconnectLandLayoutPreserved -eq $true -and $audit.sourceHostSHA256 -eq $sceneMap1Hash -and $audit.finalHostSHA256 -eq $sceneFiles[0].after -and $audit.unchangedNamedMethodsAndInitializers -eq 4652 -and $audit.originalCount -eq 4710 -and @(Compare-Object @($audit.requiredReplacements) $requiredMethods).Count -eq 0) 'Merged host bytecode and RConnect Land traits verified'
    $auditHash=File-Hash $auditPath

    $productionRows=@(Enabled-Rows $manifest)
    $runtimeManifest=Join-Path $sceneRuntime 'mods/loader-manifest.txt'
    $runtimeRows=@(Enabled-Rows $runtimeManifest)
    Test-Gate (@(Compare-Object $productionRows @($runtimeRows | Where-Object {$_ -ne 'ContinuousSceneProbe|ContinuousSceneProbe'})).Count -eq 0) 'Exact installed 1.02 module set plus isolated probe'
    Test-Gate (@($runtimeRows | Where-Object {$_ -eq 'ContinuousSceneProbe|ContinuousSceneProbe'}).Count -eq 1) 'Isolated probe enabled once'
    $loadedPaths=@($runtimeManifest)
    $unchangedModules=@()
    foreach($row in $runtimeRows) {
        $fields=$row.Split('|');$relative='mods/'+$fields[0]+'/release/'+$fields[1]+'.swf'
        $loadedPaths+=,(Join-Path $sceneRuntime $relative)
        if($row -eq 'ContinuousSceneProbe|ContinuousSceneProbe') {continue}
        # Exemption is derived from the exact four-file write set, not mod names.
        if(@($sceneFiles | Where-Object {$_.relative -eq $relative}).Count) {continue}
        $hash=File-Hash (Join-Path $sceneRuntime $relative)
        $productionHash=File-Hash (Join-Path $sceneRoot $relative)
        if($relative -eq 'mods/RealisticVision/release/RealisticVisionMod.swf' -and $productionHash -ne $hash) {
            # The independently rebuilt frozen RV differs solely in its
            # ProductInfo compilation date. All code/resources remain equal.
            $proofText=& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' (Join-Path $PSScriptRoot 'verify_rv_rebuild.py')
            Test-Gate ($LASTEXITCODE -eq 0) 'RV pinned rebuild differs only in ProductInfo date'
            $proof=$proofText | ConvertFrom-Json
            Test-Gate ($proof.passed -and $proof.production.sha256 -eq $productionHash -and $proof.runtime.sha256 -eq $hash) 'RV timestamp equivalence bound to current bytes'
            $sceneReport.visionRebuildProof=$proof
        } else {Require-Hash (Join-Path $sceneRoot $relative) $hash ('Other enabled module equals tested candidate: '+$relative)}
        $unchangedModules+=,[ordered]@{relative=$relative;hash=$productionHash}
    }
    $buildPaths=@((Join-Path $sceneRuntime 'pfe.swf'),(Join-Path $sceneRuntime 'mods/ContinuousScene/release/ContinuousSceneMod.swf'),(Join-Path $sceneRuntime 'mods/ContinuousSceneProbe/release/ContinuousSceneProbe.swf'),(Join-Path $sceneRuntime 'scene.xml'))
    $suitePlans=@(@{kind='Factory';name=$FactoryEvidence;mode='factory';fixture='scene-factory.xml'},@{kind='Lab';name=$LabEvidence;mode='full';fixture='scene-lab.xml'},@{kind='Experience';name=$ExperienceEvidence;mode='experience';fixture='scene-factory.xml'},@{kind='Perf';name=$PerfEvidence;mode='performance';fixture='scene-factory.xml'},@{kind='Native';name=$NativeEvidence;mode='native-map';fixture='scene-factory.xml'})
    Test-Gate (@($suitePlans.name | Select-Object -Unique).Count -eq 5) 'Five distinct evidence directories'
    foreach($suite in $suitePlans) {
        Test-Gate ($suite.name -match '^[a-z0-9-]+$') ('Safe evidence name: '+$suite.name)
        $dir=Join-Path $PSScriptRoot ('../knowledge/experiments/evidence/'+$suite.name)
        $result=Read-Json (Join-Path $dir 'result.json')
        Test-Gate ($result.ok -eq $true -and $result.mode -eq $suite.mode -and @($result.assertions | Where-Object {$_.ok -ne $true}).Count -eq 0) ($suite.kind+' runtime result passed')
        if($suite.kind -ne 'Experience') {Test-Gate ($result.preload -eq $true) ($suite.kind+' preloaded run')}
        $build=Hash-Index @(Read-Json (Join-Path $dir 'build-hashes.json')) $buildPaths ($suite.kind+' build evidence')
        foreach($path in $buildPaths) {
            if($path -eq (Join-Path $sceneRuntime 'scene.xml')) {
                Require-Hash (Join-Path $dir 'scene.xml') $build[(Full-Path $path)] ($suite.kind+' preserved scene bytes')
                Require-Hash (Join-Path $sceneRuntime $suite.fixture) $build[(Full-Path $path)] ($suite.kind+' fixture matches current candidate')
            } else {Require-Hash $path $build[(Full-Path $path)] ($suite.kind+' tested build bytes: '+$path)}
        }
        $loaded=Hash-Index @(Read-Json (Join-Path $dir 'loaded-module-hashes.json')) $loadedPaths ($suite.kind+' loaded evidence')
        foreach($path in $loadedPaths) {Require-Hash $path $loaded[(Full-Path $path)] ($suite.kind+' tested loaded bytes: '+$path)}
        Require-Hash (Join-Path $dir 'bytecode-audit.json') $auditHash ($suite.kind+' exact merged-host bytecode audit')
        if($suite.kind -eq 'Factory') {
            Require-Assertions $result @('factory-dimensions','factory-12-original-regions','factory-decorations-loaded','factory-single-location','factory-all-240-surfaces-preloaded','factory-exploration-keeps-preloaded-map','factory-player-walks-original-passage','factory-bullet-crosses-passage-and-hits','factory-enemy-chases-across-passage','factory-combat-keeps-preloaded-map','factory-return-base','factory-new-mission-refreshes','factory-native-save-load','loaded-ContinuousSceneMod','loaded-RealisticVisionMod','loaded-WallBlendMod') 'Factory'
            $factory=Read-Json (Join-Path $dir 'factory-audit.json')
            $factoryNames=@('factory-source-selected','factory-12-native-rooms','factory-native-interiors-preserved','factory-444-native-objects-preserved','factory-603-native-decorations-preserved','factory-object-identifiers-unique','native-raster-layer-0','native-raster-layer-1','native-raster-layer-2','native-raster-layer-3')
            Test-Gate ($factory.passed -eq $true -and @($factory.checks).Count -eq 10 -and @($factory.checks | Where-Object {$_.passed -ne $true}).Count -eq 0 -and @(Compare-Object @($factory.checks.name) $factoryNames).Count -eq 0) 'Factory all ten native-content/pixel audit checks'
            Require-Hash (Join-Path $sceneRoot 'Rooms/rooms_plant.xml') $factory.sourceSHA256 'Factory source matches audited original rooms'
            Test-Gate ($factory.sceneSHA256 -eq $sceneSceneHash) 'Factory audit uses unchanged production scene'
        } elseif($suite.kind -eq 'Lab') {
            Require-Assertions $result @('travel-respects-noAct','travel-respects-other-pause','travel-respects-story','travel-respects-injury','travel-respects-weight','whole-map-ready-before-play','walk-across-three-old-rooms','walk-does-not-regenerate-map','enemy-chases-across-room-and-render-boundaries','bullet-crosses-and-damages','physical-projectile-crosses','vertical-continuity-and-floor','projectile-destroys-tile','distant-raster-untouched-by-local-combat','normal-room-renderer-restored','scene-reentry-preserves-location','native-save-reloads-large-scene','destroyed-terrain-survives-native-load','destroyed-visual-survives-native-load','older-slot-retains-undamaged-terrain','resaved-slot-retains-damage','wallblend-large-scene-foreground','wallblend-large-scene-background','native-loader-RConnectMod','native-loader-RealisticVisionMod','native-loader-WallBlendMod') 'Lab'
        } elseif($suite.kind -eq 'Experience') {
            foreach($world in @('native','large')) {
                $names=@('map-ui-info-page-open','map-ui-uses-native-land-raster','map-ui-visible-and-clipped','map-ui-player-marker-exists','map-ui-player-within-raster','map-ui-player-aligned','map-ui-native-zoom','map-ui-native-center','map-ui-pan-transform-keeps-player-aligned','map-check-restores-ui','native-interaction-execution-0','native-interaction-execution-1','zoom-0-persists','zoom-1-persists','zoom-2-persists','background-covers-screen-zoom-0','background-covers-screen-zoom-1','background-covers-screen-zoom-2')
                Require-Assertions $result @($names | ForEach-Object {$world+'-'+$_}) 'Experience'
            }
            Require-Assertions $result @('native-map-native-grid-dimensions-unchanged','large-map-full-scene-dimensions','large-map-ui-initial-fitting-axes-visible','large-map-far-terrain-can-be-revealed','large-map-unexplored-far-terrain-stays-hidden','large-map-far-exploration-alpha','large-explored-map-full-scene-dimensions','large-explored-map-ui-player-aligned','large-explored-map-far-exploration-alpha','large-render-light-field-full-scene','large-render-far-native-light-pixel','large-render-native-light-transform','large-render-native-light-bilinear','large-render-native-light-drawn-gradient','large-render-factory-twelve-region-styles','large-render-region-native-red-style','large-render-region-native-blue-style','large-render-region-crossing-clips-cover-once','large-render-cross-region-water-exact-native-pixels','large-render-incremental-style-restored','large-render-water-only-touches-overlapping-chunks','large-all-surfaces-resident','large-decal-large-explosion-exceeds-old-centre-cutoff','large-decal-history-end-only') 'Experience'
            foreach($case in @('small-bullet-corner','rotated-scaled-bullet','mirrored-rotated-bullet','large-explosion')) {
                Require-Assertions $result @(@('reference-encloses-native-output','native-alpha-preservation','native-equivalent-buffer-pixels','crosses-neighbour-and-gutter','dirty-work-is-local','no-terrain-redraw') | ForEach-Object {'large-decal-'+$case+'-'+$_}) 'Experience'
                $decalRows=@($result.assertions | Where-Object {$_.name -eq ('large-decal-'+$case+'-native-equivalent-buffer-pixels')})
                Test-Gate ($decalRows.Count -eq 1) ('Experience unique decal pixel verdict: '+$case)
                $decal=$decalRows[0].detail
                Test-Gate ($decal.insideAlphaTolerance -eq 0 -and $decal.insideAlphaDifferenceCount -eq 0 -and
                    $decal.rejectedAlphaDifferenceCount -eq 0 -and $decal.rejectedColorPixels -eq 0 -and
                    $decal.rejectedOutsideRasterPixels -eq 0 -and $decal.outsideRawChannelTolerance -eq 8 -and
                    $decal.premultipliedProductTolerance -eq 255 -and $decal.differencePixelLimit -eq 64 -and
                    $decal.differencePixelCount -ge 0 -and $decal.differencePixelCount -le 64) ('Experience exact native alpha and bounded per-pixel raster rules: '+$case)
            }
            Require-Assertions $result @('large-render-power-fixture-restorable','large-render-power-on-off-pixels-differ','large-render-power-state-restored','large-render-power-restored-full-repaint') 'Experience'
            foreach($power in @('off','on')) {
                Require-Assertions $result @(@('native-state','regions-and-materials','backdrop-frames','entity-base-colors','full-repaint') | ForEach-Object {'large-render-power-'+$power+'-'+$_}) 'Experience'
            }
            Test-Gate (@($result.interactions).Count -eq 4 -and @($result.interactions | Where-Object {$_.result.ok -ne $true -or @($_.result.checks | Where-Object {$_.ok -ne $true}).Count -gt 0}).Count -eq 0) 'Experience all native interaction fixtures passed'
            Test-Gate (@($result.views).Count -eq 12 -and @($result.views.room | Select-Object -Unique).Count -eq 12) 'Experience twelve distinct native room views'
            foreach($image in @('native-map.png','large-map.png','large-map-explored.png','large-map-debug-full.png')+@($result.views | ForEach-Object {'region-'+$_.room+'.png'})) {
                Test-Gate ((Test-Path -LiteralPath (Join-Path $dir $image) -PathType Leaf) -and (Get-Item -LiteralPath (Join-Path $dir $image)).Length -gt 0) ('Experience screenshot available: '+$image)
            }
        } elseif($suite.kind -eq 'Native') {
            Require-Assertions $result @('setting-true','setting-false','base-remains-native','native-merged','native-live-chain','native-back-room-coverage','ordinary-return-keeps-native-generation','new-mission-refreshes-generation','native-save-load-preserves-random-return-rule','native-save-load-regenerates-large-mode','native-map-ui-player-aligned','native-map-full-scene-dimensions','ordinary-return-keeps-lamp-damage','new-mission-refreshes-lamps','disabled-native-room-size') 'Native'
        } else {
            Require-Perf $result
            $policy=Read-Json (Join-Path $dir 'process-policy.json')
            Test-Gate ($policy.PSObject.Properties['otherAirProcessIds'] -and @($policy.otherAirProcessIds).Count -eq 0) 'Perf no overlapping AIR instances observed'
        }
        $sceneReport.evidence+=,[ordered]@{suite=$suite.kind;directory=$dir;mode=$result.mode;resultSHA256=(File-Hash (Join-Path $dir 'result.json'));assertions=@($result.assertions).Count;elapsedMs=$result.elapsedMs}
    }
    Test-Gate ($WallEvidence.Count -eq 3 -and @($WallEvidence | Select-Object -Unique).Count -eq 3) 'Three distinct WB suites supplied'
    $wallKinds=@()
    foreach($name in $WallEvidence) {
        Test-Gate ($name -match '^[a-z0-9-]+$') 'Safe WB evidence path'
        $dir=Join-Path $PSScriptRoot ('../knowledge/experiments/evidence/'+$name)
        $proof=Read-Json (Join-Path $dir 'provenance.json');$result=Read-Json (Join-Path $dir 'result.json')
        Test-Gate ($proof.HostSHA256 -eq $sceneFiles[0].after -and $proof.ModSHA256 -eq $sceneFiles[2].after -and $proof.TestCommit -eq 'f32e4a99643ccc901dc4f8e8caac29a6cde441b4') 'WB exact tested host, module and frozen test lineage'
        Test-Gate ($result.passed -eq $true -and @($result.assertions | Where-Object {-not $_.passed}).Count -eq 0) ('WB suite '+$proof.Kind)
        $wallKinds+=$proof.Kind
    }
    Test-Gate (@(Compare-Object $wallKinds @('Harness','Coverage','Destruction')).Count -eq 0) 'WB test coverage complete'
    Test-Gate ($LightEvidence.Count -eq 2 -and $LightEvidence[1].StartsWith($LightEvidence[0]+'-cold-')) 'LAD warm and cold storage checks supplied'
    foreach($name in $LightEvidence) {
        Test-Gate ($name -match '^remains-lad-test-[0-9]+(-cold-[0-9]+)?$') 'Safe LAD evidence path'
        $dir=Join-Path $sceneRoot ('mods/LightAndDarkness/build/evidence/'+$name)
        $log=Get-Content -LiteralPath (Join-Path $dir 'storage/test.log') -Raw
        Test-Gate ($log -match '(?m)^\d+ SUITE_PASS$' -and $log -notmatch '(?m)^\d+ FAIL ') ('LAD checks passed '+$name)
        if($name -eq $LightEvidence[0]) {Test-Gate ($log.Contains('PASS fixtures prepared before first large-scene raster') -and $log.Contains('PASS resized illumination retains smooth interpolation')) 'LAD new scene preparation and smoothing covered'}
        $lightHashes=@(Read-Json (Join-Path $dir 'candidate-hashes.json'))
        $lightRoot=Join-Path $sceneRoot 'mods/LightAndDarkness/build/runtime'
        $lightPaths=@('pfe.swf','mods/LightAndDarkness/release/LightAndDarknessMod.swf','mods/LightAndDarkness/atmosphere.json','mods/ContinuousScene/release/ContinuousSceneMod.swf','mods/RealisticVision/release/RealisticVisionMod.swf','mods/WallBlend/release/WallBlendMod.swf','mods/ModLoader/release/ModLoaderMod.swf')
        $null=Hash-Index $lightHashes @($lightPaths | ForEach-Object {Join-Path $lightRoot $_}) ('LAD complete evidence '+$name)
        foreach($hash in $lightHashes) {
            $path=Full-Path $hash.Path;$prefix=(Full-Path (Join-Path $sceneRoot 'mods/LightAndDarkness/build/runtime'))+[IO.Path]::DirectorySeparatorChar
            Test-Gate ($path.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) 'LAD evidence belongs to isolated runtime'
            $relative=$path.Substring($prefix.Length)
            Require-Hash (Join-Path $sceneRuntime $relative) $hash.Hash ('LAD same candidate '+$relative)
        }
    }
    $atmosphereHash=File-Hash (Join-Path $sceneRuntime 'mods/LightAndDarkness/atmosphere.json')
    Require-Hash (Join-Path $sceneRoot 'mods/LightAndDarkness/atmosphere.json') $atmosphereHash 'LAD atmosphere configuration unchanged and tested'
    $sceneReport.wallEvidence=$WallEvidence;$sceneReport.lightEvidence=$LightEvidence
    $sceneReport.unchangedModules=$unchangedModules
    $sceneReport.manifestHash=$sceneManifestHash;$sceneReport.sceneXMLHash=$sceneSceneHash
    foreach($file in $sceneFiles) {
        Require-Hash $file.target $file.before ('Final baseline recheck: '+$file.relative)
        Require-Hash $file.source $file.after ('Final candidate recheck: '+$file.relative)
    }
    Require-Hash $manifest $sceneManifestHash 'Final unchanged manifest recheck'
    Require-Hash $sceneXML $sceneSceneHash 'Final unchanged factory XML recheck'
    Require-Hash (Join-Path $sceneRoot 'mods/LightAndDarkness/atmosphere.json') $atmosphereHash 'Final tested atmosphere recheck'
    if($Action -eq 'Check') {
        $sceneReport.passed=$true;$sceneReport.message='All five suites and compatibility suites, exact runtime bytes, merged-host audit and installed baselines passed. Check made no changes.'
        $sceneReport | ConvertTo-Json -Depth 12
        return
    }

    Test-Gate (-not (Test-Path -LiteralPath $sceneReceiptPath)) 'Refuse to overwrite an existing 0.6 receipt'
    $stamp=(Get-Date -Format 'yyyyMMdd-HHmmssfff')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,8)
    $backupDir=Join-Path $PSScriptRoot ('backups/upgrade-v06-'+$stamp)
    Test-Gate (-not (Test-Path -LiteralPath $backupDir)) 'Independent new rollback directory'
    New-Item -ItemType Directory -Path $backupDir | Out-Null
    foreach($file in $sceneFiles) {
        Require-Hash $file.target $file.before ('Recheck production before backup: '+$file.relative)
        Require-Hash $file.source $file.after ('Recheck tested candidate before backup: '+$file.relative)
        $file.backup=Join-Path $backupDir (Split-Path $file.target -Leaf)
        [IO.File]::Copy($file.target,$file.backup,$false)
        Require-Hash $file.backup $file.before ('Independent backup verified: '+$file.relative)
    }
    Require-Hash $manifest $sceneManifestHash 'Recheck manifest before install'
    Require-Hash $sceneXML $sceneSceneHash 'Recheck scene XML before install'
    foreach($module in $unchangedModules) {Require-Hash (Join-Path $sceneRoot $module.relative) $module.hash ('Recheck other module before install: '+$module.relative)}
    Require-Hash (Join-Path $sceneRoot 'mods/LightAndDarkness/atmosphere.json') $atmosphereHash 'Recheck atmosphere before install'
    $receipt=[ordered]@{version='0.6.0';status='prepared';preparedAt=(Get-Date).ToString('o');backupDirectory=$backupDir;hostHash=$sceneFiles[0].after;manifestHash=$sceneManifestHash;sceneXMLHash=$sceneSceneHash;files=$sceneFiles;unchangedModules=$unchangedModules;evidence=$sceneReport.evidence;bytecodeAuditSHA256=$auditHash;atmosphereHash=$atmosphereHash;wallEvidence=$WallEvidence;lightEvidence=$LightEvidence;visionRebuildProof=$sceneReport['visionRebuildProof']}
    Write-Receipt $receipt $true
    try {
        foreach($file in $sceneFiles) {Replace-Checked $file.source $file.target $file.before $file.after}
        Require-Hash $manifest $sceneManifestHash 'Manifest untouched after install'
        Require-Hash $sceneXML $sceneSceneHash 'Scene XML untouched after install'
        Require-Hash (Join-Path $sceneRoot 'mods/LightAndDarkness/atmosphere.json') $atmosphereHash 'Atmosphere unchanged after install'
        foreach($module in $unchangedModules) {Require-Hash (Join-Path $sceneRoot $module.relative) $module.hash ('Other module untouched after install: '+$module.relative)}
        $receipt.status='installed';$receipt.installedAt=(Get-Date).ToString('o');Write-Receipt $receipt
    } catch {
        $installError=$_.Exception.Message;$recovery=@()
        foreach($file in $sceneFiles) {
            try {
                $current=File-Hash $file.target
                if($current -eq $file.after) {Replace-Checked $file.backup $file.target $file.after $file.before}
                elseif($current -ne $file.before) {throw 'Target changed outside this transaction; preserved for manual review'}
            } catch {$recovery+=,[ordered]@{file=$file.relative;error=$_.Exception.Message}}
        }
        $receipt.status='install-failed';$receipt.installError=$installError;$receipt.recoveryIssues=$recovery;Write-Receipt $receipt
        throw ('Installation failed: '+$installError+'; recovery issues: '+($recovery | ConvertTo-Json -Compress))
    }
    $sceneReport.passed=$true;$sceneReport.receipt=$sceneReceiptPath;$sceneReport.message='Installed exactly four verified SWFs with independent backups. A fresh native-launch smoke test is still required; existing game processes were not restarted.'
    $sceneReport | ConvertTo-Json -Depth 12
} catch {
    $sceneReport.error=$_.Exception.Message
    $sceneReport | ConvertTo-Json -Depth 12
    throw
}
