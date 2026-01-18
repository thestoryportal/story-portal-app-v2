# Baseline Load Tests - Execution Checklist

## Status: READY TO RUN

The load testing infrastructure is complete and ready for execution. Run baseline tests when platform services are fully operational.

## Prerequisites

1. **Platform Services Running**
   ```bash
   cd /Volumes/Extreme\ SSD/projects/story-portal-app
   docker-compose -f docker-compose.app.yml up -d
   ```

2. **Verify Platform Health**
   ```bash
   curl http://localhost:8009/health/ready
   # Should return: {"status": "healthy"}
   ```

3. **Install Load Testing Dependencies**
   ```bash
   pip install -r platform/requirements-loadtest.txt
   ```

## Running Baseline Tests

### Option 1: Run Complete Baseline Suite (90 minutes)
```bash
cd platform/load-tests
./run-baseline-tests.sh
```

This runs all 4 baseline tests:
- Light Load (10 users, 5min)
- Normal Load (100 users, 10min)
- Peak Load (500 users, 15min)
- Endurance (200 users, 60min)

### Option 2: Run Individual Tests

#### Quick Smoke Test (30 seconds)
```bash
cd platform/load-tests
locust -f locustfile.py --host=http://localhost:8009 --users 10 --spawn-rate 2 --run-time 30s --headless --only-summary
```

#### Normal Load Test (5 minutes)
```bash
locust -f locustfile.py --host=http://localhost:8009 --users 100 --spawn-rate 10 --run-time 5m --headless --html load-test-report.html
```

## Expected Completion Date

**Target**: Week 9 (after Phase 4 completion)
**Estimated Duration**: 90 minutes for full baseline suite
**Recommended Time**: During off-peak hours

## Success Criteria

All baseline tests must:
- ✅ P95 response time within thresholds
- ✅ Error rate < 1%
- ✅ Throughput meets minimum requirements
- ✅ No system crashes or memory leaks

## Next Steps After Completion

1. Review individual test reports
2. Document baseline metrics in performance documentation
3. Configure production monitoring alerts based on baselines
4. Schedule regular load testing in CI/CD pipeline

---

**Status**: Infrastructure complete, tests ready to run
**Created**: 2026-01-18
**Last Updated**: 2026-01-18
