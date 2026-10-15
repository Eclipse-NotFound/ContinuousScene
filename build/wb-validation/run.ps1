param([ValidateSet('Harness','Coverage','Destruction')][string]$Kind,[int]$TimeoutSeconds=780)
$ErrorActionPreference='Stop'
$csRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$gameRoot=(Resolve-Path -LiteralPath (Join-Path $csRoot '../..')).Path
$app=Join-Path $PSScriptRoot 'app'
. (Join-Path $PSScriptRoot '../test-process.ps1')
$entry='WallBlend'+$Kind
$provenance=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'source-provenance.json') -Raw | ConvertFrom-Json
if((Get-FileHash -LiteralPath (Join-Path $app 'pfe.swf')).Hash -ne $provenance.hostSHA256){throw 'Frozen host mismatch'}
if((Get-FileHash -LiteralPath (Join-Path $app 'WallBlendMod.swf')).Hash -ne $provenance.modSHA256){throw 'Frozen candidate mismatch'}
$id='wallblend-test-cs053-'+$Kind.ToLower()+'-'+[DateTime]::Now.ToString('yyyyMMddHHmmss')+'-'+[Guid]::NewGuid().ToString('N').Substring(0,6)
$descriptor=Join-Path $app ('app-'+$id+'.xml')
$resultDir=Join-Path $csRoot ('knowledge/experiments/evidence/'+$id)
New-Item -ItemType Directory -Force -Path $resultDir | Out-Null
($entry+'|'+$entry+'|1|0|0') | Set-Content -LiteralPath (Join-Path $app 'mods/loader-manifest.txt') -Encoding utf8
@"
<?xml version="1.0" encoding="UTF-8"?>
<application xmlns="http://ns.adobe.com/air/application/30.0">
<id>$id</id><versionNumber>1.0</versionNumber><filename>CSWallBlendValidation</filename>
<initialWindow><content>pfe.swf</content><visible>false</visible><width>960</width><height>600</height><resizable>true</resizable><maximizable>true</maximizable><renderMode>direct</renderMode></initialWindow>
<supportedProfiles>extendedDesktop</supportedProfiles>
</application>
"@ | Set-Content -LiteralPath $descriptor -Encoding utf8
$store=Join-Path $env:APPDATA ($id+'/Local Store')
$record=[ordered]@{TestId=$id;Kind=$Kind;StartedUtc=[DateTime]::UtcNow.ToString('o');HostSHA256=$provenance.hostSHA256;ModSHA256=$provenance.modSHA256;HarnessSHA256=(Get-FileHash -LiteralPath (Join-Path $app ('mods/'+$entry+'/release/'+$entry+'.swf'))).Hash;TestCommit=$provenance.publishedTestCommit;DriverAdaptation=$provenance.adaptation;Storage=$store;Results=$resultDir}
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $resultDir 'provenance.json') -Encoding utf8
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'source-provenance.json') -Destination $resultDir
$process=$null
try {
    $arguments=@('-runtime',('"'+(Join-Path $gameRoot 'runtimes/air/win64')+'"'),('"'+$descriptor+'"'))
    $process=Start-Process -FilePath (Join-Path $gameRoot 'adl64.exe') -ArgumentList $arguments -WorkingDirectory $app -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $resultDir 'stdout.log') -RedirectStandardError (Join-Path $resultDir 'stderr.log')
    [ContinuousSceneTest.Power]::Responsive($process) | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $resultDir 'process-policy.json')
    [pscustomobject]@{Event='started';Kind=$Kind;TestId=$id;PID=$process.Id;Utc=[DateTime]::UtcNow.ToString('o');Results=$resultDir} | ConvertTo-Json -Compress
    $deadline=[DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while(-not $process.HasExited -and [DateTime]::UtcNow -lt $deadline){Start-Sleep -Seconds 1;$process.Refresh()}
    if(-not $process.HasExited){throw 'Isolated published harness timed out'}
    if(Test-Path -LiteralPath $store){Get-ChildItem -LiteralPath $store -File | Where-Object {$_.Extension -in @('.png','.json','.log')} | Copy-Item -Destination $resultDir}
    $resultFile=Join-Path $resultDir 'result.json'
    if(-not(Test-Path -LiteralPath $resultFile)){throw ('No harness result; exit '+$process.ExitCode)}
    $result=Get-Content -LiteralPath $resultFile -Raw | ConvertFrom-Json
    [pscustomobject]@{Event='completed';Kind=$Kind;Passed=$result.passed;Checks=$result.assertions.Count;Cases=$result.cases;DurationMs=$result.durationMs;Message=$result.message;Failures=@($result.assertions | Where-Object {-not $_.passed});Results=$resultDir;Utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Depth 9
    if(-not $result.passed -or $process.ExitCode -ne 0){throw 'Published harness reported failure'}
} finally {
    if($process -and -not $process.HasExited){Stop-Process -Id $process.Id}
    if(Test-Path -LiteralPath $store){Get-ChildItem -LiteralPath $store -File | Where-Object {$_.Extension -in @('.png','.json','.log')} | Copy-Item -Destination $resultDir -Force}
    $record.EndedUtc=[DateTime]::UtcNow.ToString('o')
    $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $resultDir 'provenance.json') -Encoding utf8
    if(Test-Path -LiteralPath $descriptor){Remove-Item -LiteralPath $descriptor}
}
