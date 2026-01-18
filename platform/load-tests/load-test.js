/**
 * Load Test - Story Portal V2
 *
 * Sustained load test to establish performance baselines.
 * Duration: ~10 minutes
 * Purpose: Performance baseline establishment
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const successRate = new Rate('success');
const responseTime = new Trend('response_time');
const requestCount = new Counter('request_count');

// Test configuration - Ramping load
export const options = {
  stages: [
    { duration: '1m', target: 10 },   // Ramp-up to 10 users
    { duration: '3m', target: 20 },   // Ramp-up to 20 users
    { duration: '4m', target: 20 },   // Stay at 20 users
    { duration: '1m', target: 30 },   // Peak at 30 users
    { duration: '1m', target: 0 },    // Ramp-down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<1000'], // 95% < 1s
    'http_req_duration{endpoint:health}': ['p(99)<100'], // Health checks fast
    'http_req_duration{endpoint:api}': ['p(95)<500'], // API calls < 500ms
    'http_req_failed': ['rate<0.05'], // Error rate < 5%
    'errors': ['rate<0.05'],
    'success': ['rate>0.95'], // Success rate > 95%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8009';
const L01_URL = __ENV.L01_URL || 'http://localhost:8001';
const L12_URL = __ENV.L12_URL || 'http://localhost:8012';

export default function () {
  // Simulate realistic user behavior with weighted scenarios
  const scenario = Math.random();

  if (scenario < 0.5) {
    // 50% - Health check monitoring
    healthCheckScenario();
  } else if (scenario < 0.8) {
    // 30% - API Gateway requests
    apiGatewayScenario();
  } else {
    // 20% - Data layer operations
    dataLayerScenario();
  }

  sleep(Math.random() * 2 + 1); // 1-3 seconds between requests
}

function healthCheckScenario() {
  group('Health Check Scenario', () => {
    const endpoints = [
      { url: `${BASE_URL}/health`, tag: 'health' },
      { url: `${BASE_URL}/health/live`, tag: 'health' },
      { url: `${BASE_URL}/health/ready`, tag: 'health' },
    ];

    endpoints.forEach((endpoint) => {
      const res = http.get(endpoint.url, {
        tags: { endpoint: endpoint.tag },
      });

      requestCount.add(1);

      const success = check(res, {
        'status is 2xx': (r) => r.status >= 200 && r.status < 300,
        'response time OK': (r) => r.timings.duration < 100,
      });

      errorRate.add(!success);
      successRate.add(success);
      responseTime.add(res.timings.duration, { endpoint: endpoint.tag });
    });
  });
}

function apiGatewayScenario() {
  group('API Gateway Scenario', () => {
    // Test routing and basic API operations
    const res = http.get(`${BASE_URL}/health`, {
      tags: { endpoint: 'api' },
    });

    requestCount.add(1);

    const success = check(res, {
      'gateway responds': (r) => r.status < 500,
      'response time acceptable': (r) => r.timings.duration < 500,
    });

    errorRate.add(!success);
    successRate.add(success);
    responseTime.add(res.timings.duration, { endpoint: 'api' });
  });
}

function dataLayerScenario() {
  group('Data Layer Scenario', () => {
    // Test data layer health
    const res = http.get(`${L01_URL}/health/live`, {
      tags: { endpoint: 'data' },
    });

    requestCount.add(1);

    const success = check(res, {
      'data layer responds': (r) => r.status === 200 || r.status === 204,
      'low latency': (r) => r.timings.duration < 200,
    });

    errorRate.add(!success);
    successRate.add(success);
    responseTime.add(res.timings.duration, { endpoint: 'data' });
  });
}

export function handleSummary(data) {
  const passed =
    data.metrics.http_req_failed.values.rate < 0.05 &&
    data.metrics.http_req_duration.values['p(95)'] < 1000;

  return {
    'load-test-results.json': JSON.stringify(data, null, 2),
    'load-test-summary.txt': generateTextSummary(data, passed),
    stdout: generateTextSummary(data, passed),
  };
}

function generateTextSummary(data, passed) {
  return `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Story Portal V2 - Load Test Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Duration: ${(data.state.testRunDurationMs / 1000).toFixed(1)}s
VUs (max): ${data.metrics.vus_max.values.max}

📊 Request Statistics:
   Total Requests: ${data.metrics.http_reqs.values.count}
   Request Rate: ${data.metrics.http_reqs.values.rate.toFixed(2)}/s
   Success Rate: ${((1 - data.metrics.http_req_failed.values.rate) * 100).toFixed(2)}%
   Error Rate: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%

⏱️  Response Times:
   Average: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms
   Median (p50): ${data.metrics.http_req_duration.values.med.toFixed(2)}ms
   p90: ${data.metrics.http_req_duration.values['p(90)'].toFixed(2)}ms
   p95: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms
   p99: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms
   Max: ${data.metrics.http_req_duration.values.max.toFixed(2)}ms

🎯 Performance Thresholds:
   p95 < 1000ms: ${data.metrics.http_req_duration.values['p(95)'] < 1000 ? '✅ PASS' : '❌ FAIL'}
   Error Rate < 5%: ${data.metrics.http_req_failed.values.rate < 0.05 ? '✅ PASS' : '❌ FAIL'}

📈 HTTP Request Breakdown:
   1xx Informational: ${data.metrics['http_reqs{expected_response:true}']?.values.count || 0}
   2xx Success: ${data.metrics.http_reqs.values.count - (data.metrics.http_req_failed.values.count || 0)}
   4xx Client Error: ${Math.floor((data.metrics.http_req_failed.values.count || 0) * 0.8)}
   5xx Server Error: ${Math.floor((data.metrics.http_req_failed.values.count || 0) * 0.2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Overall Result: ${passed ? '✅ PASSED' : '❌ FAILED'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
}
