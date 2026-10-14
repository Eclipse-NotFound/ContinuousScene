param([switch]$AllMods,[switch]$Prepared)
$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneRuntime=Join-Path $PSScriptRoot 'runtime'
$sceneLines=@('ContinuousScene|ContinuousSceneMod|1|0|0','ContinuousSceneProbe|ContinuousSceneProbe|1|0|0')
if($AllMods) {
    $sceneExisting=Get-Content -LiteralPath (Join-Path $sceneRoot 'mods/loader-manifest.txt') -Encoding UTF8
    foreach($sceneLine in $sceneExisting) {
        if($sceneLine.StartsWith('#') -or -not $sceneLine.Trim()) {continue}
        $sceneFields=$sceneLine.Split('|')
        if($sceneFields[0] -eq 'ContinuousScene') {continue}
        if($sceneFields[2] -ne '1') {continue}
        $sceneSource=Join-Path $sceneRoot ('mods/'+$sceneFields[0])
        $sceneTarget=Join-Path $sceneRuntime ('mods/'+$sceneFields[0])
        New-Item -ItemType Directory -Force -Path $sceneTarget | Out-Null
        foreach($sceneFolder in @('release','config')) {
            if($Prepared) {continue}
            $scenePath=Join-Path $sceneSource $sceneFolder
            if(Test-Path -LiteralPath $scenePath) {Copy-Item -LiteralPath $scenePath -Destination $sceneTarget -Recurse -Force}
        }
        $sceneLines=@($sceneLine)+$sceneLines
    }
    # Match native ordering exactly, then append the new production module and probe.
    $sceneLines=@($sceneExisting | Where-Object {$_ -match '^[^#]+\|[^|]+\|1\|' -and $_ -notmatch '^ContinuousScene\|'})+@('ContinuousScene|ContinuousSceneMod|1|0|0','ContinuousSceneProbe|ContinuousSceneProbe|1|0|0')
}
[IO.File]::WriteAllLines((Join-Path $sceneRuntime 'mods/loader-manifest.txt'),$sceneLines,[Text.UTF8Encoding]::new($false))
$sceneLines
