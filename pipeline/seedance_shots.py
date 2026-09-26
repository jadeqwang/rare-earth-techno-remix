"""Seedance 2.5 base-footage plan for RARE EARTH.

Every clip here is a *guide* for the JS rotoscope renderer; none of it is shown directly.
t0/dur are song times: the reference audio is the song (vocal stem, or instrumental for dance)
cut to exactly [t0, t0+dur], so a verified clip drops into the timeline at t0.

bg: "context" = drawn in its environment (print-mode shots); "green" = chroma-key green screen
(light-mode shots composited over procedural JS backgrounds).
"""

# character revision: v2 = hime cut with a pale-blue under-layer; v3 = centre part, long curtain bangs, layered
HAIR = "v3"
STYLE = (" Clean modern anime style, crisp black lineart, flat cel shading, faithful to the character"
         " reference sheet (DOT: long straight black hair with a centre part, long curtain bangs framing her face,"
         " long layered slightly choppy ends past her shoulders, no blunt fringe; orange foam"
         " headphones, cropped white flight jacket with orange stripe and a big pale-blue dot on the back,"
         " black crop top, navy cargo pants). No text, no subtitles, no logos.")
SING = " She sings the words of the reference audio with precise, clearly articulated lip sync."
GREEN = (" Background: a plain, flat, evenly lit solid chroma-key green screen (#00FF00) filling the whole"
         " frame, with nothing else in it.")

DOT = "/tmp/work/sd/dot_sheet_v3.jpg"       # design/dot_character_sheet.jpg (v2 hime-cut sheet: dot_character_sheet_v2_hime.jpg)
TOWER = "/tmp/work/refs/env_tower_top.jpg"
SUTRO = "/tmp/work/refs/env_sutro_fog.jpg"
ROOM = "/tmp/work/refs/env_control_room.jpg"
CITY = "/tmp/work/refs/env_other_city.jpg"
PETALS = "/tmp/work/refs/env_petal_field.jpg"
OTOWER = "/tmp/work/refs/env_other_tower.jpg"

SHOTS = [
    # ---------------- cold open + verse 1 (print, Earth, night, tower above the fog)
    dict(id="sd01_tower_back", t0=0.0, dur=6, audio=None, bg="context", refs=[DOT, TOWER], takes=2,
         prompt="Back view of DOT standing alone on the small top platform of a tall red-and-white radio antenna tower at night,"
                " far above a rolling sea of fog lit orange by the city beneath it. The big pale-blue circle on the back of her"
                " white jacket is clearly visible. Strong wind blows her long black hair and jacket. She slowly raises a small"
                " handheld Yagi antenna toward one bright star in the upper left of the sky. Blinking red aviation lights, Milky Way."
                " The camera slowly pushes in from behind her."),
    dict(id="sd02_cu_yearning", t0=5.2, dur=4, audio="voc", bg="context", refs=[DOT, TOWER], takes=2,
         prompt="Close-up of DOT on the top platform of a red-and-white antenna tower at night far above the fog, three-quarter"
                " view from her left; she looks up and off to the left at the stars, singing with longing, wind lifting her hair so"
                " the pale-blue under-layer flashes, orange foam headphones around her neck, cool blue night light and warm orange"
                " city glow from below." + SING),
    dict(id="sd03_mcu_listen", t0=10.4, dur=4, audio="voc", bg="context", refs=[DOT, TOWER], takes=2,
         prompt="Medium close-up of DOT facing the camera on the antenna tower platform at night; as she sings she cups her right"
                " hand behind her right ear in a listening gesture and tilts her head up toward the sky, eyes searching the stars,"
                " wind in her hair, fog and city glow far below." + SING),
    dict(id="sd04_wide_pullback", t0=12.7, dur=5, audio=None, bg="context", refs=[DOT, SUTRO], takes=2,
         prompt="Epic aerial drone shot at night: starting close behind DOT standing on the very top of a red-and-white"
                " three-pronged TV antenna tower, the camera pulls back and rises fast, revealing the whole tower rising out of an"
                " ocean of fog glowing orange from the city lights underneath, the tops of the Golden Gate Bridge towers poking"
                " through the fog in the distance, a sky full of stars."),
    # ---------------- verse 2
    dict(id="sd05_console_caught", t0=21.5, dur=4, audio="voc", bg="context", refs=[DOT, ROOM], takes=2,
         prompt="3 a.m. in a small radio-observatory control room: DOT sits at a desk in front of glowing monitors showing blue"
                " waterfall spectrograms with one bright vertical line. She wears the orange foam headphones ON her ears and presses"
                " them with both hands, her eyes widening in disbelief and wonder. Blue monitor light on her face. Medium close-up,"
                " slow push-in." + SING),
    dict(id="sd06_blink", t0=25.0, dur=4, audio="voc", bg="context", refs=[DOT, TOWER], takes=2,
         prompt="Medium shot of DOT facing the camera on the antenna tower platform at night; while singing she raises both hands"
                " beside her face and rhythmically flashes her fingers open and closed like twinkling stars, in time with the"
                " music, bright and playful, hair blowing." + SING),
    dict(id="sd07_transit", t0=30.0, dur=6, audio="voc", bg="context", refs=[DOT, TOWER], takes=2,
         prompt="Close-up of DOT's face at night, stars behind her: she slowly draws her index finger horizontally across in front"
                " of her eye, like a tiny planet crossing a star, then lowers her hand and looks into the camera with a tender,"
                " hopeful expression." + SING),
    dict(id="sd08_alone", t0=35.5, dur=5, audio="voc", bg="context", refs=[DOT, TOWER], takes=2,
         prompt="Wide low-angle shot: DOT stands on the top platform of the antenna tower, arms opening toward a sky full of"
                " stars, singing to the heavens; the camera cranes slowly up and around her, fog glowing below. Epic and lonely." + SING),
    # ---------------- drop 1 / verse 3 (light mode, green screen)
    dict(id="sd09_keep_looking", t0=61.4, dur=4, audio="voc", bg="green", refs=[DOT], takes=2,
         prompt="Medium shot of DOT in a powerful stance: she thrusts the handheld Yagi antenna straight up like a sword, hair"
                " whipping, then turns to the camera, fierce and determined." + SING + GREEN),
    dict(id="sd10_vision", t0=71.0, dur=5, audio="voc", bg="green", refs=[DOT], takes=2,
         prompt="Centered medium shot of DOT singing powerfully, one hand on her chest, the other reaching toward the camera, eyes"
                " shining with conviction, hair moving." + SING + GREEN),
    # ---------------- drop 2a / verse 4 (light mode, green screen)
    dict(id="sd11_care", t0=75.0, dur=4, audio="voc", bg="green", refs=[DOT], takes=2,
         prompt="Close-up of DOT singing directly into the camera with intense emotion, strong white rim light, hair moving." + SING + GREEN),
    dict(id="sd12_search_listen", t0=81.0, dur=4, audio="voc", bg="green", refs=[DOT], takes=2,
         prompt="Medium shot of DOT performing a sharp K-pop point move: she snaps her head left, then right, searching, then cups"
                " her hand behind her ear to listen, singing." + SING + GREEN),
    # ---------------- drop 2b / verse 5
    dict(id="sd13_caught_reply", t0=93.3, dur=4, audio="voc", bg="context", refs=[DOT, TOWER], takes=2,
         prompt="Close-up of DOT on the antenna tower platform at night: she looks up as a soft mint-green light falls on her face"
                " from the sky, astonished and joyful, hair lifting in the wind." + SING),
    dict(id="sd14_blink_dance", t0=97.2, dur=4, audio="voc", bg="green", refs=[DOT], takes=2,
         prompt="Medium shot of DOT dancing rhythmically, both hands flashing open and closed beside her face like twinkling stars,"
                " bouncing to the beat, singing." + SING + GREEN),
    dict(id="sd15_own_ecu", t0=102.8, dur=5, audio="voc", bg="context", refs=[DOT, TOWER], takes=2,
         prompt="Extreme close-up of DOT's face at night, eyes glistening with tears but smiling, a soft pale-blue light in her"
                " eyes, stars softly out of focus behind her." + SING),
    dict(id="sd16_alone_beam", t0=107.5, dur=5, audio="voc", bg="context", refs=[DOT, TOWER], takes=2,
         prompt="DOT on the top platform of the antenna tower at night seen from behind and slightly to the side: she raises the"
                " handheld Yagi antenna to the sky as a column of mint light descends from the stars toward her; the camera orbits"
                " around her; fog glowing below." + SING),
    # ---------------- final drop (instrumental dance break, green screen)
    dict(id="sd17_dance_a", t0=112.0, dur=6, audio="inst", bg="green", refs=[DOT], takes=2,
         prompt="Full-body shot of DOT performing an energetic, razor-sharp K-pop dance break that hits every beat of the reference"
                " music: powerful arm hits, a quick spin, hair flying; her whole body stays in frame." + GREEN),
    dict(id="sd18_dance_b", t0=118.0, dur=6, audio="inst", bg="green", refs=[DOT], takes=2,
         prompt="Full-body shot of DOT continuing a sharp K-pop dance to the beat of the reference music, finishing in a strong"
                " final pose with the handheld Yagi antenna raised high overhead; her whole body stays in frame." + GREEN),
    # ---------------- environments (no characters)
    dict(id="se01_fog_tower", t0=0.0, dur=5, audio=None, bg="context", refs=[SUTRO], takes=1,
         prompt="Night timelapse: thick fog pours over the hills of San Francisco like a slow waterfall, a tall red-and-white"
                " three-pronged TV antenna tower rises above the fog with blinking red lights, city lights glow orange beneath the"
                " fog, stars overhead. Anime background art, no people."),
    dict(id="se02_launch", t0=0.0, dur=5, audio=None, bg="context", refs=[], takes=1,
         prompt="A giant stainless-steel rocket lifts off from a coastal launch tower at blue hour: huge billowing exhaust clouds,"
                " a blinding flame, steel catch-arms of the tower swinging away, camera tilting up with the rocket. Anime"
                " background art style, no people, no text."),
    dict(id="se03_crowd_lights", t0=0.0, dur=5, audio=None, bg="context", refs=[], takes=1,
         prompt="Seen from behind, a huge crowd on a grassy hillside in San Francisco at night holds thousands of glowing phone"
                " lights up toward the stars, the lights waving slowly in unison like a K-pop concert light-stick ocean, city and"
                " fog below. Anime background art style, no text."),
    dict(id="se04_other_city", t0=0.0, dur=5, audio=None, bg="context", refs=[CITY], takes=1,
         prompt="Aerial flyover at golden hour of an alien terraced city of stacked white ring-shaped buildings with mint lights"
                " on cliffs with waterfalls; a luminous space-elevator tether rises from the city into a magenta sky past a giant"
                " planetary ring; a huge coral sun on the horizon. No people or creatures. Anime background art."),
    dict(id="se05_petal_field", t0=0.0, dur=5, audio=None, bg="context", refs=[PETALS], takes=1,
         prompt="At night on an alien plain, hundreds of flower-like white radio dishes with six petals open their petals in a"
                " wave and all turn toward the same point in the starry sky; thin mint light lines connect them. No people or"
                " creatures. Anime background art."),
]
