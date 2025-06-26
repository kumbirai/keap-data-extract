# Application Icons

This directory contains the application icons for the Keap Data Extract tool.

## Files

- `icon.svg` - Source SVG icon file (256x256)
- `icon.png` - PNG version for cross-platform use (256x256)
- `icon.ico` - Windows ICO format with multiple sizes (16x16 to 256x256)
- `icon_32.png` - Small PNG version for Linux desktop integration (32x32)

## Design

The icon features:
- Blue circular background (#2563eb) representing professionalism and trust
- Database symbol showing data storage
- Data flow arrows indicating extraction process
- Document/file icon representing output
- Keap branding element (simplified "K")

## Usage

- **Windows**: Uses `icon.ico` for the executable icon
- **Linux/macOS**: Uses `icon.png` for the executable icon
- **Desktop integration**: `icon_32.png` can be used for desktop shortcuts and system integration

## Regeneration

To regenerate the icon files, run:
```bash
python create_icon.py
```

This will convert the SVG source to all required formats. 