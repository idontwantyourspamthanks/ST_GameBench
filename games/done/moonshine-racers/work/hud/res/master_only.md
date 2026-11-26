### Master table per scene (stock game; cycles per pass, class means; the ticker's two 34.9 k erase passes per message are not in these means)


**race_start (driving)** (pass work: none 846,003 (n=38), typing 874,742 (n=54))

| element | routine | cycles/pass none (% of pass) | cycles/pass typing (% of pass) | redraw rule | bytes written | safe to skip? |
|---|---|---:|---:|---|---:|---|
| thermometer | `efc6` | 152 (0.0 %) | 1,089 (0.1 %) | on change of `$10ba`, 2 redraws per change | 752 | yes (clear 0,18-31,64 once) |
| engine-fire puff | `f1c0`+`f134` | 288 (0.0 %) | 377 (0.0 %) | only while `$10ba>=35` | 52 | yes |
| minimap box fill | `f214` | 9,068 (1.1 %) | 8,771 (1.0 %) | every pass | 1,152 | yes (clear once) |
| minimap | `f22c` | 54,366 (6.4 %) | 53,946 (6.2 %) | every pass | 568 | yes (clear once) |
| score | `f3b6` | 36,362 (4.3 %) | 35,475 (4.1 %) | when `$11c2` changes (every pass while driving), 2x | 336 | yes (clear once) |
| position no. | `f430` | 171 (0.0 %) | 364 (0.0 %) | when `$10ca` changes, 2x | 224 | yes |
| stopwatch dial | `f53c` | 9,859 (1.2 %) | 9,806 (1.1 %) | whole-long compare: every pass while the clock runs | 496 | yes (clear once) |
| message ticker | `11ef0` | 84 (0.0 %) | 7,437 (0.9 %) | 1 glyph/pass while typing (+1 repeat), 2 x box erase at the end | 40-48 per glyph; 4,704 erase | **NO** (race-end state machine); drawing only |
| talking face | `f90c` | 96 (0.0 %) | 12,279 (1.4 %) | every pass while a message is active | 768 | yes |
| turbo-fuel cup | `f620` | 10,450 (1.2 %) | 10,278 (1.2 %) | every pass (road erases it) | 328 | yes, clean |
| gear lever | `f76a` | 11,335 (1.3 %) | 11,076 (1.3 %) | every pass (road erases it) | 172 | yes, clean |
| speedometer | `f7f0` | 19,332 (2.3 %) | 18,943 (2.2 %) | every pass (road erases it) | 588 | yes, clean |
| **HUD total** | 13 calls | **151,563 (17.9 %)** | **169,840 (19.4 %)** | | | |

**race_grid (standing, time-out state)** (pass work: none 761,422 (n=34), typing 777,565 (n=90))

| element | routine | cycles/pass none (% of pass) | cycles/pass typing (% of pass) | redraw rule | bytes written | safe to skip? |
|---|---|---:|---:|---|---:|---|
| thermometer | `efc6` | 172 (0.0 %) | 172 (0.0 %) | on change of `$10ba`, 2 redraws per change | 752 | yes (clear 0,18-31,64 once) |
| engine-fire puff | `f1c0`+`f134` | 276 (0.0 %) | 328 (0.0 %) | only while `$10ba>=35` | 52 | yes |
| minimap box fill | `f214` | 8,571 (1.1 %) | 8,495 (1.1 %) | every pass | 1,152 | yes (clear once) |
| minimap | `f22c` | 49,961 (6.6 %) | 49,162 (6.3 %) | every pass | 568 | yes (clear once) |
| score | `f3b6` | 128 (0.0 %) | 128 (0.0 %) | when `$11c2` changes (every pass while driving), 2x | 336 | yes (clear once) |
| position no. | `f430` | 941 (0.1 %) | 445 (0.1 %) | when `$10ca` changes, 2x | 224 | yes |
| stopwatch dial | `f53c` | 168 (0.0 %) | 168 (0.0 %) | whole-long compare: every pass while the clock runs | 496 | yes (clear once) |
| message ticker | `11ef0` | 84 (0.0 %) | 7,123 (0.9 %) | 1 glyph/pass while typing (+1 repeat), 2 x box erase at the end | 40-48 per glyph; 4,704 erase | **NO** (race-end state machine); drawing only |
| talking face | `f90c` | 96 (0.0 %) | 12,107 (1.6 %) | every pass while a message is active | 768 | yes |
| turbo-fuel cup | `f620` | 10,243 (1.3 %) | 11,149 (1.4 %) | every pass (road erases it) | 328 | yes, clean |
| gear lever | `f76a` | 11,250 (1.5 %) | 13,170 (1.7 %) | every pass (road erases it) | 172 | yes, clean |
| speedometer | `f7f0` | 21,555 (2.8 %) | 19,629 (2.5 %) | every pass (road erases it) | 588 | yes, clean |
| **HUD total** | 13 calls | **103,446 (13.6 %)** | **122,075 (15.7 %)** | | | |
