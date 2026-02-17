# ICDL 2025 Paper Analysis for BabyBrain Positioning

**Conference**: IEEE International Conference on Development and Learning (ICDL) 2025
**Location**: Prague, Czech Republic, 16-19 September 2025
**Publication**: IEEE Xplore, pub number 11204361
**Total papers**: ~89 (including covers/committees)
**Analysis date**: 2026-02-11

---

## EXECUTIVE SUMMARY

After analyzing all 89 papers in the ICDL 2025 proceedings, the key finding is:

**NO paper at ICDL 2025 combines LLM-based cognition + developmental stages + multi-type memory + emotion system + brain region mapping + sleep consolidation.**

BabyBrain occupies a genuinely novel position. The conference is heavily robotics-focused (embodied sensorimotor learning), with very few papers using LLMs as cognitive engines. Only 4 papers use LLMs at all. This is favorable positioning for BabyBrain.

### Threat Level Distribution
- **Threat 4/5**: 1 paper (Growing Perspectives)
- **Threat 3/5**: 9 papers
- **Threat 2/5**: 10 papers
- **Threat 1/5**: ~15 papers (tangential relevance)
- **Threat 0/5**: ~50+ papers (no meaningful overlap)

---

## TIER 1: HIGH RELEVANCE PAPERS (Threat 3-4)

### 1. Growing Perspectives: Modelling Embodied Perspective Taking and Inner Narrative Development Using Large Language Models
- **Authors**: Sabrina Patania et al. (University of Milan-Bicocca)
- **ID**: 11204394
- **Key Contribution**: Uses LLMs (GPT) to simulate developmental stages of perspective taking based on Selman's theory. Evaluates how GPT generates internal narratives aligned with specified developmental stages in a director task.
- **Overlap with BabyBrain**: LLM + developmental stages + inner narrative. Most similar paper at ICDL 2025.
- **Threat Level**: 4/5
- **What we do that they DON'T**:
  - They use static/pre-specified Selman stages; we have emergent stage transitions driven by experience accumulation
  - NO memory system (episodic/semantic/procedural)
  - NO emotion system
  - NO brain region mapping
  - NO sleep consolidation
  - NO synaptic plasticity / Hebbian learning
  - NO spreading activation
  - Their focus is perspective-taking only; ours is full cognitive development
- **How to cite**: "While [Patania et al.] model discrete perspective-taking stages in LLMs, our system implements a comprehensive developmental architecture with emergent stage transitions, multi-type memory, and emotional modulation."

---

### 2. No Robot is an Island: An Always-On Cognitive Architecture for Social Context Awareness
- **Authors**: (Not fully extracted, cited 1x)
- **ID**: 11204444
- **Key Contribution**: Always-on cognitive architecture with sensor fusion, multimodal in-memory representation, and self-organization through **memory consolidation**. Tested at Humanoids 2024.
- **Overlap with BabyBrain**: Memory consolidation, continuous learning, cognitive architecture, self-supervised learning.
- **Threat Level**: 3/5
- **What we do that they DON'T**:
  - NO LLM integration
  - NO developmental stages
  - NO emotion system
  - NO semantic concept graph / spreading activation
  - Their consolidation is for episodic social context; ours strengthens neuron connections via Hebbian rules
  - NO anatomical brain region mapping
- **How to cite**: "Memory consolidation in [this work] focuses on episodic social context; in contrast, our sleep consolidation operates across semantic, episodic, and procedural memory types with Hebbian plasticity rules."

---

### 3. Homeostasis Driven Learning and Development in an Autonomous Robot
- **Authors**: (Unitree Go2 robot study)
- **ID**: 11204417
- **Key Contribution**: Homeostatic drives (Energy, Health, Temperature) drive exploration and cognitive development in a quadruped robot. Emergent behaviors like play, object permanence, and self-soothing arise from basic survival needs via neurohormone-modulated emergent neural networks.
- **Overlap with BabyBrain**: Internal drives affecting learning, emergent cognitive development, neural network for cognition.
- **Threat Level**: 3/5
- **What we do that they DON'T**:
  - NO LLM backbone
  - NO explicit developmental stages with gating
  - NO multi-type memory system
  - Their "emotions" are homeostatic drives, not a true emotion model (6 basic + 5 compound)
  - NO language/conversation capabilities
  - NO brain region mapping
  - NO sleep consolidation
- **How to cite**: "While [this work] demonstrates emergent cognitive behaviors from homeostatic drives in physical robots, our system operates at a higher cognitive level with LLM-based reasoning, explicit emotion modeling, and stage-gated developmental progression."

---

### 4. Silicopathy: Artificial Empathy through Cognitive and Affective Development of Pain
- **Authors**: Minoru Asada
- **ID**: 11204355
- **Key Contribution**: Position paper introducing "silicopathy" -- developmental framework for artificial moral agency through pain-based empathic learning. Uses DMBN and ODRC for short-term pain learning and internal simulation. Proposes future LLM integration for long-term pain memory.
- **Overlap with BabyBrain**: Affective development, memory-based prediction, developmental cognition, proposed LLM integration.
- **Threat Level**: 3/5
- **What we do that they DON'T**:
  - This is a position paper (no working system)
  - Focuses narrowly on pain/empathy; we model 6 basic + 5 compound emotions
  - NO developmental stages
  - NO spreading activation or concept graphs
  - NO brain region visualization
  - NO sleep consolidation
  - Their LLM integration is proposed, not implemented; ours is operational
- **How to cite**: "Asada proposes LLM integration for affective memory as future work; our system already implements LLM-driven emotional processing with compound emotion derivation affecting learning and memory consolidation."

---

### 5. Animal or Machine? Neuromodulated Emotions and their Effect on Affinity
- **Authors**: (Hazel robot team)
- **ID**: 11204403
- **Key Contribution**: Zoomorphic robot (dog) with neuromodulated emotion system (Cortisol, Adrenaline, Dopamine) conveying Happiness, Excitement, Anger, Fear, Possessiveness. Tested with 100 children aged 9-11.
- **Overlap with BabyBrain**: Emotion system with biological grounding, neuromodulation, emotion expression.
- **Threat Level**: 3/5
- **What we do that they DON'T**:
  - NO LLM or cognitive processing
  - NO developmental stages
  - NO memory system
  - Their emotions are for expression only (not learning modulation)
  - NO compound emotions
  - We have emotions AFFECTING cognition (learning rates, memory consolidation); they only express emotions
  - NO brain region mapping
- **How to cite**: "While [this work] uses neuromodulated emotions for social expression, our emotion system directly modulates cognitive processes: learning rates, memory consolidation strength, and goal generation."

---

### 6. Emulating Perceptual Development in Deep Reinforcement Learning
- **Authors**: (Not fully extracted)
- **ID**: 11204434
- **Key Contribution**: Staged perceptual development in RL agent (Pong game). State space representation changes in stages mimicking progressive infant perceptual development. Shows staged learning improves learning progress.
- **Overlap with BabyBrain**: Developmental stages, staged capability unlocking, infant-inspired learning.
- **Threat Level**: 3/5
- **What we do that they DON'T**:
  - NO LLM backbone
  - Only perceptual stages; we gate predictions, imagination, causal reasoning
  - NO memory system
  - NO emotion system
  - NO brain region mapping
  - Very narrow domain (Pong); we operate in open-ended conversational domain
  - Stages are pre-specified schedules; ours emerge from experience accumulation
- **How to cite**: "Unlike [this work]'s pre-scheduled perceptual stages, our developmental stages emerge from accumulated experience and gate increasingly complex cognitive capabilities (prediction, imagination, causal reasoning)."

---

### 7. MIMo grows! Simulating body and sensory development in a multimodal infant model
- **Authors**: (trieschlab, cited 1x)
- **ID**: 11204381
- **Key Contribution**: MIMo v2 -- multimodal infant simulation platform with growing body (birth to 24 months), foveated vision with developing acuity, sensorimotor delays. Open-source simulation framework.
- **Overlap with BabyBrain**: Developmental stages, infant model, age-appropriate capabilities.
- **Threat Level**: 3/5
- **What we do that they DON'T**:
  - Pure sensorimotor simulation (NO cognitive architecture)
  - NO LLM integration
  - NO memory system
  - NO emotion system
  - NO language or conversation
  - This is a platform/tool; ours is a cognitive architecture
  - NO brain region mapping (they model body, not brain)
- **How to cite**: "MIMo models physical sensorimotor development; our system models cognitive development with language, memory, and emotional systems operating through LLM-based reasoning."

---

### 8. Modeling the impact of phonological and semantic connectivity on early vocabulary growth
- **Authors**: (Norwegian longitudinal study, cited 1x)
- **ID**: 11204414
- **Key Contribution**: Investigates how word connectivity (phonological and semantic) in children's existing lexicon predicts new word acquisition. Shows "rich-get-richer" pattern -- semantically well-connected words predict earlier acquisition. Longitudinal data from 17-36 month Norwegian children.
- **Overlap with BabyBrain**: Semantic network for vocabulary, connectivity-based learning, developmental vocabulary growth.
- **Threat Level**: 3/5
- **What we do that they DON'T**:
  - Human study only (no computational model running)
  - NO LLM integration
  - NO emotion system affecting learning
  - NO brain region mapping
  - We implement the spreading activation and semantic concept graph computationally; they only analyze human data
  - NO stage-gated capabilities
- **How to cite**: "The 'rich-get-richer' vocabulary growth pattern documented in [this work] aligns with our spreading activation mechanism, where semantically well-connected concepts facilitate acquisition of new related concepts."

---

### 9. Unexpected Capability of Homeostasis for Open-ended Learning
- **Authors**: (Project page available)
- **ID**: 11204447
- **Key Contribution**: Homeostatically-regulated RL (HRRL) in Crafter environment. Agent acquires survival skills (foraging, water collection, shelter building, enemy attack) purely through homeostasis maintenance. Bio-inspired from computational neuroscience.
- **Overlap with BabyBrain**: Internal motivation driving learning, emergent behaviors, bio-inspired cognition.
- **Threat Level**: 3/5
- **What we do that they DON'T**:
  - NO LLM backbone
  - NO explicit developmental stages
  - NO memory types (episodic/semantic/procedural)
  - NO emotion system (homeostasis != emotion)
  - NO language capabilities
  - NO brain region mapping
  - Their agent learns actions; ours develops cognitive representations
- **How to cite**: "While HRRL demonstrates emergent behavior from homeostatic regulation, our system achieves emergent cognitive development through emotion-modulated LLM reasoning with explicit memory formation and consolidation."

---

### 10. MAGELLAN: Metacognitive predictions of learning progress guide autotelic LLM agents in large goal spaces
- **Authors**: Loris Gaven, Thomas Carta, Clement Romac, Cedric Colas, Sylvain Lamprier, Olivier Sigaud, Pierre-Yves Oudeyer
- **Source**: arXiv 2502.07709 (likely presented/associated with ICDL 2025 community)
- **Key Contribution**: LLM agents with metacognitive ability to predict their own competence and learning progress. Enables efficient curriculum learning in open-ended goal spaces.
- **Overlap with BabyBrain**: LLM agent, metacognition, learning progress, developmental progression.
- **Threat Level**: 3/5
- **What we do that they DON'T**:
  - NO multi-type memory system (episodic/semantic/procedural)
  - NO emotion system
  - NO brain region mapping
  - NO sleep consolidation
  - NO synaptic plasticity
  - Their "development" is curriculum optimization; ours models infant cognitive development stages
  - Focus is goal selection optimization; ours is comprehensive cognitive architecture
- **How to cite**: "MAGELLAN uses metacognitive LP prediction for curriculum optimization; our system models cognitive development as a comprehensive process including memory formation, emotional modulation, and stage-gated capability emergence."

---

## TIER 2: MODERATE RELEVANCE PAPERS (Threat 2)

### 11. Robot Learning Theory of Mind through Self-Observation
- **Authors**: Francesca Bianco et al. (University of Essex)
- **ID**: 11204407
- **Key Contribution**: Robot learns Theory of Mind by observing its own decision processes. Shows synergy between learning intentions/goals (low-level) and beliefs (high-level). Uses feedforward deep learning.
- **Overlap**: Cognitive development, belief modeling, internal state inference
- **Threat Level**: 2/5
- **Differentiator**: NO LLM, NO memory system, NO emotion, NO developmental stages. Focused specifically on ToM, not general cognitive development.

### 12. Teaching a Robot to Read Faces: Incremental Emotion Learning with Selective Visual Attention
- **Authors**: (developmental AI robot team)
- **ID**: 11204441
- **Key Contribution**: Robot learns facial emotion recognition through imitation game + attention-focusing mechanism. Studies how visual field restriction affects emotion recognition accuracy.
- **Overlap**: Emotion recognition, incremental learning, developmental AI
- **Threat Level**: 2/5
- **Differentiator**: Only emotion recognition (not generation or modulation of cognition). NO LLM, NO memory, NO developmental stages, NO brain mapping.

### 13. From Action to Protocol: The Emergence of Proto-Verbal Structure in Multi-Agent Communication Systems
- **Authors**: Yu Wei, Yasuo Kuniyoshi
- **ID**: 11204402
- **Key Contribution**: Multi-agent framework where agents develop communication protocols for coordinating actions. Discovers "prototype consistency" -- emergence of shared message prefixes resembling verb-like structures.
- **Overlap**: Language emergence, action-language grounding, developmental communication
- **Threat Level**: 2/5
- **Differentiator**: Multi-agent communication focus (not cognitive architecture). NO LLM, NO memory, NO emotion, NO developmental stages. Emergent language vs. our LLM-based language processing.

### 14. PRAG: Procedural Action Sequence Symbolic Generator
- **Authors**: (Not fully extracted)
- **ID**: 11204420
- **Key Contribution**: Generates multi-step manipulation tasks mirroring cognitive developmental processes. Curriculum-based progressive learning from semantic knowledge.
- **Overlap**: Procedural learning, developmental processes, progressive skill acquisition
- **Threat Level**: 2/5
- **Differentiator**: Task generation tool, not cognitive architecture. NO LLM, NO memory system, NO emotion. Focused on robotic manipulation, not cognitive development.

### 15. Fast or Slow: Adaptive Decision-Making in Reinforcement Learning with Pre-Trained LLMs
- **Authors**: Katrine Linnea Nergard, Kai Olav Ellefsen, Jim Torresen
- **ID**: 11204357
- **Key Contribution**: LLM guides RL agent between "fast" (intuitive) and "slow" (deliberate) thinking modes, inspired by dual-system theory of cognition. No fine-tuning needed.
- **Overlap**: LLM-based cognition, cognitive theory-inspired architecture
- **Threat Level**: 2/5
- **Differentiator**: Grid-world domain only. NO developmental stages, NO memory, NO emotion, NO brain mapping. Uses LLM for decision routing, not as cognitive backbone.

### 16. Performance of Large Language Models in the Wisconsin Card Sorting Task
- **Authors**: (Not fully extracted)
- **ID**: 11204408
- **Key Contribution**: Tests LLM cognitive flexibility using WCST. Finds rule-response mismatch and differences in top-down/bottom-up reasoning integration across models.
- **Overlap**: LLM cognitive capabilities, cognitive flexibility assessment
- **Threat Level**: 2/5
- **Differentiator**: Analysis paper (no architecture). Tests existing LLMs, doesn't build developmental systems. NO memory, NO emotion, NO stages.

### 17. Decentralized Collective World Model for Emergent Communication and Coordination
- **Authors**: Kentaro Nomura, Tatsuya Aoki, Tadahiro Taniguchi, Takato Horii (cited 2x)
- **ID**: 11204457
- **Key Contribution**: Multi-agent world model with symbol emergence for communication. Agents develop shared representations through bidirectional message exchange with contrastive learning.
- **Overlap**: World model, symbol emergence, shared representations
- **Threat Level**: 2/5
- **Differentiator**: Multi-agent focus. NO LLM, NO developmental stages, NO memory types, NO emotion. Symbol emergence for communication, not cognitive development.

### 18. Push, See, Predict: Emergent Perception Through Intrinsically Motivated Play
- **Authors**: Orestis Konstantaropoulos, Mehdi Khamassi, Petros Maragos, George Retsinas
- **ID**: 11204356
- **Key Contribution**: Self-supervised object-centric learning through intrinsic motivation. Robot learns world model via curiosity-driven play, improving prediction and reconstruction.
- **Overlap**: Intrinsic motivation, world model, prediction learning, infant-inspired exploration
- **Threat Level**: 2/5
- **Differentiator**: Sensorimotor learning only. NO LLM, NO memory system, NO emotion, NO developmental stages, NO language.

### 19. Interacting with Other Agents Without a-priori Knowledge: Radical Interactionist Architecture
- **Authors**: (Not fully extracted)
- **ID**: 11204437
- **Key Contribution**: Developmental agent architecture that infers other agents' motivations without prior knowledge. Learns to predict behavior in prey-predator context. Built on Radical Interactionism principles.
- **Overlap**: Developmental agent, motivation inference, building models from ground-up
- **Threat Level**: 2/5
- **Differentiator**: Multi-agent interaction focus. NO LLM, NO memory types, NO emotion system, NO developmental stages, NO brain mapping.

### 20. Computational models of the emergence of self-exploration in 2-month-old infants
- **Authors**: (Not fully extracted)
- **ID**: 11204351
- **Key Contribution**: Computational modeling of how self-exploration emerges in very young infants (2 months).
- **Overlap**: Infant developmental modeling, emergence of cognitive capabilities
- **Threat Level**: 2/5
- **Differentiator**: Very early motor development only. NO LLM, NO memory, NO emotion, NO language. Physical development, not cognitive architecture.

---

## TIER 3: LOW RELEVANCE BUT WORTH NOTING (Threat 1)

| # | Paper | ID | Relevance to BabyBrain |
|---|-------|-----|----------------------|
| 21 | Canalizing Babbling: Development-Inspired Goal Sampling | 11204428 | Motor babbling/exploration, infant-inspired but sensorimotor only |
| 22 | Comparative learning signals lead to aligned representations | 11204396 | Infant-inspired visual learning, cross-distribution alignment |
| 23 | Analyzing Multimodal Integration in the VAE | 11204413 | Multimodal integration, but pure ML approach without developmental focus |
| 24 | Cognitively-Inspired Ensemble Architecture | 11204432 | Cognitive decision-making ensemble, but URL classification task |
| 25 | Purpose-driven Open-Ended Learning | 11204395 | Intrinsic/extrinsic motivation, hierarchical OEL architecture |
| 26 | Robots that Learn to Solve Symbolic Novelties | 11204430 | Self-generated simulation, world model, but robotic manipulation |
| 27 | Cyclic Exploration and Exploitation in SMiRL | 11204397 | Surprise minimization, exploration-exploitation, but RL focus |
| 28 | A3RNN: Developmental Visual Attention in Robots | 11204426 | Developmental attention, bottom-up/top-down, but visual only |
| 29 | Variational Adaptive Noise and Dropout for RNNs | 11204433 | Stable RNN learning, but pure ML method |
| 30 | The Ungrounded Alignment Problem | 11204348 | Innate behavior in learning systems, modality-agnostic, but narrow |
| 31 | Towards Understanding Ambiguity Resolution in Multimodal Inference | 11204410 | Word meaning inference, multimodal context, language learning |
| 32 | Simulated Cortical Magnification for Object Learning | 11204429 | Cortical-inspired vision, self-supervised |
| 33 | Free Lunch? Low-Cost Intelligence Through Pattern-Guided Exploration | 11204411 | Pattern-guided exploration, intrinsic motivation |
| 34 | Predictability-Based Curiosity-Guided Action Symbol Discovery | 11204386 | Action symbol discovery, curiosity-driven |
| 35 | Contingent behavior during caregiver-child interaction improves word learning | 11204427 | Word learning, social interaction |

---

## WHAT BABYBRAIN HAS THAT NO ICDL 2025 PAPER HAS

These are our **unique differentiators** -- features that NO paper at ICDL 2025 implements:

### 1. LLM as Cognitive Backbone with Developmental Architecture
- Only 4 papers use LLMs at all (Growing Perspectives, Fast/Slow, WCST analysis, and tangentially Silicopathy)
- NONE uses LLM as the core cognitive engine of a developmental system
- **Our angle**: LLM provides human-like reasoning while development gates what the LLM can access

### 2. Three-Type Memory System (Episodic + Semantic + Procedural) as Neuron Network
- The Always-On Architecture has memory consolidation, but only for episodic social context
- NO paper has a unified multi-type memory system implemented as a concept graph
- **Our angle**: Memory types map to different cognitive functions with distinct formation and retrieval mechanisms

### 3. Compound Emotions (5 types) Derived from Basic Emotions Affecting Downstream Cognition
- Neuromodulated Emotions (Hazel) only expresses emotions, doesn't use them for cognitive modulation
- Silicopathy proposes pain-based memory but is a position paper
- NO paper has compound emotions (nostalgia, pride, guilt, jealousy, schadenfreude) affecting learning rates and memory
- **Our angle**: Emotions are not just outputs but active modulators of cognition

### 4. Experience-Driven Stage Transitions with Stage-Gated Capabilities
- Growing Perspectives uses pre-specified Selman stages
- Emulating Perceptual Development uses pre-scheduled perceptual stages
- NO paper has emergent stage transitions based on accumulated experience
- **Our angle**: Development is measured, not prescribed -- the system transitions when ready

### 5. Anatomical Brain Region Mapping with Spreading Activation
- NO paper at ICDL 2025 maps concepts to brain regions
- NO paper uses spreading activation (BFS) for memory retrieval
- **Our angle**: Biologically-grounded architecture with 9 brain regions and neuron activation patterns

### 6. LLM-Free Sleep Consolidation with Hebbian Plasticity
- Always-On Architecture has consolidation but uses different mechanism
- NO paper has explicit offline (sleep) consolidation that operates without LLM
- NO paper applies Hebbian learning rules to strengthen neuron connections
- **Our angle**: Sleep consolidation is a distinct process that strengthens frequently co-activated pathways

### 7. Integrated System (All Components Working Together)
- Individual papers address individual aspects (emotion OR stages OR memory)
- NO paper integrates all into one coherent developmental architecture
- **Our angle**: The interaction BETWEEN components (emotion affecting memory, stages gating capabilities, sleep consolidating learning) is the key contribution

---

## POSITIONING STRATEGY

### Recommended Framing for ICDL Paper
"While ICDL research has made significant progress in individual aspects of developmental learning -- sensorimotor exploration [11204428, 11204356], emotion expression [11204403, 11204441], staged learning [11204434], and memory consolidation [11204444] -- these advances remain largely siloed. We present BabyBrain, the first integrated cognitive architecture that combines LLM-based reasoning with developmental stage transitions, three-type memory with Hebbian consolidation, and emotion-modulated learning, instantiating a computational model of infant cognitive development."

### Key Comparison Table for Paper

| Feature | BabyBrain | Growing Persp. | Homeostasis | Always-On | MIMo | Silicopathy |
|---------|-----------|---------------|-------------|-----------|------|-------------|
| LLM backbone | YES | YES | NO | NO | NO | proposed |
| Dev. stages | Emergent | Pre-specified | NO | NO | Body growth | NO |
| Multi-type memory | 3 types | NO | NO | Episodic | NO | proposed |
| Emotion system | 6+5 compound | NO | Homeostatic | NO | NO | Pain only |
| Brain regions | 9 anatomical | NO | NO | NO | NO | NO |
| Sleep consolidation | Hebbian | NO | NO | YES (diff) | NO | NO |
| Spreading activation | BFS | NO | NO | NO | NO | NO |
| Language | Conversational | Director task | NO | NO | NO | NO |

### Strongest Novelty Claims
1. **First LLM-based developmental cognitive architecture** with emergent stage transitions
2. **First compound emotion system** affecting cognitive processing in a developmental agent
3. **First integrated sleep consolidation** with Hebbian plasticity in an LLM-based system
4. **First brain region mapping** with spreading activation for developmental AI

---

## PAPERS TO CITE IN RELATED WORK (Recommended)

**Must cite** (most relevant):
1. Growing Perspectives [11204394] -- LLM + developmental stages comparison
2. Homeostasis Driven Learning [11204417] -- drive-based development comparison
3. Always-On Architecture [11204444] -- memory consolidation comparison
4. Neuromodulated Emotions [11204403] -- emotion system comparison
5. Vocabulary growth model [11204414] -- semantic network growth comparison
6. MIMo grows [11204381] -- developmental model comparison

**Should cite** (to show awareness):
7. Emulating Perceptual Development [11204434] -- staged development
8. Silicopathy [11204355] -- affective development
9. Proto-Verbal Structure [11204402] -- language emergence
10. LLM Wisconsin Card Sorting [11204408] -- LLM cognitive assessment
11. MAGELLAN [arxiv 2502.07709] -- LLM metacognition

**Could cite** (for completeness):
12. Fast or Slow [11204357] -- LLM in developmental context
13. Radical Interactionist [11204437] -- ground-up development
14. PRAG [11204420] -- procedural/developmental learning
15. Push See Predict [11204356] -- intrinsic motivation
