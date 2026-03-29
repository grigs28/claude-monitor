# CHANGELOG

## [Unreleased]

### Added
- Smart confirmer with dual mode support (rule-based and AI-powered)
- AI mode using local Qwen 3.5 27B model
- Confirmation history tracking
- Automatic priority selection for "always allow" options

### Changed
- Improved prompt detection to handle various Claude Code formats
- Enhanced duplicate prevention mechanism
- Better command line detection

### Fixed
- Fixed issue with repeated confirmations
- Fixed command line false positives
- Improved timeout handling for AI mode (60 seconds)

## [1.0.0] - 2026-03-29

### Initial Release
- Basic rule-based confirmation
- Support for common Claude Code prompts
- Tmux session monitoring
- Prevent duplicate confirmations
