---
name: neo4j-patterns
description: This skill should be used when writing Cypher queries, modifying Neo4j driver code, working with graph database connections, or creating database migration scripts for the Baby AI project. Contains critical AuraDB Free connection patterns and common pitfalls that cause silent failures. Also applies when working with Upstash Redis connections.
version: 1.0.0
---

# Neo4j & Redis Connection Patterns for Baby AI

Critical connection patterns verified through testing. Deviating from these patterns causes silent failures on AuraDB Free tier.

## Neo4j AuraDB Free — Three Traps

### Trap 1: `neo4j+s://` Protocol Fails

```
neo4j+s://b76cbc85.databases.neo4j.io
```

AuraDB Free is a single-node instance. The `neo4j+s://` protocol attempts routing table discovery, which fails on single-node deployments (Neo4j Community issue #74376, Windows 11).

### Trap 2: Direct `bolt+s://` to Instance — Writer Mismatch

```
bolt+s://b76cbc85.databases.neo4j.io
```

Connecting directly to the instance hostname does not guarantee routing to the writer node, causing intermittent write failures.

### Trap 3: Explicit `database_='b76cbc85'` — "Database Not Found"

Specifying the database name directly in the driver session results in "Database does not exist" errors, even though the database appears in system DB queries.

## Correct Connection Pattern

Two-step approach — always use this:

```python
# Step 1: Query system DB for writer address
with GraphDatabase.driver(ENTRY_URI, auth=AUTH) as d:
    res = d.execute_query(
        f'SHOW DATABASES YIELD name, address, writer '
        f'WHERE name = "{DB_NAME}" AND writer = true',
        database_="system"
    )
    writer_host = res.records[0]["address"]

# Step 2: Connect directly to writer node
writer_uri = f"bolt+s://{writer_host.split(':')[0]}"
with GraphDatabase.driver(writer_uri, auth=AUTH) as d:
    with d.session() as s:
        result = s.run("MATCH (n) RETURN count(n)")
```

**Driver version**: neo4j 6.1.0
**NEVER use**: `verify_connectivity()` — unreliable on AuraDB Free

## Redis (Upstash) Connection Pattern

- **Protocol**: `rediss://` (TLS required) — `redis://` will NOT work
- **Instance**: baby-ai-redis, GCP Tokyo (asia-northeast1)
- **Endpoint**: `clean-polecat-38197.upstash.io:6379`
- **Pub/Sub**: TCP connection required (HTTP REST SDK cannot do Pub/Sub)

```python
import redis.asyncio as aioredis

client = aioredis.from_url(
    REDIS_URL,
    ssl_cert_reqs=None,  # Upstash self-signed cert
    decode_responses=True,
)
```

## Additional Resources

For detailed code examples, vector index information, and database statistics:
- **`references/connection-patterns.md`** — Full connection code, node/relationship counts, vector indexes
