"""Integration tests for L07 Learning Layer."""

import pytest
import asyncio
from typing import List, Dict, Any

from ..services.learning_service import LearningService
from ..models.training_example import TrainingExample


@pytest.mark.asyncio
async def test_learning_service_initialization():
    """Test learning service initialization."""
    service = LearningService()
    await service.initialize()

    assert service.initialized is True
    assert service.extractor is not None
    assert service.filter is not None
    assert service.curator is not None
    assert service.registry is not None
    assert service.fine_tuning_engine is not None
    assert service.validator is not None

    await service.cleanup()


@pytest.mark.asyncio
async def test_extract_and_filter_pipeline(sample_cloud_event):
    """Test extraction and filtering pipeline."""
    service = LearningService()
    await service.initialize()

    # Process single event
    example = await service.process_event(sample_cloud_event)

    assert example is not None
    assert example.quality_score == 85.0
    assert example.confidence == 0.9

    # Filter examples
    filtered = await service.filter_examples([example])

    assert len(filtered) == 1
    assert filtered[0].quality_score >= 70.0

    await service.cleanup()


@pytest.mark.asyncio
async def test_dataset_creation(sample_training_examples):
    """Test dataset creation."""
    service = LearningService()
    await service.initialize()

    dataset = await service.create_training_dataset(
        name='test-dataset',
        examples=sample_training_examples,
        description='Integration test dataset'
    )

    assert dataset is not None
    assert dataset.name == 'test-dataset'
    assert len(dataset.example_ids) == len(sample_training_examples)
    assert 'train' in dataset.splits
    assert 'validation' in dataset.splits
    assert 'test' in dataset.splits

    await service.cleanup()


@pytest.mark.asyncio
async def test_training_job(sample_training_examples):
    """Test training job creation and execution."""
    service = LearningService()
    await service.initialize()

    # Create dataset
    dataset = await service.create_training_dataset(
        name='training-test-dataset',
        examples=sample_training_examples
    )

    # Start training
    job = await service.train_model(
        dataset_id=dataset.dataset_id,
        base_model_id='test-base-model'
    )

    assert job is not None
    assert job.dataset_id == dataset.dataset_id

    # Wait for completion (simulated training is fast)
    max_wait = 10  # seconds
    waited = 0
    while not job.is_terminal() and waited < max_wait:
        await asyncio.sleep(0.5)
        waited += 0.5
        job = await service.fine_tuning_engine.get_job_status(job.job_id)

    assert job.is_terminal()
    assert job.status.value == 'completed'
    assert job.output_model_id is not None

    await service.cleanup()


@pytest.mark.asyncio
async def test_model_validation(sample_training_examples):
    """Test model validation."""
    service = LearningService()
    await service.initialize()

    # Create dataset and train model
    dataset = await service.create_training_dataset(
        name='validation-test-dataset',
        examples=sample_training_examples
    )

    job = await service.train_model(
        dataset_id=dataset.dataset_id
    )

    # Wait for completion
    max_wait = 10
    waited = 0
    while not job.is_terminal() and waited < max_wait:
        await asyncio.sleep(0.5)
        waited += 0.5
        job = await service.fine_tuning_engine.get_job_status(job.job_id)

    assert job.output_model_id is not None

    # Validate model
    validation_result = await service.validate_model(job.output_model_id)

    assert validation_result is not None
    assert validation_result.model_id == job.output_model_id
    assert validation_result.recommendation in ['DEPLOY', 'REVIEW', 'REJECT']
    assert len(validation_result.stages) > 0

    await service.cleanup()


@pytest.mark.asyncio
async def test_end_to_end_pipeline(sample_cloud_event):
    """Test complete end-to-end pipeline."""
    service = LearningService()
    await service.initialize()

    # Create multiple events
    events = []
    for i in range(20):
        event = {
            'type': 'execution.completed',
            'source': 'l02-runtime',
            'id': f'event-{i:03d}',
            'data': {
                'execution_id': f'exec-{i:03d}',
                'trace': sample_cloud_event['data']['trace'].copy(),
                'quality_score': 70.0 + (i % 30),
                'confidence': 0.7 + (i % 3) * 0.1
            }
        }
        event['data']['trace']['task_id'] = f'task-{i:03d}'
        events.append(event)

    # Run pipeline
    result = await service.end_to_end_pipeline(
        events=events,
        dataset_name='e2e-test-dataset',
        base_model_id='test-base-model'
    )

    assert result['status'] == 'success'
    assert result['examples_extracted'] > 0
    assert result['dataset_id'] is not None
    assert result['model_id'] is not None
    assert 'validation_passed' in result

    await service.cleanup()


@pytest.mark.asyncio
async def test_statistics_gathering():
    """Test statistics gathering from all components."""
    service = LearningService()
    await service.initialize()

    stats = service.get_statistics()

    assert 'learning_service' in stats
    assert 'extractor' in stats
    assert 'filter' in stats
    assert 'curator' in stats
    assert 'registry' in stats
    assert 'fine_tuning' in stats
    assert 'validator' in stats

    await service.cleanup()
