# PS5 Dump Runner Installer

A GUI application for installing dump_runner files to PS5 game dumps via FTP.

## Features

- **FTP Connection**: Connect to your PS5's FTP server to scan for game dumps
- **Auto-Scan**: Automatically scans internal storage, USB devices, and extended storage for homebrew dumps
- **GitHub Integration**: Download official dump_runner releases directly from EchoStretch's GitHub repository
- **Batch Upload**: Upload dump_runner files to multiple game dumps at once
- **Custom Files**: Option to upload your own experimental dump_runner files
- **Progress Tracking**: Visual progress indicators for downloads and uploads

## Requirements

- Python 3.11 or higher
- PS5 with FTP server running (e.g., via homebrew)
- Network connection between PC and PS5

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/ps5-dump-runner-installer.git
cd ps5-dump-runner-installer

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m src.main
```

### From Executable

Download the latest release from the Releases page and run `PS5DumpRunnerInstaller.exe`.

## Usage

### 1. Connect to PS5

1. Start an FTP server on your PS5
2. Enter your PS5's IP address in the **Host** field
3. Default port is `1337` (adjust if needed)
4. Default username is `anonymous` (adjust if needed)
5. Click **Connect & Scan** to connect and scan for game dumps

### 2. Download dump_runner Files

Click **Download from GitHub** to download the latest official dump_runner release from EchoStretch's repository.

Downloaded files are cached locally at:
- **Windows**: `%APPDATA%\PS5DumpRunnerInstaller\cache\releases\`
- **Linux**: `~/.config/PS5DumpRunnerInstaller/cache/releases/`
- **macOS**: `~/Library/Application Support/PS5DumpRunnerInstaller/cache/releases/`

### 3. Select Game Dumps

After scanning, select the game dumps you want to install dump_runner to:
- Click checkboxes next to individual dumps
- Use **Select All** / **Select None** buttons for batch selection
- Dumps show their current status: "Installed", "Partial", or "Not Installed"

### 4. Upload Files

- **Upload Downloaded Files**: Upload the official dump_runner files to selected dumps
- **Upload Custom...**: Browse and upload your own experimental files

## Scan Locations

The application scans these PS5 FTP paths for game dumps:

| Location | Path |
|----------|------|
| Internal Storage | `/data/homebrew/` |
| USB Devices | `/mnt/usb0/homebrew/` through `/mnt/usb7/homebrew/` |
| Extended Storage | `/mnt/ext0/homebrew/` through `/mnt/ext7/homebrew/` |

## Files Installed

For each game dump, the following files are uploaded:
- `dump_runner.elf` - The main executable
- `homebrew.js` - JavaScript configuration file

## Troubleshooting

### Cannot connect to PS5
- Verify the FTP server is running on your PS5
- Check the IP address is correct
- Ensure your PC and PS5 are on the same network
- Try disabling firewall temporarily

### No dumps found
- Ensure game dumps are in the correct homebrew directories
- Check that the FTP server has access to the storage locations

### Upload fails
- Verify FTP connection is still active
- Check available space on the target storage
- Ensure you have write permissions

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

### Building Executable

```bash
pyinstaller --onefile --windowed --name "PS5DumpRunnerInstaller" src/main.py
```

## Credits

- [EchoStretch](https://github.com/EchoStretch) - dump_runner development
- This installer tool provides a convenient way to deploy dump_runner files

## License

MIT License - See LICENSE file for details.

## Disclaimer

This tool is provided for educational and legitimate homebrew purposes only. Users are responsible for ensuring they comply with all applicable laws and terms of service.
