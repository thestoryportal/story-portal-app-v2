# AUD-020: LLM Model Inventory Report

## Executive Summary
**Status**: ✅ HEALTHY (P2-002 FIX VALIDATED)
**Models**: 6 models installed  
**Storage**: ~18GB total  
**Priority**: P3 (Medium) - Optimization opportunities

## Key Findings

### Model Inventory
1. **llava-llama3:latest** - 5.2GB (Vision + Language)
2. **llama3.1:8b** - 4.6GB (Latest language model)
3. **mistral:7b** - 4.1GB (Alternative LLM)
4. **llama3.2:latest** - 1.9GB (Lightweight LLM)
5. **llama3.2:1b** - 1.2GB (Tiny model)
6. **nomic-embed-text:latest** - 261MB (Embeddings)

### Sprint Fix Validation

#### P2-002: Duplicate llama3.2 Model Resolved ✅
**Status**: VALIDATED  
**Evidence**: Only ONE llama3.2:latest model exists (1.9GB)
- Previous duplicate removed
- llama3.2:1b is a separate tiny model (different variant)
- No storage waste from duplicates

### GPU Status
**Status**: CPU-only deployment  
**Impact**: Slower inference times but functional
- No NVIDIA GPU detected
- Running on CPU (acceptable for development)
- Consider GPU for production workloads

### Storage Optimization
**Total Storage**: ~18GB for all models
- Largest: llava-llama3 (5.2GB)
- Smallest: nomic-embed-text (261MB)
- All models recently used (within 10 days)

## Recommendations

### P3-003: Consider Model Pruning
**Priority**: P3 (Low)  
**Impact**: Reduced storage by ~5GB
**Action**: Evaluate if all 6 models are needed
- llama3.1:8b and mistral:7b are redundant
- Keep one primary LLM + embeddings + vision
- Archive unused models

### P4-002: GPU Acceleration Planning
**Priority**: P4 (Enhancement)  
**Action**: Plan GPU deployment for production
- NVIDIA GPU would improve inference 10-50x
- Consider cloud GPU instances
- Document GPU requirements

### P3-004: Model Version Management
**Priority**: P3 (Low)  
**Action**: Track model versions explicitly
- Document which services use which models
- Pin models to specific versions
- Create model usage matrix

## Health Score Impact
**LLM Infrastructure**: 88/100
- Deductions:
  - -7 for CPU-only deployment
  - -5 for potential model redundancy

## Evidence
- Model count: 6 models
- Duplicate removal: Verified
- Recent usage: All models accessed within 10 days
- Storage: 18GB total
