"""
L07 Learning Layer - L01 Bridge Tests

Tests for enhanced L01 Bridge integration.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4


@pytest.mark.l07
@pytest.mark.unit
class TestL01BridgeBasics:
    """Tests for basic L01 bridge functionality."""

    def test_bridge_initialization(self):
        """Test that bridge initializes correctly."""
        from L07_learning.services.l01_bridge import L07Bridge

        with patch('L07_learning.services.l01_bridge.L01Client'):
            bridge = L07Bridge()
            assert bridge.enabled is True

    @pytest.mark.asyncio
    async def test_bridge_has_event_subscription(self):
        """Test that bridge has event subscription capability."""
        from L07_learning.services.l01_bridge import L07Bridge

        with patch('L07_learning.services.l01_bridge.L01Client'):
            bridge = L07Bridge()
            assert hasattr(bridge, 'subscribe_to_events')

    @pytest.mark.asyncio
    async def test_bridge_has_fallback_support(self):
        """Test that bridge has fallback support."""
        from L07_learning.services.l01_bridge import L07Bridge

        with patch('L07_learning.services.l01_bridge.L01Client'):
            bridge = L07Bridge()
            assert hasattr(bridge, '_fallback_storage')


@pytest.mark.l07
@pytest.mark.unit
class TestEventSubscription:
    """Tests for event subscription functionality."""

    @pytest.mark.asyncio
    async def test_subscribe_to_execution_events(self):
        """Test subscribing to execution events."""
        from L07_learning.services.l01_bridge import L07Bridge

        with patch('L07_learning.services.l01_bridge.L01Client') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            mock_client.subscribe = AsyncMock()

            bridge = L07Bridge()
            callback = AsyncMock()

            await bridge.subscribe_to_events(
                event_types=["execution.completed"],
                callback=callback
            )

            # Should have registered subscription
            assert bridge._subscriptions is not None

    @pytest.mark.asyncio
    async def test_event_callback_invoked(self):
        """Test that event callback is invoked on event."""
        from L07_learning.services.l01_bridge import L07Bridge

        with patch('L07_learning.services.l01_bridge.L01Client'):
            bridge = L07Bridge()

            events_received = []

            async def callback(event):
                events_received.append(event)

            await bridge.subscribe_to_events(
                event_types=["execution.completed"],
                callback=callback
            )

            # Simulate receiving an event
            test_event = {"type": "execution.completed", "data": {"task_id": "123"}}
            await bridge._dispatch_event(test_event)

            assert len(events_received) == 1
            assert events_received[0]["data"]["task_id"] == "123"


@pytest.mark.l07
@pytest.mark.unit
class TestGracefulFallback:
    """Tests for graceful fallback when L01 unavailable."""

    @pytest.mark.asyncio
    async def test_fallback_when_l01_unavailable(self):
        """Test fallback storage when L01 is unavailable."""
        from L07_learning.services.l01_bridge import L07Bridge
        from L07_learning.models.training_example import (
            TrainingExample, ExampleSource, TaskType
        )

        with patch('L07_learning.services.l01_bridge.L01Client') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            # Simulate L01 failure
            mock_client.create_training_example = AsyncMock(
                side_effect=Exception("Connection refused")
            )

            bridge = L07Bridge()
            bridge._l01_available = False

            example = TrainingExample(
                example_id=str(uuid4()),
                execution_id=str(uuid4()),
                task_id=str(uuid4()),
                source_type=ExampleSource.SYNTHETIC,
                input_text="Test input",
                output_text="Test output",
                quality_score=0.8,
                confidence=0.9,
                domain="test",
                task_type=TaskType.SINGLE_STEP,
                difficulty=0.5,
            )

            # Should not raise, should use fallback
            result = await bridge.store_training_example(example)

            # Result may be None but example should be in fallback
            assert bridge.fallback_queue_size() > 0

    @pytest.mark.asyncio
    async def test_fallback_syncs_on_recovery(self):
        """Test that fallback data syncs when L01 recovers."""
        from L07_learning.services.l01_bridge import L07Bridge
        from L07_learning.models.training_example import (
            TrainingExample, ExampleSource, TaskType
        )

        with patch('L07_learning.services.l01_bridge.L01Client') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client

            bridge = L07Bridge()
            bridge._l01_available = False

            # Add to fallback
            example = TrainingExample(
                example_id=str(uuid4()),
                execution_id=str(uuid4()),
                task_id=str(uuid4()),
                source_type=ExampleSource.SYNTHETIC,
                input_text="Test input",
                output_text="Test output",
                quality_score=0.8,
                confidence=0.9,
                domain="test",
                task_type=TaskType.SINGLE_STEP,
                difficulty=0.5,
            )

            await bridge.store_training_example(example)
            assert bridge.fallback_queue_size() > 0

            # Simulate recovery
            bridge._l01_available = True
            mock_client.create_training_example = AsyncMock(
                return_value={"id": str(uuid4())}
            )

            synced = await bridge.sync_fallback()
            assert synced > 0


@pytest.mark.l07
@pytest.mark.unit
class TestHealthCheck:
    """Tests for L01 health checking."""

    @pytest.mark.asyncio
    async def test_check_l01_health(self):
        """Test checking L01 health."""
        from L07_learning.services.l01_bridge import L07Bridge

        with patch('L07_learning.services.l01_bridge.L01Client') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            mock_client.health_check = AsyncMock(return_value=True)

            bridge = L07Bridge()
            is_healthy = await bridge.check_l01_health()

            assert isinstance(is_healthy, bool)

    @pytest.mark.asyncio
    async def test_health_check_updates_availability(self):
        """Test that health check updates availability flag."""
        from L07_learning.services.l01_bridge import L07Bridge

        with patch('L07_learning.services.l01_bridge.L01Client') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            mock_client.health_check = AsyncMock(return_value=True)

            bridge = L07Bridge()
            bridge._l01_available = False

            await bridge.check_l01_health()

            assert bridge._l01_available is True


@pytest.mark.l07
@pytest.mark.unit
class TestDatasetPersistence:
    """Tests for dataset persistence to L01."""

    @pytest.mark.asyncio
    async def test_persist_dataset_to_l01(self):
        """Test persisting dataset to L01."""
        from L07_learning.services.l01_bridge import L07Bridge
        from L07_learning.models.dataset import Dataset

        with patch('L07_learning.services.l01_bridge.L01Client') as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            mock_client.create_dataset = AsyncMock(
                return_value={"id": str(uuid4())}
            )

            bridge = L07Bridge()

            dataset = Dataset(
                name="test_dataset",
                version="1.0.0",
                description="Test dataset",
            )

            result = await bridge.create_dataset(dataset, [])

            assert result is not None


@pytest.mark.l07
@pytest.mark.unit
class TestBridgeMetrics:
    """Tests for bridge metrics."""

    @pytest.mark.asyncio
    async def test_get_bridge_metrics(self):
        """Test getting bridge metrics."""
        from L07_learning.services.l01_bridge import L07Bridge

        with patch('L07_learning.services.l01_bridge.L01Client'):
            bridge = L07Bridge()

            metrics = bridge.get_metrics()

            assert "l01_available" in metrics
            assert "fallback_queue_size" in metrics
            assert "total_synced" in metrics
