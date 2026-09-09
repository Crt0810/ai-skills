# Origin Scientific Plot V5

This release hardens the single-panel execution script against common configuration
and Origin automation failures.

Fixed/default values:
- canvas: 250 x 250 mm
- panel: 110 x 85 mm, centered
- font: Times New Roman
- text size: 26 pt
- axis/frame width: 1.5 pt
- major tick length: 8 pt
- minor ticks: off
- curve width: 2 pt
- curve colors: red -> blue -> green

V5 changes:
- Missing/null required YAML values are resolved against built-in defaults.
- YAML syntax and geometry are validated before Origin starts.
- Empty/missing color sequences fall back to red/blue/green.
- N_in=0 is preserved correctly.
- Missing sheet names produce a useful list of available sheets.
- Plot colors use OriginPro Plot.color instead of active-plot LabTalk.
- Legend uses plot order rather than arbitrary curve IDs.
- PDF export uses documented expGraph path + filename syntax.
- Output files are checked after save/export.
- Startup prints the fully resolved key configuration values.
