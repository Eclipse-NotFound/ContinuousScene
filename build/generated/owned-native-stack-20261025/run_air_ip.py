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
VERSION = 'owned-native-ip-air-1'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

w = load('thread_cpu_fixture_support', HERE.parent / 'window-visibility-native-20261025/run.py')
old, shared, control, dense, base, r, m, support = w.old, w.shared, w.control, w.dense, w.base, w.r, w.m, w.support
patch = load('native_stack_clock_patch', HERE.parent / 'thread-cpu-native-20261025/probe_patch.py')
adapter = load('owned_air_stack_adapter', HERE / 'air-ip-only/adapter.py')

def runner_inputs():
    files = [Path(w.__file__), Path(old.__file__), Path(shared.__file__), Path(m.__file__),
             HERE/'run_air_ip.py', Path(patch.__file__), HERE/'owned_native_stack.py', HERE/'air-owned-v2/adapter.py', HERE/'air-ip-only/adapter.py', HERE/'AIR-IP-PLAN.md', w.SEED]
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
        limits=['CPU-selected IP snapshots are biased wall-time observations, not CPU percentages; counters are separate.',
            'Native module/RVA does not establish function semantics; no stack is captured or unwound.',
            'A diagnostic run has no optimization arm and cannot qualify any production speedup.'])

def native_review(policy, alignment, observation):
    assert observation['prepared'] and not observation.get('closeError') and not observation.get('bindingError')
    q=observation['sampler']
    assert q['version']=='owned-air-ip-only-v1' and q['closed'] and not q['fatal'] and not q['errors']
    assert q['ip_only'] and q['module_memory_bytes_read']==q['stack_bytes_read']==q['unwind_calls']==0
    assert q['private_desktop_launch_verified'] and not q['thread_current_desktop_verified'] and not q['thread_current_desktop_queried']
    assert q['source_sha256']==r.sha(HERE/'air-ip-only/adapter.py').lower()
    assert q['ownership_base_sha256']==r.sha(HERE/'air-owned-v2/adapter.py').lower()
    assert q['native_core_sha256']==r.sha(HERE/'owned_native_stack.py').lower()
    assert not q['new_threads_after_prepare_observed'] and not q['symbols_used'] and not q['performance_acceptance']
    assert q['identity']['pid']==policy['pid'] and q['identity']['desktop']==policy['desktop']
    assert q['prepare']==observation['prepareResult']
    assert all(e['same_as_initial'] for e in q['inventory_checks'])
    calls=[v['nativeStack'] for v in policy['ownedProcessCpuSamples'] if v.get('nativeStack')]
    assert [s for c in calls for s in c['samples']]==q['samples']
    assert [c['cpu'] for c in calls if c.get('cpu')]==q['cpu_batches']
    samples=q['samples'];assert 40<=len(samples)==q['ip_sample_count']<=160
    ft=lambda v:(v['epoch_filetime_100ns']-116444736000000000)/10000
    first,last=alignment['conservativeStartEpochMs'],alignment['conservativeEndEpochMs']
    identities={t['tid']:t['creation_filetime'] for t in q['thread_identities']}
    order=sorted(identities);previous={};cursor=0;captured=0;cpu_stats={};inside=[];modules=Counter();offsets=Counter();counts=Counter()
    for index,batch in enumerate(q['cpu_batches']):
        assert batch['index']==index and not batch['new_threads_observed']
        rows=batch['threads'];assert [v['tid'] for v in rows]==order
        ready=[v for v in rows if v.get('eligible')]
        assert batch['ranking']==[{'tid':v['tid'],'delta_100ns':v['delta_100ns']} for v in sorted(ready,key=lambda v:(-v['delta_100ns'],v['tid']))]
        positive=[v for v in ready if v['delta_100ns']>0]
        expected=[]
        if positive:expected=[min(positive,key=lambda v:(-v['delta_100ns'],v['tid']))['tid']]
        pool=sorted(v['tid'] for v in ready if (v['delta_100ns']>0 or (v.get('previous_delta_100ns') or 0)>0) and v['tid'] not in expected)
        assert batch['recent_two_window_pool_tids']==pool
        maximum=min(2,160-captured)
        if len(expected)<maximum and pool:
            for step in range(len(order)):
                j=(cursor+step)%len(order)
                if order[j] in pool:expected.append(order[j]);cursor=(j+1)%len(order);break
        assert [v['tid'] for v in batch['selected']]==expected
        for row in rows:
            assert row['creation_filetime']==identities[row['tid']] and not row.get('error')
            assert row['selected']==(row['tid'] in expected)
            assert ft(row['read_started'])<=ft(row['read_ended'])
            prior=previous.get(row['tid'])
            if row.get('delta_100ns') is not None:
                assert prior and row['delta_100ns']==row['kernel_100ns']+row['user_100ns']-prior['kernel_100ns']-prior['user_100ns']>=0
                assert row['previous_delta_100ns']==prior.get('delta_100ns')
                if first<=ft(prior['read_started'])<ft(row['read_ended'])<=last:
                    entry=cpu_stats.setdefault(row['tid'],dict(tid=row['tid'],intervals=0,cpuMs=0,elapsedLowerMs=0,elapsedUpperMs=0))
                    entry['intervals']+=1;entry['cpuMs']+=row['delta_100ns']/10000
                    entry['elapsedLowerMs']+=(row['read_started']['perf_ns']-prior['read_ended']['perf_ns'])/1e6
                    entry['elapsedUpperMs']+=(row['read_ended']['perf_ns']-prior['read_started']['perf_ns'])/1e6
            if 'kernel_100ns' in row:previous[row['tid']]=row
        captured+=sum(v['cpu_batch_index']==index for v in samples)
    for index,v in enumerate(samples):
        assert v['index']==index and v['ip_only'] and v['ip_obtained']
        assert v['stack_bytes']==v['unwind_calls']==0
        assert v['suspend_calls']==v['resume_calls']==1 and v['suspend_previous']==0 and v['resume_previous']==1
        assert not v.get('capture_error') and v['module_mapping_qualified'] is not False
        assert v['thread_creation_filetime']==identities[v['tid']]
        batch=q['cpu_batches'][v['cpu_batch_index']]
        row=next(t for t in batch['threads'] if t['tid']==v['tid'])
        assert row['selected'] and v['selection_delta_100ns']==row['delta_100ns']
        assert v['selection_reason']==row['selection_reason']
        assert int(v['module_location']['address'],16)==int(v['rip'],16)
        if first<=ft(v['started'])<=ft(v['ended'])<=last:
            inside.append(index);counts[v['tid']]+=1;loc=v['module_location']
            name=Path(loc['module']).name if loc['module'] else '[dynamic-or-unknown]'
            modules[name]+=1;offsets[name+'+'+str(loc['rva'])]+=1
    assert len(inside)>=10
    for entry in cpu_stats.values():
        entry['coreEquivalentLower']=entry['cpuMs']/entry['elapsedUpperMs'] if entry['elapsedUpperMs'] else None
        entry['coreEquivalentUpper']=entry['cpuMs']/entry['elapsedLowerMs'] if entry['elapsedLowerMs'] else None
        entry['measurementIpSamples']=counts[entry['tid']]
    return dict(passed=True,samples=len(samples),measurementSamples=len(inside),measurementSampleIndices=inside,
        selectionVerified=True,initialThreadCount=len(identities),cpuBatches=len(q['cpu_batches']),
        cpuScan=base.metrics([v['wall_ms'] for v in q['cpu_batches']]),
        prepare=q['prepare'],ripModules=dict(modules),
        ripOffsets=[dict(location=k,count=v) for k,v in offsets.most_common(40)],
        threads=sorted(cpu_stats.values(),key=lambda v:-v['cpuMs']),suspension=base.metrics([v['suspension_ms'] for v in samples]),
        capture=base.metrics([v['wall_ms'] for v in samples]),totalSuspensionMs=sum(v['suspension_ms'] for v in samples),
        rawMemoryPersisted=False,stackBytesRead=0,moduleBytesRead=0,unwindCalls=0,
        biasedSelectionIsCpuAttribution=False,wholeProcessCpuAttribution=False,newThreadsObserved=False,
        mappingBetweenChecksOrUntilExitVerified=False,functionNamesVerified=False)


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
    with m.Registration(owner='ContinuousScene / owned active native IP / 01a13816',purpose=args.name,
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
            lease.outcome='passed';lease.note='Native combat and CPU-selected owned IP diagnostic; no production performance acceptance'
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
