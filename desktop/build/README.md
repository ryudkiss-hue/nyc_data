# App icons

electron-builder auto-detects icons placed in this `build/` directory.
Add the following (optional — defaults to the Electron icon if absent):

| File | Platform | Spec |
|------|----------|------|
| `icon.ico` | Windows | multi-size, includes 256×256 |
| `icon.icns` | macOS | 512×512 + retina |
| `icon.png` | Linux | 512×512 (or larger) |

You can generate all three from a single 1024×1024 PNG with
[`electron-icon-builder`](https://www.npmjs.com/package/electron-icon-builder):

```bash
npx electron-icon-builder --input=source-1024.png --output=build
```

A source mark already exists at `../standalone/icons/icon.svg` — rasterize it
to a 1024×1024 PNG (e.g. with Inkscape or an online converter) and run the
command above.
