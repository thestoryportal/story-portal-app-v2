# Performance Audit
## Async Pattern Usage
Async patterns found: 9542

## Connection Pool Configuration
./platform/src/L02_runtime/backends/local_runtime.py:49:            # Run in thread pool since docker-py is synchronous
./platform/src/L02_runtime/models/fleet_models.py:42:    warm_pool_size: int = 0
./platform/src/L02_runtime/models/fleet_models.py:50:            "warm_pool_size": self.warm_pool_size,
./platform/src/L02_runtime/models/fleet_models.py:81:    Pre-warmed agent instance in the warm pool.
./platform/src/L02_runtime/services/fleet_manager.py:4:Manages horizontal scaling, warm pools, and graceful drain operations.
./platform/src/L02_runtime/services/fleet_manager.py:5:Implements local process pool for development, with stubs for K8s HPA.
./platform/src/L02_runtime/services/fleet_manager.py:42:    Manages agent fleet scaling and warm pool operations.
./platform/src/L02_runtime/services/fleet_manager.py:47:    - Manage warm instance pool
./platform/src/L02_runtime/services/fleet_manager.py:63:                - warm_pool: Warm pool configuration
./platform/src/L02_runtime/services/fleet_manager.py:79:        # Warm pool configuration
./platform/src/L02_runtime/services/fleet_manager.py:80:        warm_pool_config = self.config.get("warm_pool", {})
./platform/src/L02_runtime/services/fleet_manager.py:81:        self.warm_pool_enabled = warm_pool_config.get("enabled", True)
./platform/src/L02_runtime/services/fleet_manager.py:82:        self.warm_pool_size = warm_pool_config.get("size", 5)
./platform/src/L02_runtime/services/fleet_manager.py:83:        self.warm_pool_refresh_interval = warm_pool_config.get(
./platform/src/L02_runtime/services/state_manager.py:102:        self._pg_pool: Optional[Any] = None
./platform/src/L02_runtime/services/state_manager.py:116:        # Initialize PostgreSQL connection pool
./platform/src/L02_runtime/services/state_manager.py:119:                self._pg_pool = await asyncpg.create_pool(
./platform/src/L02_runtime/services/state_manager.py:124:                logger.info("PostgreSQL connection pool initialized")
./platform/src/L02_runtime/services/state_manager.py:131:                self._pg_pool = None
./platform/src/L02_runtime/services/state_manager.py:153:        if not self._pg_pool:

## Caching Patterns
./platform/output/L01_data/enhanced_context_service.py:46:        First checks Redis cache, falls back to PostgreSQL if not cached.
./platform/output/L01_data/enhanced_context_service.py:55:        cache_key = f"context:{context_id}:{version or 'latest'}"
./platform/output/L01_data/enhanced_context_service.py:57:        # Try cache first
./platform/output/L01_data/enhanced_context_service.py:58:        cached = await self.redis.get(cache_key)
./platform/output/L01_data/enhanced_context_service.py:59:        if cached:
./platform/output/L01_data/enhanced_context_service.py:60:            return json.loads(cached)
./platform/output/L01_data/enhanced_context_service.py:90:                cache_key,
./platform/output/L01_data/enhanced_context_service.py:148:        # Update cache
./platform/output/L01_data/enhanced_context_service.py:149:        cache_key = f"context:{context_id}:latest"
./platform/output/L01_data/enhanced_context_service.py:150:        await self.redis.setex(cache_key, 3600, json.dumps(context_data))
./platform/output/L01_data/enhanced_context_service.py:152:        # Invalidate version-specific cache
./platform/src/L02_runtime/services/document_bridge.py:50:                - cache_ttl_seconds: Cache TTL
./platform/src/L02_runtime/services/document_bridge.py:64:        self.cache_ttl = self.config.get("cache_ttl_seconds", 300)
./platform/src/L02_runtime/services/document_bridge.py:84:        # Query cache: query_key -> (result, expiry_time)
./platform/src/L02_runtime/services/document_bridge.py:85:        self._cache: Dict[str, tuple] = {}
./platform/src/L02_runtime/services/document_bridge.py:112:        use_cache: bool = True
./platform/src/L02_runtime/services/document_bridge.py:120:            use_cache: Whether to use cached results
./platform/src/L02_runtime/services/document_bridge.py:130:        # Check cache
./platform/src/L02_runtime/services/document_bridge.py:131:        cache_key = self._get_cache_key(query, filters)
./platform/src/L02_runtime/services/document_bridge.py:132:        if use_cache:

## Potential N+1 Query Patterns
./platform/src/L07_learning/services/example_quality_filter.py:323:                sampled.extend([items[i] for i in selected])
./platform/src/L07_learning/services/example_quality_filter.py:335:                sampled.extend([remaining_pool[i] for i in selected])
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:1647:                self.process(elem, **kw) for elem in select._for_update_arg.of
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/postgresql/base.py:2122:                            for col in select._distinct_on
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/postgresql/base.py:2145:            for c in select._for_update_arg.of:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/engine/url.py:140:          Methods for altering the contents of :attr:`_engine.URL.query`:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/bulk_persistence.py:539:                (c, _ent_for_col(c)) for c in statement._all_selected_columns
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/context.py:1213:            for opt in self.select_statement._with_options:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/context.py:1222:            for fn, key in select_statement._with_context_options:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/context.py:1240:            info.selectable for info in select_statement._from_obj
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/context.py:1273:        for memoized_entities in query._memoized_select_entities:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/context.py:2223:            for from_obj in self.from_clauses or [l_info.selectable]:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/context.py:2261:        # test for joining to an unmapped selectable as the target
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/mapper.py:1607:        for fc in set(self.tables).union([self.persist_selectable]):
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/mapper.py:1801:        for column in self.persist_selectable.columns:
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/query.py:2964:                "for linking ORM results to arbitrary select constructs.",
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/orm/util.py:1738:            for row in session.execute(select(bn)).where(bn.c.data1 == "d1"):
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/sql/compiler.py:1541:                for c in self.statement._all_selected_columns
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/sql/compiler.py:3052:                for i, c in enumerate(cs.selects)
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/sql/compiler.py:4941:                for (dialect_name, ht) in select_stmt._statement_hints
