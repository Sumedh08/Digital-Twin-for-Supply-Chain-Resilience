# Contributing to Digital Twin for Supply Chain Resilience

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs. actual behavior
- Screenshots (if applicable)
- Environment details (OS, Python version, Node version)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please create an issue describing:
- The proposed feature
- Use case and benefits
- Possible implementation approach

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Code Style

**Python:**
- Follow PEP 8
- Use type hints where possible
- Add docstrings for functions

**JavaScript/React:**
- Use ES6+ syntax
- Follow React best practices
- Use functional components with hooks

### Testing

Before submitting a PR:
- Test the frontend (`npm run dev`)
- Test the backend (`python -m uvicorn backend.main:app --reload`)
- Ensure no console errors
- Verify AI models load correctly

## Development Setup

See [README.md](README.md) for installation instructions.

## Questions?

Feel free to open an issue for any questions or discussions.
