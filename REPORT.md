# Ace Combat Zero background recovery

## Result

Recovered genuine, clean **512×448 game background layers**, with no logo, text, or menu borders baked into the selected images. Produced exact **3840×2160 RGB PNGs**, without AI, inpainting, or invented detail:

- `wallpapers/acz-main-menu-base-3840x2160.png` — red/orange underlay from **MainSelect**, the selection-menu package.
- `wallpapers/acz-title-red-clouds-3840x2160.png` — more recognizable red/orange cloud artwork from **Title**, a different scene.
- Matching `-unfiltered.png` versions omit the mild source-pixel smoothing.

**The files above are extracted base layers, not verified reconstructions of the complete animated backgrounds.** A subsequent reference-matched static reconstruction of the main-menu layers is available below; it is explicitly approximate, not an original single texture or a decoded animation frame.

## Follow-up: layered main menu matched to your PCSX2 screenshot

The screenshot in `example from pcsx2/` strongly supports the missing MainSelect components:

- **Red grid:** `1239_00163d60` (texture index 6).
- **Faint blue reflection/image:** `1239_000f2940` (texture index 1).
- **Small warm highlights and faint streaks:** `1239_0012ada0` (texture index 2). Five visible spots match the reference locations; see `previews/reference-matched-spots.png`.

Both effect textures have **constant raw GS alpha 128**, not an embedded variable opacity mask. Their black/dark pixels can remain effectively transparent under additive blending. This is evidence for layer-level draw-time blending, not a recovered separate alpha image or proof of the exact GS blend state.

`tools/analyze_reference.py` registers the source textures and estimates RGB-additive gains from **84,286 UI-free pixels**, then estimates the highlight contribution in five small text-free patches. Effective fitted RGB weights are approximately **0.990 × grid + 0.074 × blue image + 0.743 × highlights**. They are **not decoded game alpha values**. Slight horizontal registration/overscan and subpixel offsets are also estimated; the reference and composites receive native-resolution filtering for comparison.

The red-grid-only model has mean absolute error **3.44/255** in the background sampling regions; adding the blue image reduces that to **0.60/255**. The highlight-patch error is **2.10/255**. These are in-sample fit diagnostics, not an independent validation of a complete renderer or proof of exact animation timing.

New outputs, using **only original game texture pixels**:

- **`wallpapers/acz-main-menu-layered-3840x2160.png`** — reference-matched, center-cropped 4K composite.
- **`wallpapers/acz-main-menu-layered-3840x2160-full-field.png`** — retains the entire texture field, stretched anamorphically to 16:9 instead of cropped.
- **`wallpapers/acz-main-menu-layered-3840x2160-limine.png`** — cropped version with a separately documented 10% RGB darkening for white-text readability.
- `artwork/reconstructed/acz-main-menu-layered-reference-fit-512x448.png` — native-size derived composite, kept separate from originals.
- **`previews/main-menu-layered-comparison.jpg`** — grid → blue image → highlights, beside the reference.
- `analysis/reference/fit.json` and `analysis/reference/layered_manifest.json` — reproducible parameters, metrics, source/reference/output hashes.

No screenshot pixels were pasted into artwork; the screenshot appears only in labeled comparison/annotation previews. Its original hash remains unchanged. Tiny highlights reduce minimum white-text contrast to **3.79:1** in the reference-matched wallpaper (179 of 8,294,400 pixels fall below 4.5:1); the optional Limine variant has minimum **4.55:1**. The original base-only wallpapers remain unchanged.

Reproduce this follow-up after the initial extraction:

```sh
OPENBLAS_NUM_THREADS=1 python3 tools/analyze_reference.py
OPENBLAS_NUM_THREADS=1 python3 tools/reconstruct_main_menu.py
python3 -m unittest discover -s tools -p 'test_*.py' -v
python3 tools/verify_outputs.py
```

The reconstruction is a close **static screenshot-estimated composition**. SWG timelines, original blend registers, and changing opacity/animation phases remain unresolved.

## Extractor diagnosis and repair

The community script opens lowercase `data.tbl` / `data.pac`; the supplied files are uppercase. Linux filename lookup is case-sensitive. Inputs and outputs also depend on the shell's working directory. `DATA//` itself is not the Linux incompatibility, and there are no Windows drive-letter/backslash paths to fix.

More importantly, the original script recursively removes `DATA` before checking inputs, then **deletes both archives after extraction**. It was inspected, not executed, and remains unchanged.

Safe replacement: **`tools/pac_extract.py`**. It preserves the observed table/extraction layout, resolves input names case-insensitively relative to the project (or `--source`), opens archives read-only, validates the complete table before extraction, checks short reads and output hashes, supports selected indices, and refuses to overwrite existing DATs/manifests. It never removes archives or output trees. Default invocation only validates; `--all` is available but was not used.

## Archive validation and inventory

- TBL: 12,512 bytes; little-endian count **1,563**, zero reserved word, then 1,563 `(byte_offset, byte_size)` uint32 pairs.
- PAC: **1,096,925,184 bytes**. Entries are contiguous, nonzero, nonoverlapping, and cover the archive exactly; no out-of-bounds ranges.
- Extracted only entries **1236–1256 and 1426–1429**: **25 files / 54,759,424 bytes**, avoiding a full 1.1 GB duplicate.
- Full archive inventory: **`analysis/inventory_enriched.csv`** (synthetic filenames, sizes, offsets, signature-based classifications, extracted paths, recovered scene names).
- The TBL contains no filenames; `1239.dat` etc. are index-derived names, not original developer filenames. Undecoded non-UI entries remain conservatively classified rather than assigned speculative formats.
- `assets/pac/extraction_manifest.json`: hashes, sizes, offsets for extracted DATs.
- `analysis/tim2_manifest.json`, `analysis/decoded_manifest.json`: texture offsets, dimensions, pixel/CLUT formats, alpha ranges, and original-TM2 hashes.

## Resource identification: evidence from the files

Each selected DAT has a count/relative-offset directory containing a **SWAD** resource table. SWAD records contain **SWG** named scenes and **TIM2** pictures. Validated **1,031 SWAD records**, including **1,000 TIM2s** whose SWAD sizes exactly match their TIM2 lengths. Independently cross-checked **1,000 SWG texture descriptors across 31 named scenes** against the corresponding pictures. Some descriptors have smaller logical dimensions than their padded texture storage; neither is silently discarded.

| Resource | DAT-relative offset | Absolute PAC offset | Evidence |
|---|---:|---:|---|
| Main-menu red/orange base | `1239.dat + 0x163d60` | `0x3b922d60` | SWG `MainSelect`, texture index 6; SWAD record 7; 512×448, 8-bit indexed, 256-entry RGBA CLUT |
| Title red-cloud base | `1238.dat + 0x869e0` | `0x3b6a19e0` | SWG `Title`, texture index 6; SWAD record 7; 512×448, 4-bit indexed, 16-entry RGBA CLUT |

Both bases have constant raw PS2 GS alpha **128** (fully opaque in the display conversion).

Related assets, exported separately:

- `1239_0012ada0`: light/particle-like image; `1239_000f2940`: blue cockpit/image layer in MainSelect. Borders, icons, and other UI are separate resources.
- `1238_00032800`, `1238_0004e8a0`, `1238_0006a940`: gold-colored cloud layers with varying alpha in Title.
- `1238_00029b00`: light/particle atlas; `1238_000a2a80`: game logo, separate from the cloud base.
- The title cloud base also visually matches the underlying cloud pattern in [this public title-screen screenshot](https://images.launchbox-app.com/8cf7360f-c4dd-47e1-a0fc-0a254f137784.jpg). No pixels from that screenshot were used.

Detailed mappings: **`analysis/swad_manifest.csv`**, **`analysis/scene_texture_bindings.csv`**. The SWG descriptor table layout was inferred locally and cross-validated; its unknown flag is deliberately not assigned a meaning.

## Decoding and preservation

`tools/decode_tim2.py` exports all 1,000 original `.tm2` byte slices plus native-resolution color PNGs under `assets/tim2/` (997 indexed pictures and three direct RGBA pictures). The supported, observed assets are single-picture, single-mipmap TIM2 v4; unsupported layouts fail explicitly.

- 4-bit pixels: low nibble first; image planes are linear, not GS-swizzled.
- 8-bit CSM1 CLUTs: exchange palette index bits 3 and 4. Decoded logos/text provide visual sanity checks in addition to synthetic tests.
- `*_indices.png`: unchanged index plane for indexed assets.
- `*_raw-alpha.png`: decoded colors with the original numeric GS alpha values.
- Plain `.png`: display copy with alpha `min(255, 2 × GS_alpha)`, not a claim that stored alpha was originally 255.
- Byte-exact `.tm2` retains the complete original palette, metadata, and image data.

Convenient selected originals: **`artwork/original/`**, including native 512×448 PNGs, raw-GS-alpha PNGs, index planes, exact TM2s, and palette bytes in their original storage order. No logos or text were erased: they were never part of these base textures.

## Wallpaper processing and previews

`tools/make_wallpapers.py` uses the opaque bases alone. The standard versions apply a **0.65-source-pixel Gaussian prefilter**, then **Lanczos** scaling; unfiltered variants use Lanczos alone. No color grading, generative processing, fabricated extensions, or speculative layer blending.

A **4:3 display interpretation** of the 512×448 sample grid was chosen (pixel aspect 7:6), resized to 3840×2880, then center-cropped to 3840×2160. This corresponds to source rows **56–391**: 25% of the native vertical field is cropped, with all original pixels retained separately. This is a wallpaper framing choice, not a verified reconstruction of the game's widescreen settings.

The processed backgrounds retain dark colors suitable for white text; measured minimum sRGB white/background contrast is **10.88:1** for the standard menu base and **10.45:1** for the standard title clouds. `analysis/wallpaper_manifest.json` records processing, source provenance, dimensions, contrast, and output hashes.

Previews:

- **`previews/wallpaper_comparison.jpg`** — menu base versus title clouds.
- **`previews/background_candidates.jpg`** — selected layers and separate logo.
- `previews/large_01.jpg` through `large_03.jpg` — 120 large textures.
- `previews/all_01.jpg` through `all_10.jpg` — all 1,000 decoded textures.

## Verification and limitations

**Eight unit tests passed**, including three follow-up tests for robust blend fitting, additive composition, and sampling. End-to-end verification compared all 25 DATs and 1,000 original TM2 slices against their PAC bytes, checked 2,997 decoded PNGs, validated all seven wallpaper hashes/dimensions/modes, and verified the reference screenshot remained unchanged. Original PAC, TBL, and community-script SHA-256 hashes are unchanged: **`analysis/verification.json`**.

Recovered bases are ordinary embedded textures, so video decoding was unnecessary for these assets. This does not classify every unrelated PAC resource or rule out video elsewhere. No emulator frame/GS capture or SWG timeline renderer was used; the exact fully composited animation remains unresolved. A 4K upscale cannot restore detail beyond the 512×448 originals; baked texture/palette patterns remain part of the source.

No packages were installed. No rebuilder ran. Original backups, ISO, live Limine configuration, and Secure Boot setup were not touched. All deliberate file creation was inside this project.

## Core commands used / reproduction

Run from the project root with Python, Pillow, and NumPy already available. Inventory/extraction commands require fresh output paths; they intentionally refuse existing manifests/files. Derived-image scripts regenerate their own outputs.

```sh
python3 -m unittest discover -s tools -p 'test_*.py' -v
python3 tools/pac_extract.py --inventory analysis
python3 tools/pac_extract.py --indices 1236-1256,1426-1429 --output assets/pac
python3 tools/decode_tim2.py
python3 tools/inspect_containers.py
python3 tools/validate_scene_bindings.py
python3 tools/make_wallpapers.py
python3 tools/verify_outputs.py
file wallpapers/*.png
```

`analysis/source-sha256.json` contains the baseline hashes recorded before extraction. For another archive build/region, generate a new baseline first; the offsets/indices above apply specifically to the supplied PAC/TBL.
