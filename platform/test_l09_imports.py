#!/usr/bin/env python3
"""
Quick test to verify L09 imports work
"""

import sys
sys.path.insert(0, '/Volumes/Extreme SSD/projects/story-portal-app/platform')

try:
    print("Testing L09 imports...")

    # Test error codes
    from src.L09_api_gateway.errors import ErrorCode, GatewayError
    print("✓ Errors module imported")

    # Test models
    from src.L09_api_gateway.models import (
        RequestContext,
        ConsumerProfile,
        RouteDefinition,
    )
    print("✓ Models imported")

    # Test that error codes are defined
    assert ErrorCode.E9001
    assert ErrorCode.E9101
    assert ErrorCode.E9201
    print("✓ Error codes defined")

    # Test model instantiation
    from src.L09_api_gateway.models import RequestMetadata
    metadata = RequestMetadata(
        method="GET",
        path="/test",
        client_ip="127.0.0.1",
    )
    print("✓ Models can be instantiated")

    print("\n✅ All L09 imports successful!")

except Exception as e:
    print(f"\n❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
