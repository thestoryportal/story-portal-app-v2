"""
Minimal Locust Load Testing Suite for V2 Platform
==================================================

This is a simplified load test focusing only on implemented endpoints.

Usage:
    locust -f locustfile-minimal.py --host=http://localhost:8009 --users 10 --spawn-rate 2 --run-time 1m --headless
"""

from locust import HttpUser, task, between, events
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Success criteria thresholds
PERFORMANCE_THRESHOLDS = {
    "max_response_time_ms": 500,  # 95th percentile
    "max_error_rate_percent": 1,  # Maximum 1% error rate
    "min_requests_per_second": 100,  # Minimum throughput
}

# Track custom metrics
request_times = []
error_count = 0
success_count = 0

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track all request metrics for threshold validation."""
    global error_count, success_count, request_times

    request_times.append(response_time)

    if exception:
        error_count += 1
    else:
        success_count += 1

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Validate performance against thresholds at test completion."""
    global error_count, success_count, request_times

    total_requests = error_count + success_count

    if total_requests == 0:
        logger.warning("No requests completed")
        return

    # Calculate metrics
    error_rate = (error_count / total_requests) * 100
    p95_response_time = sorted(request_times)[int(len(request_times) * 0.95)] if request_times else 0

    # Validate thresholds
    logger.info("=" * 80)
    logger.info("MINIMAL LOAD TEST RESULTS SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total Requests: {total_requests}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {error_count}")
    logger.info(f"Error Rate: {error_rate:.2f}%")
    logger.info(f"95th Percentile Response Time: {p95_response_time:.2f}ms")
    logger.info("=" * 80)

    # Check thresholds
    threshold_passed = True

    if p95_response_time > PERFORMANCE_THRESHOLDS["max_response_time_ms"]:
        logger.error(f"❌ FAILED: P95 response time ({p95_response_time:.2f}ms) exceeds threshold ({PERFORMANCE_THRESHOLDS['max_response_time_ms']}ms)")
        threshold_passed = False
    else:
        logger.info(f"✅ PASSED: P95 response time within threshold")

    if error_rate > PERFORMANCE_THRESHOLDS["max_error_rate_percent"]:
        logger.error(f"❌ FAILED: Error rate ({error_rate:.2f}%) exceeds threshold ({PERFORMANCE_THRESHOLDS['max_error_rate_percent']}%)")
        threshold_passed = False
    else:
        logger.info(f"✅ PASSED: Error rate within threshold")

    logger.info("=" * 80)

    if threshold_passed:
        logger.info("🎉 ALL PERFORMANCE THRESHOLDS PASSED")
    else:
        logger.error("⚠️  SOME PERFORMANCE THRESHOLDS FAILED")

    logger.info("=" * 80)


class MinimalHealthCheckUser(HttpUser):
    """
    Minimal load test user that only tests health endpoints.

    These endpoints are operational and don't require authentication.
    """
    wait_time = between(1, 3)

    @task(10)
    def health_live(self):
        """Test /health/live endpoint."""
        self.client.get("/health/live", name="GET /health/live")

    @task(5)
    def health_startup(self):
        """Test /health/startup endpoint."""
        self.client.get("/health/startup", name="GET /health/startup")


if __name__ == "__main__":
    """
    Entry point for running minimal load tests.

    Example commands:
        # Light load (baseline)
        locust -f locustfile-minimal.py --host=http://localhost:8009 --users 10 --spawn-rate 2 --run-time 5m --headless --html report-light.html

        # Normal load
        locust -f locustfile-minimal.py --host=http://localhost:8009 --users 100 --spawn-rate 10 --run-time 10m --headless --html report-normal.html

        # Peak load
        locust -f locustfile-minimal.py --host=http://localhost:8009 --users 500 --spawn-rate 50 --run-time 15m --headless --html report-peak.html
    """
    pass
