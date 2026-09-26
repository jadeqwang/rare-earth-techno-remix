# RARE EARTH — music video treatment

*Song: "Rare Earth" (Pale Blue Dot), DDR/techno version. Lyrics written in 2011 for a SETI event.
Runtime 2:08. Tempo accelerates 129.7 → 135 BPM (tracked, not constant).*

## One line

Two lonely worlds, each singing into the dark, discover the other one was listening the whole time —
and the song itself is the signal.

## The idea underneath

The lyrics are addressed from Earth to someone out there, but they read both ways:
*"You're yearning to see the life out there / Searching for me."* The other side is searching too.
The video makes that literal. Verses 1–2 are Earth asking. The build reveals a second world doing
exactly the same thing. Verse 3 is the Great Filter — the Drake equation's last term, **L**, the
lifetime of a civilization ("before they launch or self-destruct"). Verses 4–5 repeat verses 1–2
as call-and-response between the worlds. The final drop is contact, and then the camera pulls back to
show the galaxy lit up with connections: *how could we be alone.*

"Are you still there?" is not just longing — it is astrophysics. Light takes centuries between stars;
by the time a reply arrives the sender may be gone. That is why the Drake **L** matters, and why
"keep on looking, keep the faith, keep up funding" is the moral center of the song (the Allen Telescope
Array really was put into hibernation for lack of funds in 2011, the year this song was written).

"A planet's transit is not that far from my own": we find exoplanets by the dip in starlight when they
cross their star. 1,715 nearby stars sit in the *Earth Transit Zone* and could have watched **our**
transit (Kaltenegger & Faherty, Nature 2021). The other world here is fictional — **ETZ-1715 b**, named
after that count — a world that saw us the same way we saw it.

## Characters and worlds

**DOT** — the voice of the pale blue dot. 20, night-shift radio-observatory listener and singer.
Long straight black hair with a centre part and long curtain bangs (revision v3; v1 had a hime cut with a
pale-blue under-layer), 1977-style orange-foam headphones (the year of the Wow!
signal and the Voyager Golden Record), oversized white flight jacket with a giant pale-blue dot on the
back, handheld Yagi antenna as her hero prop. Signature: a pale-blue dot catchlight in each eye.
Point moves: **LISTEN** (hand cupped to ear, eyes up), **BLINK** (hands flash open/closed like a
twinkling star), **TRANSIT** (index finger crosses in front of her eye), **ANTENNA** (Yagi raised like a sword).

**Earth locations** — Sutro Tower above Karl the Fog (San Francisco's antenna, blinking red), a 42-dish
array in a high desert valley, a 3 a.m. control room with waterfall spectrograms, a launch tower,
the Voyager pale-blue-dot sunbeam, the night side of Earth.

**ETZ-1715 b** — never its inhabitants, only its scale: a ringed super-Earth under a coral sun,
magenta sky, terraced ring-cities over waterfalls, a space elevator, a listening field of petal dishes
linked by mint light, orbital rings, a signal tower above violet cloud. Zoomed out, always.

## Visual language — SIGNAL PRINT

A moving risograph anime. Every frame is built from a handful of spot-color inks, black ink linework,
halftone shading, slight plate misregistration and paper grain. When the signal is strong the print
**lights up**: linework turns to neon on black with bloom. *Paper → light* is the arc of the whole video
(verses print, drops glow, the finale is pure light).

| Ink | Hex | Use |
|---|---|---|
| Klein Blue | `#1F2BD1` | Earth night |
| Beacon Orange | `#FF5A1F` | Earth warmth, aviation lights, DOT's stripe |
| Pale Blue Dot | `#9CCBFF` | Earth, DOT |
| Fluo Pink | `#FF48B0` | the other world's sky |
| Mint Signal | `#3FE0C5` | the other world's light |
| Signal Yellow | `#FFE14D` | contact |
| Ink | `#0B0B14` | line, night |
| Paper | `#F3EFE6` | stock, highlights |

Earth shots use Klein + Orange + Pale Blue. ETZ-1715 b uses Fluo Pink + Mint + Ink. Contact is Yellow on black.

**Rotoscope method.** Seedance 2.5 generates the performances and organic physics (hair, cloth, fog,
exhaust, crowds). Those clips are never shown. The JS renderer reads them as guides — edges, tone
bands, mattes — and redraws every frame as ink, halftone and light in the palette above, with the
character on twos (12 fps drawings) and camera/type/effects on ones, like hand-drawn anime.
Planets, dish arrays, the space elevator, signals, UI and all typography are procedural.

## Typography

* **Lyrics huge at the start** (the hook): heavy extended grotesk, word-by-word on the sung syllable,
  left two-thirds of frame, DOT on the right third.
* **Verse 2**: key words big (PALE BLUE DOT, SIGNAL, STAR, TRANSIT, ALONE), the rest as elegant subtitles.
* **Verse 3**: brutalist — monospace terminal lines, headline slams, a censor bar at the blank.
* **Verse 4–5**: the same lyrics arrive first as ETZ glyphs and *decode* into English — the song was received.
* **Title card** "RARE EARTH / 稀有地球 / Уникальная Земля" drops on the first drop, anime-OP style. Both
  translations mean Earth the planet, as in the Rare Earth hypothesis, not rare-earth metals (稀土 /
  редкоземельные). The Russian is the hypothesis's established name («гипотеза уникальной Земли»). The ETZ-1715 b chapter card reads 第二地球 / Вторая Земля, "a second Earth".
* UI: `RX 1420.40575 MHz`, SNR, drift, latency — the hydrogen line SETI listens on.

## Motion rules

* The beat grid is law: cuts on beats (half-beats in drops), big changes on phrase downbeats.
* Text hits on the sung syllable onsets (word timings aligned from the vocal stem).
* Kick = halftone dots swell; snare = misregistration jolt; drops open with an **impact frame**.
* Character drawings on twos; camera, type and FX on ones.
* The blank at 61.03–61.45 s ("and now we're ‑‑‑") is a true void: black frame, censor bar, nothing else.

## Arc and time budget

| Section | Time | World | Mode |
|---|---|---|---|
| Cold open | 0:00–0:03 | Earth | print |
| V1 asking | 0:03–0:18 | Earth | print, huge type |
| V2 the signal | 0:18–0:40 | Earth | print |
| Build: the other world | 0:40–0:54 | ETZ-1715 b | print → glow |
| Drop 1 / V3: the filter, keep looking | 0:54–1:15 | both | light + brutalist |
| Drop 2a / V4: call and response | 1:15–1:30 | both, alternating | light |
| Drop 2b / V5: arrival | 1:30–1:52 | both, mirrored | light + print |
| Final drop: contact | 1:52–2:03 | both → galaxy | pure light |
| Outro | 2:03–2:08 | two dots | print |

Earth ≈ 50%, ETZ-1715 b ≈ 30%, the space between (signal, galaxy) ≈ 20%.

## Zeitgeist anchors (why this lands in 2026)

Artemis II's *Earthset* photographs (April 2026) made the pale blue dot new again; *Project Hail Mary*
made first contact through music a blockbuster idea; *KPop Demon Hunters* made K-pop × anime the
dominant pop-animation language; SF tech Twitter knows Sutro Tower, Karl the Fog, the Wow! signal,
the Drake equation, Dyson-sphere and Kardashev memes, and the fight over science funding.
The video speaks to all of it without naming any of it.
