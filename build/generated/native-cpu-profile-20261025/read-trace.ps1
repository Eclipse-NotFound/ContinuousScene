[CmdletBinding(DefaultParameterSetName = 'Trace')]
param(
    [Parameter(Mandatory, ParameterSetName = 'Trace')][string]$TracePath,
    [Parameter(Mandatory, ParameterSetName = 'Trace')][ValidateRange(1, 2147483647)][int]$TargetProcessId,
    [Parameter(Mandatory, ParameterSetName = 'Trace')][double]$StartMs,
    [Parameter(Mandatory, ParameterSetName = 'Trace')][double]$EndMs,
    [Parameter(Mandatory, ParameterSetName = 'Smoke')][switch]$SmokeOnly,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [ValidateRange(1, 100)][int]$Top = 30
)

# Offline consumer of Microsoft's parser. Never creates or controls an ETW session.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$version = 'native-cpu-offline-1'
$libraryDir = 'C:/Users/hello/.nuget/packages/microsoft.diagnostics.tracing.traceevent/3.1.13/lib/netstandard2.0'
if (-not [IO.Path]::IsPathFullyQualified($OutputDirectory)) { throw 'OutputDirectory must be absolute.' }
$output = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $output) { throw 'OutputDirectory must be new; existing evidence is never overwritten.' }
if (-not $SmokeOnly) {
    if (-not [IO.Path]::IsPathFullyQualified($TracePath)) { throw 'TracePath must be absolute.' }
    if (-not [double]::IsFinite($StartMs) -or -not [double]::IsFinite($EndMs) -or $StartMs -lt 0 -or $EndMs -le $StartMs) {
        throw 'Require finite 0 <= StartMs < EndMs, relative to ETL session start.'
    }
    $inputPath = (Get-Item -LiteralPath $TracePath).FullName
    if ([IO.Path]::GetExtension($inputPath) -ine '.etl') { throw 'Input must be a saved .etl file.' }
}
[void][IO.Directory]::CreateDirectory($output)
$log = $null; $inputLock = $null; $conversionWriter = $null
$report = [ordered]@{version=$version; mode=if($SmokeOnly){'api-smoke'}else{'offline-trace'}; passed=$false; actualEtlRead=$false}
function Save-Report {
    $name = if($SmokeOnly){'smoke.json'}else{'summary.json'}
    [IO.File]::WriteAllText((Join-Path $output $name), ($report | ConvertTo-Json -Depth 14), [Text.UTF8Encoding]::new($false))
}
function Add-Count([hashtable]$table, [string]$key) {
    if ($table.ContainsKey($key)) { $table[$key] = [long]$table[$key] + 1 } else { $table[$key] = [long]1 }
}
function Top-Counts([hashtable]$table, [long]$denominator) {
    @($table.GetEnumerator() | Sort-Object @{Expression='Value';Descending=$true},Name | Select-Object -First $Top | ForEach-Object {
        [ordered]@{key=[string]$_.Key; samples=[long]$_.Value; fraction=if($denominator){[double]$_.Value/$denominator}else{0}}
    })
}

try {
    Add-Type -Path (Join-Path $libraryDir 'Microsoft.Diagnostics.FastSerialization.dll')
    Add-Type -Path (Join-Path $libraryDir 'Microsoft.Diagnostics.Tracing.TraceEvent.dll')
    $assembly = [Microsoft.Diagnostics.Tracing.Etlx.TraceLog].Assembly
    if ($assembly.GetName().Version.ToString() -ne '3.1.13.0' -or
        [IO.Path]::GetFullPath($assembly.Location) -ine [IO.Path]::GetFullPath((Join-Path $libraryDir 'Microsoft.Diagnostics.Tracing.TraceEvent.dll'))) {
        throw 'Unexpected TraceEvent assembly identity.'
    }
    $api = @(
        [Microsoft.Diagnostics.Tracing.Etlx.TraceLog].GetMethods() | Where-Object {$_.Name -in @('CreateFromEventTraceLogFile','GetCallStackForEvent') } | ForEach-Object {$_.ToString()}
        [Microsoft.Diagnostics.Tracing.Etlx.TraceLogExtensions].GetMethods() | Where-Object {$_.Name -in @('Process','IntructionPointerCodeAddress')} | ForEach-Object {$_.ToString()}
    )
    foreach ($property in @('Events','EventsLost','Truncated','SampleProfileInterval','SessionEndTimeRelativeMSec','HasCallStacks')) {
        if ($null -eq [Microsoft.Diagnostics.Tracing.Etlx.TraceLog].GetProperty($property)) { throw "Missing TraceLog property $property" }
    }
    $options = [Microsoft.Diagnostics.Tracing.Etlx.TraceLogOptions]::new()
    $options.ShouldResolveSymbols = [Predicate[string]]{param([string]$unused) return $false}
    $options.LocalSymbolsOnly = $true
    $options.AlwaysResolveSymbols = $false
    $options.ContinueOnError = $false
    $report.runtime = [ordered]@{powerShell=$PSVersionTable.PSVersion.ToString(); framework=[Runtime.InteropServices.RuntimeInformation]::FrameworkDescription}
    $report.library = [ordered]@{path=$assembly.Location; assemblyVersion=$assembly.GetName().Version.ToString(); sha256=(Get-FileHash -LiteralPath $assembly.Location -Algorithm SHA256).Hash; api=$api}
    $report.consumerSHA256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash
    $report.policy = [ordered]@{recording=$false; symbolResolution=$false; symbolDownloads=$false; sourceEtlPreserved=$true; cpuSamplingOnly=$true; wallClockAttribution=$false; gpuAttribution=$false; actionScriptNamesAssumed=$false}
    if ($SmokeOnly) {
        # Constructor/property/delegate checks only; no ETL is fabricated or opened.
        if ($options.ShouldResolveSymbols.Invoke('not-a-file.dll')) { throw 'Symbol lookup guard failed.' }
        if (@($api | Where-Object {$_ -like '*CreateFromEventTraceLogFile(System.String, System.String,*'}).Count -ne 1 -or
            @($api | Where-Object {$_ -like '*GetCallStackForEvent(*'}).Count -ne 1 -or
            @($api | Where-Object {$_ -like '*IntructionPointerCodeAddress(Microsoft.Diagnostics.Tracing.Parsers.Kernel.SampledProfileTraceData)'}).Count -ne 1) {
            throw 'Required public overload not found.'
        }
        $report.passed = $true
        $report.scope = 'Assembly load, public API reflection and no-symbol options only; no real ETL conversion validated.'
    } else {
        # Keep a shared-read handle throughout conversion and aggregation: no writer/deleter can alter the original.
        $inputLock = [IO.File]::Open($inputPath, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
        $inputHash = (Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash
        $report.input = [ordered]@{path=$inputPath; bytes=$inputLock.Length; sha256=$inputHash; targetProcessId=$TargetProcessId; startMs=$StartMs; endMsExclusive=$EndMs; timeOrigin='ETL SessionStartTime'}
        $conversionWriter = [IO.StreamWriter]::new((Join-Path $output 'conversion.log'), $false, [Text.UTF8Encoding]::new($false))
        $options.ConversionLog = $conversionWriter
        $etlx = Join-Path $output 'trace.etlx'
        $created = [Microsoft.Diagnostics.Tracing.Etlx.TraceLog]::CreateFromEventTraceLogFile($inputPath, $etlx, $options, $null)
        $conversionWriter.Flush()
        if ([IO.Path]::GetFullPath($created) -ine $etlx) { throw 'Unexpected ETLX destination.' }
        $log = [Microsoft.Diagnostics.Tracing.Etlx.TraceLog]::new($etlx)
        $report.actualEtlRead = $true
        $report.trace = [ordered]@{etlxPath=$etlx; sessionStartUtc=$log.SessionStartTime.ToUniversalTime().ToString('o'); sessionDurationMs=$log.SessionEndTimeRelativeMSec; sampleIntervalMs=$log.SampleProfileInterval.TotalMilliseconds; eventsLost=$log.EventsLost; truncated=$log.Truncated; hasCallStacks=$log.HasCallStacks}
        if ($EndMs -gt $log.SessionEndTimeRelativeMSec) { throw 'Requested end is outside trace duration; do not silently clip.' }
        $threads=@{}; $modules=@{}; $addresses=@{}; $stackCounts=@{}; $stackExamples=@{}; $processes=@{}; $payloadCounts=@{}
        [long]$samples=0; [long]$noModule=0; [long]$noStack=0; [long]$badTimes=0; [long]$nonProcess=0; [long]$dpc=0; [long]$isr=0
        [double]$first=[double]::PositiveInfinity; [double]$last=[double]::NegativeInfinity
        foreach ($event in $log.Events) {
            if ($event.ProcessID -ne $TargetProcessId -or $event -isnot [Microsoft.Diagnostics.Tracing.Parsers.Kernel.SampledProfileTraceData]) { continue }
            $at = $event.TimeStampRelativeMSec
            if (-not [double]::IsFinite($at)) { $badTimes++; continue }
            if ($at -lt $StartMs -or $at -ge $EndMs) { continue }
            $samples++; $first=[Math]::Min($first,$at); $last=[Math]::Max($last,$at)
            Add-Count $threads ([string]$event.ThreadID)
            Add-Count $payloadCounts ([string]$event.Count)
            if($event.NonProcess){$nonProcess++}; if($event.ExecutingDPC){$dpc++}; if($event.ExecutingISR){$isr++}
            $process = [Microsoft.Diagnostics.Tracing.Etlx.TraceLogExtensions]::Process($event)
            if ($null -ne $process) {
                $processes[[string]$process.ProcessIndex] = [ordered]@{processIndex=[int]$process.ProcessIndex; processId=$process.ProcessID; name=$process.Name; startMs=$process.StartTimeRelativeMsec; endMs=$process.EndTimeRelativeMsec}
            }
            $code = [Microsoft.Diagnostics.Tracing.Etlx.TraceLogExtensions]::IntructionPointerCodeAddress($event)
            $module = if($null -ne $code -and -not [string]::IsNullOrEmpty($code.ModuleFilePath)){$code.ModuleFilePath}else{'[unknown-module]'}
            if($module -eq '[unknown-module]'){$noModule++}
            Add-Count $modules $module
            Add-Count $addresses ($module + '!0x' + $event.InstructionPointer.ToString('X'))
            $stack = $log.GetCallStackForEvent($event)
            if($null -eq $stack){$noStack++; continue}
            $stackKey = [string]$stack.CallStackIndex
            Add-Count $stackCounts $stackKey
            # Save only an index; TraceEvent instances are reused by the library's enumerator.
            if(-not $stackExamples.ContainsKey($stackKey)){$stackExamples[$stackKey]=$stack.CallStackIndex}
        }
        $topStacks = @($stackCounts.GetEnumerator() | Sort-Object @{Expression='Value';Descending=$true},Name | Select-Object -First $Top | ForEach-Object {
            $key=[string]$_.Key; $chain=$log.CallStacks[$stackExamples[$key]]; $frames=[Collections.Generic.List[object]]::new()
            while($null -ne $chain -and $frames.Count -lt 64){
                $c=$chain.CodeAddress
                $frames.Add([ordered]@{module=$c.ModuleFilePath; address=('0x'+$c.Address.ToString('X'))})
                $chain=$chain.Caller
            }
            [ordered]@{callStackIndex=$key; samples=[long]$_.Value; fraction=if($samples){[double]$_.Value/$samples}else{0}; frames=$frames.ToArray(); displayDepthLimited=($null -ne $chain)}
        })
        $report.counts = [ordered]@{samples=$samples; firstSampleMs=if($samples){$first}else{$null}; lastSampleMs=if($samples){$last}else{$null}; invalidTargetSampleTimes=$badTimes; noModule=$noModule; noStack=$noStack; noModuleFraction=if($samples){$noModule/[double]$samples}else{$null}; noStackFraction=if($samples){$noStack/[double]$samples}else{$null}; nonProcess=$nonProcess; executingDpc=$dpc; executingIsr=$isr; payloadCountHistogram=(Top-Counts $payloadCounts $samples); countMeaning='One per SampledProfile record; payload Count is retained separately, not silently used as a time weight.'}
        $report.targetProcessInstances = @($processes.Values)
        $report.threads = Top-Counts $threads $samples
        $report.leafModules = Top-Counts $modules $samples
        $report.leafAddresses = Top-Counts $addresses $samples
        $report.topStacks = $topStacks
        $report.distinct = [ordered]@{threads=$threads.Count; leafModules=$modules.Count; leafAddresses=$addresses.Count; stacks=$stackCounts.Count; topLimit=$Top}
        $report.integrity = [ordered]@{sourceHashUnchanged=((Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash -eq $inputHash); eventsLostZero=($log.EventsLost -eq 0); notTruncated=(-not $log.Truncated); targetSamplesPositive=($samples -gt 0); oneProcessInstance=($processes.Count -eq 1); validSampleTimes=($badTimes -eq 0)}
        $report.passed = -not ($report.integrity.Values -contains $false)
        $report.stackAttributionAvailable = $report.passed -and $noStack -lt $samples
        $report.moduleAttributionAvailable = $report.passed -and $noModule -lt $samples
        $report.limitations = @('CPU sample counts approximate on-CPU activity, not frame time or GPU time.', 'No PDB lookup: AIR/JIT may remain module+address or unknown; main/render thread identity is not inferred from thread rank.', 'ETLX conversion indexes the complete trace, but summaries inspect only the requested PID/time range.', 'Top lists are bounded; distinct counts and total sample denominator remain complete. Missing stacks/modules are retained, not dropped.')
    }
} catch {
    $report.passed = $false
    $report.error = $_.Exception.ToString()
} finally {
    $cleanupErrors = [Collections.Generic.List[string]]::new()
    foreach($resource in @($log,$conversionWriter,$inputLock)) {
        if($null -eq $resource){continue}
        try {$resource.Dispose()} catch {$cleanupErrors.Add($_.Exception.ToString())}
    }
    $report.cleanupErrors = $cleanupErrors.ToArray()
    if($cleanupErrors.Count -gt 0){$report.passed=$false}
    Save-Report
}
[pscustomobject]@{passed=$report.passed; mode=$report.mode; reportDirectory=$output; actualEtlRead=$report.actualEtlRead} | ConvertTo-Json -Compress
if(-not $report.passed){exit 1}
