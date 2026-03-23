# Neo4j & Redis Connection Patterns — Detailed Reference

## Neo4j AuraDB Free: Complete Connection Code

### Environment Variables

```env
NEO4J_URI=bolt+s://b76cbc85.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=<password>
NEO4J_DATABASE=b76cbc85
```

### Full Connection Pattern (Python)

```python
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

ENTRY_URI = os.getenv("NEO4J_URI")   # bolt+s://b76cbc85.databases.neo4j.io
USERNAME  = os.getenv("NEO4J_USERNAME")
PASSWORD  = os.getenv("NEO4J_PASSWORD")
DB_NAME   = os.getenv("NEO4J_DATABASE")  # b76cbc85
AUTH = (USERNAME, PASSWORD)

# Step 1: Query system DB for writer address
with GraphDatabase.driver(ENTRY_URI, auth=AUTH) as d:
    res = d.execute_query(
        f'SHOW DATABASES YIELD name, address, writer '
        f'WHERE name = "{DB_NAME}" AND writer = true',
        database_="system"
    )
    if not res.records:
        raise RuntimeError(f"No writer found for database '{DB_NAME}'")
    writer_host = res.records[0]["address"]  # e.g. p-mt-xxx.neo4j.io:7687

# Step 2: Connect directly to writer node
writer_uri = f"bolt+s://{writer_host.split(':')[0]}"
with GraphDatabase.driver(writer_uri, auth=AUTH) as d:
    with d.session() as s:
        result = s.run("MATCH (n) RETURN count(n) AS total").single()["total"]
```

### Async Pattern (for FastAPI)

```python
from neo4j import AsyncGraphDatabase

async def get_neo4j_writer_uri():
    async with AsyncGraphDatabase.driver(ENTRY_URI, auth=AUTH) as d:
        res = await d.execute_query(
            f'SHOW DATABASES YIELD name, address, writer '
            f'WHERE name = "{DB_NAME}" AND writer = true',
            database_="system"
        )
        writer_host = res.records[0]["address"]
        return f"bolt+s://{writer_host.split(':')[0]}"
```

## Database Statistics (2026-03-19, Post-Migration)

### Node Counts

| Label | Count | Notes |
|-------|-------|-------|
| Concept | 820 | Core semantic concepts (neurons) |
| Experience | 3,039 | Interaction experiences |
| EmotionLog | 1,503 | Emotional state snapshots |
| CuriosityLog | 811 | Curiosity-driven explorations |
| SleepLog | 2,716 | Memory consolidation events |
| Procedure | 102 | Procedural knowledge patterns |
| AutonomousGoal | 146 | Self-generated goals |
| BrainRegion | 9 | Brain architecture regions |

### Relationship Counts

| Type | Count | Between |
|------|-------|---------|
| RELATES_TO | 680 | Concept ↔ Concept |
| MAPPED_TO | 820 | Concept → BrainRegion |
| INVOLVES | 1,060 | Experience → Concept |
| CAUSES | 3 | Concept → Concept (causal) |

### Vector Indexes

| Index Name | Status | Dimensions | Node Label |
|-----------|--------|------------|------------|
| concept_embeddings | ONLINE | 1536 (OpenAI) | Concept |
| experience_embeddings | ONLINE | 1536 (OpenAI) | Experience |
| visual_embeddings | ONLINE | 1536 (OpenAI) | VisualExperience |

**Embedding coverage**:
- Concept: 148/820 have embeddings (18%)
- Experience: 106/3039 have embeddings (3.5%)

### Common Cypher Queries

```cypher
-- Count all nodes by label
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC

-- Get baby state
MATCH (s:BabyState) RETURN s LIMIT 1

-- Concept with relations
MATCH (c:Concept)-[r:RELATES_TO]-(other:Concept)
WHERE c.name = $name
RETURN c, r, other

-- Vector similarity search (requires embedding)
CALL db.index.vector.queryNodes('concept_embeddings', 10, $embedding)
YIELD node, score
RETURN node.name, node.description, score

-- Recent experiences
MATCH (e:Experience)
RETURN e ORDER BY e.created_at DESC LIMIT 10
```

## Redis (Upstash) Connection — Full Pattern

### Environment Variables

```env
REDIS_URL=rediss://default:<password>@clean-polecat-38197.upstash.io:6379
```

### Basic Connection (Async)

```python
import redis.asyncio as aioredis

client = aioredis.from_url(
    REDIS_URL,
    ssl_cert_reqs=None,  # Required for Upstash self-signed cert
    decode_responses=True,
)

# Basic operations
await client.set("key", "value", ex=60)  # 60s expiry
val = await client.get("key")
await client.delete("key")
await client.aclose()  # Always close
```

### Pub/Sub Pattern (for SSE)

```python
# Publisher
pub_client = aioredis.from_url(REDIS_URL, ssl_cert_reqs=None, decode_responses=True)
await pub_client.publish("baby-ai:channel", "message-data")

# Subscriber
sub_client = aioredis.from_url(REDIS_URL, ssl_cert_reqs=None, decode_responses=True)
async with sub_client.pubsub() as ps:
    await ps.subscribe("baby-ai:channel")
    async for msg in ps.listen():
        if msg["type"] == "message":
            process(msg["data"])
```

### Key Gotchas

1. **`rediss://` not `redis://`** — TLS is mandatory for Upstash
2. **`ssl_cert_reqs=None`** — Required for Upstash's certificate
3. **Pub/Sub requires TCP** — HTTP REST SDK cannot do Pub/Sub
4. **Always `aclose()`** — Prevent connection leaks in async code
