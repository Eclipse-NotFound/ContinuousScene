"""Strict 80CF Camera.calc-only retention; actual import approvals start empty."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
B = OUT.parents[1]
BASE = B/'generated/combat-near-native-20261023/logic-profile-audit/fog-last-blocker-production-minimal'
BASE_SWF, BASE_XML = BASE/'pfe.swf', BASE/'pfe.xml'
HOST_SHA = '80CFD8CF3138EE59CBF6EDA0A1824A9EC960F413BD95E4B90D41DD0322B4FD3D'
BASE_XML_SHA = 'B92260A7A0DFA80EB129C60AEF273645C32BBBA9B3588770BD7083D6984E7E04'
CLASS = 'fe.inter.Camera'
TARGET = CLASS+'::0:1:calc'
REVIEWED_IMPORT_XML_SHA = 'D401E2B181BE9A5FC1E5E2FEAB388D1364DBF1A64A83C8212905FA2421B1933C'
REVIEWED_CODE_SHA = '15315A6FFD285685C9CF7B2087D07483EB56CB35C81F5A982C463FA729F18B17'
REVIEWED_FRAME = dict(init_scope_depth='4',max_scope_depth='5',max_regs='15',max_stack='8')
REVIEWED_PRIVATE_MAP = {}
REVIEWED_BINDINGS_SHA = 'CDE5B03958B711256B80578B9EE5EE5B0724A55DA636372FA6B4585DE5FD1EF4'
REVIEWED_RAW_BINDINGS_SHA = 'D16460D71B9E499ADE70DA3C4545994F13D5A8FAB3F17148A42B450374C900AE'
NORMALIZED_SET = 182
RAW_SET_MEMBERS = [1,421,14,36,867,62,846,866]
ORIGINAL_SET = 164
ORIGINAL_SET_MEMBERS = [1,421,14,36,62,846]
DYNAMIC_NAMES = {'','constructor','isFinite','version','camera','loc','scale','screenX','screenY','lookActive','lastPlayerX','lastPlayerY'}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


engine = load('vertical_camera_band_retainer', B/'bullet-segments-audit.py')
engine.CLASS, engine.TARGET, engine.OUT = CLASS, TARGET, OUT
engine.BASE_SWF, engine.BASE_XML, engine.BASE_HASH = BASE_SWF, BASE_XML, HOST_SHA
core, require, sha = engine.core, engine.require, engine.sha
original_audit = engine.audit
_baseline = None


def baseline():
    global _baseline
    if _baseline is None:
        require(sha(BASE_XML) == BASE_XML_SHA and sha(BASE_SWF) == HOST_SHA, 'Exact current 80CF pair required')
        _baseline = core.ABC(ET.parse(BASE_XML).findall('.//abc')[0])
        require(TARGET in _baseline.named, 'Camera.calc missing from expected ABC')
    return _baseline


def code_sha(body):
    return hashlib.sha256(bytes.fromhex(body.get('codeBytes'))).hexdigest().upper()


def normalized_namespace(abc, index):
    mapping = REVIEWED_PRIVATE_MAP or {}
    if index in mapping:
        require(engine.private(abc,index), 'Only explicitly reviewed private identities may map')
        return mapping[index], '5', ''
    return index,abc.cp['constant_namespace'][index].get('kind'),engine.namespace_name(abc,index)


def bindings(abc, rows):
    result = {}
    for row in rows:
        for kind,value in row[3]:
            if kind == 'n':
                node = abc.cp['constant_multiname'][value]
                require(node.get('kind') in ('7','9','27'), 'New multiname kind requires separate review')
                ns,ss = int(node.get('namespace_index','0')),int(node.get('namespace_set_index','0'))
                result['n:'+str(value)] = (node.get('kind'),abc.simple(value),
                    normalized_namespace(abc,ns) if ns else None,
                    sorted(normalized_namespace(abc,n) for n in engine.set_members(abc,ss)) if ss else None)
            elif kind == 's':result['s:'+str(value)] = abc.string(value)
            elif kind in ('i','q','d'):result[kind+':'+str(value)] = core.xml_value(abc.cp[core.POOLS[kind]][value])
            elif kind == 'p':result['p:'+str(value)] = normalized_namespace(abc,value)
            elif kind in ('m','c'):raise AssertionError('Method/class operand needs explicit relocation')
    return result


def bindings_sha(abc, rows):
    return hashlib.sha256(json.dumps(bindings(abc,rows),sort_keys=True).encode()).hexdigest().upper()


def body_proof(abc,index):
    a = baseline();oi = a.named[TARGET];old = a.bodies[oi]
    require(abc.names_by_method.get(index) == TARGET, 'Wrong body')
    body = abc.bodies[index];rows,addresses = core.decode(bytes.fromhex(body.get('codeBytes')))
    core.Compare.exceptions(body,abc,addresses)
    require(abc.methods[index].get('flags') == a.methods[oi].get('flags'), 'Exact native flags required')
    require(abc.signature(index) == a.signature(oi), 'Exact native return/parameters required')
    require(not list(body.find('traits/traits')) and not list(body.find('exceptions')), 'No activation/catch allowed')
    require(not any(r[2] in (0x40,0x43,0x57,0x5a,0x6c,0x6d,0x6e,0x6f) for r in rows),
        'Closure/direct-method/activation/numeric slots require separate review')
    keys = ('init_scope_depth','max_scope_depth','max_regs','max_stack')
    frame = {k:body.get(k) for k in keys};original = code_sha(body) == code_sha(old)
    if original:
        require(index == oi and frame == {k:old.get(k) for k in keys}, 'Baseline body/frame drift')
    else:
        require(all(x is not None for x in (REVIEWED_CODE_SHA,REVIEWED_FRAME,REVIEWED_PRIVATE_MAP,REVIEWED_BINDINGS_SHA)),
            'Actual import has not been reviewed')
        require(code_sha(body) == REVIEWED_CODE_SHA and frame == REVIEWED_FRAME, 'Reviewed code/frame drift')
        require(frame['init_scope_depth'] == old.get('init_scope_depth')
            and frame['max_scope_depth'] == old.get('max_scope_depth'), 'Native scope changed')
        require(bindings_sha(abc,rows) == REVIEWED_BINDINGS_SHA, 'Operand binding drift')
    return dict(baseline=original,index=index,codeSHA256=code_sha(body),frame=frame,
        signature=abc.signature(index),flags=abc.methods[index].get('flags'))


def body_operands(abc,index):
    body_proof(abc,index)
    rows,_ = core.decode(bytes.fromhex(abc.bodies[index].get('codeBytes')))
    return {v for row in rows for k,v in row[3] if k == 'n'}


def timer_binding(abc,index):
    rows,_ = core.decode(bytes.fromhex(abc.bodies[index].get('codeBytes')))
    require(not any(abc.simple(v) in ('getTimer','getQualifiedClassName')
        for row in rows for k,v in row[3] if k == 'n'), 'No diagnostic function in production body')
    return dict(callCount=0,diagnosticCalls=False,callOffsets=[])


def lexical_map(a,b,old_names,new_names):
    old_sets,old_direct = engine.namespace_uses(a,old_names)
    old_used = old_direct | {n for s in old_sets for n in engine.set_members(a,s)}
    old_private = {n for n in old_used if engine.private(a,n)}
    sets,direct = engine.namespace_uses(b,new_names)
    if NORMALIZED_SET in sets:
        require(len(a.cp['constant_namespace_set']) == NORMALIZED_SET,
            'Reviewed scope must be a newly appended set')
        require(engine.set_members(a,ORIGINAL_SET) == ORIGINAL_SET_MEMBERS
            and engine.set_members(b,NORMALIZED_SET) == ORIGINAL_SET_MEMBERS,
            'Normalized Camera scope differs from exact original class scope')
    used = direct | {n for s in sets for n in engine.set_members(b,s)}
    new_private = {n for n in used if engine.private(b,n)} - old_private
    mapping = {}
    if new_private:
        require(REVIEWED_PRIVATE_MAP is not None and set(REVIEWED_PRIVATE_MAP) == new_private,
            'Imported private identity map absent')
        mapping = dict(REVIEWED_PRIVATE_MAP)
        require(set(mapping.values()) <= old_private and len(set(mapping.values())) == len(mapping),
            'Private map is not an injective original-identity mapping')
        require(all(k >= len(a.cp['constant_namespace']) and engine.private(b,k) for k in mapping),
            'Cannot rebind an existing/nonprivate namespace')
    evidence=[]
    for s in sets:
        members=engine.set_members(b,s)
        if not any(engine.private(b,n) for n in members):continue
        mapped=[mapping.get(n,n) for n in members]
        matches=[o for o in old_sets if mapped == engine.set_members(a,o)]
        require(len(matches)==1,'Exact ordered lexical scope no longer matches original')
        evidence.append(dict(candidateSet=s,originalSet=matches[0],exactPrivateMap=mapping))
    require(all(mapping.get(n,n) in old_private for n in used if engine.private(b,n)),
        'Private use outside original Camera scope')
    return mapping,evidence


def normalize_import(path):
    """Drop exactly two unused fresh Camera private identities, never map them.

    Original Camera has no private traits or private operands anywhere in its
    constructor/methods. Its existing ordered scope is set 164. New plain Object
    reads/writes and isFinite are the only consumers of appended set 182.
    No private member can be selected; keep the exact original public/protected
    scope instead. All other imported nodes and all code bytes stay unchanged.
    """
    require(sha(path) == REVIEWED_IMPORT_XML_SHA,'Only the reviewed raw import may normalize')
    a=baseline();tree=ET.parse(path);nodes=tree.findall('.//abc');b=core.ABC(nodes[0])
    require(len(a.cp['constant_namespace_set']) == NORMALIZED_SET,'Wrong original pool size')
    require(engine.set_members(a,ORIGINAL_SET) == ORIGINAL_SET_MEMBERS,'Wrong existing Camera scope')
    require(engine.set_members(b,NORMALIZED_SET) == RAW_SET_MEMBERS,'Unexpected raw scope')
    require(len(a.cp['constant_namespace']) == 866 and len(b.cp['constant_namespace']) == 868,'Unexpected namespace append')
    require(engine.private(b,866) and engine.namespace_name(b,866)=='Camera.as$29'
        and engine.private(b,867) and engine.namespace_name(b,867)=='fe.inter:Camera','Wrong discarded identities')
    require(not any(engine.private(a,n) and 'Camera' in engine.namespace_name(a,n)
        for n in range(len(a.cp['constant_namespace']))),'Original Camera private namespace exists')
    for abc in (a,b):
        ci=abc.class_by_name[CLASS]
        for obj,container in ((abc.instances[ci],'instance_traits/traits'),(abc.statics[ci],'static_traits/traits')):
            for trait in obj.find(container):
                mn=abc.cp['constant_multiname'][int(trait.get('name_index'))]
                ns=int(mn.get('namespace_index','0'))
                require(not ns or not engine.private(abc,ns),'Camera has a private trait')
    body=b.bodies[b.named[TARGET]];rows,_=core.decode(bytes.fromhex(body.get('codeBytes')))
    require(code_sha(body)==REVIEWED_CODE_SHA and bindings_sha(b,rows)==REVIEWED_RAW_BINDINGS_SHA,'Raw code/binding drift')
    consumers={v for r in rows for k,v in r[3] if k=='n'
        and int(b.cp['constant_multiname'][v].get('namespace_set_index','0'))==NORMALIZED_SET}
    require({b.simple(v) for v in consumers}==DYNAMIC_NAMES,'Unexpected dynamic operand')
    require(all(b.cp['constant_multiname'][v].get('kind') in ('9','27') for v in consumers),'Unexpected dynamic kind')
    # Strong equality proof: reverse the sole node edit and compare the entire XML
    # serialization, including every constant pool, body, class, asset and ABC.
    before=hashlib.sha256(ET.tostring(tree.getroot())).hexdigest().upper()
    target=b.cp['constant_namespace_set'][NORMALIZED_SET].find('namespaces')
    previous=list(target)
    for n in previous:target.remove(n)
    for value in ORIGINAL_SET_MEMBERS:ET.SubElement(target,'item').text=str(value)
    normalized=ET.tostring(tree.getroot(),encoding='utf-8',xml_declaration=True)
    for n in list(target):target.remove(n)
    for n in previous:target.append(n)
    require(hashlib.sha256(ET.tostring(tree.getroot())).hexdigest().upper()==before,'Other imported XML changed')
    out=OUT/'reviewed-normalized-import.xml'
    digest=hashlib.sha256(normalized).hexdigest().upper()
    if out.exists():require(sha(out)==digest,'Preserve prior normalized import')
    else:out.write_bytes(normalized)
    report=dict(rawImportSHA256=sha(path),normalizedImportSHA256=digest,codeSHA256=REVIEWED_CODE_SHA,
        changedNamespaceSet=NORMALIZED_SET,originalEquivalentSet=ORIGINAL_SET,
        before=RAW_SET_MEMBERS,after=ORIGINAL_SET_MEMBERS,removedUnusedPrivateIdentities=[866,867],
        cameraPrivateTraits=0,allOtherXMLNodesUnchanged=True,codeBytesUnchanged=True,
        originalPoolPrefixUnchanged=True,normalizationReversible=True,dynamicNames=sorted(DYNAMIC_NAMES))
    (OUT/'namespace-normalization.json').write_text(json.dumps(report,indent=2),'utf-8')
    return out


def strict_audit(base_xml,candidate_xml,base_swf=BASE_SWF,candidate_swf=OUT/'pfe.swf'):
    require(sha(base_xml)==BASE_XML_SHA and sha(base_swf)==HOST_SHA,'Exact 80CF baseline required')
    result=original_audit(base_xml,candidate_xml,base_swf,candidate_swf)
    require(result['actualChangedBodies']==[TARGET],'Only Camera.calc may change')
    result.update(preservedOriginalLayout=True,constructorsPreserved=True,importedClassCopied=False,
        reviewedBodySHA256=REVIEWED_CODE_SHA,operandBindingsSHA256=REVIEWED_BINDINGS_SHA,
        priorLightingPatchPreserved=True)
    return result


engine.body_operands,engine.timer_binding=body_operands,timer_binding
engine.lexical_map,engine.audit=lexical_map,strict_audit


def inspect(path):
    a=baseline();b=core.ABC(ET.parse(path).findall('.//abc')[0]);index=b.named[TARGET];body=b.bodies[index]
    rows,addresses=core.decode(bytes.fromhex(body.get('codeBytes')));core.Compare.exceptions(body,b,addresses)
    names={v for row in rows for k,v in row[3] if k=='n'}
    sets,direct=engine.namespace_uses(b,names);ns=direct|{n for s in sets for n in engine.set_members(b,s)}
    old_names={v for row in core.decode(bytes.fromhex(a.bodies[a.named[TARGET]].get('codeBytes')))[0] for k,v in row[3] if k=='n'}
    os,od=engine.namespace_uses(a,old_names);ons=od|{n for s in os for n in engine.set_members(a,s)}
    return dict(inspected=True,passed=False,runtimeReady=False,reviewRequired=True,target=TARGET,
        baseline=body_proof(a,a.named[TARGET]),importedXMLSHA256=sha(path),importedCodeSHA256=code_sha(body),
        frame={k:v for k,v in body.attrib.items() if k!='codeBytes'},methodMetadata=b.methods[index].attrib,
        activation=[x.attrib for x in body.find('traits/traits')],exceptions=[x.attrib for x in body.find('exceptions')],
        originalNamespaceSets={str(s):engine.set_members(a,s) for s in os},
        originalNamespaces={str(n):dict(name=engine.namespace_name(a,n),**a.cp['constant_namespace'][n].attrib) for n in ons},
        namespaceSets={str(s):engine.set_members(b,s) for s in sets},
        namespaces={str(n):dict(name=engine.namespace_name(b,n),**b.cp['constant_namespace'][n].attrib) for n in ns},
        timerBinding=timer_binding(b,index),instructions=rows,operandBindings=bindings(b,rows),
        operandBindingsSHA256=bindings_sha(b,rows),requiredReview=[
            'Native Camera.calc statements preserved around scene-only vertical follow selection',
            'Correct this.w.main carrier access, plain Object API/state and exclusive versioned state writes',
            'First/context/zoom/teleport/look-exit reset writes direct target Y only inside normal follow branch',
            'Finite screen-pixel band, full scY height and +100 foot anchor; integer rounding reserve',
            'No changes to look/camRun, X, clamps, quake/RNG, sceneTick, Snd or cel mappings',
            'No Camera fields/methods, activation, exception frames, timers or diagnostics',
            'Original ordered lexical namespace/private identities and exact emitted local register bindings'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',type=Path,default=OUT/'compiled.xml')
    p.add_argument('--candidate-swf',type=Path,default=OUT/'pfe.swf')
    p.add_argument('--out',type=Path,required=True)
    g=p.add_mutually_exclusive_group();g.add_argument('--inspect-import',action='store_true')
    g.add_argument('--retain',action='store_true');g.add_argument('--splice-abc',action='store_true')
    x=p.parse_args();require(x.out.resolve().is_relative_to(OUT.resolve()),'Isolated output only')
    require(sha(BASE_XML)==BASE_XML_SHA and sha(BASE_SWF)==HOST_SHA,'Wrong baseline')
    if x.inspect_import:result=inspect(x.candidate)
    elif x.retain:
        require(REVIEWED_IMPORT_XML_SHA is not None and sha(x.candidate)==REVIEWED_IMPORT_XML_SHA,'Unreviewed import')
        result=engine.retain(BASE_XML,normalize_import(x.candidate),x.out)
    elif x.splice_abc:result=engine.splice_abc(BASE_XML,x.candidate,BASE_SWF,x.candidate_swf,x.out)
    else:result=strict_audit(BASE_XML,x.candidate,BASE_SWF,x.candidate_swf)
    result.update(productionCandidate=True,performanceEligible=False,deployed=False,wrapperSHA256=sha(Path(__file__)))
    if not (x.retain or x.splice_abc):
        require(x.out.suffix=='.json','Report must be JSON');x.out.write_text(json.dumps(result,indent=2),'utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('instructions','operandBindings','unchangedMethodBodySHA256')}))


if __name__=='__main__':main()
