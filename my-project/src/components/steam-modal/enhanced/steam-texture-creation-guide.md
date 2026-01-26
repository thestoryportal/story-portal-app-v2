# Steam Texture Creation Guide - Quick Reference

## Overview
Creating high-quality steam textures is the single most important upgrade for achieving AAA visual quality. This guide provides step-by-step instructions for multiple creation methods.

---

## Method 1: Substance Designer (Best Quality, Procedural)

### Required Software
- Substance Designer (Free trial available: https://www.adobe.com/products/substance3d-designer.html)

### Step-by-Step Process

**1. Create New Graph**
- File → New Substance Graph
- Set output size to 512x512
- Name: "steam_wispy_01"

**2. Build Node Network**

```
[Perlin Noise] 
  ↓ Scale: 4
  ↓
[Directional Warp] ← [Clouds 2] (as intensity)
  ↓ Intensity: 0.3
  ↓
[Gradient Linear 1] (vertical)
  ↓
[Blend] (mode: Multiply)
  ↓
[Histogram Scan]
  ↓ Position: 0.35, Contrast: 0.7
  ↓
[Blur HQ]
  ↓ Intensity: 0.15
  ↓
[OUTPUT: Base Color (Grayscale)]
[OUTPUT: Opacity (same connection)]
```

**3. Export Settings**
- Format: PNG
- Size: 512x512
- Color Space: sRGB
- Bit Depth: 16-bit
- Alpha: Yes
- File name pattern: `steam_${graph}_${identifier}.png`

**4. Create Variations**
- Adjust Perlin Noise scale: 3, 5, 7
- Vary Directional Warp angle: 0°, 45°, 90°, 135°
- Change Histogram Scan position: 0.25-0.45
- Mix in different noise types (Cellular, FBM, Fracsum)

**5. Batch Export**
- Create 8-10 variations
- Use Exposed Parameters for quick iteration
- Export all as 512x512 PNG with alpha

### Parameter Presets

**Wispy Tendrils:**
- Noise Scale: 7-10
- Warp Intensity: 0.4-0.5
- Histogram Position: 0.25
- Blur: 0.1

**Dense Clouds:**
- Noise Scale: 3-4
- Warp Intensity: 0.2-0.3
- Histogram Position: 0.4
- Blur: 0.2

**Swirling Forms:**
- Noise Scale: 5-6
- Warp Intensity: 0.5-0.7 (high!)
- Add Transformation 2D node with rotation
- Histogram Position: 0.35

---

## Method 2: Blender (3D Smoke Simulation)

### Setup (5 minutes)

**1. New Scene**
- Delete default cube
- Add → Quick Effects → Quick Smoke
- This creates Domain + Flow objects

**2. Domain Settings**
- Resolution Divisions: 256 (higher = better quality, slower)
- Time Scale: 0.5 (slower dissipation)
- Vorticity: 0.1 (adds swirl)
- Dissolve: 50 frames

**3. Flow Settings**
- Flow Type: Smoke
- Flow Behavior: Inflow
- Sampling Substeps: 2
- Surface Emission: 1.5

**4. Camera Setup**
- Add Camera (Shift+A → Camera)
- Position: (0, -8, 2)
- Rotation: (80°, 0°, 0°)
- Focal Length: 50mm

**5. Lighting**
- Add Area Light behind smoke
- Energy: 500
- Size: 5x5

### Rendering Steam Sprites (10 minutes per frame)

**1. Render Settings**
- Engine: Cycles
- Samples: 128 (minimum for clean alpha)
- Transparent background: Enable
- Film → Transparent: Check

**2. Shader Setup for Smoke**
```
[Volume Scatter]
  ↓
[Volume Absorption] 
  ↓ (Mix)
[Add Shader]
  ↓
[Material Output → Volume]
```

**3. Bake Simulation**
- Physics Properties → Cache → Bake
- Wait 2-10 minutes depending on resolution
- Scrub timeline to find good frames (typically 15-60)

**4. Render Single Frames**
- Find frames with interesting shapes
- Render → Render Image (F12)
- Save as PNG with alpha: Image → Save As
- Filename: `steam_blender_frame_025.png`

**5. Batch Process 10 Frames**
- Frames 15, 22, 30, 38, 45, 52, 60, 68, 75, 82
- Render each, save with sequential names

### Post-Processing in Blender Compositor

**1. Add Nodes:**
```
[Render Layers]
  ↓
[Color Balance] (warm tint: +10% red/yellow)
  ↓
[Blur] (X: 2px, Y: 2px)
  ↓
[Composite]
```

**2. Export**
- Render → Render Animation (or single frame)
- Output Properties → Format: PNG, RGBA
- Color Depth: 16-bit

---

## Method 3: Photoshop + Real Photos (Fastest)

### Equipment Needed
- Camera (phone camera OK)
- Dark background (black foam board)
- Kettle or humidifier
- Bright light from side

### Photography Setup

**1. Environment**
- Dark room
- Black background 2-3 feet behind steam source
- Single bright light at 45° angle
- Camera 3-4 feet from steam

**2. Camera Settings**
- ISO: 800-1600
- Shutter: 1/250s or faster
- Aperture: f/4-f/5.6
- Focus: Manual, on steam column
- Shoot RAW if possible

**3. Capture**
- Let steam stabilize for 30 seconds
- Take 50-100 photos in burst mode
- Vary light position and intensity
- Move steam source slightly between bursts

### Photoshop Processing (5 minutes per texture)

**1. Open RAW Image**
- Camera Raw: Increase Exposure +1, Contrast +20
- Convert to Grayscale: Image → Mode → Grayscale

**2. Isolation**
- Select → Color Range → Shadows
- Invert selection (Select → Inverse)
- Layer → Layer Mask → Reveal Selection

**3. Cleanup**
- Levels: Adjust black/white points to maximize contrast
- Curves: S-curve for definition
- Remove unwanted elements with Clone Stamp

**4. Create Alpha Channel**
- Duplicate grayscale to alpha channel
- Channels panel → Duplicate Green channel
- Rename to "Alpha"
- Adjust levels on alpha for clean edges

**5. Export**
- File → Export → Export As
- Format: PNG
- Check "Transparency"
- Resolution: 512x512 (Image Size → Resample: Bicubic Smoother)
- Save

### Batch Processing Actions

**Record Photoshop Action:**
1. Window → Actions → New Action
2. Name: "Steam Sprite Process"
3. Record:
   - Image → Mode → Grayscale
   - Image → Adjustments → Levels (adjust)
   - Select → Color Range → Shadows
   - Select → Inverse
   - Layer → Layer Mask → Reveal Selection
   - Image → Image Size → 512x512
   - File → Export → Export As PNG
4. Stop recording
5. File → Automate → Batch → Apply to folder of images

---

## Method 4: After Effects (Video-Based Procedural)

### Setup (10 minutes)

**1. New Composition**
- 512x512, 30fps, 10 seconds
- Background: Black

**2. Create Particle System**
- Effect → Simulation → CC Particle World
- Settings:
  - Birth Rate: 2
  - Longevity: 5 seconds
  - Gravity: -0.3 (upward)
  - Resistance: 0.1

**3. Add Turbulence**
- Effect → Distort → Turbulent Displace
- Amount: 50
- Size: 100
- Complexity: 3
- Evolution: 2x rotations (keyframe)
- Random Seed: Vary for each export

**4. Blur & Glow**
- Effect → Blur & Sharpen → Gaussian Blur: 10px
- Effect → Stylize → Glow: 
  - Threshold: 50%
  - Radius: 30
  - Intensity: 0.5

### Rendering Sprites (2 minutes per sprite)

**1. Preview Timeline**
- Scrub to find interesting frames
- Good frames: 1:00, 2:15, 3:30, 4:45, 6:00, 7:15, 8:30

**2. Render Frame**
- Composition → Save Frame As → File
- Format: PNG Sequence
- Channels: RGB + Alpha
- Save to: `/steam_sprites/ae_frame_XXX.png`

**3. Create Variations**
- Duplicate composition 10 times
- Change Random Seeds in Turbulent Displace
- Adjust Particle World birth rate: 1.5, 2, 2.5
- Export one frame from each composition

---

## Quality Checklist

Before using textures in production, verify:

- [ ] Alpha channel is clean (no gray halos)
- [ ] Resolution is exactly 512x512 pixels
- [ ] File format is PNG with transparency
- [ ] Texture is grayscale (will be tinted by code)
- [ ] Edge fadeoff is smooth, not hard
- [ ] No visible patterns or repetition
- [ ] Texture center is not perfectly centered (organic)
- [ ] File size is 50-200KB (16-bit PNG)
- [ ] No visible compression artifacts
- [ ] Texture tiles somewhat if wrapped (optional)

---

## Texture Naming Convention

Use consistent naming:
```
steam_[type]_[variation].png

Examples:
steam_wispy_01.png
steam_wispy_02.png
steam_cloud_01.png
steam_cloud_02.png
steam_swirl_01.png
steam_swirl_02.png
steam_mist_01.png
steam_mist_02.png
```

---

## Quick Comparison: Which Method?

| Method | Time | Quality | Skill Required | Best For |
|--------|------|---------|----------------|----------|
| Substance Designer | 2-3 hours | Excellent | Medium | Procedural, iterative |
| Blender | 3-4 hours | Excellent | Medium-High | Realistic physics |
| Photoshop + Photos | 1-2 hours | Good | Low | Quick turnaround |
| After Effects | 2-3 hours | Good | Medium | Animated source material |

**Recommendation**: Start with **Photoshop + Real Photos** for fastest results, then upgrade to **Substance Designer** for maximum control and quality.

---

## Testing Your Textures

1. Open `/home/claude/steam-animation-enhanced.jsx`
2. Place textures in `/public/assets/steam/`
3. Update texture URLs in `useEffect` hook
4. Run dev server and check browser console for errors
5. Adjust texture properties based on visual results

### Common Issues & Fixes

**Problem**: Texture looks too sharp/crisp
**Fix**: Increase blur in creation process, or add ctx.filter blur in render code

**Problem**: Alpha channel has gray halo
**Fix**: Use Photoshop's "Remove White Matte" or "Remove Black Matte" in layer options

**Problem**: Texture repeats visibly
**Fix**: Create more variations (aim for 8-10 minimum)

**Problem**: File size too large (>500KB)
**Fix**: Use PNG compression tools (TinyPNG, pngquant) or reduce to 8-bit

---

## Asset Library Resources

If creating textures from scratch isn't feasible, consider:

1. **Envato Elements**: Search "steam sprite sheet" (~$16/month subscription)
2. **Unity Asset Store**: Free particle packs with steam textures
3. **OpenGameArt.org**: CC0 smoke/steam textures
4. **Kenney.nl**: Free game assets including particle sprites

**Important**: Verify license allows web use and modification.

---

## Next Steps After Creating Textures

1. Optimize textures with pngquant or TinyPNG
2. Create texture atlas if using >8 textures
3. Test on mobile devices for performance
4. Adjust particle counts based on texture complexity
5. Fine-tune blend modes in canvas context for best effect
