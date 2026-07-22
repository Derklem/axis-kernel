# Memory Lattice Specification v2.0 (Authoritative)

## 1. Overview
The Memory Lattice is a unified, queryable knowledge graph connecting Axis Chronicle events, GPT-Memory shards, and Horizon entities. It serves as the primary long-term memory store for the Axis Sovereign System.

## 2. Core Schemas

### 2.1 Nodes
Nodes are immutable units of memory.
- **id**: `MEM-` + First 12 chars of `SHA256(content.summary + source.path + source.position)`.
- **schema**: `"2.0"`
- **kind**:
  - `chronicle_event`: From logs or timelines.
  - `gpt_shard`: From GPT interactions/markdown files.
  - `entity_record`: From Horizon Entities (Future integration).
  - `concept`: Abstract grouping (Future Phase).
  - `kernel_axiom`: Core truth (Future Phase).
- **content**:
  - `summary`: Always present. Text summary.
  - `raw`: Full content (for events/axioms). Null for GPT shards (v2.0 Rule).
- **tags**: Array of strings.
- **source**:
  - `system`: "Chronicle", "Mind", "GPT-Memory", etc.
  - `path`: File path.
  - `position`: Line number or index.
  - `timestamp`: ISO 8601.
- **links**:
  - `in`: Array of Source Node IDs.
  - `out`: Array of Target Node IDs.
- **confidence**: Float (0.0 - 1.0). Default 1.0.
- **created_at**: ISO 8601.

### 2.2 Edges
Edges represent directed relationships.
- **source**: Node ID.
- **target**: Node ID.
- **relation**:
  - `evolution_of`: Temporal sequence (e.g., log lines).
  - `mentions`: Entity reference (text match).
  - `part_of`: Logical grouping (Concept Glue).
  - `supports`/`contradicts`: Semantic relation.
- **weight**: Float (0.0 - 1.0).
- **created_at**: ISO 8601.

## 3. Ingestion Logic (Axis_Chronicle)

### 3.1 Registry Pattern
- Deduplication is handled via `Memory_Lattice_Registry.json`.
- Each source (File) stores a `last_hash` of its content.
- If hash matches, ingestion is skipped.

### 3.2 Granularity & Content Rules
- **GPT-Memory**:
  - **Granularity**: v2.0a Coarse Mode (One Node per File).
  - **Content**: Summary Only. Raw content is null to save space.
- **Log Files / Timelines**:
  - **Granularity**: One Node per Line/JSON Object.
  - **Content**: Full Raw + Summary.
  
### 3.3 Deterministic Edges
- **Temporal**: Log events create `evolution_of` edges to the immediately preceding event in the same ingest run.
- **Entity**: Node content is scanned against `Horizon_Entities.json`. Matches create `mentions` edges.
- **Concept Glue**: (Future Phase) Logic to group shards by shared tags.

## 4. File Structure
- `Memory_Lattice_Index.json`: Main Graph (Nodes + Edges).
- `Memory_Lattice_Nodes/`: Individual Node Fragments (JSON).
- `Memory_Lattice_Registry.json`: Ingestion State.
