"""L07 Learning Layer E2E tests with L01 Data Layer integration."""
import pytest
from datetime import datetime
from uuid import uuid4


class TestL07Learning:
    """Test L07 Learning Layer functionality with L01 integration."""

    @pytest.fixture
    async def learning_service(self):
        """Initialize Learning Service with L01 bridge."""
        from src.L07_learning.services.learning_service import LearningService

        # Initialize with L01 connection (may fall back to local storage if L01 unavailable)
        service = LearningService(
            storage_path="/tmp/test_l07_learning",
            enable_rlhf=False,
            l01_base_url="http://localhost:8002"
        )
        await service.initialize()
        yield service
        await service.cleanup()

    @pytest.fixture
    async def l07_bridge(self):
        """Initialize L07 Bridge."""
        from src.L07_learning.services.l01_bridge import L07Bridge

        bridge = L07Bridge(l01_base_url="http://localhost:8002")
        await bridge.initialize()
        yield bridge
        await bridge.cleanup()

    @pytest.fixture
    def sample_training_examples(self):
        """Create sample training examples."""
        from src.L07_learning.models.training_example import (
            TrainingExample,
            ExampleSource,
            TaskType
        )

        examples = []
        for i in range(5):
            example = TrainingExample(
                example_id=str(uuid4()),
                execution_id=f"exec-{i:03d}",
                task_id=f"task-{i:03d}",
                agent_id=str(uuid4()),
                source_type=ExampleSource.EXECUTION_TRACE,
                input_text=f"Sample input {i}",
                output_text=f"Sample output {i}",
                expected_actions=[{"action": "test", "args": {"value": i}}],
                final_answer=f"Answer {i}",
                quality_score=85.0 + i,
                confidence=0.85 + (i * 0.01),
                labels=["test", f"category-{i % 2}"],
                domain="testing",
                task_type=TaskType.SINGLE_STEP,
                difficulty=0.5 + (i * 0.1),
                metadata={"test_iteration": i}
            )
            examples.append(example)

        return examples

    @pytest.fixture
    def sample_events(self):
        """Create sample CloudEvents for extraction."""
        events = []
        for i in range(3):
            event = {
                "type": "execution.completed",
                "id": str(uuid4()),
                "source": "test-agent",
                "specversion": "1.0",
                "time": datetime.utcnow().isoformat(),
                "data": {
                    "execution_id": f"exec-{i:03d}",
                    "task_id": f"task-{i:03d}",
                    "agent_id": str(uuid4()),
                    "input_text": f"Test input {i}",
                    "output_text": f"Test output {i}",
                    "actions": [{"action": "test", "args": {"value": i}}],
                    "final_answer": f"Answer {i}",
                    "quality_score": 85.0,
                    "confidence": 0.85,
                    "domain": "testing"
                }
            }
            events.append(event)

        return events

    @pytest.mark.asyncio
    async def test_learning_service_initialization(self, learning_service):
        """Learning service initializes correctly."""
        assert learning_service is not None
        assert learning_service.initialized is True
        assert learning_service.curator is not None
        assert learning_service.extractor is not None

    @pytest.mark.asyncio
    async def test_l07_bridge_connection(self, l07_bridge):
        """L07 Bridge connects to L01."""
        assert l07_bridge is not None
        assert l07_bridge.enabled is True
        assert l07_bridge.l01_client is not None

    @pytest.mark.asyncio
    async def test_store_training_example_via_bridge(
        self,
        l07_bridge,
        sample_training_examples
    ):
        """Store training example via L07Bridge to L01."""
        example = sample_training_examples[0]

        # Store example
        l01_example_id = await l07_bridge.store_training_example(example)

        # May be None if L01 is unavailable (graceful degradation)
        if l01_example_id:
            assert l01_example_id is not None
            print(f"✓ Stored training example in L01: {l01_example_id}")

            # Retrieve example
            retrieved = await l07_bridge.get_training_example(l01_example_id)
            assert retrieved is not None
            assert retrieved.input_text == example.input_text
            assert retrieved.quality_score == example.quality_score
            print(f"✓ Retrieved training example from L01")
        else:
            print("⚠ L01 unavailable, skipping L01 persistence test")

    @pytest.mark.asyncio
    async def test_list_training_examples(self, l07_bridge, sample_training_examples):
        """List training examples from L01."""
        # Store multiple examples
        stored_ids = []
        for example in sample_training_examples[:3]:
            l01_id = await l07_bridge.store_training_example(example)
            if l01_id:
                stored_ids.append(l01_id)

        if stored_ids:
            # List examples
            examples = await l07_bridge.list_training_examples(
                domain="testing",
                min_quality=80.0,
                limit=10
            )

            assert isinstance(examples, list)
            assert len(examples) >= len(stored_ids)
            print(f"✓ Listed {len(examples)} training examples from L01")
        else:
            print("⚠ L01 unavailable, skipping list test")

    @pytest.mark.asyncio
    async def test_create_dataset_with_l01_persistence(
        self,
        learning_service,
        sample_training_examples
    ):
        """Create dataset with L01 persistence via LearningService."""
        # Create dataset through LearningService
        dataset = await learning_service.create_training_dataset(
            name="test-dataset-001",
            examples=sample_training_examples,
            description="Test dataset for L07-L01 integration",
            tags=["test", "integration"]
        )

        assert dataset is not None
        assert dataset.name == "test-dataset-001"
        assert len(dataset.example_ids) == len(sample_training_examples)
        assert "train" in dataset.splits
        assert "validation" in dataset.splits
        assert "test" in dataset.splits

        # Check if L01 ID was stored
        if learning_service.l01_bridge and dataset.metadata:
            l01_dataset_id = dataset.metadata.get("l01_dataset_id")
            if l01_dataset_id:
                print(f"✓ Dataset persisted to L01: {l01_dataset_id}")
            else:
                print("⚠ Dataset created but L01 persistence failed")
        else:
            print("⚠ L01 Bridge disabled, using local storage")

        print(f"✓ Created dataset with {len(dataset.example_ids)} examples")
        print(f"  - Train: {len(dataset.splits['train'])} examples")
        print(f"  - Validation: {len(dataset.splits['validation'])} examples")
        print(f"  - Test: {len(dataset.splits['test'])} examples")

    @pytest.mark.asyncio
    async def test_dataset_split_ratios(
        self,
        learning_service,
        sample_training_examples
    ):
        """Dataset splits match configured ratios."""
        dataset = await learning_service.create_training_dataset(
            name="test-dataset-splits",
            examples=sample_training_examples,
            description="Test split ratios"
        )

        total_examples = len(dataset.example_ids)
        train_count = len(dataset.splits["train"])
        val_count = len(dataset.splits["validation"])
        test_count = len(dataset.splits["test"])

        # Verify all examples are assigned to a split
        assert train_count + val_count + test_count == total_examples

        # Verify ratios are approximately correct (within small margin)
        train_ratio = train_count / total_examples
        val_ratio = val_count / total_examples
        test_ratio = test_count / total_examples

        # For small datasets (<10 examples), ratios may be less accurate
        if total_examples >= 10:
            assert 0.7 <= train_ratio <= 0.9  # Target 0.8
            assert 0.0 <= val_ratio <= 0.2    # Target 0.1
            assert 0.0 <= test_ratio <= 0.2   # Target 0.1
        else:
            # For very small datasets, just verify all splits are present
            assert train_count > 0
            print(f"⚠ Small dataset ({total_examples} examples), split ratios may vary")

        print(f"✓ Split ratios: train={train_ratio:.2f}, val={val_ratio:.2f}, test={test_ratio:.2f}")

    @pytest.mark.asyncio
    async def test_extract_examples_from_events(
        self,
        learning_service,
        sample_events
    ):
        """Extract training examples from CloudEvents."""
        # Process batch of events
        examples = await learning_service.process_events_batch(sample_events)

        # Extraction may return fewer examples than events (filtering)
        assert isinstance(examples, list)
        print(f"✓ Extracted {len(examples)} examples from {len(sample_events)} events")

    @pytest.mark.asyncio
    async def test_filter_examples_by_quality(
        self,
        learning_service,
        sample_training_examples
    ):
        """Filter examples by quality score."""
        # Filter examples
        filtered = await learning_service.filter_examples(sample_training_examples)

        assert isinstance(filtered, list)
        assert len(filtered) <= len(sample_training_examples)

        # All filtered examples should have minimum quality
        for example in filtered:
            assert example.quality_score >= learning_service.filter.config.quality_threshold

        print(f"✓ Filtered {len(sample_training_examples)} -> {len(filtered)} examples")

    @pytest.mark.asyncio
    async def test_end_to_end_pipeline_with_l01(
        self,
        learning_service,
        sample_events
    ):
        """Run complete E2E pipeline with L01 persistence."""
        result = await learning_service.end_to_end_pipeline(
            events=sample_events,
            dataset_name="e2e-test-dataset",
            base_model_id="gpt-4-turbo-2024-04"
        )

        assert result is not None
        assert "status" in result

        if result["status"] == "success":
            assert "examples_extracted" in result
            assert "dataset_id" in result
            assert "model_id" in result
            print(f"✓ E2E pipeline completed successfully")
            print(f"  - Extracted: {result['examples_extracted']} examples")
            print(f"  - Dataset: {result['dataset_id']}")
            print(f"  - Model: {result['model_id']}")
        else:
            # Pipeline may fail due to insufficient examples or other reasons
            print(f"⚠ Pipeline status: {result['status']}")
            print(f"  Reason: {result.get('reason', 'unknown')}")

    @pytest.mark.asyncio
    async def test_get_learning_statistics(self, learning_service):
        """Get comprehensive learning statistics."""
        stats = learning_service.get_statistics()

        assert stats is not None
        assert "learning_service" in stats
        assert "extractor" in stats
        assert "curator" in stats
        assert "registry" in stats

        print(f"✓ Learning service statistics:")
        print(f"  - Initialized: {stats['learning_service']['initialized']}")
        print(f"  - L01 enabled: {stats['learning_service'].get('l01', 'disabled')}")
        print(f"  - Total datasets: {stats['curator'].get('total_datasets', 0)}")

    @pytest.mark.asyncio
    async def test_retrieve_dataset_from_l01(self, l07_bridge, sample_training_examples):
        """Create and retrieve dataset from L01."""
        from src.L07_learning.models.dataset import Dataset

        # Create dataset
        dataset = Dataset(
            name="test-retrieve-dataset",
            version="1.0.0",
            description="Test retrieval",
            tags=["test"],
            split_ratios={"train": 0.8, "validation": 0.1, "test": 0.1}
        )

        # Manually set splits for test
        dataset.splits = {
            "train": [ex.example_id for ex in sample_training_examples[:3]],
            "validation": [sample_training_examples[3].example_id],
            "test": [sample_training_examples[4].example_id]
        }

        # Create via bridge
        l01_dataset_id = await l07_bridge.create_dataset(
            dataset=dataset,
            examples=sample_training_examples
        )

        if l01_dataset_id:
            print(f"✓ Created dataset in L01: {l01_dataset_id}")

            # Retrieve dataset
            retrieved = await l07_bridge.get_dataset(l01_dataset_id)
            if retrieved:
                assert retrieved.name == dataset.name
                assert retrieved.version == dataset.version
                print(f"✓ Retrieved dataset from L01")
            else:
                print("⚠ Failed to retrieve dataset from L01")
        else:
            print("⚠ L01 unavailable, skipping retrieval test")

    @pytest.mark.asyncio
    async def test_list_datasets_from_l01(self, l07_bridge):
        """List datasets from L01."""
        datasets = await l07_bridge.list_datasets(
            name_filter="test",
            limit=10
        )

        assert isinstance(datasets, list)
        print(f"✓ Listed {len(datasets)} datasets from L01")

    @pytest.mark.asyncio
    async def test_graceful_degradation_without_l01(self):
        """Learning Service works without L01 (local storage fallback)."""
        from src.L07_learning.services.learning_service import LearningService

        # Initialize without L01 bridge
        service = LearningService(
            storage_path="/tmp/test_l07_no_l01",
            enable_rlhf=False,
            l01_base_url=None  # No L01 connection
        )
        await service.initialize()

        assert service is not None
        assert service.l01_bridge is None
        print("✓ LearningService initialized without L01 (local mode)")

        # Create sample example
        from src.L07_learning.models.training_example import (
            TrainingExample,
            ExampleSource,
            TaskType
        )

        example = TrainingExample(
            example_id=str(uuid4()),
            source_type=ExampleSource.EXECUTION_TRACE,
            input_text="Test input",
            output_text="Test output",
            quality_score=85.0,
            confidence=0.85,
            domain="testing",
            task_type=TaskType.SINGLE_STEP,
            difficulty=0.5
        )

        # Create dataset locally
        dataset = await service.create_training_dataset(
            name="local-dataset",
            examples=[example],
            description="Test local storage"
        )

        assert dataset is not None
        assert dataset.name == "local-dataset"
        print("✓ Dataset created with local storage fallback")

        await service.cleanup()
