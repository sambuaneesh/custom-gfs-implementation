# Contributing to GFS Implementation

Thank you for your interest in contributing to our GFS implementation! This document provides guidelines for contributions.

## Code Style and Standards

### Python Code Style
- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Maximum line length: 100 characters
- Use descriptive variable names

### Logging Standards
The logger is configured to log to both file and console:
```python
# Retrieve a logger
logger = GFSLogger.get_logger("ComponentName")

# Log levels and their usage
logger.debug("Detailed information for debugging")
logger.info("General operational messages")
logger.warning("Warning messages for potential issues")
logger.error("Error messages for actual problems", exc_info=True)
```

### Error Handling
```python
try:
    # Operation code
    logger.debug("Operation details")
except SpecificException as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    raise CustomException(f"Meaningful error message: {str(e)}")
```

## Development Workflow

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/gfs-implementation.git
   cd gfs-implementation
   ```

2. **Create Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Set Up Development Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Make Changes**
   - Write code following style guidelines
   - Add appropriate logging
   - Update tests if necessary
   - Update documentation

5. **Test Changes**
   - Run unit tests
   - Test with multiple chunk servers
   - Verify logging output

6. **Submit Pull Request**
   - Clear description of changes
   - Reference any related issues
   - Include test results

## Adding New Features

1. **Component Integration**
   - Follow existing architectural patterns
   - Maintain separation of concerns
   - Add appropriate logging

2. **Documentation**
   - Update README.md if needed
   - Add docstrings to new functions/classes
   - Update ARCHITECTURE.md for structural changes

3. **Testing**
   - Add unit tests for new features
   - Include integration tests if needed
   - Test with multiple chunk servers

## Commit Message Format
```
type(scope): Brief description

Detailed description of changes
- Change 1
- Change 2

Fixes #issue_number
```

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation
- style: Formatting
- refactor: Code restructuring
- test: Adding tests
- chore: Maintenance

## Pull Request Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Code refactoring

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Tested with multiple chunk servers

## Checklist
- [ ] Code follows style guidelines
- [ ] Appropriate logging added
- [ ] Documentation updated
- [ ] Tests added/updated
```
