# PWA Icons

This folder contains the Progressive Web App icons for Mux Minus.

## Required Icons

You need to generate PNG icons from the SVG source files:

### From `icon.svg` (standard icons with rounded corners):
- `icon-72x72.png`
- `icon-96x96.png`
- `icon-128x128.png`
- `icon-144x144.png`
- `icon-152x152.png`
- `icon-192x192.png`
- `icon-384x384.png`
- `icon-512x512.png`

### From `icon-maskable.svg` (maskable icons for adaptive icon systems):
- `icon-maskable-192x192.png`
- `icon-maskable-512x512.png`

## Generating PNG Icons

You can use various tools to convert SVG to PNG:

### Using ImageMagick (command line):
```bash
# Standard icons
convert -background none icon.svg -resize 72x72 icon-72x72.png
convert -background none icon.svg -resize 96x96 icon-96x96.png
convert -background none icon.svg -resize 128x128 icon-128x128.png
convert -background none icon.svg -resize 144x144 icon-144x144.png
convert -background none icon.svg -resize 152x152 icon-152x152.png
convert -background none icon.svg -resize 192x192 icon-192x192.png
convert -background none icon.svg -resize 384x384 icon-384x384.png
convert -background none icon.svg -resize 512x512 icon-512x512.png

# Maskable icons
convert -background none icon-maskable.svg -resize 192x192 icon-maskable-192x192.png
convert -background none icon-maskable.svg -resize 512x512 icon-maskable-512x512.png
```

### Using Inkscape (command line):
```bash
inkscape icon.svg --export-type=png --export-filename=icon-512x512.png -w 512 -h 512
```

### Online Tools:
- https://realfavicongenerator.net/
- https://www.pwabuilder.com/imageGenerator
- https://maskable.app/editor (for testing maskable icons)

## Testing

After generating the icons, you can test your PWA using:
- Chrome DevTools > Application > Manifest
- https://www.pwabuilder.com/
- Lighthouse audit in Chrome DevTools
