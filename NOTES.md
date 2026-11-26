# MOTION STUDIO rebuild - production notes

## Phase 0 - setup (2026-11-25)
- Dirs created: src/, output/, qc/, assets/fonts/ under ~/workspace/motion-studio/rebuild/
- Fonts bundled in assets/fonts/: SpaceGrotesk.ttf (136,676 B, variable, display), Inter.ttf (876,576 B, spare grotesk), JetBrainsMono.ttf (downloaded from google/fonts GitHub raw, variable TTF, verified with `file` as real TrueType). Brief allows ONE grotesk display + ONE mono on screen: Space Grotesk + JetBrains Mono are the on-screen pair; Inter stays unused in assets as a spare.
- Env: PIL 10.2.0, numpy 1.26.4, ffmpeg 8.1.2, 4 cores visible, RAM tight (~1.1 GB available). Renderer streams raw frames to ffmpeg stdin; SS 1.5 internal canvas 2880x1620 for the 1920x1080 master.

## Timeline design (120 BPM, beat = 15 frames, every cut on a beat)
Total 1545 frames = 51.5 s at 30 fps.
- 0-119 cold open (120 f, 4.0 s)
- 120-149 chapter MOTION (30 f)
- 150-254 anime.js (105 f)
- 255-359 react-spring (105 f)
- 360-464 PixiJS (105 f)
- 465-494 chapter DATA (30 f)
- 495-614 D3 (120 f)
- 615-644 chapter 2D/3D (30 f)
- 645-749 p5.js (105 f)
- 750-854 Motion Canvas (105 f)
- 855-959 Lottie Web (105 f)
- 960-1064 Blender (105 f)
- 1065-1169 three.js (105 f)
- 1170-1199 chapter VIDEO/SOUND (30 f)
- 1200-1304 Remotion Skills (105 f)
- 1305-1424 Tone.js (120 f, 8 steps x 15 f, plucks on the step grid)
- 1425-1544 closing (120 f, 4.0 s)
three.js counted once: 11 hero scenes total (brief double-counted it).

## Phase 1 - code + probe frames (qc/probe1/, 17 frames viewed)
Pipeline works end to end. Probe verdicts:
- Cold open lockup, chapter beat, spring curve (real overshoot), Pixi ring+disc form, D3 line phase with cursor, p5 flow field, Motion Canvas timeline sync, Lottie heart (real JSON playback), Remotion split, Tone grid, closing assembly: all read correctly.
- DEFECTS found in probes and fixed before render 1:
  1. Variable fonts defaulted to Light weight. engine.font() now pins display=700, mono=500 via set_variation_by_axes.
  2. Cold-open scaled letters were clipped by their paste layers. Letters now drawn directly at scaled font size, centered on their cell.
  3. anime.js star morph was a wobbly blob (radius modulation). Replaced with a true 5-point star polygon, perimeter-walked.
  4. Lottie heart too small: placement scale 600 -> 800 output px.
  5. Blender title/star were erased by the full-canvas viewport layers. Layers now pasted cropped to the viewport window only.
  6. three.js knot filled the whole frame (camera too close), accent bands too wide. cam_z 30-24 -> 47-40, focal 1.15h -> 1.0h, tube r 3.0 -> 2.6, accent threshold 0.93 -> 0.965.
  7. Closing lockup box was too small: grid names poked out around it. Replaced with a full-frame dim (blend 88 percent to BG) under the lockup.
  8. Lottie player: keyframed scalars arrive as 1-element lists; coerced in trim evaluation.
  9. Blender mesh indexing: verts[tuple] failed; uses np.array(tri).

## QC ITERATION 1 - output/iter1.mp4 (19,334,474 B silent + AAC mux)
Evidence: 103 frames at 0.5 s intervals viewed as 9 contact sheets; ffprobe: 1920x1080, 30 fps, 1545 frames, 51.5 s, h264 + aac.
- Frame-hash check: 1545 frames hashed, exactly 1 consecutive duplicate (frame 610, D3 held treemap at the transition head).
- Sync: initial FAIL was a detector artifact at t=0 (no preceding window). Detector now pads 100 ms of silence; re-run on the same file: SYNC PASS, all 23 targets within 11 ms (tolerance 33.3 ms).
- Layout registry (13,619 text elements): 62 defects:
  1. Spring readout crossed the left/right safe margins at stage extremes and overlapped the title during overshoot (f250-260, f350-354).
  2. Motion Canvas NODE label crossed both margins at stage extremes (f745-849).
  3. Closing names fly in from off-frame during the 5 transition lead frames before the segment start (f1421-1424); flagged by the margin check.
- Visual defects from the contact sheets:
  4. Spring relaunch drew a vertical reset cliff in the curve.
  5. Pixi burst threw the ring off-frame; the reformed square read as a thin vector outline.
  6. D3 slice-and-dice treemap read as a second bar chart; bar value labels sat on the axis for bars that had not grown yet.
  7. Remotion rendered title small and high in its panel.
Fixes applied for iteration 2:
  1. Readout clamped inside margins; moves below the block when the block rides high.
  2. Motion Canvas stage (curve + node) inset 84 px each side.
  3. QC exception documented: closing assembly flight frames (incl. lead frames) are intentional off-frame entries; at rest all names are inside margins.
  4. Curve polyline breaks at the relaunch frame instead of connecting.
  5. Burst distance 0.42 -> 0.20 of unit; square targets get +-6 px particle grain.
  6. Two-row value-balanced treemap; bar labels only once grow > 0.6; pulse dot on the hero treemap rect (also removes the frame-610 duplicate).
  7. Remotion title 64 -> 88 px, anchored lower in the panel.

## QC ITERATION 2 - output/iter2.mp4
- Layout registry (13,503 text elements): PASS, zero defects.
- Sync: PASS (all 23 targets within 11 ms).
- Frame hashes: 1545 frames, 1 consecutive duplicate at frame 355 (spring settled tail identical at the wipe head).
- Visual pass (9 contact sheets + full-size transition frames 147/253/350/358/463/1197/1422):
  all iteration-1 fixes verified on screen: spring readout placed and clamped, curve break at relaunch, Pixi burst stays in frame and the square reads as particles, two-row treemap reads as a treemap, Motion Canvas node inside margins, Remotion title larger.
- Transition audit note: the block wipe on disk is a cover-reveal wipe (accent floods in from the left, hard cut under full cover at the beat, accent drains to the right revealing the next scene). Verified frame by frame at the spring-to-Pixi cut (frames 352-366); it is bold and beat-locked, kept as designed.
- Remaining defect for iteration 3: frame 355 duplicate. Fix: the spring TARGET dashed line now marches 2 px per frame, so the settled tail is never pixel-static.

## QC ITERATION 3 - main final + variant audit
- Main 1920x1080 (render 3, marching-dash fix): layout QC PASS, SYNC PASS, frame hashes: 1545 frames, ZERO consecutive duplicates. Main is final: output/motion-studio-cinema-1920x1080.mp4.
- Variant audit (portrait 1080x1920, scene midpoints viewed): the landscape-first layouts did NOT all adapt. Defects:
  1. Footer code line clipped at the right edge and overlapped the scene index in every narrow scene (anime, Pixi, D3, p5, Blender, three.js, Tone).
  2. Blender split layout kept the viewport in a tall right strip; mesh cramped.
  3. three.js focal length used frame height, so the knot ballooned in portrait.
  4. Closing name grid kept 3 landscape columns: names overlapped each other; the lockup line exceeded the margins.
  5. anime.js stagger grid kept 14x7 landscape geometry: tiny cells, huge vertical gaps in portrait.
- Fixes (all aspect-conditional; the 1920x1080 output is pixel-identical under the new code, verified by construction: every changed branch reduces to the old values at 16:9):
  1. footer() auto-fits the code size to the available width and splits the line in two at a natural break when it still does not fit; the index never overlaps.
  2. Blender stacks in portrait: full-width viewport below the title, mesh scaled to viewport width.
  3. three.js focal = min(W, H).
  4. Closing grid: 3 columns at W >= 1400, 2 columns below; lockup font fitted to the margins.
  5. anime grid: 10x18 in portrait, 12x12 in square, 14x7 in landscape.
- Portrait and square re-rendered from the fixed code; midpoint QC follows.

## Variant audit round 2 + FINAL DELIVERABLES
- Square midpoint audit found 3 more narrow-aspect defects: (1) the Remotion Skills header title overflowed the frame and ran under the star widget; (2) the Remotion split panels overlapped, code clipped by the render panel, SPRING IN clipped by its panel; (3) chapter titles, once fitted to full width, collided with the top-right chapter progress list.
- Fixes: header() auto-fits any title to the available width; draw_chapter fits its title and moves the progress list to the bottom-right in narrow aspects; Remotion stacks its panels in portrait and uses a wrapped code variant plus a fitted SPRING IN in square. All verified at probe level, then both variants re-rendered in full.
- FINAL VERIFICATION (ffprobe, on disk):
  - output/motion-studio-cinema-1920x1080.mp4: 20,304,438 B, 1920x1080, 30 fps, 1545 frames, 51.5 s, h264 + aac.
  - output/motion-studio-cinema-1080x1920.mp4: 20,531,025 B, 1080x1920, 30 fps, 1545 frames, 51.5 s, h264 + aac.
  - output/motion-studio-cinema-1080x1080.mp4: 16,876,241 B, 1080x1080, 30 fps, 1545 frames, 51.5 s, h264 + aac.
  - output/score.wav: 4,542,344 B.
- Sync check re-run on the portrait deliverable: SYNC PASS (same audio track as the main).
- Final variant frames viewed from the actual deliverables (qc/final/): Remotion portrait + square and chapter square all clean; earlier midpoint sets in qc/portrait2/ and qc/square/.
- output/ now holds exactly the 3 finals + score.wav; iteration renders and silent intermediates moved to qc/evidence/.
- No em-dashes anywhere in deliverable text (hyphens only). No watermark. Palette locked to tokens in all scenes and aspects.
