// Neo4j Schema DDL - Baby AI Migration Phase 1
// 실행 순서: 제약조건 → 일반 인덱스 → 벡터 인덱스 (순서 엄수)
// 모든 구문 IF NOT EXISTS로 재실행 안전
//
// 검증된 수치:
//   embedding dim = 1536 (OpenAI text-embedding-3-small)
//   AuraDB Free: 200K nodes / 400K relationships 한도
//
// 실행 방법: 각 구문을 AuraDB Browser에서 개별 실행 (세미콜론 구분)
// 또는 import_to_neo4j.py의 apply_schema() 함수로 자동 실행

// ============================================================
// SECTION 1: UNIQUE CONSTRAINTS (12개 노드 레이블)
// ============================================================

CREATE CONSTRAINT concept_id IF NOT EXISTS
  FOR (n:Concept) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT experience_id IF NOT EXISTS
  FOR (n:Experience) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT brain_region_name IF NOT EXISTS
  FOR (n:BrainRegion) REQUIRE n.name IS UNIQUE;

CREATE CONSTRAINT baby_state_id IF NOT EXISTS
  FOR (n:BabyState) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT emotion_log_id IF NOT EXISTS
  FOR (n:EmotionLog) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT prediction_id IF NOT EXISTS
  FOR (n:Prediction) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT imagination_id IF NOT EXISTS
  FOR (n:Imagination) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT procedure_id IF NOT EXISTS
  FOR (n:Procedure) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT visual_exp_id IF NOT EXISTS
  FOR (n:VisualExperience) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT pending_q_id IF NOT EXISTS
  FOR (n:PendingQuestion) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT autonomous_goal_id IF NOT EXISTS
  FOR (n:AutonomousGoal) REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT curiosity_log_id IF NOT EXISTS
  FOR (n:CuriosityLog) REQUIRE n.id IS UNIQUE;

// ============================================================
// SECTION 2: LOOKUP INDEXES
// ============================================================

CREATE INDEX concept_category IF NOT EXISTS
  FOR (n:Concept) ON (n.category);

CREATE INDEX concept_strength IF NOT EXISTS
  FOR (n:Concept) ON (n.strength);

CREATE INDEX experience_created IF NOT EXISTS
  FOR (n:Experience) ON (n.created_at);

CREATE INDEX experience_stage IF NOT EXISTS
  FOR (n:Experience) ON (n.development_stage);

CREATE INDEX pending_q_status IF NOT EXISTS
  FOR (n:PendingQuestion) ON (n.status);

CREATE INDEX emotion_log_created IF NOT EXISTS
  FOR (n:EmotionLog) ON (n.created_at);

// ============================================================
// SECTION 3: VECTOR INDEXES
// 중요: 데이터 임포트 완료 후 실행할 것 (인덱스 빌드 속도)
// dim=1536 (OpenAI text-embedding-3-small - 실측 확인)
// ============================================================

CREATE VECTOR INDEX concept_embeddings IF NOT EXISTS
  FOR (n:Concept) ON n.embedding
  OPTIONS {
    indexConfig: {
      `vector.dimensions`: 1536,
      `vector.similarity_function`: 'cosine'
    }
  };

CREATE VECTOR INDEX experience_embeddings IF NOT EXISTS
  FOR (n:Experience) ON n.embedding
  OPTIONS {
    indexConfig: {
      `vector.dimensions`: 1536,
      `vector.similarity_function`: 'cosine'
    }
  };

CREATE VECTOR INDEX visual_embeddings IF NOT EXISTS
  FOR (n:VisualExperience) ON n.embedding
  OPTIONS {
    indexConfig: {
      `vector.dimensions`: 1536,
      `vector.similarity_function`: 'cosine'
    }
  };

// ============================================================
// VERIFICATION QUERIES (실행 후 확인)
// ============================================================

// 인덱스 상태 확인 (ONLINE이 아닌 것이 0개여야 정상)
// SHOW INDEXES YIELD name, type, state WHERE state <> 'ONLINE' RETURN name, type, state;

// 전체 인덱스/제약조건 목록
// SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state RETURN *;
