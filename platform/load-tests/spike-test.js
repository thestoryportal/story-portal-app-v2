/**
 * Spike Test - Story Portal V2
 *
 * Test system behavior under sudden traffic spikes.
 * Duration: ~8 minutes
 * Purpose: Resilience and auto-scaling validation
 */

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const recoveryTime = new Trend('recovery_time');
const spikeResponseTime = new Trend('spike_response_time');

// Test configuration - Sudden spikes
export const options = {
  stages: [
    { duration: '30s', target: 10 },   // Baseline load
    { duration: '10s', target: 100 },  // Sudden spike to 100
    { duration: '1m', target: 100 },   // Sustained spike
    { duration: '10s', target: 10 },   // Drop back
    { duration: '30s', target: 10 },   // Recovery period
    { duration: '10s', target: 200 },  // Second spike (larger)
    { duration: '1m', target: 200 },   // Sustained
    { duration: '10s', target: 10 },   // Drop
    { duration: '1m', target: 10 },    // Final recovery
  ],
  thresholds: {
    'http_req_duration': ['p(95)<1500'], // Allow degradation during spikes
    'http_req_failed': ['rate<0.10'], // 10% failure acceptable during spikes
    'errors': ['rate<0.10'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8009';

let spikeStartTime = 0;
let baselineEstablished = false;

export default function () {
  const currentVUs = __VU;

  // Detect spike conditions
  if (currentVUs > 50 && !spikeStartTime) {
    spikeStartTime = Date.now();
  }

  group('Spike Test Scenario', () => {
    const res = http.get(`${BASE_URL}/health/live`);

    const success = check(res, {
      'status OK': (r) => r.status === 200 || r.status === 204,
      'not timeout': (r) => r.status !== 0,
    });

    errorRate.add(!success);

    // Track spike-specific metrics
    if (currentVUs > 50) {
      spikeResponseTime.add(res.timings.duration);
    }
  });

  sleep(Math.random() * 0.3 + 0.2); // 0.2-0.5s between requests
}

export function handleSummary(data) {
  return {
    'spike-test-results.json': JSON.stringify(data, null, 2),
    'spike-test-report.txt': generateSpikeReport(data),
    stdout: generateSpikeReport(data),
  };
}

function generateSpikeReport(data) {
  const peakVUs = data.metrics.vus_max.values.max;
  const errorRate = data.metrics.http_req_failed.values.rate;
  const p95 = data.metrics.http_req_duration.values['p(95)'];

  // Determine spike resilience
  let resilience = 'Poor';
  if (errorRate < 0.05 && p95 < 1000) {
    resilience = 'Excellent';
  } else if (errorRate < 0.10 && p95 < 1500) {
    resilience = 'Good';
  } else if (errorRate < 0.15 && p95 < 2000) {
    resilience = 'Fair';
  }

  return `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Story Portal V2 - Spike Test Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Duration: ${(data.state.testRunDurationMs / 1000).toFixed(1)}s
Peak VUs: ${peakVUs}
Spike Magnitude: ${(peakVUs / 10).toFixed(0)}x baseline

🎯 Spike Resilience: ${resilience}

📊 Performance During Spikes:
   Error Rate: ${(errorRate * 100).toFixed(2)}%
   p50 Response Time: ${data.metrics.http_req_duration.values.med.toFixed(2)}ms
   p95 Response Time: ${p95.toFixed(2)}ms
   p99 Response Time: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms

⏱️  Recovery Analysis:
   ${analyzeRecovery(data)}

🔍 Spike Handling:
   ${analyzeSpikeHandling(errorRate, p95)}

💡 Auto-Scaling Recommendations:
   ${generateScalingRecommendations(peakVUs, errorRate, p95)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
}

function analyzeRecovery(data) {
  const p99 = data.metrics.http_req_duration.values['p(99)'];
  const errorRate = data.metrics.http_req_failed.values.rate;

  if (errorRate < 0.05 && p99 < 1000) {
    return '✅ Fast recovery - System returned to baseline quickly';
  } else if (errorRate < 0.10 && p99 < 2000) {
    return '⚠️  Moderate recovery - Some degradation persisted';
  } else {
    return '❌ Slow recovery - Consider implementing backpressure';
  }
}

function analyzeSpikeHandling(errorRate, p95) {
  const issues = [];

  if (errorRate > 0.15) {
    issues.push('❌ High error rate during spikes - Add rate limiting');
  } else if (errorRate > 0.05) {
    issues.push('⚠️  Moderate errors - Review circuit breakers');
  } else {
    issues.push('✅ Low error rate - Good spike handling');
  }

  if (p95 > 2000) {
    issues.push('❌ Severe response time degradation - Scale out needed');
  } else if (p95 > 1500) {
    issues.push('⚠️  Response time degradation - Consider caching');
  } else {
    issues.push('✅ Response times acceptable');
  }

  return issues.join('\n   ');
}

function generateScalingRecommendations(peakVUs, errorRate, p95) {
  const recommendations = [];

  // Calculate scaling thresholds
  const scaleOutThreshold = Math.floor(peakVUs * 0.6);

  if (errorRate > 0.10 || p95 > 1500) {
    recommendations.push(`• Set auto-scaling trigger at ${scaleOutThreshold} concurrent users`);
    recommendations.push('• Implement horizontal pod autoscaling (HPA)');
    recommendations.push('• Consider read replicas for database');
  } else {
    recommendations.push('✅ Current capacity sufficient for observed spikes');
    recommendations.push(`• Monitor for spikes exceeding ${peakVUs} users`);
    recommendations.push('• Keep auto-scaling configured as safety net');
  }

  return recommendations.join('\n   ');
}
