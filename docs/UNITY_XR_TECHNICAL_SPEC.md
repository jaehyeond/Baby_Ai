# BrainXR: Unity XR Technical Specification

**Version**: 1.0
**Date**: 2026-02-25
**Target**: Meta Quest 3 / Quest 3S, Unity 6 LTS (6000.3.9f1+)
**Paper**: ISMAR 2026 "BrainXR" submission
**Status**: Pre-implementation specification

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Unity Project Structure](#2-unity-project-structure)
3. [Data Pipeline](#3-data-pipeline)
4. [Rendering Strategy](#4-rendering-strategy)
5. [Performance Budget](#5-performance-budget)
6. [Interaction Design](#6-interaction-design)
7. [Sleep Mode Animation](#7-sleep-mode-animation)
8. [MR Passthrough Configuration](#8-mr-passthrough-configuration)
9. [Web-to-Unity Mapping Table](#9-web-to-unity-mapping-table)
10. [Data Schema (Fixed JSON for Evaluation)](#10-data-schema-fixed-json-for-evaluation)
11. [Shader Specifications](#11-shader-specifications)
12. [Build Configuration](#12-build-configuration)
13. [Risk Register](#13-risk-register)

---

## 1. Architecture Overview

### 1.1 System Topology

```
[User Conversation]
        |
        v
[Supabase Edge Functions]  <--- conversation-process EF
        |
        v
[Supabase PostgreSQL]
   |            |
   |            +---> neuron_activations (INSERT event)
   |            +---> semantic_concepts (488 rows)
   |            +---> concept_relations (616 rows)
   |            +---> brain_regions (9 rows)
   |            +---> baby_state (singleton)
   |            +---> experience_concepts (~500 rows)
   |
   +--- REST (PostgREST) ---> [Unity: Initial Data Load]
   |
   +--- WebSocket (Phoenix Channel) ---> [Unity: Realtime Activation Stream]
                                                |
                                                v
                                    [BrainDataManager (C#)]
                                         |          |
                                    [Renderers]  [XR Interaction]
                                         |          |
                                         v          v
                                    [Quest 3 Display @ 72fps]
```

Unity operates as a **read-only visualization client**. The backend (Supabase DB + Edge Functions) remains completely unchanged. No writes flow from Unity to Supabase.

### 1.2 Dual Data Strategy

The system supports two data modes to satisfy both development and evaluation needs:

| Mode | Source | Use Case |
|------|--------|----------|
| **Live Mode** | Supabase REST + WebSocket | Development, demos, real-time visualization |
| **Fixed JSON Mode** | `StreamingAssets/brain_data.json` | User study (reproducible conditions across participants) |

For the ISMAR paper user study, Fixed JSON Mode is mandatory. The dataset is frozen at: **18 concepts, 22 relations, 9 brain regions** (a curated subset of the full 488/616 production data).

### 1.3 Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Unity 6 LTS over Unity 2022 | Meta XR SDK v74+ recommends Unity 6.1+; OpenXR Meta plugin v2.1.0 requires it |
| URP over Built-in RP | Quest 3 requires URP for SRP Batcher, Multiview stereo rendering |
| SRP Batcher over GPU Instancing | URP default; avoids disabling SRP Batcher globally for other objects |
| `NativeWebSocket` over `supabase-csharp` Realtime | supabase-csharp WebSocket breaks under IL2CPP/Android AOT; NativeWebSocket is battle-tested on Quest |
| Procedural mesh over LineRenderer for synapses | 616 LineRenderers = 616 draw calls; single procedural mesh = 1 draw call |
| Icosphere (80 tris) over Unity Sphere (768 tris) | 488 neurons x 768 = 374K tris; 488 x 80 = 39K tris -- 9.6x reduction |

---

## 2. Unity Project Structure

```
BrainXR/
├── Assets/
│   ├── _Project/                          # All project-specific assets
│   │   ├── Scripts/
│   │   │   ├── Core/
│   │   │   │   ├── BrainXRManager.cs         # Top-level MonoBehaviour, lifecycle orchestrator
│   │   │   │   ├── BrainDataManager.cs       # Data loading, Fibonacci placement, clustering
│   │   │   │   ├── ActivationManager.cs      # Activation state, decay timers, spreading logic
│   │   │   │   └── DataModeController.cs     # Switches between Live/Fixed JSON modes
│   │   │   │
│   │   │   ├── Data/
│   │   │   │   ├── SupabaseRestClient.cs     # UnityWebRequest-based REST client
│   │   │   │   ├── SupabaseRealtimeClient.cs # NativeWebSocket Phoenix Channel client
│   │   │   │   ├── BrainDataModels.cs        # C# data classes (BrainRegion, Concept, etc.)
│   │   │   │   └── JsonDataLoader.cs         # Fixed JSON loader from StreamingAssets
│   │   │   │
│   │   │   ├── Rendering/
│   │   │   │   ├── NeuronRenderer.cs         # SRP Batcher instanced neuron spheres
│   │   │   │   ├── SynapseRenderer.cs        # Single procedural mesh for all connections
│   │   │   │   ├── RegionRenderer.cs         # 9 transparent URP spheres + heatmap
│   │   │   │   ├── BrainShellRenderer.cs     # Outer cortex transparent shell
│   │   │   │   ├── ActivationEffects.cs      # Emissive glow, decay, ripple ring
│   │   │   │   └── SpreadingRipple.cs        # Expanding ring effect per region
│   │   │   │
│   │   │   ├── Interaction/
│   │   │   │   ├── BrainRayInteractor.cs     # XR ray-based selection of neurons/regions
│   │   │   │   ├── InfoPanelController.cs    # World-space UI panel on selection
│   │   │   │   ├── GrabManipulator.cs        # Grab + drag brain positioning
│   │   │   │   ├── PinchZoomController.cs    # Two-hand pinch to scale brain
│   │   │   │   └── HandMenuController.cs     # Palm-up menu for mode switching
│   │   │   │
│   │   │   ├── Animation/
│   │   │   │   ├── SleepModeAnimator.cs      # 4-phase 20-second sleep animation
│   │   │   │   ├── DevelopmentStageAnimator.cs # Brain scale/density transitions
│   │   │   │   └── ThoughtFlowAnimator.cs    # 3D arrow trajectory for thought path
│   │   │   │
│   │   │   ├── UI/
│   │   │   │   ├── ThoughtProcessPanel.cs    # World-space thought flow display
│   │   │   │   ├── ConversationContextPanel.cs # Shows user/AI message context
│   │   │   │   ├── RegionLegendPanel.cs      # Active regions + heatmap legend
│   │   │   │   ├── StageInfoDisplay.cs       # Development stage badge
│   │   │   │   └── EmotionAuraController.cs  # Brain-surrounding emotion color
│   │   │   │
│   │   │   └── Utilities/
│   │   │       ├── FibonacciSphere.cs        # Ported from useBrainData.ts
│   │   │       ├── SphericalCoordinates.cs   # Ported from RealisticBrain.tsx
│   │   │       ├── LouvainClustering.cs      # Ported from useBrainData.ts
│   │   │       └── ColorUtilities.cs         # Category color mapping
│   │   │
│   │   ├── Shaders/
│   │   │   ├── NeuronGlow.shadergraph        # URP ShaderGraph: base + emissive + fresnel
│   │   │   ├── RegionTransparent.shadergraph # URP ShaderGraph: transparent + heatmap tint
│   │   │   ├── SynapseQuad.shadergraph       # Billboard quad with alpha fade
│   │   │   └── RippleRing.shadergraph        # Expanding ring with radial fade
│   │   │
│   │   ├── Materials/
│   │   │   ├── M_Neuron_Base.mat             # Shared neuron material (SRP Batcher key)
│   │   │   ├── M_Region_[0-8].mat            # Per-region transparent materials (9 total)
│   │   │   ├── M_Synapse.mat                 # Shared synapse quad material
│   │   │   ├── M_BrainShell.mat              # Outer cortex shell material
│   │   │   └── M_Ripple.mat                  # Spreading ripple ring material
│   │   │
│   │   ├── Meshes/
│   │   │   └── Icosphere_LOD0.fbx            # Custom icosphere mesh (80 tris)
│   │   │
│   │   ├── Prefabs/
│   │   │   ├── BrainXR_Root.prefab           # Top-level prefab containing full brain
│   │   │   ├── XR_InfoPanel.prefab           # World-space info panel (TextMeshPro)
│   │   │   ├── XR_HandMenu.prefab            # Palm-up hand menu
│   │   │   └── XR_ThoughtPanel.prefab        # Thought process world-space panel
│   │   │
│   │   └── Data/
│   │       └── CategoryColors.asset          # ScriptableObject: category -> Color mapping
│   │
│   ├── StreamingAssets/
│   │   └── brain_data.json                   # Fixed evaluation dataset (18c, 22r, 9br)
│   │
│   ├── XR/                                   # XR Interaction Toolkit assets (auto-created)
│   ├── Plugins/
│   │   └── link.xml                          # IL2CPP preserve rules for WebSocket, JSON
│   │
│   └── Settings/
│       ├── URP_Renderer_Quest.asset          # Quest-optimized URP renderer settings
│       └── URP_Asset_Quest.asset             # Quest URP pipeline asset
│
├── Packages/
│   └── manifest.json                         # See Section 12 for required packages
│
└── ProjectSettings/
    ├── ProjectSettings.asset                 # IL2CPP, ARM64, Vulkan
    └── QualitySettings.asset                 # Single quality level targeting Quest 3
```

### 2.1 Key Script Responsibilities

**BrainXRManager.cs** -- Top-level lifecycle orchestrator:
```csharp
public class BrainXRManager : MonoBehaviour
{
    [SerializeField] private DataModeController dataMode;
    [SerializeField] private BrainDataManager brainData;
    [SerializeField] private ActivationManager activations;
    [SerializeField] private NeuronRenderer neuronRenderer;
    [SerializeField] private SynapseRenderer synapseRenderer;
    [SerializeField] private RegionRenderer regionRenderer;

    // Lifecycle: Init -> Load -> Render -> Subscribe -> Loop
    private async void Start()
    {
        await brainData.LoadAsync(dataMode.CurrentMode);
        neuronRenderer.Initialize(brainData.Neurons);
        synapseRenderer.Initialize(brainData.Synapses, brainData.NeuronPositions);
        regionRenderer.Initialize(brainData.Regions);

        if (dataMode.CurrentMode == DataMode.Live)
        {
            activations.StartRealtimeSubscription();
        }
    }
}
```

**BrainDataManager.cs** -- Data loading and spatial computation:
```csharp
public class BrainDataManager : MonoBehaviour
{
    // Output data
    public List<ConceptData> Neurons { get; private set; }
    public List<RelationData> Synapses { get; private set; }
    public List<BrainRegionData> Regions { get; private set; }
    public Dictionary<string, Vector3> NeuronPositions { get; private set; }
    public Dictionary<string, string> NeuronToCluster { get; private set; }

    public async UniTask LoadAsync(DataMode mode)
    {
        if (mode == DataMode.FixedJSON)
            LoadFromJSON();
        else
            await LoadFromSupabase();

        ComputePositions();  // Fibonacci sphere + region placement
        ComputeClusters();   // Louvain clustering
    }

    // Port of fibonacciSphere() from useBrainData.ts
    private Vector3 FibonacciSphere(int index, int total, float radius) { ... }

    // Port of sphericalToCartesian() from RealisticBrain.tsx
    private Vector3 SphericalToCartesian(float theta, float phi, float r,
        float scaleX = 1.2f, float scaleY = 1.0f, float scaleZ = 1.1f) { ... }

    // Port of getRandomPositionInRegion() from RealisticBrain.tsx
    private Vector3 GetRandomPositionInRegion(BrainRegionData region, float jitter = 0.3f) { ... }
}
```

**ActivationManager.cs** -- Activation state and decay:
```csharp
public class ActivationManager : MonoBehaviour
{
    // Maps: regionId -> intensity (0-1)
    public Dictionary<string, float> ActiveRegions { get; private set; }
    public Dictionary<string, float> SpreadingRegions { get; private set; }
    public Dictionary<string, float> HeatmapRegions { get; private set; }

    // Maps: conceptId -> intensity (0-1)
    public Dictionary<string, float> ActiveNeurons { get; private set; }

    // Decay constants (ported from useNeuronActivations.ts)
    private const float DIRECT_DECAY_SECONDS = 3.0f;
    private const float SPREADING_DECAY_SECONDS = 5.0f;

    // Events for renderers to subscribe
    public event Action<string, float, bool> OnNeuronActivated;   // (conceptId, intensity, isSpreading)
    public event Action<string, float, bool> OnRegionActivated;   // (regionId, intensity, isSpreading)
    public event Action OnActivationsCleared;

    public void ProcessActivation(NeuronActivationData activation)
    {
        bool isSpreading = activation.trigger_type == "spreading_activation";
        float decayTime = isSpreading ? SPREADING_DECAY_SECONDS : DIRECT_DECAY_SECONDS;

        // Update region intensity (max of current and incoming)
        // Schedule decay coroutine
        // Fire events for renderers
    }

    private IEnumerator DecayCoroutine(string key, Dictionary<string, float> map, float duration)
    {
        yield return new WaitForSeconds(duration);
        map.Remove(key);
    }
}
```

---

## 3. Data Pipeline

### 3.1 Initial Load (REST API)

Six sequential HTTP requests using `UnityWebRequest` to Supabase PostgREST:

| # | Endpoint | Query | Expected Rows | Response Size |
|---|----------|-------|---------------|---------------|
| 1 | `GET /rest/v1/baby_state?select=development_stage&limit=1` | singleton | 1 | <1KB |
| 2 | `GET /rest/v1/brain_regions?select=*&order=development_stage_min` | all | 9 | ~3KB |
| 3 | `GET /rest/v1/semantic_concepts?select=id,name,category,strength,usage_count&ablation_run_id=is.null&order=usage_count.desc&limit=500` | filtered | ~488 | ~80KB |
| 4 | `GET /rest/v1/concept_relations?select=id,from_concept_id,to_concept_id,relation_type,strength,evidence_count&ablation_run_id=is.null&order=evidence_count.desc&limit=500` | filtered | ~500 | ~60KB |
| 5 | `GET /rest/v1/experience_concepts?select=experience_id,concept_id,relevance,co_activation_count&order=co_activation_count.desc&limit=500` | top 500 | ~500 | ~40KB |
| 6 | `POST /rest/v1/rpc/get_brain_activation_summary` | RPC | varies | ~20KB |

**Total initial load: ~200KB, <2 seconds on WiFi.**

Headers required:
```
Authorization: Bearer {SUPABASE_ANON_KEY}
apikey: {SUPABASE_ANON_KEY}
Content-Type: application/json
```

```csharp
// SupabaseRestClient.cs
public class SupabaseRestClient
{
    private readonly string _baseUrl;
    private readonly string _anonKey;

    public async UniTask<T> GetAsync<T>(string path, string query = "")
    {
        string url = $"{_baseUrl}/rest/v1/{path}?{query}";
        using var request = UnityWebRequest.Get(url);
        request.SetRequestHeader("Authorization", $"Bearer {_anonKey}");
        request.SetRequestHeader("apikey", _anonKey);

        await request.SendWebRequest();

        if (request.result != UnityWebRequest.Result.Success)
            throw new Exception($"Supabase REST error: {request.error}");

        return JsonConvert.DeserializeObject<T>(request.downloadHandler.text);
    }

    public async UniTask<T> RpcAsync<T>(string functionName, object body = null)
    {
        string url = $"{_baseUrl}/rest/v1/rpc/{functionName}";
        string json = body != null ? JsonConvert.SerializeObject(body) : "{}";

        using var request = new UnityWebRequest(url, "POST");
        request.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
        request.downloadHandler = new DownloadHandlerBuffer();
        request.SetRequestHeader("Authorization", $"Bearer {_anonKey}");
        request.SetRequestHeader("apikey", _anonKey);
        request.SetRequestHeader("Content-Type", "application/json");

        await request.SendWebRequest();

        if (request.result != UnityWebRequest.Result.Success)
            throw new Exception($"Supabase RPC error: {request.error}");

        return JsonConvert.DeserializeObject<T>(request.downloadHandler.text);
    }
}
```

### 3.2 Realtime Subscription (WebSocket)

Supabase Realtime uses Phoenix Channels over WebSocket. The `supabase-csharp` Realtime module has known issues with IL2CPP AOT on Android. The recommended approach is **NativeWebSocket** (`endel/NativeWebSocket`) with a manual Phoenix Channel implementation.

**Connection flow:**
```
1. Connect WSS: wss://{project}.supabase.co/realtime/v1/websocket?apikey={anon_key}&vsn=1.0.0
2. Send join: {"topic":"realtime:public:neuron_activations","event":"phx_join","payload":{"config":{"postgres_changes":[{"event":"INSERT","schema":"public","table":"neuron_activations"}]}},"ref":"1"}
3. Heartbeat every 30s: {"topic":"phoenix","event":"heartbeat","payload":{},"ref":"hb"}
4. Receive INSERT events as: {"event":"postgres_changes","payload":{"data":{"record":{...}}}}
```

```csharp
// SupabaseRealtimeClient.cs
public class SupabaseRealtimeClient : MonoBehaviour
{
    private NativeWebSocket.WebSocket _ws;
    private readonly string _url;
    private float _heartbeatTimer = 0f;
    private const float HEARTBEAT_INTERVAL = 30f;

    public event Action<NeuronActivationData> OnActivationReceived;

    public async UniTask ConnectAsync()
    {
        _ws = new NativeWebSocket.WebSocket(_url);

        _ws.OnOpen += () => { SendJoinChannel(); };
        _ws.OnMessage += (bytes) => { HandleMessage(Encoding.UTF8.GetString(bytes)); };
        _ws.OnError += (err) => { Debug.LogError($"[Realtime] Error: {err}"); };
        _ws.OnClose += (code) => { StartCoroutine(ReconnectAfterDelay(5f)); };

        await _ws.Connect();
    }

    private void Update()
    {
        _ws?.DispatchMessageQueue();  // Required by NativeWebSocket

        _heartbeatTimer += Time.deltaTime;
        if (_heartbeatTimer >= HEARTBEAT_INTERVAL)
        {
            _heartbeatTimer = 0f;
            SendHeartbeat();
        }
    }

    private void HandleMessage(string json)
    {
        var msg = JsonConvert.DeserializeObject<PhoenixMessage>(json);
        if (msg.@event == "postgres_changes")
        {
            var record = msg.payload.data.record;
            var activation = JsonConvert.DeserializeObject<NeuronActivationData>(
                JsonConvert.SerializeObject(record));
            OnActivationReceived?.Invoke(activation);
        }
    }
}
```

### 3.3 Fixed JSON Schema (Evaluation Mode)

For the user study, a frozen JSON file in `StreamingAssets/` provides deterministic data:

```json
{
  "metadata": {
    "version": "1.0",
    "frozen_at": "2026-02-25T00:00:00Z",
    "source": "production_subset"
  },
  "baby_state": {
    "development_stage": 5
  },
  "brain_regions": [
    {
      "id": "uuid-1",
      "name": "prefrontal_cortex",
      "display_name": "전두엽 피질",
      "display_name_en": "Prefrontal Cortex",
      "color": "#8b5cf6",
      "theta_min": 0.0, "theta_max": 0.6,
      "phi_min": -0.5, "phi_max": 0.5,
      "radius_min": 0.7, "radius_max": 1.0,
      "development_stage_min": 0,
      "is_internal": false,
      "description": "Planning, reasoning, executive function"
    }
  ],
  "concepts": [
    {
      "id": "concept-uuid-1",
      "name": "happiness",
      "category": "emotion",
      "strength": 0.85,
      "usage_count": 42,
      "brain_region_id": "uuid-1",
      "emotional_salience": 0.9,
      "recency": 0.7
    }
  ],
  "relations": [
    {
      "id": "rel-uuid-1",
      "from_concept_id": "concept-uuid-1",
      "to_concept_id": "concept-uuid-2",
      "relation_type": "associated",
      "strength": 0.75,
      "evidence_count": 12
    }
  ],
  "activation_replay": [
    {
      "timestamp_offset_ms": 0,
      "concept_id": "concept-uuid-1",
      "brain_region_id": "uuid-1",
      "intensity": 0.9,
      "trigger_type": "conversation"
    },
    {
      "timestamp_offset_ms": 200,
      "concept_id": "concept-uuid-3",
      "brain_region_id": "uuid-2",
      "intensity": 0.6,
      "trigger_type": "spreading_activation"
    }
  ],
  "sleep_phases": {
    "emotional_strengthening": ["concept-uuid-1", "concept-uuid-5"],
    "forgetting_curve": ["concept-uuid-8"],
    "pattern_promotion": ["concept-uuid-2", "concept-uuid-3"],
    "synaptic_pruning": ["rel-uuid-4"]
  }
}
```

### 3.4 Data Model Classes (C#)

```csharp
// BrainDataModels.cs

[System.Serializable]
public class BrainRegionData
{
    public string id;
    public string name;
    public string display_name;
    public string display_name_en;
    public string color;          // Hex color "#rrggbb"
    public float theta_min, theta_max;
    public float phi_min, phi_max;
    public float radius_min, radius_max;
    public int development_stage_min;
    public bool is_internal;
    public string description;
}

[System.Serializable]
public class ConceptData
{
    public string id;
    public string name;
    public string category;
    public float strength;
    public int usage_count;
    public string brain_region_id;    // For fixed JSON mode
    public float emotional_salience;  // For node color encoding
    public float recency;             // For node opacity encoding
}

[System.Serializable]
public class RelationData
{
    public string id;
    public string from_concept_id;
    public string to_concept_id;
    public string relation_type;
    public float strength;
    public int evidence_count;
}

[System.Serializable]
public class NeuronActivationData
{
    public string concept_id;
    public string brain_region_id;
    public float intensity;
    public string trigger_type;       // "conversation" | "spreading_activation"
    public string created_at;
    public string experience_id;
}

// Development stage scaling (ported from useBrainRegions.ts STAGE_PARAMS)
public static class DevelopmentStageParams
{
    public static readonly Dictionary<int, (float scale, float synapseDensity, string label)> Stages =
        new()
        {
            { 0, (0.25f, 0.30f, "NEWBORN") },
            { 1, (0.48f, 0.60f, "INFANT") },
            { 2, (0.65f, 0.85f, "BABY") },
            { 3, (0.80f, 1.00f, "TODDLER") },
            { 4, (0.90f, 0.70f, "CHILD") },
            { 5, (0.95f, 0.55f, "TEEN") },
            { 6, (0.98f, 0.45f, "YOUNG_ADULT") },
            { 7, (1.00f, 0.40f, "MATURE") },
        };
}
```

---

## 4. Rendering Strategy

### 4.1 URP Configuration

**URP Renderer Settings (Quest-optimized):**

| Setting | Value | Rationale |
|---------|-------|-----------|
| Render Scale | 0.9 (adjustable at runtime) | 10% pixel reduction saves significant GPU; barely noticeable in MR |
| MSAA | 4x | Required for Quest VR clarity, especially wireframe/transparent |
| HDR | OFF | Quest GPU does not benefit; saves bandwidth |
| Post-processing | OFF | Bloom via emissive materials instead (cheaper) |
| Shadows | Disabled globally | Brain visualization has no shadow-casting objects |
| Depth Texture | ON | Required for OpenXR passthrough composition |
| Opaque Texture | OFF | Not needed |
| SRP Batcher | ON (default) | Key to batching 488 neuron draw calls |
| Stereo Rendering | Multiview | Single-pass for both eyes; required for Quest 72fps |

### 4.2 Neuron Rendering (488 Concepts)

**Strategy: SRP Batcher with shared material + MaterialPropertyBlock per neuron.**

All 488 neurons use the same `M_Neuron_Base` material (same shader variant). Per-neuron visual variation is achieved through `MaterialPropertyBlock`:

```csharp
// NeuronRenderer.cs
public class NeuronRenderer : MonoBehaviour
{
    [SerializeField] private Mesh icosphereMesh;      // 80 tris icosphere
    [SerializeField] private Material neuronMaterial;  // Shared URP/Lit-based

    private Matrix4x4[] _matrices;
    private MaterialPropertyBlock[] _propertyBlocks;
    private Vector4[] _colors;
    private float[] _emissionIntensities;

    // Pre-allocated arrays for Graphics.DrawMeshInstanced
    // Maximum batch size for DrawMeshInstanced is 1023
    private const int MAX_BATCH = 1023;

    public void Initialize(List<ConceptData> neurons)
    {
        int count = neurons.Count;
        _matrices = new Matrix4x4[count];
        _propertyBlocks = new MaterialPropertyBlock[count];

        for (int i = 0; i < count; i++)
        {
            var concept = neurons[i];
            float size = 0.008f + concept.strength * 0.012f; // Ported from web: 0.08-0.2 scaled to meters

            Vector3 pos = _brainData.NeuronPositions[concept.id];
            _matrices[i] = Matrix4x4.TRS(pos, Quaternion.identity, Vector3.one * size);

            _propertyBlocks[i] = new MaterialPropertyBlock();
            Color color = ColorUtilities.GetCategoryColor(concept.category);
            _propertyBlocks[i].SetColor("_BaseColor", color);
            _propertyBlocks[i].SetColor("_EmissionColor", color * 0.1f);

            // Paper requirement: size=strength, color=emotional_salience, opacity=recency
            float opacity = 0.5f + concept.recency * 0.5f;
            _propertyBlocks[i].SetFloat("_Alpha", opacity);
        }
    }

    // Called by ActivationManager when a neuron activates
    public void SetNeuronGlow(int index, float intensity, bool isSpreading)
    {
        Color baseColor = ColorUtilities.GetCategoryColor(_neurons[index].category);
        Color emissive = isSpreading
            ? new Color(0.96f, 0.62f, 0.04f) * intensity * 2f  // Amber #f59e0b
            : baseColor * intensity * 2f;

        _propertyBlocks[index].SetColor("_EmissionColor", emissive);
    }

    private void Update()
    {
        // Render all neurons using DrawMeshInstanced (batched)
        int remaining = _matrices.Length;
        int offset = 0;
        while (remaining > 0)
        {
            int batchSize = Mathf.Min(remaining, MAX_BATCH);
            var batchMatrices = new ArraySegment<Matrix4x4>(_matrices, offset, batchSize);
            // Note: DrawMeshInstanced with MaterialPropertyBlock array not supported;
            // use individual DrawMesh calls batched by SRP Batcher instead
            for (int i = offset; i < offset + batchSize; i++)
            {
                Graphics.DrawMesh(icosphereMesh, _matrices[i], neuronMaterial, 0, null, 0, _propertyBlocks[i]);
            }
            offset += batchSize;
            remaining -= batchSize;
        }
    }
}
```

**Alternative approach (if SRP Batcher proves insufficient):** Use a ComputeBuffer with `Graphics.DrawMeshInstancedIndirect` for true GPU instancing, passing per-neuron data (color, emission, size) via a StructuredBuffer.

### 4.3 Synapse Rendering (616 Relations)

**Strategy: Single procedural mesh with billboard quads.**

Each synapse is a camera-facing quad strip connecting two neuron positions. All 616 connections are merged into a single mesh, yielding 1 draw call.

```csharp
// SynapseRenderer.cs
public class SynapseRenderer : MonoBehaviour
{
    [SerializeField] private Material synapseMaterial;

    private Mesh _synapseMesh;
    private Vector3[] _vertices;
    private int[] _triangles;
    private Color[] _colors;

    // Each connection = 4 vertices (quad), 2 triangles
    // 616 connections = 2464 vertices, 1232 triangles (3696 indices)
    private const float QUAD_WIDTH = 0.002f; // 2mm width in world space

    public void Initialize(List<RelationData> synapses, Dictionary<string, Vector3> positions)
    {
        int count = synapses.Count;
        _vertices = new Vector3[count * 4];
        _triangles = new int[count * 6];
        _colors = new Color[count * 4];

        for (int i = 0; i < count; i++)
        {
            var rel = synapses[i];
            if (!positions.TryGetValue(rel.from_concept_id, out Vector3 from)) continue;
            if (!positions.TryGetValue(rel.to_concept_id, out Vector3 to)) continue;

            BuildQuad(i, from, to, rel.strength);
        }

        _synapseMesh = new Mesh();
        _synapseMesh.vertices = _vertices;
        _synapseMesh.triangles = _triangles;
        _synapseMesh.colors = _colors;
        _synapseMesh.RecalculateBounds();

        GetComponent<MeshFilter>().mesh = _synapseMesh;
    }

    private void BuildQuad(int index, Vector3 from, Vector3 to, float strength)
    {
        // Direction and perpendicular for billboard effect
        Vector3 dir = (to - from).normalized;
        Vector3 perp = Vector3.Cross(dir, Camera.main.transform.forward).normalized * QUAD_WIDTH;

        int vi = index * 4;
        _vertices[vi + 0] = from - perp;
        _vertices[vi + 1] = from + perp;
        _vertices[vi + 2] = to + perp;
        _vertices[vi + 3] = to - perp;

        int ti = index * 6;
        _triangles[ti + 0] = vi;
        _triangles[ti + 1] = vi + 1;
        _triangles[ti + 2] = vi + 2;
        _triangles[ti + 3] = vi;
        _triangles[ti + 4] = vi + 2;
        _triangles[ti + 5] = vi + 3;

        // Opacity based on strength (ported from web: 0.1 + strength * 0.2)
        float alpha = 0.1f + strength * 0.2f;
        Color c = new Color(0.278f, 0.333f, 0.412f, alpha); // slate-500 #475569
        _colors[vi] = _colors[vi + 1] = _colors[vi + 2] = _colors[vi + 3] = c;
    }

    // Called per-frame to orient quads toward camera (billboard effect)
    private void LateUpdate()
    {
        // Rebuild perpendicular vectors based on current camera direction
        // Only needed if camera moves significantly (threshold check)
    }
}
```

### 4.4 Brain Region Rendering (9 Regions)

Each region is a separate transparent sphere with URP material:

```csharp
// RegionRenderer.cs
public class RegionRenderer : MonoBehaviour
{
    [SerializeField] private Material regionMaterialTemplate;
    [SerializeField] private Mesh sphereMesh;  // Standard sphere (768 tris OK for 9 objects)

    private GameObject[] _regionObjects;
    private MaterialPropertyBlock[] _propertyBlocks;

    public void Initialize(List<BrainRegionData> regions)
    {
        _regionObjects = new GameObject[regions.Count];

        for (int i = 0; i < regions.Count; i++)
        {
            var region = regions[i];
            var go = new GameObject($"Region_{region.name}");
            go.transform.SetParent(transform);

            // Position: spherical to cartesian (ported from RealisticBrain.tsx getRegionCenter)
            float thetaMid = (region.theta_min + region.theta_max) / 2f;
            float phiMid = (region.phi_min + region.phi_max) / 2f;
            float rMid = (region.radius_min + region.radius_max) / 2f;
            go.transform.localPosition = SphericalCoordinates.ToCartesian(thetaMid, phiMid, rMid * 4f);

            var filter = go.AddComponent<MeshFilter>();
            filter.mesh = sphereMesh;
            var renderer = go.AddComponent<MeshRenderer>();
            renderer.material = new Material(regionMaterialTemplate);

            Color regionColor = ColorUtility.TryParseHtmlString(region.color, out Color c) ? c : Color.white;
            renderer.material.SetColor("_BaseColor", new Color(regionColor.r, regionColor.g, regionColor.b, 0.45f));
            renderer.material.SetFloat("_Surface", 1); // Transparent
            renderer.material.renderQueue = 3000;       // Transparent queue

            _regionObjects[i] = go;
        }
    }

    // Heatmap: tint region color toward warm (red/orange) based on cumulative activation
    public void SetHeatmapIntensity(int regionIndex, float normalizedIntensity)
    {
        // Lerp from region base color to warm orange based on intensity
        Color baseColor = _baseColors[regionIndex];
        Color warm = new Color(1f, 0.5f, 0.1f); // Warm orange
        Color result = Color.Lerp(baseColor, warm, normalizedIntensity * 0.6f);
        result.a = 0.2f + normalizedIntensity * 0.3f;

        var renderer = _regionObjects[regionIndex].GetComponent<MeshRenderer>();
        renderer.material.SetColor("_BaseColor", result);
        renderer.material.SetColor("_EmissionColor", result * normalizedIntensity * 0.3f);
    }
}
```

### 4.5 Brain Shell (Outer Cortex)

Ported from `BrainShell` in RealisticBrain.tsx. A single large transparent sphere with subtle breathing animation:

```csharp
// BrainShellRenderer.cs
public class BrainShellRenderer : MonoBehaviour
{
    [SerializeField] private float breathSpeed = 0.5f;
    [SerializeField] private float breathAmplitude = 0.01f;
    [SerializeField] private Color shellColor = new Color(0.545f, 0.361f, 0.965f, 0.06f); // #8b5cf6 @ 6%

    private float _baseScale;

    private void Update()
    {
        float breath = Mathf.Sin(Time.time * breathSpeed) * breathAmplitude;
        float s = (_baseScale + breath);
        transform.localScale = new Vector3(
            s * 1.2f,  // Ellipsoid X
            s * 1.0f,  // Ellipsoid Y
            s * 1.1f   // Ellipsoid Z
        );
    }
}
```

---

## 5. Performance Budget

### 5.1 Quest 3 Hardware Constraints

| Constraint | Value | Source |
|------------|-------|--------|
| Target framerate | 72 fps (13.9ms/frame) | Meta Quest 3 default |
| GPU frame budget | ~8ms (after OS overhead) | Meta performance guidelines |
| Draw call budget | <100 | Meta recommendation for sustained 72fps |
| Triangle budget | 750K-1M | Meta recommendation |
| Thermal throttle threshold | 5-7 minutes at full GPU | Empirical; triggers downclocking |
| RAM available | ~3.5GB (of 8GB total) | After OS and Guardian |

### 5.2 Projected Resource Usage

| Component | Draw Calls | Triangles | GPU Time (est.) |
|-----------|-----------|-----------|-----------------|
| 488 neuron icospheres (SRP Batcher) | 1-5 (batched) | 39,040 (488 x 80) | ~1.0ms |
| 616 synapse quads (single mesh) | 1 | 1,232 | ~0.2ms |
| 9 brain region spheres | 9 | 6,912 (9 x 768) | ~0.3ms |
| 1 brain shell | 1 | 768 | ~0.1ms |
| Spreading ripple rings (max 9) | 0-9 | 0-2,880 | ~0.2ms |
| UI panels (TextMeshPro, world-space) | 5-10 | ~5,000 | ~0.5ms |
| **Total** | **~17-35** | **~55,000** | **~2.3ms** |

**Budget utilization: ~29% of GPU frame budget, ~5% of draw call budget, ~7% of triangle budget.**

This leaves substantial headroom for:
- MR passthrough composition overhead (~2-3ms)
- XR Interaction Toolkit processing (~0.5ms)
- Hand tracking processing (~1ms)

### 5.3 LOD Strategy

Given the generous budget headroom, a formal LOD system is not required for the initial implementation. However, the following fallback strategy is prepared if thermal throttling is observed:

| LOD Level | Trigger | Action |
|-----------|---------|--------|
| LOD 0 (Full) | Default | All 488 neurons, 616 synapses, 9 regions |
| LOD 1 (Reduced) | Sustained >11ms GPU | Reduce neuron count to 200 (top by usage_count), reduce synapse count to 300 |
| LOD 2 (Minimal) | Sustained >13ms GPU | Neurons as point particles (Billboard shader), disable synapse quads, reduce region sphere segments |

LOD transitions should use `Application.targetFrameRate` monitoring:
```csharp
if (1f / Time.smoothDeltaTime < 68f)  // Below 72fps with 4fps margin
    DowngradeLOD();
```

### 5.4 Memory Budget

| Asset | Size |
|-------|------|
| 488 icosphere meshes (shared, instanced) | ~50KB (single mesh reference) |
| 1 synapse procedural mesh | ~120KB (2464 verts x 48 bytes) |
| Material instances (9 regions + shared) | ~20KB |
| Brain data in memory (C# objects) | ~200KB |
| Textures (minimal, procedural colors) | ~1MB |
| **Total application memory** | **~1.5MB** (excluding Unity/XR overhead) |

---

## 6. Interaction Design

### 6.1 XR Interaction Toolkit Setup

**Required packages:**
- `com.unity.xr.interaction.toolkit` (v3.0+)
- `com.unity.xr.hands` (v1.5+)

**XR Rig hierarchy:**
```
XR Origin (XR Rig)
├── Camera Offset
│   ├── Main Camera (tracked)
│   ├── Left Hand (XR Hand Tracking)
│   │   └── XR Ray Interactor
│   └── Right Hand (XR Hand Tracking)
│       └── XR Ray Interactor
├── Left Controller (fallback)
│   └── XR Ray Interactor
└── Right Controller (fallback)
```

### 6.2 Interaction Mapping

| Gesture / Input | Action | Implementation |
|----------------|--------|----------------|
| **Point + Air Tap** | Select neuron/region | XR Ray Interactor + XR Simple Interactable on each region collider; neurons use layer-based raycast with custom hit detection |
| **Pinch Zoom** (two hands) | Scale brain model | Custom `PinchZoomController`: track distance between thumb+index tips of both hands; map delta to `transform.localScale` |
| **Grab + Drag** (one hand grab) | Move brain position | XR Grab Interactable on brain root object; constrained to horizontal plane (Y-axis locked) |
| **Palm-up menu** | Toggle modes (live/sleep/heatmap) | `HandMenuController`: detect left palm facing up (dot product of palm normal vs up > 0.7); show/hide radial menu |
| **Gaze + dwell** | Fallback selection (accessibility) | XR Gaze Interactor with 1.5s dwell timer |

### 6.3 Ray-Based Selection Details

Neurons are small (8-20mm in world space). Direct raycasting against 488 sphere colliders would be expensive. Instead:

```csharp
// BrainRayInteractor.cs
public class BrainRayInteractor : MonoBehaviour
{
    [SerializeField] private float selectionRadius = 0.05f; // 5cm proximity threshold
    [SerializeField] private LayerMask regionLayer;          // Only regions have colliders

    private void OnRayHit(RaycastHit hit)
    {
        // Step 1: Check if a region was hit directly
        if (hit.collider.TryGetComponent<RegionInteractable>(out var region))
        {
            ShowRegionInfo(region.Data);
            return;
        }

        // Step 2: Find nearest neuron to ray hit point (spatial query)
        string nearestNeuronId = _brainData.FindNearestNeuron(hit.point, selectionRadius);
        if (nearestNeuronId != null)
        {
            ShowNeuronInfo(nearestNeuronId);
        }
    }
}
```

**Spatial indexing:** For 488 neurons, a simple brute-force distance check per frame is acceptable (~488 distance calculations = negligible CPU). If performance becomes an issue, partition neurons into an octree.

### 6.4 Info Panel (World-Space UI)

When a neuron or region is selected, a world-space Canvas panel appears near the selected object:

```
+----------------------------------+
| [Neuron Name]        [Category]  |
|                                  |
| Strength: ████████░░ 85%         |
| Usage:    42 times               |
| Connections: 7                   |
| Region: Prefrontal Cortex        |
|                                  |
| [Emotional Salience: High]       |
| [Last Active: 2m ago]            |
+----------------------------------+
```

Implementation: TextMeshPro on a world-space Canvas, billboarded toward the user camera, positioned 0.15m above the selected object. Use DOTween for fade-in animation (0.2s).

### 6.5 Grab Manipulation Constraints

```csharp
// GrabManipulator.cs
[RequireComponent(typeof(XRGrabInteractable))]
public class GrabManipulator : MonoBehaviour
{
    [SerializeField] private float minScale = 0.3f;
    [SerializeField] private float maxScale = 3.0f;
    [SerializeField] private float rotationSpeed = 1.0f;

    // Constrain grab to prevent brain from going through floor/walls
    private void OnGrabbed()
    {
        // Lock Y minimum to table height (detected via passthrough scene mesh)
        // Enable rotation on all axes
        // Disable physics (kinematic)
    }
}
```

---

## 7. Sleep Mode Animation

### 7.1 Overview

The sleep mode visualizes memory consolidation as a 20-second choreographed animation with 4 phases. This mirrors the backend's `useIdleSleep.ts` 4-phase process (memory consolidation, curiosity generation, exploration, imagination).

### 7.2 Phase Timeline

```
Time:  0s────5s────10s────15s────20s
Phase: |--1--|--2---|---3---|--4--|

Phase 1 (0-5s):   Emotional Strengthening
Phase 2 (5-10s):  Forgetting Curve (Decay)
Phase 3 (10-15s): Pattern Promotion (Synaptic Consolidation)
Phase 4 (15-20s): Synaptic Pruning
```

### 7.3 Phase Specifications

#### Phase 1: Emotional Strengthening (0-5s)

Emotionally salient neurons glow brighter, pulse, and grow slightly.

| Property | Start | End | Easing |
|----------|-------|-----|--------|
| Target neurons | emotional_salience > 0.6 | -- | -- |
| Emission intensity | current | current * 3.0 | EaseInOutSine (pulse 2 cycles) |
| Scale | current | current * 1.3 | EaseOutElastic |
| Connected synapse alpha | current | current * 2.0 | EaseInOutQuad |
| Region glow (containing region) | 0 | 0.4 | EaseInOutSine |
| Warm aura (brain shell) | transparent | warm amber (0.15 alpha) | EaseIn |

```csharp
// Phase 1 implementation
private IEnumerator Phase1_EmotionalStrengthening()
{
    var emotionalNeurons = _concepts.Where(c => c.emotional_salience > 0.6f).ToList();

    // Dim all non-emotional neurons
    foreach (var n in _allNeurons.Except(emotionalNeurons))
        DOTween.To(() => GetNeuronAlpha(n), v => SetNeuronAlpha(n, v), 0.15f, 1f);

    // Pulse emotional neurons
    foreach (var n in emotionalNeurons)
    {
        DOTween.To(() => GetEmission(n), v => SetEmission(n, v), 3f, 1.5f)
            .SetLoops(2, LoopType.Yoyo)
            .SetEase(Ease.InOutSine);

        DOTween.To(() => GetScale(n), v => SetScale(n, v), 1.3f, 2f)
            .SetEase(Ease.OutElastic);
    }

    // Warm aura on brain shell
    DOTween.To(() => _shellMaterial.GetFloat("_Alpha"), v => _shellMaterial.SetFloat("_Alpha", v),
        0.15f, 2f).SetEase(Ease.InQuad);
    _shellMaterial.SetColor("_BaseColor", new Color(0.96f, 0.62f, 0.04f, 0.15f)); // Amber

    yield return new WaitForSeconds(5f);
}
```

#### Phase 2: Forgetting Curve (5-10s)

Low-recency, low-usage neurons fade out and shrink. Represents Ebbinghaus forgetting curve decay.

| Property | Start | End | Easing |
|----------|-------|-----|--------|
| Target neurons | recency < 0.3 AND usage_count < 5 | -- | -- |
| Alpha | current | 0.05 | EaseInExpo (fast fade) |
| Scale | current | current * 0.3 | EaseInBack |
| Color | current | desaturated gray | EaseInOutQuad |
| Connected synapses | current alpha | 0.02 | EaseInExpo |
| Particle effect | none | small grey particles drifting away | -- |

```csharp
// Phase 2 implementation
private IEnumerator Phase2_ForgettingCurve()
{
    var forgettingNeurons = _concepts.Where(c => c.recency < 0.3f && c.usage_count < 5).ToList();

    foreach (var n in forgettingNeurons)
    {
        // Fade out
        DOTween.To(() => GetNeuronAlpha(n), v => SetNeuronAlpha(n, v), 0.05f, 3f)
            .SetEase(Ease.InExpo);

        // Shrink
        DOTween.To(() => GetScale(n), v => SetScale(n, v), 0.3f, 3f)
            .SetEase(Ease.InBack);

        // Desaturate
        Color grey = new Color(0.4f, 0.4f, 0.4f, 0.05f);
        DOTween.To(() => GetColor(n), v => SetColor(n, v), grey, 2f);

        // Particle burst (small dust particles)
        EmitForgetParticles(GetPosition(n), 5);
    }

    yield return new WaitForSeconds(5f);
}
```

#### Phase 3: Pattern Promotion (10-15s)

High-co-occurrence synapses brighten and thicken. Represents synaptic consolidation (long-term potentiation).

| Property | Start | End | Easing |
|----------|-------|-----|--------|
| Target synapses | evidence_count > median | -- | -- |
| Synapse alpha | current | 0.8 | EaseOutQuad |
| Synapse width | current | current * 2.5 | EaseOutElastic |
| Synapse color | slate gray | violet (#8b5cf6) | EaseInOutQuad |
| Connected neuron emission | current | +0.5 | EaseInOutSine |
| Ripple wave | -- | emanates from strongest cluster center | -- |

#### Phase 4: Synaptic Pruning (15-20s)

Weakest synapses (low strength, low evidence) dissolve. Represents developmental pruning.

| Property | Start | End | Easing |
|----------|-------|-----|--------|
| Target synapses | strength < 0.2 AND evidence_count < 3 | -- | -- |
| Synapse alpha | current | 0.0 | EaseInExpo |
| Synapse vertex positions | straight line | sag downward (gravity) | EaseInQuad |
| Break particles | none | small spark at midpoint | -- |
| Brain shell | warm amber | return to base violet (0.06) | EaseOutQuad |

### 7.4 Sleep Animation Controller

```csharp
// SleepModeAnimator.cs
public class SleepModeAnimator : MonoBehaviour
{
    [SerializeField] private float totalDuration = 20f;
    [SerializeField] private NeuronRenderer neuronRenderer;
    [SerializeField] private SynapseRenderer synapseRenderer;
    [SerializeField] private RegionRenderer regionRenderer;
    [SerializeField] private BrainShellRenderer shellRenderer;

    private Coroutine _sleepCoroutine;
    private bool _isPlaying = false;

    public bool IsPlaying => _isPlaying;
    public float Progress { get; private set; } // 0-1

    public event Action OnSleepStarted;
    public event Action OnSleepCompleted;
    public event Action<int> OnPhaseChanged; // 1-4

    public void StartSleepAnimation()
    {
        if (_isPlaying) return;
        _sleepCoroutine = StartCoroutine(SleepSequence());
    }

    public void StopSleepAnimation()
    {
        if (_sleepCoroutine != null)
        {
            StopCoroutine(_sleepCoroutine);
            DOTween.KillAll();
            ResetAllVisuals();
        }
        _isPlaying = false;
    }

    private IEnumerator SleepSequence()
    {
        _isPlaying = true;
        OnSleepStarted?.Invoke();

        // Phase 1: Emotional Strengthening (0-5s)
        OnPhaseChanged?.Invoke(1);
        yield return Phase1_EmotionalStrengthening();

        // Phase 2: Forgetting Curve (5-10s)
        OnPhaseChanged?.Invoke(2);
        yield return Phase2_ForgettingCurve();

        // Phase 3: Pattern Promotion (10-15s)
        OnPhaseChanged?.Invoke(3);
        yield return Phase3_PatternPromotion();

        // Phase 4: Synaptic Pruning (15-20s)
        OnPhaseChanged?.Invoke(4);
        yield return Phase4_SynapticPruning();

        // Reset to normal state
        yield return ResetWithFade(2f);

        _isPlaying = false;
        OnSleepCompleted?.Invoke();
    }
}
```

### 7.5 DOTween Configuration

```csharp
// In BrainXRManager.Start()
DOTween.SetTweensCapacity(500, 100); // 500 tweeners, 100 sequences
DOTween.defaultAutoPlay = AutoPlay.None;
DOTween.defaultRecyclable = true;  // Reduce GC pressure on Quest
```

---

## 8. MR Passthrough Configuration

### 8.1 OpenXR Meta Passthrough Setup

**Package:** `com.unity.xr.meta-openxr` v2.1.0+

**Required OpenXR Features (enabled in Project Settings > XR Plug-in Management > OpenXR):**

| Feature | Class | Purpose |
|---------|-------|---------|
| Meta Quest Feature | `MetaQuestFeature` | Base Quest support |
| Meta Quest Passthrough | `MetaQuestPassthroughFeature` | Color passthrough |
| Hand Tracking Subsystem | `HandTracking` | 25-joint hand skeleton |

### 8.2 Scene Setup for Passthrough

```csharp
// PassthroughSetup.cs -- attach to XR Origin
public class PassthroughSetup : MonoBehaviour
{
    private void Start()
    {
        // 1. Set camera clear to solid black (passthrough composites on black)
        Camera.main.clearFlags = CameraClearFlags.SolidColor;
        Camera.main.backgroundColor = Color.clear;

        // 2. Enable passthrough via OpenXR
        // The Meta Quest Passthrough Feature handles this automatically
        // when enabled in OpenXR settings

        // 3. Set environment blend mode to alpha blend
        // This allows virtual objects to composite over passthrough
        var xrDisplay = XRGeneralSettings.Instance?.Manager?.activeLoader?
            .GetLoadedSubsystem<XRDisplaySubsystem>();
        if (xrDisplay != null)
        {
            xrDisplay.TrySetEnvironmentBlendMode(XRDisplaySubsystem.EnvironmentBlendMode.AlphaBlend);
        }
    }
}
```

### 8.3 URP Passthrough Compatibility

For passthrough to work correctly with URP transparent materials:

1. **Camera background type**: Set to "Uninitialized" or "Solid Color" with alpha = 0
2. **URP Renderer**: Add the "Meta Quest Background Renderer Feature" (from `com.unity.xr.meta-openxr`)
3. **Material render queue**: Brain objects use Transparent queue (3000+)
4. **Depth write**: Ensure transparent brain materials have depth write OFF so passthrough shows through gaps

### 8.4 Spatial Anchoring

Place the brain at a fixed position relative to the user's initial head position, or anchor to a detected surface:

```csharp
// SpatialAnchorManager.cs
public class SpatialAnchorManager : MonoBehaviour
{
    [SerializeField] private Transform brainRoot;
    [SerializeField] private float defaultDistance = 0.8f;  // 80cm in front
    [SerializeField] private float defaultHeight = -0.3f;   // 30cm below eye level (table height)

    public void PlaceBrainAtDefault()
    {
        // Place brain in front of user at table height
        Vector3 headPos = Camera.main.transform.position;
        Vector3 headForward = Camera.main.transform.forward;
        headForward.y = 0; // Flatten to horizontal
        headForward.Normalize();

        brainRoot.position = headPos + headForward * defaultDistance + Vector3.up * defaultHeight;
        brainRoot.rotation = Quaternion.LookRotation(-headForward, Vector3.up);
    }

    // Alternative: use Meta Scene API for table detection
    // Requires room setup and scene mesh
}
```

### 8.5 Passthrough-Aware Rendering

The brain should appear as a holographic object floating in real space. Key visual considerations:

- **No skybox**: Camera clears to transparent
- **Ambient light**: Match to approximate room lighting (or use passthrough light estimation if available)
- **Object shadows**: Disabled (no ground plane shadow -- brain floats)
- **Transparency**: Brain shell at 6% opacity blends naturally with passthrough
- **Bloom substitute**: Emissive materials provide glow without post-processing

---

## 9. Web-to-Unity Mapping Table

### 9.1 Components

| Web (React/Three.js) | Unity (C#/URP) | Notes |
|---|---|---|
| `RealisticBrain.tsx` (775 lines) | `BrainXRManager.cs` + `NeuronRenderer.cs` + `RegionRenderer.cs` | Split into separate concerns |
| `BrainVisualization.tsx` (709 lines) | Same renderers (mode toggle in `DataModeController`) | Abstract view uses same renderers with different positioning |
| `useNeuronActivations.ts` (325 lines) | `ActivationManager.cs` + `SupabaseRealtimeClient.cs` | Hook -> MonoBehaviour; state -> dictionaries |
| `useBrainRegions.ts` (81 lines) | `BrainDataManager.cs` (region loading portion) | Embedded in data manager |
| `useBrainData.ts` (477 lines) | `BrainDataManager.cs` + `FibonacciSphere.cs` + `LouvainClustering.cs` | Split utilities into separate files |
| `BrainShell` component | `BrainShellRenderer.cs` | Direct port, breathing animation |
| `SpreadingRipple` component | `SpreadingRipple.cs` + `RippleRing.shadergraph` | Ring geometry + shader-driven fade |
| `BrainRegionMesh` component | `RegionRenderer.cs` | MaterialPropertyBlock for dynamic glow |
| `RegionNeurons` component | `NeuronRenderer.cs` | Merged into single instanced renderer |
| `RegionConnections` component | `SynapseRenderer.cs` | Single procedural mesh |
| `ThoughtProcessPanel` component | `ThoughtProcessPanel.cs` (world-space Canvas) | HTML/CSS -> TextMeshPro |
| `NeuronInfoPanel` component | `InfoPanelController.cs` (world-space Canvas) | Same data, XR-friendly layout |
| `Neuron` component (click/hover) | `BrainRayInteractor.cs` | Mouse events -> XR ray interactor |
| `OrbitControls` | `GrabManipulator.cs` + `PinchZoomController.cs` | Drei controls -> XR hand-based manipulation |
| `Canvas` (R3F) | Unity Camera (XR tracked) | Automatic with OpenXR |
| `useIdleSleep.ts` (353 lines) | `SleepModeAnimator.cs` | Logic stays server-side; Unity only animates |
| `MemoryConsolidationCard.tsx` | N/A | Not needed in XR (sleep is visual-only) |

### 9.2 Rendering Techniques

| Web Technique | Unity Equivalent |
|---|---|
| `meshStandardMaterial` (emissive) | URP/Lit shader with Emission channel |
| `meshBasicMaterial` (transparent) | URP/Unlit shader, Surface Type: Transparent |
| `BufferGeometry.setFromPoints` (lines) | Procedural `Mesh` with billboard quads |
| `Html` (drei, tooltip overlays) | World-space `Canvas` + `TextMeshPro` |
| `Text` (drei, 3D labels) | `TextMeshPro` - 3D Text |
| `useFrame` (per-frame animation) | `Update()` / `LateUpdate()` |
| `useRef<THREE.Mesh>` | `[SerializeField] MeshRenderer` or direct reference |
| `useMemo` (memoized computation) | Computed once in `Initialize()`, cached in fields |
| `useState` + `useEffect` | C# properties + `Start()` / event subscriptions |
| CSS `backdrop-blur` | N/A in XR (world-space panels use semi-transparent background) |
| Framer Motion animations | DOTween sequences |
| `THREE.DoubleSide` | URP material: Render Face = Both |
| `depthWrite: false` | URP material: ZWrite Off (in ShaderGraph) |

### 9.3 Coordinate System

| Axis | Web (Three.js) | Unity | Conversion |
|------|----------------|-------|------------|
| Right | +X | +X | Same |
| Up | +Y | +Y | Same |
| Forward | -Z (into screen) | +Z (into screen) | Negate Z |
| Rotation | Radians, CCW | Degrees internally, Quaternion API | `Mathf.Rad2Deg` |

**Scale factor:** Web uses arbitrary units (sphere radius 4, scene ~20 units across). Unity uses meters. Apply a global scale factor:

```
Unity meters = Web units * 0.1
```

This maps the web brain (~8 unit diameter) to a ~0.8m diameter brain in XR -- a comfortable size for table-top viewing.

### 9.4 Color Mapping (Category Colors)

Ported directly from `CATEGORY_COLORS` in `useBrainData.ts`:

```csharp
// ColorUtilities.cs
public static class ColorUtilities
{
    private static readonly Dictionary<string, Color> CategoryColors = new()
    {
        { "frozen_knowledge", HexToColor("#64748b") },
        { "learned",          HexToColor("#d946ef") },
        { "emotion",          HexToColor("#f97316") },
        { "person",           HexToColor("#14b8a6") },
        { "abstract concept", HexToColor("#3b82f6") },
        { "action",           HexToColor("#22c55e") },
        { "identity",         HexToColor("#fbbf24") },
        { "thing",            HexToColor("#a855f7") },
        { "location",         HexToColor("#10b981") },
        { "communication",    HexToColor("#ec4899") },
        { "default",          HexToColor("#6366f1") },
    };

    // Korean aliases (same as web implementation)
    private static readonly Dictionary<string, string> Aliases = new()
    {
        { "감정", "emotion" }, { "관계", "person" }, { "사람", "person" },
        { "인물", "person" }, { "추상적 개념", "abstract concept" },
        { "인지", "abstract concept" }, { "행위", "action" }, { "활동", "action" },
        { "행동", "action" }, { "이름", "identity" }, { "사물", "thing" },
        { "물체", "thing" }, { "장소", "location" }, { "지리", "location" },
        { "인사말", "communication" },
    };

    public static Color GetCategoryColor(string category)
    {
        if (CategoryColors.TryGetValue(category, out Color c)) return c;
        if (Aliases.TryGetValue(category, out string alias))
            if (CategoryColors.TryGetValue(alias, out Color ac)) return ac;
        return CategoryColors["default"];
    }
}
```

---

## 10. Data Schema (Fixed JSON for Evaluation)

### 10.1 Curated Subset Selection Criteria

The full production database (488 concepts, 616 relations) is reduced to a **18-concept, 22-relation** subset for the user study. Selection criteria:

1. **Coverage**: At least 2 concepts per brain region (ensures all 9 regions are visually active)
2. **Diversity**: Mix of categories (emotion, person, action, abstract, identity)
3. **Connectivity**: Selected concepts must form a connected graph (no isolated nodes)
4. **Activation patterns**: Include concepts that are part of known spreading activation paths
5. **Salience range**: Include both high and low emotional salience concepts

### 10.2 Activation Replay Sequences

For each user study task, a pre-recorded activation sequence is included:

| Task | Sequence | Duration | Concepts Activated |
|------|----------|----------|-------------------|
| T1: Region identification | Strong prefrontal activation | 5s | 4 concepts in 1 region |
| T2: Path tracing | 3-hop spreading activation | 8s | 6 concepts across 3 regions |
| T3: Pattern comparison | Two different conversations | 2x 6s | 8 concepts each, overlapping |
| T4: Development estimation | Stage-gated region visibility | static | All 18 concepts |

---

## 11. Shader Specifications

### 11.1 NeuronGlow.shadergraph

**Type:** URP Lit ShaderGraph
**Surface:** Transparent
**Blend:** Alpha

| Property | Type | Range | Description |
|----------|------|-------|-------------|
| `_BaseColor` | Color | -- | Category-based color |
| `_EmissionColor` | Color | -- | Activation glow color |
| `_EmissionIntensity` | Float | 0-5 | Activation intensity multiplier |
| `_Alpha` | Float | 0-1 | Recency-based opacity |
| `_FresnelPower` | Float | 1-5 | Edge glow effect (default 3) |

**Graph structure:**
```
Base Color * Alpha --> Albedo
Emission Color * Emission Intensity --> Emission
Fresnel(Normal, View, Power) * Emission Color * 0.3 --> Add to Emission
```

The Fresnel term adds a subtle edge glow that makes neurons readable against both dark and passthrough backgrounds.

### 11.2 RegionTransparent.shadergraph

**Type:** URP Lit ShaderGraph
**Surface:** Transparent
**Blend:** Alpha
**Render Face:** Both
**Depth Write:** Off

| Property | Type | Range | Description |
|----------|------|-------|-------------|
| `_BaseColor` | Color | -- | Region color with alpha (0.45 default) |
| `_EmissionColor` | Color | -- | Heatmap/activation glow |
| `_EmissionIntensity` | Float | 0-2 | Activation intensity |
| `_HeatmapIntensity` | Float | 0-1 | Cumulative activation (warm tint) |

### 11.3 SynapseQuad.shadergraph

**Type:** URP Unlit ShaderGraph
**Surface:** Transparent
**Blend:** Alpha
**Render Face:** Both
**Cull:** Off

| Property | Type | Range | Description |
|----------|------|-------|-------------|
| `_Color` | Color | -- | Connection color + alpha |

Vertex colors from the procedural mesh override `_Color` for per-synapse variation.

### 11.4 RippleRing.shadergraph

**Type:** URP Unlit ShaderGraph
**Surface:** Transparent
**Custom:** Ring geometry with UV-based radial fade

| Property | Type | Range | Description |
|----------|------|-------|-------------|
| `_Color` | Color | -- | Region color |
| `_FadeProgress` | Float | 0-1 | Animated by script; 0=visible, 1=fully faded |
| `_RingWidth` | Float | 0.01-0.5 | UV-based ring mask width |

---

## 12. Build Configuration

### 12.1 Package Manifest (Required Packages)

```json
{
  "dependencies": {
    "com.unity.xr.openxr": "1.13.0",
    "com.unity.xr.meta-openxr": "2.1.0",
    "com.unity.xr.interaction.toolkit": "3.0.7",
    "com.unity.xr.hands": "1.5.0",
    "com.unity.textmeshpro": "4.0.0",
    "com.unity.nuget.newtonsoft-json": "3.2.1",
    "com.unity.render-pipelines.universal": "17.0.3"
  }
}
```

**Additional NuGet packages (via NuGetForUnity or manual DLL import):**
- `Cysharp.UniTask` (v2.5+) -- async/await for Unity
- `DOTween` (HOTween v2, via Asset Store or Unity Package) -- animation tweening
- `endel/NativeWebSocket` (v1.1.4+, via git URL) -- WebSocket for Quest/IL2CPP

### 12.2 Project Settings

| Setting | Value |
|---------|-------|
| **Scripting Backend** | IL2CPP |
| **Target Architecture** | ARM64 |
| **API Compatibility Level** | .NET Standard 2.1 |
| **Graphics API** | Vulkan (remove OpenGLES) |
| **Minimum API Level** | Android 12 (API 32) |
| **Target API Level** | Android 14 (API 34) |
| **Install Location** | Automatic |
| **Internet Access** | Required (for Supabase) |
| **Managed Stripping Level** | Low (to avoid IL2CPP stripping WebSocket classes) |

### 12.3 link.xml (IL2CPP Preservation)

```xml
<!-- Assets/Plugins/link.xml -->
<linker>
    <!-- Preserve WebSocket types for NativeWebSocket -->
    <assembly fullname="System.Net.WebSockets" preserve="all"/>
    <assembly fullname="System.Net.WebSockets.Client" preserve="all"/>

    <!-- Preserve JSON serialization types -->
    <assembly fullname="Newtonsoft.Json" preserve="all"/>

    <!-- Preserve System.Reactive if using supabase-csharp Realtime -->
    <assembly fullname="System.Reactive" preserve="all"/>

    <!-- Preserve UniTask async state machines -->
    <assembly fullname="UniTask" preserve="all"/>
</linker>
```

### 12.4 Quality Settings

Single quality level for Quest 3:

| Setting | Value |
|---------|-------|
| Pixel Light Count | 2 |
| Texture Quality | Half Res |
| Anisotropic Textures | Disabled |
| Anti-Aliasing | 4x (MSAA, via URP) |
| Soft Particles | OFF |
| Realtime Reflection Probes | OFF |
| Billboards Face Camera | ON |
| Shadow Resolution | 0 (disabled) |
| Shadow Distance | 0 (disabled) |
| V Sync Count | Don't Sync (OpenXR manages vsync) |

---

## 13. Risk Register

| # | Risk | Probability | Impact | Mitigation |
|---|------|------------|--------|------------|
| R1 | `supabase-csharp` Realtime WebSocket fails under IL2CPP AOT on Quest | High | High | Use NativeWebSocket with manual Phoenix Channel protocol. Fallback: polling REST every 2s. |
| R2 | SRP Batcher does not batch 488 neurons efficiently | Medium | Medium | Profile on Quest. Fallback: `DrawMeshInstancedIndirect` with ComputeBuffer. |
| R3 | Thermal throttling after 5+ minutes of sustained rendering | Medium | Medium | Implement LOD system (Section 5.3). Reduce render scale to 0.8. Disable spreading ripples when idle. |
| R4 | Hand tracking latency causes interaction frustration | Medium | Low | Provide controller fallback. Add visual ray feedback. Use generous selection radius (5cm). |
| R5 | Passthrough color passthrough introduces visual noise behind transparent brain | Low | Low | Increase brain shell opacity to 0.12. Add dark backdrop plane option. |
| R6 | DOTween GC allocation causes frame spikes during sleep animation | Medium | Medium | Use `SetRecyclable(true)`. Pre-allocate tween pool. Avoid string allocations in tween callbacks. |
| R7 | Font rendering in world-space TextMeshPro is blurry in VR | Medium | Low | Use SDF font with appropriate atlas resolution (1024+). Set Canvas scale factor appropriately. |
| R8 | JSON parse time for 488 concepts blocks main thread on load | Low | Low | Use `UniTask.RunOnThreadPool` for JSON deserialization. Show loading indicator. |
| R9 | Newtonsoft.Json reflection causes IL2CPP issues | Medium | High | Add all model classes to `link.xml`. Test on device early. Fallback: use source generator for JSON. |
| R10 | User study participants experience motion sickness | Medium | High | Keep brain stationary (table-anchored). Avoid vection. Measure SSQ before and after. Limit MR session to 15 minutes. |

---

## Appendix A: Ported Algorithm -- Fibonacci Sphere

Direct port from `useBrainData.ts` line 85-96:

```csharp
// FibonacciSphere.cs
public static class FibonacciSphere
{
    private static readonly float GoldenRatio = (1f + Mathf.Sqrt(5f)) / 2f;

    /// <summary>
    /// Generate a point on a Fibonacci sphere.
    /// Produces evenly-distributed points on a sphere surface.
    /// </summary>
    public static Vector3 GetPoint(int index, int total, float radius)
    {
        if (total <= 0) return Vector3.zero;

        float theta = 2f * Mathf.PI * index / GoldenRatio;
        float phi = Mathf.Acos(1f - 2f * (index + 0.5f) / total);

        float x = radius * Mathf.Sin(phi) * Mathf.Cos(theta);
        float y = radius * Mathf.Sin(phi) * Mathf.Sin(theta);
        float z = radius * Mathf.Cos(phi);

        return new Vector3(x, y, z);
    }
}
```

## Appendix B: Ported Algorithm -- Spherical Coordinates

Direct port from `RealisticBrain.tsx` line 15-24:

```csharp
// SphericalCoordinates.cs
public static class SphericalCoordinates
{
    /// <summary>
    /// Convert spherical coords (theta, phi, r) to cartesian (x, y, z)
    /// with ellipsoid scaling factors.
    /// </summary>
    public static Vector3 ToCartesian(float theta, float phi, float r,
        float scaleX = 1.2f, float scaleY = 1.0f, float scaleZ = 1.1f)
    {
        return new Vector3(
            r * Mathf.Sin(theta) * Mathf.Cos(phi) * scaleX,
            r * Mathf.Cos(theta) * scaleY,
            r * Mathf.Sin(theta) * Mathf.Sin(phi) * scaleZ
        );
    }

    /// <summary>
    /// Get center position of a brain region in scene space.
    /// </summary>
    public static Vector3 GetRegionCenter(BrainRegionData region, float sceneScale = 4f)
    {
        float thetaMid = (region.theta_min + region.theta_max) / 2f;
        float phiMid = (region.phi_min + region.phi_max) / 2f;
        float rMid = (region.radius_min + region.radius_max) / 2f;
        return ToCartesian(thetaMid, phiMid, rMid * sceneScale);
    }

    /// <summary>
    /// Get a random position within a brain region's bounds.
    /// </summary>
    public static Vector3 GetRandomPositionInRegion(BrainRegionData region,
        float sceneScale = 4f, float jitter = 0.3f)
    {
        float theta = UnityEngine.Random.Range(region.theta_min, region.theta_max);
        float phi = UnityEngine.Random.Range(region.phi_min, region.phi_max);
        float r = UnityEngine.Random.Range(region.radius_min, region.radius_max);

        Vector3 pos = ToCartesian(theta, phi, r * sceneScale);
        pos.x += UnityEngine.Random.Range(-jitter, jitter) * 0.5f;
        pos.y += UnityEngine.Random.Range(-jitter, jitter) * 0.5f;
        pos.z += UnityEngine.Random.Range(-jitter, jitter) * 0.5f;

        return pos;
    }
}
```

## Appendix C: Ported Algorithm -- Simplified Louvain Clustering

Direct port from `useBrainData.ts` line 98-181:

```csharp
// LouvainClustering.cs
public static class LouvainClustering
{
    private const int MaxIterations = 10;

    /// <summary>
    /// Simplified Louvain-style community detection.
    /// Returns: (neuronId -> clusterId mapping, clusterId -> member list)
    /// </summary>
    public static (Dictionary<string, string> clusters, Dictionary<string, List<string>> clusterMembers)
        Cluster(List<ConceptData> neurons, List<RelationData> synapses)
    {
        // Build adjacency map with weights
        var adjacency = new Dictionary<string, Dictionary<string, float>>();
        foreach (var n in neurons)
            adjacency[n.id] = new Dictionary<string, float>();

        foreach (var s in synapses)
        {
            if (adjacency.ContainsKey(s.from_concept_id) && adjacency.ContainsKey(s.to_concept_id))
            {
                adjacency[s.from_concept_id][s.to_concept_id] = s.strength;
                adjacency[s.to_concept_id][s.from_concept_id] = s.strength;
            }
        }

        // Initialize: each neuron is its own cluster
        var clusters = new Dictionary<string, string>();
        foreach (var n in neurons)
            clusters[n.id] = n.id;

        // Iteratively optimize
        bool changed = true;
        int iterations = 0;

        while (changed && iterations < MaxIterations)
        {
            changed = false;
            iterations++;

            foreach (var neuron in neurons)
            {
                string currentCluster = clusters[neuron.id];
                var neighbors = adjacency.GetValueOrDefault(neuron.id);
                if (neighbors == null || neighbors.Count == 0) continue;

                // Calculate strength to each neighboring cluster
                var clusterStrengths = new Dictionary<string, float>();
                foreach (var (neighborId, strength) in neighbors)
                {
                    string neighborCluster = clusters[neighborId];
                    clusterStrengths.TryGetValue(neighborCluster, out float current);
                    clusterStrengths[neighborCluster] = current + strength;
                }

                if (!clusterStrengths.ContainsKey(currentCluster))
                    clusterStrengths[currentCluster] = 0;

                // Find best cluster
                string bestCluster = currentCluster;
                float bestStrength = clusterStrengths[currentCluster];

                foreach (var (cluster, strength) in clusterStrengths)
                {
                    if (strength > bestStrength)
                    {
                        bestStrength = strength;
                        bestCluster = cluster;
                    }
                }

                if (bestCluster != currentCluster)
                {
                    clusters[neuron.id] = bestCluster;
                    changed = true;
                }
            }
        }

        // Build cluster members map
        var clusterMembers = new Dictionary<string, List<string>>();
        foreach (var (neuronId, clusterId) in clusters)
        {
            if (!clusterMembers.ContainsKey(clusterId))
                clusterMembers[clusterId] = new List<string>();
            clusterMembers[clusterId].Add(neuronId);
        }

        return (clusters, clusterMembers);
    }
}
```

---

## Appendix D: Development Stage Visual Properties

Ported from `useBrainRegions.ts` `STAGE_PARAMS`:

| Stage | Label | Brain Scale | Synapse Density | Regions Available |
|-------|-------|-------------|-----------------|-------------------|
| 0 | NEWBORN | 25% | 30% | development_stage_min <= 0 |
| 1 | INFANT | 48% | 60% | development_stage_min <= 1 |
| 2 | BABY | 65% | 85% | development_stage_min <= 2 |
| 3 | TODDLER | 80% | 100% (peak) | development_stage_min <= 3 |
| 4 | CHILD | 90% | 70% (pruning begins) | development_stage_min <= 4 |
| 5 | TEEN | 95% | 55% | All regions |
| 6 | YOUNG_ADULT | 98% | 45% | All regions |
| 7 | MATURE | 100% | 40% | All regions |

**Visual implementation:**
- `Brain Scale`: Applied to `BrainXR_Root.prefab` `transform.localScale`
- `Synapse Density`: Controls what fraction of synapses are rendered (random subset selection, seeded)
- `Regions Available`: Regions with `development_stage_min > currentStage` are rendered at 40% scale and 8% opacity (dimmed/dormant)

---

## Appendix E: Node Visual Property Encoding (Paper Requirements)

The ISMAR paper specifies specific visual mappings for node properties:

| Data Property | Visual Channel | Formula | Range |
|---|---|---|---|
| `strength` | Sphere **size** | `baseRadius + strength * scaleMultiplier` | 8mm - 20mm |
| `emotional_salience` | Sphere **base color saturation** | `Lerp(desaturated, fullColor, salience)` | 0-1 |
| `emotional_salience` | Sphere **emission intensity** | `salience * 2.0` (when idle, not activated) | 0-2 HDR |
| `recency` | Sphere **opacity** | `0.3 + recency * 0.7` | 0.3-1.0 |
| `category` | Sphere **hue** | Category color lookup table | Discrete |
| Activation (direct) | **Emission pulse** | `baseEmission + sin(t * 4) * intensity * 2` | Pulsing, 3s decay |
| Activation (spreading) | **Amber emission** + ripple ring | `amber * intensity`, ring expands 1.25s cycle | 5s decay |

---

*End of Technical Specification*
