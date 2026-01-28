"""
L10 Human Interface Layer - Cost Service Tests

Tests for CostService including L06 bridge integration.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timedelta, UTC

from ..models import CostSummary, ErrorCode, InterfaceError
from ..services import CostService


@pytest.mark.l10
class TestCostServiceSummary:
    """Tests for CostService.get_cost_summary()."""

    @pytest.mark.asyncio
    async def test_get_cost_summary_success(self, cost_service, mock_l06_bridge):
        """Test successful cost summary retrieval."""
        result = await cost_service.get_cost_summary("tenant-1")

        assert isinstance(result, CostSummary)
        assert result.total_cost_dollars >= 0
        mock_l06_bridge.query_metrics.assert_called()

    @pytest.mark.asyncio
    async def test_get_cost_summary_aggregates_by_model(self, mock_l06_bridge):
        """Test that costs are aggregated by model."""
        mock_l06_bridge.query_metrics.return_value = [
            {
                "metric_name": "model_cost_dollars",
                "value": 0.10,
                "labels": {"model": "claude-3-opus", "agent_id": "agent-1"},
            },
            {
                "metric_name": "model_cost_dollars",
                "value": 0.05,
                "labels": {"model": "claude-3-sonnet", "agent_id": "agent-1"},
            },
            {
                "metric_name": "model_cost_dollars",
                "value": 0.03,
                "labels": {"model": "claude-3-opus", "agent_id": "agent-2"},
            },
        ]
        service = CostService(l06_bridge=mock_l06_bridge)

        result = await service.get_cost_summary("tenant-1")

        assert "claude-3-opus" in result.cost_by_model
        assert result.cost_by_model["claude-3-opus"] == 0.13  # 0.10 + 0.03
        assert result.cost_by_model["claude-3-sonnet"] == 0.05

    @pytest.mark.asyncio
    async def test_get_cost_summary_aggregates_by_agent(self, mock_l06_bridge):
        """Test that costs are aggregated by agent."""
        mock_l06_bridge.query_metrics.return_value = [
            {
                "metric_name": "model_cost_dollars",
                "value": 0.10,
                "labels": {"model": "claude-3-opus", "agent_id": "agent-1"},
            },
            {
                "metric_name": "model_cost_dollars",
                "value": 0.05,
                "labels": {"model": "claude-3-sonnet", "agent_id": "agent-1"},
            },
            {
                "metric_name": "model_cost_dollars",
                "value": 0.03,
                "labels": {"model": "claude-3-opus", "agent_id": "agent-2"},
            },
        ]
        service = CostService(l06_bridge=mock_l06_bridge)

        result = await service.get_cost_summary("tenant-1")

        assert "agent-1" in result.cost_by_agent
        assert result.cost_by_agent["agent-1"] == 0.15  # 0.10 + 0.05
        assert result.cost_by_agent["agent-2"] == 0.03

    @pytest.mark.asyncio
    async def test_get_cost_summary_projects_monthly(self, mock_l06_bridge):
        """Test that projected monthly cost is calculated."""
        mock_l06_bridge.query_metrics.return_value = [
            {
                "metric_name": "model_cost_dollars",
                "value": 30.0,  # $30 over 30 days
                "labels": {"model": "claude-3-opus", "agent_id": "agent-1"},
            },
        ]
        service = CostService(l06_bridge=mock_l06_bridge)

        result = await service.get_cost_summary("tenant-1")

        # 30 days of data, projected to 30 days = $30
        assert result.projected_monthly_cost == 30.0

    @pytest.mark.asyncio
    async def test_get_cost_summary_empty_metrics(self, mock_l06_bridge):
        """Test handling of no metrics data."""
        mock_l06_bridge.query_metrics.return_value = []
        service = CostService(l06_bridge=mock_l06_bridge)

        result = await service.get_cost_summary("tenant-1")

        assert result.total_cost_dollars == 0.0
        assert result.cost_by_model == {}
        assert result.cost_by_agent == {}
        assert result.projected_monthly_cost == 0.0

    @pytest.mark.asyncio
    async def test_get_cost_summary_l06_unavailable(self):
        """Test graceful degradation when L06 is unavailable."""
        service = CostService(l06_bridge=None)

        result = await service.get_cost_summary("tenant-1")

        # Should return zero costs, not raise
        assert result.total_cost_dollars == 0.0
        assert result.projected_monthly_cost == 0.0

    @pytest.mark.asyncio
    async def test_get_cost_summary_calculates_from_tokens(self, mock_l06_bridge):
        """Test cost calculation from token metrics when cost metrics unavailable."""
        # First call returns empty cost metrics, second returns token metrics
        mock_l06_bridge.query_metrics.side_effect = [
            [],  # No cost metrics
            [
                {
                    "metric_name": "model_tokens_used",
                    "value": 1000,  # 1000 tokens
                    # Use exact model name from our cost map
                    "labels": {"model": "claude-3-sonnet-20240229", "agent_id": "agent-1"},
                },
            ],
        ]
        service = CostService(l06_bridge=mock_l06_bridge)

        result = await service.get_cost_summary("tenant-1")

        # 1000 tokens at $0.003/1K = $0.003
        assert result.total_cost_dollars == pytest.approx(0.003, rel=0.01)


@pytest.mark.l10
class TestCostServiceAgentCost:
    """Tests for CostService.get_agent_cost()."""

    @pytest.mark.asyncio
    async def test_get_agent_cost_success(self, cost_service, mock_l06_bridge):
        """Test successful agent cost retrieval."""
        now = datetime.now(UTC)
        start = now - timedelta(days=7)

        result = await cost_service.get_agent_cost("agent-1", start, now)

        assert "agent_id" in result
        assert result["agent_id"] == "agent-1"
        assert "total_cost" in result
        assert "cost_by_model" in result

    @pytest.mark.asyncio
    async def test_get_agent_cost_time_range(self, mock_l06_bridge):
        """Test agent cost with specific time range."""
        now = datetime.now(UTC)
        start = now - timedelta(hours=24)
        service = CostService(l06_bridge=mock_l06_bridge)

        result = await service.get_agent_cost("agent-1", start, now)

        assert result["start"] == start.isoformat()
        assert result["end"] == now.isoformat()

    @pytest.mark.asyncio
    async def test_get_agent_cost_breakdown_by_model(self, mock_l06_bridge):
        """Test that agent cost includes model breakdown."""
        mock_l06_bridge.query_metrics.side_effect = [
            [
                {
                    "metric_name": "model_cost_dollars",
                    "value": 0.10,
                    "labels": {"model": "claude-3-opus", "agent_id": "agent-1"},
                },
                {
                    "metric_name": "model_cost_dollars",
                    "value": 0.05,
                    "labels": {"model": "claude-3-sonnet", "agent_id": "agent-1"},
                },
            ],
            [],  # Token metrics
        ]
        service = CostService(l06_bridge=mock_l06_bridge)
        now = datetime.now(UTC)

        result = await service.get_agent_cost("agent-1", now - timedelta(days=1), now)

        assert result["cost_by_model"]["claude-3-opus"] == 0.1
        assert result["cost_by_model"]["claude-3-sonnet"] == 0.05
        assert result["total_cost"] == 0.15

    @pytest.mark.asyncio
    async def test_get_agent_cost_l06_unavailable(self):
        """Test agent cost when L06 is unavailable."""
        service = CostService(l06_bridge=None)
        now = datetime.now(UTC)

        result = await service.get_agent_cost("agent-1", now - timedelta(days=1), now)

        assert result["total_cost"] == 0.0
        assert result["cost_by_model"] == {}

    @pytest.mark.asyncio
    async def test_get_agent_cost_includes_token_count(self, mock_l06_bridge):
        """Test that agent cost includes token usage."""
        mock_l06_bridge.query_metrics.side_effect = [
            [
                {
                    "metric_name": "model_cost_dollars",
                    "value": 0.10,
                    "labels": {"model": "claude-3-opus", "agent_id": "agent-1"},
                },
            ],
            [
                {
                    "metric_name": "model_tokens_used",
                    "value": 10000,
                    "labels": {"model": "claude-3-opus", "agent_id": "agent-1"},
                },
            ],
        ]
        service = CostService(l06_bridge=mock_l06_bridge)
        now = datetime.now(UTC)

        result = await service.get_agent_cost("agent-1", now - timedelta(days=1), now)

        assert result["tokens_used"] == 10000
        assert "tokens_by_model" in result


@pytest.mark.l10
class TestCostServiceTrend:
    """Tests for CostService.get_cost_trend()."""

    @pytest.mark.asyncio
    async def test_get_cost_trend_success(self, mock_l06_bridge):
        """Test successful cost trend retrieval."""
        mock_l06_bridge.query_metrics.return_value = [
            {"value": 1.0, "labels": {}},
        ]
        service = CostService(l06_bridge=mock_l06_bridge)

        result = await service.get_cost_trend("tenant-1", days=7)

        assert len(result) == 7
        assert all("date" in point and "cost" in point for point in result)

    @pytest.mark.asyncio
    async def test_get_cost_trend_l06_unavailable(self):
        """Test cost trend when L06 is unavailable."""
        service = CostService(l06_bridge=None)

        result = await service.get_cost_trend("tenant-1", days=7)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_cost_trend_ordered_by_date(self, mock_l06_bridge):
        """Test that trend is ordered oldest first."""
        mock_l06_bridge.query_metrics.return_value = [
            {"value": 1.0, "labels": {}},
        ]
        service = CostService(l06_bridge=mock_l06_bridge)

        result = await service.get_cost_trend("tenant-1", days=3)

        # Should be oldest to newest
        dates = [point["date"] for point in result]
        assert dates == sorted(dates)
