$ErrorActionPreference='Stop'
$expected=[ordered]@{
    'pfe.swf'='A61EA4A30F0E4978173F2B92B5F33A02960098D706B810FC6196105278EFA73F'
    'ContinuousSceneMod.swf'='B5E8110E11FE2DF8A748B223DFFA6E0EC42E4F61A931D4D4E065CC199EFA2F1B'
    'TDFCMod.swf'='03243196C99D6C4F1A2BE081598DBAE9B5D89A414BCD48E1F860232BCFDDE1E5'
    'WallBlendMod.swf'='0BD209A1763D1C08BCEEAA6415DC768AB3D18AD99BAD377B4D8C188EBD48DE5A'
}
$final=Join-Path $PSScriptRoot 'candidate-v08-final'
$wall=Join-Path $PSScriptRoot 'candidate-v08-wall-trim/WallBlendMod.swf'
if((Get-FileHash -LiteralPath $wall).Hash -ne $expected['WallBlendMod.swf']){throw 'Wall candidate changed'}
Copy-Item -LiteralPath $wall -Destination (Join-Path $final 'WallBlendMod.swf') -Force
foreach($name in $expected.Keys){
    if((Get-FileHash -LiteralPath (Join-Path $final $name)).Hash -ne $expected[$name]){throw ('Frozen bytes changed: '+$name)}
}
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' (Join-Path $PSScriptRoot 'wallblend_trim.py')
if($LASTEXITCODE -ne 0){throw 'Wall source provenance failed'}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'generated/wb-trim-source/source-manifest.json') -Destination (Join-Path $final 'wall-source-manifest.json') -Force
$expected|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $final 'frozen-hashes.json') -Encoding utf8
$expected
