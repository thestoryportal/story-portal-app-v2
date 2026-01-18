# L09 API Gateway Audit
## Health Check
{'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757541512, 'trace_id': '16792696d8b14eff825b0464f97af8b9', 'request_id': 'f1d26931-0e21-4626-a050-a83e470b9521', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}## Gateway Configuration
Config not accessible
## Rate Limiting
Request 1: {'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757547183, 'trace_id': '55f403cf61b741eea2bd8f110d89e318', 'request_id': '0e65b4a2-1cd6-4291-92ca-eb899b76ec96', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
HTTP_CODE:401
Request 2: {'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757547207, 'trace_id': '88e3c2f5037c48ab9e4ccac4ea790952', 'request_id': 'e6609f6b-a736-48cd-adc1-5aa0e831d105', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
HTTP_CODE:401
Request 3: {'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757547229, 'trace_id': 'fd73043f14094456b0124be21006fef2', 'request_id': '6951a79a-32d1-4354-9c30-9264ef9186a9', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
HTTP_CODE:401
Request 4: {'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757547252, 'trace_id': '8844a53be1de444f933eb4b1d00ddc14', 'request_id': '8072865a-5847-421b-aae4-e98f414d1a59', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
HTTP_CODE:401
Request 5: {'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757547278, 'trace_id': '7a25ba128ee54b97a1b157c9baf4baf7', 'request_id': 'e405ffe1-5ff2-4170-a3a5-0d5defe0c0a0', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
HTTP_CODE:401
## CORS Configuration
Route discovery not available
## Backend Service Routing
### Testing proxy to port 8001 (L01)
{'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757554723, 'trace_id': 'cb9c43cc1d3644849554dd92b08ced45', 'request_id': '194d2d28-3be7-4ab3-9a80-67a8c4cd26a4', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
Status: 401### Testing proxy to port 8002 (L02)
{'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757554751, 'trace_id': '1f35fe4f0ce346eda93079c5a5f8985a', 'request_id': 'ff9a88a6-a015-4920-b752-6ef969d6b964', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
Status: 401### Testing proxy to port 8003 (L03)
{'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757554777, 'trace_id': 'd64be324a98a450ebf7bd4c6a5ca7c1c', 'request_id': '36396649-7ce3-4a64-bb41-0c147dca9b42', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
Status: 401### Testing proxy to port 8004 (L04)
{'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757554804, 'trace_id': '44c2499df9e54429ad28dfedb5a779df', 'request_id': '9788fba6-8c78-49d2-b4cb-64d6fd0e1bfb', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
Status: 401### Testing proxy to port 8005 (L05)
{'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757554831, 'trace_id': '92c1268c421b4bc386aa1dff32ab6fb5', 'request_id': 'd526f540-15ab-45b9-ac3a-affb9f6aa710', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
Status: 401### Testing proxy to port 8006 (L06)
{'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757554858, 'trace_id': '6efa0baa5973454ab23052498814ff7b', 'request_id': 'ec0e1ec4-a693-43d9-a9c2-d5fa2e310bae', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
Status: 401### Testing proxy to port 8007 (L07)
{'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757554885, 'trace_id': '0ef5b05c1d5f4e539362457e7138bd89', 'request_id': 'af44968a-dfaf-4f45-934b-4ac5aac75f01', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
Status: 401### Testing proxy to port 8010 (L10)
{'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757554913, 'trace_id': 'b01b18a1405041bfa057588279c6d834', 'request_id': '87725e65-761c-41d0-ab0b-72d60f0e7a16', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
Status: 401### Testing proxy to port 8011 (L11)
{'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757554939, 'trace_id': 'c55c6b2d4cd74c8aad0e610344bbc953', 'request_id': 'ea04358e-d1a5-4a07-a385-dc1980666860', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
Status: 401### Testing proxy to port 8012 (L12)
{'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757554967, 'trace_id': 'd0cdaa018085491d99d87e221ee9353e', 'request_id': 'f8817c4e-3960-43c8-8e88-992cf4f0ed7b', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}
Status: 401## Authentication
Found 36 auth-related code lines
## Error Handling
{'error': {'code': 'E9103', 'message': 'Missing authentication credentials', 'timestamp': 1768757555152, 'trace_id': 'df26b16bce3d4e4eb71e009a9dddb898', 'request_id': 'c208abed-4e7b-42f7-94bc-3dbd7b53e23e', 'details': {'supported_methods': ['api_key', 'oauth_jwt', 'mtls']}}}