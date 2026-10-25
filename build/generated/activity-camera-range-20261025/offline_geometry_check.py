"""Read-only, deterministic Camera geometry checks; no game or compiler imports.

The native model follows Camera's assignments and branches.  The candidate
adapter must be reviewed against the frozen AS source separately.  Sampling
finite cases is not a proof about writes by objects between activity and calc.
This program writes only its JSON report to stdout.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import hashlib
import json
import math
import random
import time

HERE = Path(__file__).resolve().parent
CAMERA = HERE.parent / 'vertical-camera-band-20261023/source/fe/inter/Camera.as'
CAMERA_SHA = '392218D33CAD0A9ACB1C5237281B407A513E6360DD8E8454A8260C24598A4C70'
VERSION = 'activity-camera-range-offline-1'
SCALE_CASES = (0.5, 0.8, 1.0, 1.25)
CANDIDATE = HERE / 'source-candidate/SceneActivityCameraRange.as'
CANDIDATE_SHA = '898D0C6C260A49FC3DD5FF8B374933845A168948F3FACAA90A669FB903A99227'
INTERMEDIATE_CANDIDATE_SHA = '7B37947202A01F690485163613E6BA4CBAD7907161CD70984113D748154E7DC1'
PRIOR_CANDIDATE_SHA = 'C05A56EC4A8D75609ED694F47CD8A0DF59EDA10FE71EDEEE97DCE92ACDD6C63A'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def as3_int(value: float) -> int:
    """ECMAScript ToInt32, including wrap; not Python round/floor."""
    if not math.isfinite(value) or value == 0:
        return 0
    unsigned = math.trunc(value) % 4294967296
    return unsigned - 4294967296 if unsigned >= 2147483648 else unsigned


@dataclass(frozen=True)
class Rect:
    left: float
    top: float
    right: float
    bottom: float

    def contains(self, other: 'Rect', tolerance: float = 0.0) -> bool:
        # Same strict containment as the candidate; no numerical forgiveness.
        return (self.left <= other.left + tolerance and self.top <= other.top + tolerance
                and self.right + tolerance >= other.right and self.bottom + tolerance >= other.bottom)

    def union(self, other: 'Rect') -> 'Rect':
        return Rect(min(self.left, other.left), min(self.top, other.top),
                    max(self.right, other.right), max(self.bottom, other.bottom))

    def padded(self, x: float, y: float | None = None) -> 'Rect':
        if y is None:
            y = x
        return Rect(self.left - x, self.top - y, self.right + x, self.bottom + y)

    def data(self) -> dict:
        return dict(left=self.left, top=self.top, right=self.right, bottom=self.bottom)


@dataclass(frozen=True)
class Pose:
    scale: float = 1.0
    width: int = 2032
    height: int = 1084
    maxvx: int = 7568
    maxvy: int = 3916
    gx: float = 4833.807499515905
    gy: float = 4120.0
    old_y: int = 4119
    vx: int = -3817
    vy: int = -3477
    qx: float = 0.0
    qy: float = 0.0
    body_height: float = 70.0
    # Actual displayed translation can differ from the just-written quake.
    actual_tx: float = -3817.0
    actual_ty: float = -3477.0
    moved: bool = True
    vertical_mode: str = 'band'


def viewport(tx: float, ty: float, p: Pose) -> Rect:
    return Rect(-tx / p.scale, -ty / p.scale,
                (p.width - tx) / p.scale, (p.height - ty) / p.scale)


def native_quake(q: float, first_random: float, second_random: float) -> float:
    # Camera.as 344..363; both axes use separate random draws.
    if q != 0:
        if first_random > 0.2:
            q *= -(second_random * 0.3 + 0.5)
        if -1 < q < 1:
            q = 0.0
    return q


def native_calc(p: Pose, rx: tuple[float, float], ry: tuple[float, float]) -> dict:
    """Execute the eligible ordinary-follow branches, independently of bounds.

    vertical_mode chooses a branch already selected by native carrier state.
    No claim is made that every synthetic mode/state is a reachable gameplay
    history.  Including additional branches is conservative for containment.
    """
    vx, vy = p.vx, p.vy
    x = as3_int(p.gx * p.scale)
    y = p.old_y
    branch = 'not-moved'
    if p.moved:
        if p.vertical_mode == 'reset':
            y = as3_int(p.gy * p.scale)
            branch = 'reset'
        elif p.vertical_mode == 'band':
            foot = p.height / 2 + 100
            margin = 2 + abs(p.qy)
            band = max(0, min(160, p.height * 0.18,
                              foot - p.body_height * p.scale - margin,
                              p.height - margin - foot))
            y = as3_int(max(p.gy * p.scale - band,
                           min(p.old_y, p.gy * p.scale + band)))
            branch = 'band'
        elif p.vertical_mode == 'legacy':
            difference = p.old_y - p.gy * p.scale
            if 5 < difference < 50:
                y = as3_int(p.old_y - difference / 4)
                branch = 'legacy-quarter'
            else:
                y = as3_int(p.gy * p.scale)
                branch = 'legacy-direct'
        else:
            raise AssertionError('unknown native branch')
        if p.maxvx < 0:
            vx = as3_int(-p.maxvx / 2)
        else:
            vx = as3_int(-x + p.width / 2)
            if vx > 0:
                vx = 0
            if vx < -p.maxvx:
                vx = -p.maxvx
        if p.maxvy < 0:
            vy = as3_int(-p.maxvy / 2)
        else:
            vy = as3_int(-y + p.height / 2 + 100)
            if vy > 0:
                vy = 0
            if vy < -p.maxvy:
                vy = -p.maxvy
    qx, qy = native_quake(p.qx, *rx), native_quake(p.qy, *ry)
    return dict(vx=vx, vy=vy, qx=qx, qy=qy, branch=branch,
                rectangle=viewport(vx + qx, vy + qy, p))


def directed_poses():
    """Independent inputs, including odd screens and both int/clamp edges."""
    screens = ((640, 480), (1280, 800), (2032, 1084), (2033, 1085), (101, 201))
    differences = (-10000, -160.01, -5.01, 0, 4.999, 5, 5.001, 49.999, 50, 50.001, 160.01, 10000)
    for scale in SCALE_CASES:
        for width, height in screens:
            for maximum in ((-101, -51), (0, 0), (7568, 3916)):
                for difference in differences:
                    for mode in ('reset', 'band', 'legacy'):
                        gy = 4120.375 / scale
                        yield Pose(scale=scale, width=width, height=height,
                                   maxvx=maximum[0], maxvy=maximum[1],
                                   gx=(-0.625 if difference < 0 else 9600.625), gy=gy,
                                   old_y=as3_int(gy * scale + difference),
                                   qx=0.999, qy=-1.001, vertical_mode=mode)
        # Exact native legacy boundaries, with integer old_y and fractional gy.
        for difference in (4.999, 5.0, 5.001, 49.999, 50.0, 50.001):
            yield Pose(scale=scale, gy=(4120 - difference) / scale,
                       old_y=4120, vertical_mode='legacy', qx=-17.5, qy=7.25)
        # No camera translation, but quake still executes.
        yield Pose(scale=scale, moved=False, qx=20.0, qy=-20.0)
    rng = random.Random(20261025)
    for _ in range(2000):
        scale = rng.choice(SCALE_CASES)
        yield Pose(scale=scale, width=rng.choice((640, 2032, 2033)),
                   height=rng.choice((480, 1084, 1085)),
                   maxvx=rng.choice((-101, -1, 0, 1, 7568)),
                   maxvy=rng.choice((-51, -1, 0, 1, 3916)),
                   gx=rng.uniform(-1000, 12000), gy=rng.uniform(-1000, 7000),
                   old_y=rng.randint(-5000, 12000),
                   qx=rng.choice((0, 0.999, 1.0, -1.0, 20.0, -120.5)),
                   qy=rng.choice((0, 0.999, 1.0, -1.0, 20.0, -120.5)),
                   actual_tx=rng.uniform(-9000, 1000), actual_ty=rng.uniform(-5000, 1000),
                   vertical_mode=rng.choice(('reset', 'band', 'legacy')))


def check_native_primitives() -> dict:
    expected = ((1.9, 1), (-1.9, -1), (2147483648.0, -2147483648),
                (-2147483649.0, 2147483647), (4294967296.0, 0),
                (math.nan, 0), (math.inf, 0), (-math.inf, 0))
    for value, result in expected:
        assert as3_int(value) == result
    randoms = ((0.0, 0.0), (0.2, 0.0), (0.2000001, 0.0),
               (0.9, 0.5), (math.nextafter(1.0, 0.0), math.nextafter(1.0, 0.0)))
    quake_checks = 0
    for q in (0, 0.001, -0.001, 0.999, -0.999, 1, -1, 2, -2, 127.5, -127.5):
        for random_pair in randoms:
            assert abs(native_quake(q, *random_pair)) <= abs(q)
            quake_checks += 1
    # Show why floor or rounding cannot substitute for AS3 int.
    assert as3_int(-1.9) != math.floor(-1.9)
    assert as3_int(1.9) != round(1.9)
    return dict(toInt32Cases=len(expected), quakeCases=quake_checks,
                negativeFloorAndRoundSubstitutionRejected=True)


def reviewed_candidate(p: Pose) -> tuple[Rect, Rect]:
    """Literal geometry adapter for the hash-pinned AS offset/plan methods.

    This interval algorithm is the subject under test, not the oracle.  The
    oracle above executes each actual native Y branch and quake choice.  AIR
    object/domain/Stage guards are NOT executed by this Python adapter.
    """
    def safe_int(value: float) -> int:
        if not math.isfinite(value) or not -2147483646 <= value <= 2147483646:
            raise ValueError('unsafe int')
        return as3_int(value)

    def integer(value: float) -> float:
        if safe_int(value) != value:
            raise ValueError('not integer')
        return value

    def offset(center: int, screen: float, maximum: float, vertical: bool) -> int:
        if maximum < 0:
            return safe_int(-maximum / 2)
        result = safe_int(-float(center) + screen / 2 + (100 if vertical else 0))
        if result > 0:
            result = 0
        if result < -maximum:
            result = safe_int(-maximum)
        return result

    if not p.moved:
        raise ValueError('ordinary guard requires moved')
    if (not math.isfinite(p.scale) or p.scale <= 0
            or integer(p.width) <= 0 or integer(p.height) <= 0):
        raise ValueError('invalid viewport')
    for value in (p.gx, p.gy, p.qx, p.qy, p.actual_tx, p.actual_ty):
        if not math.isfinite(value):
            raise ValueError('non-finite field')
    old_y = integer(p.old_y)
    max_x, max_y = integer(p.maxvx), integer(p.maxvy)
    vx = offset(safe_int(p.gx * p.scale), p.width, max_x, False)
    vya = offset(safe_int(min(old_y, p.gy * p.scale)), p.height, max_y, True)
    vyb = offset(safe_int(max(old_y, p.gy * p.scale)), p.height, max_y, True)
    qx, qy = abs(p.qx) + 2, abs(p.qy) + 2
    predicted = Rect((-vx - qx) / p.scale, (-max(vya, vyb) - qy) / p.scale,
                     (p.width - vx + qx) / p.scale, (p.height - min(vya, vyb) + qy) / p.scale)
    actual = viewport(p.actual_tx, p.actual_ty, p)
    return actual.union(predicted).padded(320), predicted


def candidate_geometry_checks(poses: list[Pose]) -> dict:
    assert digest(CANDIDATE) == CANDIDATE_SHA, 'Candidate changed: inspect AS and update adapter explicitly'
    raw = CANDIDATE.read_bytes()
    newline = b'\r\n' if b'\r\n' in raw else b'\n'
    counter_replacements = (
        ('                    visibleSleeping:0,visibleSleepingExamples:[],oldNearOnlySleeping:0,oldNearOnlySleepingExamples:[],\n'
         '                    unitsExamined:0,errors:[],checkComplete:false};\n',
         '                    visibleSleeping:0,visibleSleepingExamples:[],unitsExamined:0,errors:[],checkComplete:false};\n'),
        ('                viewportContained:null,visibleSleeping:0,visibleSleepingExamples:[],oldNearOnlySleeping:0,\n'
         '                oldNearOnlySleepingExamples:[],unitsExamined:0,errors:[],checkComplete:false};\n',
         '                viewportContained:null,visibleSleeping:0,visibleSleepingExamples:[],unitsExamined:0,errors:[],checkComplete:false};\n'),
        ('''                    if(last.applied) {
                        var inNew:Boolean=x+sx>=last.planned.left && x-sx<=last.planned.right && y>=last.planned.top && y-sy<=last.planned.bottom;
                        var inOld:Boolean=x+sx>=last.oldNear.left && x-sx<=last.oldNear.right && y>=last.oldNear.top && y-sy<=last.oldNear.bottom;
                        var oldPlayerNear:Boolean=Math.abs(x-last.inputs.playerXScaled/last.inputs.scale)<1900 &&
                            Math.abs(y-last.inputs.playerYScaled/last.inputs.scale)<1300;
                        if(!inNew && (inOld || oldPlayerNear)) {
                            ++out.oldNearOnlySleeping;
                            if(out.oldNearOnlySleepingExamples.length<8)
                                out.oldNearOnlySleepingExamples.push({x:x,y:y,scX:sx,scY:sy});
                        }
                    }
''', ''),
    )
    previous = raw
    for new, old in counter_replacements:
        new_bytes = new.encode().replace(b'\n', newline)
        old_bytes = old.encode().replace(b'\n', newline)
        assert previous.count(new_bytes) == 1
        previous = previous.replace(new_bytes, old_bytes, 1)
    assert hashlib.sha256(previous).hexdigest().upper() == INTERMEDIATE_CANDIDATE_SHA
    additions = (
        b"            return last; // Explicit for this compiler's try/finally return analysis." + newline,
        newline.join((
            b'                if(last.applied && (ordinary(w,w.loc,w.cam)!=null || Number(w.cam.scaleV)!==last.inputs.scale ||',
            b'                    w.cam.screenX!==last.inputs.screenX || w.cam.screenY!==last.inputs.screenY))',
            b'                    throw new Error("post-check-follow-scale-or-size-changed");',
        )) + newline,
    )
    for addition in additions:
        assert previous.count(addition) == 1
        previous = previous.replace(addition, b'', 1)
    assert hashlib.sha256(previous).hexdigest().upper() == PRIOR_CANDIDATE_SHA
    # Hash pins every guard too; these anchors identify what was manually mapped.
    source = CANDIDATE.read_text('utf-8-sig')
    for anchor in ('private static function offset(center:int,screen:Number,maximum:Number,vertical:Boolean):int',
                   'Math.abs(number(c.quakeX,"quakeX"))+2',
                   'offset(safeInt(Math.min(oldY,y),"nextY-low"),height,maxY,true)',
                   'Math.min(current.left,predicted.left)-320'):
        assert source.count(anchor) == 1, 'Candidate mapping anchor changed'
    choices = ((0.0, 0.0), (0.2, 0.0), (0.2000001, 0.0),
               (0.9, 0.5), (math.nextafter(1.0, 0.0), math.nextafter(1.0, 0.0)))
    count = current_count = outcomes = 0
    branches = {}
    fallback = {}
    violations = []
    for p in poses:
        if not p.moved:
            fallback['not-moved'] = fallback.get('not-moved', 0) + 1
            continue
        planned, predicted = reviewed_candidate(p)
        current_count += 1
        assert planned.contains(viewport(p.actual_tx, p.actual_ty, p))
        count += 1
        for rx in choices:
            for ry in choices:
                result = native_calc(p, rx, ry)
                branches[result['branch']] = branches.get(result['branch'], 0) + 1
                # Additional coordinate-setter stress, NOT a proved AIR rounding rule.
                # Test both signs and zero without relying on a specific rounding mode.
                for error_x, error_y in ((0, 0), (-0.05, 0.05), (0.05, -0.05)):
                    actual = viewport(result['vx'] + result['qx'] + error_x,
                                      result['vy'] + result['qy'] + error_y, p)
                    outcomes += 1
                    if not predicted.contains(actual) or not planned.contains(actual):
                        if len(violations) < 8:
                            violations.append(dict(pose=p.__dict__, branch=result['branch'],
                                                   predicted=predicted.data(), actual=actual.data()))
    assert not violations, json.dumps(violations, ensure_ascii=False)

    rejected = []
    invalid = (replace(Pose(), scale=0), replace(Pose(), scale=-1),
               replace(Pose(), scale=math.nan), replace(Pose(), width=0),
               replace(Pose(), height=-1), replace(Pose(), gx=math.inf),
               replace(Pose(), gy=math.nan), replace(Pose(), old_y=1.5),
               replace(Pose(), maxvx=2147483647), replace(Pose(), gx=2147483647),
               replace(Pose(), gy=-2147483647), replace(Pose(), qx=math.nan),
               replace(Pose(), actual_tx=math.inf), replace(Pose(), moved=False))
    for index, p in enumerate(invalid):
        try:
            reviewed_candidate(p)
        except ValueError:
            rejected.append(index)
    assert len(rejected) == len(invalid), 'Unsafe geometry was admitted'

    # Negative controls distinguish actual history, future motion and quake.
    teleport = replace(Pose(), gx=9000, vertical_mode='reset')
    outcome = native_calc(teleport, (0, 0), (0, 0))['rectangle']
    assert not viewport(teleport.actual_tx, teleport.actual_ty, teleport).padded(320).contains(outcome)
    changed_visual = replace(Pose(), actual_tx=-9000)
    _, forecast = reviewed_candidate(changed_visual)
    assert not forecast.padded(320).contains(viewport(changed_visual.actual_tx, changed_visual.actual_ty, changed_visual))
    shaking = replace(Pose(), qx=1000, qy=-1000)
    no_quake_plan, _ = reviewed_candidate(replace(shaking, qx=0, qy=0))
    assert not no_quake_plan.contains(native_calc(shaking, (0, 0), (0, 0))['rectangle'])

    # These are explicit out-of-contract witnesses, not failures to hide or fix
    # by silently enlarging the candidate until it covers the entire map.
    start = Pose()
    original_plan, _ = reviewed_candidate(start)
    late_writes = {
        'late-quake': replace(start, qx=10000),
        'late-player-teleport': replace(start, gx=9000, vertical_mode='reset'),
        'late-scale': replace(start, scale=0.5, maxvx=2768, maxvy=1416, vertical_mode='reset'),
    }
    uncovered = {}
    for name, changed in late_writes.items():
        actual = native_calc(changed, (0, 0), (0, 0))['rectangle']
        assert not original_plan.contains(actual), 'Expected late-write counterexample was not exercised'
        uncovered[name] = dict(planned=original_plan.data(), actual=actual.data())
    return dict(candidateChecked=True, candidateSource=str(CANDIDATE), candidateSHA256=CANDIDATE_SHA,
                candidatePriorSHA256=PRIOR_CANDIDATE_SHA, twoAdditionsReverseExact=True,
                candidateIntermediateSHA256=INTERMEDIATE_CANDIDATE_SHA, observerCountersReverseExact=True,
                candidateGeometryUnchangedSincePrior=True,
                adapterKind='manually-reviewed-hash-pinned-AS-geometry-only',
                conditionalGeometryPassed=True, runtimeGuardsExecuted=False,
                ordinaryPoses=count, currentViewChecks=current_count, nativeOutcomes=outcomes,
                nativeBranches=branches, expectedFallbackPoses=fallback,
                unsafeInputsRejected=len(rejected), violations=violations,
                negativeControls=['missing-next-view', 'missing-actual-view', 'missing-quake-bound'],
                explicitUncoveredLateWrites=uncovered,
                displaySetterStressStagePixels=0.05, strictContainmentTolerance=0,
                lateObjectWritesProvenSafe=False)


def main() -> int:
    started = time.perf_counter()
    assert digest(CAMERA) == CAMERA_SHA, 'Native Camera source fingerprint changed'
    report = dict(version=VERSION, nativeSource=str(CAMERA), nativeSourceSHA256=CAMERA_SHA,
                  scriptSHA256=digest(Path(__file__)), nativePrimitives=check_native_primitives(),
                  candidateChecked=False, candidateStatus='awaiting-reviewed-candidate-adapter',
                  gameRun=False, compiled=False, productionAcceptance=False,
                  limitations=[
                      'No AIR runtime execution or display-list rendering is performed.',
                      'No object-step writes between activity and Camera.calc are modeled.',
                      'Late quake/player/viewport/scale writes are not covered.',
                      'Finite enumerated cases do not prove every possible runtime input.',
                      'No AI, interaction, alarm, projectile, or sleep lifecycle acceptance.'
                  ])
    counts = {}
    poses = list(directed_poses())
    for pose in poses:
        result = native_calc(pose, (0.9, 0.5), (0.9, 0.5))
        counts[result['branch']] = counts.get(result['branch'], 0) + 1
        assert all(math.isfinite(x) for x in result['rectangle'].data().values())
    report['candidateGeometry'] = candidate_geometry_checks(poses)
    report.update(candidateChecked=True, candidateStatus='conditional-geometry-only-passed',
                  nativeModelPoses=len(poses), nativeBranches=counts,
                  elapsedMs=(time.perf_counter() - started) * 1000)
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
