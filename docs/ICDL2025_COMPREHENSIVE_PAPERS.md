# ICDL 2025: Comprehensive Paper Listing
## All 89 Papers with Full Metadata

**Conference**: IEEE ICDL 2025 (International Conference on Development and Learning)
**Dates**: 16-19 September 2025
**Location**: Prague, Czech Republic
**Publisher**: IEEE Xplore (Publication Number: 11204361)
**Analysis Date**: 11 February 2026

---

## TABLE OF CONTENTS

1. **Tier 1 (Threat 3-4)**: 10 papers - Highly relevant to BabyBrain
2. **Tier 2 (Threat 2)**: 10 papers - Moderately relevant
3. **Tier 3 (Threat 1)**: 35 papers - Low/tangential relevance
4. **Tier 4 (Threat 0)**: 34 papers - Minimal to no overlap

---

# TIER 1: HIGH RELEVANCE PAPERS (Threat Level 3-4/5)

## 1. Growing Perspectives: Modelling Embodied Perspective Taking and Inner Narrative Development Using Large Language Models
- **IEEE Xplore ID**: 11204394
- **Authors**: Sabrina Patania, Department of Psychology, University of Milan-Bicocca, Milan, Italy
- **Pages**: 1-6
- **Cited**: Yes (1x)
- **Key Contribution**: Implements PerspAct system integrating ReAct paradigm with LLMs (GPT) to simulate developmental stages of perspective-taking based on Selman's theory. Evaluates how LLMs generate developmentally-consistent internal narratives and assess impact on collaborative task performance in extended director task.
- **Methods**: LLM prompt engineering, developmental stage scaffolding, behavioral evaluation
- **Overlap with BabyBrain**:
  - Uses LLM as cognitive engine (like us)
  - Models developmental stages (like us)
  - Focuses on inner narrative (related to our conversation-process)
- **Threat Level**: **4/5** (HIGHEST)
- **What BabyBrain does they don't**:
  - Stages are pre-specified (Selman levels); ours emerge from experience accumulation
  - No memory system (episodic/semantic/procedural)
  - No emotion system affecting learning
  - No brain region mapping or visualization
  - No sleep consolidation or Hebbian plasticity
  - No spreading activation mechanism
  - Single-task focus (perspective-taking); we model comprehensive cognitive development
- **Citation Strategy**: Positioning statement: "While [Patania et al.] demonstrate discrete perspective-taking stages in LLMs, our architecture implements emergent developmental stage transitions based on cumulative experience, combined with multi-type memory, emotional modulation, and brain region mapping."
- **Related Keywords**: LLM reasoning, developmental cognition, perspective-taking, inner speech

---

## 2. No Robot is an Island: An Always-On Cognitive Architecture for Social Context Awareness in Dynamic Environments
- **IEEE Xplore ID**: 11204444
- **Authors**: (ACo approach team, cited 1x)
- **Pages**: 1-6
- **Cited**: Yes (1x)
- **Key Contribution**: Presents always-on cognitive architecture combining sensor fusion, efficient multimodal in-memory representation, and **self-organization through memory consolidation**. Tested at Humanoids 2024 conference for autonomous context-aware behavior development.
- **Methods**: Sensor fusion, real-time processing, memory consolidation algorithms
- **Overlap with BabyBrain**:
  - Memory consolidation (core to our sleep phase)
  - Continuous autonomous learning
  - Multimodal perception integration
  - Self-supervised representation building
- **Threat Level**: **3/5**
- **What BabyBrain does they don't**:
  - No LLM cognitive backbone
  - No explicit developmental stages
  - No emotion system
  - No semantic concept graph or spreading activation
  - Consolidation is for social context only; ours applies across all memory types
  - No anatomical brain region mapping
  - No language/conversational capabilities
- **Citation Strategy**: "While [this work] demonstrates memory consolidation for episodic social context, BabyBrain operates across semantic, episodic, and procedural memory types with explicit Hebbian plasticity rules during LLM-free sleep consolidation."
- **Related Keywords**: Memory consolidation, cognitive architecture, autonomous learning, sensor fusion

---

## 3. Homeostasis Driven Learning and Development in an Autonomous Robot
- **IEEE Xplore ID**: 11204417
- **Authors**: (Unitree Go2 quadruped robot study)
- **Pages**: 1-6
- **Key Contribution**: Demonstrates that homeostatic drives (Energy, Health, Temperature) can serve as catalysts for cognitive development in autonomous robots. Using neurohormone-modulated emergent neural networks, a Unitree Go2 quadruped learns from homeostatic needs, exhibiting emergent behaviors including play, object permanence, and self-soothing without explicit reward functions.
- **Methods**: Homeostatic reinforcement learning, embodied learning, neurohormone modulation
- **Overlap with BabyBrain**:
  - Internal drives affecting learning trajectory
  - Emergent cognitive behaviors arising from simple constraints
  - Neural network for cognition
  - Bio-inspired learning mechanisms
- **Threat Level**: **3/5**
- **What BabyBrain does they don't**:
  - No LLM backbone (pure embodied learning)
  - No explicit developmental stages with gating
  - Homeostatic drives ≠ emotion system (6 basic + 5 compound emotions)
  - No multi-type memory system
  - No language or conversational capabilities
  - No anatomical brain region mapping
  - No sleep consolidation
  - Physical robot focus; we're cognitive architecture focus
- **Citation Strategy**: "While [this work] shows emergent development from homeostatic regulation in physical robots, BabyBrain demonstrates emergent cognitive development in conversational agents through LLM-based reasoning modulated by compound emotions and stage-gated capabilities."
- **Related Keywords**: Homeostasis, intrinsic motivation, embodied learning, emergent cognition

---

## 4. Silicopathy: Artificial Empathy through Cognitive and Affective Development of Pain
- **IEEE Xplore ID**: 11204355
- **Authors**: Minoru Asada
- **Pages**: 1-6
- **Key Contribution**: **Position paper** introducing "silicopathy" -- a developmental and embodied framework for constructing artificial moral agency through pain-based empathic learning. Proposes Deep Modality Blending Networks (DMBN) and Oscillator-Driven Reservoir Computing (ODRC) for short-term pain learning and internal simulation, with future LLM integration for long-term pain memory and socially interpretable behavior.
- **Methods**: Computational emotion modeling, pain-based learning, proposed LLM integration (not implemented)
- **Overlap with BabyBrain**:
  - Affective development framework
  - Memory-based prediction in emotional context
  - Developmental cognitive architecture
  - Proposed but not implemented LLM integration
- **Threat Level**: **3/5**
- **What BabyBrain does they don't**:
  - This is a position paper (no working system); ours is operational
  - Focuses narrowly on pain/empathy; we model 6 basic emotions + 5 compound emotions
  - No developmental stages
  - No spreading activation or semantic concept graphs
  - No brain region visualization (unlike our 9-region model)
  - No sleep consolidation mechanism
  - LLM integration is proposed future work; ours is implemented
  - No multi-type memory system
- **Citation Strategy**: "Asada [2025] proposes LLM integration for affective memory as future work; BabyBrain already implements LLM-driven emotional processing with computational models of compound emotion derivation affecting learning rates and memory consolidation."
- **Related Keywords**: Artificial empathy, affective development, moral cognition, pain modeling

---

## 5. Animal or Machine? Neuromodulated Emotions and their Effect on Affinity
- **IEEE Xplore ID**: 11204403
- **Authors**: (Hazel robot development team)
- **Pages**: 1-6
- **Key Contribution**: Presents Hazel, a zoomorphic robotic dog system with neuromodulated emotion system based on biological parameters (Cortisol, Adrenaline, Dopamine) that conveys five emotional states: Happiness, Excitement, Anger, Fear, and Possessiveness. Tested with 100 children aged 9-11 in school setting; found children could identify emotional states and attribute agency/internal desires to the system.
- **Methods**: Neuromodulation, emotion expression, child interaction study
- **Overlap with BabyBrain**:
  - Neuromodulated emotion system
  - Biologically-grounded emotional modeling
  - Developmental appropriateness (children study)
- **Threat Level**: **3/5**
- **What BabyBrain does they don't**:
  - No LLM or cognitive processing
  - Emotions are for EXPRESSION only (output); ours MODULATE cognition (affect learning rates, memory consolidation, goal generation)
  - No developmental stages
  - No memory system
  - No compound emotions (only 5 basic states)
  - No brain region mapping
  - No language/conversation capabilities
  - Robot is purely expressive; we're cognitive architecture
- **Citation Strategy**: "While Hazel uses neuromodulated emotions for social expression to overcome uncanny valley effects, BabyBrain's emotion system directly modulates cognitive processes: learning rates, memory consolidation strength, and generation of new goals aligned with emotional state."
- **Related Keywords**: Neuromodulation, emotion expression, child-robot interaction, affinity

---

## 6. Emulating Perceptual Development in Deep Reinforcement Learning
- **IEEE Xplore ID**: 11204434
- **Authors**: (Not fully extracted)
- **Pages**: 1-6
- **Key Contribution**: Explores how emulated perceptual development (EPD) in RL settings can improve learning compared to standard RL. In Pong game environment, the agent's state space representation changes in developmental stages (inspired by progressive perceptual development in infants), demonstrating faster convergence and better final performance than baseline learners.
- **Methods**: Staged RL, state space expansion, policy gradient learning
- **Overlap with BabyBrain**:
  - Developmental stages concept
  - Infant-inspired learning approach
  - Staged capability unlocking
- **Threat Level**: **3/5**
- **What BabyBrain does they don't**:
  - No LLM backbone
  - Stages are pre-scheduled (hard-coded development timeline); ours are experience-driven
  - Only perceptual stages; we gate multiple cognitive capabilities (prediction, imagination, causal reasoning)
  - No memory system (episodic/semantic/procedural)
  - No emotion system
  - No brain region mapping
  - Very narrow domain (single Pong game); we operate in open-ended conversational domain
  - No language capabilities
- **Citation Strategy**: "Unlike [this work]'s pre-scheduled perceptual state space expansion, BabyBrain's developmental stages emerge adaptively from accumulated experience and gate increasingly complex cognitive capabilities (prediction, imagination, causal reasoning) across conversational domains."
- **Related Keywords**: Perceptual development, staged learning, RL, infant-inspired

---

## 7. MIMo grows! Simulating body and sensory development in a multimodal infant model
- **IEEE Xplore ID**: 11204381
- **Authors**: trieschlab group (cited 1x)
- **Pages**: 1-6
- **Cited**: Yes (1x)
- **Key Contribution**: Presents MIMo v2 -- an enhanced multimodal infant model with growing body (birth to 24 months), developing visual acuity with foveated vision, sensorimotor delays (finite signal transmission), inverse kinematics module, and random environment generation. Open-source framework for realistic sensorimotor development modeling.
- **Methods**: Embodied simulation, developmental kinematics, sensor simulation
- **Overlap with BabyBrain**:
  - Developmental stages (age-appropriate capabilities)
  - Infant development modeling
  - Multimodal sensory integration
- **Threat Level**: **3/5**
- **What BabyBrain does they don't**:
  - Pure sensorimotor/physical simulation (no cognitive architecture)
  - No LLM integration
  - No memory system
  - No emotion system
  - No language or conversation
  - This is a platform/tool for embodiment; ours is a cognitive architecture
  - Models body development, not cognitive/brain development
  - No anatomical brain region mapping
  - No sleep consolidation or Hebbian learning
- **Citation Strategy**: "While MIMo v2 provides a platform for simulating sensorimotor development, BabyBrain models cognitive development with integrated language processing, semantic memory networks, and emotional systems all operating through LLM-based reasoning."
- **Related Keywords**: Infant simulation, sensorimotor development, embodied learning, developmental platform

---

## 8. Modeling the impact of phonological and semantic connectivity on early vocabulary growth
- **IEEE Xplore ID**: 11204414
- **Authors**: (Norwegian longitudinal study, cited 1x)
- **Pages**: 1-6
- **Cited**: Yes (1x)
- **Key Contribution**: Investigates the extent to which early word learning is shaped by children's existing lexical knowledge vs. environment. Using longitudinal data from 17-36 month-old Norwegian children, demonstrates "rich-get-richer" pattern: semantically well-connected words in children's existing lexicons predict earlier acquisition of novel words. Phonological connectivity impedes learning except in early development with low semantic connectivity.
- **Methods**: Longitudinal empirical study, computational network analysis, predictive modeling
- **Overlap with BabyBrain**:
  - Semantic network structure driving vocabulary growth
  - Connectivity-based learning (related to our spreading activation)
  - Developmental vocabulary growth modeling
- **Threat Level**: **3/5**
- **What BabyBrain does they don't**:
  - Human empirical study only (no computational model implementation)
  - No LLM integration
  - No emotion system affecting learning rates
  - No brain region mapping
  - No developmental stages with gating
  - We computationally implement the spreading activation mechanism; they only analyze human data
  - No sleep consolidation
- **Citation Strategy**: "The 'rich-get-richer' vocabulary growth pattern documented in [this work] directly aligns with our spreading activation mechanism, where semantically well-connected concepts in our semantic neuron graph facilitate acquisition of new related concepts through contrastive learning."
- **Related Keywords**: Vocabulary development, semantic networks, phonological learning, connectivity

---

## 9. Unexpected Capability of Homeostasis for Open-ended Learning
- **IEEE Xplore ID**: 11204447
- **Authors**: (Project page: https://sites.google.com/view/movingsloth/projects/...)
- **Pages**: 1-6
- **Key Contribution**: Demonstrates that homeostatically-regulated reinforcement learning (HRRL) -- inspired by computational neuroscience -- enables continuous autonomous acquisition of diverse survival skills in open-ended environments (Crafter game). Agent learns foraging, water collection, shelter building, and enemy combat purely through homeostasis maintenance without extrinsic rewards, showing emergent integrated behaviors.
- **Methods**: Homeostatic RL, emergent behavior, open-ended learning
- **Overlap with BabyBrain**:
  - Internal motivation driving diverse behavior acquisition
  - Emergent complex behaviors from simple constraints
  - Bio-inspired cognition
- **Threat Level**: **3/5**
- **What BabyBrain does they don't**:
  - No LLM backbone
  - No explicit developmental stages with capability gating
  - Homeostatic drives ≠ emotion system
  - No multi-type memory system (episodic/semantic/procedural)
  - No emotion system affecting learning
  - No language capabilities
  - No brain region mapping
  - Focus is behavioral skill acquisition; ours is cognitive representation development
- **Citation Strategy**: "While HRRL demonstrates emergent behavioral skills from homeostatic regulation, BabyBrain achieves emergent cognitive development through emotion-modulated LLM reasoning with explicit memory formation and consolidation mechanisms."
- **Related Keywords**: Homeostasis, intrinsic motivation, open-ended learning, emergent behavior

---

## 10. MAGELLAN: Metacognitive predictions of learning progress guide autotelic LLM agents in large goal spaces
- **Source**: arXiv 2502.07709 (February 2025) -- likely presented/associated with ICDL 2025 community
- **Authors**: Loris Gaven, Thomas Carta, Clement Romac, Cedric Colas, Sylvain Lamprier, Olivier Sigaud, Pierre-Yves Oudeyer
- **Key Contribution**: Introduces MAGELLAN, a metacognitive framework enabling LLM agents to predict their own competence and learning progress in open-ended goal spaces with evolving dynamics. Uses semantic relationships between goals for sample-efficient LP estimation and enables dynamic curriculum learning without extensive sampling or expert-defined goal groupings.
- **Methods**: Metacognitive monitoring, competence prediction, semantic goal clustering
- **Overlap with BabyBrain**:
  - LLM-based agent with developmental progression
  - Metacognitive self-assessment
  - Learning progress tracking
  - Open-ended goal space exploration
- **Threat Level**: **3/5**
- **What BabyBrain does they don't**:
  - No multi-type memory system (episodic/semantic/procedural)
  - No emotion system affecting learning
  - No anatomical brain region mapping
  - No sleep consolidation or Hebbian plasticity
  - Their "development" is curriculum optimization; ours models infant cognitive development stages
  - No spreading activation mechanism
  - Focus is goal selection optimization; ours is comprehensive cognitive architecture
- **Citation Strategy**: "MAGELLAN uses metacognitive learning progress prediction for curriculum optimization; BabyBrain models cognitive development as a comprehensive process including memory formation, emotional modulation, stage-gated capability emergence, and offline consolidation."
- **Related Keywords**: Metacognition, learning progress, LLM agents, curriculum learning

---

# TIER 2: MODERATE RELEVANCE PAPERS (Threat Level 2/5)

## 11. Robot Learning Theory of Mind through Self-Observation: Exploiting the Intentions-Beliefs Synergy
- **IEEE Xplore ID**: 11204407
- **Authors**: Francesca Bianco et al., University of Essex, Colchester, UK
- **Pages**: 1-7
- **Key Contribution**: Demonstrates that robots can learn Theory of Mind by observing their own decision processes in partially observable environments. Shows synergy between learning low-level mental states (intentions, goals) and high-level ones (beliefs): faster and more accurate prediction when both are learned simultaneously. Uses feedforward deep learning model.
- **Overlap**: Cognitive development, belief/intention modeling, internal state inference, robot learning
- **Threat Level**: **2/5**
- **Differentiator**: Narrow focus on Theory of Mind learning. No LLM, no memory system, no emotion, no developmental stages, no brain mapping. Uses deep learning, not LLM.

---

## 12. Teaching a Robot to Read Faces: Incremental Emotion Learning with Selective Visual Attention
- **IEEE Xplore ID**: 11204441
- **Authors**: (developmental AI robot team)
- **Pages**: 1-6
- **Key Contribution**: Presents system for robots to learn facial emotion recognition through imitation game (behavioral matching) combined with attention-focusing mechanism. Studies how visual field restrictions affect emotion recognition accuracy; results show consistency with human perception patterns.
- **Overlap**: Emotion recognition, incremental learning, developmental robotics, attention mechanisms
- **Threat Level**: **2/5**
- **Differentiator**: Emotion recognition only (not generation or modulation of cognition). No LLM, no memory, no developmental stages, no brain mapping. Robot learns to perceive emotions, not to use them for reasoning.

---

## 13. From Action to Protocol: The Emergence of Proto-Verbal Structure in Multi-Agent Communication Systems
- **IEEE Xplore ID**: 11204402
- **Authors**: Yu Wei, Yasuo Kuniyoshi
- **Pages**: 1-6
- **Key Contribution**: Multi-agent framework investigating how agents develop communication protocols for coordinating complex actions (navigation, object manipulation). Discovers "prototype consistency" -- emergence of shared message prefixes for categorically similar tasks, resembling verb-like structures in natural language. Ablation studies show linguistic organization emerges from listeners' learned behavioral patterns.
- **Overlap**: Language emergence, action-language grounding, developmental communication, symbol grounding
- **Threat Level**: **2/5**
- **Differentiator**: Multi-agent communication focus. No LLM, no developmental stages, no memory types, no emotion. Emergent language from action coordination vs. our LLM-based conversational language.

---

## 14. PRAG: Procedural Action Sequence Symbolic Generator as a Mechanism for Autonomous Learning
- **IEEE Xplore ID**: 11204420
- **Authors**: (Not fully extracted)
- **Pages**: 1-8
- **Key Contribution**: Introduces PRAG, a generative mechanism for constructing multi-step manipulation tasks mirroring cognitive developmental processes. Given atomic actions, objects, and spatial predicates, autonomously produces novel, solvable task sequences of specified complexity. Validates through symbolic consistency and physical feasibility checks, enabling curriculum-based progressive learning.
- **Overlap**: Procedural learning, developmental processes, progressive skill acquisition, curriculum learning
- **Threat Level**: **2/5**
- **Differentiator**: Task generation tool for robotic manipulation, not cognitive architecture. No LLM, no memory system, no emotion. Focused on procedural task structure, not cognitive development.

---

## 15. Fast or Slow: Adaptive Decision-Making in Reinforcement Learning with Pre-Trained LLMs
- **IEEE Xplore ID**: 11204357
- **Authors**: Katrine Linnea Nergård, Kai Olav Ellefsen, Jim Torresen
- **Pages**: 1-7
- **Key Contribution**: Investigates using pre-trained LLMs in RL to mimic human adaptive reasoning. Inspired by dual-system theory of cognition (fast intuitive vs. slow deliberate), LLM guides RL agent between two policies without fine-tuning. Grid-world experiments show LLM can dynamically select appropriate mode for varying situations.
- **Overlap**: LLM-based cognition, cognitive theory-inspired architecture, dual-process thinking
- **Threat Level**: **2/5**
- **Differentiator**: Grid-world domain only. No developmental stages, no memory, no emotion, no brain mapping. Uses LLM for decision routing, not as cognitive backbone of comprehensive architecture.

---

## 16. Performance of Large Language Models and Analysis of Responses in the Wisconsin Card Sorting Task
- **IEEE Xplore ID**: 11204408
- **Authors**: (Not fully extracted)
- **Pages**: 1-7
- **Key Contribution**: Applies Wisconsin Card Sorting Task (cognitive flexibility benchmark) to various LLMs (ChatGPT o1, ChatGPT o1-mini, Gemini 1.5/2.0). Finds rule-response mismatch and varying tendencies in integrating bottom-up card information with top-down rule-based reasoning. Contributes to "machine psychology" framework.
- **Overlap**: LLM cognitive capabilities, cognitive flexibility assessment, machine psychology
- **Threat Level**: **2/5**
- **Differentiator**: Analysis/evaluation paper (no architecture). Tests existing LLMs rather than building developmental systems. No memory, no emotion, no stages.

---

## 17. Decentralized Collective World Model for Emergent Communication and Coordination
- **IEEE Xplore ID**: 11204457
- **Authors**: Kentaro Nomura, Tatsuya Aoki, Tadahiro Taniguchi, Takato Horii (cited 2x)
- **Pages**: 1-8
- **Key Contribution**: Proposes fully decentralized multi-agent world model enabling both symbol emergence and coordinated behavior. Agents develop communication through world models predicting environmental dynamics and message exchange with contrastive learning. Outperforms non-communicative models when agents have divergent perceptions.
- **Overlap**: World model, symbol emergence, shared representations, multi-agent learning
- **Threat Level**: **2/5**
- **Differentiator**: Multi-agent coordination focus. No LLM, no developmental stages, no memory types, no emotion. Symbol emergence for communication, not for cognitive development.

---

## 18. Push, See, Predict: Emergent Perception Through Intrinsically Motivated Play
- **IEEE Xplore ID**: 11204356
- **Authors**: Orestis Konstantaropoulos, Mehdi Khamassi, Petros Maragos, George Retsinas
- **Pages**: 1-7
- **Key Contribution**: Presents fully self-supervised, object-centric learning framework inspired by children's curious play. Robot first segments input via Slot Attention, then trains graph-based world model. Intrinsically motivated reward (world model prediction error) drives policy to collect informative trajectories, improving prediction/reconstruction up to 3x over random baseline.
- **Overlap**: Intrinsic motivation, world model, prediction learning, infant-inspired exploration, self-supervised learning
- **Threat Level**: **2/5**
- **Differentiator**: Sensorimotor learning focus. No LLM, no memory system, no emotion, no developmental stages, no language. Robot learns object dynamics, not cognitive representation.

---

## 19. Interacting with Other Agents Without a-priori Knowledge: a Radical Interactionist Architecture Developing From the Ground-Up the Ability to Infer Motivations and Predict Behaviour
- **IEEE Xplore ID**: 11204437
- **Authors**: (Not fully extracted)
- **Pages**: 1-7
- **Key Contribution**: Proposes developmental agent architecture based on Radical Interactionism principles that infers unknown motivations of other agents without prior knowledge. Learns to predict behavior through interaction in prey-predator multi-agent context without external rewards, demonstrating ground-up capability development.
- **Overlap**: Developmental agent architecture, motivation inference, ground-up learning, multi-agent development
- **Threat Level**: **2/5**
- **Differentiator**: Multi-agent interaction focus. No LLM, no memory types, no emotion system, no developmental stages, no brain mapping. Focuses on behavioral prediction rather than cognitive development.

---

## 20. Computational models of the emergence of self-exploration in 2-month-old infants
- **IEEE Xplore ID**: 11204351
- **Authors**: (Not fully extracted)
- **Pages**: 1-6
- **Key Contribution**: Computational modeling of how self-exploration emerges in very young infants (around 2 months of age). Models early motor development and sensorimotor exploration behaviors.
- **Overlap**: Infant developmental modeling, emergence of cognitive capabilities, motor development
- **Threat Level**: **2/5**
- **Differentiator**: Very early sensorimotor development only. No LLM, no memory, no emotion, no language. Models physical motor development, not cognitive architecture.

---

# TIER 3: LOW RELEVANCE BUT WORTH NOTING (Threat Level 1/5)

## 21-55: Papers with Limited Overlap

| # | Title | ID | Authors | Overlap | Reason for Threat 1 |
|---|-------|-----|---------|---------|------------------|
| 21 | Canalizing Babbling: Development-Inspired Goal Sampling for Visuo-Motor Learning | 11204428 | (Not extracted) | Motor babbling/exploration, infant-inspired | Sensorimotor only, no cognitive modeling |
| 22 | Comparative learning signals lead to aligned representations in an infant-inspired visual task | 11204396 | (Not extracted) | Infant-inspired visual learning | Visual learning only, no developmental stages |
| 23 | Analyzing Multimodal Integration in the Variational Autoencoder | 11204413 | Carlotta Langer et al., University of Essex | Multimodal integration | Pure ML method, no developmental focus |
| 24 | A Cognitively-Inspired Ensemble Architecture for Robust Decision-Making | 11204432 | (Not extracted) | Cognitive decision-making ensemble | URL classification task, narrow domain |
| 25 | Purpose-driven Open-Ended Learning: biasing OEL through external guidance | 11204395 | Andrea Morelli et al. | Intrinsic/extrinsic motivation | Open-ended learning focus, not development |
| 26 | Robots that Learn to Solve Symbolic Novelties with Self-Generated RL Simulations | 11204430 | (Not extracted) | Self-generated simulation, world model | Robotic manipulation focus, not cognitive |
| 27 | Cyclic Exploration and Exploitation in Surprise Minimizing RL | 11204397 | (Not extracted) | Surprise minimization, exploration-exploitation | RL algorithm focus, not development |
| 28 | A3RNN: Bi-directional Fusion of Bottom-up and Top-down Process for Developmental Visual Attention in Robots | 11204426 | (Not extracted) | Developmental attention mechanisms | Visual attention only, no broader cognition |
| 29 | Variational Adaptive Noise and Dropout towards Stable Recurrent Neural Networks | 11204433 | (Not extracted) | Stable RNN learning, imitation learning | Pure ML method, no developmental model |
| 30 | The Ungrounded Alignment Problem | 11204348 | (Not extracted) | Innate behavior in learning systems | Narrow theory problem, limited practical scope |
| 31 | Towards Understanding Ambiguity Resolution in Multimodal Inference of Meaning | 11204410 | Yufei Wang et al., University of Pittsburgh | Word meaning inference, multimodal context | Language learning task but human-focused |
| 32 | Simulated Cortical Magnification Supports Self-Supervised Object Learning | 11204429 | (Not extracted) | Cortical-inspired vision, self-supervised | Vision-specific, not general cognition |
| 33 | Free Lunch? Low-Cost Intelligence Through Pattern-Guided Exploration | 11204411 | (Not extracted) | Pattern-guided exploration, intrinsic motivation | Exploration algorithm focus |
| 34 | Predictability-Based Curiosity-Guided Action Symbol Discovery | 11204386 | (Not extracted) | Action symbol discovery, curiosity-driven | Symbol learning focus, not broad development |
| 35 | Contingent behavior during caregiver-child interaction improves word learning | 11204427 | (Not extracted) | Word learning, social interaction | Empirical study, not computational model |
| 36 | Who Said What (WSW 2.0)? Enhanced Automated Analysis of Preschool Classroom Speech | 11204438 | (Not extracted) | Speech analysis, child speech | Analysis tool, not cognitive architecture |
| 37 | Contingencies Across Object and Action Labeling in Mother-Infant Object Play | 11204439 | (Not extracted) | Object/action labeling, mother-infant | Empirical study of human interaction |
| 38 | Parents and Children Jointly Create Multimodal Semantic Regularities During Naturalistic Toy Play | 11204452 | (Not extracted) | Semantic regularities in play | Empirical analysis, not computational |
| 39 | Probabilistic Fusion of Deictic Gestures and Language Command | 11204446 | (Not extracted) | Gesture-language fusion, robot instruction | Robot control focus |
| 40 | Exploring Tactile Perception for Object Localization in Granular Media | 11204359 | (Not extracted) | Tactile perception, object localization | Sensorimotor perception only |
| 41 | Using VR and Psychophysics to Test Embodied Cognitive Flexibility in Children with ADHD | 11204431 | (Not extracted) | Cognitive flexibility in children | Empirical study with clinical focus |
| 42 | Identifying and Localizing Dynamic Affordances to Improve Interactions | 11204390 | (Not extracted) | Affordance learning, multi-agent interaction | Affordance learning focus |
| 43 | Object-Centric Action-Enhanced Representations for Robot Visuo-Motor Policy | 11204392 | (Not extracted) | Object-centric learning, visuo-motor | Robot control focus |
| 44 | Behavioral Modeling of Pedestrian Agents: A Value-Driven Approach | 11204399 | (Not extracted) | Pedestrian behavior modeling | Pedestrian simulation, not cognitive |
| 45 | Towards a Novel Method for Evaluating Gait Stability | 11204400 | (Not extracted) | Gait stability analysis | Biomechanics focus |
| 46 | How Socioeconomic Status and Home Environment Influence Early Cognitive Development | 11204405 | (Not extracted) | Social factors in child development | Human empirical study |
| 47 | Exploring within-task calibration in free-flowing manual sampling in 9-month-olds | 11204387 | (Not extracted) | Infant exploration, object interaction | Empirical infant study |
| 48 | The role of social cues in infants' word segmentation with a Furhat Robot | 11204451 | (Not extracted) | Word segmentation, robot interaction | Infant-robot interaction study |
| 49 | Camera-based Assessment of Gendered Toy Preference in Free-Play Parent-Child | 11204419 | (Not extracted) | Toy preference, parent-child interaction | Empirical behavioral study |
| 50 | Automated head-turn estimation from nose position in infant videos | 11204409 | (Not extracted) | Infant head-turn detection | Computer vision tool, not cognitive |
| 51 | Intrinsic Reward Decomposition for Soft Robotic Manipulation Tasks | 11204455 | (Not extracted) | Intrinsic reward, soft robotics | Robotic control focus |
| 52 | Learning Locomotion by Co-Evolution of Morphological and Neural Parameters | 11204450 | (Not extracted) | Morphological evolution, locomotion | Embodied learning, not cognition |
| 53 | Groups Matter: Investigating Effects of Homophily in Child Interactions | 11204354 | (Not extracted) | Child social dynamics, group behavior | Empirical social study |
| 54 | Exploring Multimodal and Verbal Cues in Naturalistic Caregiver-Infant Joint Attention | 11204353 | (Not extracted) | Joint attention development, multimodal | Empirical infant study |
| 55 | Measuring predictability in the home environment using daylong audio recordings | 11204360 | (Not extracted) | Environmental predictability, audio analysis | Environmental analysis tool |

---

## 56-89: Minimal Overlap Papers (Threat 0/5)

Remaining papers focus on:
- Specific sensorimotor skills (reaching, grasping, locomotion)
- Empirical studies of human infants/children
- Engineering/robotics tasks (manipulation, navigation)
- Analysis tools and datasets
- Specialized focus areas (attention, eye-gaze, speech)

These include papers on:
- Kinematic analysis of infant movements (11204442)
- Infant gaze following (11204352)
- Personalized motion retargeting (11204350)
- School-age children exploration (11204349)
- Generative to discriminative knowledge distillation (11204436)
- Feature-based Lie Group Transformers (11204453)
- Graph-theory approaches for block construction (11204448)
- Whisper ASR benchmarking (11204445)
- Visual search attention modeling (11204443)
- Temporal relation of gestures and language (11204382)
- Turn-taking in children (11204384)
- Unified attention modeling (11204383)
- Facial emotion landmarks (11204422)
- Bipedal locomotion evaluation (11204404)
- And others focused on specific empirical studies or engineering challenges

---

# SYNTHESIS: THREAT ASSESSMENT SUMMARY

## Threat Level Distribution

| Level | Count | Papers |
|-------|-------|--------|
| **4/5** | 1 | Growing Perspectives |
| **3/5** | 9 | Homeostasis, Always-On, Silicopathy, Neuromodulated Emotions, Emulating Perceptual Dev, MIMo, Vocabulary Growth, HRRL, MAGELLAN |
| **2/5** | 10 | ToM, Emotion Recognition, Proto-Verbal, PRAG, Fast/Slow, WCST, World Model, Push/See/Predict, Radical Interactionist, Self-exploration |
| **1/5** | 25+ | Various domain-specific papers |
| **0/5** | 35+ | Minimal overlap, empirical studies, engineering tasks |

## Key Insight

**NO ICDL 2025 paper combines LLM + developmental stages + multi-type memory + emotion system + brain mapping + sleep consolidation.**

BabyBrain is **genuinely novel** at ICDL 2025.

---

# RECOMMENDATIONS

## Papers to Cite in BabyBrain ICDL Paper

### Must Cite (Tier 1)
1. Growing Perspectives [11204394]
2. Homeostasis Driven Learning [11204417]
3. Always-On Architecture [11204444]
4. Neuromodulated Emotions [11204403]
5. Vocabulary Growth Model [11204414]
6. MIMo grows [11204381]

### Should Cite (Show Awareness)
7. Emulating Perceptual Development [11204434]
8. Silicopathy [11204355]
9. Proto-Verbal Structure [11204402]
10. Wisconsin Card Sorting [11204408]
11. MAGELLAN [2502.07709]

### Could Cite (For Completeness)
12. Fast or Slow [11204357]
13. Radical Interactionist [11204437]
14. PRAG [11204420]
15. Push See Predict [11204356]

---

# MANUSCRIPT FRAMING

**Opening:** "While ICDL 2025 demonstrates progress in individual aspects of developmental learning -- memory consolidation [11204444], emotional expression [11204403], staged perception [11204434], and vocabulary growth [11204414] -- these advances remain largely isolated from each other. We present BabyBrain, the first integrated cognitive architecture that combines..."

**Novelty Claim:** "Previous developmental systems address individual components in isolation. BabyBrain is the first to integrate: (1) LLM-based reasoning as the cognitive engine, (2) emergent developmental stage transitions based on experience, (3) three-type memory with Hebbian consolidation, (4) compound emotion-based learning modulation, and (5) anatomical brain region mapping with spreading activation."

**Positioning:** "ICDL research has predominantly focused on embodied sensorimotor development in physical robots. BabyBrain shifts the paradigm to model cognitive development in conversational agents, leveraging recent advances in LLMs while grounding them in developmental science."
