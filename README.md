# Bald Spider

A Python web scraping framework built with modern Python tooling.

## Project Structure

```
bald_spider/
├── bald_spider/
│   ├── __init__.py
│   ├── main.py
│   └── core/
│       └── engine.py
├── tests/
│   ├── __init__.py
│   ├── test_main.py
│   └── baidu_spider/
│       ├── __init__.py
│       └── baidu.py
├── pyproject.toml
├── uv.lock
├── .gitignore
└── README.md
```

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for package management.

```bash
# Install dependencies
uv sync

# Install in development mode
uv pip install -e .
```

## Development

```bash
# Run tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Format code
uv run black .

# Run the package
uv run python -c "from bald_spider import main; main()"
```

## Features

- Modern Python packaging with uv
- Comprehensive testing setup with pytest
- Code formatting with black
- Source layout with `src/` directory

## License

MIT
