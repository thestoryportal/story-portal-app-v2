# Database Schema Audit
## Tables
                     List of relations
    Schema     |          Name           | Type  |  Owner   
---------------+-------------------------+-------+----------
 mcp_documents | agents                  | table | postgres
 mcp_documents | alerts                  | table | postgres
 mcp_documents | anomalies               | table | postgres
 mcp_documents | api_requests            | table | postgres
 mcp_documents | authentication_events   | table | postgres
 mcp_documents | circuit_breaker_events  | table | postgres
 mcp_documents | claims                  | table | postgres
 mcp_documents | compliance_results      | table | postgres
 mcp_documents | configurations          | table | postgres
 mcp_documents | conflicts               | table | postgres
 mcp_documents | consolidations          | table | postgres
 mcp_documents | control_operations      | table | postgres
 mcp_documents | dataset_examples        | table | postgres
 mcp_documents | datasets                | table | postgres
 mcp_documents | document_tags           | table | postgres
 mcp_documents | documents               | table | postgres
 mcp_documents | entities                | table | postgres
 mcp_documents | evaluations             | table | postgres
 mcp_documents | events                  | table | postgres
 mcp_documents | feedback                | table | postgres
 mcp_documents | feedback_entries        | table | postgres
 mcp_documents | goals                   | table | postgres
 mcp_documents | metrics                 | table | postgres
 mcp_documents | model_usage             | table | postgres
 mcp_documents | plans                   | table | postgres
 mcp_documents | provenance              | table | postgres
 mcp_documents | quality_scores          | table | postgres
 mcp_documents | rate_limit_events       | table | postgres
 mcp_documents | saga_executions         | table | postgres
 mcp_documents | saga_steps              | table | postgres
 mcp_documents | sections                | table | postgres
 mcp_documents | service_registry_events | table | postgres
 mcp_documents | sessions                | table | postgres
 mcp_documents | supersessions           | table | postgres
 mcp_documents | tasks                   | table | postgres
 mcp_documents | tool_definitions        | table | postgres
 mcp_documents | tool_executions         | table | postgres
 mcp_documents | tool_invocations        | table | postgres
 mcp_documents | tool_versions           | table | postgres
 mcp_documents | tools                   | table | postgres
 mcp_documents | training_examples       | table | postgres
 mcp_documents | user_interactions       | table | postgres
(42 rows)

## Indexes
                                            List of relations
    Schema     |                    Name                    | Type  |  Owner   |          Table          
---------------+--------------------------------------------+-------+----------+-------------------------
 mcp_documents | agents_did_key                             | index | postgres | agents
 mcp_documents | agents_pkey                                | index | postgres | agents
 mcp_documents | alerts_alert_id_key                        | index | postgres | alerts
 mcp_documents | alerts_pkey                                | index | postgres | alerts
 mcp_documents | anomalies_anomaly_id_key                   | index | postgres | anomalies
 mcp_documents | anomalies_pkey                             | index | postgres | anomalies
 mcp_documents | api_requests_pkey                          | index | postgres | api_requests
 mcp_documents | api_requests_request_id_key                | index | postgres | api_requests
 mcp_documents | authentication_events_event_id_key         | index | postgres | authentication_events
 mcp_documents | authentication_events_pkey                 | index | postgres | authentication_events
 mcp_documents | circuit_breaker_events_event_id_key        | index | postgres | circuit_breaker_events
 mcp_documents | circuit_breaker_events_pkey                | index | postgres | circuit_breaker_events
 mcp_documents | claims_pkey                                | index | postgres | claims
 mcp_documents | compliance_results_pkey                    | index | postgres | compliance_results
 mcp_documents | compliance_results_result_id_key           | index | postgres | compliance_results
 mcp_documents | configurations_namespace_key_key           | index | postgres | configurations
 mcp_documents | configurations_pkey                        | index | postgres | configurations
 mcp_documents | conflicts_pkey                             | index | postgres | conflicts
 mcp_documents | consolidations_pkey                        | index | postgres | consolidations
 mcp_documents | control_operations_operation_id_key        | index | postgres | control_operations
 mcp_documents | control_operations_pkey                    | index | postgres | control_operations
 mcp_documents | dataset_examples_dataset_id_example_id_key | index | postgres | dataset_examples
 mcp_documents | dataset_examples_pkey                      | index | postgres | dataset_examples
 mcp_documents | datasets_pkey                              | index | postgres | datasets
 mcp_documents | document_tags_pkey                         | index | postgres | document_tags
 mcp_documents | documents_pkey                             | index | postgres | documents
 mcp_documents | entities_pkey                              | index | postgres | entities
 mcp_documents | evaluations_pkey                           | index | postgres | evaluations
 mcp_documents | events_pkey                                | index | postgres | events
 mcp_documents | feedback_entries_pkey                      | index | postgres | feedback_entries
 mcp_documents | feedback_pkey                              | index | postgres | feedback
 mcp_documents | goals_goal_id_key                          | index | postgres | goals
 mcp_documents | goals_pkey                                 | index | postgres | goals
 mcp_documents | idx_alerts_agent                           | index | postgres | alerts
 mcp_documents | idx_alerts_delivered                       | index | postgres | alerts
 mcp_documents | idx_alerts_severity                        | index | postgres | alerts
 mcp_documents | idx_alerts_timestamp                       | index | postgres | alerts
 mcp_documents | idx_alerts_type                            | index | postgres | alerts
 mcp_documents | idx_anomalies_agent                        | index | postgres | anomalies
 mcp_documents | idx_anomalies_detected                     | index | postgres | anomalies
 mcp_documents | idx_anomalies_metric                       | index | postgres | anomalies
 mcp_documents | idx_anomalies_severity                     | index | postgres | anomalies
 mcp_documents | idx_anomalies_status                       | index | postgres | anomalies
 mcp_documents | idx_api_requests_consumer                  | index | postgres | api_requests
 mcp_documents | idx_api_requests_path                      | index | postgres | api_requests
 mcp_documents | idx_api_requests_status                    | index | postgres | api_requests
 mcp_documents | idx_api_requests_tenant                    | index | postgres | api_requests
 mcp_documents | idx_api_requests_timestamp                 | index | postgres | api_requests
 mcp_documents | idx_api_requests_trace                     | index | postgres | api_requests
 mcp_documents | idx_auth_events_consumer                   | index | postgres | authentication_events
 mcp_documents | idx_auth_events_success                    | index | postgres | authentication_events
 mcp_documents | idx_auth_events_timestamp                  | index | postgres | authentication_events
 mcp_documents | idx_circuit_breaker_events_service         | index | postgres | circuit_breaker_events
 mcp_documents | idx_circuit_breaker_events_state           | index | postgres | circuit_breaker_events
 mcp_documents | idx_circuit_breaker_events_timestamp       | index | postgres | circuit_breaker_events
 mcp_documents | idx_claims_document                        | index | postgres | claims
 mcp_documents | idx_claims_embedding                       | index | postgres | claims
 mcp_documents | idx_claims_section                         | index | postgres | claims
 mcp_documents | idx_claims_subject                         | index | postgres | claims
 mcp_documents | idx_compliance_agent                       | index | postgres | compliance_results
 mcp_documents | idx_compliance_compliant                   | index | postgres | compliance_results
 mcp_documents | idx_compliance_execution                   | index | postgres | compliance_results
 mcp_documents | idx_compliance_tenant                      | index | postgres | compliance_results
 mcp_documents | idx_compliance_timestamp                   | index | postgres | compliance_results
 mcp_documents | idx_conflicts_claims                       | index | postgres | conflicts
 mcp_documents | idx_conflicts_status                       | index | postgres | conflicts
 mcp_documents | idx_control_operations_agent               | index | postgres | control_operations
 mcp_documents | idx_control_operations_status              | index | postgres | control_operations
 mcp_documents | idx_control_operations_timestamp           | index | postgres | control_operations
 mcp_documents | idx_control_operations_user                | index | postgres | control_operations
 mcp_documents | idx_dataset_examples_dataset               | index | postgres | dataset_examples
 mcp_documents | idx_dataset_examples_split                 | index | postgres | dataset_examples
 mcp_documents | idx_datasets_name                          | index | postgres | datasets
 mcp_documents | idx_docs_content_hash                      | index | postgres | documents
 mcp_documents | idx_docs_embedding                         | index | postgres | documents
 mcp_documents | idx_docs_fts                               | index | postgres | documents
 mcp_documents | idx_docs_source_path                       | index | postgres | documents
 mcp_documents | idx_docs_type                              | index | postgres | documents
 mcp_documents | idx_entities_canonical                     | index | postgres | entities
 mcp_documents | idx_entities_embedding                     | index | postgres | entities
 mcp_documents | idx_entities_name                          | index | postgres | entities
 mcp_documents | idx_events_aggregate                       | index | postgres | events
 mcp_documents | idx_events_created                         | index | postgres | events
 mcp_documents | idx_events_type                            | index | postgres | events
 mcp_documents | idx_goals_agent                            | index | postgres | goals
 mcp_documents | idx_goals_agent_did                        | index | postgres | goals
 mcp_documents | idx_goals_created                          | index | postgres | goals
 mcp_documents | idx_goals_goal_id                          | index | postgres | goals
 mcp_documents | idx_goals_status                           | index | postgres | goals
 mcp_documents | idx_invocation_agent_time                  | index | postgres | tool_invocations
 mcp_documents | idx_invocation_status                      | index | postgres | tool_invocations
 mcp_documents | idx_invocation_tenant_time                 | index | postgres | tool_invocations
 mcp_documents | idx_metrics_agent                          | index | postgres | metrics
 mcp_documents | idx_metrics_labels                         | index | postgres | metrics
 mcp_documents | idx_metrics_name                           | index | postgres | metrics
 mcp_documents | idx_metrics_tenant                         | index | postgres | metrics
 mcp_documents | idx_metrics_timestamp                      | index | postgres | metrics
 mcp_documents | idx_model_usage_agent                      | index | postgres | model_usage
 mcp_documents | idx_model_usage_agent_did                  | index | postgres | model_usage
 mcp_documents | idx_model_usage_created                    | index | postgres | model_usage
 mcp_documents | idx_model_usage_model                      | index | postgres | model_usage
 mcp_documents | idx_model_usage_request                    | index | postgres | model_usage
 mcp_documents | idx_model_usage_session                    | index | postgres | model_usage
 mcp_documents | idx_model_usage_tenant                     | index | postgres | model_usage
 mcp_documents | idx_plans_agent                            | index | postgres | plans
 mcp_documents | idx_plans_created                          | index | postgres | plans
 mcp_documents | idx_plans_goal                             | index | postgres | plans
 mcp_documents | idx_plans_plan_id                          | index | postgres | plans
 mcp_documents | idx_plans_status                           | index | postgres | plans
 mcp_documents | idx_quality_scores_agent                   | index | postgres | quality_scores
 mcp_documents | idx_quality_scores_assessment              | index | postgres | quality_scores
 mcp_documents | idx_quality_scores_tenant                  | index | postgres | quality_scores
 mcp_documents | idx_quality_scores_timestamp               | index | postgres | quality_scores
 mcp_documents | idx_rate_limit_events_consumer             | index | postgres | rate_limit_events
 mcp_documents | idx_rate_limit_events_exceeded             | index | postgres | rate_limit_events
 mcp_documents | idx_rate_limit_events_timestamp            | index | postgres | rate_limit_events
 mcp_documents | idx_saga_executions_started                | index | postgres | saga_executions
 mcp_documents | idx_saga_executions_status                 | index | postgres | saga_executions
 mcp_documents | idx_saga_steps_saga                        | index | postgres | saga_steps
 mcp_documents | idx_saga_steps_status                      | index | postgres | saga_steps
 mcp_documents | idx_sections_document                      | index | postgres | sections
 mcp_documents | idx_sections_embedding                     | index | postgres | sections
 mcp_documents | idx_sections_fts                           | index | postgres | sections
 mcp_documents | idx_service_registry_events_service        | index | postgres | service_registry_events
 mcp_documents | idx_service_registry_events_timestamp      | index | postgres | service_registry_events
 mcp_documents | idx_service_registry_events_type           | index | postgres | service_registry_events
 mcp_documents | idx_tasks_agent                            | index | postgres | tasks
 mcp_documents | idx_tasks_created                          | index | postgres | tasks
 mcp_documents | idx_tasks_plan                             | index | postgres | tasks
 mcp_documents | idx_tasks_status                           | index | postgres | tasks
 mcp_documents | idx_tasks_task_id                          | index | postgres | tasks
 mcp_documents | idx_tool_category                          | index | postgres | tool_definitions
 mcp_documents | idx_tool_deprecation_state                 | index | postgres | tool_definitions
 mcp_documents | idx_tool_description_embedding             | index | postgres | tool_definitions
 mcp_documents | idx_tool_executions_agent                  | index | postgres | tool_executions
 mcp_documents | idx_tool_executions_created                | index | postgres | tool_executions
 mcp_documents | idx_tool_executions_invocation             | index | postgres | tool_executions
 mcp_documents | idx_tool_executions_session                | index | postgres | tool_executions
 mcp_documents | idx_tool_executions_status                 | index | postgres | tool_executions
 mcp_documents | idx_tool_executions_tenant                 | index | postgres | tool_executions
 mcp_documents | idx_tool_executions_tool                   | index | postgres | tool_executions
 mcp_documents | idx_tool_version_tool_id                   | index | postgres | tool_versions
 mcp_documents | idx_training_examples_agent                | index | postgres | training_examples
 mcp_documents | idx_training_examples_domain               | index | postgres | training_examples
 mcp_documents | idx_training_examples_quality              | index | postgres | training_examples
 mcp_documents | idx_user_interactions_timestamp            | index | postgres | user_interactions
 mcp_documents | idx_user_interactions_type                 | index | postgres | user_interactions
 mcp_documents | idx_user_interactions_user                 | index | postgres | user_interactions
 mcp_documents | ix_tool_invocations_agent_did              | index | postgres | tool_invocations
 mcp_documents | ix_tool_invocations_invocation_id          | index | postgres | tool_invocations
 mcp_documents | ix_tool_invocations_session_id             | index | postgres | tool_invocations
 mcp_documents | ix_tool_invocations_tenant_id              | index | postgres | tool_invocations
 mcp_documents | ix_tool_invocations_tool_id                | index | postgres | tool_invocations
 mcp_documents | metrics_pkey                               | index | postgres | metrics
 mcp_documents | model_usage_pkey                           | index | postgres | model_usage
 mcp_documents | model_usage_request_id_key                 | index | postgres | model_usage
 mcp_documents | plans_pkey                                 | index | postgres | plans
 mcp_documents | plans_plan_id_key                          | index | postgres | plans
 mcp_documents | provenance_pkey                            | index | postgres | provenance
 mcp_documents | quality_scores_pkey                        | index | postgres | quality_scores
 mcp_documents | quality_scores_score_id_key                | index | postgres | quality_scores
 mcp_documents | rate_limit_events_event_id_key             | index | postgres | rate_limit_events
 mcp_documents | rate_limit_events_pkey                     | index | postgres | rate_limit_events
 mcp_documents | saga_executions_pkey                       | index | postgres | saga_executions
 mcp_documents | saga_executions_saga_id_key                | index | postgres | saga_executions
 mcp_documents | saga_steps_pkey                            | index | postgres | saga_steps
 mcp_documents | saga_steps_step_id_key                     | index | postgres | saga_steps
 mcp_documents | sections_pkey                              | index | postgres | sections
 mcp_documents | service_registry_events_event_id_key       | index | postgres | service_registry_events
 mcp_documents | service_registry_events_pkey               | index | postgres | service_registry_events
 mcp_documents | sessions_pkey                              | index | postgres | sessions
 mcp_documents | supersessions_pkey                         | index | postgres | supersessions
 mcp_documents | tasks_pkey                                 | index | postgres | tasks
 mcp_documents | tasks_task_id_key                          | index | postgres | tasks
 mcp_documents | tool_definitions_pkey                      | index | postgres | tool_definitions
 mcp_documents | tool_executions_invocation_id_key          | index | postgres | tool_executions
 mcp_documents | tool_executions_pkey                       | index | postgres | tool_executions
 mcp_documents | tool_invocations_pkey                      | index | postgres | tool_invocations
 mcp_documents | tool_versions_pkey                         | index | postgres | tool_versions
 mcp_documents | tool_versions_tool_id_version_key          | index | postgres | tool_versions
 mcp_documents | tools_name_key                             | index | postgres | tools
 mcp_documents | tools_pkey                                 | index | postgres | tools
 mcp_documents | training_examples_pkey                     | index | postgres | training_examples
 mcp_documents | user_interactions_interaction_id_key       | index | postgres | user_interactions
 mcp_documents | user_interactions_pkey                     | index | postgres | user_interactions
(185 rows)

## Foreign Key Constraints
                 conname                 |      conrelid      |     confrelid     
-----------------------------------------+--------------------+-------------------
 sections_document_id_fkey               | sections           | documents
 claims_document_id_fkey                 | claims             | documents
 claims_section_id_fkey                  | claims             | sections
 conflicts_claim_a_id_fkey               | conflicts          | claims
 conflicts_claim_b_id_fkey               | conflicts          | claims
 supersessions_old_document_id_fkey      | supersessions      | documents
 supersessions_new_document_id_fkey      | supersessions      | documents
 consolidations_result_document_id_fkey  | consolidations     | documents
 provenance_document_id_fkey             | provenance         | documents
 document_tags_document_id_fkey          | document_tags      | documents
 feedback_claim_id_fkey                  | feedback           | claims
 feedback_conflict_id_fkey               | feedback           | conflicts
 feedback_document_id_fkey               | feedback           | documents
 tool_versions_tool_id_fkey              | tool_versions      | tool_definitions
 evaluations_agent_id_fkey               | evaluations        | agents
 quality_scores_agent_id_fkey            | quality_scores     | agents
 metrics_agent_id_fkey                   | metrics            | agents
 anomalies_agent_id_fkey                 | anomalies          | agents
 compliance_results_agent_id_fkey        | compliance_results | agents
 alerts_agent_id_fkey                    | alerts             | agents
 feedback_entries_agent_id_fkey          | feedback_entries   | agents
 training_examples_agent_id_fkey         | training_examples  | agents
 dataset_examples_dataset_id_fkey        | dataset_examples   | datasets
 dataset_examples_example_id_fkey        | dataset_examples   | training_examples
 sessions_agent_id_fkey                  | sessions           | agents
 control_operations_target_agent_id_fkey | control_operations | agents
 tool_executions_tool_id_fkey            | tool_executions    | tools
 tool_executions_agent_id_fkey           | tool_executions    | agents
 model_usage_agent_id_fkey               | model_usage        | agents
 goals_agent_id_fkey                     | goals              | agents
 plans_agent_id_fkey                     | plans              | agents
 tasks_agent_id_fkey                     | tasks              | agents
(32 rows)

## Schema Files in Codebase
./platform/ui/node_modules/@typescript-eslint/utils/dist/json-schema.js
./platform/ui/node_modules/@typescript-eslint/utils/dist/json-schema.d.ts.map
./platform/ui/node_modules/@typescript-eslint/utils/dist/json-schema.js.map
./platform/ui/node_modules/@typescript-eslint/utils/dist/json-schema.d.ts
./platform/ui/node_modules/@typescript-eslint/eslint-plugin/dist/rules/naming-convention-utils/schema.js
./platform/ui/node_modules/@typescript-eslint/eslint-plugin/dist/rules/naming-convention-utils/schema.js.map
./platform/ui/node_modules/@types/json-schema
./platform/ui/node_modules/@humanwhocodes/object-schema
./platform/ui/node_modules/@humanwhocodes/object-schema/src/object-schema.js
./platform/ui/node_modules/@eslint/eslintrc/conf/config-schema.js
./platform/ui/node_modules/eslint/lib/config/flat-config-schema.js
./platform/ui/node_modules/eslint/conf/config-schema.js
./platform/ui/node_modules/ajv/lib/compile/schema_obj.js
./platform/ui/node_modules/ajv/lib/definition_schema.js
./platform/ui/node_modules/ajv/lib/refs/json-schema-draft-04.json
./platform/ui/node_modules/ajv/lib/refs/json-schema-draft-06.json
./platform/ui/node_modules/ajv/lib/refs/json-schema-draft-07.json
./platform/ui/node_modules/ajv/lib/refs/json-schema-secure.json
./platform/ui/node_modules/js-yaml/lib/schema
./platform/ui/node_modules/js-yaml/lib/schema.js
./platform/ui/node_modules/json-schema-traverse
./platform/ui/node_modules/json-schema-traverse/spec/fixtures/schema.js
./platform/src/L01_data_layer/routers/models.py
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/sql/schema.py
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/sql/__pycache__/schema.cpython-314.pyc
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/testing/schema.py
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/testing/__pycache__/schema.cpython-314.pyc
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/__pycache__/schema.cpython-314.pyc
./platform/scripts/venv/lib/python3.14/site-packages/pydantic_core/core_schema.py
./platform/scripts/venv/lib/python3.14/site-packages/pydantic_core/__pycache__/core_schema.cpython-314.pyc
