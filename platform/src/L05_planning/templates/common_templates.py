"""
L05 Planning Layer - Common Templates.

Predefined decomposition templates for common goal patterns.
"""

from typing import List
from .template_registry import GoalTemplate


class CommonTemplates:
    """Collection of common goal decomposition templates."""

    @staticmethod
    def get_all_templates() -> List[GoalTemplate]:
        """Get all common templates."""
        return [
            CommonTemplates.file_processing_template(),
            CommonTemplates.data_pipeline_template(),
            CommonTemplates.report_generation_template(),
            CommonTemplates.simple_query_template(),
        ]

    @staticmethod
    def file_processing_template() -> GoalTemplate:
        """Template for file processing goals."""
        return GoalTemplate(
            template_id="file-processing-v1",
            name="File Processing",
            description="Process one or more files with transformations",
            patterns=[
                r"process\s+(?P<file_type>\w+)\s+files?",
                r"transform\s+(?P<file_type>\w+)\s+data",
                r"convert\s+(?P<source_format>\w+)\s+to\s+(?P<target_format>\w+)",
            ],
            task_templates=[
                {
                    "id": "read_files",
                    "name": "Read input files",
                    "description": "Read {{file_type}} files from source",
                    "type": "tool_call",
                    "tool_name": "file_reader",
                    "inputs": {"file_type": "{{file_type}}"},
                    "timeout_seconds": 60,
                    "dependencies": [],
                },
                {
                    "id": "process_data",
                    "name": "Process data",
                    "description": "Transform data according to requirements",
                    "type": "atomic",
                    "inputs": {},
                    "timeout_seconds": 300,
                    "dependencies": [{"task_id": "read_files", "type": "data", "output_key": "data"}],
                },
                {
                    "id": "write_output",
                    "name": "Write output",
                    "description": "Write processed data to output",
                    "type": "tool_call",
                    "tool_name": "file_writer",
                    "inputs": {},
                    "timeout_seconds": 60,
                    "dependencies": [{"task_id": "process_data", "type": "data", "output_key": "result"}],
                },
            ],
            metadata={"category": "data_processing", "complexity": "low"},
        )

    @staticmethod
    def data_pipeline_template() -> GoalTemplate:
        """Template for data pipeline goals."""
        return GoalTemplate(
            template_id="data-pipeline-v1",
            name="Data Pipeline",
            description="Extract, transform, and load data",
            patterns=[
                r"create\s+(?:a\s+)?(?:data\s+)?pipeline",
                r"etl\s+process",
                r"extract.*transform.*load",
            ],
            task_templates=[
                {
                    "id": "extract",
                    "name": "Extract data",
                    "description": "Extract data from source",
                    "type": "atomic",
                    "inputs": {},
                    "timeout_seconds": 120,
                    "dependencies": [],
                },
                {
                    "id": "transform",
                    "name": "Transform data",
                    "description": "Transform extracted data",
                    "type": "atomic",
                    "inputs": {},
                    "timeout_seconds": 300,
                    "dependencies": [{"task_id": "extract", "type": "data", "output_key": "data"}],
                },
                {
                    "id": "load",
                    "name": "Load data",
                    "description": "Load transformed data to destination",
                    "type": "atomic",
                    "inputs": {},
                    "timeout_seconds": 120,
                    "dependencies": [{"task_id": "transform", "type": "data", "output_key": "data"}],
                },
                {
                    "id": "validate",
                    "name": "Validate pipeline",
                    "description": "Validate pipeline execution and data quality",
                    "type": "atomic",
                    "inputs": {},
                    "timeout_seconds": 60,
                    "dependencies": [{"task_id": "load", "type": "blocking"}],
                },
            ],
            metadata={"category": "data_engineering", "complexity": "medium"},
        )

    @staticmethod
    def report_generation_template() -> GoalTemplate:
        """Template for report generation goals."""
        return GoalTemplate(
            template_id="report-generation-v1",
            name="Report Generation",
            description="Generate reports from data",
            patterns=[
                r"generate\s+(?:a\s+)?report",
                r"create\s+(?:a\s+)?summary",
                r"analyze.*(?:and\s+)?report",
            ],
            task_templates=[
                {
                    "id": "collect_data",
                    "name": "Collect data",
                    "description": "Collect data for report",
                    "type": "atomic",
                    "inputs": {},
                    "timeout_seconds": 120,
                    "dependencies": [],
                },
                {
                    "id": "analyze",
                    "name": "Analyze data",
                    "description": "Perform analysis on collected data",
                    "type": "llm_call",
                    "llm_prompt": "Analyze the following data and generate insights",
                    "inputs": {},
                    "timeout_seconds": 180,
                    "dependencies": [{"task_id": "collect_data", "type": "data", "output_key": "data"}],
                },
                {
                    "id": "format_report",
                    "name": "Format report",
                    "description": "Format analysis into report",
                    "type": "atomic",
                    "inputs": {},
                    "timeout_seconds": 60,
                    "dependencies": [{"task_id": "analyze", "type": "data", "output_key": "insights"}],
                },
            ],
            metadata={"category": "reporting", "complexity": "medium"},
        )

    @staticmethod
    def simple_query_template() -> GoalTemplate:
        """Template for simple query/lookup goals."""
        return GoalTemplate(
            template_id="simple-query-v1",
            name="Simple Query",
            description="Simple lookup or query operation",
            patterns=[
                r"(?:what|where|when|who|how)\s+(?:is|are|was|were)",
                r"find\s+(?:the\s+)?(?P<entity>\w+)",
                r"look\s+up\s+(?P<entity>\w+)",
                r"get\s+(?:the\s+)?(?P<entity>\w+)",
            ],
            task_templates=[
                {
                    "id": "query",
                    "name": "Execute query",
                    "description": "Execute query to find {{entity}}",
                    "type": "llm_call",
                    "llm_prompt": "Answer the following question: {{goal}}",
                    "inputs": {},
                    "timeout_seconds": 60,
                    "dependencies": [],
                },
            ],
            metadata={"category": "query", "complexity": "low"},
        )
