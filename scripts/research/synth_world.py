"""
Synthetic Embodied World Stream — 스케일링 연구용 생성기
==============================================================================
program_roadmap Phase 4 / EMBODIMENT_PIPELINE §다음. 실제 Quest 데이터가 하드웨어
의존이라, **통제 가능한 합성 스트림**으로 자기학습 스택의 스케일 거동을 규명한다.

정직성 원칙: 판타지가 아니라 **실제 45프레임 통계에 캘리브레이션한 외삽**.
캘리브레이션 타깃 (calib_stats, 2026-07-13):
  objects/frame mean 5.44 · Jaccard(연속) 0.309 · new/frame 3.11 · singleton 51% ·
  최빈객체 점유 0.80 · vocab Zipfian(top5 [36,22,22,13,13]).

생성 모델 (embodied 구조를 잠재로)
----------------------------------
- 세계 = n_scenes 장면. 각 장면 = home 객체(gaze 근처, 최빈) + stable 객체(고정 각도) +
  일부 shared 객체(장면 간 구조).
- 에이전트 = (scene, head_angle). 프레임마다 머리 회전(motion) / 드물게 장면 전환.
- 프레임 = FOV 콘 안 객체 (dropout noise) + **transient 객체**(전역 유일 id, 그 프레임만
  등장 → singleton 생성). → home+stable=지속성(Jaccard), transient+motion=novelty(new/frame).
- 각 프레임 pose = [cos θ, sin θ, scene] (감각운동 예측용, pose delta = 머리움직임).

노브 (스케일링 격자): N(밀도) · n_scenes(다양성) · motion(움직임) · transient_rate(novelty)
  · noise(dropout). 출력 = [(t, [objects], pose)] — prequential/trainable 하니스와 동일 포맷.

Usage:
    python scripts/research/synth_world.py --calibrate   # 실제 대비 통계 검증
"""
from __future__ import annotations
import argparse, math, random, statistics, sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")
TWO_PI = 2 * math.pi

# 실제 캘리브레이션 타깃 (calib_stats 2026-07-13)
TARGET = {"objs_per_frame": 5.44, "jaccard": 0.309, "new_per_frame": 3.11,
          "singleton_frac": 0.51, "top_share": 0.80}


def build_world(n_scenes, stable_per_scene, shared_frac, rng):
    n_shared = max(1, int(stable_per_scene * shared_frac))
    shared = [f"sh_{i}" for i in range(n_shared * 2)]
    scenes = []
    for s in range(n_scenes):
        # ghome = 전역 최빈 객체(모든 장면·항상 보임, 실제 keyboard 80% 재현) + 장면별 home
        objs = [("ghome", 0.0), (f"home_{s}", 0.0)]
        for _ in range(n_shared):                          # 장면 간 공유 구조
            objs.append((rng.choice(shared), rng.uniform(0, TWO_PI)))
        for i in range(stable_per_scene - n_shared):       # 장면 고유 stable
            objs.append((f"s{s}_o{i}", rng.uniform(0, TWO_PI)))
        scenes.append(objs)
    return scenes


def angdist(a, b):
    return abs(((a - b + math.pi) % TWO_PI) - math.pi)


def generate_stream(N, n_scenes=2, motion=2.0, transient_rate=0.35, noise=0.08,
                    stable_per_scene=16, fov=1.6, seed=0, scene_dwell=0.97,
                    transient_recur=0.4):
    """scene_dwell = 프레임당 같은 장면에 머물 확률 (높을수록 저다양성=실제 데스크 장면 근사).
    home 객체는 장면 안에서 항상 보임(dropout만) → 최빈객체(실제 keyboard 80%) 재현."""
    rng = random.Random(seed)
    scenes = build_world(n_scenes, stable_per_scene, shared_frac=0.3, rng=rng)
    frames = []
    scene = rng.randrange(n_scenes)
    angle = 0.0
    t = 0.0
    trans_id = 0
    recent_trans: list[str] = []
    for _i in range(N):
        if rng.random() > scene_dwell:                    # 장면 전환 (다양성 노브)
            scene = rng.randrange(n_scenes); angle = rng.uniform(0, TWO_PI)
        else:
            angle += -math.sin(angle) * 0.25              # home(0) 쪽 복원력
            angle += rng.gauss(0, motion)                 # 머리 회전 (움직임 노브)
        angle %= TWO_PI
        vis = []
        for (name, oa) in scenes[scene]:
            always = name == "ghome" or name.startswith("home_")   # 항상 보임(dropout만)
            if always or angdist(oa, angle) <= fov / 2:
                if rng.random() > noise:
                    vis.append(name)
        n_tr = 0                                          # transient → novelty (일부는 재등장)
        while rng.random() < transient_rate and n_tr < 3:
            if recent_trans and rng.random() < transient_recur:
                vis.append(rng.choice(recent_trans))      # 재등장 → freq≥2 (singleton 완화)
            else:
                nm = f"trans_{trans_id}"; trans_id += 1
                vis.append(nm)
                recent_trans.append(nm)
                if len(recent_trans) > 25:
                    recent_trans.pop(0)
            n_tr += 1
        objs = list(dict.fromkeys(vis))
        t += rng.uniform(4, 8)
        pose = [math.cos(angle), math.sin(angle), float(scene)]
        frames.append((round(t, 2), objs, pose))
    return frames


def stats(frames):
    counts = [len(set(f[1])) for f in frames]
    vocab = Counter()
    for _t, ns, _p in frames:
        for n in set(ns):
            vocab[n] += 1
    freqs = sorted(vocab.values(), reverse=True)
    singleton = sum(1 for v in freqs if v == 1)
    # 연속 Jaccard / new (동일 스트림, 세션 분할 없음 — 합성은 연속)
    jac, new = [], []
    for i in range(len(frames) - 1):
        a = set(frames[i][1]); b = set(frames[i + 1][1])
        if a and b:
            jac.append(len(a & b) / len(a | b)); new.append(len(b - a))
    usable = sum(1 for c in counts if c >= 2)
    return {
        "n_frames": len(frames), "vocab": len(vocab),
        "objs_per_frame": round(statistics.mean(counts), 2),
        "usable_frac": round(usable / len(frames), 2),
        "jaccard": round(statistics.mean(jac), 3) if jac else 0,
        "new_per_frame": round(statistics.mean(new), 2) if new else 0,
        "singleton_frac": round(singleton / len(vocab), 2) if vocab else 0,
        "top_share": round(freqs[0] / len(frames), 2) if freqs else 0,
    }


def to_events(frames):
    """prequential/trainable 하니스 포맷 (t, [names]) — pose 분리."""
    return [(t, objs) for (t, objs, _p) in frames]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("-N", type=int, default=200)
    args = ap.parse_args()
    frames = generate_stream(args.N, seed=42)
    s = stats(frames)
    print(f"=== SYNTH WORLD (N={args.N}, default knobs) ===")
    print(f"  {'metric':<18}{'synth':>10}{'real target':>14}")
    for k, tgt in [("objs_per_frame", TARGET["objs_per_frame"]),
                   ("jaccard", TARGET["jaccard"]),
                   ("new_per_frame", TARGET["new_per_frame"]),
                   ("singleton_frac", TARGET["singleton_frac"]),
                   ("top_share", TARGET["top_share"])]:
        dev = abs(s[k] - tgt) / tgt
        flag = "✅" if dev < 0.25 else ("🟡" if dev < 0.5 else "❌")
        print(f"  {k:<18}{s[k]:>10}{tgt:>14}  {flag} ({dev*100:.0f}% off)")
    print(f"  {'vocab':<18}{s['vocab']:>10}  usable_frac {s['usable_frac']}")
    if args.calibrate:
        print("\n  (모든 지표 ✅/🟡 = 실제 분포에 근사. ❌면 노브 재튜닝.)")


if __name__ == "__main__":
    main()
