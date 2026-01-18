/**
 * Stress Test - Story Portal V2
 *
 * Find the breaking point of the system.
 * Duration: ~15 minutes
 * Purpose: Capacity planning and bottleneck identification
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const connectionErrors = new Counter('connection_errors');
const timeouts = new Counter('timeouts');
const responseTime = new Trend('response_time');

// Test configuration - Progressive stress
export const options = {
  stages: [
    { duration: '2m', target: 10 },   // Warm-up
    { duration: '3m', target: 50 },   // Ramp to 50
    { duration: '3m', target: 100 },  // Ramp to 100
    { duration: '3m', target: 200 },  // Ramp to 200 (stress)
    { duration: '2m', target: 300 },  // Ramp to 300 (breaking point)
    { duration: '2m', target: 0 },    // Ramp-down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<2000'], // Allow degradation to 2s
    'http_req_failed': ['rate<0.20'], // Allow 20% failure at peak
    'errors': ['rate<0.20'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8009';

export default function () {
  group('Stress Test Scenario', () => {
    const res = http.get(`${BASE_URL}/health/live`, {
      timeout: '10s', // 10-second timeout
    });

    const success = check(res, {
      'responds': (r) => r.status !== 0,
      'not 5xx': (r) => r.status < 500 || r.status === 0,
    });

    if (res.status === 0) {
      connectionErrors.add(1);
    }

    if (res.timings.duration > 10000) {
      timeouts.add(1);
    }

    errorRate.add(!success);
    responseTime.add(res.timings.duration);
  });

  sleep(Math.random() * 0.5); // Minimal sleep for stress
}

export function handleSummary(data) {
  const maxVUs = data.metrics.vus_max.values.max;
  const errorRate = data.metrics.http_req_failed.values.rate;
  const p95Duration = data.metrics.http_req_duration.values['p(95)'];

  // Determine system capacity
  let capacity = 'Unknown';
  if (errorRate < 0.05 && p95Duration < 1000) {
    capacity = `${maxVUs}+ users (system not stressed)`;
  } else if (errorRate < 0.10 && p95Duration < 2000) {
    capacity = `~${Math.floor(maxVUs * 0.8)} users (recommended capacity)`;
  } else {
    capacity = `~${Math.floor(maxVUs * 0.5)} users (breaking point reached)`;
  }

  return {
    'stress-test-results.json': JSON.stringify(data, null, 2),
    'stress-test-capacity.txt': generateCapacityReport(data, capacity),
    stdout: generateCapacityReport(data, capacity),
  };
}

function generateCapacityReport(data, capacity) {
  return `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Story Portal V2 - Stress Test Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Duration: ${(data.state.testRunDurationMs / 1000).toFixed(1)}s
Peak VUs: ${data.metrics.vus_max.values.max}

📊 System Capacity Analysis:
   Estimated Capacity: ${capacity}
   Total Requests: ${data.metrics.http_reqs.values.count}
   Peak Request Rate: ${data.metrics.http_reqs.values.rate.toFixed(2)}/s

⚠️  Failure Analysis:
   Error Rate: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%
   Connection Errors: ${data.metrics.connection_errors?.values.count || 0}
   Timeouts: ${data.metrics.timeouts?.values.count || 0}

⏱️  Response Time Degradation:
   p50: ${data.metrics.http_req_duration.values.med.toFixed(2)}ms
   p90: ${data.metrics.http_req_duration.values['p(90)'].toFixed(2)}ms
   p95: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms
   p99: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms
   Max: ${data.metrics.http_req_duration.values.max.toFixed(2)}ms

🔍 Bottleneck Indicators:
   ${analyzeBottlenecks(data)}

💡 Recommendations:
   ${generateRecommendations(data)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
}

function analyzeBottlenecks(data) {
  const indicators = [];
  const errorRate = data.metrics.http_req_failed.values.rate;
  const p95Duration = data.metrics.http_req_duration.values['p(95)'];
  const connectionErrors = data.metrics.connection_errors?.values.count || 0;

  if (errorRate > 0.15) {
    indicators.push('❌ High error rate - Service overload detected');
  }

  if (p95Duration > 2000) {
    indicators.push('⚠️  Slow responses - Database or compute bottleneck');
  }

  if (connectionErrors > 100) {
    indicators.push('🔌 Connection failures - Network or connection pool limits');
  }

  if (indicators.length === 0) {
    indicators.push('✅ No major bottlenecks detected');
  }

  return indicators.join('\n   ');
}

function generateRecommendations(data) {
  const recommendations = [];
  const errorRate = data.metrics.http_req_failed.values.rate;
  const p95Duration = data.metrics.http_req_duration.values['p(95)'];

  if (errorRate > 0.10) {
    recommendations.push('• Scale horizontally (add more service instances)');
    recommendations.push('• Implement rate limiting');
    recommendations.push('• Add circuit breakers');
  }

  if (p95Duration > 1000) {
    recommendations.push('• Optimize database queries');
    recommendations.push('• Add caching (Redis)');
    recommendations.push('• Review slow endpoints');
  }

  if (recommendations.length === 0) {
    recommendations.push('✅ System performing well under stress');
    recommendations.push('• Monitor production for similar load patterns');
  }

  return recommendations.join('\n   ');
}
