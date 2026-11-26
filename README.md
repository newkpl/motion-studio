# MOTION STUDIO - technical cinema rebuild

A 51.5 second deterministic motion piece presenting 11 open-source motion
libraries. Dark technical-cinema direction: base #0B0D10, off-white #F2F0EA,
one accent #FF4D2E, muted gray #8A8F98. No cards, no pastel, no watermark.
Every demo is monochrome plus the single accent.

## Deliverables

- output/motion-studio-cinema-1920x1080.mp4 (main)
- output/motion-studio-cinema-1080x1920.mp4 (portrait)
- output/motion-studio-cinema-1080x1080.mp4 (square)
- output/score.wav (the synthesized score, before AAC muxing)

All three videos: H.264 + AAC 160k, 30 fps, 1545 frames, 51.5 s.
Rendered at 1.5x supersample and downscaled with lanczos for crisp type.

## Production workflow

1. Design tokens live in exactly one file, src/tokens.py: palette, type
   scale, 12-column grid, 96 px safe margin, easing curves. Every scene
   reads only tokens.
2. src/timeline.py is the single source of truth for the edit: segment
   order, durations, transitions, star counts, the Tone.js step grid.
   All segment lengths are multiples of 15 frames (120 BPM, one beat =
   0.5 s = 15 frames), so every cut lands on the beat grid.
3. src/engine.py is the deterministic canvas: frame number is the only
   clock; every animation is a pure function of the frame index. It also
   provides the RK4 spring integrator, seeded value noise, the software
   3D helpers, camera moves and the transitions (accent cover-reveal
   block wipe, whip pan with motion blur, type scale-through, hard cut).
   Every text draw registers (text, bbox, font size, color, background)
   into a layout registry used by QC.
4. src/scenes.py holds one draw function per segment plus shared
   header/footer components. src/lottie.py is a minimal Bodymovin
   player (layers, keyframed trim paths and transforms with cubic-bezier
   easing) that reads assets/heart-pulse.json at render time.
5. src/audio.py synthesizes the score offline in numpy on the same
   timeline: a kick on frame 0 and on every cut, beat pulses and offbeat
   hats under hero scenes, a riser into each chapter beat, pluck notes
   on the Tone.js step grid, and one hit on the closing lockup.
6. src/render.py streams frames into ffmpeg (no frames held in RAM).
   The same code renders all three aspects; layout adapts through the
   token/grid system (portrait stacks, square centers, footers auto-fit,
   the closing grid re-columns).
7. QC: src/qc.py checks the layout registry (margins, overlaps, minimum
   font size, WCAG contrast); src/sync_check.py extracts the muxed audio
   and verifies a transient within plus/minus 1 frame of every cut, the
   lockup hit and every Tone.js pluck step; frame-hash runs check for
   duplicated frames. Three full QC iterations were run on the main
   render (see NOTES.md), plus a midpoint visual audit of both variants.

Rebuild everything:

    cd src
    python3 audio.py ../output/score.wav
    python3 render.py --w 1920 --h 1080 --ss 1.5 --out ../output/main-silent.mp4 --registry ../qc/registry.json
    ffmpeg -i ../output/main-silent.mp4 -i ../output/score.wav -c:v copy -c:a aac -b:a 160k -shortest ../output/motion-studio-cinema-1920x1080.mp4

## Timeline (30 fps, 1545 frames, 51.5 s)

| segment | frames | time | transition in |
|---|---|---|---|
| cold open | 0-119 | 0.0-4.0 s | - |
| chapter 01 MOTION | 120-149 | 4.0-5.0 s | wipe |
| anime.js | 150-254 | 5.0-8.5 s | wipe |
| react-spring | 255-359 | 8.5-12.0 s | whip |
| PixiJS | 360-464 | 12.0-15.5 s | wipe |
| chapter 02 DATA | 465-494 | 15.5-16.5 s | wipe |
| D3 | 495-614 | 16.5-20.5 s | wipe |
| chapter 03 2D/3D | 615-644 | 20.5-21.5 s | wipe |
| p5.js | 645-749 | 21.5-25.0 s | wipe |
| Motion Canvas | 750-854 | 25.0-28.5 s | scale |
| Lottie Web | 855-959 | 28.5-32.0 s | wipe |
| Blender | 960-1064 | 32.0-35.5 s | wipe |
| three.js | 1065-1169 | 35.5-39.0 s | whip |
| chapter 04 VIDEO/SOUND | 1170-1199 | 39.0-40.0 s | wipe |
| Remotion Skills | 1200-1304 | 40.0-43.5 s | scale |
| Tone.js | 1305-1424 | 43.5-47.5 s | cut (keeps the step grid sample-aligned) |
| closing + lockup | 1425-1544 | 47.5-51.5 s | wipe |

Lockup hit at frame 1485 (49.5 s). Chapters: MOTION (anime.js,
react-spring, PixiJS), DATA (D3), 2D/3D (p5.js, Motion Canvas, Lottie
Web, Blender, three.js), VIDEO/SOUND (Remotion Skills, Tone.js).

## Honesty notes

- three.js is one of the 11 libraries. The original brief listed
  "11 hero scenes plus three.js", which double-counts it; the film has
  exactly 11 hero scenes, one per library, three.js included.
- Blender is an honest stand-in: there is no Blender in this pipeline.
  The scene renders our own software 3D (numpy): a subdivided
  icosahedron rotating in a viewport, wireframe in the first half,
  flat-shaded with a single light in the second. The README is the only
  place this is stated; nothing in the video claims otherwise beyond the
  normal title, code line and star elements every scene carries.
- Every demo is a faithful implementation of the library's own
  algorithm inside this deterministic renderer, not footage of the
  library running in a browser: the react-spring curve is an RK4
  integration of the actual spring (mass 1, tension 170, friction 13);
  the Remotion title is driven by the same kind of spring evaluated at
  the displayed frame number; the Motion Canvas node's eased progress
  is exactly the playhead position on its timeline; the D3 sequence
  interpolates one dataset through bars, line and treemap states.
- Lottie is real playback: assets/heart-pulse.json is a genuine
  Bodymovin file (trim-path keyframes, pulse, rotating ring), parsed
  and rendered per frame by the built-in minimal player in
  src/lottie.py.
- The score is synthesized offline in numpy on the Tone.js scene's own
  step grid (120 BPM, 8 steps); it is not Tone.js rendering audio in a
  browser. The steps that light in the Tone.js scene are the steps that
  sound, verified by the sync check.

## QC summary

- Iteration 1: 62 layout defects (spring readout margins/overlap,
  Motion Canvas node margins, closing flight frames), 1 sync miss at
  frame 0 (a detector artifact, fixed by padding the analysis window),
  1 duplicated frame, plus 5 visual defects. All fixed.
- Iteration 2: layout PASS, sync PASS (all 23 targets within 11 ms of
  their cut, tolerance 33.3 ms), 1 duplicated frame left (spring tail).
  Fixed with a marching target line.
- Iteration 3 (main final): layout PASS, sync PASS, 1545 frames with
  zero duplicated consecutive frames. Variant audit then found 8
  aspect-adaptation defects (footer fit, Blender stacking, three.js
  focal length, closing columns, anime grid pitch, header title fit,
  Remotion panel stacking with a wrapped code variant for square,
  chapter progress list position); all fixed in aspect-conditional
  branches that leave the 1920x1080 output pixel-identical, and both
  variants were re-rendered and re-checked at scene midpoints.
  Sync re-verified PASS on the portrait file as well.
- Documented QC exceptions: cold-open kinetic letters may overlap
  during their scale-through (the registry skips that segment's
  overlap test); closing names intentionally enter from off-frame
  during assembly (margin test skipped until they land); the dimmed
  closing grid sits under the lockup by design.

## Repo notes

Font binaries under assets/fonts/ are not included in this upload (GitHub connector pushes text only); the renderer expects Space Grotesk and JetBrains Mono TTFs there. The rendered videos live in output/.
