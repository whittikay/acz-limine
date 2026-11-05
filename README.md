# Ace Combat Zero menu wallpaper recovery

Recovering the original PS2 **Ace Combat Zero: The Belkan War** menu artwork and preparing a clean **3840×2160 PNG** for Limine. No AI-generated artwork or screenshot inpainting.

## Finished images

| File under `wallpapers/` | Description |
|---|---|
| `acz-main-menu-layered-3840x2160-limine.png` | Recommended for Limine: layered reconstruction, center-cropped, 10% darker for white text |
| `acz-main-menu-layered-3840x2160.png` | Screenshot-matched layered reconstruction, center-cropped |
| `acz-main-menu-layered-3840x2160-full-field.png` | Entire source field stretched to 16:9 instead of cropped |
| `acz-main-menu-base-3840x2160.png` | Original red-grid base alone |
| `acz-title-red-clouds-3840x2160.png` | Separate title-screen cloud base |

The source layers are **512×448**, not native 4K. The layered result uses the original red grid, faint blue image, and warm particle/highlight texture. Layer registration and additive RGB gains were estimated from a PCSX2 reference screenshot; this is **not an exact decoded animation frame**. The default framing uses a 4:3 display interpretation, Lanczos scaling to 3840×2880, and a center crop to 3840×2160.

See **[REPORT.md](REPORT.md)** for resource offsets, format findings, limitations, processing, and validation results.

## Repository contents

- `tools/`: safe extractor, TIM2 decoder, inspectors, reference fitting, reconstruction, and tests.
- `assets/tim2/`: only nine documented source textures and their native diagnostic exports. The rest of the bulk extraction is ignored.
- `artwork/original/`: selected original TM2s, native PNGs, index planes, and stored palette bytes.
- `artwork/reconstructed/`: native-resolution derived composite, separate from originals.
- `previews/`: contact sheets, layer comparisons, and wallpaper previews.
- `example from pcsx2/`: the supplied reference screenshot, unchanged.
- `analysis/`: inventories, source hashes, fitted parameters, mappings, and verification records.
- `wallpapers/`: finished PNGs. No live bootloader configuration or signing material.

**Not included:** `DATA.PAC`, `DATA.TBL`, disc images, bulk DAT extraction, Python caches, credentials, or local environment files. The original archives remain untouched on the local machine.

## Run the tests

Tested with Python 3.14.9, Pillow 13.0.0, and NumPy 2.5.4. Dependencies are recorded in `requirements.txt`; use an isolated environment if they are not already available.

```sh
python3 -m unittest discover -s tools -p 'test_*.py' -v
```

The tests use synthetic data and do not require the game archives.

## Reproduce the layered wallpaper without the archives

The necessary source PNGs, reference, and manifests are retained in Git. From the project root:

```sh
# Optional: refit the provided screenshot rather than using the saved parameters.
OPENBLAS_NUM_THREADS=1 python3 tools/analyze_reference.py

# Regenerate the native composite, previews, and three layered 4K variants.
OPENBLAS_NUM_THREADS=1 python3 tools/reconstruct_main_menu.py
```

These derivative scripts rewrite their own generated outputs. They do not modify the reference screenshot or original textures.

## Archive extraction and full verification

Supply your own matching `DATA.PAC` and `DATA.TBL` in the project root. The supplied archive build is identified by `analysis/source-sha256.json`; do not assume the documented indices apply to other regions/builds.

```sh
# Read-only validation; no extraction by default.
python3 tools/pac_extract.py

# Selectively extract the 25 relevant UI packages into a fresh directory.
python3 tools/pac_extract.py --indices 1236-1256,1426-1429 --output assets/pac
python3 tools/decode_tim2.py
python3 tools/inspect_containers.py
python3 tools/validate_scene_bindings.py
python3 tools/verify_outputs.py
```

The safe extractor refuses to overwrite existing DATs/manifests. Full verification needs the local archives and bulk extraction; it is not expected to run against a bare clone alone. For a new inventory, use a fresh path, e.g. `python3 tools/pac_extract.py --inventory analysis/rescan`.

**Do not run `ACZ PAC extractor.py`.** This unmodified community script, attributed to **death_the_d0g**, is preserved for provenance. It contains destructive cleanup logic, including deleting the source archives. Use `tools/pac_extract.py` instead. No PAC rebuilder is used.

Game artwork remains the property of its respective rights holders. No ownership or redistribution license for the game assets or community script is asserted here.
