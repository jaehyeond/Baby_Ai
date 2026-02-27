# ISMAR 2026 Gap Analysis: Paper Claims vs Actual System

**Date**: 2026-02-25
**Purpose**: Map every ISMAR paper section to actual implementation, identify gaps for Unity XR porting, and plan figure strategy.

---

## 1. Paper vs Reality Mapping (Section-by-Section)

### Section 3.1: Cognitive Architecture Summary (0.5 page)

**Paper Claims**: Brief summary of the Baby AI cognitive architecture (referencing ICDL paper). 13 modules, developmental stages, emotion-modulated learning.

**Actual Implementation**:

| Paper Claim | Actual State | File(s) | Gap |
|-------------|-------------|---------|-----|
| 13 cognitive modules | 13 Edge Functions deployed and ACTIVE | `Task.md` line 33-49 | NONE - System EXCEEDS paper scope |
| 5 developmental stages | Defined in Python + DB (stage=5 currently) | `neural/baby/development.py`, `useBrainRegions.ts` (STAGE_PARAMS 0-7) | EXCEEDS: 8 stages defined (0-7), paper describes 5 |
| Emotion-modulated learning | LC-NE Adaptive Gain modulator (v28) | `conversation-process` v30, `PAPER_PLAN.md` F4-F5 | NONE |
| Memory consolidation (sleep) | LLM-free consolidation v6 | `memory-consolidation` Edge Function | NONE |

**Verdict**: System significantly EXCEEDS what the paper describes. The paper only needs a 0.5-page summary.

---

### Section 3.2: Brain Region Mapping (9 regions, spherical coordinates)

**Paper Claims**: 486 artificial semantic concepts mapped onto 9 anatomically-inspired brain regions using spherical coordinates.

**Actual Implementation**:

| Paper Claim | Actual State | File(s) |
|-------------|-------------|---------|
| 9 brain regions | 9 regions in `brain_regions` table | `useBrainRegions.ts` line 6-21 (BrainRegion interface) |
| Spherical coordinates (theta, phi, r) | Each region has `theta_min/max`, `phi_min/max`, `radius_min/max` | `useBrainRegions.ts` line 6-21 |
| 486 concepts | **488** semantic_concepts (live, growing) | `semantic_concepts` table |
| Concept-to-region mapping | **452** mappings in `concept_brain_mapping` | DB table |
| Spherical-to-Cartesian conversion | `sphericalToCartesian()` function with ellipsoid scaling | `RealisticBrain.tsx` line 15-24 |
| Region size based on neuron count | `baseSize = max(0.3, min(1.2, 0.3 + neuronCount * 0.003))` | `RealisticBrain.tsx` line 146-148 |
| Development-gated region availability | `developmentStage >= region.development_stage_min` filter | `useBrainRegions.ts` line 65-67 |

**Key Differences**:
- Paper says "486 concepts" -- actual system has **488** (and growing with every conversation)
- Paper describes a fixed dataset; actual system is **live and accumulating**
- Paper does not mention the **ellipsoid scaling** (scaleX=1.2, scaleY=1.0, scaleZ=1.1) that gives the brain a realistic non-spherical shape

**Verdict**: EXACT MATCH with minor EXCEED (live data > fixed dataset).

---

### Section 3.3: Spreading Activation Visualization (BFS + ripple)

**Paper Claims**: Real-time visualization of spreading activation waves using BFS traversal from directly activated concepts to 2-hop neighbors.

**Actual Implementation**:

| Paper Claim | Actual State | File(s) |
|-------------|-------------|---------|
| BFS spreading activation | Implemented in `conversation-process` v30 backend | Edge Function |
| Direct activation (t=0) | `trigger_type === 'conversation'`, intensity: source=0.6 | `useNeuronActivations.ts` line 57-58 |
| 1-hop spreading (t=1) | `trigger_type === 'spreading_activation'` | `useNeuronActivations.ts` line 58 |
| 2-hop max depth | `k_max = 2` in spreading algorithm | `PAPER_PLAN.md` F2 formula |
| Decay factor d=0.5 | Implemented in backend | Edge Function |
| Visual ripple effect | `SpreadingRipple` component (expanding ring, 1.25s cycle) | `RealisticBrain.tsx` line 81-115 |
| Activation decay timers | Direct: 3s, Spreading: 5s | `useNeuronActivations.ts` line 60 |
| Heatmap (cumulative) | `heatmapRegions` map, normalized activation_count | `useNeuronActivations.ts` line 153-161 |
| Thought Process Panel | Shows direct path + spreading region groups | `RealisticBrain.tsx` line 445-589 |
| Replay on page load | Last conversation replayed over 3s on mount | `useNeuronActivations.ts` line 203-218 |

**What the paper does NOT describe but EXISTS**:
- **ThoughtProcessPanel**: Shows the causal chain "user said X -> concept A -> concept B -> spreading to regions" -- this is a major XAI feature the paper should highlight
- **Wave count tracking** (`waveCount` state)
- **Bidirectional spreading** with reverse decay gamma=0.7
- **ActivationContext**: Links each activation wave to the conversation that caused it
- **Amber color coding** for spreading vs direct activations

**Verdict**: System SIGNIFICANTLY EXCEEDS paper claims. The ThoughtProcessPanel alone is a major contribution not in the paper draft.

---

### Section 3.4: Real-time Pipeline (Supabase -> Unity/Client)

**Paper Claims**: Supabase REST for initial data load, WebSocket (Phoenix Channel) for real-time neuron activations.

**Actual Implementation (Web)**:

| Pipeline Step | Actual Implementation | File(s) |
|---------------|----------------------|---------|
| Initial data load | Supabase JS client direct queries | `useBrainData.ts`, `useBrainRegions.ts` |
| Real-time activations | `supabase.channel('brain-activity').on('postgres_changes', INSERT, 'neuron_activations')` | `useNeuronActivations.ts` line 232-237 |
| Activation summary RPC | `get_brain_activation_summary()` PostgreSQL function | `useNeuronActivations.ts` line 146 |
| Data tables queried | `semantic_concepts`, `concept_relations`, `brain_regions`, `concept_brain_mapping`, `neuron_activations`, `baby_state` | Multiple hooks |

**For Unity XR Port** (paper claims Unity 2022 LTS + Meta XR SDK):
- The web system uses Supabase JS SDK. Unity needs `supabase-csharp` + `UnityWebRequest`
- WebSocket Realtime in Unity needs `NativeWebSocket` or `supabase-csharp` Realtime with IL2CPP `link.xml` workaround
- This is the largest implementation gap

**Verdict**: Web pipeline is COMPLETE. Unity pipeline needs FULL BUILD from scratch.

---

### Section 3.5: Sleep Mode Memory Consolidation Visualization

**Paper Claims** (from user's paper structure description):
- Phase 0 (0-2s): Initiation, environment dims
- Phase 1 (2-8s): Emotional Strengthening (salience >0.3 pulse/glow/grow)
- Phase 2 (8-14s): Forgetting (old weak memories shrink/fade)
- Phase 3 (14-18s): Synaptic Pruning (weak edges fade, strong thicken)
- Phase 4 (18-20s): Completion

**Actual Implementation**:

| Paper Phase | Backend Reality | Frontend Reality |
|-------------|----------------|------------------|
| Emotional Strengthening | `emotional_salience > 0.3` strengthened in `memory-consolidation` v6 | `MemoryConsolidationCard.tsx` shows `memories_strengthened` count |
| Forgetting | `last_accessed > 1 day` decayed | Shows `memories_decayed` count |
| Synaptic Pruning | Pattern promotion (2+ repetitions -> procedural) | Shows `patterns_promoted` count |
| 5-phase animation (0-20s) | **DOES NOT EXIST** | Sleep page is a **static card UI** with stats |

**CRITICAL GAP**: The paper describes a rich 5-phase animated visualization of the sleep consolidation process. The actual implementation has:
- A static `MemoryConsolidationCard` showing consolidation log statistics
- An `useIdleSleep` hook that triggers consolidation after 30 min idle
- A `/sleep` page with info cards and the MemoryConsolidationCard
- **NO animated visualization** of the consolidation phases
- **NO dimming, pulsing, shrinking, or edge manipulation animations**

The backend consolidation algorithm IS real (emotional strengthening, forgetting, pattern promotion), but the frontend visualization of these phases as a temporal animation is **entirely absent**.

**Verdict**: Backend MATCHES paper claims. Frontend visualization is a CRITICAL GAP -- the 5-phase animation needs to be built.

---

### Section 3.6: Node Properties Encoding

**Paper Claims**: Node properties encode memory_strength, emotional_salience, last_accessed.

**Actual Implementation**:

| Property | DB Column | Frontend Visual Encoding | File(s) |
|----------|-----------|-------------------------|---------|
| memory_strength | `semantic_concepts.strength` (0-1) | Node size: `0.08 + strength * 0.12` | `BrainVisualization.tsx` line 33 |
| emotional_salience | Computed from `emotion_logs` + `experiences.emotional_weight` | **NOT directly encoded on nodes** | -- |
| last_accessed | `semantic_concepts.updated_at` or `last_accessed_at` | **NOT visually encoded** | -- |
| usage_count | `semantic_concepts.usage_count` | NOT directly on nodes; used for sort/filter | `useBrainData.ts` |
| category | `semantic_concepts.category` | Node color via `CATEGORY_COLORS` map (~20 categories) | `useBrainData.ts` line 34-80 |
| emissive glow | Activation intensity | `emissiveIntensity` on material | `BrainVisualization.tsx` line 70 |

**Gap**: `emotional_salience` and `last_accessed` are NOT visually encoded on individual neuron nodes. Only `strength` (size) and `category` (color) are mapped. The heatmap intensity on brain REGIONS encodes cumulative activation count, not per-node temporal recency.

**Verdict**: PARTIAL MATCH. Two of three claimed encodings (emotional_salience, last_accessed) are not visually represented on individual nodes.

---

### Section 4: Fixed JSON Dataset (18 concepts, 22 relations)

**Paper Claims**: Fixed JSON dataset with 18 semantic concepts and 22 relations.

**Actual System**:

| Paper | Actual | Ratio |
|-------|--------|-------|
| 18 concepts | **488** semantic_concepts | 27x larger |
| 22 relations | **616** concept_relations | 28x larger |
| Fixed JSON | **Live Supabase DB** (growing) | Dynamic vs Static |
| N/A | 9 brain regions | Additional layer |
| N/A | 452 concept-brain mappings | Additional layer |
| N/A | 965 experiences | Additional dimension |
| N/A | 553 consolidation logs | Additional dimension |

**Analysis**: The paper describes a radically simplified subset for the Unity XR demo. This is a sensible strategy:
- Unity on Quest 3S needs to render at 72fps
- 488 nodes + 616 edges is feasible (tested at 500 in the web version)
- But the paper's claim of "18 concepts, 22 relations" is for a pre-baked demo scenario
- The actual system can feed ANY subset via REST API query with LIMIT

**Recommendation**: Do NOT lock the paper to 18/22. Instead:
- Load top-N concepts by usage_count (N configurable, default 100-200 for Quest performance)
- The paper should state "the system supports dynamic data loading; we demonstrate with a curated subset of N concepts for controlled evaluation"

---

### Section 5: Interaction (Point+Air Tap, Pinch Zoom, Grab+Drag)

**Paper Claims**: Quest 3 XR interaction with point+air tap, pinch zoom, grab+drag.

**Actual Implementation (Web)**:

| Paper Interaction | Web Equivalent | Implementation |
|-------------------|---------------|----------------|
| Point + Air Tap | Mouse click on node | `onClick` handlers on mesh objects |
| Pinch Zoom | Scroll wheel zoom | `OrbitControls enableZoom={true}` |
| Grab + Drag | Click-drag rotate | `OrbitControls enableRotate={true}` |
| Node selection | Click to select/deselect | `selectedNeuron`, `selectedRegion` state |
| Hover tooltip | Mouse hover shows label | `onPointerOver/Out` + `Html` drei component |
| Auto-rotate | Idle rotation | `OrbitControls autoRotate autoRotateSpeed={0.3-0.5}` |

**For Unity XR Port**:
- Need XR Interaction Toolkit + XR Hands integration
- Raycast selection replaces mouse click
- Hand tracking (25-joint skeleton) for pinch/grab
- World-space UI panels for tooltips (no Html/CSS in Unity)

**Verdict**: Web interaction is COMPLETE. Unity XR interaction needs FULL BUILD.

---

### Section 6: Expert Evaluation

**Paper Claims**: 6 experts (2 XR, 2 AI, 2 HCI), 30-min sessions, 7 Temporal XAI Heuristics.

**Actual State**: **NOT CONDUCTED**. This is a future study.

Note: The ISMAR Strategy document (`ISMAR_2026_STRATEGY.md`) describes a more ambitious 3-condition within-subjects user study (N=16-24) with 2D vs 3D Desktop vs MR conditions, NASA-TLX, SUS, SSQ, IPQ. The paper draft's expert evaluation (N=6) is simpler and more feasible within the timeline.

**Verdict**: ENTIRE SECTION needs to be conducted post-implementation.

---

### Section 7: Temporal XAI Heuristics (H1-H7)

**Paper Claims**: 7 heuristics for evaluating temporal XAI visualization.

**Actual State**: These are THEORETICAL CONTRIBUTIONS defined by the paper, not implementation artifacts. They need to be validated through the expert evaluation.

However, the system already addresses several implicitly:
- **H1 (Temporal Progression Visibility)**: Spreading activation replay shows t=0 -> t=1 -> t=2
- **H2 (Mechanism Transparency)**: ThoughtProcessPanel shows WHY each concept activated
- **H3 (State Persistence)**: Heatmap shows cumulative activation history
- **H4 (Transition Clarity)**: SpreadingRipple ring effect distinguishes direct vs spreading
- **H5 (Temporal Granularity)**: Decay timers (3s/5s) control temporal resolution

---

## 2. System EXCEEDS Paper Claims -- Highlight Opportunities

The following features exist in the actual system but are NOT mentioned in the paper draft. These represent missed opportunities for stronger contributions:

### 2.1 ThoughtProcessPanel (Major Contribution)

**File**: `RealisticBrain.tsx` lines 445-589

This panel shows the complete reasoning chain:
1. **Cause**: "User said: [message]" with emotion tag
2. **Direct Path**: concept A -> concept B -> concept C (with arrows, per-concept region labels)
3. **Spreading Regions**: grouped by brain region, showing which concepts were activated associatively

This is literally the "Temporal XAI" the paper title promises. It should be Figure 3 or similar.

### 2.2 Two Visualization Modes (Anatomical + Abstract)

**File**: `brain/page.tsx` line 26 (`BrainViewMode = 'abstract' | 'anatomical'`)

The paper mentions one view. The system has TWO:
- **Anatomical**: 9 region spheres in spherical coordinates, neuron particles, region connections (`RealisticBrain.tsx`)
- **Abstract**: Full 488-node network with Louvain clustering, Astrocyte meta-nodes, 616 synapses (`BrainVisualization.tsx`)

This duality directly supports **RQ2** from the ISMAR strategy: "Is the anatomical metaphor more intuitive than the abstract network?"

### 2.3 Louvain Clustering + Astrocyte Meta-nodes

**File**: `useBrainData.ts` (hook), `BrainVisualization.tsx` (AstrocyteSphere component)

Community detection algorithm that groups semantically related concepts into clusters, with each cluster represented by a glowing "Astrocyte" meta-node. Not mentioned in the paper.

### 2.4 Fibonacci Sphere Placement

**File**: Referenced in ISMAR strategy as existing in useBrainData. The golden-ratio spiral distributes neurons evenly on the sphere surface.

### 2.5 Imagination Session Visualization

**File**: `ImaginationPanel.tsx`, `BrainVisualization.tsx` (ImaginationConnection component)

During idle periods, the system runs "imagination sessions" that discover new connections between concepts. These are visualized as amber glowing lines in the abstract brain view.

### 2.6 Prediction Verification UI

**File**: `PredictionVerifyPanel.tsx`

Users can verify the AI's predictions (was_correct, actual_outcome, insight_gained). This closed-loop feedback is a strong AI transparency feature.

### 2.7 Real-time Emotion Radar

**File**: `EmotionRadar.tsx`

6 basic + 5 complex emotions visualized as a radar chart with real-time updates. Directly supports the emotion-modulation claims.

### 2.8 13 Backend Modules (vs paper's simplified description)

The paper describes a "cognitive architecture" briefly. The actual system has 13 independently deployable Edge Functions, each version-controlled, with a full conversation pipeline including:
- Memory Recall Pipeline (keyword extraction -> concept/experience retrieval)
- LC-NE Adaptive Gain modulator (Aston-Jones & Cohen 2005)
- Ablation-aware data isolation
- Autonomous curiosity with question routing

---

## 3. Critical Gaps for Unity XR Porting

### 3.1 Must Build from Scratch in Unity

| Component | Estimated Effort | Complexity | Notes |
|-----------|-----------------|------------|-------|
| **SupabaseClient (REST)** | 4h | Medium | UnityWebRequest + JSON parsing for 6 tables |
| **SupabaseRealtimeClient (WebSocket)** | 6h | High | `supabase-csharp` Realtime + `link.xml` for IL2CPP |
| **BrainDataManager** | 4h | Medium | Fibonacci sphere placement + Louvain clustering port from JS to C# |
| **NeuronRenderer** | 3h | Medium | SRP Batcher, 500 icospheres (80-320 tris each, NOT Unity default 768-tri sphere) |
| **ConnectionRenderer** | 3h | Medium | Single procedural mesh with billboard quads (NOT 600 LineRenderers) |
| **RegionRenderer** | 2h | Low | 9 URP transparent spheres + heatmap coloring |
| **ActivationEffects** | 4h | Medium | Emissive glow, 3s/5s decay timers, SpreadingRipple equivalent |
| **XR Interaction** | 4h | Medium | XR Interaction Toolkit + XR Hands raycast/grab |
| **MR Passthrough** | 3h | Low | OpenXR Meta Passthrough API |
| **ThoughtProcessPanel (3D)** | 4h | High | World-space UI in VR (TextMeshPro panels, no HTML/CSS) |
| **Sleep Animation (5-phase)** | 6h | High | The entire 20-second phased visualization -- NEW BUILD |
| **Total** | **~43h** | | |

### 3.2 Can Be Adapted (Logic Port, Not Rewrite)

| Component | Source | Target | Notes |
|-----------|--------|--------|-------|
| Spherical-to-Cartesian math | `RealisticBrain.tsx` line 15-24 | C# `Vector3` | Direct port, ~10 lines |
| Decay timer logic | `useNeuronActivations.ts` line 56-139 | C# coroutines or `UniTask` | Same logic, different async model |
| Heatmap normalization | `useNeuronActivations.ts` line 153-161 | C# Dictionary operations | Direct port |
| Region availability filter | `useBrainRegions.ts` line 65-67 | C# LINQ | Direct port |
| Category color mapping | `useBrainData.ts` line 34-80 | C# Dictionary<string, Color> | Direct port |

### 3.3 No Port Needed (Backend Stays)

| Component | Reason |
|-----------|--------|
| All 13 Edge Functions | Unity reads from same Supabase DB |
| Database schema (57+ tables) | Unity is read-only client |
| Conversation processing pipeline | Unity does not process conversations |
| Memory consolidation algorithm | Runs server-side, Unity only visualizes results |
| Ablation framework | ICDL paper only |

---

## 4. Data Pipeline Mapping

### 4.1 Paper's "Fixed JSON 18/22" vs Actual Live System

```
PAPER DESCRIPTION                    ACTUAL SYSTEM
==================                   ==============

[Fixed JSON file]                    [Supabase PostgreSQL]
  18 concepts ─────────────────────>   488 semantic_concepts (live, growing)
  22 relations ────────────────────>   616 concept_relations (live, growing)
  Pre-baked                            Real-time via Supabase Realtime

[Unity loads JSON]                   [Web: Supabase JS SDK]
  One-time parse ──────────────────>   REST API queries with LIMIT/ORDER
  No updates ──────────────────────>   WebSocket INSERT subscription on neuron_activations

[Static display]                     [Dynamic pipeline]
  No real-time ────────────────────>   conversation-process v30
  No spreading ────────────────────>     -> Gemini LLM -> concept extraction
                                         -> neuron_activations INSERT
                                         -> spreading_activation INSERT (BFS)
                                         -> Supabase Realtime -> Client
```

### 4.2 Recommended Data Pipeline for Unity XR

```
[Existing Backend - NO CHANGES]
  User talks to Baby AI (web or /sense page)
    -> conversation-process v30
    -> neuron_activations INSERT + spreading INSERT
    -> Supabase Realtime broadcast

[Unity XR Client - NEW BUILD]
  Startup:
    1. REST GET baby_state (1 row)              -> development stage
    2. REST GET brain_regions (9 rows)           -> region geometry
    3. REST GET semantic_concepts (LIMIT 200)    -> neuron nodes
    4. REST GET concept_relations (LIMIT 300)    -> synapse edges
    5. REST GET concept_brain_mapping            -> region assignment
    6. RPC get_brain_activation_summary()        -> heatmap + replay

  Runtime:
    7. WebSocket SUBSCRIBE neuron_activations INSERT
       -> Activation event { concept_id, brain_region_id, intensity, trigger_type }
       -> REST GET concept name/category, region name (cached after first lookup)
       -> Apply decay timer (3s direct, 5s spreading)
       -> Update emissive glow + SpreadingRipple effect
```

### 4.3 Performance Budget Comparison

| Metric | Web (R3F) | Unity Quest 3S | Paper Claims |
|--------|-----------|----------------|--------------|
| Node count | 488 rendered | ~200 target (SRP Batcher) | 18 (fixed JSON) |
| Edge count | 616 rendered | ~300 target (procedural mesh) | 22 (fixed JSON) |
| Draw calls | ~500+ (unoptimized) | ~16-25 (batched) | N/A |
| Frame rate | 60fps (desktop) | 72fps (Quest target) | 72fps claimed |
| Triangles | ~400K+ | ~170K (icospheres) | N/A |

---

## 5. Figure Strategy: Screenshots to Paper Figures

### Available Screenshots (18 images, per user description)

| Screenshot # | Content | Paper Figure Mapping | Priority |
|--------------|---------|---------------------|----------|
| 1 | Home dashboard | Fig 1 (system overview) or supplementary | LOW - not XR |
| 2-10 | Advanced visualization tabs (growth, emotion, brain, milestones, imagination, influence, curiosity, questions, question modal) | Supplementary material | LOW |
| **11** | **Brain abstract view (488 neurons + 616 synapses network)** | **Fig 4a: Abstract network visualization (2D condition)** | HIGH |
| **12** | **Brain anatomical view (9 regions + thought process + spreading activation wave 66)** | **Fig 4b: Anatomical brain with spreading activation** | CRITICAL |
| 13 | Brain prediction verification panel | Supplementary | LOW |
| 14-16 | Sense page (camera, mic, chat tabs) | Supplementary (interaction modalities) | LOW |
| **17-18** | **Sleep & memory consolidation** | **Fig 5: Memory consolidation process** (if animation is built) | MEDIUM |

### Recommended Paper Figure Plan

| Figure # | Content | Source | Status |
|----------|---------|--------|--------|
| **Fig 1** | System architecture diagram (Baby AI -> Supabase -> Unity -> Quest 3S pipeline) | New diagram (draw.io/TikZ) | NEEDS CREATION |
| **Fig 2** | MR demonstration photo (Quest 3S passthrough, brain on table) | Quest 3S capture | NEEDS UNITY BUILD + PHOTO |
| **Fig 3** | Spreading activation sequence (t=0 direct -> t=1 spreading -> t=2 fade) | Screenshot 12 + staged captures | NEEDS UNITY BUILD |
| **Fig 4** | 3-condition comparison (same data: 2D dashboard / 3D desktop / MR) | Screenshot 11 (2D), Unity editor (3D), Quest capture (MR) | PARTIALLY AVAILABLE |
| **Fig 5** | ThoughtProcessPanel close-up (XAI explanation chain) | Screenshot 12 (panel visible) | AVAILABLE from web |
| **Fig 6** | Task results bar chart (accuracy/time across 3 conditions) | Statistical analysis output | NEEDS USER STUDY |
| **Fig 7** | NASA-TLX results (6 subscales) | Statistical analysis output | NEEDS USER STUDY |

### Using Web Screenshots in the Paper

The web dashboard (screenshots 11, 12) can serve as the **2D condition baseline** (C1) in the user study. This is explicitly planned in the ISMAR strategy. The paper can include web screenshots labeled as "2D Dashboard condition" alongside Unity Desktop and MR screenshots.

**Critical**: Screenshots 11 and 12 (brain abstract + anatomical) are the most paper-ready assets. They demonstrate:
- 488 neurons with category-based coloring
- 616 synapses with strength-based opacity
- 9 brain regions with spherical coordinate placement
- Real-time spreading activation (wave 66 visible in screenshot 12)
- ThoughtProcessPanel showing the reasoning chain

---

## 6. Summary: Gap Severity Classification

### RED (Must Fix Before Paper Submission)

| Gap | Description | Effort | Blocker |
|-----|-------------|--------|---------|
| **No Unity XR build** | Paper claims Unity 2022 LTS + Meta XR SDK + Quest 3 | ~35-43h | Cannot submit without MR screenshots |
| **No sleep animation** | Paper describes 5-phase 20-second animation; actual UI is a static stats card | ~6h | Sleep mode is a highlighted paper contribution |
| **No user study** | Section 6 is all TBD | 2-3 weeks | Paper core contribution depends on evaluation |
| **No MR screenshots** | Fig 2 requires Quest 3S running the system | Depends on Unity build | Cannot submit |

### YELLOW (Should Fix, But Paper Can Work Around)

| Gap | Description | Workaround |
|-----|-------------|------------|
| Node property encoding | emotional_salience and last_accessed not visually mapped on nodes | Add opacity mapping for recency, size-pulse for salience |
| Fixed JSON claim | Paper says 18/22 but system has 488/616 | Reframe as "dynamic system demonstrated with N-node subset" |
| useBrainRegions stage 5+ bug | Stage 5 falls back to BABY display params | Fixed in code: STAGE_PARAMS now has 0-7 |

### GREEN (Opportunities to Strengthen Paper)

| Opportunity | Description | Action |
|-------------|-------------|--------|
| ThoughtProcessPanel | Major XAI contribution not in paper | Add as key system feature in Section 3 |
| Dual visualization modes | Anatomical + Abstract toggle | Supports RQ2 directly |
| Louvain clustering | Community detection on concept graph | Novel visualization technique for AI |
| 13 real backend modules | Full cognitive architecture | Strengthen Section 3.1 credibility |
| Live data pipeline | Not pre-baked demo | Emphasize in contribution claims |

---

## 7. Recommended Action Plan

### Phase 1: Unity Foundation (Week 1 -- now)
1. Unity 6 LTS project + URP + Meta OpenXR setup
2. Supabase REST client (6 tables)
3. BrainDataManager (fibonacci + clustering port)
4. NeuronRenderer + ConnectionRenderer + RegionRenderer

### Phase 2: Real-time + MR + Sleep Animation (Week 2)
5. Supabase Realtime WebSocket client
6. Activation effects (glow, decay, ripple)
7. **Sleep consolidation 5-phase animation** (CRITICAL NEW BUILD)
8. MR passthrough + spatial anchoring
9. XR interaction (raycast, grab)

### Phase 3: Paper Assets + Study (Week 3)
10. Capture MR screenshots/video on Quest 3S
11. Create architecture diagram (Fig 1)
12. Stage spreading activation sequence for Fig 3
13. Run expert evaluation / user study
14. Write Sections 5-7

---

## Appendix A: Key File Paths

### Frontend (Web -- existing)
- `E:/A2A/our-a2a-project/frontend/baby-dashboard/src/components/RealisticBrain.tsx` -- Anatomical brain 3D view (9 regions, spherical coords, spreading ripple)
- `E:/A2A/our-a2a-project/frontend/baby-dashboard/src/components/BrainVisualization.tsx` -- Abstract brain 3D view (488 neurons, 616 synapses, Louvain clustering)
- `E:/A2A/our-a2a-project/frontend/baby-dashboard/src/hooks/useNeuronActivations.ts` -- Real-time activation pipeline (Supabase Realtime, decay timers, heatmap, replay)
- `E:/A2A/our-a2a-project/frontend/baby-dashboard/src/hooks/useBrainRegions.ts` -- Brain region data + stage params (0-7)
- `E:/A2A/our-a2a-project/frontend/baby-dashboard/src/hooks/useBrainData.ts` -- Concept/relation data + Louvain + Fibonacci placement
- `E:/A2A/our-a2a-project/frontend/baby-dashboard/src/components/MemoryConsolidationCard.tsx` -- Sleep mode UI (static stats, no animation)
- `E:/A2A/our-a2a-project/frontend/baby-dashboard/src/hooks/useIdleSleep.ts` -- Idle detection + auto-consolidation trigger
- `E:/A2A/our-a2a-project/frontend/baby-dashboard/src/app/brain/page.tsx` -- Brain page (anatomical/abstract toggle, panels)
- `E:/A2A/our-a2a-project/frontend/baby-dashboard/src/app/sleep/page.tsx` -- Sleep page (info cards + MemoryConsolidationCard)

### Backend (Python -- reference)
- `E:/A2A/our-a2a-project/neural/baby/memory.py` -- Memory system (3-tier: episodic/semantic/procedural)
- `E:/A2A/our-a2a-project/neural/baby/development.py` -- Development stages + milestone checks

### Documentation
- `E:/A2A/our-a2a-project/docs/ISMAR_2026_STRATEGY.md` -- Full ISMAR submission strategy (RQ, user study design, timeline)
- `E:/A2A/our-a2a-project/docs/PAPER_PLAN.md` -- Mathematical formalization (F1-F10+)
- `E:/A2A/our-a2a-project/Task.md` -- System state tracking (EF versions, DB stats)

### Database (Supabase)
- `semantic_concepts` (488 rows) -- Neurons
- `concept_relations` (616 rows) -- Synapses
- `brain_regions` (9 rows) -- Anatomical regions
- `concept_brain_mapping` (452 rows) -- Neuron-to-region assignment
- `neuron_activations` (realtime) -- Activation events
- `memory_consolidation_logs` (553 rows) -- Sleep session logs
- `baby_state` (1 row, stage=5) -- Current developmental state
