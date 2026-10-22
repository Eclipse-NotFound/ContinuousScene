"""Strict isolated BEFC Unit.step player-only diagnostic audit.

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
OUT = B/'generated/player-step-profile-20261022'
CLASS = 'fe.unit.Unit'
TARGET = CLASS + '::0:1:step'
BASE_XML_HASH = 'E5DBF6959F268078B99F0111EB9720F49C2759C1837C82486D9638A17AB92A66'
BASE_CODE_HASH = '291CC5E503DA7832DD362A569A281ACC8E90DC11F3551357243B2BCF58D7ADA4'
BASE_FRAME = dict(init_scope_depth='7', max_scope_depth='12', max_regs='5', max_stack='8')
NATIVE_LOCALS = [('tf', 0), ('div', 0), ('i', 0)]
REVIEWED_IMPORT_XML_SHA = 'A94C6FAFE796BE95888CF287FEF9572F9A4C86E3550EBAF0183219FB3AF0A21C'
REVIEWED_CODE_SHA = '4810BE5D77AF08B70BE10427BC6E0B1B5C86A329F71A4236C5052EDB5FA6952F'
REVIEWED_FRAME = dict(init_scope_depth='7', max_scope_depth='12', max_regs='7', max_stack='8')
REVIEWED_EXCEPTION = dict(type='ABCException',start='2524',end='2539',target='2543',name_index='191',type_index='0')
REVIEWED_ACTIVATION_ORDER = [('csPSStats',13),('csPSWholeStart',3),('csPSPartStart',3),('csPSElapsed',3)] + NATIVE_LOCALS
REVIEWED_OPERAND_BINDINGS_SHA = '0D41A82717BE77A1F50E857C177BCD367962505EAE226EC9CB791BBA5D8A5F23'
REVIEWED_NATIVE_PROJECTION_SHA = '5B01F4922161374AE664BAD7D545E38D7F635360D0F2B153139D1DEB14564D14'
NATIVE_RANGES = [(0,12),(553,589),(791,930),(1132,1210),(1322,1327),(1439,1444),
    (1556,1738),(1850,1855),(1967,1972),(2084,2102),(2214,2256),(2368,2557),
    (2590,2618),(2730,2782),(2984,2985)]
_REVIEWED_SLOT_OFFSETS = [
    ('17 68 96 140 151', '72 83 100 116 127 155 166 176 186 194 202 211 220 229 238 247 256 265 274 283 292 301 310 319 328 337 346 355 364 373 382 391 400 409 418 427 436 445 454 463 472 481 490 499 508 517 526 591 617 621 636 660 671 682 708 712 731 742 753 773 932 958 962 977 1001 1012 1023 1049 1053 1072 1083 1094 1114 1212 1238 1242 1257 1281 1292 1303 1329 1355 1359 1374 1398 1409 1420 1446 1472 1476 1491 1515 1526 1537 1740 1766 1770 1785 1809 1820 1831 1857 1883 1887 1902 1926 1937 1948 1974 2000 2004 2019 2043 2054 2065 2104 2130 2134 2149 2173 2184 2195 2258 2284 2288 2303 2327 2338 2349 2559 2568 2620 2646 2650 2665 2689 2700 2711 2784 2810 2814 2829 2853 2864 2875 2901 2905 2924 2935 2946 2966'),
    ('23 543', '549 700 1041 2893'),
    ('29 551 1320 1437 1554 1848 1965 2082 2212 2366 2728', '609 950 1230 1347 1464 1758 1875 1992 2122 2276 2638 2802'),
    ('35 613 704 954 1045 1234 1351 1468 1762 1879 1996 2126 2280 2642 2806 2897', '628 656 675 719 727 746 969 997 1016 1060 1068 1087 1249 1277 1296 1366 1394 1413 1483 1511 1530 1777 1805 1824 1894 1922 1941 2011 2039 2058 2141 2169 2188 2295 2323 2342 2657 2685 2704 2821 2849 2868 2912 2920 2939'),
    ('557 856', '868 872 879 904'),
    ('563 1694', '1711 1732'),
    ('569 1701 1724 2507', '1721 1728 2515 2530 2595'),
]
REVIEWED_SLOT_RECEIVERS = {int(offset):(opcode,slot,'activation')
    for slot,pair in enumerate(_REVIEWED_SLOT_OFFSETS,1)
    for opcode,offsets in zip((0x6d,0x6c),pair) for offset in offsets.split()}
REVIEWED_SLOT_RECEIVERS[2555] = (0x6d,1,'catch')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine = load('player_step_private_bullet_audit', B/'bullet-segments-audit.py')
recipe = load('player_step_profile_recipe', B/'player-step-profile.py')
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
    require(kind in ('7','9','27'),'Unreviewed Unit target multiname kind')
    def namespace(number):
        item=abc.cp['constant_namespace'][number]
        if number in (840,841):
            require(item.get('kind')=='5' and engine.namespace_name(abc,number)==
                {840:'fe.unit:Unit',841:'Unit.as$94'}[number],'Reviewed imported private identity changed')
            return {840:140,841:592}[number],'5',''
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
    """Fixed byte offsets plus typed native declarations prove compiler idioms."""
    old,_=core.decode(bytes.fromhex(a.bodies[a.named[TARGET]].get('codeBytes')))
    imported,_=core.decode(bytes.fromhex(b.bodies[b.named[TARGET]].get('codeBytes')))
    fields={'fe.Obj':{'prior':'Number','onCursor':'Number'},'fe.loc.Location':{'active':'Boolean'},
        CLASS:{'disabled':'Boolean','trigDis':'Boolean','isVis':'Boolean','fixed':'Boolean','visDamDY':'int'}}
    for owner,expected in fields.items():
        traits=list(a.instances[a.class_by_name[owner]].find('instance_traits/traits'))
        for name,kind in expected.items():
            matches=[t for t in traits if a.simple(int(t.get('name_index')))==name]
            require(len(matches)==1 and matches[0].get('type')=='TraitSlotConst'
                and matches[0].get('kindType')=='0' and a.simple(int(matches[0].get('type_index')))==kind,
                'Native compiler-idiom field proof changed: '+owner+'.'+name)
    def canonical(abc,rows,is_new):
        native=[]
        for offset,end,opcode,args in rows:
            if opcode in core.DEBUG:continue
            if is_new and not any(lo<=offset<hi for lo,hi in NATIVE_RANGES):continue
            # Typed Boolean read coercions; redundant Boolean/any conversions.
            removed={1560,1571,2752} if is_new else {28,39,279,534,638,645,757,768,769,780,793}
            if offset in removed:continue
            lo,hi=(1717,1726) if is_new else (434,445)
            if lo<=offset<hi:
                if offset==lo:native.append((offset,end,'native-i-increment',[('slot',3)]))
                continue
            # !fixed; iffalse becomes the same fixed; iftrue exit as the original.
            if offset==(1561 if is_new else 275):opcode,args=0x11,[('target',1738 if is_new else 457)]
            # onCursor:Number and visDamDY:int are mutable slots, never setters/const.
            if not is_new and offset in (646,750):opcode=0x61
            if is_new and opcode in (0x6c,0x6d) and offset!=2555:args=[('u',args[0][1]-4)]
            native.append((offset,end,opcode,args))
        positions=[row[0] for row in native];result=[]
        for offset,end,opcode,args in native:
            operands=[]
            for kind,value in args:
                if kind=='n':value=resolved_name(abc,value)
                elif kind in core.POOLS:value=abc.value(core.POOLS[kind],value)
                elif kind=='target':value=bisect.bisect_left(positions,value)
                operands.append((kind,value))
            result.append((opcode,operands))
        return result
    before,after=canonical(a,old,False),canonical(b,imported,True)
    require(len(before)==355 and before==after and value_sha(before)==REVIEWED_NATIVE_PROJECTION_SHA,
        'Original Unit instructions, local identities, operands or branch destinations changed')
    return dict(nativeCanonicalInstructions=355,nativeProjectionSHA256=REVIEWED_NATIVE_PROJECTION_SHA,
        originalCallAndBranchOrderPreserved=True,originalLocals={'tf':[1,5],'div':[2,6],'i':[3,7]},
        compilerIdioms='fixed typed Boolean/Number conversions, same i++, mutable onCursor/visDamDY assignment',
        diagnosticCatchCounterOnly=True,originalCatchCallPreserved=True)


def slot_receiver_proof(abc, rows):
    """All 266 receivers traced to activation scope1 or the one native catch."""
    executable=[row for row in rows if row[2] not in core.DEBUG]
    require([(r[2],r[3]) for r in executable[:6]] ==
        [(0xd0,[]),(0x30,[]),(0x57,[]),(0x2a,[]),(0xd5,[]),(0x30,[])], 'Activation local1 identity changed')
    require([(r[0],r[2],r[3]) for r in rows if 2543<=r[0]<=2555] == [
        (2543,0xd0,[]),(2544,0x30,[]),(2545,0xd1,[]),(2546,0x30,[]),
        (2547,0x5a,[('u',0)]),(2549,0x2a,[]),(2550,0x63,[('u',4)]),
        (2552,0x2a,[]),(2553,0x30,[]),(2554,0x2b,[]),(2555,0x6d,[('u',1)])],
        'Native catch reconstruction changed')
    require({r[0] for r in rows if r[2]==0xd1}=={2545} and
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
        elif row[0]==2555 and source[2:]==(0x5a,[('u',0)]):owner='catch'
        else:raise AssertionError('Not the reviewed activation/catch receiver: '+str(row[0]))
        proven[row[0]]=(row[2],row[3][0][1],owner)
    require(proven==REVIEWED_SLOT_RECEIVERS, 'Slot identity/access/receiver differs from explicit reviewed offsets')
    require({r[0] for r in rows if r[2:]==(0x65,[('b',1)])}==consumed, 'Activation scope object escapes slot operations')
    return dict(numericSlotOperations=266,activationScopeIndex=1,activationAccesses=265,
                nativeCatchWriteOffset=2555,nativeCatchReadCount=0,staticSlotAccess=False,
                originalSlotMap={'tf':5,'div':6,'i':7},activationObjectEscapes=False)


def activation_proof(abc, index):
    require(abc.names_by_method.get(index) == TARGET, 'Approval only applies to Unit.step')
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
        require(index == 1153 and frame == BASE_FRAME and actual == NATIVE_LOCALS, 'Original Unit.step identity/layout changed')
        require(exceptions[0].attrib == dict(type='ABCException', start='686', end='701', target='705',
                    name_index='191', type_index='0'), 'Original catch range changed')
    else:
        require(REVIEWED_CODE_SHA is not None and REVIEWED_FRAME is not None and REVIEWED_EXCEPTION is not None
                and REVIEWED_ACTIVATION_ORDER is not None and REVIEWED_SLOT_RECEIVERS is not None,
                'Player activation/catch requires exact post-compile review')
        require(code_sha(body) == REVIEWED_CODE_SHA and frame == REVIEWED_FRAME, 'Reviewed target body/frame changed')
        require(actual == REVIEWED_ACTIVATION_ORDER and len(actual) == 7
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


def lexical_map(a, b, old_names, new_names):
    require(a.named[TARGET] == 1153, 'Wrong baseline target identity')
    old_sets, old_direct = engine.namespace_uses(a, old_names)
    require(old_sets == {76} and old_direct == {1,9,41,53}, 'Original Unit lexical bindings changed')
    original = engine.set_members(a,76)
    require(original == [140,1,53,7,9,592,421,25,10,6,15,139,593,558,429], 'Original Unit lexical set changed')
    def class_private(abc):
        traits = abc.instances[abc.class_by_name[CLASS]].find('instance_traits/traits')
        anchors = [int(t.get('name_index')) for t in traits if abc.simple(int(t.get('name_index'))) == 'namok_t']
        require(len(anchors) == 1, 'Unique private namok_t field anchor missing')
        namespace = int(abc.cp['constant_multiname'][anchors[0]].get('namespace_index'))
        require(engine.private(abc,namespace), 'namok_t is not class-private')
        return namespace
    require(class_private(a) == 140, 'Original class-private field identity changed')
    candidate_class_private = class_private(b)
    new_sets, direct = engine.namespace_uses(b,new_names)
    mapping,evidence = {},[]
    stable = set(original) - {140,592}
    for nsset in sorted(new_sets):
        members = engine.set_members(b,nsset)
        private_members = {number for number in members if engine.private(b,number)}
        if not private_members:continue
        require(len(members) == len(set(members)) and set(members)-private_members == stable,
                'Imported lexical non-private scope changed')
        require(candidate_class_private in private_members and len(private_members) == 2, 'File-private scope ambiguous')
        for new,old in ((candidate_class_private,140),(next(iter(private_members-{candidate_class_private})),592)):
            if new != old:
                require((new,old) in ((840,140),(841,592)) and candidate_class_private == 840
                        and nsset == 159 and len(a.cp['constant_namespace_set']) == 181
                        and engine.namespace_name(b,new) == {840:'fe.unit:Unit',841:'Unit.as$94'}[new],
                        'Only the reviewed appended Unit references may reuse existing private constants')
                require(mapping.get(new,old) == old,'Conflicting private mapping')
                mapping[new]=old
        require({mapping.get(number,number) for number in members} == set(original),'Mapped private scope changed')
        evidence.append(dict(candidateSet=nsset,originalSet=76,classPrivateFieldAnchor='namok_t',privateMap=dict(mapping)))
    require(all(not engine.private(b,number) or mapping.get(number,number) in (140,592) for number in direct),
            'Unbound direct private reference')
    if mapping:
        for name in new_names:
            node=b.cp['constant_multiname'][name]
            if int(node.get('namespace_index','0')) in mapping or node.get('namespace_set_index')=='159':
                require(name>=len(a.cp['constant_multiname']),'Existing multiname cannot be rebound')
    return mapping,evidence


engine.body_operands=body_operands
engine.timer_binding=timer_binding
engine.lexical_map=lexical_map


def rejected_imported_layout(a,b):
    """Review one fixed imported permutation; never install that class layout."""
    require(a.class_by_name[CLASS]==b.class_by_name[CLASS]==94, 'Class identity changed')
    compare=core.Compare(a,b)
    for part in ('instance','static'):
        left=(a.instances if part=='instance' else a.statics)[94]
        right=(b.instances if part=='instance' else b.statics)[94]
        ignored={'iinit_index','cinit_index','bytes','fileOffset'}
        require(engine.support.header(left,ignored)==engine.support.header(right,ignored), 'Class header changed')
        container=part+'_traits/traits';x,y=list(left.find(container)),list(right.find(container))
        omitted=part+'_traits'
        require([core.xml_value(n,ignored) for n in left if n.tag!=omitted]==
                [core.xml_value(n,ignored) for n in right if n.tag!=omitted], 'Class interfaces/metadata changed')
        if part=='instance':
            require(len(x)==len(y)==324 and all(compare.trait(t,a)==compare.trait(u,b) for t,u in zip(x,y)),
                    'Instance traits changed beyond reviewed private binding')
            continue
        require(len(x)==len(y)==39, 'Static trait count changed')
        names=[a.simple(int(t.get('name_index'))) for t in x]
        require(names[:24]==['D_BUL','D_BLADE','D_PHIS','D_FIRE','D_EXPL','D_LASER','D_PLASMA','D_VENOM',
            'D_EMP','D_SPARK','D_ACID','D_CRIO','D_POISON','D_BLEED','D_FANG','D_BALE','D_NECRO','D_PSY',
            'D_ASTRO','D_PINK','D_INSIDE','D_FRIEND','txtMiss','arrIcos'], 'Original static identities changed')
        permutation=[22,23]+list(range(22))+list(range(24,39))
        require([b.simple(int(t.get('name_index'))) for t in y]==[names[i] for i in permutation],
                'Static permutation differs from the reviewed import')
        for new_index,old_index in enumerate(permutation):
            old,new=x[old_index],y[new_index]
            old_value,new_value=compare.trait(old,a),compare.trait(new,b)
            if old_index<24:
                require(old.get('type')==new.get('type')=='TraitSlotConst'
                        and old.get('slot_id')==str(old_index+1) and new.get('slot_id')==str(new_index+1),
                        'Reviewed original/imported static slot position changed')
                old_value=(tuple(pair for pair in old_value[0] if pair[0]!='slot_id'),old_value[1])
                new_value=(tuple(pair for pair in new_value[0] if pair[0]!='slot_id'),new_value[1])
            require(old_value==new_value, 'Static trait type/default/metadata changed: '+names[old_index])
    target_names=body_operands(b,b.named[TARGET])
    require(not set(names[:24]).intersection(b.simple(n) for n in target_names), 'Target refers to discarded static drift')
    return dict(rejected=True,importedClassCopied=False,importedConstructorsCopied=False,
        instanceTraits=324,staticTraits=39,staticFields=24,staticMethods=15,
        exactImportedFieldPermutation=[22,23]+list(range(22)),staticSlotRenumberingInstalled=False,
        allTypesDefaultsAndMetadataPreserved=True,targetUsesDiscardedStaticFields=False,
        targetNumericSlots='activation and original catch only')


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
            if mapping and entry.get('namespace_set_index')=='159':entry.set('namespace_set_index','76')
        for entry in list(constants.find('constant_namespace_set'))[len(a.cp['constant_namespace_set']):]:
            for item in entry.findall('namespaces/item'):
                if int(item.text) in mapping:item.text=str(mapping[int(item.text)])
        normalized=copy.deepcopy(new_node)
        normalized.remove(normalized.find('constants'));normalized.insert(0,copy.deepcopy(constants))
        rejected=rejected_imported_layout(a,core.ABC(normalized))
        preserved=dict(preserved=True,classIndex=94,originalInstanceInitializer=int(a.instances[94].get('iinit_index')),
            originalStaticInitializer=int(a.statics[94].get('cinit_index')),allTables='exact original BEFC',onlyCopiedBody=TARGET)
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
    require(found == 1 and changed == [TARGET], 'Exactly Unit.step must change')
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
                requiredReview=['original tf/div/i slot identity and receiver preservation',
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
                      strictFinalLayoutCheckUnmodified=True, discardedImportStaticPermutationReviewed=True)
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
