"""Strict isolated BEFC UnitPlayer.animate player-only diagnostic audit.

The initial import is inspection-only. New activation slots and the existing
catch must be individually reviewed before exact approval constants are set.
No production source or shared audit is changed; only the target body is kept.
"""
from __future__ import annotations
import argparse
import bisect
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
OUT = B/'generated/player-animate-profile-20261022'
CLASS = 'fe.unit.UnitPlayer'
TARGET = CLASS + '::0:1:animate'
BASE_XML_HASH = 'E5DBF6959F268078B99F0111EB9720F49C2759C1837C82486D9638A17AB92A66'
BASE_CODE_HASH = 'EF8F702E0048CBBE836A5D8A9BE0BB9C0F778EC9D0E0425D65DFFA7A2B7133C7'
BASE_FRAME = dict(init_scope_depth='9', max_scope_depth='14', max_regs='4', max_stack='6')
NATIVE_LOCALS = [('_loc1_',3),('_loc2_',3)]
REVIEWED_IMPORT_XML_SHA = '2B56C6C07305769C910A0EA165D1C9229B796EC1D1597284CECD06FF928B27FE'
REVIEWED_CODE_SHA = '4F6F24030D8F1E2AA6A086552855669CB96914906A249E3214F7235D36A96D03'
REVIEWED_FRAME = dict(init_scope_depth='9',max_scope_depth='14',max_regs='5',max_stack='6')
REVIEWED_EXCEPTION = dict(type='ABCException',start='1669',end='1694',target='1698',name_index='191',type_index='0')
REVIEWED_ACTIVATION_ORDER = [('csPAStats',13),('csPAWholeStart',3),('csPAPartStart',3),('csPAElapsed',3)]+NATIVE_LOCALS
_REVIEWED_SLOT_OFFSETS = [
    ('17 68 96 140 151', '72 83 100 116 127 155 166 176 186 194 202 211 220 229 238 247 256 265 274 283 292 301 310 319 328 337 346 355 364 373 382 391 400 409 418 427 476 502 506 521 545 556 567 593 597 616 627 638 658 1145 1171 1175 1190 1214 1225 1236 1262 1266 1285 1296 1307 1327 1434 1460 1464 1479 1503 1514 1525 1551 1555 1574 1585 1596 1616 1713 1722 1757 1783 1787 1802 1826 1837 1848 1874 1878 1897 1908 1919 1939 2021 2047 2051 2066 2090 2101 2112 2138 2142 2161 2172 2183 2203 2261 2287 2291 2306 2330 2341 2352 2378 2382 2401 2412 2423 2443 5482 5508 5512 5527 5551 5562 5573 5911 5937 5941 5956 5980 5991 6002 6305 6331 6335 6350 6374 6385 6396 6422 6448 6452 6467 6491 6502 6513 7110 7136 7140 7155 7179 7190 7201 7227 7231 7250 7261 7272 7292'),
    ('23 444', '450 585 1254 1543 1866 2130 2370 7219'),
    ('29 452 5590 6019 6413 6530', '494 1163 1452 1775 2039 2279 5500 5929 6323 6440 7128'),
    ('35 498 589 1167 1258 1456 1547 1779 1870 2043 2134 2283 2374 5504 5933 6327 6444 7132 7223', '513 541 560 604 612 631 1182 1210 1229 1273 1281 1300 1471 1499 1518 1562 1570 1589 1794 1822 1841 1885 1893 1912 2058 2086 2105 2149 2157 2176 2298 2326 2345 2389 2397 2416 5519 5547 5566 5948 5976 5995 6342 6370 6389 6459 6487 6506 7147 7175 7194 7238 7246 7265'),
    ('458 3014 4605 5283 5299 5315 5371 5387 5403 5429 5445 5461', '3109 3130 3250 3328 3365 3377 3426 3509 3536 4610 4629 4648 4682 4701 5287 5303 5375 5391 5433 5449 5474'),
    ('464 5615 5688', '5820'),
]
REVIEWED_SLOT_RECEIVERS = {int(offset):(opcode,slot,'activation') for slot,pair in enumerate(_REVIEWED_SLOT_OFFSETS,1) for opcode,offsets in zip((0x6d,0x6c),pair) for offset in offsets.split()}
REVIEWED_SLOT_RECEIVERS[1709]=(0x6d,1,'catch')
REVIEWED_OPERAND_BINDINGS_SHA = '9563EBB71849078C8402C026AE2BAE37DD961571244AC7AFF257285266166317'
REVIEWED_NATIVE_PROJECTION_SHA = '6D04E9CD1E85C955214C28F49CFB6870FACBF0C260040F8EC279E9D178A07CC1'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine = load('player_animate_private_bullet_audit', B/'bullet-segments-audit.py')
recipe = load('player_animate_profile_recipe', B/'player-animate-profile.py')
engine.CLASS, engine.TARGET, engine.OUT = CLASS, TARGET, OUT
core, require = engine.core, engine.require
BASE_XML, BASE_SWF, BASE_HASH = engine.BASE_XML, engine.BASE_SWF, engine.BASE_HASH
_timer_binding = engine.timer_binding


def code_sha(body):
    return hashlib.sha256(bytes.fromhex(body.get('codeBytes'))).hexdigest().upper()


def value_sha(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest().upper()


def resolved_name(abc,index):
    node=abc.cp['constant_multiname'][index];kind=node.get('kind')
    require(kind in ('7','9','27'),'Unreviewed animate target multiname kind')
    def namespace(number):
        item=abc.cp['constant_namespace'][number]
        if number in (864,849):
            require(item.get('kind')=='5' and engine.namespace_name(abc,number)==
                {864:'fe.unit:UnitPlayer',849:'UnitPlayer.as$145'}[number],'Reviewed imported private identity changed')
            return {864:195,849:726}[number],'5',''
        return number,item.get('kind'),engine.namespace_name(abc,number)
    ns=int(node.get('namespace_index','0'));nsset=int(node.get('namespace_set_index','0'))
    return kind,abc.simple(index),namespace(ns) if ns else None,sorted(namespace(n) for n in engine.set_members(abc,nsset)) if nsset else None


def operand_bindings_sha(abc,rows):
    bindings={}
    for row in rows:
        for kind,value in row[3]:
            if kind=='n':bindings['n:'+str(value)]=resolved_name(abc,value)
            elif kind in core.POOLS:bindings[kind+':'+str(value)]=abc.value(core.POOLS[kind],value)
            else:require(kind not in ('m','c'),'Unreviewed method/class operand')
    return value_sha(bindings)


def native_projection_proof(a,b):
    old,_=core.decode(bytes.fromhex(a.bodies[a.named[TARGET]].get('codeBytes')))
    imported,_=core.decode(bytes.fromhex(b.bodies[b.named[TARGET]].get('codeBytes')))
    diagnostics=[(12,454),(474,565),(565,676),(1143,1234),(1234,1345),(1432,1523),(1523,1634),
        (1711,1742),(1755,1846),(1846,1957),(2019,2110),(2110,2221),(2259,2350),(2350,2461),
        (5480,5571),(5571,5592),(5909,6000),(6000,6021),(6303,6394),(6394,6415),
        (6420,6511),(6511,6532),(7108,7199),(7199,7310)]
    by_offset={r[0]:i for i,r in enumerate(old)}
    for offset in (920,2429,2662,4699):
        i=by_offset[offset];require(old[i][2:]==(0x76,[]),'Reviewed Boolean conversion changed')
        if offset in (920,4699):
            require(old[i-1][2]==0xab and old[i+1][2]==0x2a,'Equality already returns Boolean')
        else:require(old[i+1][2]==0x12,'iffalse itself applies Boolean coercion')
    native=[r for r in imported if not any(lo<=r[0]<hi for lo,hi in diagnostics)]
    def canonical(abc,rows,is_new):
        rows=[r for r in rows if r[2] not in core.DEBUG];positions=[r[0] for r in rows];result=[]
        for offset,end,opcode,args in rows:
            fixed=[]
            for kind,value in args:
                if kind=='n':value=resolved_name(abc,value)
                elif kind in core.POOLS:value=abc.value(core.POOLS[kind],value)
                elif kind=='target':value=bisect.bisect_left(positions,value)
                elif is_new and kind=='u' and opcode in (0x6c,0x6d) and value>=5:value-=4
                fixed.append((kind,value))
            result.append((opcode,fixed))
        return result,positions
    before,old_positions=canonical(a,[r for r in old if r[0] not in (920,2429,2662,4699)],False)
    after,new_positions=canonical(b,native,True)
    require(len(before)==2041 and before==after and value_sha(before)==REVIEWED_NATIVE_PROJECTION_SHA,
        'Original animate instructions, operands, slots, calls or branch destinations changed')
    def exception_positions(abc,positions):
        return [(bisect.bisect_left(positions,int(n.get(k))) for k in ('start','end','target'))
            for n in abc.bodies[abc.named[TARGET]].find('exceptions')]
    require([tuple(x) for x in exception_positions(a,old_positions)]==
        [tuple(x) for x in exception_positions(b,new_positions)],'Original catch coverage changed')
    return dict(nativeCanonicalInstructions=2041,nativeProjectionSHA256=REVIEWED_NATIVE_PROJECTION_SHA,
        originalCallAndBranchOrderPreserved=True,originalLocals={'_loc1_':[1,5],'_loc2_':[2,6]},
        removedRedundantBooleanConversions=[920,2429,2662,4699],originalCatchCoveragePreserved=True,
        diagnosticCatchCounterOnly=True,excludedDiagnosticRanges=diagnostics)


def slot_receiver_proof(abc, rows):
    """All 300 receivers traced to activation scope1 or the one native catch."""
    executable=[row for row in rows if row[2] not in core.DEBUG]
    require([(r[2],r[3]) for r in executable[:6]] ==
        [(0xd0,[]),(0x30,[]),(0x57,[]),(0x2a,[]),(0xd5,[]),(0x30,[])], 'Activation local1 identity changed')
    require([(r[0],r[2],r[3]) for r in rows if 1698<=r[0]<=1709] == [
        (1698,0xd0,[]),(1699,0x30,[]),(1700,0xd1,[]),(1701,0x30,[]),
        (1702,0x5a,[('u',0)]),(1704,0x2a,[]),(1705,0xd6,[]),
        (1706,0x2a,[]),(1707,0x30,[]),(1708,0x2b,[]),(1709,0x6d,[('u',1)])],
        'Native catch reconstruction changed')
    require({r[0] for r in rows if r[2]==0xd1}=={1700} and
            {r[0] for r in rows if r[2]==0xd5}=={10}, 'Activation local1 escapes or is overwritten')
    def receiver(position,depth):
        for j in range(position-1,-1,-1):
            row=rows[j];op,args=row[2],row[3]
            if op in core.DEBUG:continue
            if op==0x2a:depth=1 if depth<=2 else depth-1;continue
            if op==0x2b:
                if depth<=2:depth=3-depth
                continue
            if op in (0x65,0x5a,0x20,0x21,0x24,0x25,0x26,0x27,0x2c,0x2d,0x5d,0x60,0x62,0xd0,0xd1,0xd2,0xd3):pops,pushes=0,1
            elif op in (0x73,0x76,0x80,0x82,0x85,0x86,0x91,0xc0,0xc1):pops,pushes=1,1
            elif op in (0x1e,0xa0,0xa1,0xa2,0xa3,0x87):pops,pushes=2,1
            elif op in (0x66,0x6c):pops,pushes=1,1
            elif op==0x46:pops,pushes=int(args[1][1])+1,1
            elif op in (0x63,0xd5,0xd6,0xd7,0x30,0x29):pops,pushes=1,0
            else:raise AssertionError('Unreviewed slot receiver expression at '+str(row[0])+': '+hex(op))
            if op in (0x5d,0x60,0x66,0x46):
                kind=abc.cp['constant_multiname'][args[0][1]].get('kind')
                require(kind in ('7','9','13','14') or op==0x66 and kind=='27', 'Unreviewed late-name stack effect')
                if kind=='27':pops+=1
            if depth<=pushes:return row
            depth=depth-pushes+pops
        raise AssertionError('Slot receiver escaped reviewed expression')
    proven,consumed={},set()
    for i,row in enumerate(rows):
        if row[2] not in (0x6c,0x6d):continue
        source=receiver(i,1 if row[2]==0x6c else 2)
        if source[2:]==(0x65,[('b',1)]):
            owner='activation';consumed.add(source[0])
        elif row[0]==1709 and source[2:]==(0x5a,[('u',0)]):owner='catch'
        else:raise AssertionError('Not the reviewed activation/catch receiver: '+str(row[0]))
        proven[row[0]]=(row[2],row[3][0][1],owner)
    require(proven==REVIEWED_SLOT_RECEIVERS, 'Slot identity/access/receiver differs from explicit reviewed offsets')
    require({r[0] for r in rows if r[2:]==(0x65,[('b',1)])}==consumed, 'Activation scope object escapes slot operations')
    return dict(numericSlotOperations=300,activationScopeIndex=1,activationAccesses=299,
                nativeCatchWriteOffset=1709,nativeCatchReadCount=0,staticSlotAccess=False,
                originalSlotMap={'_loc1_':5,'_loc2_':6},activationObjectEscapes=False)


def activation_proof(abc, index):
    require(abc.names_by_method.get(index) == TARGET, 'Approval only applies to UnitPlayer.animate')
    body = abc.bodies[index]
    rows, addresses = core.decode(bytes.fromhex(body.get('codeBytes')))
    core.Compare.exceptions(body, abc, addresses)
    require(abc.methods[index].get('flags') == '2', 'Original activation flag changed')
    frame = {key: body.get(key) for key in BASE_FRAME}
    traits = list(body.find('traits/traits'))
    actual = [(abc.simple(int(t.get('name_index'))), int(t.get('type_index'))) for t in traits]
    exceptions = list(body.find('exceptions'))
    require(len(exceptions) == 1 and exceptions[0].get('name_index') == '191'
            and exceptions[0].get('type_index') == '0' and abc.simple(191) == 'err', 'Original catch identity changed')
    baseline = code_sha(body) == BASE_CODE_HASH
    receivers = None
    if baseline:
        require(index == 1832 and frame == BASE_FRAME and actual == NATIVE_LOCALS, 'Original UnitPlayer.animate identity/layout changed')
        require(exceptions[0].attrib == dict(type='ABCException', start='621', end='646', target='650',
                    name_index='191', type_index='0'), 'Original catch range changed')
    else:
        require(REVIEWED_CODE_SHA is not None and REVIEWED_FRAME is not None and REVIEWED_EXCEPTION is not None
                and REVIEWED_ACTIVATION_ORDER is not None and REVIEWED_SLOT_RECEIVERS is not None,
                'Player activation/catch requires exact post-compile review')
        require(code_sha(body) == REVIEWED_CODE_SHA and frame == REVIEWED_FRAME, 'Reviewed target body/frame changed')
        require(actual == REVIEWED_ACTIVATION_ORDER and len(actual) == 6
                and set(actual) == set(NATIVE_LOCALS + recipe.LOCAL_SCHEMA), 'Original or diagnostic local identity changed')
        require(exceptions[0].attrib == REVIEWED_EXCEPTION, 'Reviewed native catch range changed')
        require(operand_bindings_sha(abc,rows)==REVIEWED_OPERAND_BINDINGS_SHA,
                'Reviewed operand constant/namespace identity changed')
        receivers = slot_receiver_proof(abc, rows)
    for slot, (trait, (name, kind)) in enumerate(zip(traits, actual), 1):
        qname = int(trait.get('name_index'))
        require({key: value for key, value in trait.attrib.items() if key not in ('bytes','fileOffset')} ==
                dict(type='TraitSlotConst', deleted='false', kindFlags='0', kindType='0', name_index=str(qname),
                     slot_id=str(slot), type_index=str(kind), value_index='0', value_kind='0'), 'Local flags/defaults changed: ' + name)
        require(abc.cp['constant_multiname'][qname].get('kind') == '7'
                and abc.cp['constant_multiname'][qname].get('namespace_index') == '53'
                and abc.cp['constant_namespace'][53].get('kind') == '23'
                and engine.namespace_name(abc, 53) == 'fe.unit', 'Activation local namespace changed')
        require(len(trait) == 1 and trait[0].tag == 'metadata' and not list(trait[0]), 'Unexpected local metadata')
    require(sum(row[2] == 0x57 for row in rows) == sum(row[2] == 0x5a for row in rows) == 1,
            'Activation/catch object count changed')
    require(not any(row[2] in (0x40,0x43,0x6e,0x6f) for row in rows), 'New closure/direct-method/global-slot instruction')
    return dict(originalLocals=NATIVE_LOCALS, diagnosticLocals=0 if baseline else 4, codeSHA256=code_sha(body),
                nativeCatch='one separate err:* catch object', receiverEvidence=receivers)


def body_operands(abc, index):
    activation_proof(abc, index)
    rows, _ = core.decode(bytes.fromhex(abc.bodies[index].get('codeBytes')))
    require(not any(kind in ('m','c') for row in rows for kind, value in row[3]), 'New method/class index operand')
    return {value for row in rows for kind, value in row[3] if kind == 'n'}


def timer_binding(abc, index):
    result = _timer_binding(abc, index)
    require(result['callCount'] == recipe.TIMER_CALLS, 'Player timer count changed')
    return result


def lexical_map(a,b,old_names,new_names):
    require(a.named[TARGET]==1832,'Wrong baseline target identity')
    old_sets,old_direct=engine.namespace_uses(a,old_names)
    require(old_sets=={167} and old_direct=={1,194,195,9,139,16,53},'Original animate bindings changed')
    original=engine.set_members(a,167)
    require(original==[1,421,7,53,9,14,6,10,639,593,558,429,195,194,727,726],'Original UnitPlayer lexical set changed')
    def class_private(abc):
        traits=abc.instances[abc.class_by_name[CLASS]].find('instance_traits/traits')
        fields=[t for t in traits if abc.simple(int(t.get('name_index'))) in ('t_stay','t_walk')]
        require(len(fields)==2,'Private t_stay/t_walk field anchors missing')
        namespaces={int(abc.cp['constant_multiname'][int(t.get('name_index'))].get('namespace_index')) for t in fields}
        require(len(namespaces)==1 and all(engine.private(abc,n) for n in namespaces),'Ambiguous UnitPlayer private identity')
        return next(iter(namespaces))
    require(class_private(a)==195,'Original private fields changed')
    new_private=class_private(b);require(new_private in (195,864),'Unreviewed imported class-private field identity')
    new_sets,direct=engine.namespace_uses(b,new_names);mapping,evidence={},[]
    for nsset in sorted(new_sets):
        members=engine.set_members(b,nsset);private_members={n for n in members if engine.private(b,n)}
        require(len(members)==len(set(members)) and set(members)-private_members==set(original)-{195,726},
            'Imported lexical non-private scope changed')
        require(new_private in private_members and len(private_members)==2,'Ambiguous imported file-private identity')
        for new,old in ((new_private,195),(next(iter(private_members-{new_private})),726)):
            if new!=old:
                require((new,old) in ((864,195),(849,726)) and nsset==181 and nsset>=len(a.cp['constant_namespace_set'])
                    and engine.namespace_name(b,new)=={864:'fe.unit:UnitPlayer',849:'UnitPlayer.as$145'}[new],
                    'Only reviewed appended UnitPlayer references may be rebound')
                require(mapping.get(new,old)==old,'Conflicting private mapping');mapping[new]=old
        require({mapping.get(n,n) for n in members}==set(original),'Mapped scope changed')
        evidence.append(dict(candidateSet=nsset,originalSet=167,privateFieldAnchors=['t_stay','t_walk'],privateMap=dict(mapping)))
    require(all(not engine.private(b,n) or mapping.get(n,n) in (195,726) for n in direct),'Unbound direct private reference')
    for name in new_names:
        node=b.cp['constant_multiname'][name]
        if int(node.get('namespace_index','0')) in mapping or node.get('namespace_set_index')=='181':
            require(name>=len(a.cp['constant_multiname']),'An existing multiname must never be rebound')
    return mapping,evidence


engine.body_operands=body_operands
engine.timer_binding=timer_binding
engine.lexical_map=lexical_map


def rejected_imported_layout(a,b):
    require(a.class_by_name[CLASS]==b.class_by_name[CLASS]==145,'Class identity changed')
    compare=core.Compare(a,b)
    for part in ('instance','static'):
        left=(a.instances if part=='instance' else a.statics)[145]
        right=(b.instances if part=='instance' else b.statics)[145]
        ignored={'iinit_index','cinit_index','bytes','fileOffset'}
        require(engine.support.header(left,ignored)==engine.support.header(right,ignored),'Class header changed')
        container=part+'_traits/traits';x,y=list(left.find(container)),list(right.find(container))
        require(len(x)==len(y)==(228 if part=='instance' else 0),'Original trait count changed')
        require(all(compare.trait(t,a)==compare.trait(u,b) for t,u in zip(x,y)),'Imported layout differs from exact original')
        omitted=part+'_traits'
        require([core.xml_value(n,ignored) for n in left if n.tag!=omitted]==
            [core.xml_value(n,ignored) for n in right if n.tag!=omitted],'Class interfaces/metadata changed')
    return dict(rejected=True,importedClassCopied=False,importedConstructorsCopied=False,
        instanceTraits=228,staticTraits=0,allTypesDefaultsAndMetadataPreserved=True)


def retain_player(base_xml,candidate_xml,output_xml):
    base_xml,candidate_xml,output_xml=map(Path,(base_xml,candidate_xml,output_xml))
    require(engine.sha(base_xml)==BASE_XML_HASH and engine.sha(candidate_xml)==REVIEWED_IMPORT_XML_SHA,
            'Retain requires exact reviewed baseline/import')
    require(output_xml.resolve() not in (base_xml.resolve(),candidate_xml.resolve()), 'Use separate retained XML')
    before,imported=ET.parse(base_xml),ET.parse(candidate_xml)
    old_nodes,new_nodes=before.findall('.//abc'),imported.findall('.//abc')
    require(len(old_nodes)==len(new_nodes) and old_nodes,'ABC count changed')
    copied,scopes,timer,rejected,preserved=[],[],None,None,None
    ignored={'bytes','fileOffset'}
    for number,(old_node,new_node) in enumerate(zip(old_nodes,new_nodes)):
        a,b=core.ABC(old_node),core.ABC(new_node)
        if TARGET not in a.named:
            require(core.xml_value(old_node,ignored)==core.xml_value(new_node,ignored),'Unrelated ABC changed')
            continue
        require(old_node.attrib==new_node.attrib and set(a.named)==set(b.named)
                and set(a.class_by_name)==set(b.class_by_name) and len(a.methods)==len(b.methods), 'ABC identities changed')
        require(set(a.cp)==set(b.cp),'Constant pool kind changed')
        for pool,entries in a.cp.items():
            require(len(b.cp[pool])>=len(entries) and all(core.xml_value(v)==core.xml_value(b.cp[pool][i])
                for i,v in enumerate(entries)), 'Original constant prefix changed: '+pool)
        oi,ni=a.named[TARGET],b.named[TARGET]
        require(a.signature(oi)==b.signature(ni) and a.bodies[oi].get('init_scope_depth')==b.bodies[ni].get('init_scope_depth'),
                'Target signature/captured scope changed')
        old_names,new_names=body_operands(a,oi),body_operands(b,ni)
        timer=timer_binding(b,ni);mapping,evidence=lexical_map(a,b,old_names,new_names)
        projection=native_projection_proof(a,b)
        constants=copy.deepcopy(new_node.find('constants'))
        for entry in list(constants.find('constant_multiname'))[len(a.cp['constant_multiname']):]:
            ns=int(entry.get('namespace_index','0'))
            if ns in mapping:entry.set('namespace_index',str(mapping[ns]))
        for entry in list(constants.find('constant_namespace_set'))[len(a.cp['constant_namespace_set']):]:
            for item in entry.findall('namespaces/item'):
                if int(item.text) in mapping:item.text=str(mapping[int(item.text)])
        normalized=copy.deepcopy(new_node)
        normalized.remove(normalized.find('constants'));normalized.insert(0,copy.deepcopy(constants))
        rejected=rejected_imported_layout(a,core.ABC(normalized))
        preserved=dict(preserved=True,classIndex=145,originalInstanceInitializer=int(a.instances[145].get('iinit_index')),
            originalStaticInitializer=int(a.statics[145].get('cinit_index')),allTables='exact original BEFC',onlyCopiedBody=TARGET)
        original_tables={key:core.xml_value(old_node.find(key),ignored) for key in ('instance_info','class_info','script_info','method_info')}
        replacement=copy.deepcopy(b.bodies[ni]);replacement.set('method_info',str(oi))
        bodies=old_node.find('bodies');index=list(bodies).index(a.bodies[oi]);bodies.remove(a.bodies[oi]);bodies.insert(index,replacement)
        old_constants=old_node.find('constants');index=list(old_node).index(old_constants);old_node.remove(old_constants);old_node.insert(index,constants)
        require(all(core.xml_value(old_node.find(key),ignored)==value for key,value in original_tables.items()),'Original class/script/method table changed')
        require(all(core.xml_value(body,ignored)==core.xml_value(a.bodies[int(body.get('method_info'))],ignored)
            for body in bodies if int(body.get('method_info'))!=oi),'Non-target body changed')
        copied.append(dict(abc=number,method=TARGET,importedIndex=ni,originalIndex=oi))
        scopes.append(dict(abc=number,privateNamespaces=mapping,originalScopeEvidence=evidence))
    require(len(copied)==1 and rejected and preserved,'Expected exactly one target body')
    before.write(output_xml,encoding='utf-8',xml_declaration=True)
    return dict(stagedXML=True,outputXML=str(output_xml),outputXMLSHA256=engine.sha(output_xml),
        baseXMLSHA256=engine.sha(base_xml),importedXMLSHA256=engine.sha(candidate_xml),copiedBodies=copied,
        namespaceMappings=scopes,timerBinding=timer,nativeProjectionProof=projection,
        rejectedImportedLayout=rejected,preservedOriginalLayout=preserved)


def strict_audit(base_xml, candidate_xml, base_swf=BASE_SWF, candidate_swf=OUT/'pfe.swf'):
    paths = list(map(Path, (base_xml, candidate_xml, base_swf, candidate_swf)))
    require(engine.sha(paths[0]) == BASE_XML_HASH and engine.sha(paths[2]) == BASE_HASH, 'Not exact BEFC')
    require(engine.support.swf_envelope(paths[2]) == engine.support.swf_envelope(paths[3]), 'Non-ABC asset changed')
    old_nodes, new_nodes = ET.parse(paths[0]).findall('.//abc'), ET.parse(paths[1]).findall('.//abc')
    require(len(old_nodes) == len(new_nodes) and old_nodes, 'ABC count changed')
    ignored = {'bytes', 'fileOffset'}
    changed, hashes, pools, found, activation, timer, projection = [], {}, [], 0, None, None, None
    counts = dict(unchangedMethodBodies=0, unchangedNamedMethods=0, unchangedClassLayouts=0,
                  unchangedScriptInitializers=0, unchangedUnnamedBodies=0, totalMethods=0)
    for number, (old, new) in enumerate(zip(old_nodes, new_nodes)):
        a, b = core.ABC(old), core.ABC(new)
        require(old.attrib == new.attrib and a.named == b.named and a.class_by_name == b.class_by_name,
                'ABC or named/class identity/index changed')
        require(len(a.methods) == len(b.methods) and set(a.cp) == set(b.cp), 'Method/pool table changed')
        for pool, entries in a.cp.items():
            require(len(b.cp[pool]) >= len(entries)
                    and all(core.xml_value(n) == core.xml_value(b.cp[pool][i]) for i, n in enumerate(entries)),
                    'Original constant prefix changed: ' + pool)
        pools.append({key: len(b.cp[key]) - len(value) for key, value in a.cp.items()})
        for index, (x, y) in enumerate(zip(a.methods, b.methods)):
            require(core.xml_value(x, ignored) == core.xml_value(y, ignored), 'Method metadata changed: ' + str(index))
        require(set(a.bodies) == set(b.bodies), 'Method body set changed')
        script_ids = {int(n.get('init_index')) for n in old.find('script_info')}
        for index, body in a.bodies.items():
            candidate = b.bodies[index]
            name = a.names_by_method.get(index)
            if name == TARGET:
                found += 1
                old_names, new_names = body_operands(a, index), body_operands(b, index)
                activation = activation_proof(b, index)
                projection = native_projection_proof(a,b)
                require(activation['diagnosticLocals'] == 4, 'Missing reviewed diagnostic locals')
                timer = timer_binding(b, index)
                mapping, _ = lexical_map(a, b, old_names, new_names)
                require(not mapping, 'Final body retains a new private binding')
                if core.xml_value(body, ignored) != core.xml_value(candidate, ignored):changed.append(TARGET)
            else:
                require(core.xml_value(body, ignored) == core.xml_value(candidate, ignored),
                        (name or 'method-' + str(index)) + ': non-target body changed')
                hashes['abc-' + str(number) + '/method-' + str(index)] = code_sha(body)
                counts['unchangedMethodBodies'] += 1
                if index not in a.names_by_method and index not in script_ids:counts['unchangedUnnamedBodies'] += 1
        for table in ('instance_info', 'class_info', 'script_info'):
            require(core.xml_value(old.find(table), ignored) == core.xml_value(new.find(table), ignored),
                    table + ': original layout/binding changed')
        covered = {'constants', 'method_info', 'bodies', 'instance_info', 'class_info', 'script_info'}
        require([core.xml_value(n, ignored) for n in old if n.tag not in covered] ==
                [core.xml_value(n, ignored) for n in new if n.tag not in covered], 'Other ABC metadata changed')
        counts['unchangedNamedMethods'] += len(a.named) - int(TARGET in a.named)
        counts['unchangedClassLayouts'] += len(a.class_by_name)
        counts['unchangedScriptInitializers'] += len(list(old.find('script_info')))
        counts['totalMethods'] += len(a.methods)
    require(found == 1 and changed == [TARGET], 'Exactly UnitPlayer.animate must change')
    return dict(passed=True, auditTarget=TARGET, **counts, actualChangedBodies=changed,
                originalConstantPoolPreserved=True, appendedConstants=pools, nonABCSWFEnvelopePreserved=True,
                preservedOriginalLayout=True, constructorsPreserved=True, addedFields=[], addedMethods=[],
                timerBinding=timer, activationProof=activation, nativeProjectionProof=projection, unchangedMethodBodySHA256=hashes,
                baseSHA256=engine.sha(paths[2]), candidateSHA256=engine.sha(paths[3]),
                baseXMLSHA256=engine.sha(paths[0]), candidateXMLSHA256=engine.sha(paths[1]))


engine.audit = strict_audit


def safe_output(path, suffix):
    path = Path(path)
    require(path.suffix == suffix and path.resolve().is_relative_to(OUT.resolve()), 'Output must stay in isolated generated directory')
    return path


def inspect_import(base_xml, candidate_xml):
    """Evidence only. A successful inspection never authorizes retention."""
    a = core.ABC(ET.parse(base_xml).findall('.//abc')[0])
    b = core.ABC(ET.parse(candidate_xml).findall('.//abc')[0])
    oi, ni = a.named[TARGET], b.named[TARGET]
    baseline = activation_proof(a, oi)
    body = b.bodies[ni]
    rows, addresses = core.decode(bytes.fromhex(body.get('codeBytes')))
    core.Compare.exceptions(body, b, addresses)
    slots = [dict(offset=r[0], opcode=r[2], slot=r[3][0][1]) for r in rows if r[2] in (0x6c, 0x6d)]
    compare = core.Compare(a, b)
    differences = []
    for part, x, y, child in [('instance', a.instances[a.class_by_name[CLASS]], b.instances[b.class_by_name[CLASS]], 'instance_traits/traits'),
                              ('static', a.statics[a.class_by_name[CLASS]], b.statics[b.class_by_name[CLASS]], 'static_traits/traits')]:
        old, new = list(x.find(child)), list(y.find(child))
        for i in range(max(len(old), len(new))):
            left, right = old[i] if i < len(old) else None, new[i] if i < len(new) else None
            if left is None or right is None or compare.trait(left, a) != compare.trait(right, b):
                differences.append(dict(part=part, row=i, original=None if left is None else left.attrib,
                                        imported=None if right is None else right.attrib,
                                        originalName=None if left is None else a.simple(int(left.get('name_index'))),
                                        importedName=None if right is None else b.simple(int(right.get('name_index')))))
    return dict(inspected=True, passed=False, runtimeReady=False, reviewRequired=True, target=TARGET,
                originalMethod=oi, importedMethod=ni, originalActivation=baseline,
                importedXMLSHA256=engine.sha(candidate_xml), importedCodeSHA256=code_sha(body),
                frame={k: v for k, v in body.attrib.items() if k != 'codeBytes'},
                activation=[dict(name=b.simple(int(t.get('name_index'))), **t.attrib) for t in body.find('traits/traits')],
                exceptions=[n.attrib for n in body.find('exceptions')], numericSlotOperations=slots,
                importedLayoutDifferences=differences,
                requiredReview=['original _loc1_/_loc2_ slot identity and receiver preservation',
                    '4 new locals never escape; err catch remains a distinct object',
                    'qualified timer binding, lexical private callable identity, no new closures',
                    'imported class/constructor discarded; any layout drift must receive separate exact review'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, default=BASE_XML)
    p.add_argument('--candidate', type=Path, default=OUT/'compiled.xml')
    p.add_argument('--base-swf', type=Path, default=BASE_SWF)
    p.add_argument('--candidate-swf', type=Path, default=OUT/'pfe.swf')
    p.add_argument('--out', type=Path)
    actions = p.add_mutually_exclusive_group()
    actions.add_argument('--inspect-import', action='store_true')
    actions.add_argument('--retain', action='store_true')
    actions.add_argument('--splice-abc', action='store_true')
    args = p.parse_args()
    require(engine.sha(args.base) == BASE_XML_HASH, 'Requires exact BEFC XML')
    if args.inspect_import:
        result = inspect_import(args.base, args.candidate)
    elif args.retain:
        require(REVIEWED_IMPORT_XML_SHA is not None and engine.sha(args.candidate) == REVIEWED_IMPORT_XML_SHA,
                'Compiled import is not yet explicitly reviewed')
        require(args.out is not None, 'Retain requires output')
        result = retain_player(args.base, args.candidate, safe_output(args.out, '.xml'))
        result['preservedOriginalLayoutEvidence']=result['preservedOriginalLayout']
        result.update(preservedOriginalLayout=True, importedClassCopied=False, importedConstructorsCopied=False,
                      strictFinalLayoutCheckUnmodified=True, exactImportedLayoutReviewed=True)
    elif args.splice_abc:
        require(args.out is not None, 'Splice requires output')
        result = engine.splice_abc(args.base, args.candidate, args.base_swf, args.candidate_swf, safe_output(args.out, '.swf'))
    else:
        result = strict_audit(args.base, args.candidate, args.base_swf, args.candidate_swf)
    result.update(diagnosticOnly=True, performanceEligible=False, wrapperSHA256=engine.sha(Path(__file__)))
    if args.retain:
        safe_output(OUT/'retained-audit.json','.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),'utf-8')
    if args.out and not (args.retain or args.splice_abc):
        safe_output(args.out, '.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('unchangedMethodBodySHA256', 'numericSlotOperations', 'activation', 'importedLayoutDifferences')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
