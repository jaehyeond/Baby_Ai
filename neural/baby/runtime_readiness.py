"""Read-only runtime readiness checks and explicit initialization helpers."""

from __future__ import annotations

import asyncio
import math
import os
from collections.abc import Awaitable, Callable, Mapping
from typing import Any


DEFAULT_READINESS_TIMEOUT_SECONDS = 2.0
DEFAULT_EXPERIENCE_VECTOR_INDEX = "experience_embeddings"

REQUIRED_CONSTRAINTS = frozenset({
    "concept_id",
    "experience_id",
    "brain_region_name",
    "baby_state_id",
    "emotion_log_id",
    "prediction_id",
    "imagination_id",
    "procedure_id",
    "visual_exp_id",
    "pending_q_id",
    "autonomous_goal_id",
    "curiosity_log_id",
    "user_model_sid",
})
REQUIRED_LOOKUP_INDEX_SPECS = {
    "concept_category": ("Concept", "category"),
    "concept_strength": ("Concept", "strength"),
    "experience_created": ("Experience", "created_at"),
    "experience_stage": ("Experience", "development_stage"),
    "pending_q_status": ("PendingQuestion", "status"),
    "emotion_log_created": ("EmotionLog", "created_at"),
    "exp_hour": ("Experience", "hour_of_day"),
    "exp_speaker": ("Experience", "speaker_id"),
    "tp_time_slot": ("TemporalPattern", "time_slot"),
}
REQUIRED_LOOKUP_INDEXES = frozenset(REQUIRED_LOOKUP_INDEX_SPECS)


def readiness_timeout(environ: Mapping[str, str] | None = None) -> float:
    """Return a bounded per-check timeout without rejecting startup."""
    source = os.environ if environ is None else environ
    try:
        value = float(source.get("BABY_READINESS_TIMEOUT_SECONDS", ""))
    except (TypeError, ValueError):
        return DEFAULT_READINESS_TIMEOUT_SECONDS
    if not math.isfinite(value) or value <= 0:
        return DEFAULT_READINESS_TIMEOUT_SECONDS
    return min(value, 30.0)


def experience_vector_index_name(
    environ: Mapping[str, str] | None = None,
) -> str:
    """Resolve the configured Experience vector index registry name."""
    source = os.environ if environ is None else environ
    configured = source.get("BABY_EXPERIENCE_VECTOR_INDEX", "").strip()
    return configured or DEFAULT_EXPERIENCE_VECTOR_INDEX


def _failure(component: str, exc: BaseException) -> dict[str, Any]:
    timed_out = isinstance(exc, TimeoutError)
    return {
        "healthy": False,
        "status": "timed_out" if timed_out else "failed",
        "error_code": "timeout" if timed_out else "check_failed",
        "message": f"{component} readiness check failed",
    }


async def _records(result: Any) -> list[dict[str, Any]]:
    if hasattr(result, "data"):
        data = await result.data()
        return [dict(row) for row in data]
    rows = await result.fetch(10_000)
    return [dict(row) for row in rows]


async def _neo4j_ping(driver: Any, database: str | None) -> None:
    async with driver.session(database=database) as session:
        result = await session.run("RETURN 1 AS ready")
        record = await result.single()
        if record is None or record["ready"] != 1:
            raise RuntimeError("unexpected Neo4j readiness response")


async def _neo4j_schema(driver: Any, database: str | None) -> dict[str, Any]:
    async with driver.session(database=database) as session:
        indexes_result = await session.run(
            "SHOW INDEXES YIELD name, type, entityType, state, labelsOrTypes, properties "
            "RETURN name, type, entityType, state, labelsOrTypes, properties"
        )
        indexes = await _records(indexes_result)
        constraints_result = await session.run(
            "SHOW CONSTRAINTS YIELD name RETURN name"
        )
        constraints = await _records(constraints_result)
    return {"indexes": indexes, "constraints": constraints}


def _schema_checks(
    registry: dict[str, Any],
    vector_index_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    indexes = [dict(item) for item in registry["indexes"]]
    indexes_by_name = {str(item.get("name")): item for item in indexes}
    constraint_names = {str(item.get("name")) for item in registry["constraints"]}

    missing_constraints = sorted(REQUIRED_CONSTRAINTS - constraint_names)
    resolved_lookup: dict[str, str] = {}
    missing_lookup: list[str] = []
    offline_lookup: list[dict[str, Any]] = []
    wrong_shape_lookup: list[dict[str, Any]] = []
    for logical_name, (label, prop) in REQUIRED_LOOKUP_INDEX_SPECS.items():
        shape_matches = [
            item
            for item in indexes
            if str(item.get("entityType", "")).upper() == "NODE"
            and str(item.get("type", "")).upper() == "RANGE"
            and list(item.get("labelsOrTypes") or []) == [label]
            and list(item.get("properties") or []) == [prop]
        ]
        online = [
            item
            for item in shape_matches
            if str(item.get("state", "")).upper() == "ONLINE"
        ]
        if online:
            resolved_lookup[logical_name] = sorted(
                str(item.get("name")) for item in online
            )[0]
            continue
        if shape_matches:
            offline_lookup.append({
                "requirement": logical_name,
                "names": sorted(str(item.get("name")) for item in shape_matches),
            })
            continue

        named = indexes_by_name.get(logical_name)
        if named is not None:
            wrong_shape_lookup.append({
                "requirement": logical_name,
                "name": logical_name,
                "entity_type": named.get("entityType"),
                "type": named.get("type"),
                "labels_or_types": list(named.get("labelsOrTypes") or []),
                "properties": list(named.get("properties") or []),
            })
        else:
            missing_lookup.append(logical_name)

    schema_healthy = (
        not missing_constraints
        and not missing_lookup
        and not offline_lookup
        and not wrong_shape_lookup
    )
    schema = {
        "healthy": schema_healthy,
        "status": "ready" if schema_healthy else "schema_mismatch",
        "missing_constraints": missing_constraints,
        "missing_indexes": sorted(missing_lookup),
        "offline_indexes": offline_lookup,
        "wrong_shape_indexes": wrong_shape_lookup,
        "resolved_indexes": resolved_lookup,
    }

    vector = indexes_by_name.get(vector_index_name)
    expected_labels = ["Experience"]
    expected_properties = ["embedding"]
    vector_details = {
        "required": True,
        "name": vector_index_name,
        "healthy": False,
        "status": "missing",
        "expected_labels_or_types": expected_labels,
        "expected_properties": expected_properties,
    }
    if vector is not None:
        state = str(vector.get("state", "")).upper()
        index_type = str(vector.get("type", "")).upper()
        labels = list(vector.get("labelsOrTypes") or [])
        properties = list(vector.get("properties") or [])
        shape_matches = labels == expected_labels and properties == expected_properties
        type_matches = index_type == "VECTOR"
        online = state == "ONLINE"
        vector_details.update({
            "state": state,
            "type": index_type,
            "labels_or_types": labels,
            "properties": properties,
            "healthy": online and type_matches and shape_matches,
            "status": (
                "ready"
                if online and type_matches and shape_matches
                else "schema_mismatch"
                if not shape_matches or not type_matches
                else "offline"
            ),
        })
    return schema, vector_details


def _provider_status(environ: Mapping[str, str]) -> dict[str, Any]:
    conversation_configured = bool(
        environ.get("GOOGLE_API_KEY") or environ.get("OPENAI_API_KEY")
    )
    embedding_configured = bool(environ.get("OPENAI_API_KEY"))
    return {
        "conversation": {
            "required": False,
            "configured": conversation_configured,
            "probed": False,
            "status": (
                "configured_not_probed"
                if conversation_configured
                else "not_configured"
            ),
        },
        "embedding": {
            "required": False,
            "configured": embedding_configured,
            "probed": False,
            "status": (
                "configured_not_probed"
                if embedding_configured
                else "not_configured"
            ),
        },
    }


async def build_readiness_report(
    *,
    neo4j_getter: Callable[[], Any],
    neo4j_reconnect: Callable[[], Awaitable[Any]] | None = None,
    redis_getter: Callable[[], Any],
    database: str | None,
    startup: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Probe required local services without changing data or calling providers."""
    source = os.environ if environ is None else environ
    timeout_seconds = readiness_timeout(source)
    vector_name = experience_vector_index_name(source)
    checks: dict[str, Any] = {}

    reconnect_attempted = False
    try:
        try:
            driver = neo4j_getter()
        except Exception:
            if neo4j_reconnect is None:
                raise
            reconnect_attempted = True
            await asyncio.wait_for(neo4j_reconnect(), timeout_seconds)
            driver = neo4j_getter()
        await asyncio.wait_for(_neo4j_ping(driver, database), timeout_seconds)
        checks["neo4j"] = {
            "healthy": True,
            "status": "ready",
            "reconnect_attempted": reconnect_attempted,
        }
    except Exception as exc:
        checks["neo4j"] = _failure("Neo4j", exc)
        checks["neo4j"]["reconnect_attempted"] = reconnect_attempted
        checks["schema"] = {
            "healthy": False,
            "status": "not_checked",
            "reason": "neo4j_unavailable",
        }
        checks["vector_search"] = {
            "required": True,
            "name": vector_name,
            "healthy": False,
            "status": "not_checked",
            "reason": "neo4j_unavailable",
        }
    else:
        try:
            registry = await asyncio.wait_for(
                _neo4j_schema(driver, database), timeout_seconds
            )
            checks["schema"], checks["vector_search"] = _schema_checks(
                registry, vector_name
            )
        except Exception as exc:
            checks["schema"] = _failure("Neo4j schema", exc)
            checks["vector_search"] = {
                "required": True,
                "name": vector_name,
                **_failure("Neo4j vector index", exc),
            }

    try:
        redis = redis_getter()
        ping = await asyncio.wait_for(redis.ping(), timeout_seconds)
        if ping is not True:
            raise RuntimeError("unexpected Redis readiness response")
        checks["redis"] = {"healthy": True, "status": "ready"}
    except Exception as exc:
        checks["redis"] = _failure("Redis", exc)

    startup_state = dict(startup or {"status": "not_requested", "mutated": False})
    startup_healthy = startup_state.get("status") != "failed"
    required = ("neo4j", "schema", "vector_search", "redis")
    ready = startup_healthy and all(checks[name].get("healthy") for name in required)
    return {
        "status": "healthy" if ready else "unhealthy",
        "ready": ready,
        "version": "2.0.0",
        "backend": "neo4j+redis",
        "timeout_seconds": timeout_seconds,
        "checks": checks,
        "startup_initialization": startup_state,
        "providers": _provider_status(source),
    }


async def run_explicit_initialization(
    db: Any,
    *,
    include_schema: bool = False,
    include_seed: bool = False,
) -> dict[str, Any]:
    """Run legacy schema/seed routines only through an explicit caller choice."""
    if not include_schema and not include_seed:
        return {
            "status": "not_requested",
            "mutation_attempted": False,
            "mutated": False,
        }

    completed: list[str] = []
    try:
        if include_schema:
            await db.ensure_indexes()
            completed.append("schema")
        if include_seed:
            await db.seed_brain_regions()
            completed.append("brain_regions")
            await db.seed_region_connections()
            completed.append("region_connections")
            await db.seed_identity_concepts()
            completed.append("identity_concepts")
    except Exception as exc:
        return {
            "status": "failed",
            "mutation_attempted": True,
            "mutation_result": "not_measured",
            "completed": completed,
            "error_code": "initialization_failed",
            "message": "Explicit schema/seed initialization failed",
        }
    return {
        "status": "completed",
        "mutation_attempted": True,
        "mutation_result": "not_measured",
        "completed": completed,
    }
