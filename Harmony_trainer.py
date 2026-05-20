"""
harmony_engine.py — Exhaustive chord progression generator
============================================================
Sources:
  - Temperley (2009) Kostka-Payne corpus empirical transition data (classical)
  - Hooktheory 40,000-song database (pop/rock): I=18.9%, IV=17.2%, V=15.7%, vi=14.7%
  - Functional harmony: T→S→D→T cycle, voice leading conventions
  - Rock idioms: bVII, bIII, bVI borrowing (parallel minor)
  - Jazz: ii-V-I, secondary dominants, tritone substitution
  - Blues: 12-bar structure, I7/IV7/V7

Algorithm: weighted Markov chain with:
  - Genre-specific transition matrices (classical/pop/rock/blues/jazz)
  - Difficulty gates (beginner=diatonic only, advanced=all chromatics)
  - Anti-repeat guard
  - Optional authentic cadence forcing
"""

import random
from dataclasses import dataclass, field
from typing import Optional

# ─── Chord vocabulary ─────────────────────────────────────────────────────────

@dataclass
class ChordDef:
    idx: int
    roman: str
    semitones: int        # semitones above tonic
    quality: str          # major minor dim aug dom7 maj7 min7 hdim7
    function: str         # T S D X
    difficulty: int       # 1 2 3
    description: str
    genre_tags: list = field(default_factory=list)

CHORDS = [
    # ── Diatonic major ────────────────────────────────────────────────────────
    ChordDef( 0, 'I',      0,  'major', 'T', 1, 'Tonic. Home base. Stable and resolved.',                    ['classical','pop','rock','jazz','blues']),
    ChordDef( 1, 'ii',     2,  'minor', 'S', 1, 'Supertonic minor. Pre-dominant tension.',                   ['classical','pop','rock','jazz']),
    ChordDef( 2, 'iii',    4,  'minor', 'T', 2, 'Mediant minor. Tonic function, introspective.',             ['classical','pop']),
    ChordDef( 3, 'IV',     5,  'major', 'S', 1, 'Subdominant. Departure and lift.',                         ['classical','pop','rock','blues']),
    ChordDef( 4, 'V',      7,  'major', 'D', 1, 'Dominant. Tension seeking resolution to I.',               ['classical','pop','rock','jazz','blues']),
    ChordDef( 5, 'vi',     9,  'minor', 'T', 1, 'Submediant minor. Emotional depth, relative minor.',       ['classical','pop','rock']),
    ChordDef( 6, 'vii°',  11,  'dim',   'D', 2, 'Leading-tone diminished. Strong dominant pull.',           ['classical','jazz']),
    # ── Diatonic minor (natural minor) ───────────────────────────────────────
    ChordDef( 7, 'i',      0,  'minor', 'T', 1, 'Minor tonic. Dark home.',                                  ['classical','rock','pop','blues']),
    ChordDef( 8, 'ii°',   2,   'dim',   'S', 2, 'Diminished supertonic. Pre-dominant.',                     ['classical','jazz']),
    ChordDef( 9, 'III',   3,   'major', 'T', 1, 'Mediant major in minor key. Relative major warmth.',       ['rock','pop','classical']),
    ChordDef(10, 'iv',    5,   'minor', 'S', 1, 'Minor subdominant. Dark and emotional.',                   ['classical','rock','pop','blues']),
    ChordDef(11, 'V',     7,   'major', 'D', 1, 'Dominant major (raised 7th). Strong pull home.',           ['classical','pop','rock','jazz']),
    ChordDef(12, 'v',     7,   'minor', 'D', 2, 'Dominant minor (natural 7th). Softer resolution.',         ['classical']),
    ChordDef(13, 'VI',    8,   'major', 'T', 1, 'Subtonic major in minor. Relative major area.',            ['classical','rock','pop']),
    ChordDef(14, 'VII',  10,   'major', 'X', 1, 'Subtonic major. Mixolydian modal colour.',                 ['rock','pop']),
    # ── Modal interchange / borrowed from parallel minor ──────────────────────
    ChordDef(15, 'bII',   1,   'major', 'S', 3, 'Neapolitan. Dramatic flat-two, resolves to V.',            ['classical','jazz']),
    ChordDef(16, 'bIII',  3,   'major', 'T', 2, 'Borrowed flat-three. Soulful lift from parallel minor.',   ['rock','pop']),
    ChordDef(17, 'bVI',   8,   'major', 'S', 2, 'Borrowed flat-six. Cinematic, emotional pull.',            ['rock','pop','classical']),
    ChordDef(18, 'bVII', 10,   'major', 'X', 1, 'Borrowed flat-seven. The rock anthem chord. Mixolydian.',  ['rock','pop','blues']),
    # ── Secondary dominants ───────────────────────────────────────────────────
    ChordDef(19, 'V/ii',  9,   'major', 'D', 3, 'Secondary dominant of ii. Briefly tonicises ii.',         ['classical','jazz','pop']),
    ChordDef(20, 'V/IV',  0,   'dom7',  'D', 3, 'Secondary dominant of IV. Strong approach to IV.',        ['classical','jazz','blues']),
    ChordDef(21, 'V/V',   2,   'major', 'D', 2, 'Secondary dominant of V. Intensifies dominant approach.', ['classical','pop','rock','jazz']),
    ChordDef(22, 'V/vi',  4,   'major', 'D', 2, 'Secondary dominant of vi. Tonicises relative minor.',     ['classical','pop']),
    # ── Augmented sixth chords ────────────────────────────────────────────────
    ChordDef(23, 'It+6',  6,   'aug',   'D', 3, 'Italian aug6. Chromatic pre-dominant → V.',               ['classical']),
    ChordDef(24, 'Ger+6', 6,   'dom7',  'D', 3, 'German aug6. Chromatic pre-dominant → V.',                ['classical']),
    # ── Seventh chords ────────────────────────────────────────────────────────
    ChordDef(25, 'IV7',   5,   'dom7',  'S', 2, 'Blues IV7. Core 12-bar chord.',                           ['blues','jazz']),
    ChordDef(26, 'I7',    0,   'dom7',  'T', 2, 'Blues tonic dominant 7th.',                               ['blues','jazz']),
    ChordDef(27, 'V7',    7,   'dom7',  'D', 2, 'Dominant seventh. Strongest pull to I.',                  ['blues','jazz','classical','pop','rock']),
    ChordDef(28, 'ii7',   2,   'min7',  'S', 2, 'Minor seventh supertonic. Jazz ii-V staple.',             ['jazz','pop']),
    # ── Tritone substitution ──────────────────────────────────────────────────
    ChordDef(29, 'subV',  1,   'dom7',  'D', 3, 'Tritone substitution (bII7). Jazz dominant sub → I.',     ['jazz']),
]

CHORD_BY_IDX = {c.idx: c for c in CHORDS}

# ─── Transition tables (from_idx → {to_idx: weight}) ─────────────────────────
# Weights are relative frequencies; normalised inside weighted_choice().

TRANS = {
  'classical': {
    'major': {
        0:  {1:15, 2:5,  3:22, 4:40, 5:10, 6:8,  21:5,  22:5,  20:3,  15:2},
        1:  {0:10, 4:45, 6:20, 27:15,21:5,  5:5},
        2:  {0:8,  3:25, 5:35, 4:15, 6:10, 1:7},
        3:  {0:20, 4:40, 6:15, 1:10, 5:8,  27:7},
        4:  {0:70, 5:10, 1:5,  6:5,  3:5,  2:5},
        5:  {1:30, 3:25, 4:20, 2:10, 0:10, 6:5},
        6:  {0:80, 5:10, 2:5,  1:5},
        15: {4:60, 27:25,0:15},
        19: {1:80, 5:15, 0:5},
        20: {3:75, 0:15, 25:10},
        21: {4:80, 27:15,0:5},
        22: {5:75, 0:15, 1:10},
        23: {4:70, 27:20,0:10},
        24: {4:70, 27:20,0:10},
        27: {0:65, 5:15, 1:10, 3:10},
    },
    'minor': {
        7:  {10:22,11:30,8:15, 13:12,14:8,  9:8,  12:5},
        8:  {11:50,7:15, 6:15, 27:10,9:5,  10:5},
        9:  {7:30, 10:30,13:20,11:10,14:10},
        10: {11:40,7:20, 8:15, 13:10,9:10, 14:5},
        11: {7:70, 13:12,10:8, 8:5,  9:5},
        12: {7:55, 13:15,10:15,9:10, 8:5},
        13: {10:25,8:20, 11:25,7:15, 9:10, 14:5},
        14: {7:40, 11:30,10:15,13:10,9:5},
        27: {7:65, 13:15,10:12,8:8},
        15: {11:60,27:25,7:15},
    },
  },
  'pop': {
    'major': {
        0:  {3:24, 4:21, 5:19, 1:8,  2:5,  18:10,16:5,  17:4,  22:4},
        1:  {4:50, 3:15, 0:10, 5:10, 27:10,28:5},
        2:  {3:30, 5:35, 1:15, 4:10, 0:10},
        3:  {0:38, 4:28, 5:12, 1:8,  18:7, 2:4,  17:3},
        4:  {0:32, 5:29, 3:25, 1:7,  2:4,  18:3},
        5:  {3:35, 4:25, 0:15, 1:12, 2:8,  18:5},
        6:  {0:70, 5:15, 1:15},
        16: {0:30, 5:25, 3:20, 4:15, 18:10},
        17: {0:30, 4:35, 18:20,3:15},
        18: {0:40, 3:30, 4:15, 5:10, 1:5},
        19: {1:80, 0:10, 5:10},
        21: {4:80, 27:15,0:5},
        22: {5:75, 0:15, 1:10},
        27: {0:65, 5:20, 3:10, 1:5},
        28: {27:60,4:25, 0:15},
        29: {0:70, 5:20, 3:10},
    },
    'minor': {
        7:  {13:22,9:18, 14:16,10:14,11:12,8:8,  17:5,  5:5},
        8:  {11:45,7:15, 10:15,27:15,9:10},
        9:  {7:28, 10:28,13:22,14:12,11:10},
        10: {11:35,7:22, 13:20,14:12,8:8,  9:3},
        11: {7:55, 13:18,10:12,9:10, 8:5},
        13: {10:28,7:22, 11:22,14:15,9:8,  8:5},
        14: {7:35, 11:28,13:18,10:14,9:5},
        17: {7:32, 11:28,14:22,10:18},
        27: {7:62, 13:18,10:12,9:8},
    },
  },
  'rock': {
    'major': {
        0:  {3:20, 4:18, 5:12, 18:18,1:6,  16:8, 17:6,  2:4,  6:2,  22:4,  21:2},
        1:  {4:40, 3:20, 0:15, 5:10, 18:10,27:5},
        2:  {3:30, 5:30, 4:15, 0:10, 18:10,1:5},
        3:  {0:30, 4:25, 5:10, 18:20,1:8,  17:7},
        4:  {0:35, 5:20, 3:20, 18:12,1:8,  2:5},
        5:  {3:28, 18:20,4:20, 0:15, 17:10,1:7},
        6:  {0:65, 5:20, 1:15},
        16: {0:30, 5:20, 3:18, 18:18,4:14},
        17: {0:28, 18:22,4:25, 3:15, 5:10},
        18: {0:35, 3:28, 5:12, 4:12, 17:8, 1:5},
        21: {4:70, 27:20,0:10},
        22: {5:65, 0:20, 18:15},
        25: {4:45, 0:30, 26:15,1:10},
        26: {3:40, 4:35, 0:25},
        27: {0:55, 5:20, 3:12, 18:8, 1:5},
    },
    'minor': {
        7:  {9:18, 10:18,13:15,14:18,11:12,8:5,  17:7,  18:7},
        8:  {11:40,7:20, 10:15,27:15,9:10},
        9:  {7:30, 10:25,13:20,14:15,11:10},
        10: {11:35,7:20, 14:15,13:15,8:10, 9:5},
        11: {7:55, 13:15,10:15,9:10, 14:5},
        13: {10:25,11:25,7:20, 14:15,9:10, 8:5},
        14: {7:35, 11:25,10:20,13:15,9:5},
        17: {7:35, 11:30,14:20,10:15},
        18: {7:30, 13:25,10:20,11:15,14:10},
        27: {7:60, 13:15,10:15,9:10},
    },
  },
  'blues': {
    'major': {
        26: {25:35,27:25,0:20, 3:15, 5:5},
        25: {26:50,27:20,0:20, 5:10},
        27: {26:40,25:30,0:20, 5:10},
        0:  {3:30, 4:25, 26:20,25:15,5:10},
        3:  {0:35, 4:25, 26:20,25:15,5:5},
        4:  {0:40, 3:30, 26:20,5:10},
        5:  {3:30, 4:25, 0:20, 26:15,1:10},
        1:  {4:50, 27:25,0:15, 3:10},
        28: {27:55,26:25,0:15, 25:5},
    },
    'minor': {  # minor blues
        7:  {10:30,14:25,11:20,13:15,9:10},
        10: {11:35,7:25, 14:20,13:15,9:5},
        11: {7:50, 13:20,10:15,14:15},
        13: {10:30,11:25,7:20, 14:15,9:10},
        14: {7:35, 11:30,10:20,13:15},
    },
  },
  'jazz': {
    'major': {
        0:  {1:20, 28:20,3:10, 5:10, 22:10,21:10,20:8,  19:8,  2:4},
        1:  {4:30, 27:30,28:15,29:15,0:10},
        2:  {5:30, 3:25, 1:15, 0:15, 4:15},
        3:  {0:20, 4:20, 1:15, 28:15,27:15,5:15},
        4:  {0:50, 5:15, 1:10, 29:10,3:8,  2:7},
        5:  {1:25, 28:20,3:15, 4:15, 0:15, 22:10},
        6:  {0:60, 5:15, 1:15, 29:10},
        19: {1:65, 28:20,0:15},
        20: {3:60, 25:25,0:15},
        21: {4:70, 27:20,29:10},
        22: {5:55, 0:15, 28:20,1:10},
        27: {0:55, 5:15, 1:10, 3:10, 29:10},
        28: {27:40,29:30,4:15, 0:10, 5:5},
        29: {0:65, 5:15, 1:10, 3:10},
        15: {4:55, 27:25,29:15,0:5},
        23: {4:55, 27:25,29:15,0:5},
    },
    'minor': {
        7:  {10:20,8:15, 13:15,11:20,28:10,27:10,15:5,  29:5},
        8:  {11:45,27:25,29:15,7:10, 13:5},
        10: {11:35,8:25, 7:20, 13:12,27:8},
        11: {7:55, 13:15,10:12,8:8,  29:10},
        13: {10:28,8:22, 11:22,7:18, 14:10},
        14: {7:35, 11:30,13:20,10:15},
        27: {7:60, 13:15,10:12,8:8,  29:5},
        28: {27:45,29:30,11:15,7:10},
        29: {7:65, 13:15,10:12,8:8},
    },
  },
}

# Starting chord probabilities by genre/tonality
START_WEIGHTS = {
    ('classical','major'): {0:70, 5:10, 1:5,  3:8,  4:5,  2:2},
    ('classical','minor'): {7:70, 13:10,9:8,  10:7, 11:5},
    ('pop','major'):        {0:50, 5:15, 1:10, 3:12, 4:8,  2:5},
    ('pop','minor'):        {7:50, 13:15,9:10, 10:12,11:8, 14:5},
    ('rock','major'):       {0:45, 5:15, 3:12, 18:12,4:8,  16:5, 17:3},
    ('rock','minor'):       {7:45, 13:15,9:12, 14:12,10:8, 17:5, 18:3},
    ('blues','major'):      {26:35,0:30, 25:20,3:10, 4:5},
    ('blues','minor'):      {7:55, 10:20,13:15,14:10},
    ('jazz','major'):       {0:35, 1:15, 28:15,3:10, 5:12, 2:8,  22:5},
    ('jazz','minor'):       {7:40, 10:15,8:15, 13:12,11:10,28:8},
}

# Difficulty allowed chord sets
DIFFICULTY_ALLOWED = {
    'beginner':     {0, 1, 3, 4, 5, 6, 7, 9, 10, 11, 13, 14},
    'intermediate': {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,16,17,18,21,22,25,26,27,28},
    'advanced':     set(range(30)),
}

NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

QUALITY_INTERVALS = {
    'major':  [0, 4, 7],
    'minor':  [0, 3, 7],
    'dim':    [0, 3, 6],
    'aug':    [0, 4, 8],
    'dom7':   [0, 4, 7, 10],
    'maj7':   [0, 4, 7, 11],
    'min7':   [0, 3, 7, 10],
    'hdim7':  [0, 3, 6, 10],
}

TONIC_IDX = {'major': 0, 'minor': 7}

def weighted_choice(weights: dict, allowed: set) -> Optional[int]:
    filtered = {k: v for k, v in weights.items() if k in allowed}
    if not filtered:
        return None
    total = sum(filtered.values())
    r = random.random() * total
    cum = 0
    for idx, w in filtered.items():
        cum += w
        if r <= cum:
            return idx
    return list(filtered.keys())[-1]

def chord_notes(tonic_semitone: int, chord_def: ChordDef) -> list:
    root = (tonic_semitone + chord_def.semitones) % 12
    ivs = QUALITY_INTERVALS.get(chord_def.quality, [0, 4, 7])
    return [NOTES[(root + iv) % 12] for iv in ivs], root

def generate_progression(
    length: int = 4,
    genre: str = 'pop',
    tonality: str = 'major',
    difficulty: str = 'intermediate',
    tonic_semitone: int = 0,
    cadence: bool = True,
) -> list:
    """
    Generate a chord progression list. Each element is a dict:
      roman, quality, function, root_semitone, notes, description
    """
    allowed   = DIFFICULTY_ALLOWED[difficulty]
    mat       = TRANS.get(genre, TRANS['pop']).get(tonality, {})
    tonic_idx = TONIC_IDX[tonality]

    # Pick starting chord
    sw = START_WEIGHTS.get((genre, tonality), {tonic_idx: 100})
    current = weighted_choice(sw, allowed) or tonic_idx

    progression = []
    prev = None

    for step in range(length):
        chord = CHORD_BY_IDX.get(current, CHORD_BY_IDX[tonic_idx])
        notes, root_semi = chord_notes(tonic_semitone, chord)
        progression.append({
            'chord':        chord,
            'roman':        chord.roman,
            'quality':      chord.quality,
            'function':     chord.function,
            'root_semitone':root_semi,
            'notes':        notes,
            'description':  chord.description,
        })
        prev = current

        # Second to last: steer toward dominant for authentic cadence
        if cadence and step == length - 2 and length >= 3:
            dom = 4 if tonality == 'major' else 11
            v7  = 27
            if dom in allowed:
                current = dom
                continue
            elif v7 in allowed:
                current = v7
                continue

        # Pick next from matrix
        transitions = mat.get(current, {})
        if not transitions:
            # Fallback: use tonic transitions
            transitions = mat.get(tonic_idx, {tonic_idx: 1})

        nxt = weighted_choice(transitions, allowed)
        if nxt is None:
            nxt = tonic_idx

        # Anti-repeat: if same chord picked, re-roll once
        if nxt == prev and length > 2:
            alt = weighted_choice(transitions, allowed - {prev})
            if alt is not None:
                nxt = alt

        current = nxt

    # Force tonic at end if cadence requested
    if cadence and progression:
        t = CHORD_BY_IDX[tonic_idx]
        notes, root_semi = chord_notes(tonic_semitone, t)
        progression[-1] = {
            'chord':        t,
            'roman':        t.roman,
            'quality':      t.quality,
            'function':     t.function,
            'root_semitone':root_semi,
            'notes':        notes,
            'description':  t.description,
        }

    return progression

def describe_progression(prog: list) -> str:
    romans = '  '.join(p['roman'] for p in prog)
    lines  = [romans]
    funcs  = '→'.join(p['function'] for p in prog)
    if funcs.endswith('T') and 'D' in funcs:
        lines.append('Authentic cadential motion (…D→T)')
    elif 'S' in funcs and 'D' in funcs:
        lines.append('Classical T→S→D motion present')
    else:
        lines.append('Loop / modal motion')
    for p in prog:
        rn   = NOTES[p['root_semitone']]
        qlbl = f"{rn} {p['quality']}"
        lines.append(f"  {p['roman']:8s}= {qlbl:18s} notes: {' '.join(p['notes'])}")
    return '\n'.join(lines)

# ─── Triad / chord shape vocabulary ──────────────────────────────────────────

TRIAD_TYPES = {
    # Basic
    'Major':           {'intervals': [0, 4, 7],        'difficulty': 1, 'desc': 'Root – M3 – P5. Bright.'},
    'Minor':           {'intervals': [0, 3, 7],        'difficulty': 1, 'desc': 'Root – m3 – P5. Dark.'},
    'Diminished':      {'intervals': [0, 3, 6],        'difficulty': 2, 'desc': 'Root – m3 – d5. Tense.'},
    'Augmented':       {'intervals': [0, 4, 8],        'difficulty': 2, 'desc': 'Root – M3 – A5. Dreamy.'},
    # Inversions
    '1st Inv (Major)': {'intervals': [4, 7, 12],       'difficulty': 2, 'desc': '3rd in bass. Softer major.'},
    '1st Inv (Minor)': {'intervals': [3, 7, 12],       'difficulty': 2, 'desc': '3rd in bass. Softer minor.'},
    '2nd Inv (Major)': {'intervals': [7, 12, 16],      'difficulty': 3, 'desc': '5th in bass. Cadential 6/4.'},
    # Suspended
    'sus2':            {'intervals': [0, 2, 7],        'difficulty': 2, 'desc': 'Root – M2 – P5. Open, ambiguous.'},
    'sus4':            {'intervals': [0, 5, 7],        'difficulty': 2, 'desc': 'Root – P4 – P5. Suspended tension.'},
    # Added tones
    'add9':            {'intervals': [0, 4, 7, 14],    'difficulty': 2, 'desc': 'Major + 9th. Pop shimmer.'},
    'madd9':           {'intervals': [0, 3, 7, 14],    'difficulty': 2, 'desc': 'Minor + 9th. Emotional richness.'},
    # Seventh chords
    'Major 7':         {'intervals': [0, 4, 7, 11],    'difficulty': 2, 'desc': 'Maj7. Smooth and jazzy.'},
    'Dominant 7':      {'intervals': [0, 4, 7, 10],    'difficulty': 2, 'desc': 'Dom7. Bluesy tension.'},
    'Minor 7':         {'intervals': [0, 3, 7, 10],    'difficulty': 2, 'desc': 'Min7. Warm minor.'},
    'Half-dim 7':      {'intervals': [0, 3, 6, 10],    'difficulty': 3, 'desc': 'm7b5. Jazz pre-dominant.'},
    'Full-dim 7':      {'intervals': [0, 3, 6, 9],     'difficulty': 3, 'desc': 'Fully diminished 7th. Max tension.'},
    # Extended
    'Major 9':         {'intervals': [0, 4, 7, 11, 14],'difficulty': 3, 'desc': 'Maj9. Lush jazz tonic.'},
    'Dominant 9':      {'intervals': [0, 4, 7, 10, 14],'difficulty': 3, 'desc': 'Dom9. Blues/jazz dominant.'},
    'Minor 9':         {'intervals': [0, 3, 7, 10, 14],'difficulty': 3, 'desc': 'Min9. Rich minor.'},
    'Dom b9':          {'intervals': [0, 4, 7, 10, 13],'difficulty': 3, 'desc': 'Altered dom. Flamenco, jazz.'},
    'Dom #9 (Jimi)':   {'intervals': [0, 4, 7, 10, 15],'difficulty': 3, 'desc': 'Hendrix chord. Blues-rock fire.'},
    # Power
    'Power (5th)':     {'intervals': [0, 7],           'difficulty': 1, 'desc': 'Root + 5th only. Rock, no quality.'},
}

# ─── Self-test ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    random.seed(99)
    print('=== Harmony Engine self-test ===\n')
    tests = [
        ('pop',       'major', 'beginner',     0,  4),
        ('pop',       'major', 'intermediate', 0,  4),
        ('rock',      'major', 'intermediate', 4,  4),
        ('rock',      'minor', 'advanced',     4,  4),
        ('classical', 'major', 'advanced',     0,  6),
        ('classical', 'minor', 'intermediate', 9,  4),
        ('blues',     'major', 'intermediate', 9,  12),
        ('jazz',      'major', 'advanced',     0,  8),
    ]
    for genre, tonality, diff, tonic, length in tests:
        print(f'{genre.upper():10} {tonality:5} {diff:12} key={NOTES[tonic]:3} len={length}')
        prog = generate_progression(length, genre, tonality, diff, tonic)
        print(describe_progression(prog))
        print()