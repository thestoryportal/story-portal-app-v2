Implement L07 Learning Layer: Autonomous end-to-end sprint.

## CRITICAL ENVIRONMENT CONSTRAINTS

READ THESE FIRST - DO NOT VIOLATE:

1. DO NOT create docker-compose files - infrastructure ALREADY RUNNING
2. DO NOT create virtual environments (venv) - use system Python
3. DO NOT run docker-compose up - services ALREADY RUNNING
4. ALWAYS use: pip install <package> --break-system-packages
5. CORRECT directory: /Volumes/Extreme SSD/projects/story-portal-app/platform/src/L07_learning/

## Running Infrastructure (DO NOT RECREATE)

| Service | Host | Port | Container/Process |
|---------|------|------|-------------------|
| PostgreSQL | localhost | 5432 | agentic-postgres |
| Redis | localhost | 6379 | agentic-redis |
| Ollama | localhost | 11434 | PM2 managed |

Verify with: docker ps | grep agentic && pm2 status

## Specification

Location: /Volumes/Extreme SSD/projects/story-portal-app/platform/specs/learning-layer-specification-v1.2-final-ASCII.md

Read specification Sections 3 (Architecture) and 11 (Implementation Guide) first.

## Layer Purpose

The Learning Layer (L07) is the continuous improvement engine. It extracts training data from execution traces, manages model fine-tuning pipelines, implements RLHF feedback loops, and enables the system to improve autonomously based on quality signals from L06.

## Key Distinction

- L06 measures WHAT happened (quality scores)
- L07 determines WHY and HOW to make it better

## Completed Layers (Available for Integration)

| Layer | Location | Key Integration |
|-------|----------|-----------------|
| L01 Data Layer | MCP services | Event stream, artifact storage |
| L02 Agent Runtime | platform/src/L02_runtime/ | Execution traces source |
| L04 Model Gateway | platform/src/L04_model_gateway/ | Model deployment target |
| L05 Planning | platform/src/L05_planning/ | Planning traces source |
| L06 Evaluation | platform/src/L06_evaluation/ | Quality scores source |

## Output Location

/Volumes/Extreme SSD/projects/story-portal-app/platform/src/L07_learning/

## Directory Structure

Create these directories and files:

Root: platform/src/L07_learning/
  - __init__.py
  - PROGRESS.md
  - README.md

Subdirectory: platform/src/L07_learning/models/
  - __init__.py
  - training_example.py (TrainingExample, ExampleSource, ExampleLabel)
  - dataset.py (Dataset, DatasetVersion, DatasetSplit)
  - training_job.py (TrainingJob, JobStatus, JobConfig)
  - model_artifact.py (ModelArtifact, ModelVersion, ModelLineage)
  - reward_signal.py (RewardSignal, PreferencePair, RewardModel)
  - curriculum.py (CurriculumStage, DifficultyLevel, LearningPath)
  - pattern.py (BehavioralPattern, PlanningStrategy, PatternConfidence)
  - error_codes.py (E7000-E7999)

Subdirectory: platform/src/L07_learning/services/
  - __init__.py
  - training_data_extractor.py (Parse traces to training examples)
  - example_quality_filter.py (Score and filter examples)
  - dataset_curator.py (Version, split, manage datasets)
  - fine_tuning_engine.py (Orchestrate SFT with LoRA)
  - rlhf_engine.py (Reward model + PPO training)
  - model_registry.py (Version and manage model artifacts)
  - model_validator.py (Regression tests, benchmarks)
  - distillation_engine.py (Compress large models)
  - curriculum_planner.py (Order training by difficulty)
  - pattern_extractor.py (Extract behavioral patterns)
  - strategy_optimizer.py (Optimize planning strategies)
  - learning_service.py (Main orchestrator)

Subdirectory: platform/src/L07_learning/pipelines/
  - __init__.py
  - sft_pipeline.py (Supervised fine-tuning pipeline)
  - rlhf_pipeline.py (RLHF training pipeline)
  - distillation_pipeline.py (Knowledge distillation)
  - evaluation_pipeline.py (Model validation pipeline)

Subdirectory: platform/src/L07_learning/tests/
  - __init__.py
  - conftest.py
  - test_models.py
  - test_extractor.py
  - test_filter.py
  - test_curator.py
  - test_registry.py
  - test_integration.py

## Implementation Phases

Execute in order per spec Section 11:

### Phase 1: Foundation (Models and Data Extraction)

Create data models per spec Section 5.

TrainingExample fields:
  - example_id: str (UUID)
  - source_type: ExampleSource (EXECUTION_TRACE, PLANNING_TRACE, QUALITY_FEEDBACK)
  - input_text: str (model input)
  - output_text: str (expected output)
  - quality_score: float (0-100 from L06)
  - confidence: float (0-1)
  - metadata: dict (trace_id, agent_id, task_type, timestamp)
  - labels: list[str] (domain labels)

Dataset fields:
  - dataset_id: str (UUID)
  - name: str
  - version: str (semver)
  - examples: list[TrainingExample]
  - splits: dict[str, list[str]] (train/val/test -> example_ids)
  - statistics: DatasetStatistics
  - created_at: datetime
  - lineage: DatasetLineage

TrainingJob fields:
  - job_id: str (UUID)
  - job_type: JobType (SFT, RLHF, DISTILLATION)
  - status: JobStatus (PENDING, RUNNING, COMPLETED, FAILED)
  - config: JobConfig
  - dataset_id: str
  - base_model_id: str
  - output_model_id: str | None
  - metrics: dict (loss, accuracy, etc.)
  - started_at: datetime | None
  - completed_at: datetime | None

ModelArtifact fields:
  - model_id: str (UUID)
  - name: str
  - version: str (semver)
  - model_type: ModelType (BASE, FINE_TUNED, DISTILLED, LORA_ADAPTER)
  - artifact_path: str
  - parent_model_id: str | None
  - training_job_id: str | None
  - metrics: dict
  - signature: str (checksum)
  - created_at: datetime

Error codes E7000-E7999 per spec Appendix B.

### Phase 2: Training Data Extractor

Extract training examples from execution traces per spec Section 8.3.1:

Input sources:
  - L02 execution traces (task.completed events)
  - L05 planning traces (plan.created events)
  - L06 quality scores (evaluation.completed events)

Extractor responsibilities:
  - Parse CloudEvents into structured examples
  - Generate input-output pairs
  - Attach quality scores as labels
  - Validate trace completeness
  - Handle malformed traces gracefully

Interface:
  async def extract_from_event(event: CloudEvent) -> TrainingExample | None:
      # Parse event and create training example
      
  async def extract_batch(events: list[CloudEvent]) -> list[TrainingExample]:
      # Batch extraction with filtering

### Phase 3: Example Quality Filter

Filter and score examples per spec Section 8.3.2:

Filtering criteria:
  - Quality score >= minimum threshold (default 70)
  - Confidence >= minimum confidence (default 0.8)
  - Example completeness (no missing fields)
  - Not a duplicate
  - Not poisoned data (security check)

Interface:
  async def filter(examples: list[TrainingExample]) -> list[TrainingExample]:
      # Filter to high-quality subset
      
  async def score_example(example: TrainingExample) -> float:
      # Compute composite quality score

### Phase 4: Dataset Curator

Manage dataset versions per spec Section 8.3.3:

Responsibilities:
  - Create train/validation/test splits (80/10/10)
  - Handle class imbalance (stratified sampling)
  - Version datasets with metadata
  - Compute dataset statistics
  - Support incremental updates

Interface:
  async def create_dataset(
      name: str,
      examples: list[TrainingExample],
      split_ratios: dict[str, float] = {"train": 0.8, "val": 0.1, "test": 0.1}
  ) -> Dataset:
      # Create versioned dataset with splits
      
  async def add_examples(dataset_id: str, examples: list[TrainingExample]) -> Dataset:
      # Incremental update, creates new version

### Phase 5: Model Registry

Version and manage model artifacts per spec Section 8.3.5:

Responsibilities:
  - Store model artifacts with checksums
  - Track model lineage (parent models, training data)
  - Support model versioning (semver)
  - Enable model comparison
  - Manage model lifecycle (staging, production, archived)

Interface:
  async def register_model(artifact: ModelArtifact) -> str:
      # Register new model, return model_id
      
  async def get_model(model_id: str) -> ModelArtifact:
      # Retrieve model by ID
      
  async def list_models(
      model_type: ModelType | None = None,
      status: str | None = None
  ) -> list[ModelArtifact]:
      # List models with filters
      
  async def promote_model(model_id: str, stage: str) -> None:
      # Promote model to stage (staging, production)

Storage: PostgreSQL for metadata, local filesystem for artifacts (production would use S3/GCS).

### Phase 6: Fine-Tuning Engine (SFT)

Orchestrate supervised fine-tuning per spec Section 8.3.4:

For local development, implement a lightweight training simulation:
  - Load dataset
  - Simulate training loop
  - Track metrics (loss curves)
  - Generate model artifact

Production would use HuggingFace + LoRA adapters.

Interface:
  async def start_training(
      dataset_id: str,
      base_model_id: str,
      config: JobConfig
  ) -> TrainingJob:
      # Start fine-tuning job
      
  async def get_job_status(job_id: str) -> TrainingJob:
      # Get job status and metrics
      
  async def cancel_job(job_id: str) -> None:
      # Cancel running job

JobConfig fields (from spec):
  - learning_rate: float (default 2e-5)
  - batch_size: int (default 16)
  - epochs: int (default 3)
  - max_seq_length: int (default 2048)
  - lora_rank: int (default 16)
  - lora_alpha: float (default 32)

### Phase 7: RLHF Engine (Stub)

Implement RLHF pipeline stub per spec Section 8.3.5:

For local development, create interface with stub implementation:
  - Reward model training (stub)
  - PPO policy optimization (stub)
  - Quality signal integration

Interface:
  async def train_reward_model(
      preference_pairs: list[PreferencePair]
  ) -> RewardModel:
      # Train reward model from preferences (stub)
      
  async def optimize_policy(
      base_model_id: str,
      reward_model: RewardModel,
      config: RLHFConfig
  ) -> ModelArtifact:
      # PPO policy optimization (stub)

Note: Full RLHF requires significant GPU resources. Local dev uses simulation.

### Phase 8: Model Validator

Validate models before deployment per spec Section 8.3.8:

Validation stages:
  1. Regression tests (predefined test cases)
  2. Performance benchmarks (latency, throughput)
  3. A/B test simulation
  4. Safety checks

Interface:
  async def validate_model(
      model_id: str,
      baseline_model_id: str | None = None
  ) -> ValidationResult:
      # Run all validation stages
      
  async def run_regression_tests(model_id: str) -> TestResults:
      # Run regression test suite

ValidationResult fields:
  - passed: bool
  - stages: dict[str, StageResult]
  - regression_detected: bool
  - recommendation: str (DEPLOY, REVIEW, REJECT)

### Phase 9: Learning Service (Orchestrator)

Main service combining all components:

  class LearningService:
      def __init__(
          self,
          extractor: TrainingDataExtractor,
          filter: ExampleQualityFilter,
          curator: DatasetCurator,
          registry: ModelRegistry,
          sft_engine: FineTuningEngine,
          validator: ModelValidator
      ): ...
      
      async def process_event(self, event: CloudEvent) -> None:
          # Extract training example from event
          
      async def create_training_dataset(
          self,
          name: str,
          min_examples: int = 1000
      ) -> Dataset:
          # Create dataset from accumulated examples
          
      async def train_model(
          self,
          dataset_id: str,
          config: JobConfig | None = None
      ) -> TrainingJob:
          # Start training job
          
      async def deploy_model(self, model_id: str) -> None:
          # Validate and deploy model to L04

### Phase 10: Observability and Integration

Add metrics, logging, L04 integration:

Metrics:
  - l07_examples_extracted_total
  - l07_examples_filtered_total
  - l07_datasets_created_total
  - l07_training_jobs_total
  - l07_training_job_duration_seconds
  - l07_models_registered_total
  - l07_validation_pass_rate

L04 Integration for model deployment:
  from src.L04_model_gateway.services.model_registry import ModelRegistry as L04Registry
  
  async def deploy_to_gateway(model_artifact: ModelArtifact) -> None:
      # Register fine-tuned model with L04

## Error Code Range

L07 uses E7000-E7999:

| Range | Category |
|-------|----------|
| E7000-E7099 | Training data extraction |
| E7100-E7199 | Example filtering |
| E7200-E7299 | Model registry and deployment |
| E7300-E7399 | RLHF and reward modeling |
| E7400-E7499 | Monitoring and reliability |
| E7500-E7599 | Configuration |
| E7600-E7699 | Knowledge distillation |
| E7700-E7799 | Cost and resources |
| E7800-E7899 | Observability |
| E7900-E7999 | System and integration |

## Local Development Constraints

For local dev without GPU:
  - Fine-tuning: Simulate training loop, don't actually train
  - RLHF: Stub implementation only
  - Distillation: Stub implementation only
  - Model artifacts: Store metadata, not actual model weights

This allows testing the full pipeline flow without GPU resources.

## Test Configuration

Create tests/conftest.py with:
  - Event loop fixture
  - Cleanup timeout fixture (2 second max)
  - Mock CloudEvent fixture
  - Mock training example fixture
  - Mock model artifact fixture

## Validation After Each Phase

Run after each phase:
  cd /Volumes/Extreme SSD/projects/story-portal-app/platform
  python3 -m py_compile $(find src/L07_learning -name "*.py")
  python3 -c "from src.L07_learning import *; print('OK')"

## Progress Logging

After each phase append to PROGRESS.md:
  Phase [N] complete: [components] - [timestamp]

## Final Validation

After all phases:
  1. Syntax check all files
  2. Import check main service
  3. Run test suite with 30 second timeout
  4. Test end-to-end pipeline flow

Integration test:
  python3 << 'EOF'
  import asyncio
  import sys
  sys.path.insert(0, '.')
  
  async def test():
      from src.L07_learning.services.learning_service import LearningService
      from src.L07_learning.models.training_example import TrainingExample, ExampleSource
      
      service = LearningService()
      await service.initialize()
      
      # Create mock training example
      example = TrainingExample(
          example_id="test-1",
          source_type=ExampleSource.EXECUTION_TRACE,
          input_text="Summarize this document",
          output_text="The document discusses...",
          quality_score=85.0,
          confidence=0.9,
          metadata={"agent_id": "agent-1", "task_type": "summarization"}
      )
      
      # Test extraction and filtering
      filtered = await service.filter_examples([example])
      print(f"Filtered examples: {len(filtered)}")
      
      # Test dataset creation
      dataset = await service.create_training_dataset(
          name="test-dataset",
          examples=filtered
      )
      print(f"Dataset created: {dataset.dataset_id}")
      
      await service.cleanup()
  
  asyncio.run(test())
  EOF

## Completion Criteria

Sprint complete when:
  - All 10 phases implemented
  - All files pass syntax validation
  - All imports resolve
  - Tests exist for each component
  - Tests pass with no hangs
  - Pipeline flow works (extract -> filter -> curate -> train -> validate)
  - PROGRESS.md shows all phases complete

## Error Handling

If blocked:
  1. Log blocker to PROGRESS.md
  2. Stub the problematic component with TODO
  3. Continue to next phase
  4. Do not stop the sprint

## Final Steps

1. Create completion summary in PROGRESS.md
2. Stage files: git add platform/src/L07_learning/
3. Do NOT commit - await human review

## REMINDERS

- NO docker-compose
- NO venv
- Use --break-system-packages for pip
- Infrastructure ALREADY RUNNING
- Training is SIMULATED (no GPU required)
- RLHF and Distillation are STUBS
- Follow L02/L03/L04/L05/L06 patterns

## Begin

Read the specification. Execute all phases. Log progress. Complete end-to-end.