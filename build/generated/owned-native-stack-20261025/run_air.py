"""Owned bounded native stack diagnostic over the exact native SMG combat fixture."""
from pathlib import Path
import argparse
from collections import Counter
import traceback
import importlib.util
import json
import math
import shutil
import sys
import time
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'owned-native-stack-air-1'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

w = load('thread_cpu_fixture_support', HERE.parent / 'window-visibility-native-20261025/run.py')
old, shared, control, dense, base, r, m, support = w.old, w.shared, w.control, w.dense, w.base, w.r, w.m, w.support
patch = load('native_stack_clock_patch', HERE.parent / 'thread-cpu-native-20261025/probe_patch.py')
adapter = load('owned_air_stack_adapter', HERE / 'air-owned/adapter.py')

def runner_inputs():
    files = [Path(w.__file__), Path(old.__file__), Path(shared.__file__), Path(m.__file__),
             HERE/'run_air.py', Path(patch.__file__), HERE/'owned_native_stack.py', HERE/'air-owned/adapter.py', HERE/'AIR-PLAN.md', w.SEED]
    values = dict(old.runner_inputs(), **{str(p): r.sha(p) for p in files})
    values.update({str(r.ROOT/p): v for p,v in w.runtime_inputs().items()})
    return values

def fixture_inputs():
    value = w.seed()
    return {str(p): r.sha(p) for p in [w.SEED, Path(value['probePath']), Path(value['configPath']),
        Path(value['sourceOrigin']), Path(value['probePath']).parent/'probe-build.json',
        Path(patch.__file__), support.OUT/'source-provenance.json']}

def compile_probe(lease, baseline, scripts, compiler, fixture):
    value = w.seed(); staging = HERE/'source-staging'/uuid.uuid4().hex
    patch.prepare(Path(value['frozenSourcePath']), staging/'src')
    after = base.tree_hashes(staging/'src')
    changed = sorted(k for k in set(after)|set(value['frozenSourceSHA256'])
        if after.get(k) != value['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(after) == 85
    origin = staging/'source-origin.json'
    r.save(origin, dict(version=VERSION, seedReceiptSHA256=w.SEED_SHA, seedProbeSHA256=w.PROBE_SHA,
        seedSourceSHA256=value['frozenSourceSHA256'], stagedSHA256=after, changed=changed, fixtureInputs=fixture))
    path = shared.compile_frozen(lease, staging/'src', baseline, scripts, compiler, fixture)
    receipt = r.read(path)
    receipt.update(threadCpuVersion=VERSION, denseFixture=w.FIXTURE,
        sourceOrigin=str(origin), sourceOriginSHA256=r.sha(origin))
    r.save(path, receipt); return path

def verify_probe(path, baseline, scripts, compiler, fixture):
    raw = r.read(path)
    assert path.resolve() == (Path(raw['probePath']).parent/'probe-build.json').resolve()
    value = base.verify_probe(path, baseline, scripts, compiler, fixture)
    assert value['threadCpuVersion'] == VERSION and value['denseFixture'] == w.FIXTURE
    op = Path(value['sourceOrigin']); assert r.sha(op) == value['sourceOriginSHA256']
    origin, seed = r.read(op), w.seed()
    assert origin['seedReceiptSHA256'] == w.SEED_SHA and origin['seedProbeSHA256'] == w.PROBE_SHA
    assert origin['seedSourceSHA256'] == seed['frozenSourceSHA256'] and origin['changed'] == patch.CHANGED
    assert origin['stagedSHA256'] == value['frozenSourceSHA256'] and origin['fixtureInputs'] == fixture
    changed = sorted(k for k in set(value['frozenSourceSHA256'])|set(seed['frozenSourceSHA256'])
        if value['frozenSourceSHA256'].get(k) != seed['frozenSourceSHA256'].get(k))
    assert changed == patch.CHANGED and len(value['frozenSourceSHA256']) == 85
    assert (Path(value['frozenSourcePath'])/patch.CHANGED[0]).read_text('utf-8-sig') == patch.transform(
        (Path(seed['frozenSourcePath'])/patch.CHANGED[0]).read_text('utf-8-sig'))
    return value

def sampled_cpu(original, state):
    def sample(process, elapsed):
        before, mono_before = time.time()*1000, time.monotonic()*1000
        value = original(process, elapsed)
        after, mono_after = time.time()*1000, time.monotonic()*1000
        if process.poll() is not None:
            return dict(value, epochBeforeMs=before, epochAfterMs=after, epochMs=(before+after)/2,
                monotonicBeforeMs=mono_before, monotonicAfterMs=mono_after,
                nativeStack=None, nativeStackSkipped='owned process exited during polling sleep')
        if state.get('sampler') is None:
            try: state['sampler'] = adapter.OwnedAirSampler(process, m.ROOT/'adl64.exe', Path(process.command[-1]))
            except Exception as error:
                state['bindingError']={'error':repr(error),'evidence':getattr(error,'evidence',None)}
                raise
        sampler = state['sampler']
        observation = None
        obs_before = time.time()*1000
        if elapsed >= 35:
            if not state.get('prepared'):
                state['prepareResult'] = sampler.prepare()
                state['prepared'] = True
            observation = sampler.sample(max_threads=2)
        obs_after = time.time()*1000
        return dict(value, epochBeforeMs=before, epochAfterMs=after, epochMs=(before+after)/2,
            monotonicBeforeMs=mono_before, monotonicAfterMs=mono_after,
            nativeStack=observation, nativeStackEpochBeforeMs=obs_before, nativeStackEpochAfterMs=obs_after)
    return sample


def bounds(mark):
    assert all(isinstance(mark[k],(int,float)) and math.isfinite(mark[k])
        for k in ('sampleAtMs','timerBeforeMs','epochMs','timerAfterMs'))
    assert mark['sampleAtMs'] <= mark['timerBeforeMs'] <= mark['timerAfterMs']
    return (mark['epochMs']+mark['sampleAtMs']-mark['timerAfterMs']-2,
            mark['epochMs']+mark['sampleAtMs']-mark['timerBeforeMs']+2)

def process_alignment(result, policy):
    clock = result['environmentClock']; assert clock['version']=='environment-clock-1'
    start, end = clock['start'], clock['end']
    assert start['sampleAtMs']==result['continuousSampling']['startedAtMs']
    assert end['sampleAtMs']==result['samples'][-1]['sampleAtMs'][-1]
    begin, finish = bounds(start)[1], bounds(end)[0]
    mid = lambda x:(x['timerBeforeMs']+x['timerAfterMs'])/2
    drift = end['epochMs']-start['epochMs']-mid(end)+mid(start)
    assert abs(drift)<=20, ('Clock discontinuity',drift)
    samples = policy['ownedProcessCpuSamples']; assert not policy.get('cpuSamplingErrors')
    intervals=[]
    for first,last in zip(samples,samples[1:]):
        elapsed=last['monotonicBeforeMs']-first['monotonicBeforeMs']
        assert elapsed>0 and abs(last['epochBeforeMs']-first['epochBeforeMs']-elapsed)<=20
        cpu=last['kernelMs']+last['userMs']-first['kernelMs']-first['userMs'];assert cpu>=0
        if first['epochBeforeMs']>=begin and last['epochAfterMs']<=finish:
            intervals.append(dict(first=samples.index(first),last=samples.index(last),elapsedMs=elapsed,cpuMs=cpu))
    assert intervals
    elapsed=sum(x['elapsedMs'] for x in intervals);cpu=sum(x['cpuMs'] for x in intervals)
    marks=result['threadClockCases'];assert len(marks)==4
    for i,mark in enumerate(marks):
        assert mark['index']==i and mark['sampleAtMs']==result['samples'][i]['caseBeginAtMs'];bounds(mark)
        assert abs(mark['epochMs']-start['epochMs']-mid(mark)+mid(start))<=20
    return dict(anchors=clock,caseAnchors=marks,clockDriftMs=drift,conservativeStartEpochMs=begin,
        conservativeEndEpochMs=finish,intervals=intervals,coveredElapsedMs=elapsed,processCpuMs=cpu,
        meanCoreEquivalent=cpu/elapsed,exactWholePhaseCpu=False)

def summarize(raw, policy, observation):
    assert raw['ok'] and not raw['error'] and len(raw['assertions'])==26 and all(x['ok'] for x in raw['assertions'])
    cfg,motion=raw['config'],raw['nativeInputMotion']
    assert cfg['drawControl']=='rcnative' and cfg['benchmark']=='scene'
    assert all(cfg[k] for k in ('nativeInputMotion','nativeSprint','stableMotion','playerFire','fixedEnemies','combatRoute','noLighting','noWall'))
    assert not any(cfg[k] for k in ('localEnemies','vision','profile','presentationCheck','worldProfile','locationProfile','guiWeaponProfile','playerStepProfile','playerAnimateProfile'))
    assert raw['denseFixture']['version']==w.FIXTURE and raw['denseFixture']['enemyWeapon']=='smg10'
    assert raw['driver']['forcedPositionCalls']==0 and motion['spawn']['calls']==1
    assert motion['warmup']['ready'] and motion['warmup']['roundTrips']>=1 and motion['warmup']['groundContactRun']>=10
    assert motion['timingStart']['floorContact'] and motion['route']['terrainVerified']
    assert (raw['world']['width'],raw['world']['height'],raw['world']['layoutSeed'])==(240,125,20261019)
    assert raw['viewport']['zoom']==1 and len(raw['samples'])==4
    assert not any(k in raw for k in ('atlasMotion','windowVisibility','cameraHold','rcOfflineInitial'))
    assert raw['observerPolicy']==dict(version='dense-observer-lean-2',settingsDuringTiming=False,
        segmentProgressWrites=False,segmentCensus=False,finalCensus=True,heartbeatIntervalMs=5000,continuousFramesRetained=True)
    old.six_smg10(raw['playerFireWarmup']['encounter'])
    continuous=dense.continuous(raw);rows=[]
    for i,row in enumerate(raw['samples']):
        assert row['name']=='dense-native-'+str(i) and row['empty']==row['misses']==0
        assert row['playerShotFrames']>0 and row['enemyShotFrames']>0
        old.six_smg10(row['encounter'])
        for item in row['combatWindows']:old.six_smg10(item['encounter'])
        assert 'activityCensus' not in row and sum(row['probeTiming']['censusMs'])==sum(row['probeTiming']['progressSaveMs'])==0
        rows.append(dict(index=i,continuous=base.metrics(row['continuousFramesMs']),
            workload=dense.workload(row,motion['route']),playerShots=row['playerShotFrames'],enemyShots=row['enemyShotFrames'],
            bands={k:base.metrics(row[k]) for k in ('nativeBand','wallBand','sceneBand','preBand','tailBand','totalScript','afterProbeBand')},
            warmed=sum(row['warm']),slices=row['slices'],forced=row['forced'],activity=row['activity']))
    census=raw['finalActivityCensus'];assert census['afterFinalSample'] and census['data']
    assert raw['samples'][-1]['sampleAtMs'][-1]<=census['startedAtMs']<=census['endedAtMs']
    qualification=dict(actualSprint=sum(x['workload']['aboveWalkSpeedFrames'] for x in rows)>=30,
        concurrentFixtureBullets=any(v>=3 for row in raw['samples'] for v in row['denseFrames']['fixtureBullets']),
        observedNativePlayerBullets=any(v>0 for row in raw['samples'] for v in row['denseFrames']['playerBullets']))
    qualification['passed']=all(qualification.values())
    alignment=process_alignment(raw,policy)
    thread_summary=native_review(policy, alignment, observation)
    return dict(version=VERSION,complete=True,passed=qualification['passed'] and thread_summary['passed'],qualification=qualification,
        diagnosticOnly=True,performanceEligible=False,performanceAcceptance=False,deployed=False,
        continuous=continuous,rows=rows,clockAlignment=alignment,threads=thread_summary,
        limits=['Native stacks are sparse wall-time snapshots, not CPU percentages; counters separately measure running CPU.',
            'Native module/RVA and unwind paths do not establish function semantics without symbols or further evidence.',
            'A diagnostic run has no optimization arm and cannot qualify any production speedup.'])

def native_review(policy, alignment, observation):
    assert observation['prepared'] and not observation.get('closeError') and not observation.get('bindingError')
    sampler=observation['sampler']
    assert sampler['closed'] and not sampler['fatal'] and not sampler['symbols_used']
    assert not sampler['performance_acceptance'] and not sampler['new_threads_after_prepare_observed']
    assert sampler['source_sha256']==r.sha(HERE/'air-owned/adapter.py').lower()
    ident=sampler['identity']
    assert ident['pid']==policy['pid'] and ident['desktop']==policy['desktop']
    assert Path(ident['image']).resolve()==(m.ROOT/'adl64.exe').resolve()
    fatal=[error for error in sampler['errors'] if error['phase']!='offline-unwind']
    assert not fatal
    samples=sampler['samples'];assert 40<=len(samples)<=sampler['sample_limit']==160
    retained=[sample for call in policy['ownedProcessCpuSamples'] if call.get('nativeStack')
        for sample in call['nativeStack']['samples']]
    assert retained==samples
    assert all(check['same_as_cache'] for check in sampler['inventory_checks'])
    assert sampler['prepare']==observation['prepareResult']
    ft=lambda stamp:(stamp['epoch_filetime_100ns']-116444736000000000)/10000
    first,last=alignment['conservativeStartEpochMs'],alignment['conservativeEndEpochMs']
    inside=[];threads={};modules=Counter();ips=Counter();stack_locations=Counter();previous={}
    for index,sample in enumerate(samples):
        assert sample['index']==index
        assert sample['suspend_calls']==sample['resume_calls']==1
        assert sample['suspend_previous']==0 and sample['resume_previous']==1
        assert not sample.get('capture_error') and sample['module_mapping_qualified'] is not False
        assert 0<sample['stack_bytes']<=65536 and sample['suspension_ms']>=0
        assert ft(sample['ended'])>=ft(sample['started'])
        walk=sample['walk'];assert walk['frames']
        assert int(walk['frames'][0]['address'],16)==int(sample['rip'],16)
        if 'live_reads_during_walk' in walk:assert walk['live_reads_during_walk']==0
        assert not walk.get('symbol_engine_initialized',False)
        key=str(sample['tid'])+':'+str(sample['thread_creation_filetime'])
        entry=threads.setdefault(key,dict(tid=sample['tid'],creationFiletime=sample['thread_creation_filetime'],
            samples=0,measurementSamples=0,ripModules=Counter(),ripOffsets=Counter(),cpuIntervals=[]))
        entry['samples']+=1
        if first<=ft(sample['started'])<=ft(sample['ended'])<=last:
            inside.append(index);entry['measurementSamples']+=1
            loc=walk['frames'][0];name=Path(loc['module']).name if loc['module'] else '[dynamic-or-unknown]'
            label=name+'+'+str(loc['rva'])
            modules[name]+=1;ips[label]+=1;entry['ripModules'][name]+=1;entry['ripOffsets'][label]+=1
            for frame in walk['frames']:
                stack_locations[(Path(frame['module']).name if frame['module'] else '[dynamic-or-unknown]')+'+'+str(frame['rva'])]+=1
        prior=previous.get(key);previous[key]=sample
        delta=sample.get('cpu_since_previous')
        if delta:
            assert delta['kernel_100ns']>=0 and delta['user_100ns']>=0
            if prior and first<=ft(prior['started'])<ft(sample['ended'])<=last:
                ms=(delta['to']['perf_ns']-delta['from']['perf_ns'])/1e6
                assert ms>0
                entry['cpuIntervals'].append(dict(elapsedMs=ms, elapsedUpperMs=(sample['ended']['perf_ns']-prior['started']['perf_ns'])/1e6,
                    conservativeStartEpochMs=ft(prior['started']),conservativeEndEpochMs=ft(sample['ended']),
                    cpuMs=(delta['kernel_100ns']+delta['user_100ns'])/10000))
    assert len(inside)>=10,'Insufficient samples wholly within actual combat measurement'
    def top(counter):return [dict(location=k,count=v) for k,v in counter.most_common(20)]
    for entry in threads.values():
        elapsed=sum(x['elapsedMs'] for x in entry['cpuIntervals']);used=sum(x['cpuMs'] for x in entry['cpuIntervals'])
        entry.update(coveredElapsedMs=elapsed,cpuMs=used,meanCoreEquivalent=used/elapsed if elapsed else None,
            ripModules=dict(entry['ripModules']),ripOffsets=top(entry['ripOffsets']),coreEquivalentUsesLowerElapsedBound=True)
    return dict(passed=True,samples=len(samples),measurementSampleIndices=inside,measurementSamples=len(inside),
        prepare=sampler['prepare'],inventoryChecks=sampler['inventory_checks'],ripModules=dict(modules),
        ripOffsets=top(ips),stackLocations=top(stack_locations),threads=list(threads.values()),
        suspension=base.metrics([s['suspension_ms'] for s in samples]),
        captureAndWalk=base.metrics([s['wall_ms'] for s in samples]),
        totalSuspensionMs=sum(s['suspension_ms'] for s in samples),
        walkMultiFrame=sum(len(s['walk']['frames'])>1 for s in samples),
        unwindErrors=[e for e in sampler['errors'] if e['phase']=='offline-unwind'],
        unknownIP=sum(s['walk']['frames'][0]['module'] is None for s in samples),
        cleanupVerified=sampler['closed'],wholeProcessCpuAttribution=False,
        mappingBetweenChecksOrUntilExitVerified=False,functionNamesVerified=False,
        rawMemoryPersisted=False,symbolsUsed=False)



def main():
    assert __debug__
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--name',required=True)
    parser.add_argument('--registry-wait',type=int,default=600)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--compile-probe',action='store_true');group.add_argument('--probe-build',type=Path)
    args=parser.parse_args();assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder=r.E/args.name;assert not folder.exists(),'Preserve prior evidence'
    options=old.options(args.name);assert options[-2:]==['--draw-control','atlas'];options[-1]='rcnative'
    record=dict(version=VERSION,options=options,diagnosticOnly=True,performanceEligible=False)
    with m.Registration(owner='ContinuousScene / owned native stack / 01a13816',purpose=args.name,
                        run_dir=m.RUNTIME,evidence=folder,resource='game',wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids(),'Other AIR remains untouched'
            memory=control.memory_gate()
            baseline,scripts,compiler,fixture=r.baseline(),runner_inputs(),support.compiler_inputs(),fixture_inputs()
            runtime=w.runtime_inputs();assert len(baseline)==526
            for key,digest in old.PINS.items():assert baseline[key]==digest,key
            rv=r.read(old.RV_RECEIPT);assert rv['result']=='PASS' and rv['new'].upper()==old.RV_CURRENT
            record.update(baseline=baseline,runnerInputs=scripts,compilerInputs=compiler,fixtureInputs=fixture,
                runtimeInputs=runtime,memoryBefore=memory)
            path=compile_probe(lease,baseline,scripts,compiler,fixture) if args.compile_probe else args.probe_build.resolve()
            probe=verify_probe(path,baseline,scripts,compiler,fixture)
            m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert r.sha(m.RUNTIME/key)==digest,key
            assert baseline==r.baseline() and scripts==runner_inputs() and runtime==w.runtime_inputs()
            record.update(probeBuildPath=str(path),probeSHA256=probe['probeSHA256'],memoryBeforeAir=control.memory_gate())
            original_cpu=m.cpu_owned;run_error=None;state={};observation={}
            try:
                m.cpu_owned=sampled_cpu(original_cpu,state)
                m.run_owned(m.parse_args(options),lease)
            except Exception as error:
                run_error=error;record['executionError']=repr(error);record['executionTraceback']=traceback.format_exc()
            finally:
                m.cpu_owned=original_cpu
                if state.get('sampler'):
                    try: state['sampler'].close()
                    except Exception as close_error: observation['closeError']=repr(close_error)
                    observation['sampler']=state['sampler'].summary()
                    observation['moduleBackingFilesAfterRun']={}
                    for entry in observation['sampler']['initial_modules']:
                        try: observation['moduleBackingFilesAfterRun'][entry['path']]={'sha256':r.sha(Path(entry['path']))}
                        except OSError as hash_error: observation['moduleBackingFilesAfterRun'][entry['path']]={'error':repr(hash_error)}
                observation['bindingError']=state.get('bindingError')
                observation['prepared']=state.get('prepared',False)
                observation['prepareResult']=state.get('prepareResult')
                if folder.exists():
                    r.save(folder/'native-stack-observation.json',observation)
                    if run_error:r.save(folder/'execution-error.json',dict(error=repr(run_error)))
                    r.save(folder/'probe-build.json',probe);r.save(folder/'runner-inputs.json',record)
            assert baseline==r.baseline() and scripts==runner_inputs() and fixture==fixture_inputs()
            assert compiler==support.compiler_inputs() and runtime==w.runtime_inputs()
            verify_probe(path,baseline,scripts,compiler,fixture)
            if run_error:raise run_error
            raw,actual=w.read_retained_result(folder)
            for key,digest in baseline.items():
                if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key
            assert actual[base.PROBE_PATH]==probe['probeSHA256']
            policy=r.read(folder/'process-policy.json')
            assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
            assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
            summary=summarize(raw,policy,observation)
            summary.update(probeSHA256=probe['probeSHA256'],resultSHA256=r.sha(folder/'storage/result.json'),
                inputsUnchanged=True,runtimeInputsUnchanged=True,checks=len(raw['assertions']))
            r.save(folder/'summary.json',summary)
            if run_error:raise run_error
            assert summary['passed']
            lease.outcome='passed';lease.note='Native combat and bounded owned stack diagnostic; no production performance acceptance'
            print(json.dumps(dict(name=args.name,passed=summary['passed'],continuous=summary['continuous'],
                processCoreEquivalent=summary['clockAlignment']['meanCoreEquivalent'])),flush=True)
        except BaseException as error:
            lease.outcome='failed';lease.note=repr(error);folder.mkdir(parents=True,exist_ok=True)
            r.save(folder/'runner-failure.json',dict(record,error=repr(error),complete=False,deployed=False));raise

shared.HERE,shared.VERSION=HERE,VERSION
shared.runner_inputs,shared.fixture_inputs=runner_inputs,fixture_inputs
base.OUT=HERE/'probe-builds'
base.runner_inputs,base.candidate_inputs=runner_inputs,fixture_inputs
if __name__=='__main__':main()
