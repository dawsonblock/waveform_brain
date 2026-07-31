```markdown
# waveform_brain Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches you the core development patterns used in the `waveform_brain` Python repository. You'll learn the project's coding conventions, file organization, import/export styles, and how to structure your own contributions to match the existing codebase. While no specific frameworks or automated workflows are detected, this guide will help you write consistent, maintainable code and understand the project's approach to testing.

## Coding Conventions

### File Naming
- **Style:** snake_case
- **Example:**  
  ```python
  waveform_processor.py
  data_loader.py
  ```

### Import Style
- **Style:** Relative imports are used within the package.
- **Example:**  
  ```python
  from .utils import normalize_waveform
  from .data_loader import load_data
  ```

### Export Style
- **Style:** Named exports (explicitly listing functions/classes to be exported).
- **Example:**  
  ```python
  __all__ = ['WaveformProcessor', 'normalize_waveform']
  ```

### Commit Patterns
- **Type:** Freeform messages, no strict prefix required.
- **Average Length:** ~41 characters.
- **Example:**  
  ```
  Add new waveform normalization method
  Fix bug in data loading routine
  ```

## Workflows

_No automated workflows detected in this repository. All processes are manual._

## Testing Patterns

- **Framework:** Unknown (no standard Python test framework detected).
- **File Pattern:** Test files are named with the pattern `*.test.ts`, which is typical for TypeScript but unusual for Python projects. This may indicate legacy or mixed-language testing, or a placeholder for future tests.
- **Example:**  
  ```
  waveform_processor.test.ts
  ```

## Commands

| Command         | Purpose                                           |
|-----------------|--------------------------------------------------|
| /new-module     | Scaffold a new Python module with snake_case name |
| /add-test       | Create a new test file (see Testing Patterns)     |
| /list-exports   | List all named exports in a module                |
| /normalize-imports | Convert imports to relative style              |

> _Note: These commands are suggested for workflow automation and are not implemented in the repository._

```