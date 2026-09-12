import asyncio

import dotenv
import pytest

_load_dotenv = dotenv.load_dotenv
dotenv.load_dotenv = lambda *_args, **_kwargs: False
try:
    from neural.baby import redis_client
finally:
    dotenv.load_dotenv = _load_dotenv

redis_connection_options = redis_client.redis_connection_options

from neural.baby.runtime_readiness import (
    REQUIRED_CONSTRAINTS,
    REQUIRED_LOOKUP_INDEXES,
    REQUIRED_LOOKUP_INDEX_SPECS,
    build_readiness_report,
    experience_vector_index_name,
    run_explicit_initialization,
)


RESTORED_LOOKUP_INDEX_NAMES = {
    "concept_category": "index_d54c82b6",
    "concept_strength": "index_a5453a2",
    "experience_created": "index_966d95a6",
    "experience_stage": "index_c2439b97",
    "pending_q_status": "index_4b11d800",
    "emotion_log_created": "index_6642c76c",
    "exp_hour": "index_1f7b4bb0",
    "exp_speaker": "index_3deb3da8",
    "tp_time_slot": "index_f6e5335e",
}


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    async def single(self):
        return self.rows[0] if self.rows else None

    async def data(self):
        return self.rows


class FakeSession:
    def __init__(self, driver):
        self.driver = driver

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def run(self, query):
        if query.startswith("RETURN 1"):
            if self.driver.neo4j_error:
                raise RuntimeError(self.driver.neo4j_error)
            return FakeResult([{"ready": 1}])
        if query.startswith("SHOW INDEXES"):
            if self.driver.schema_error:
                raise RuntimeError(self.driver.schema_error)
            return FakeResult(self.driver.indexes)
        if query.startswith("SHOW CONSTRAINTS"):
            return FakeResult([{"name": name} for name in self.driver.constraints])
        raise AssertionError(f"Unexpected query: {query}")


class FakeDriver:
    def __init__(self, *, vector_name="experience_embeddings", lookup_names=None):
        self.neo4j_error = None
        self.schema_error = None
        self.constraints = set(REQUIRED_CONSTRAINTS)
        self.indexes = [
            {
                "name": (lookup_names or {}).get(name, name),
                "type": "RANGE",
                "entityType": "NODE",
                "state": "ONLINE",
                "labelsOrTypes": [REQUIRED_LOOKUP_INDEX_SPECS[name][0]],
                "properties": [REQUIRED_LOOKUP_INDEX_SPECS[name][1]],
            }
            for name in REQUIRED_LOOKUP_INDEXES
        ]
        self.indexes.append({
            "name": vector_name,
            "type": "VECTOR",
            "entityType": "NODE",
            "state": "ONLINE",
            "labelsOrTypes": ["Experience"],
            "properties": ["embedding"],
        })

    def session(self, *, database):
        assert database == "neo4j"
        return FakeSession(self)


class FakeRedis:
    def __init__(self):
        self.available = True

    async def ping(self):
        if not self.available:
            raise ConnectionError("redis://secret-user:secret-password@private-host")
        return True


def build_report(driver, redis, environ=None):
    return asyncio.run(build_readiness_report(
        neo4j_getter=lambda: driver,
        redis_getter=lambda: redis,
        database="neo4j",
        environ=environ or {},
    ))


def test_redis_transport_options_separate_plain_and_tls() -> None:
    plain = redis_connection_options("redis://127.0.0.1:6379/0")
    assert plain == {"decode_responses": True}
    assert not any(key.startswith("ssl") for key in plain)

    tls = redis_connection_options("rediss://example.test:6379/0")
    assert tls["ssl_cert_reqs"] == "required"
    assert tls["ssl_check_hostname"] is True


def test_redis_transport_options_reject_unknown_scheme() -> None:
    try:
        redis_connection_options("http://example.test")
    except ValueError as exc:
        assert str(exc) == "REDIS_URL must use redis:// or rediss://"
    else:
        raise AssertionError("unknown Redis scheme was accepted")


@pytest.mark.parametrize(
    "url",
    [
        "redis://localhost:6379?ssl_cert_reqs=none",
        "redis://localhost:6379?ssl_check_hostname=false",
        "rediss://example.test:6379?ssl_cert_reqs=none",
        "rediss://example.test:6379?ssl_cert_reqs=optional",
        "rediss://example.test:6379?ssl_check_hostname=false",
        (
            "rediss://example.test:6379"
            "?ssl_cert_reqs=required&ssl_cert_reqs=none"
        ),
    ],
)
def test_redis_transport_options_reject_query_policy_weakening(url) -> None:
    with pytest.raises(ValueError):
        redis_connection_options(url)


def test_redis_transport_options_allow_explicit_secure_tls_query() -> None:
    options = redis_connection_options(
        "rediss://example.test:6379"
        "?ssl_cert_reqs=required&ssl_check_hostname=true"
    )
    assert options["ssl_cert_reqs"] == "required"
    assert options["ssl_check_hostname"] is True


def test_actual_connection_pool_settings_do_not_connect() -> None:
    plain = redis_client.init_redis("redis://127.0.0.1:6379/0")
    plain_settings = plain.connection_pool.connection_kwargs
    assert plain_settings["decode_responses"] is True
    assert not any(key.startswith("ssl") for key in plain_settings)
    assert plain.connection_pool.connection_class.__name__ == "Connection"
    asyncio.run(redis_client.close_redis())

    tls = redis_client.init_redis(
        "rediss://example.test:6379/0"
        "?ssl_cert_reqs=required&ssl_check_hostname=true"
    )
    tls_settings = tls.connection_pool.connection_kwargs
    assert tls_settings["ssl_cert_reqs"] == "required"
    assert tls_settings["ssl_check_hostname"] is True
    assert tls.connection_pool.connection_class.__name__ == "SSLConnection"
    asyncio.run(redis_client.close_redis())


def test_readiness_uses_configured_vector_registry_name() -> None:
    driver = FakeDriver(vector_name="index_2bacf740")
    report = build_report(
        driver,
        FakeRedis(),
        {"BABY_EXPERIENCE_VECTOR_INDEX": "index_2bacf740"},
    )

    assert experience_vector_index_name({}) == "experience_embeddings"
    assert report["ready"] is True
    assert report["status"] == "healthy"
    assert report["checks"]["vector_search"] == {
        "required": True,
        "name": "index_2bacf740",
        "healthy": True,
        "status": "ready",
        "expected_labels_or_types": ["Experience"],
        "expected_properties": ["embedding"],
        "state": "ONLINE",
        "type": "VECTOR",
        "labels_or_types": ["Experience"],
        "properties": ["embedding"],
    }
    assert report["providers"]["conversation"]["probed"] is False
    assert report["providers"]["conversation"]["status"] == "not_configured"
    assert report["providers"]["embedding"]["probed"] is False


def test_lookup_readiness_accepts_real_shaped_auto_generated_names() -> None:
    auto_names = RESTORED_LOOKUP_INDEX_NAMES
    report = build_report(
        FakeDriver(lookup_names=auto_names),
        FakeRedis(),
    )

    assert report["ready"] is True
    assert report["checks"]["schema"]["resolved_indexes"] == auto_names
    assert report["checks"]["schema"]["missing_indexes"] == []
    assert report["checks"]["schema"]["wrong_shape_indexes"] == []
    assert report["checks"]["schema"]["offline_indexes"] == []


def test_lookup_readiness_fails_named_wrong_shape_and_semantic_offline() -> None:
    wrong_shape = FakeDriver()
    wrong_shape_row = next(
        item for item in wrong_shape.indexes if item["name"] == "concept_category"
    )
    wrong_shape_row["properties"] = ["wrong_property"]
    wrong_report = build_report(wrong_shape, FakeRedis())
    assert wrong_report["ready"] is False
    assert wrong_report["checks"]["schema"]["wrong_shape_indexes"] == [{
        "requirement": "concept_category",
        "name": "concept_category",
        "entity_type": "NODE",
        "type": "RANGE",
        "labels_or_types": ["Concept"],
        "properties": ["wrong_property"],
    }]

    auto_names = RESTORED_LOOKUP_INDEX_NAMES
    offline = FakeDriver(lookup_names=auto_names)
    offline_name = auto_names["experience_created"]
    next(item for item in offline.indexes if item["name"] == offline_name)[
        "state"
    ] = "POPULATING"
    offline_report = build_report(offline, FakeRedis())
    assert offline_report["ready"] is False
    assert offline_report["checks"]["schema"]["offline_indexes"] == [{
        "requirement": "experience_created",
        "names": [offline_name],
    }]


def test_disconnect_then_recovery_changes_readiness_without_leaking_errors() -> None:
    driver = FakeDriver()
    redis = FakeRedis()
    driver.neo4j_error = "bolt://secret-user:secret-password@private-host"
    redis.available = False

    failed = build_report(driver, redis)
    assert failed["ready"] is False
    assert failed["status"] == "unhealthy"
    assert failed["checks"]["neo4j"]["error_code"] == "check_failed"
    assert failed["checks"]["redis"]["error_code"] == "check_failed"
    assert "secret" not in repr(failed)

    driver.neo4j_error = None
    redis.available = True
    recovered = build_report(driver, redis)
    assert recovered["ready"] is True
    assert recovered["checks"]["neo4j"]["status"] == "ready"
    assert recovered["checks"]["redis"]["status"] == "ready"


def test_readiness_reconnects_neo4j_after_failed_startup_in_same_process() -> None:
    holder = {"driver": None}
    reconnect_calls = []
    redis = FakeRedis()

    def get_driver():
        if holder["driver"] is None:
            raise RuntimeError("driver not initialized")
        return holder["driver"]

    async def reconnect():
        reconnect_calls.append("attempted")
        driver = FakeDriver()
        driver.neo4j_error = "database still unavailable"
        holder["driver"] = driver
        raise ConnectionError("bolt://secret-user:secret-password@private-host")

    first = asyncio.run(build_readiness_report(
        neo4j_getter=get_driver,
        neo4j_reconnect=reconnect,
        redis_getter=lambda: redis,
        database="neo4j",
        environ={},
    ))
    assert first["ready"] is False
    assert first["checks"]["neo4j"]["reconnect_attempted"] is True
    assert "secret" not in repr(first)

    holder["driver"].neo4j_error = None
    recovered = asyncio.run(build_readiness_report(
        neo4j_getter=get_driver,
        neo4j_reconnect=reconnect,
        redis_getter=lambda: redis,
        database="neo4j",
        environ={},
    ))
    assert recovered["ready"] is True
    assert recovered["checks"]["neo4j"]["reconnect_attempted"] is False
    assert reconnect_calls == ["attempted"]


def test_query_failure_and_vector_schema_mismatch_are_distinct() -> None:
    driver = FakeDriver()
    driver.schema_error = "SHOW INDEXES denied with password=secret"
    query_failure = build_report(driver, FakeRedis())
    assert query_failure["checks"]["neo4j"]["healthy"] is True
    assert query_failure["checks"]["schema"]["status"] == "failed"
    assert query_failure["checks"]["vector_search"]["status"] == "failed"
    assert "secret" not in repr(query_failure)

    driver.schema_error = None
    driver.indexes[-1]["properties"] = ["wrong_property"]
    mismatch = build_report(driver, FakeRedis())
    assert mismatch["checks"]["schema"]["healthy"] is True
    assert mismatch["checks"]["vector_search"]["status"] == "schema_mismatch"
    assert mismatch["ready"] is False


def test_failed_explicit_initialization_keeps_readiness_nonhealthy() -> None:
    report = asyncio.run(build_readiness_report(
        neo4j_getter=lambda: FakeDriver(),
        redis_getter=FakeRedis,
        database="neo4j",
        startup={"status": "failed", "mutated": False},
        environ={},
    ))
    assert report["checks"]["neo4j"]["healthy"] is True
    assert report["checks"]["redis"]["healthy"] is True
    assert report["ready"] is False
    assert report["status"] == "unhealthy"


def test_redis_timeout_is_nonhealthy_and_sanitized() -> None:
    class SlowRedis:
        async def ping(self):
            await asyncio.sleep(0.05)
            return True

    report = build_report(
        FakeDriver(),
        SlowRedis(),
        {"BABY_READINESS_TIMEOUT_SECONDS": "0.001"},
    )
    assert report["ready"] is False
    assert report["checks"]["redis"]["status"] == "timed_out"
    assert report["checks"]["redis"]["error_code"] == "timeout"


@pytest.mark.parametrize("value", ["nan", "inf", "+inf", "-inf", "0", "-1", "bad"])
def test_readiness_timeout_rejects_nonfinite_and_nonpositive_values(value) -> None:
    report = build_report(
        FakeDriver(),
        FakeRedis(),
        {"BABY_READINESS_TIMEOUT_SECONDS": value},
    )
    assert report["timeout_seconds"] == 2.0


def test_readiness_timeout_caps_large_finite_values() -> None:
    report = build_report(
        FakeDriver(),
        FakeRedis(),
        {"BABY_READINESS_TIMEOUT_SECONDS": "999"},
    )
    assert report["timeout_seconds"] == 30.0


def test_explicit_initialization_defaults_to_no_mutation_and_signals_failure() -> None:
    class FakeDb:
        def __init__(self):
            self.calls = []
            self.fail_seed = False

        async def ensure_indexes(self):
            self.calls.append("schema")

        async def seed_brain_regions(self):
            self.calls.append("brain_regions")

        async def seed_region_connections(self):
            self.calls.append("region_connections")
            if self.fail_seed:
                raise RuntimeError("password=secret")

        async def seed_identity_concepts(self):
            self.calls.append("identity_concepts")

    db = FakeDb()
    no_op = asyncio.run(run_explicit_initialization(db))
    assert no_op == {
        "status": "not_requested",
        "mutation_attempted": False,
        "mutated": False,
    }
    assert db.calls == []

    db.fail_seed = True
    failed = asyncio.run(run_explicit_initialization(db, include_seed=True))
    assert failed["status"] == "failed"
    assert failed["completed"] == ["brain_regions"]
    assert failed["mutation_attempted"] is True
    assert failed["mutation_result"] == "not_measured"
    assert "secret" not in repr(failed)
