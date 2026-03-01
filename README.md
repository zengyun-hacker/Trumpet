<p align="center">
  <img src="icon.png" width="128" height="128" alt="Trumpet">
</p>

# Trumpet

Toot from Alfred. A simple Alfred workflow to post to Mastodon.

## Installation

Download `Trumpet.alfredworkflow` from the [release](./release) folder and double-click to install.

## Usage

### 1. Configure your Mastodon instance

```
mast config <domain>
```

Example: `mast config mastodon.social`

### 2. Login to your account

```
mast login
```

This opens your browser for OAuth authorization. After authorizing, copy the code and run:

```
mast auth <code>
```

### 3. Send a toot

```
toot <your message>
```

Press Enter to send.

## Requirements

- Alfred 4+ with Powerpack
- Python 3
- macOS

## License

MIT
