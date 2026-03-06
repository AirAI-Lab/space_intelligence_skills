# OpenClaw Sub-Agent Examples
## Practical Examples for Common Tasks

### Example 1: Code Analysis (Large Codebase)

**Without Sub-Agent** (Consumes 50K+ tokens):
```
User: Analyze the entire backend API for security issues

Agent: [Runs read on 50+ files, exec security tools, stores all results in main context]
```

**With Sub-Agent** (Consumes ~1K tokens in main context):
```
User: Analyze the entire backend API for security issues

Agent: I'll spawn a sub-agent to handle this comprehensive analysis.

[sessions_spawn tool called with task]
→ Sub-agent runs in isolated context
→ Reads all files, runs security scans
→ Only final report is announced back

[Result: Clean security report delivered to user]
```

### Example 2: Paper Revision (Multi-Step Process)

**Without Sub-Agent**:
```
User: Help revise our paper with Humanizer integration

Agent: [Reads paper, configures Humanizer, runs analysis, makes edits - all in main context]
→ Context grows by 100K+ tokens
```

**With Sub-Agent**:
```
User: Help revise our paper with Humanizer integration

Agent: I'll handle this in stages using sub-agents to keep our conversation clean.

Step 1: [Spawn sub-agent for paper analysis]
→ Sub-agent reads paper, analyzes structure
→ Returns summary

Step 2: [Spawn sub-agent for Humanizer setup]
→ Sub-agent configures Humanizer, runs checks
→ Returns configuration status

Step 3: [Spawn sub-agent for applying changes]
→ Sub-agent makes revisions, validates
→ Returns final paper with changes

[Final summary: All work complete, main context still clean]
```

### Example 3: Batch File Processing

**Without Sub-Agent**:
```
User: Rename all images in /assets to lowercase with timestamp prefix

Agent: [Loops through 100 files, exec each rename, all output in context]
→ 500+ KB of exec output in main conversation
```

**With Sub-Agent**:
```
User: Rename all images in /assets to lowercase with timestamp prefix

Agent: Spawning sub-agent for batch file processing...

[sessions_spawn with task]
→ Sub-agent handles all 100 files
→ Progress updates only announced at milestones
→ Final result: "Renamed 100 files successfully"

Main context: Only ~500 bytes for final result
```

### Example 4: Parallel Research Tasks

**Orchestrator Pattern** (maxSpawnDepth: 2):
```
User: Research best practices for: 1) API design, 2) Database schema, 3) Caching strategy

Agent (Orchestrator): I'll spawn parallel sub-agents for each topic.

[sessions_spawn for API design]
[sessions_spawn for Database schema]
[sessions_spawn for Caching strategy]

→ Three sub-agents run in parallel
→ Each researches independently
→ Results synthesized when all complete

Main context: Only the synthesized summary (~2K tokens)
Instead of: All research output (~50K+ tokens)
```

### Example 5: Long-Running Build/Test

**Without Sub-Agent**:
```
User: Build the project and run all tests

Agent: [exec npm install, exec npm build, exec npm test - all in main context]
→ Build logs (10K lines) stored in conversation
→ Test output (5K lines) stored in conversation
→ Context explodes
```

**With Sub-Agent**:
```
User: Build the project and run all tests

Agent: Spawning sub-agent for build and test process...

[sessions_spawn with runTimeoutSeconds: 600]
→ Sub-agent runs build (all logs in its context)
→ Sub-agent runs tests (all output in its context)
→ Announces: "Build successful, 142 tests passed, 3 failed"

Main context: Clean, only final result
```

### Example 6: Git Operations Across Multiple Repos

**Without Sub-Agent**:
```
User: Update all 10 project repositories and check for conflicts

Agent: [cd to each repo, git pull, check status - all output in context]
→ 10 repos × 5KB output each = 50KB in main context
```

**With Sub-Agent**:
```
User: Update all 10 project repositories and check for conflicts

Agent: Spawning sub-agent for repository maintenance...

[sessions_spawn with task]
→ Sub-agent visits each repo
→ Runs git operations
→ Returns summary table

Result:
✅ repo-1: Updated, no conflicts
✅ repo-2: Updated, no conflicts
⚠️  repo-3: Updated, 1 merge conflict
✅ repo-4: Already up to date
...

Main context: Only the summary table (~1KB)
```

### Configuration for Each Example

#### Example 1-3, 6: Standard Sub-Agent
```json
{
  "agents": {
    "defaults": {
      "subagents": {
        "model": "zai/glm-4.7-flash",
        "maxConcurrent": 4
      }
    }
  }
}
```

#### Example 4: Orchestrator Pattern
```json
{
  "agents": {
    "defaults": {
      "subagents": {
        "model": "zai/glm-4.7-flash",
        "maxConcurrent": 8,
        "maxSpawnDepth": 2
      }
    }
  }
}
```

#### Example 5: Long-Running Task
```json
{
  "agents": {
    "defaults": {
      "subagents": {
        "model": "zai/glm-4.7-flash",
        "runTimeoutSeconds": 900
      }
    }
  }
}
```

### Monitoring Commands

```
# List all running sub-agents
/subagents list

# Check specific sub-agent details
/subagents info 1

# View sub-agent output
/subagents log 1

# Stop a runaway sub-agent
/subagents kill 1

# Stop all sub-agents
/subagents kill all
```

### Token Comparison

| Task | Without Sub-Agent | With Sub-Agent | Savings |
|------|------------------|----------------|---------|
| Paper revision | 120K tokens | 15K tokens | 87.5% |
| Code analysis | 80K tokens | 8K tokens | 90% |
| Batch processing | 50K tokens | 2K tokens | 96% |
| Research synthesis | 100K tokens | 20K tokens | 80% |

### When NOT to Use Sub-Agents

- Quick single-file edits (just use read/write directly)
- Simple questions that don't require tools
- Tasks that need immediate user feedback
- One-liner commands

### Quick Reference Card

```
SIMPLE TASK → Main Agent
MULTI-STEP → Sub-Agent
PARALLEL → Multiple Sub-Agents
LONG-RUNNING → Sub-Agent with timeout
ORCHESTRATION → maxSpawnDepth: 2
```
