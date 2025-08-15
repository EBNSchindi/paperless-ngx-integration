# Personal Agent Usage Guide

## Overview

This project includes a collection of specialized personal agents located in `.claude/agents/`. These agents provide specific capabilities for different development tasks.

## Available Agents

### 1. **researcher**
**Purpose**: Research and requirements analysis
**When to use**: 
- Investigating new technologies or libraries
- Analyzing requirements before implementation
- Researching best practices and patterns

**Example**:
```python
# Use researcher to investigate a new integration
"Research best practices for Sevdesk API integration"
```

### 2. **architect-cleaner**
**Purpose**: Architecture validation and aggressive repository cleanup
**When to use**:
- Validating Clean Architecture compliance
- Cleaning up repository structure
- Removing unnecessary files and dependencies

**Important**: This agent follows strict documentation placement rules:
- Creates docs in `docs/architecture/` and `docs/project-management/`
- NEVER creates .md files in project root
- Performs aggressive cleanup operations

### 3. **python-generator**
**Purpose**: Modern Python 3.10+ code generation with Context7 integration
**When to use**:
- Implementing new features
- Creating new modules or services
- Generating type-safe Python code

**Features**:
- Uses modern Python features (3.10+)
- Integrates with Context7 for documentation
- Follows project's Clean Architecture

### 4. **test-engineer**
**Purpose**: Comprehensive test suite creation
**When to use**:
- Creating unit tests for new features
- Developing integration tests
- Building end-to-end test scenarios

### 5. **code-reviewer**
**Purpose**: Comprehensive code review for Python projects
**When to use**:
- After implementing new features
- Before merging significant changes
- For security and performance audits

### 6. **doc-writer**
**Purpose**: Documentation generation and maintenance
**When to use**:
- Creating user documentation
- Updating API documentation
- Writing technical guides

**Note**: Updates documentation in appropriate `docs/` subdirectories

### 7. **security-engineer**
**Purpose**: Security analysis and vulnerability detection
**When to use**:
- Reviewing code for security issues
- Analyzing dependencies for vulnerabilities
- Implementing security best practices

### 8. **prompt-engineer**
**Purpose**: Transforms vague ideas into precise technical prompts
**When to use**:
- Creating optimized prompts for LLM operations
- Designing agent chains
- Optimizing metadata extraction prompts

### 9. **claude-status**
**Purpose**: Dashboard and metrics tracking
**When to use**:
- Tracking project metrics
- Generating status reports
- Monitoring agent activity

## Agent Chain Examples

### Example 1: Feature Implementation
```
1. researcher → Investigate requirements and best practices
2. architect-cleaner → Validate architecture compliance
3. python-generator → Implement the feature
4. test-engineer → Create comprehensive tests
5. code-reviewer → Review implementation
6. doc-writer → Update documentation
```

### Example 2: Bug Fix
```
1. researcher → Investigate root cause
2. python-generator → Implement fix
3. test-engineer → Add regression tests
4. code-reviewer → Validate fix
```

### Example 3: Documentation Update
```
1. claude-status → Generate current metrics
2. doc-writer → Update user documentation
3. architect-cleaner → Clean up old docs
```

## Important Rules

### Documentation Placement
All agents must follow these documentation placement rules:

**Root Directory Files** (only these):
- `README.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `LICENSE`
- `CLAUDE.md`
- `AGENT_LOG.md`

**All Other Documentation** goes in `docs/`:
```
docs/
├── architecture/       # Technical architecture docs
├── project-management/ # Project management docs
├── development/       # Development guides
├── setup/            # Setup and configuration
└── user-guide/       # User documentation
```

### Agent Log

All agents should write their activities to `AGENT_LOG.md` in the project root. This provides a history of agent activities and decisions.

## Usage in This Project

### Current Implementation Status

The following agents were used in the Sevdesk integration:
- **researcher**: Investigated IONOS email issues and Sevdesk requirements
- **architect-cleaner**: Validated Clean Architecture compliance
- **python-generator**: Implemented all feature changes

### Recommended Next Steps

1. Use **test-engineer** to expand test coverage
2. Use **security-engineer** to audit the IONOS implementation
3. Use **doc-writer** to create end-user documentation
4. Use **claude-status** to track implementation metrics

## Best Practices

1. **Chain agents appropriately**: Use researcher before implementation
2. **Validate with architect-cleaner**: Ensure architecture compliance
3. **Document everything**: Use AGENT_LOG.md for traceability
4. **Review before deployment**: Always use code-reviewer
5. **Keep docs organized**: Follow the documentation structure rules

## Integration with Project

The agents are aware of:
- Project's Clean Architecture
- Pydantic v2 models
- LiteLLM integration
- Paperless NGX API
- Sevdesk requirements

They will automatically follow project conventions and patterns when generating code or documentation.