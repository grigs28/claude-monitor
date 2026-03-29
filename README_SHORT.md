# Claude Auto Confirmer

Automatically monitor and confirm Claude Code prompts.

## Features

- 🔀 **Dual Mode**: Rule-based (fast) or AI-powered (intelligent)
- 🎯 **Smart Detection**: Auto-detect Claude Code confirmation prompts
- ⚡ **Fast Response**: 1-2 second check interval
- 🧠 **AI Powered**: Optional Qwen 3.5 27B for intelligent decisions
- 🛡️ **Safe**: Command line detection, duplicate prevention

## Quick Start

```bash
# Rule mode (fast, default)
python3 smart_confirmer.py claude

# AI mode (intelligent)
python3 smart_confirmer.py claude --ai
```

## Documentation

- [完整中文文档](README.md)
- [Bilingual Guide](README_EN_CN.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## Requirements

- Python 3.7+
- tmux
- For AI mode: Local Qwen API access

## License

MIT License - see [LICENSE](LICENSE)
