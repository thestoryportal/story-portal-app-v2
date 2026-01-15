==========================================
L01-L06 End-to-End Test Suite
==========================================
Started: Thu Jan 15 01:52:04 MST 2026

Checking infrastructure...
  ✓ PostgreSQL
  ✓ Redis
  ✓ Ollama

Running tests...

--- Layer Initialization Tests ---
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.2, pluggy-1.6.0 -- /usr/local/opt/python@3.14/bin/python3.14
cachedir: .pytest_cache
rootdir: /Volumes/Extreme SSD/projects/story-portal-app/platform/tests/e2e
configfile: pytest.ini
plugins: anyio-4.12.1, timeout-2.4.0, asyncio-1.3.0
timeout: 30.0s
timeout method: thread
timeout func_only: False
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 11 items

tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l02_runtime_imports PASSED [  9%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l02_runtime_initializes PASSED [ 18%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l03_tools_imports PASSED [ 27%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l03_tools_initializes PASSED [ 36%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l04_gateway_imports PASSED [ 45%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l04_gateway_initializes PASSED [ 54%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l05_planning_imports PASSED [ 63%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l05_planning_initializes PASSED [ 72%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l06_evaluation_imports PASSED [ 81%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_l06_evaluation_initializes PASSED [ 90%]
tests/e2e/test_layer_initialization.py::TestLayerInitialization::test_all_layers_initialize_together PASSED [100%]

============================== 11 passed in 0.84s ==============================

--- L02 Runtime Tests ---
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.2, pluggy-1.6.0 -- /usr/local/opt/python@3.14/bin/python3.14
cachedir: .pytest_cache
rootdir: /Volumes/Extreme SSD/projects/story-portal-app/platform/tests/e2e
configfile: pytest.ini
plugins: anyio-4.12.1, timeout-2.4.0, asyncio-1.3.0
timeout: 60.0s
timeout method: thread
timeout func_only: False
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 7 items

tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_executor_initialization PASSED [ 14%]
tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_session_bridge_connection PASSED [ 28%]
tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_document_bridge_connection PASSED [ 42%]
tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_session_save_snapshot FAILED [ 57%]
tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_session_get_context FAILED [ 71%]
tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_document_query PASSED [ 85%]
tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_document_find_source FAILED [100%]

=================================== FAILURES ===================================
________________ TestL02AgentRuntime.test_session_save_snapshot ________________
tests/e2e/test_l02_runtime.py:55: in test_session_save_snapshot
    result = await session_bridge.save_snapshot(
E   TypeError: SessionBridge.save_snapshot() got an unexpected keyword argument 'task_id'
---------------------------- Captured log teardown -----------------------------
WARNING  src.L02_runtime.services.session_bridge:session_bridge.py:469 Timeout disconnecting MCP client
_________________ TestL02AgentRuntime.test_session_get_context _________________
tests/e2e/test_l02_runtime.py:65: in test_session_get_context
    result = await session_bridge.get_unified_context(task_id="test-task-001")
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: SessionBridge.get_unified_context() got an unexpected keyword argument 'task_id'
---------------------------- Captured log teardown -----------------------------
WARNING  src.L02_runtime.services.session_bridge:session_bridge.py:469 Timeout disconnecting MCP client
________________ TestL02AgentRuntime.test_document_find_source _________________
tests/e2e/test_l02_runtime.py:79: in test_document_find_source
    result = await document_bridge.find_source_of_truth(query="specification")
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: DocumentBridge.find_source_of_truth() got an unexpected keyword argument 'query'
------------------------------ Captured log setup ------------------------------
WARNING  src.L02_runtime.services.mcp_client:mcp_client.py:164 Server initialization timeout, proceeding anyway
ERROR    src.L02_runtime.services.mcp_client:mcp_client.py:511 [document-consolidator] Embedding service error: 2026-01-15 01:53:38,371 - __main__ - INFO - Loading model: all-MiniLM-L6-v2
ERROR    src.L02_runtime.services.mcp_client:mcp_client.py:511 [document-consolidator] Embedding service error: 2026-01-15 01:53:38,405 - __main__ - INFO - Using device: cpu
ERROR    src.L02_runtime.services.mcp_client:mcp_client.py:511 [document-consolidator] Embedding service error: 2026-01-15 01:53:38,407 - sentence_transformers.SentenceTransformer - INFO - Load pretrained SentenceTransformer: all-MiniLM-L6-v2
ERROR    src.L02_runtime.services.mcp_client:mcp_client.py:511 [document-consolidator] Embedding service error: Batches:   0%|          | 0/1 [00:00<?, ?it/s]
ERROR    src.L02_runtime.services.mcp_client:mcp_client.py:511 [document-consolidator] Embedding service error: Batches: 100%|██████████| 1/1 [00:00<00:00, 41.74it/s]
ERROR    src.L02_runtime.services.mcp_client:mcp_client.py:511 [document-consolidator] Embedding service error: 2026-01-15 01:53:40,259 - __main__ - INFO - Model loaded successfully. Embedding dimension: 384
ERROR    src.L02_runtime.services.mcp_client:mcp_client.py:511 [document-consolidator] Embedding service error: 2026-01-15 01:53:40,259 - __main__ - INFO - Starting JSON-RPC server
---------------------------- Captured log teardown -----------------------------
WARNING  src.L02_runtime.services.mcp_client:mcp_client.py:344 Force killing document-consolidator
=========================== short test summary info ============================
FAILED tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_session_save_snapshot - TypeError: SessionBridge.save_snapshot() got an unexpected keyword argument 'task_id'
FAILED tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_session_get_context - TypeError: SessionBridge.get_unified_context() got an unexpected keyword argument 'task_id'
FAILED tests/e2e/test_l02_runtime.py::TestL02AgentRuntime::test_document_find_source - TypeError: DocumentBridge.find_source_of_truth() got an unexpected keyword argument 'query'
==================== 3 failed, 4 passed in 98.40s (0:01:38) ====================

--- L03 Tool Tests ---
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.2, pluggy-1.6.0 -- /usr/local/opt/python@3.14/bin/python3.14
cachedir: .pytest_cache
rootdir: /Volumes/Extreme SSD/projects/story-portal-app/platform/tests/e2e
configfile: pytest.ini
plugins: anyio-4.12.1, timeout-2.4.0, asyncio-1.3.0
timeout: 60.0s
timeout method: thread
timeout func_only: False
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 5 items

tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_registry_initialization PASSED [ 20%]
tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_executor_initialization PASSED [ 40%]
tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_list_available_tools FAILED [ 60%]
tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_get_tool_by_name FAILED [ 80%]
tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_execute_mock_tool SKIPPEDord argument 'tool_name') [100%]

=================================== FAILURES ===================================
________________ TestL03ToolExecution.test_list_available_tools ________________
tests/e2e/test_l03_tools.py:40: in test_list_available_tools
    tools = await tool_registry.list_tools()
                  ^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'ToolRegistry' object has no attribute 'list_tools'
__________________ TestL03ToolExecution.test_get_tool_by_name __________________
tests/e2e/test_l03_tools.py:47: in test_get_tool_by_name
    tools = await tool_registry.list_tools()
                  ^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'ToolRegistry' object has no attribute 'list_tools'
=========================== short test summary info ============================
FAILED tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_list_available_tools - AttributeError: 'ToolRegistry' object has no attribute 'list_tools'
FAILED tests/e2e/test_l03_tools.py::TestL03ToolExecution::test_get_tool_by_name - AttributeError: 'ToolRegistry' object has no attribute 'list_tools'
==================== 2 failed, 2 passed, 1 skipped in 1.11s ====================

--- L04 Gateway Tests ---
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.2, pluggy-1.6.0 -- /usr/local/opt/python@3.14/bin/python3.14
cachedir: .pytest_cache
rootdir: /Volumes/Extreme SSD/projects/story-portal-app/platform/tests/e2e
configfile: pytest.ini
plugins: anyio-4.12.1, timeout-2.4.0, asyncio-1.3.0
timeout: 60.0s
timeout method: thread
timeout func_only: False
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 8 items

tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_gateway_initialization PASSED [ 12%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_registry_initialization PASSED [ 25%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_router_initialization PASSED [ 37%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_list_available_models FAILED [ 50%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_ollama_provider_health PASSED [ 62%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_simple_completion FAILED [ 75%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_semantic_cache PASSED [ 87%]
tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_rate_limiter FAILED [100%]

=================================== FAILURES ===================================
________________ TestL04ModelGateway.test_list_available_models ________________
tests/e2e/test_l04_gateway.py:49: in test_list_available_models
    models = await model_registry.list_models()
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   TypeError: 'list' object can't be awaited
__________________ TestL04ModelGateway.test_simple_completion __________________
tests/e2e/test_l04_gateway.py:71: in test_simple_completion
    logical_prompt=LogicalPrompt(
E   TypeError: LogicalPrompt.__init__() got an unexpected keyword argument 'system'
____________________ TestL04ModelGateway.test_rate_limiter _____________________
tests/e2e/test_l04_gateway.py:99: in test_rate_limiter
    allowed = await limiter.check_limit(agent_id="test-agent", tokens=100)
                    ^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'RateLimiter' object has no attribute 'check_limit'. Did you mean: 'check_rate_limit'?
=========================== short test summary info ============================
FAILED tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_list_available_models - TypeError: 'list' object can't be awaited
FAILED tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_simple_completion - TypeError: LogicalPrompt.__init__() got an unexpected keyword argument 'system'
FAILED tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_rate_limiter - AttributeError: 'RateLimiter' object has no attribute 'check_limit'. Did you mean: 'check_rate_limit'?
========================= 3 failed, 5 passed in 0.35s ==========================

--- L05 Planning Tests ---
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.2, pluggy-1.6.0 -- /usr/local/opt/python@3.14/bin/python3.14
cachedir: .pytest_cache
rootdir: /Volumes/Extreme SSD/projects/story-portal-app/platform/tests/e2e
configfile: pytest.ini
plugins: anyio-4.12.1, timeout-2.4.0, asyncio-1.3.0
timeout: 60.0s
timeout method: thread
timeout func_only: False
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 8 items

tests/e2e/test_l05_planning.py::TestL05Planning::test_planning_service_initialization PASSED [ 12%]
tests/e2e/test_l05_planning.py::TestL05Planning::test_goal_decomposer_initialization ERROR [ 25%]
tests/e2e/test_l05_planning.py::TestL05Planning::test_create_simple_plan +++++++++++++++++++++++++++++++++++ Timeout ++++++++++++++++++++++++++++++++++++
~~~~~~~~~~~~~~~~~~~~~ Stack of asyncio_0 (123145403715584) ~~~~~~~~~~~~~~~~~~~~~
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/threading.py", line 1044, in _bootstrap
    self._bootstrap_inner()
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/threading.py", line 1082, in _bootstrap_inner
    self._context.run(self.run)
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/threading.py", line 1024, in run
    self._target(*self._args, **self._kwargs)
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/concurrent/futures/thread.py", line 116, in _worker
    work_item = work_queue.get(block=True)
~~~~~~~~~~~~~~~~~~~~ Stack of MainThread (140704632716928) ~~~~~~~~~~~~~~~~~~~~~
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/usr/local/lib/python3.14/site-packages/pytest/__main__.py", line 9, in <module>
    raise SystemExit(pytest.console_main())
  File "/usr/local/lib/python3.14/site-packages/_pytest/config/__init__.py", line 223, in console_main
    code = main()
  File "/usr/local/lib/python3.14/site-packages/_pytest/config/__init__.py", line 199, in main
    ret: ExitCode | int = config.hook.pytest_cmdline_main(config=config)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
  File "/usr/local/lib/python3.14/site-packages/_pytest/main.py", line 365, in pytest_cmdline_main
    return wrap_session(config, _main)
  File "/usr/local/lib/python3.14/site-packages/_pytest/main.py", line 318, in wrap_session
    session.exitstatus = doit(config, session) or 0
  File "/usr/local/lib/python3.14/site-packages/_pytest/main.py", line 372, in _main
    config.hook.pytest_runtestloop(session=session)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
  File "/usr/local/lib/python3.14/site-packages/_pytest/main.py", line 396, in pytest_runtestloop
    item.config.hook.pytest_runtest_protocol(item=item, nextitem=nextitem)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
  File "/usr/local/lib/python3.14/site-packages/_pytest/runner.py", line 118, in pytest_runtest_protocol
    runtestprotocol(item, nextitem=nextitem)
  File "/usr/local/lib/python3.14/site-packages/_pytest/runner.py", line 137, in runtestprotocol
    reports.append(call_and_report(item, "call", log))
  File "/usr/local/lib/python3.14/site-packages/_pytest/runner.py", line 244, in call_and_report
    call = CallInfo.from_call(
  File "/usr/local/lib/python3.14/site-packages/_pytest/runner.py", line 353, in from_call
    result: TResult | None = func()
  File "/usr/local/lib/python3.14/site-packages/_pytest/runner.py", line 245, in <lambda>
    lambda: runtest_hook(item=item, **kwds),
  File "/usr/local/lib/python3.14/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
  File "/usr/local/lib/python3.14/site-packages/_pytest/runner.py", line 179, in pytest_runtest_call
    item.runtest()
  File "/usr/local/lib/python3.14/site-packages/pytest_asyncio/plugin.py", line 469, in runtest
    super().runtest()
  File "/usr/local/lib/python3.14/site-packages/_pytest/python.py", line 1720, in runtest
    self.ihook.pytest_pyfunc_call(pyfuncitem=self)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
  File "/usr/local/lib/python3.14/site-packages/_pytest/python.py", line 166, in pytest_pyfunc_call
    result = testfunction(**testargs)
  File "/usr/local/lib/python3.14/site-packages/pytest_asyncio/plugin.py", line 716, in inner
    runner.run(coro, context=context)
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/runners.py", line 127, in run
    return self._loop.run_until_complete(task)
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 706, in run_until_complete
    self.run_forever()
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 677, in run_forever
    self._run_once()
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 2008, in _run_once
    event_list = self._selector.select(timeout)
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/selectors.py", line 548, in select
    kev_list = self._selector.control(None, max_ev, timeout)
+++++++++++++++++++++++++++++++++++ Timeout ++++++++++++++++++++++++++++++++++++

--- L06 Evaluation Tests ---
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.2, pluggy-1.6.0 -- /usr/local/opt/python@3.14/bin/python3.14
cachedir: .pytest_cache
rootdir: /Volumes/Extreme SSD/projects/story-portal-app/platform/tests/e2e
configfile: pytest.ini
plugins: anyio-4.12.1, timeout-2.4.0, asyncio-1.3.0
timeout: 60.0s
timeout method: thread
timeout func_only: False
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 10 items

tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_evaluation_service_initialization PASSED [ 10%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_quality_scorer_initialization ERROR [ 20%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_engine_initialization ERROR [ 30%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_process_cloud_event PASSED [ 40%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_quality_score_computation ERROR [ 50%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_quality_dimensions ERROR [ 60%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_dimension_weights_sum_to_one ERROR [ 70%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_ingestion ERROR [ 80%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_query ERROR [ 90%]
tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_anomaly_detection FAILED [100%]

==================================== ERRORS ====================================
____ ERROR at setup of TestL06Evaluation.test_quality_scorer_initialization ____
tests/e2e/test_l06_evaluation.py:22: in quality_scorer
    scorer = QualityScorer()
             ^^^^^^^^^^^^^^^
E   TypeError: QualityScorer.__init__() missing 1 required positional argument: 'metrics_engine'
____ ERROR at setup of TestL06Evaluation.test_metrics_engine_initialization ____
tests/e2e/test_l06_evaluation.py:31: in metrics_engine
    engine = MetricsEngine()
             ^^^^^^^^^^^^^^^
E   TypeError: MetricsEngine.__init__() missing 1 required positional argument: 'storage_manager'
______ ERROR at setup of TestL06Evaluation.test_quality_score_computation ______
tests/e2e/test_l06_evaluation.py:22: in quality_scorer
    scorer = QualityScorer()
             ^^^^^^^^^^^^^^^
E   TypeError: QualityScorer.__init__() missing 1 required positional argument: 'metrics_engine'
_________ ERROR at setup of TestL06Evaluation.test_quality_dimensions __________
tests/e2e/test_l06_evaluation.py:22: in quality_scorer
    scorer = QualityScorer()
             ^^^^^^^^^^^^^^^
E   TypeError: QualityScorer.__init__() missing 1 required positional argument: 'metrics_engine'
____ ERROR at setup of TestL06Evaluation.test_dimension_weights_sum_to_one _____
tests/e2e/test_l06_evaluation.py:22: in quality_scorer
    scorer = QualityScorer()
             ^^^^^^^^^^^^^^^
E   TypeError: QualityScorer.__init__() missing 1 required positional argument: 'metrics_engine'
__________ ERROR at setup of TestL06Evaluation.test_metrics_ingestion __________
tests/e2e/test_l06_evaluation.py:31: in metrics_engine
    engine = MetricsEngine()
             ^^^^^^^^^^^^^^^
E   TypeError: MetricsEngine.__init__() missing 1 required positional argument: 'storage_manager'
____________ ERROR at setup of TestL06Evaluation.test_metrics_query ____________
tests/e2e/test_l06_evaluation.py:31: in metrics_engine
    engine = MetricsEngine()
             ^^^^^^^^^^^^^^^
E   TypeError: MetricsEngine.__init__() missing 1 required positional argument: 'storage_manager'
=================================== FAILURES ===================================
___________________ TestL06Evaluation.test_anomaly_detection ___________________
tests/e2e/test_l06_evaluation.py:141: in test_anomaly_detection
    await detector.initialize()
          ^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'AnomalyDetector' object has no attribute 'initialize'
=========================== short test summary info ============================
FAILED tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_anomaly_detection - AttributeError: 'AnomalyDetector' object has no attribute 'initialize'
ERROR tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_quality_scorer_initialization - TypeError: QualityScorer.__init__() missing 1 required positional argument: 'metrics_engine'
ERROR tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_engine_initialization - TypeError: MetricsEngine.__init__() missing 1 required positional argument: 'storage_manager'
ERROR tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_quality_score_computation - TypeError: QualityScorer.__init__() missing 1 required positional argument: 'metrics_engine'
ERROR tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_quality_dimensions - TypeError: QualityScorer.__init__() missing 1 required positional argument: 'metrics_engine'
ERROR tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_dimension_weights_sum_to_one - TypeError: QualityScorer.__init__() missing 1 required positional argument: 'metrics_engine'
ERROR tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_ingestion - TypeError: MetricsEngine.__init__() missing 1 required positional argument: 'storage_manager'
ERROR tests/e2e/test_l06_evaluation.py::TestL06Evaluation::test_metrics_query - TypeError: MetricsEngine.__init__() missing 1 required positional argument: 'storage_manager'
==================== 1 failed, 2 passed, 7 errors in 0.35s =====================

--- Cross-Layer Integration Tests ---
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.2, pluggy-1.6.0 -- /usr/local/opt/python@3.14/bin/python3.14
cachedir: .pytest_cache
rootdir: /Volumes/Extreme SSD/projects/story-portal-app/platform/tests/e2e
configfile: pytest.ini
plugins: anyio-4.12.1, timeout-2.4.0, asyncio-1.3.0
timeout: 120.0s
timeout method: thread
timeout func_only: False
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 4 items

tests/e2e/test_cross_layer_integration.py::TestCrossLayerIntegration::test_l04_l05_integration +++++++++++++++++++++++++++++++++++ Timeout ++++++++++++++++++++++++++++++++++++
~~~~~~~~~~~~~~~~~~~~~ Stack of asyncio_0 (123145401438208) ~~~~~~~~~~~~~~~~~~~~~
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/threading.py", line 1044, in _bootstrap
    self._bootstrap_inner()
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/threading.py", line 1082, in _bootstrap_inner
    self._context.run(self.run)
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/threading.py", line 1024, in run
    self._target(*self._args, **self._kwargs)
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/concurrent/futures/thread.py", line 116, in _worker
    work_item = work_queue.get(block=True)
~~~~~~~~~~~~~~~~~~~~ Stack of MainThread (140704632716928) ~~~~~~~~~~~~~~~~~~~~~
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/usr/local/lib/python3.14/site-packages/pytest/__main__.py", line 9, in <module>
    raise SystemExit(pytest.console_main())
  File "/usr/local/lib/python3.14/site-packages/_pytest/config/__init__.py", line 223, in console_main
    code = main()
  File "/usr/local/lib/python3.14/site-packages/_pytest/config/__init__.py", line 199, in main
    ret: ExitCode | int = config.hook.pytest_cmdline_main(config=config)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
  File "/usr/local/lib/python3.14/site-packages/_pytest/main.py", line 365, in pytest_cmdline_main
    return wrap_session(config, _main)
  File "/usr/local/lib/python3.14/site-packages/_pytest/main.py", line 318, in wrap_session
    session.exitstatus = doit(config, session) or 0
  File "/usr/local/lib/python3.14/site-packages/_pytest/main.py", line 372, in _main
    config.hook.pytest_runtestloop(session=session)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
  File "/usr/local/lib/python3.14/site-packages/_pytest/main.py", line 396, in pytest_runtestloop
    item.config.hook.pytest_runtest_protocol(item=item, nextitem=nextitem)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
  File "/usr/local/lib/python3.14/site-packages/_pytest/runner.py", line 118, in pytest_runtest_protocol
    runtestprotocol(item, nextitem=nextitem)
  File "/usr/local/lib/python3.14/site-packages/_pytest/runner.py", line 137, in runtestprotocol
    reports.append(call_and_report(item, "call", log))
  File "/usr/local/lib/python3.14/site-packages/_pytest/runner.py", line 244, in call_and_report
    call = CallInfo.from_call(
  File "/usr/local/lib/python3.14/site-packages/_pytest/runner.py", line 353, in from_call
    result: TResult | None = func()
  File "/usr/local/lib/python3.14/site-packages/_pytest/runner.py", line 245, in <lambda>
    lambda: runtest_hook(item=item, **kwds),
  File "/usr/local/lib/python3.14/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
  File "/usr/local/lib/python3.14/site-packages/_pytest/runner.py", line 179, in pytest_runtest_call
    item.runtest()
  File "/usr/local/lib/python3.14/site-packages/pytest_asyncio/plugin.py", line 469, in runtest
    super().runtest()
  File "/usr/local/lib/python3.14/site-packages/_pytest/python.py", line 1720, in runtest
    self.ihook.pytest_pyfunc_call(pyfuncitem=self)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_hooks.py", line 512, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
  File "/usr/local/lib/python3.14/site-packages/pluggy/_callers.py", line 121, in _multicall
    res = hook_impl.function(*args)
  File "/usr/local/lib/python3.14/site-packages/_pytest/python.py", line 166, in pytest_pyfunc_call
    result = testfunction(**testargs)
  File "/usr/local/lib/python3.14/site-packages/pytest_asyncio/plugin.py", line 716, in inner
    runner.run(coro, context=context)
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/runners.py", line 127, in run
    return self._loop.run_until_complete(task)
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 706, in run_until_complete
    self.run_forever()
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 677, in run_forever
    self._run_once()
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py", line 2008, in _run_once
    event_list = self._selector.select(timeout)
  File "/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/selectors.py", line 548, in select
    kev_list = self._selector.control(None, max_ev, timeout)
+++++++++++++++++++++++++++++++++++ Timeout ++++++++++++++++++++++++++++++++++++

--- Full Pipeline Tests ---
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.2, pluggy-1.6.0 -- /usr/local/opt/python@3.14/bin/python3.14
cachedir: .pytest_cache
rootdir: /Volumes/Extreme SSD/projects/story-portal-app/platform/tests/e2e
configfile: pytest.ini
plugins: anyio-4.12.1, timeout-2.4.0, asyncio-1.3.0
timeout: 180.0s
timeout method: thread
timeout func_only: False
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 3 items

tests/e2e/test_full_pipeline.py::TestFullPipeline::test_goal_to_evaluation_pipeline PASSED [ 33%]
tests/e2e/test_full_pipeline.py::TestFullPipeline::test_multi_task_plan_execution FAILED [ 66%]
tests/e2e/test_full_pipeline.py::TestFullPipeline::test_all_layers_concurrent PASSED [100%]

=================================== FAILURES ===================================
_______________ TestFullPipeline.test_multi_task_plan_execution ________________
src/L05_planning/services/goal_decomposer.py:389: in _parse_llm_response
    data = json.loads(json_str)
           ^^^^^^^^^^^^^^^^^^^^
/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/json/__init__.py:352: in loads
    return _default_decoder.decode(s)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/json/decoder.py:345: in decode
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/usr/local/Cellar/python@3.14/3.14.2/Frameworks/Python.framework/Versions/3.14/lib/python3.14/json/decoder.py:363: in raw_decode
    raise JSONDecodeError("Expecting value", s, err.value) from None
E   json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)

During handling of the above exception, another exception occurred:
src/L05_planning/services/goal_decomposer.py:341: in _decompose_llm
    plan = self._parse_llm_response(goal, response.content, response)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/L05_planning/services/goal_decomposer.py:435: in _parse_llm_response
    raise PlanningError.from_code(
E   src.L05_planning.models.error_codes.PlanningError: ErrorCode.E5106: LLM response could not be parsed | Details: {'error': 'Expecting value: line 1 column 1 (char 0)', 'content': 'Here are the decomposed tasks:\n\n{\n  "tasks": [\n    {\n      "id": "task-1",\n      "name": "Read file",\n      "description": "Open the specified file in read mode and retrieve its contents.",\n      "typ'}

During handling of the above exception, another exception occurred:
tests/e2e/test_full_pipeline.py:115: in test_multi_task_plan_execution
    plan = await planner.create_plan(goal)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/L05_planning/services/planning_service.py:154: in create_plan
    plan = await self.decomposer.decompose(goal)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/L05_planning/services/goal_decomposer.py:131: in decompose
    plan = await self._decompose_hybrid(goal)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/L05_planning/services/goal_decomposer.py:193: in _decompose_hybrid
    return await self._decompose_llm(goal)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/L05_planning/services/goal_decomposer.py:353: in _decompose_llm
    raise PlanningError.from_code(
E   src.L05_planning.models.error_codes.PlanningError: ErrorCode.E5101: LLM-based decomposition encountered an error | Details: {'goal_id': '1ef8ecda-177e-4493-a995-5de88cabac36', 'error': 'ErrorCode.E5106: LLM response could not be parsed | Details: {\'error\': \'Expecting value: line 1 column 1 (char 0)\', \'content\': \'Here are the decomposed tasks:\\n\\n{\\n  "tasks": [\\n    {\\n      "id": "task-1",\\n      "name": "Read file",\\n      "description": "Open the specified file in read mode and retrieve its contents.",\\n      "typ\'}'}
------------------------------ Captured log call -------------------------------
WARNING  src.L04_model_gateway.services.semantic_cache:semantic_cache.py:306 Embedding generation failed: Client error '404 Not Found' for url 'http://localhost:11434/api/embeddings'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/404
ERROR    src.L04_model_gateway.providers.base.ollama:ollama_adapter.py:149 Ollama timeout: 
WARNING  src.L04_model_gateway.services.model_gateway:model_gateway.py:273 Primary model llama3.1:8b failed: [E4202] Ollama request timed out - {'timeout': 60}, trying 2 fallbacks
WARNING  src.L04_model_gateway.services.semantic_cache:semantic_cache.py:306 Embedding generation failed: Client error '404 Not Found' for url 'http://localhost:11434/api/embeddings'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/404
ERROR    src.L05_planning.services.goal_decomposer:goal_decomposer.py:434 Failed to parse LLM response as JSON: Expecting value: line 1 column 1 (char 0)
ERROR    src.L05_planning.services.goal_decomposer:goal_decomposer.py:352 LLM decomposition failed: ErrorCode.E5106: LLM response could not be parsed | Details: {'error': 'Expecting value: line 1 column 1 (char 0)', 'content': 'Here are the decomposed tasks:\n\n{\n  "tasks": [\n    {\n      "id": "task-1",\n      "name": "Read file",\n      "description": "Open the specified file in read mode and retrieve its contents.",\n      "typ'}
=========================== short test summary info ============================
FAILED tests/e2e/test_full_pipeline.py::TestFullPipeline::test_multi_task_plan_execution - src.L05_planning.models.error_codes.PlanningError: ErrorCode.E5101: LLM-based decomposition encountered an error | Details: {'goal_id': '1ef8ecda-177e-4493-a995-5de88cabac36', 'error': 'ErrorCode.E5106: LLM response could not be parsed | Details: {\'error\': \'Expecting value: line 1 column 1 (char 0)\', \'content\': \'Here are the decomposed tasks:\\n\\n{\\n  "tasks": [\\n    {\\n      "id": "task-1",\\n      "name": "Read file",\\n      "description": "Open the specified file in read mode and retrieve its contents.",\\n      "typ\'}'}
=================== 1 failed, 2 passed in 208.63s (0:03:28) ====================

--- Error Handling Tests ---
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.2, pluggy-1.6.0 -- /usr/local/opt/python@3.14/bin/python3.14
cachedir: .pytest_cache
rootdir: /Volumes/Extreme SSD/projects/story-portal-app/platform/tests/e2e
configfile: pytest.ini
plugins: anyio-4.12.1, timeout-2.4.0, asyncio-1.3.0
timeout: 60.0s
timeout method: thread
timeout func_only: False
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 5 items

tests/e2e/test_error_handling.py::TestErrorHandling::test_l05_invalid_goal_handling FAILED [ 20%]
tests/e2e/test_error_handling.py::TestErrorHandling::test_l04_invalid_request_handling FAILED [ 40%]
tests/e2e/test_error_handling.py::TestErrorHandling::test_l06_malformed_event_handling PASSED [ 60%]
tests/e2e/test_error_handling.py::TestErrorHandling::test_layer_cleanup_idempotent PASSED [ 80%]
tests/e2e/test_error_handling.py::TestErrorHandling::test_layer_double_initialization PASSED [100%]

=================================== FAILURES ===================================
_______________ TestErrorHandling.test_l05_invalid_goal_handling _______________
tests/e2e/test_error_handling.py:27: in test_l05_invalid_goal_handling
    plan = await planner.create_plan(goal)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/L05_planning/services/planning_service.py:154: in create_plan
    plan = await self.decomposer.decompose(goal)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/L05_planning/services/goal_decomposer.py:113: in decompose
    raise PlanningError.from_code(
E   src.L05_planning.models.error_codes.PlanningError: ErrorCode.E5004: Goal text contains invalid characters or injection patterns | Details: {'goal_id': '1ab71ec8-dec7-4cab-a8bb-b1be636fa666', 'error': 'Goal text contains invalid characters (E5004)'}
_____________ TestErrorHandling.test_l04_invalid_request_handling ______________
tests/e2e/test_error_handling.py:50: in test_l04_invalid_request_handling
    logical_prompt=LogicalPrompt(
E   TypeError: LogicalPrompt.__init__() got an unexpected keyword argument 'system'
=========================== short test summary info ============================
FAILED tests/e2e/test_error_handling.py::TestErrorHandling::test_l05_invalid_goal_handling - src.L05_planning.models.error_codes.PlanningError: ErrorCode.E5004: Goal text contains invalid characters or injection patterns | Details: {'goal_id': '1ab71ec8-dec7-4cab-a8bb-b1be636fa666', 'error': 'Goal text contains invalid characters (E5004)'}
FAILED tests/e2e/test_error_handling.py::TestErrorHandling::test_l04_invalid_request_handling - TypeError: LogicalPrompt.__init__() got an unexpected keyword argument 'system'
========================= 2 failed, 3 passed in 1.16s ==========================

--- Performance Tests ---
============================= test session starts ==============================
platform darwin -- Python 3.14.2, pytest-9.0.2, pluggy-1.6.0 -- /usr/local/opt/python@3.14/bin/python3.14
cachedir: .pytest_cache
rootdir: /Volumes/Extreme SSD/projects/story-portal-app/platform/tests/e2e
configfile: pytest.ini
plugins: anyio-4.12.1, timeout-2.4.0, asyncio-1.3.0
timeout: 120.0s
timeout method: thread
timeout func_only: False
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 5 items / 2 deselected / 3 selected

tests/e2e/test_performance.py::TestPerformance::test_layer_initialization_time PASSED [ 33%]
tests/e2e/test_performance.py::TestPerformance::test_plan_creation_latency FAILED [ 66%]
tests/e2e/test_performance.py::TestPerformance::test_event_processing_throughput PASSED [100%]

=================================== FAILURES ===================================
__________________ TestPerformance.test_plan_creation_latency __________________
tests/e2e/test_performance.py:82: in test_plan_creation_latency
    plan = await planner.create_plan(goal)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/L05_planning/services/planning_service.py:171: in create_plan
    raise PlanningError.from_code(
E   src.L05_planning.models.error_codes.PlanningError: ErrorCode.E5600: Plan validation failed | Details: {'goal_id': 'd4f00716-a9f0-49cf-a9a6-d9338e8deee8', 'errors': [{'code': 'E5606', 'message': 'Tool call task missing tool_name', 'level': 'semantic'}]}
------------------------------ Captured log call -------------------------------
WARNING  src.L04_model_gateway.services.semantic_cache:semantic_cache.py:306 Embedding generation failed: Client error '404 Not Found' for url 'http://localhost:11434/api/embeddings'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/404
ERROR    src.L04_model_gateway.providers.base.ollama:ollama_adapter.py:149 Ollama timeout: 
WARNING  src.L04_model_gateway.services.model_gateway:model_gateway.py:273 Primary model llama3.1:8b failed: [E4202] Ollama request timed out - {'timeout': 60}, trying 2 fallbacks
WARNING  src.L04_model_gateway.services.semantic_cache:semantic_cache.py:306 Embedding generation failed: Client error '404 Not Found' for url 'http://localhost:11434/api/embeddings'
For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/404
ERROR    src.L05_planning.services.planning_service:planning_service.py:167 Validation error [E5606]: Tool call task missing tool_name
=========================== short test summary info ============================
FAILED tests/e2e/test_performance.py::TestPerformance::test_plan_creation_latency - src.L05_planning.models.error_codes.PlanningError: ErrorCode.E5600: Plan validation failed | Details: {'goal_id': 'd4f00716-a9f0-49cf-a9a6-d9338e8deee8', 'errors': [{'code': 'E5606', 'message': 'Tool call task missing tool_name', 'level': 'semantic'}]}
============= 1 failed, 2 passed, 2 deselected in 86.91s (0:01:26) =============

==========================================
Test Suite Complete: Thu Jan 15 02:01:52 MST 2026
==========================================
========================= 66 tests collected in 0.09s ==========================
