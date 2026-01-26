# AUD-020: LLM/Model Inventory Audit Report

**Audit Date:** 2026-01-18
**Agent:** AUD-020
**Category:** Infrastructure Discovery
**Status:** COMPLETE

## Executive Summary

Ollama is **OPERATIONAL** with 7 models installed totaling approximately **20.5GB** of storage. The platform has a diverse model portfolio spanning embeddings, general-purpose LLMs, and multimodal capabilities. Models are recent and actively maintained.

### Key Metrics
- **Total Models:** 7
- **Total Storage:** ~20.5GB
- **Model Types:** Text embedding (1), Text generation (5), Multimodal (1)
- **Ollama Status:** Running (inferred from successful API query)
- **GPU Acceleration:** Not available (CPU-only deployment)

## Detailed Findings

### Model Inventory

#### 1. nomic-embed-text:latest (274MB)
- **Type:** Embedding model
- **Size:** 274MB
- **Last Modified:** 2026-01-18 (TODAY - most recently updated)
- **Purpose:** Text embeddings for RAG, semantic search
- **Status:** ✅ Active and current

#### 2. mistral:7b (4.37GB)
- **Type:** Text generation (7B parameters)
- **Size:** 4.37GB
- **Last Modified:** 2026-01-18 (TODAY)
- **Purpose:** General-purpose instruction-following LLM
- **Status:** ✅ Active and current

#### 3. llama3.1:8b (4.92GB)
- **Type:** Text generation (8B parameters)
- **Size:** 4.92GB
- **Last Modified:** 2026-01-15 (3 days ago)
- **Purpose:** Latest Llama 3.1 instruction model
- **Status:** ✅ Recent

#### 4. llama3.2:latest (2.02GB)
- **Type:** Text generation (3B parameters)
- **Size:** 2.02GB
- **Last Modified:** 2026-01-15 (3 days ago)
- **Purpose:** Newer, more efficient Llama variant
- **Status:** ✅ Recent

#### 5. llama3.2:3b (2.02GB)
- **Type:** Text generation (3B parameters)
- **Size:** 2.02GB (duplicate of llama3.2:latest)
- **Last Modified:** 2026-01-14 (4 days ago)
- **Purpose:** Same as llama3.2:latest
- **Status:** ⚠️ Duplicate

#### 6. llama3.2:1b (1.32GB)
- **Type:** Text generation (1B parameters)
- **Size:** 1.32GB
- **Last Modified:** 2026-01-09 (9 days ago)
- **Purpose:** Lightweight model for fast inference
- **Status:** ✅ Recent

#### 7. llava-llama3:latest (5.55GB)
- **Type:** Multimodal (vision + language)
- **Size:** 5.55GB
- **Last Modified:** 2025-12-26 (23 days ago)
- **Purpose:** Image understanding and analysis
- **Status:** ⚠️ Slightly outdated

### Model Portfolio Analysis

**Strengths:**
- ✅ Diverse model sizes (1B to 8B parameters) for different use cases
- ✅ Embedding model present for RAG/semantic search
- ✅ Multimodal capability with LLaVA
- ✅ Recent Llama 3.1/3.2 models included
- ✅ Good balance of performance vs. efficiency

**Weaknesses:**
- ⚠️ Duplicate llama3.2 tags (latest and 3b appear identical)
- ⚠️ No larger models (13B+) for complex reasoning tasks
- ⚠️ No code-specialized models
- ⚠️ LLaVA model 3+ weeks old

### Ollama Service Status

**API Connectivity:** ✅ HEALTHY
- Successfully queried `/api/tags` endpoint
- Service responding to HTTP requests on port 11434

**Container Status:** ⚠️ AMBIGUOUS
- From AUD-019: `awesome_hypatia` (ollama container) is STOPPED
- Yet API is accessible, suggesting:
  - Ollama running as host service (not containerized), OR
  - Different Ollama container not tracked in Docker

### GPU Status: CPU-ONLY

**Finding:** No NVIDIA GPU detected
- **Impact:** Model inference running on CPU
- **Performance:** Slower inference speeds (seconds vs. milliseconds)
- **Suitability:** Acceptable for development, may be limiting for production

**CPU Performance Considerations:**
- 1B models: Fast enough for real-time (~1-2s latency)
- 3B-7B models: Moderate latency (~3-10s)
- 8B+ models: Slower inference (~10-30s+)

## Priority Findings

### P1 - CRITICAL
None

### P2 - HIGH
1. **Ollama Container Status Unclear**
   - API accessible but container stopped in Docker
   - Risk: Service management confusion
   - Action: Clarify Ollama deployment method (Docker vs. host service)

### P3 - MEDIUM
2. **Duplicate llama3.2 Models**
   - Both `llama3.2:latest` and `llama3.2:3b` identical (2.02GB)
   - Impact: 2GB wasted storage
   - Action: Remove duplicate tag

3. **No Code-Specialized Models**
   - Platform lacks CodeLlama or similar
   - Impact: Suboptimal for code generation tasks
   - Action: Consider adding codellama:13b or similar

4. **LLaVA Model Outdated**
   - 23 days since last update
   - Impact: May miss recent improvements
   - Action: Update to latest LLaVA variant

### P4 - LOW
5. **No GPU Acceleration**
   - CPU-only deployment
   - Impact: Slower inference
   - Action: Document performance expectations; consider GPU for production

6. **Missing Enterprise Models**
   - No larger models (13B+) for complex tasks
   - Action: Evaluate need based on use cases

## Recommendations

### Immediate Actions (Week 1)
1. Clarify Ollama deployment (Docker vs. host service)
2. Remove duplicate llama3.2:3b tag
3. Update LLaVA to latest version

### Short-term Actions (Week 2-4)
4. Add CodeLlama model if code generation is a use case
5. Document model selection strategy
6. Set up model update schedule
7. Benchmark inference performance on CPU

### Long-term Improvements (Month 2+)
8. Evaluate GPU acceleration needs based on usage metrics
9. Consider model quantization for faster inference
10. Implement model versioning/rollback strategy
11. Add model performance monitoring

## Health Score: 78/100

**Breakdown:**
- Model Coverage: 18/25 (good variety, missing code models)
- Model Currency: 20/25 (mostly recent, LLaVA outdated)
- Storage Efficiency: 15/20 (duplicate detected)
- Infrastructure: 15/20 (CPU-only, container status unclear)
- Documentation: 10/10 (API accessible, easy to query)

## Storage Utilization

| Model | Size (GB) | % of Total |
|-------|-----------|------------|
| llava-llama3 | 5.55 | 27.1% |
| llama3.1:8b | 4.92 | 24.0% |
| mistral:7b | 4.37 | 21.3% |
| llama3.2:latest | 2.02 | 9.9% |
| llama3.2:3b | 2.02 | 9.9% (DUPLICATE) |
| llama3.2:1b | 1.32 | 6.4% |
| nomic-embed-text | 0.27 | 1.3% |
| **TOTAL** | **20.47** | **100%** |

## Evidence Files
- Raw findings: `./audit/findings/AUD-020-llm.md`
- Model count: 7
- Total storage: ~20.5GB
- GPU status: None detected

## Conclusion

The LLM infrastructure is **functional and well-provisioned** with a good selection of models for various use cases. The model portfolio demonstrates thoughtful curation with attention to both capability and efficiency. Primary concerns are minor (duplicate model, outdated multimodal model) and easily remediated. CPU-only deployment is acceptable for development but should be monitored for performance under load.
