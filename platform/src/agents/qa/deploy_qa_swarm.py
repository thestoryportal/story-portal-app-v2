#!/usr/bin/env python3
"""Deploy QA Agent Swarm and execute platform testing."""

import json
import logging
import time
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

from qa_orchestrator import qa_orchestrator
from api_tester import api_tester
from integration_tester import integration_tester
from data_validator import data_validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QASwarmDeployer:
    """Deploys and manages the QA agent swarm."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.deployed_agents: Dict[str, str] = {}  # name -> agent_id
        self.test_results: List[Dict[str, Any]] = []
        self.start_time = datetime.utcnow()

    def check_platform_health(self) -> Dict[str, bool]:
        """Check health of all platform services."""
        services = {
            "L09 API Gateway (8000)": f"{self.base_url}/health/live",
            "L01 Data Layer (8001)": "http://localhost:8001/health/live",
            "L05 Orchestration (8006)": "http://localhost:8006/health/live",
        }

        health_status = {}
        for name, url in services.items():
            try:
                response = requests.get(url, timeout=2)
                health_status[name] = response.status_code == 200
            except requests.RequestException:
                health_status[name] = False

        return health_status

    def deploy_agent(self, agent_config) -> Optional[str]:
        """Deploy a single QA agent."""
        payload = agent_config.to_api_payload()
        logger.info(f"=== Deploying {payload['name']} ===")
        logger.info(f"Agent Type: {payload['agent_type']}")
        logger.info(f"Capabilities: {', '.join(payload['capabilities'][:3])}...")

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/agents",
                json=payload,
                timeout=10
            )

            if response.status_code == 201:
                agent_id = response.json().get("agent_id")
                logger.info(f"✓ Agent deployed successfully: {agent_id}")
                self.deployed_agents[payload['name']] = agent_id
                return agent_id
            else:
                logger.error(f"✗ Deployment failed: {response.status_code}")
                logger.error(f"  Response: {response.text}")
                return None

        except requests.RequestException as e:
            logger.error(f"✗ Deployment error: {e}")
            return None

    def submit_goal(self, agent_id: str, goal_config: Dict[str, Any]) -> Optional[str]:
        """Submit a goal to an agent."""
        goal_config["agent_id"] = agent_id

        try:
            response = requests.post(
                f"{self.base_url}/api/v1/goals",
                json=goal_config,
                timeout=10
            )

            if response.status_code == 201:
                goal_id = response.json().get("goal_id")
                logger.info(f"✓ Goal submitted: {goal_id}")
                return goal_id
            else:
                logger.error(f"✗ Goal submission failed: {response.status_code}")
                return None

        except requests.RequestException as e:
            logger.error(f"✗ Goal submission error: {e}")
            return None

    def monitor_goal(self, goal_id: str, timeout_seconds: int = 300) -> Dict[str, Any]:
        """Monitor goal execution until completion or timeout."""
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            try:
                response = requests.get(
                    f"{self.base_url}/api/v1/goals/{goal_id}",
                    timeout=5
                )

                if response.status_code == 200:
                    goal_data = response.json()
                    status = goal_data.get("status")

                    if status in ["completed", "failed", "cancelled"]:
                        return goal_data

                    logger.info(f"  Goal status: {status}")

            except requests.RequestException as e:
                logger.warning(f"  Monitoring error: {e}")

            time.sleep(5)

        return {"status": "timeout", "message": "Goal did not complete within timeout"}

    def run_deployment(self) -> Dict[str, Any]:
        """Execute full QA swarm deployment."""
        logger.info("=" * 70)
        logger.info("QA AGENT SWARM DEPLOYMENT")
        logger.info("=" * 70)

        # Check platform health
        logger.info("--- Platform Health Check ---")
        health = self.check_platform_health()
        for service, is_healthy in health.items():
            status = "✓ UP" if is_healthy else "✗ DOWN"
            logger.info(f"{service}: {status}")

        if not all(health.values()):
            logger.warning("⚠ Warning: Some services are down. Continuing anyway...")

        # Deploy agents
        logger.info("--- Agent Deployment Phase ---")
        agents_to_deploy = [
            qa_orchestrator,
            api_tester,
            integration_tester,
            data_validator
        ]

        for agent_config in agents_to_deploy:
            agent_id = self.deploy_agent(agent_config)
            if agent_id:
                time.sleep(1)  # Brief pause between deployments

        # Submit orchestrator goal
        if "qa-orchestrator" in self.deployed_agents:
            logger.info("--- Goal Submission Phase ---")
            orchestrator_id = self.deployed_agents["qa-orchestrator"]
            campaign = qa_orchestrator.create_test_campaign()
            goal_id = self.submit_goal(orchestrator_id, campaign)

            if goal_id:
                logger.info(f"--- Monitoring Execution (Goal: {goal_id}) ---")
                result = self.monitor_goal(goal_id, timeout_seconds=600)
                self.test_results.append(result)

        # Generate summary
        return self.generate_summary()

    def generate_summary(self) -> Dict[str, Any]:
        """Generate deployment and execution summary."""
        duration = (datetime.utcnow() - self.start_time).total_seconds()

        summary = {
            "deployment_time": self.start_time.isoformat(),
            "duration_seconds": duration,
            "agents_deployed": len(self.deployed_agents),
            "agent_ids": self.deployed_agents,
            "goals_executed": len(self.test_results),
            "test_results": self.test_results,
            "status": "completed" if self.test_results else "partial"
        }

        logger.info("=" * 70)
        logger.info("DEPLOYMENT SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Duration: {duration:.1f}s")
        logger.info(f"Agents Deployed: {len(self.deployed_agents)}")
        logger.info(f"Goals Executed: {len(self.test_results)}")

        if self.deployed_agents:
            logger.info("Deployed Agents:")
            for name, agent_id in self.deployed_agents.items():
                logger.info(f"  - {name}: {agent_id}")

        return summary


def main():
    """Main execution function."""
    # Try multiple possible API gateway URLs
    possible_urls = [
        "http://localhost:8000",
        "http://localhost:8001",
        "http://localhost:8006"
    ]

    deployer = None
    for url in possible_urls:
        try:
            response = requests.get(f"{url}/health/live", timeout=2)
            if response.status_code == 200:
                logger.info(f"Found active API at: {url}")
                deployer = QASwarmDeployer(base_url=url)
                break
        except requests.RequestException:
            continue

    if not deployer:
        logger.warning("⚠ No active API gateway found on standard ports")
        logger.info("Attempting deployment on default port 8000...")
        deployer = QASwarmDeployer()

    # Run deployment
    summary = deployer.run_deployment()

    # Save summary
    with open("qa_deployment_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    logger.info("Summary saved to: qa_deployment_summary.json")

    return 0 if summary["status"] == "completed" else 1


if __name__ == "__main__":
    exit(main())
