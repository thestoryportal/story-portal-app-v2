"""Pytest configuration and fixtures for L07 Learning Layer tests."""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from ..models.training_example import TrainingExample, ExampleSource, TaskType
from ..models.dataset import Dataset
from ..models.model_artifact import ModelArtifact, ModelType, ModelStage
from ..models.training_job import TrainingJob, JobType, JobStatus


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_execution_trace() -> Dict[str, Any]:
    """Sample execution trace for testing."""
    return {
        'trace_id': 'trace-001',
        'task_id': 'task-001',
        'agent_id': 'agent-001',
        'task_description': 'Book a flight from NYC to SF',
        'task_context': {'budget': 500, 'date': '2026-02-01'},
        'steps': [
            {
                'action_type': 'tool_call',
                'tool_name': 'search_flights',
                'parameters': {'from': 'NYC', 'to': 'SF'},
                'reasoning': 'Need to search for available flights'
            },
            {
                'action_type': 'tool_call',
                'tool_name': 'book_flight',
                'parameters': {'flight_id': 'FL123'},
                'reasoning': 'Selected best option within budget'
            }
        ],
        'final_answer': 'Booked flight FL123 from NYC to SF for $450',
        'output': 'Successfully booked flight',
        'domain': 'travel',
        'version': '1.0'
    }


@pytest.fixture
def sample_cloud_event(sample_execution_trace) -> Dict[str, Any]:
    """Sample CloudEvent for testing."""
    return {
        'type': 'execution.completed',
        'source': 'l02-runtime',
        'id': 'event-001',
        'time': datetime.utcnow().isoformat(),
        'data': {
            'execution_id': 'exec-001',
            'trace': sample_execution_trace,
            'quality_score': 85.0,
            'confidence': 0.9
        }
    }


@pytest.fixture
def sample_training_example() -> TrainingExample:
    """Sample training example for testing."""
    return TrainingExample(
        example_id='ex-001',
        execution_id='exec-001',
        task_id='task-001',
        agent_id='agent-001',
        source_type=ExampleSource.EXECUTION_TRACE,
        input_text='Book a flight from NYC to SF',
        input_structured={'budget': 500},
        output_text='Booked flight FL123',
        final_answer='Successfully booked flight',
        quality_score=85.0,
        confidence=0.9,
        difficulty=0.5,
        domain='travel',
        task_type=TaskType.MULTI_STEP
    )


@pytest.fixture
def sample_training_examples() -> List[TrainingExample]:
    """List of sample training examples."""
    examples = []
    for i in range(50):
        example = TrainingExample(
            example_id=f'ex-{i:03d}',
            execution_id=f'exec-{i:03d}',
            task_id=f'task-{i:03d}',
            source_type=ExampleSource.EXECUTION_TRACE,
            input_text=f'Test task {i}',
            output_text=f'Test output {i}',
            quality_score=70.0 + (i % 30),
            confidence=0.7 + (i % 3) * 0.1,
            difficulty=(i % 10) / 10.0,
            domain=['travel', 'coding', 'qa'][i % 3],
            task_type=[TaskType.SINGLE_STEP, TaskType.MULTI_STEP, TaskType.REASONING][i % 3]
        )
        examples.append(example)
    return examples


@pytest.fixture
def sample_dataset(sample_training_examples) -> Dataset:
    """Sample dataset for testing."""
    dataset = Dataset(
        name='test-dataset',
        version='1.0.0',
        description='Test dataset',
        example_ids=[ex.example_id for ex in sample_training_examples]
    )
    dataset.compute_statistics(sample_training_examples)
    return dataset


@pytest.fixture
def sample_model_artifact() -> ModelArtifact:
    """Sample model artifact for testing."""
    return ModelArtifact(
        model_id='model-001',
        name='test-model',
        version='1.0.0',
        model_type=ModelType.FINE_TUNED,
        stage=ModelStage.DEVELOPMENT,
        artifact_path='/tmp/test_model.pt',
        artifact_format='pytorch',
        description='Test model artifact'
    )


@pytest.fixture
def sample_training_job() -> TrainingJob:
    """Sample training job for testing."""
    return TrainingJob(
        job_id='job-001',
        job_name='test-training-job',
        job_type=JobType.SFT,
        status=JobStatus.PENDING,
        dataset_id='dataset-001',
        base_model_id='base-model-001'
    )


@pytest.fixture
async def cleanup_timeout():
    """Ensure cleanup completes within timeout."""
    yield
    # Wait max 2 seconds for cleanup
    await asyncio.sleep(0.1)
