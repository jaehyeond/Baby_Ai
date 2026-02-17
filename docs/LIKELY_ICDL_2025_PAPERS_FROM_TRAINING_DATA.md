# Likely ICDL 2025 Papers (From Training Data Knowledge)

**⚠️ IMPORTANT**: These are papers I have REASONABLE CONFIDENCE are from ICDL 2025 or were likely presented based on known research groups' trajectories. However, **I CANNOT guarantee these exact papers appeared at ICDL 2025** without access to the proceedings.

**Use this as a STARTING POINT, not a substitute for manual proceedings search.**

---

## HIGH CONFIDENCE PAPERS (Based on known research trajectory)

### H1. Emotion-Modulated Learning (DIRECT OVERLAP)

**Paper**: "The Role of Emotions in Learning and Adaptation" or similar
- **Likely Authors**: Lones, M. et al. (University of Edinburgh)
- **Expected at**: ICDL 2025 or ICDL 2024-2025 workshop
- **Mechanism**: Appraisal-theory-based emotion system that modulates exploration/exploitation
- **Threat**: **3/5** -- MUST FIND. This directly competes with your emotion-modulated learning claim.
- **Search Query**:
  ```
  "Lones" emotion learning 2024 2025
  "appraisal" emotion reinforcement 2024 2025
  ```

**Paper**: "Cognitive Developmental Robotics: Emotional Development Across Life Stages"
- **Likely Authors**: Asada, M. et al. (Osaka University)
- **Expected at**: ICDL 2025 or ICDL 2024
- **Mechanism**: Emotion development in robots through interaction; pain-based learning; affective signals
- **Threat**: **2-3/5** -- They do emotion + development in robots. You do emotion + development in LLM agent. Must differentiate.
- **Search Query**:
  ```
  "Asada" emotion development 2024 2025
  "affective" cognitive developmental robotics 2024 2025
  ```

---

### H2. Intrinsic Motivation & Curiosity (CORE ICDL TOPIC)

**Paper**: "Language-Conditioned Intrinsic Motivation with Large Language Models" or similar variant
- **Likely Authors**: Colas, C., Sigaud, O., Oudeyer, P-Y. (Inria Bordeaux / Université de Bordeaux)
- **Expected at**: ICDL 2025 or adjacent (CoRL, NeurIPS workshop)
- **Mechanism**: Language scaffolds intrinsic motivation; agent imagines goals using LLM; learning progress (LP) guides curriculum
- **Overlap**: Your curiosity-driven exploration is similar to their LP-based curiosity
- **Threat**: **3/5** -- They solve "how development progresses" using LP-based curriculum. You use explicit stages. Reviewers WILL compare.
- **Search Query**:
  ```
  "Colas" language motivation 2024 2025
  "Oudeyer" large language model goal 2024 2025
  ```

**Paper**: "Automatic Curriculum Learning for Developmental Tasks" or similar
- **Likely Authors**: Portelas, R., Oudeyer, P-Y. et al.
- **Expected at**: ICDL 2023-2025 (ongoing line of work)
- **Mechanism**: Learning progress computed as competence derivative; tasks selected for highest LP (Goldilocks zone); curriculum emerges
- **Overlap**: Their developmental curriculum ~ your stage transitions; their LP ~ your curiosity
- **Threat**: **3/5** -- LP-based curriculum is arguably more principled than hand-coded stage thresholds. Must cite and defend.
- **Search Query**:
  ```
  "Portelas" curriculum 2024 2025
  "learning progress" development 2024 2025
  ```

---

### H3. Memory Systems in Development (DIRECT OVERLAP)

**Paper**: "Autobiographical Memory and Narrative Development in Social Robots" or variant
- **Likely Authors**: Pointeau, G., Dominey, P. (LIRMM Montpellier)
- **Expected at**: ICDL 2023-2025 (ongoing line of work)
- **Mechanism**: Episodic memory storage → semantic memory extraction → procedural skills. Three-type memory system.
- **Direct Overlap**: Same 3-type memory taxonomy as BabyBrain
- **Threat**: **3/5** -- MUST CITE. They have formalized 3-type memory in robots. You cannot claim this as novel without acknowledging them.
- **Search Query**:
  ```
  "Pointeau" episodic memory 2024 2025
  "Dominey" autobiographical narrative 2024 2025
  ```

**Paper**: "Brain-Inspired Memory Consolidation Through Sleep Replay"
- **Likely Authors**: van de Ven, G., Siegelmann, H., Tolias, A. (2020, Nature Comms) -- not ICDL but ICDL community uses this
- **Expected at**: ICDL workshop or similar developmental learning venue in 2024-2025
- **Mechanism**: Generative replay during sleep-like phases prevents catastrophic forgetting; mimics hippocampal replay
- **Direct Overlap**: Your LLM-free sleep consolidation is conceptually related
- **Threat**: **2/5** -- Different venue but ICDL reviewers know this work. Must cite for thoroughness.
- **Search Query**:
  ```
  "van de Ven" replay memory 2024 2025
  "consolidation" sleep neural 2024 2025
  ```

---

### H4. Developmental Learning & Stage-Gated Capability

**Paper**: "Complexity Scaling in Predictive Development" or similar
- **Likely Authors**: Tani, J. et al. (Okinawa Institute)
- **Expected at**: ICDL 2023-2025 (ongoing line of work)
- **Mechanism**: Multiple timescale recurrent predictive coding; complexity emerges with development; prediction error drives learning
- **Overlap**: Your stage-gated development ~ their complexity scaling; your prediction mechanism ~ their predictive coding
- **Threat**: **2/5** -- Different implementation but same developmental inspiration. Should cite for context.
- **Search Query**:
  ```
  "Tani" predictive development 2024 2025
  "timescale" complexity learning 2024 2025
  ```

**Paper**: "Modular Intrinsic Motivation with Learning Progress Scaling"
- **Likely Authors**: Forestier, R., Oudeyer, P-Y.
- **Expected at**: ICDL 2023-2025 (ongoing line of work)
- **Mechanism**: Modular goal babbling with per-module learning progress; multi-goal curriculum
- **Overlap**: Goal-directed learning driven by intrinsic motivation
- **Threat**: **2/5** -- Robotics-focused, but conceptually related to your curiosity mechanism.
- **Search Query**:
  ```
  "Forestier" modular motivation 2024 2025
  "babbling" curriculum 2024 2025
  ```

---

### H5. Synaptic Plasticity & Hebbian Learning

**Paper**: "Information-Driven Self-Organization in Neural Development" or variant
- **Likely Authors**: Triesch, J. et al. (University of Frankfurt)
- **Expected at**: ICDL 2023-2025 (ongoing line of work)
- **Mechanism**: STDP (Spike-Timing-Dependent Plasticity) with information-maximization; develops visual cortex properties from scratch
- **Overlap**: Both claim "Hebbian learning"; both in developmental context
- **Threat**: **1/5** -- Very different level (real neurons vs concept networks). BUT: reviewers may critique your "Hebbian" terminology as misleading.
- **Search Query**:
  ```
  "Triesch" STDP development 2024 2025
  "information" plasticity 2024 2025
  ```

---

### H6. Affective Computing & Development

**Paper**: "Social-Emotional Robot Learning Through Facial Expression Interaction"
- **Likely Authors**: Boucenna, S., Gaussier, P., Hafez, K. (ETIS, Cergy, France)
- **Expected at**: ICDL 2023-2025 (ongoing line of work)
- **Mechanism**: Emotion recognition from facial expressions → emotional learning in social context
- **Overlap**: Emotion in developmental learning
- **Threat**: **2/5** -- They focus on emotion perception; you focus on internal emotion dynamics. Different but should acknowledge.
- **Search Query**:
  ```
  "Boucenna" emotion robot 2024 2025
  "Gaussier" social learning 2024 2025
  ```

---

### H7. Language & Developmental AI

**Paper**: "Embodied Language Grounding with Developmental Scaffolding"
- **Likely Authors**: Cangelosi, A. et al. (University of Manchester)
- **Expected at**: ICDL 2023-2025 (ongoing line of work)
- **Mechanism**: Embodied language acquisition; developmental trajectory of linguistic competence; multimodal grounding
- **Overlap**: Developmental learning in language-capable agents
- **Threat**: **2/5** -- Robotics-focused, not emotion-focused. Adjacent but not directly competing.
- **Search Query**:
  ```
  "Cangelosi" language development 2024 2025
  "grounding" scaffold 2024 2025
  ```

---

## MEDIUM CONFIDENCE PAPERS (Likely but not certain)

### M1. RL + Emotion

**Paper**: "Emotion-Shaped Reinforcement Learning for Goal-Directed Behavior"
- **Likely Authors**: Various (ICDL community)
- **Expected at**: ICDL 2025 or 2024-2025 workshop
- **Mechanism**: Emotional state shapes reward function or exploration strategy
- **Threat**: **2-3/5** -- Similar concept to your emotion-modulated learning. Must check for existence.

### M2. LLM + Developmental Constraints (BLACK SWAN)

**Paper**: [UNKNOWN TITLE - Possibly doesn't exist yet]
- **Likely Authors**: [Unknown -- Could be from LLM/AI community crossing into ICDL]
- **Expected at**: ICDL 2025 [Uncertain]
- **Mechanism**: LLM agent with explicit developmental stages / constraints / scaffolding
- **Threat**: **5/5 IF EXISTS** -- Directly competes with BabyBrain's core positioning
- **Probability of Existence**: 15-25% (growing trend of LLM + development, but still niche)
- **Critical Search**: Look for any ICDL 2025 paper with "LLM" + "development" or "developmental" + "language model"

---

## LOW CONFIDENCE PAPERS (Unlikely or from non-ICDL venues)

### L1. Historical References (Must cite but not novel threats)

**Hebbian Learning Foundations**:
- Hebb (1949) "The Organization of Behavior" -- foundational
- Triesch (2012) "Information-Driven Self-Organization" -- ICDL regular but established work

**Spreading Activation**:
- Anderson (1983) "The Architecture of Cognition" (ACT-R) -- must cite for spreading activation
- Collins & Loftus (1975) "A Spreading Activation Theory of Semantic Processing" -- foundational

**Memory Consolidation**:
- McClelland et al. (1995) "Why there are complementary learning systems in the hippocampus and neocortex" -- theoretical foundation
- van de Ven et al. (2020) "Brain-inspired replay for continual learning" -- recent strong work

**Intrinsic Motivation**:
- Oudeyer & Kaplan (2007) "What is intrinsic motivation?" -- foundational ICDL paper
- Schmidhuber (2010) "Formal theory of creativity" -- theoretical foundation

---

## SEARCH PRIORITY RANKING

**TIER 1 (MUST FIND - Do first)**:
1. Lones et al. emotion modulation papers
2. Colas/Oudeyer LLM + motivation papers
3. Pointeau/Dominey 3-type memory papers
4. Any ICDL 2025 paper with "LLM" + "development"

**TIER 2 (SHOULD FIND)**:
1. Asada emotion development papers
2. Portelas/Oudeyer curriculum learning papers
3. Tani predictive coding papers
4. van de Ven et al. memory replay (if recent ICDL version)

**TIER 3 (NICE TO HAVE)**:
1. Boucenna social emotion papers
2. Cangelosi language development papers
3. Triesch Hebbian development papers
4. Any emotion + RL papers

---

## VALIDATION STRATEGY

**After you complete manual search**, compare against this list:

- [ ] Found Lones emotion paper? (Expected HIGH likelihood)
- [ ] Found Colas/Oudeyer LLM paper? (Expected HIGH likelihood)
- [ ] Found Pointeau/Dominey memory paper? (Expected MEDIUM-HIGH likelihood)
- [ ] Found Asada emotion+development paper? (Expected MEDIUM likelihood)
- [ ] Found any LLM+development paper I didn't predict? (Expected LOW likelihood but CRITICAL if exists)
- [ ] Found other papers in emotion, memory, or development not listed here? (Expected YES - add to tracker)

---

## HONEST CONFIDENCE ASSESSMENT

| Topic | My Confidence | Reliability |
|-------|---------------|------------|
| Oudeyer group still active in intrinsic motivation | 95% | Very High |
| Dominey/Pointeau have 3-type memory work | 90% | Very High |
| Emotion-modulated learning papers exist somewhere in 2024-2025 literature | 85% | High |
| Specific ICDL 2025 papers by these authors | 50-60% | Medium (depends on conference dates/proceedings indexing) |
| Existence of LLM+development paper at ICDL 2025 | 20-25% | Low (educated guess based on trends) |

**BOTTOM LINE**: Use this as a research guide, not as complete truth. You must manually verify everything before citing in your paper.

---

## NEXT STEPS

1. **Print or bookmark** this document
2. **Use it while searching** to validate what you find
3. **Add new papers** to the ICDL_2025_PAPER_TRACKER.md as you discover them
4. **Note surprises**: If you find papers on topics I didn't predict, that's valuable data
5. **Report back**: Let me know what you find; it helps calibrate future searches

