# External Dependencies Audit
## Python Dependencies
## External API References
./platform/archive/l12-pre-v2/config/settings.py:273:        # Must start with http:// or https://
./platform/archive/l12-pre-v2/config/settings.py:274:        if not v.startswith(("http://", "https://")):
./platform/archive/l12-pre-v2/config/settings.py:275:            raise ValueError(f"Base URL must start with http:// or https://: {v}")
./platform/src/L04_model_gateway/providers/anthropic_adapter.py:35:        base_url: str = "https://api.anthropic.com",
./platform/src/L04_model_gateway/providers/openai_adapter.py:35:        base_url: str = "https://api.openai.com/v1",
./platform/src/L09_api_gateway/models/operation_models.py:41:        if not v.startswith("https://"):
./platform/src/L09_api_gateway/services/async_handler.py:204:        if not url.startswith("https://"):
./platform/src/L10_human_interface/app.py:92:        base_url=f"http://{settings.l01_host}:{settings.l01_port}",
./platform/src/L10_human_interface/app.py:99:        l01_base_url=f"http://{settings.l01_host}:{settings.l01_port}",
./platform/src/L12_nl_interface/config/settings.py:326:        # Must start with http:// or https://
./platform/src/L12_nl_interface/config/settings.py:327:        if not v.startswith(("http://", "https://")):
./platform/src/L12_nl_interface/config/settings.py:328:            raise ValueError(f"Base URL must start with http:// or https://: {v}")
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/__init__.py:6:# the MIT License: https://www.opensource.org/licenses/mit-license.php
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:6:# the MIT License: https://www.opensource.org/licenses/mit-license.php
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:430:  https://blogs.oracle.com/oraclemagazine/on-rownum-and-limiting-results .
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:467:https://web.archive.org/web/20090317041251/https://asktom.oracle.com/tkyte/update_cascade/index.html
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:752:    <https://python-oracledb.readthedocs.io/en/latest/user_guide/vector_data_type.html>`_ - in the documentation
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:905:    `CREATE VECTOR INDEX <https://www.oracle.com/pls/topic/lookup?ctx=dblatest&id=GUID-B396C369-54BB-4098-A0DD-7C54B3A0D66F>`_ - in the Oracle documentation
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:1132:                # https://www.oracletutorial.com/oracle-basics/oracle-float/
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:1321:                # https://docs.oracle.com/database/121/SQLRF/queries006.htm#SQLRF52354
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:1514:                # https://blogs.oracle.com/oraclemagazine/\
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:1782:        # https://web.archive.org/web/20090317041251/https://asktom.oracle.com/tkyte/update_cascade/index.html
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:2027:        # https://docs.oracle.com/cd/A87860_01/doc/index.htm
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:2030:        # https://docs.oracle.com/cd/A64702_01/doc/index.htm
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/base.py:2883:                # https://docs.oracle.com/cd/B14117_01/server.101/b10758/sqlqr06.htm
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/cx_oracle.py:6:# the MIT License: https://www.opensource.org/licenses/mit-license.php
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/cx_oracle.py:14:    :url: https://oracle.github.io/python-cx_Oracle/
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/cx_oracle.py:85:<https://cx-oracle.readthedocs.io/en/latest/user_guide/connection_handling.html#autonomousdb>`_.
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/cx_oracle.py:221:<https://cx-oracle.readthedocs.io/en/latest/user_guide/ha.html#application-continuity-ac>`_.
./platform/scripts/venv/lib/python3.14/site-packages/sqlalchemy/dialects/oracle/cx_oracle.py:232:<https://cx-oracle.readthedocs.io/en/latest/user_guide/connection_handling.html#database-resident-connection-pooling-drcp>`_.
## CI/CD Files
No GitHub Actions found
## Lock Files
./platform/ui/node_modules/uri-js/yarn.lock
./platform/ui/node_modules/combined-stream/yarn.lock
./platform/ui/node_modules/lodash/flake.lock
./platform/ui/package-lock.json
./platform/services/mcp-document-consolidator/node_modules/uri-js/yarn.lock
./platform/services/mcp-document-consolidator/package-lock.json
./platform/services/mcp-context-orchestrator/package-lock.json
./platform/services/mcp-context-orchestrator/node_modules/uri-js/yarn.lock
./my-project/node_modules/.pnpm/uri-js@4.4.1/node_modules/uri-js/yarn.lock
./my-project/node_modules/.pnpm/webgl-constants@1.1.1/node_modules/webgl-constants/yarn.lock
