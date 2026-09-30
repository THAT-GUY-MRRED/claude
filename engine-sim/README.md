# Renault RS27-2012 V8 for Engine Simulator

`renault_rs27_2012.mr` is a script for [AngeTheGreat's Engine Simulator](https://github.com/ange-yaghi/engine-sim)
(v0.1.x). It models the 2.4 L 90° flat-plane V8 from the 2012 Lotus E20, paired with
an E20-like car and a 7-speed gearbox.

## Install

1. Copy `renault_rs27_2012.mr` into `assets/engines/` in your Engine Simulator folder.
2. Edit `assets/main.mr` so the engine import points at it:

   ```
   import "engine_sim.mr"
   import "themes/default.mr"
   import "engines/renault_rs27_2012.mr"

   use_default_theme()
   main()
   ```
3. Launch the app (or press `R` in-app to reload scripts).

## What's real and what's guessed

| Value | Source |
|---|---|
| 2400 cc, 8 cyl, 90° V, 98 mm bore | FIA regs / Renault |
| 39.8 mm stroke | calculated from the above |
| 18,000 rpm rev limit & redline | FIA regs |
| 250 g piston | Renault |
| 640 kg car, 7 gears | FIA regs |
| Flat-plane crank, 1-5-3-7-4-8-2-6 firing order | estimate |
| ~13.5:1 compression (24 cc chamber) | estimate |
| 100 mm rod, 14 mm compression height, 300 g rod | estimate |
| Cams, head flow, intake/exhaust sizes, ignition map | estimate, tuned for ~750 bhp at the limiter |
| Gear/diff ratios, drag | estimate (~320 km/h in 7th) |

Renault never published the internal geometry, cams or port data, so the power curve
and sound are an approximation, not a replica. Full sourced specs are in
`Renault_RS27-2012_V8_specs.txt`.

## Tuning tips

- `simulation_frequency` is 24000 to keep 18,000 rpm stable. If the sim stutters, lower it
  (or use the in-app frequency controls); if it sounds harsh at the limiter, raise it.
- Too much / too little power: adjust `flow_attenuation` on the heads, or the cam `lift` and
  `duration_at_50_thou`.
- F1 engines idle around 4,000-5,000 rpm. Idle speed is set by `idle_throttle_plate_position`
  in the `intake` block (lower = higher idle).
- Crank inertia is very low, as on the real engine, so revs rise and fall very fast.
