/**
 * Smoke Test - Story Portal V2
 *
 * Quick validation that all services are responding correctly.
 * Duration: ~2 minutes
 * Purpose: Pre-deployment sanity check
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const serviceAvailability = new Rate('service_availability');
const responseTime = new Trend('response_time');

// Test configuration
export const options = {
  vus: 5, // 5 virtual users
  duration: '2m', // 2 minutes
  thresholds: {
    'http_req_duration': ['p(95)<200'], // 95% of requests < 200ms
    'http_req_failed': ['rate<0.01'], // Error rate < 1%
    'errors': ['rate<0.01'],
    'service_availability': ['rate>0.99'], // 99% availability
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8009';

export default function () {
  group('Health Checks', () => {
    // L09 API Gateway
    let res = http.get(`${BASE_URL}/health/live`);
    check(res, {
      'L09 is alive': (r) => r.status === 200 || r.status === 204,
    }) || errorRate.add(1);
    serviceAvailability.add(res.status === 200 || res.status === 204);
    responseTime.add(res.timings.duration);

    // L01 Data Layer (via gateway)
    res = http.get('http://localhost:8001/health/live');
    check(res, {
      'L01 is alive': (r) => r.status === 200 || r.status === 204,
    }) || errorRate.add(1);

    // L12 Service Hub
    res = http.get('http://localhost:8012/health');
    check(res, {
      'L12 is healthy': (r) => r.status === 200 && r.json('status') === 'healthy',
    }) || errorRate.add(1);
  });

  group('Basic Endpoint Availability', () => {
    // Test endpoints without authentication (if available)
    const endpoints = [
      `${BASE_URL}/health`,
      `${BASE_URL}/health/ready`,
    ];

    endpoints.forEach((endpoint) => {
      const res = http.get(endpoint);
      check(res, {
        [`${endpoint} responds`]: (r) => r.status < 500,
      });
    });
  });

  sleep(1); // 1 second between iterations
}

export function handleSummary(data) {
  return {
    'smoke-test-results.json': JSON.stringify(data),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, options) {
  // Simple summary for console
  return `
Smoke Test Summary
==================
Duration: ${data.state.testRunDurationMs / 1000}s
VUs: ${options.vus || 'N/A'}

Requests:
- Total: ${data.metrics.http_reqs.values.count}
- Failed: ${data.metrics.http_req_failed.values.rate * 100}%
- Duration (avg): ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms
- Duration (p95): ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms

Status: ${data.metrics.http_req_failed.values.rate < 0.01 ? '✅ PASS' : '❌ FAIL'}
`;
}
