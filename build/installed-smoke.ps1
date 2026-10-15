param([string]$Receipt='install-receipt.json',[string]$SceneVersion='0.2.0',[string]$VisionVersion='v0.30.3-scene',[string]$WallVersion='0.4.1',[string]$SceneRegistration='registered 192x60 native land')
$ErrorActionPreference='Stop'
$sceneRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../..')).Path
$sceneReceipt=Get-Content -LiteralPath (Join-Path $PSScriptRoot $Receipt) -Raw | ConvertFrom-Json
if((Get-FileHash -LiteralPath (Join-Path $sceneRoot 'pfe.swf')).Hash -ne $sceneReceipt.hostHash) {throw 'Installed host differs from receipt'}
$sceneId='pfe-modsettings-continuous-installed-'+(Get-Date -Format 'yyyyMMddHHmmss')
$sceneDescriptor=Join-Path $PSScriptRoot 'generated/installed-smoke.xml'
@"
<?xml version="1.0" encoding="UTF-8"?>
<application xmlns="http://ns.adobe.com/air/application/30.0"><id>$sceneId</id><versionNumber>1.0</versionNumber><filename>ContinuousSceneSmoke</filename>
<initialWindow><content>pfe.swf</content><visible>false</visible><width>1280</width><height>800</height><renderMode>direct</renderMode></initialWindow><supportedProfiles>extendedDesktop</supportedProfiles></application>
"@ | Set-Content -LiteralPath $sceneDescriptor -Encoding UTF8
$sceneEvidence=Join-Path $PSScriptRoot ('../knowledge/experiments/evidence/'+$sceneId)
New-Item -ItemType Directory -Force -Path $sceneEvidence | Out-Null
$sceneProcess=$null
try {
    # Real native initial content and application directory; no nested Loader.
    $sceneProcess=Start-Process -FilePath (Join-Path $sceneRoot 'adl64.exe') -ArgumentList @('-runtime',('"'+(Join-Path $sceneRoot 'runtimes/air/win64')+'"'),('"'+$sceneDescriptor+'"'),('"'+$sceneRoot+'"')) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $sceneEvidence 'stdout.log') -RedirectStandardError (Join-Path $sceneEvidence 'stderr.log')
    Write-Output ('Native installed-files smoke PID '+$sceneProcess.Id)
    $sceneProcess.WaitForExit(42000) | Out-Null
    if($sceneProcess.HasExited) {throw 'Native game exited before the startup check'}
    $sceneStore=Join-Path $env:APPDATA ($sceneId+'/Local Store')
    Get-ChildItem -LiteralPath $sceneStore -File | Where-Object {$_.Extension -in '.json','.log'} | Copy-Item -Destination $sceneEvidence
    $sceneSol=@(Get-ChildItem -LiteralPath $sceneStore -Filter 'ModLoader.sol' -Recurse -File)
    if($sceneSol.Count -ne 1) {throw 'Missing fresh native loader status'}
    $sceneStatus=[Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($sceneSol[0].FullName))
    $sceneChecks=@()
    foreach($sceneLine in Get-Content -LiteralPath (Join-Path $sceneRoot 'mods/loader-manifest.txt')) {
        $sceneFields=$sceneLine.Split('|')
        if($sceneFields.Length -eq 5 -and $sceneFields[2] -eq '1') {
            $sceneChecks += [pscustomobject]@{name=('native-loader-'+$sceneFields[1]);passed=$sceneStatus.Contains('ok_'+$sceneFields[1]) -and -not $sceneStatus.Contains('err_'+$sceneFields[1])}
        }
    }
    $sceneLog=Get-Content -LiteralPath (Join-Path $sceneStore 'ContinuousScene.log') -Raw
    $sceneRvLog=Get-Content -LiteralPath (Join-Path $sceneStore 'RVision.log') -Raw
    $sceneWallLog=Get-Content -LiteralPath (Join-Path $sceneStore 'WallBlend.log') -Raw
    $sceneChecks += [pscustomobject]@{name='scene-registered-native-host';passed=$sceneLog.Contains('v'+$SceneVersion+' loaded') -and $sceneLog.Contains($SceneRegistration) -and $sceneLog.Contains('heartbeat') -and -not $sceneLog.Contains('ERROR')}
    $sceneChecks += [pscustomobject]@{name='vision-version';passed=$sceneRvLog.Contains('init ok '+$VisionVersion) -and $sceneRvLog.Contains('tick 181')}
    $sceneChecks += [pscustomobject]@{name='wall-version';passed=$sceneWallLog.Contains('v'+$WallVersion+' loaded') -and -not $sceneWallLog.Contains('"failed":true')}
    $sceneOutput=[string](Get-Content -LiteralPath (Join-Path $sceneEvidence 'stdout.log') -Raw)
    $sceneChecks += [pscustomobject]@{name='no-uncaught-error';passed=$sceneOutput -notmatch '(TypeError|ReferenceError|VerifyError): Error #'}
    $sceneResult=[pscustomobject]@{passed=@($sceneChecks | Where-Object {-not $_.passed}).Count -eq 0;appId=$sceneId;checks=$sceneChecks;scope='Native startup using installed bytes; button/travel coverage belongs to the referenced same-hash isolated regression';runtimeRoot=$sceneRoot}
    $sceneResult | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $sceneEvidence 'InstalledSmoke.json')
    $sceneResult | ConvertTo-Json -Depth 5
    Get-FileHash -LiteralPath (Join-Path $sceneRoot 'pfe.swf'),(Join-Path $sceneRoot 'mods/loader-manifest.txt'),(Join-Path $sceneRoot 'mods/ContinuousScene/release/ContinuousSceneMod.swf'),(Join-Path $sceneRoot 'mods/RealisticVision/release/RealisticVisionMod.swf'),(Join-Path $sceneRoot 'mods/WallBlend/release/WallBlendMod.swf') | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $sceneEvidence 'installed-hashes.json')
    if(-not $sceneResult.passed) {throw 'Native installed smoke failed'}
    Write-Output $sceneEvidence
} finally {
    if($sceneProcess -and -not $sceneProcess.HasExited) {$sceneProcess.Kill();$sceneProcess.WaitForExit()}
}
