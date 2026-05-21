"""
harmony_engine.py
=================
Unified music theory engine combining:
  - Claude Code: 31 triads (levelled), 21 scales/modes, 40 named progressions,
                 chord graph for random generation, 5-level difficulty system
  - Claude:      Markov chain generator (5 genres × major/minor × difficulty),
                 CHORD_LIBRARY with 30+ chord types, algorithmic inversion/subset
                 voicing generator, functional harmony labels (T/S/D/X)

Empirical sources:
  Temperley (2009) Kostka-Payne corpus — 919 classical chords
  Hooktheory database — 40,000+ pop/rock songs
"""

import random
from dataclasses import dataclass, field
from typing import Optional
from itertools import combinations

NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

# ─── Triad / scale shape library ──────────────────────────────────────────────
# level:     1–5 difficulty gate (CC system)
# dot_types: colour role per interval position for fretboard display
# category:  grouping for UI filtering

TRIADS = {
    # ── Level 1: Fundamentals ─────────────────────────────────────────────────
    'Power':          {'intervals':[0,7,12],  'level':1,'category':'power',
                       'dot_types':['root','fifth','root'],
                       'desc':'Root + P5 + octave. The rock/metal staple with distortion.'},
    'Major':          {'intervals':[0,4,7],   'level':1,'category':'triad',
                       'dot_types':['root','third','fifth'],
                       'desc':'Root – M3 – P5. Bright. The foundation of Western harmony.'},
    'Minor':          {'intervals':[0,3,7],   'level':1,'category':'triad',
                       'dot_types':['root','third','fifth'],
                       'desc':'Root – m3 – P5. Dark, emotive counterpart to major.'},
    # ── Level 2: Core extensions ──────────────────────────────────────────────
    'Sus2':           {'intervals':[0,2,7],   'level':2,'category':'suspended',
                       'dot_types':['root','interval','fifth'],
                       'desc':'Root – M2 – P5. Open and ambiguous. Resolves to major or minor.'},
    'Sus4':           {'intervals':[0,5,7],   'level':2,'category':'suspended',
                       'dot_types':['root','interval','fifth'],
                       'desc':'Root – P4 – P5. Suspended tension, yearns to resolve to major.'},
    'Diminished':     {'intervals':[0,3,6],   'level':2,'category':'triad',
                       'dot_types':['root','third','fifth'],
                       'desc':'Root – m3 – d5. Tense, unstable. Strong pull to resolve.'},
    'Augmented':      {'intervals':[0,4,8],   'level':2,'category':'triad',
                       'dot_types':['root','third','fifth'],
                       'desc':'Root – M3 – A5. Symmetrical, dreamy, unresolved.'},
    # ── Level 3: Shell voicings & alterations ─────────────────────────────────
    'Major b5':       {'intervals':[0,4,6],   'level':3,'category':'altered',
                       'dot_types':['root','third','fifth'],
                       'desc':'Major with flattened 5th. Lydian flavour, ambiguous.'},
    'Minor #5':       {'intervals':[0,3,8],   'level':3,'category':'altered',
                       'dot_types':['root','third','fifth'],
                       'desc':'Minor with raised 5th. Melodic minor harmony.'},
    'Shell Dom7':     {'intervals':[0,4,10],  'level':3,'category':'shell',
                       'dot_types':['root','third','interval'],
                       'desc':'Root – M3 – m7. Stripped dominant. No 5th — ideal jazz/blues voicing.'},
    'Shell Min7':     {'intervals':[0,3,10],  'level':3,'category':'shell',
                       'dot_types':['root','third','interval'],
                       'desc':'Root – m3 – m7. Stripped minor seventh. Smooth voice leading.'},
    'Shell Maj7':     {'intervals':[0,4,11],  'level':3,'category':'shell',
                       'dot_types':['root','third','interval'],
                       'desc':'Root – M3 – M7. Stripped major seventh. Lush tonic colour.'},
    'Shell Maj6':     {'intervals':[0,4,9],   'level':3,'category':'shell',
                       'dot_types':['root','third','interval'],
                       'desc':'Root – M3 – M6. Major sixth shell. Warm, resolved jazz colour.'},
    'Shell Min6':     {'intervals':[0,3,9],   'level':3,'category':'shell',
                       'dot_types':['root','third','interval'],
                       'desc':'Root – m3 – M6. Minor sixth shell. Dorian flavour.'},
    # ── Level 4: Advanced colours ─────────────────────────────────────────────
    'Quartal':        {'intervals':[0,5,10],  'level':4,'category':'quartal',
                       'dot_types':['root','interval','interval'],
                       'desc':'Stacked fourths. McCoy Tyner, so-what voicing. Modal ambiguity.'},
    'Shell MinMaj7':  {'intervals':[0,3,11],  'level':4,'category':'shell',
                       'dot_types':['root','third','interval'],
                       'desc':'Root – m3 – M7. Haunting. James Bond theme opening chord.'},
    'Power + b7':     {'intervals':[0,7,10,12],'level':4,'category':'power',
                       'dot_types':['root','fifth','interval','root'],
                       'desc':'Power chord + b7 + octave. Mixolydian shell.'},
    'Power + Maj7':   {'intervals':[0,7,11,12],'level':4,'category':'power',
                       'dot_types':['root','fifth','interval','root'],
                       'desc':'Power chord + M7 + octave. Dreamy suspended tonic.'},
    'Power + 6':      {'intervals':[0,7,9,12], 'level':4,'category':'power',
                       'dot_types':['root','fifth','interval','root'],
                       'desc':'Power chord + M6 + octave. Open country/folk flavour.'},
    'Power + b6':     {'intervals':[0,7,8,12], 'level':4,'category':'power',
                       'dot_types':['root','fifth','interval','root'],
                       'desc':'Power chord + b6 + octave. Dark Phrygian colour.'},
    'Phrygian':       {'intervals':[0,1,7],   'level':4,'category':'modal',
                       'dot_types':['root','interval','fifth'],
                       'desc':'Root – b2 – P5. Phrygian modal flavour. Flamenco, metal.'},
    'Tritone Shell':  {'intervals':[0,6,10],  'level':4,'category':'shell',
                       'dot_types':['root','interval','interval'],
                       'desc':'Root – tritone – b7. Altered dominant shell. Maximum jazz tension.'},
    # ── Level 5: Exotic / niche ───────────────────────────────────────────────
    'Aug Sus4':       {'intervals':[0,5,8],   'level':5,'category':'exotic',
                       'dot_types':['root','interval','fifth'],
                       'desc':'Augmented sus4. Whole-tone adjacent. Dreamy and unstable.'},
    'Sus2 b5':        {'intervals':[0,2,6],   'level':5,'category':'exotic',
                       'dot_types':['root','interval','fifth'],
                       'desc':'Sus2 with flat 5th. Lydian/whole-tone fragment.'},
    'Sus4 b5':        {'intervals':[0,5,6],   'level':5,'category':'exotic',
                       'dot_types':['root','interval','interval'],
                       'desc':'Sus4 with flat 5th. Tritone cluster, very dissonant.'},
    'Phrygian Tri':   {'intervals':[0,1,5],   'level':5,'category':'exotic',
                       'dot_types':['root','interval','interval'],
                       'desc':'Root – b2 – P4. Phrygian cluster. Flamenco approach chord.'},
    'Whole Tone Tri': {'intervals':[0,2,4],   'level':5,'category':'exotic',
                       'dot_types':['root','interval','third'],
                       'desc':'Three consecutive whole tones. Whole-tone scale fragment.'},
    'Aug Quartal':    {'intervals':[0,6,11],  'level':5,'category':'quartal',
                       'dot_types':['root','interval','interval'],
                       'desc':'Augmented quartal. Tritone + major 7th. Extreme dissonance.'},
    'Minor Cluster':  {'intervals':[0,2,3],   'level':5,'category':'exotic',
                       'dot_types':['root','interval','third'],
                       'desc':'Root – M2 – m3. Tight cluster. Used in contemporary classical.'},
    'Sus2 + b7':      {'intervals':[0,2,10],  'level':5,'category':'exotic',
                       'dot_types':['root','interval','interval'],
                       'desc':'Root – M2 – m7. Open quartal sound with added colour.'},
    'Cluster b7':     {'intervals':[0,1,10],  'level':5,'category':'exotic',
                       'dot_types':['root','interval','interval'],
                       'desc':'Root – b2 – b7. Extreme dissonance. Avant-garde/noise.'},
}

# ─── Scales and modes ─────────────────────────────────────────────────────────

MODES = {
    # ── Level 1 ───────────────────────────────────────────────────────────────
    'Ionian (Major)':     {'intervals':[0,2,4,5,7,9,11],   'level':1,
                           'desc':'Standard major scale. Bright and resolved.'},
    'Aeolian (Minor)':    {'intervals':[0,2,3,5,7,8,10],   'level':1,
                           'desc':'Natural minor. Sad, introspective. Rock ballads.'},
    # ── Level 2 ───────────────────────────────────────────────────────────────
    'Major Pentatonic':   {'intervals':[0,2,4,7,9],         'level':2,
                           'desc':'5-note major. No half-steps — always sounds good. Country, rock.'},
    'Minor Pentatonic':   {'intervals':[0,3,5,7,10],         'level':2,
                           'desc':'5-note minor. The rock/blues workhorse. Learn this first.'},
    'Blues':              {'intervals':[0,3,5,6,7,10],       'level':2,
                           'desc':'Minor pentatonic + b5 blue note. The soul of the blues.'},
    'Dorian':             {'intervals':[0,2,3,5,7,9,10],     'level':2,
                           'desc':'Minor with raised 6th. Jazzy, funky. Santana, Miles Davis.'},
    'Mixolydian':         {'intervals':[0,2,4,5,7,9,10],     'level':2,
                           'desc':'Major with flat 7th. Blues/rock staple. Sweet Home Alabama.'},
    # ── Level 3 ───────────────────────────────────────────────────────────────
    'Phrygian':           {'intervals':[0,1,3,5,7,8,10],     'level':3,
                           'desc':'Minor with flat 2nd. Dark Spanish flavour. Flamenco & metal.'},
    'Lydian':             {'intervals':[0,2,4,6,7,9,11],     'level':3,
                           'desc':'Major with raised 4th. Floating, cinematic. Film scores.'},
    'Locrian':            {'intervals':[0,1,3,5,6,8,10],     'level':3,
                           'desc':'Flat 2nd and flat 5th. Extremely dark. Rarely used directly.'},
    'Harmonic Minor':     {'intervals':[0,2,3,5,7,8,11],     'level':3,
                           'desc':'Natural minor with raised 7th. Classical minor key staple.'},
    'Melodic Minor':      {'intervals':[0,2,3,5,7,9,11],     'level':3,
                           'desc':'Minor with raised 6th and 7th ascending. Jazz minor.'},
    # ── Level 4 ───────────────────────────────────────────────────────────────
    'Phrygian Dominant':  {'intervals':[0,1,4,5,7,8,10],     'level':4,
                           'desc':'Harmonic minor mode 5. Phrygian with major 3rd. Flamenco fire.'},
    'Lydian Dominant':    {'intervals':[0,2,4,6,7,9,10],     'level':4,
                           'desc':'Lydian with flat 7th. Jazz/fusion. Herbie Hancock territory.'},
    'Whole Tone':         {'intervals':[0,2,4,6,8,10],       'level':4,
                           'desc':'All whole steps. 6 notes, symmetrical. Debussy, altered dominants.'},
    'Half-Whole Dim':     {'intervals':[0,1,3,4,6,7,9,10],   'level':4,
                           'desc':'Alternating half/whole steps. 8 notes. Dominant diminished scale.'},
    'Whole-Half Dim':     {'intervals':[0,2,3,5,6,8,9,11],   'level':4,
                           'desc':'Alternating whole/half steps. 8 notes. Diminished chord scale.'},
    # ── Level 5 ───────────────────────────────────────────────────────────────
    'Altered':            {'intervals':[0,1,3,4,6,8,10],     'level':5,
                           'desc':'Super Locrian. All alterations. Jazz altered dominant.'},
    'Hungarian Minor':    {'intervals':[0,2,3,6,7,8,11],     'level':5,
                           'desc':'Harmonic minor with raised 4th. Exotic, Eastern European.'},
    'Double Harmonic':    {'intervals':[0,1,4,5,7,8,11],     'level':5,
                           'desc':'Two augmented seconds. Byzantine scale. Middle Eastern.'},
    'Bebop Major':        {'intervals':[0,2,4,5,7,8,9,11],   'level':5,
                           'desc':'Major scale + chromatic passing tone. 8 notes. Jazz bebop.'},
}

# ─── Named progressions (from Claude Code, 40 total, levelled) ───────────────
# chords: list of (semitone_offset_from_key_root, quality_code)
# quality codes: M=major  m=minor  d=diminished  a=augmented  p=power

NAMED_PROGRESSIONS = [
    # ── Level 1 ───────────────────────────────────────────────────────────────
    {'name':'I – IV – V',            'genre':'Blues/Rock',     'level':1,
     'chords':[(0,'M'),(5,'M'),(7,'M')]},
    {'name':'I – V – vi – IV',       'genre':'Pop',            'level':1,
     'chords':[(0,'M'),(7,'M'),(9,'m'),(5,'M')]},
    {'name':'I – vi – IV – V',       'genre':'Pop / 50s',      'level':1,
     'chords':[(0,'M'),(9,'m'),(5,'M'),(7,'M')]},
    {'name':'vi – IV – I – V',       'genre':'Pop',            'level':1,
     'chords':[(9,'m'),(5,'M'),(0,'M'),(7,'M')]},
    {'name':'i – bVII – bVI – bVII', 'genre':'Rock/Metal',     'level':1,
     'chords':[(0,'m'),(10,'M'),(8,'M'),(10,'M')]},
    # ── Level 2 ───────────────────────────────────────────────────────────────
    {'name':'I – bVII – IV',         'genre':'Rock',           'level':2,
     'chords':[(0,'M'),(10,'M'),(5,'M')]},
    {'name':'I – V – vi – iii – IV', 'genre':'Pop/Classical',  'level':2,
     'chords':[(0,'M'),(7,'M'),(9,'m'),(4,'m'),(5,'M')]},
    {'name':'I – IV – V – IV',       'genre':'Rock/Blues',     'level':2,
     'chords':[(0,'M'),(5,'M'),(7,'M'),(5,'M')]},
    {'name':'i – bVI – bIII – bVII', 'genre':'Rock/Metal',     'level':2,
     'chords':[(0,'m'),(8,'M'),(3,'M'),(10,'M')]},
    {'name':'I – III – IV – iv',     'genre':'Rock/Pop',       'level':2,
     'chords':[(0,'M'),(4,'M'),(5,'M'),(5,'m')]},
    {'name':'I – IV – ii – V',       'genre':'Pop/Jazz',       'level':2,
     'chords':[(0,'M'),(5,'M'),(2,'m'),(7,'M')]},
    {'name':'i – iv – v – i',        'genre':'Classical',      'level':2,
     'chords':[(0,'m'),(5,'m'),(7,'m'),(0,'m')]},
    {'name':'I – IV – I – V',        'genre':'Blues',          'level':2,
     'chords':[(0,'M'),(5,'M'),(0,'M'),(7,'M')]},
    # ── Level 3 ───────────────────────────────────────────────────────────────
    {'name':'ii – V – I',            'genre':'Jazz',           'level':3,
     'chords':[(2,'m'),(7,'M'),(0,'M')]},
    {'name':'I – vi – ii – V',       'genre':'Jazz/Pop',       'level':3,
     'chords':[(0,'M'),(9,'m'),(2,'m'),(7,'M')]},
    {'name':'IV – V – iii – vi',     'genre':'Pop',            'level':3,
     'chords':[(5,'M'),(7,'M'),(4,'m'),(9,'m')]},
    {'name':'I – bIII – IV',         'genre':'Blues/Rock',     'level':3,
     'chords':[(0,'M'),(3,'M'),(5,'M')]},
    {'name':'I – bVI – bVII – I',    'genre':'Rock',           'level':3,
     'chords':[(0,'M'),(8,'M'),(10,'M'),(0,'M')]},
    {'name':'i – V – i',             'genre':'Classical',      'level':3,
     'chords':[(0,'m'),(7,'M'),(0,'m')]},
    {'name':'I – IV – bVII – IV',    'genre':'Rock',           'level':3,
     'chords':[(0,'M'),(5,'M'),(10,'M'),(5,'M')]},
    {'name':'vi – ii – V – I',       'genre':'Jazz/Pop',       'level':3,
     'chords':[(9,'m'),(2,'m'),(7,'M'),(0,'M')]},
    {'name':'i – iv – bVII – bIII',  'genre':'Metal/Rock',     'level':3,
     'chords':[(0,'m'),(5,'m'),(10,'M'),(3,'M')]},
    {'name':'V – IV – I',            'genre':'Blues',          'level':3,
     'chords':[(7,'M'),(5,'M'),(0,'M')]},
    {'name':'I – II – IV – I',       'genre':'Rock/Pop',       'level':3,
     'chords':[(0,'M'),(2,'M'),(5,'M'),(0,'M')]},
    # ── Level 4 ───────────────────────────────────────────────────────────────
    {'name':'I–IV–vii°–iii–vi–ii–V–I','genre':'Classical',    'level':4,
     'chords':[(0,'M'),(5,'M'),(11,'d'),(4,'m'),(9,'m'),(2,'m'),(7,'M'),(0,'M')]},
    {'name':'iii – IV – I – V',      'genre':'Pop/Classical',  'level':4,
     'chords':[(4,'m'),(5,'M'),(0,'M'),(7,'M')]},
    {'name':'I – III – vi – IV',     'genre':'Jazz/Pop',       'level':4,
     'chords':[(0,'M'),(4,'M'),(9,'m'),(5,'M')]},
    {'name':'i – iv – bII – V',      'genre':'Classical',      'level':4,
     'chords':[(0,'m'),(5,'m'),(1,'M'),(7,'M')]},
    {'name':'I – bVI – IV – bII',    'genre':'Modern',         'level':4,
     'chords':[(0,'M'),(8,'M'),(5,'M'),(1,'M')]},
    {'name':'bVI – bVII – I',        'genre':'Rock/Classical', 'level':4,
     'chords':[(8,'M'),(10,'M'),(0,'M')]},
    {'name':'i – bVI – V – i',       'genre':'Classical/Metal','level':4,
     'chords':[(0,'m'),(8,'M'),(7,'M'),(0,'m')]},
    {'name':'I – IV – #iv° – V',     'genre':'Classical',      'level':4,
     'chords':[(0,'M'),(5,'M'),(6,'d'),(7,'M')]},
    {'name':'i – bVII – bVI – V',    'genre':'Flamenco',       'level':4,
     'chords':[(0,'m'),(10,'M'),(8,'M'),(7,'M')]},
    # ── Level 5 ───────────────────────────────────────────────────────────────
    {'name':'I–V–vi–iii–IV–I–IV–V', 'genre':'Classical (Canon)','level':5,
     'chords':[(0,'M'),(7,'M'),(9,'m'),(4,'m'),(5,'M'),(0,'M'),(5,'M'),(7,'M')]},
    {'name':'I – bII – I',           'genre':'Jazz/Classical', 'level':5,
     'chords':[(0,'M'),(1,'M'),(0,'M')]},
    {'name':'ii – bII – I',          'genre':'Jazz',           'level':5,
     'chords':[(2,'m'),(1,'M'),(0,'M')]},
    {'name':'I – bIII – bVI – bII',  'genre':'Modern/Jazz',    'level':5,
     'chords':[(0,'M'),(3,'M'),(8,'M'),(1,'M')]},
    {'name':'I – #IV° – V',          'genre':'Classical',      'level':5,
     'chords':[(0,'M'),(6,'d'),(7,'M')]},
    {'name':'i – II – iv – I',       'genre':'Flamenco',       'level':5,
     'chords':[(0,'m'),(2,'M'),(5,'m'),(0,'M')]},

    # ── Cinematic progressions (Hans Zimmer / film score style) ─────────────
    {'name':'i – bVI – bVII – i',    'genre':'Cinematic',      'level':2,
     'chords':[(0,'m'),(8,'M'),(10,'M'),(0,'m')]},
    {'name':'i – bVII – bVI – bVII','genre':'Cinematic',       'level':2,
     'chords':[(0,'m'),(10,'M'),(8,'M'),(10,'M')]},
    {'name':'I – bVI – bVII – I (epic)','genre':'Cinematic',   'level':2,
     'chords':[(0,'M'),(8,'M'),(10,'M'),(0,'M')]},
    {'name':'vi – IV – I – V (epic pop)','genre':'Cinematic',  'level':1,
     'chords':[(9,'m'),(5,'M'),(0,'M'),(7,'M')]},
    {'name':'i – v – bVI – bVII',    'genre':'Cinematic',      'level':3,
     'chords':[(0,'m'),(7,'m'),(8,'M'),(10,'M')]},
    {'name':'i – iv – bVI – V',      'genre':'Cinematic',      'level':3,
     'chords':[(0,'m'),(5,'m'),(8,'M'),(7,'M')]},
    {'name':'i – bIII – bVII – iv',  'genre':'Cinematic',      'level':3,
     'chords':[(0,'m'),(3,'M'),(10,'M'),(5,'m')]},
    {'name':'I – iii – bVI – bVII',  'genre':'Cinematic',      'level':4,
     'chords':[(0,'M'),(4,'m'),(8,'M'),(10,'M')]},
    {'name':'i – bVI – iv – bVII',   'genre':'Cinematic',      'level':4,
     'chords':[(0,'m'),(8,'M'),(5,'m'),(10,'M')]},
]

# Chord graph for random progression generation (CC system)
# Keys: (semitone, quality_code).  Values: [(next_semitone, next_quality, min_level), ...]
CHORD_GRAPH = {
    (0,'M'):  [(5,'M',1),(7,'M',1),(9,'m',1),(2,'m',1),
               (4,'m',2),(10,'M',2),(8,'M',3),(3,'M',3),(11,'d',3),(5,'m',3),(1,'M',4)],
    (0,'m'):  [(5,'m',1),(7,'M',1),(10,'M',1),(8,'M',2),(3,'M',2),(5,'M',3),(7,'m',3)],
    (5,'M'):  [(7,'M',1),(0,'M',1),(2,'m',2),(10,'M',2),(5,'m',3),(11,'d',3)],
    (5,'m'):  [(0,'M',2),(7,'M',2),(10,'M',2),(0,'m',3)],
    (7,'M'):  [(0,'M',1),(9,'m',2),(5,'M',2),(2,'m',3),(0,'m',3)],
    (7,'m'):  [(0,'m',2),(3,'M',2),(8,'M',3)],
    (9,'m'):  [(2,'m',1),(5,'M',1),(7,'M',2),(0,'M',2),(4,'m',3)],
    (2,'m'):  [(7,'M',1),(5,'M',2),(11,'d',2),(0,'M',3),(1,'M',4)],
    (4,'m'):  [(9,'m',2),(5,'M',2),(0,'M',3),(7,'M',3)],
    (4,'M'):  [(9,'m',3),(7,'M',3),(0,'M',4)],
    (10,'M'): [(0,'M',2),(5,'M',2),(8,'M',3),(3,'M',3)],
    (8,'M'):  [(10,'M',2),(7,'M',3),(0,'M',4),(5,'M',3)],
    (3,'M'):  [(10,'M',2),(5,'M',3),(0,'M',4)],
    (11,'d'): [(0,'M',2),(7,'M',3)],
    (6,'d'):  [(7,'M',4),(0,'M',5)],
    (1,'M'):  [(0,'M',4),(7,'M',4),(5,'M',5)],
    (2,'M'):  [(5,'M',3),(7,'M',3),(0,'M',4)],
}

QUALITY_INTERVALS = {'M':[0,4,7],'m':[0,3,7],'d':[0,3,6],'a':[0,4,8],'p':[0,7,12]}
QUALITY_DOT_TYPES = {'M':['root','third','fifth'],'m':['root','third','fifth'],
                     'd':['root','third','fifth'],'a':['root','third','fifth'],'p':['root','fifth','root']}
QUALITY_LABEL     = {'M':'','m':'m','d':'°','a':'+','p':'5'}
DEG_NAMES = {0:'1',1:'b2',2:'2',3:'b3',4:'3',5:'4',6:'b5',7:'5',8:'b6',9:'6',10:'b7',11:'7'}

# ─── Extended chord library (for inversions / subset voicing generator) ───────
# Used by Triads mode when the user wants extended chord voicings on the fretboard.

CHORD_LIBRARY = {
    # triads
    'Major':           {'intervals':[0,4,7],       'level':1,'category':'triad'},
    'Minor':           {'intervals':[0,3,7],       'level':1,'category':'triad'},
    'Diminished':      {'intervals':[0,3,6],       'level':2,'category':'triad'},
    'Augmented':       {'intervals':[0,4,8],       'level':2,'category':'triad'},
    'sus2':            {'intervals':[0,2,7],       'level':2,'category':'suspended'},
    'sus4':            {'intervals':[0,5,7],       'level':2,'category':'suspended'},
    'Power':           {'intervals':[0,7,12],      'level':1,'category':'power'},
    # added tones
    'add9':            {'intervals':[0,4,7,14],    'level':2,'category':'added'},
    'minor add9':      {'intervals':[0,3,7,14],    'level':2,'category':'added'},
    'add11':           {'intervals':[0,4,7,17],    'level':2,'category':'added'},
    '6':               {'intervals':[0,4,7,9],     'level':2,'category':'added'},
    'minor 6':         {'intervals':[0,3,7,9],     'level':2,'category':'added'},
    '6/9':             {'intervals':[0,4,7,9,14],  'level':3,'category':'added'},
    # sevenths
    'Major 7':         {'intervals':[0,4,7,11],    'level':2,'category':'seventh'},
    'Dominant 7':      {'intervals':[0,4,7,10],    'level':2,'category':'seventh'},
    'Minor 7':         {'intervals':[0,3,7,10],    'level':2,'category':'seventh'},
    'Minor/Major 7':   {'intervals':[0,3,7,11],    'level':3,'category':'seventh'},
    'Augmented 7':     {'intervals':[0,4,8,10],    'level':3,'category':'seventh'},
    'Augmented Maj7':  {'intervals':[0,4,8,11],    'level':3,'category':'seventh'},
    'Half-dim 7':      {'intervals':[0,3,6,10],    'level':3,'category':'seventh'},
    'Full-dim 7':      {'intervals':[0,3,6,9],     'level':3,'category':'seventh'},
    'Dom 7 sus4':      {'intervals':[0,5,7,10],    'level':2,'category':'seventh'},
    # ninths
    'Major 9':         {'intervals':[0,4,7,11,14], 'level':3,'category':'ninth'},
    'Dominant 9':      {'intervals':[0,4,7,10,14], 'level':3,'category':'ninth'},
    'Minor 9':         {'intervals':[0,3,7,10,14], 'level':3,'category':'ninth'},
    'Dom b9':          {'intervals':[0,4,7,10,13], 'level':3,'category':'ninth'},
    'Dom #9':          {'intervals':[0,4,7,10,15], 'level':3,'category':'ninth'},
    'Dom 7 #11':       {'intervals':[0,4,7,10,18], 'level':4,'category':'ninth'},
    # elevenths
    'Minor 11':        {'intervals':[0,3,7,10,14,17],'level':4,'category':'eleventh'},
    'Dominant 11':     {'intervals':[0,4,7,10,14,17],'level':4,'category':'eleventh'},
    'Major 11':        {'intervals':[0,4,7,11,14,17],'level':4,'category':'eleventh'},
    # thirteenths
    'Major 13':        {'intervals':[0,4,7,11,14,17,21],'level':5,'category':'thirteenth'},
    'Dominant 13':     {'intervals':[0,4,7,10,14,17,21],'level':5,'category':'thirteenth'},
    'Minor 13':        {'intervals':[0,3,7,10,14,17,21],'level':5,'category':'thirteenth'},
    'Dom 7 b13':       {'intervals':[0,4,7,10,20], 'level':5,'category':'thirteenth'},
}

# ─── Markov chain progression generator ──────────────────────────────────────
# Sources: Temperley (2009) classical corpus + Hooktheory 40k-song database

@dataclass
class ChordDef:
    idx: int
    roman: str
    semitones: int
    quality: str      # major minor dim aug dom7 min7
    function: str     # T=tonic S=subdominant D=dominant X=chromatic
    difficulty: int   # 1-3 (maps to levels 1-2, 3, 4-5)
    description: str
    genre_tags: list = field(default_factory=list)

CHORDS = [
    ChordDef( 0,'I',    0,'major','T',1,'Tonic. Home base.',                          ['classical','pop','rock','jazz','blues']),
    ChordDef( 1,'ii',   2,'minor','S',1,'Supertonic minor. Pre-dominant.',            ['classical','pop','rock','jazz']),
    ChordDef( 2,'iii',  4,'minor','T',2,'Mediant minor. Tonic function.',             ['classical','pop']),
    ChordDef( 3,'IV',   5,'major','S',1,'Subdominant. Departure and lift.',           ['classical','pop','rock','blues']),
    ChordDef( 4,'V',    7,'major','D',1,'Dominant. Tension seeking resolution to I.',['classical','pop','rock','jazz','blues']),
    ChordDef( 5,'vi',   9,'minor','T',1,'Submediant. Emotional depth.',               ['classical','pop','rock']),
    ChordDef( 6,'vii°',11,'dim',  'D',2,'Leading-tone dim. Strong dominant pull.',   ['classical','jazz']),
    ChordDef( 7,'i',    0,'minor','T',1,'Minor tonic.',                               ['classical','rock','pop','blues']),
    ChordDef( 8,'ii°',  2,'dim',  'S',2,'Dim supertonic. Pre-dominant.',             ['classical','jazz']),
    ChordDef( 9,'III',  3,'major','T',1,'Mediant major in minor key.',                ['rock','pop','classical']),
    ChordDef(10,'iv',   5,'minor','S',1,'Minor subdominant. Dark and emotional.',    ['classical','rock','pop','blues']),
    ChordDef(11,'V',    7,'major','D',1,'Dominant major (raised 7th).',              ['classical','pop','rock','jazz']),
    ChordDef(12,'v',    7,'minor','D',2,'Dominant minor (natural 7th).',             ['classical']),
    ChordDef(13,'VI',   8,'major','T',1,'Subtonic major in minor.',                  ['classical','rock','pop']),
    ChordDef(14,'VII', 10,'major','X',1,'Subtonic. Mixolydian colour.',              ['rock','pop']),
    ChordDef(15,'bII',  1,'major','S',3,'Neapolitan. Resolves to V.',               ['classical','jazz']),
    ChordDef(16,'bIII', 3,'major','T',2,'Borrowed flat-three.',                     ['rock','pop']),
    ChordDef(17,'bVI',  8,'major','S',2,'Borrowed flat-six. Cinematic.',            ['rock','pop','classical']),
    ChordDef(18,'bVII',10,'major','X',1,'Borrowed flat-seven. Rock anthem chord.',  ['rock','pop','blues']),
    ChordDef(19,'V/ii', 9,'major','D',3,'Secondary dominant of ii.',                ['classical','jazz','pop']),
    ChordDef(20,'V/IV', 0,'dom7', 'D',3,'Secondary dominant of IV.',               ['classical','jazz','blues']),
    ChordDef(21,'V/V',  2,'major','D',2,'Secondary dominant of V.',                ['classical','pop','rock','jazz']),
    ChordDef(22,'V/vi', 4,'major','D',2,'Secondary dominant of vi.',               ['classical','pop']),
    ChordDef(23,'It+6', 6,'aug',  'D',3,'Italian aug6 → V.',                       ['classical']),
    ChordDef(24,'Ger+6',6,'dom7', 'D',3,'German aug6 → V.',                        ['classical']),
    ChordDef(25,'IV7',  5,'dom7', 'S',2,'Blues IV7.',                              ['blues','jazz']),
    ChordDef(26,'I7',   0,'dom7', 'T',2,'Blues tonic dominant 7th.',               ['blues','jazz']),
    ChordDef(27,'V7',   7,'dom7', 'D',2,'Dominant seventh. Strongest pull to I.',  ['blues','jazz','classical','pop','rock']),
    ChordDef(28,'ii7',  2,'min7', 'S',2,'Minor seventh supertonic. Jazz ii-V.',    ['jazz','pop']),
    ChordDef(29,'subV', 1,'dom7', 'D',3,'Tritone substitution → I.',              ['jazz']),
]
CHORD_BY_IDX = {c.idx: c for c in CHORDS}

TRANS = {
  'classical':{'major':{
      0:{1:15,2:5,3:22,4:40,5:10,6:8,21:5,22:5,20:3,15:2},
      1:{0:10,4:45,6:20,27:15,21:5,5:5}, 2:{0:8,3:25,5:35,4:15,6:10,1:7},
      3:{0:20,4:40,6:15,1:10,5:8,27:7}, 4:{0:70,5:10,1:5,6:5,3:5,2:5},
      5:{1:30,3:25,4:20,2:10,0:10,6:5}, 6:{0:80,5:10,2:5,1:5},
      15:{4:60,27:25,0:15}, 19:{1:80,5:15,0:5}, 20:{3:75,0:15,25:10},
      21:{4:80,27:15,0:5}, 22:{5:75,0:15,1:10},
      23:{4:70,27:20,0:10}, 24:{4:70,27:20,0:10}, 27:{0:65,5:15,1:10,3:10}},
   'minor':{
      7:{10:22,11:30,8:15,13:12,14:8,9:8,12:5}, 8:{11:50,7:15,6:15,27:10,9:5,10:5},
      9:{7:30,10:30,13:20,11:10,14:10}, 10:{11:40,7:20,8:15,13:10,9:10,14:5},
      11:{7:70,13:12,10:8,8:5,9:5}, 12:{7:55,13:15,10:15,9:10,8:5},
      13:{10:25,8:20,11:25,7:15,9:10,14:5}, 14:{7:40,11:30,10:15,13:10,9:5},
      27:{7:65,13:15,10:12,8:8}, 15:{11:60,27:25,7:15}}},
  'pop':{'major':{
      0:{3:24,4:21,5:19,1:8,2:5,18:10,16:5,17:4,22:4},
      1:{4:50,3:15,0:10,5:10,27:10,28:5}, 2:{3:30,5:35,1:15,4:10,0:10},
      3:{0:38,4:28,5:12,1:8,18:7,2:4,17:3}, 4:{0:32,5:29,3:25,1:7,2:4,18:3},
      5:{3:35,4:25,0:15,1:12,2:8,18:5}, 6:{0:70,5:15,1:15},
      16:{0:30,5:25,3:20,4:15,18:10}, 17:{0:30,4:35,18:20,3:15},
      18:{0:40,3:30,4:15,5:10,1:5}, 19:{1:80,0:10,5:10},
      21:{4:80,27:15,0:5}, 22:{5:75,0:15,1:10},
      27:{0:65,5:20,3:10,1:5}, 28:{27:60,4:25,0:15}, 29:{0:70,5:20,3:10}},
   'minor':{
      7:{13:22,9:18,14:16,10:14,11:12,8:8,17:5,5:5},
      8:{11:45,7:15,10:15,27:15,9:10}, 9:{7:28,10:28,13:22,14:12,11:10},
      10:{11:35,7:22,13:20,14:12,8:8,9:3}, 11:{7:55,13:18,10:12,9:10,8:5},
      13:{10:28,7:22,11:22,14:15,9:8,8:5}, 14:{7:35,11:28,13:18,10:14,9:5},
      17:{7:32,11:28,14:22,10:18}, 27:{7:62,13:18,10:12,9:8}}},
  'rock':{'major':{
      0:{3:20,4:18,5:12,18:18,1:6,16:8,17:6,2:4,6:2,22:4,21:2},
      1:{4:40,3:20,0:15,5:10,18:10,27:5}, 2:{3:30,5:30,4:15,0:10,18:10,1:5},
      3:{0:30,4:25,5:10,18:20,1:8,17:7}, 4:{0:35,5:20,3:20,18:12,1:8,2:5},
      5:{3:28,18:20,4:20,0:15,17:10,1:7}, 6:{0:65,5:20,1:15},
      16:{0:30,5:20,3:18,18:18,4:14}, 17:{0:28,18:22,4:25,3:15,5:10},
      18:{0:35,3:28,5:12,4:12,17:8,1:5},
      21:{4:70,27:20,0:10}, 22:{5:65,0:20,18:15},
      25:{4:45,0:30,26:15,1:10}, 26:{3:40,4:35,0:25}, 27:{0:55,5:20,3:12,18:8,1:5}},
   'minor':{
      7:{9:18,10:18,13:15,14:18,11:12,8:5,17:7,18:7},
      8:{11:40,7:20,10:15,27:15,9:10}, 9:{7:30,10:25,13:20,14:15,11:10},
      10:{11:35,7:20,14:15,13:15,8:10,9:5}, 11:{7:55,13:15,10:15,9:10,14:5},
      13:{10:25,11:25,7:20,14:15,9:10,8:5}, 14:{7:35,11:25,10:20,13:15,9:5},
      17:{7:35,11:30,14:20,10:15}, 18:{7:30,13:25,10:20,11:15,14:10},
      27:{7:60,13:15,10:15,9:10}}},
  'blues':{'major':{
      26:{25:35,27:25,0:20,3:15,5:5}, 25:{26:50,27:20,0:20,5:10},
      27:{26:40,25:30,0:20,5:10}, 0:{3:30,4:25,26:20,25:15,5:10},
      3:{0:35,4:25,26:20,25:15,5:5}, 4:{0:40,3:30,26:20,5:10},
      5:{3:30,4:25,0:20,26:15,1:10}, 1:{4:50,27:25,0:15,3:10},
      28:{27:55,26:25,0:15,25:5}},
   'minor':{
      7:{10:30,14:25,11:20,13:15,9:10}, 10:{11:35,7:25,14:20,13:15,9:5},
      11:{7:50,13:20,10:15,14:15}, 13:{10:30,11:25,7:20,14:15,9:10},
      14:{7:35,11:30,10:20,13:15}}},
  'jazz':{'major':{
      0:{1:20,28:20,3:10,5:10,22:10,21:10,20:8,19:8,2:4},
      1:{4:30,27:30,28:15,29:15,0:10}, 2:{5:30,3:25,1:15,0:15,4:15},
      3:{0:20,4:20,1:15,28:15,27:15,5:15}, 4:{0:50,5:15,1:10,29:10,3:8,2:7},
      5:{1:25,28:20,3:15,4:15,0:15,22:10}, 6:{0:60,5:15,1:15,29:10},
      19:{1:65,28:20,0:15}, 20:{3:60,25:25,0:15}, 21:{4:70,27:20,29:10},
      22:{5:55,0:15,28:20,1:10}, 27:{0:55,5:15,1:10,3:10,29:10},
      28:{27:40,29:30,4:15,0:10,5:5}, 29:{0:65,5:15,1:10,3:10},
      15:{4:55,27:25,29:15,0:5}, 23:{4:55,27:25,29:15,0:5}},
   'minor':{
      7:{10:20,8:15,13:15,11:20,28:10,27:10,15:5,29:5},
      8:{11:45,27:25,29:15,7:10,13:5}, 10:{11:35,8:25,7:20,13:12,27:8},
      11:{7:55,13:15,10:12,8:8,29:10}, 13:{10:28,8:22,11:22,7:18,14:10},
      14:{7:35,11:30,13:20,10:15}, 27:{7:60,13:15,10:12,8:8,29:5},
      28:{27:45,29:30,11:15,7:10}, 29:{7:65,13:15,10:12,8:8}}},
  # ── Cinematic — Hans Zimmer / Ramin Djawadi style ──────────────────────────
  # Heavy modal interchange, bVI/bVII vamps, slow harmonic rhythm, minor bias.
  # Major key: pop-cinematic — vi/IV centred, frequent bVII and bVI.
  # Minor key: heroic/dark — i, bVI, bVII, bIII, iv form the backbone.
  'cinematic':{'major':{
      0:{5:25, 3:18, 18:18, 17:12, 4:10, 16:8, 1:5, 22:4},
      1:{4:35, 3:25, 18:15, 0:10, 5:10, 27:5},
      2:{5:30, 3:25, 18:18, 0:12, 4:8, 1:7},
      3:{0:25, 5:20, 18:18, 17:14, 4:13, 1:6, 22:4},
      4:{0:25, 5:30, 3:20, 17:12, 18:10, 22:3},
      5:{3:25, 18:22, 17:18, 0:15, 4:13, 16:5, 22:2},
      6:{0:60, 5:25, 1:15},
      16:{0:18, 5:22, 3:18, 18:22, 17:15, 4:5},
      17:{0:18, 18:30, 5:18, 4:14, 3:12, 16:8},
      18:{0:28, 5:22, 17:18, 3:18, 4:10, 16:4},
      22:{5:60, 0:20, 18:12, 17:8},
      27:{0:55, 5:25, 17:12, 18:8},
   },
   'minor':{
      7:{13:25, 10:20, 14:20, 9:15, 11:10, 17:5, 18:5},
      8:{11:40, 7:18, 10:18, 27:15, 9:9},
      9:{7:25, 13:22, 10:20, 14:18, 11:10, 17:5},
      10:{11:25, 13:22, 7:20, 14:18, 9:10, 8:5},
      11:{7:55, 13:18, 10:13, 9:9, 8:5},
      13:{14:25, 10:22, 11:18, 7:18, 9:12, 8:5},
      14:{7:25, 13:25, 10:22, 11:18, 9:8, 17:2},
      17:{7:25, 11:22, 14:22, 13:18, 10:13},
      18:{7:25, 13:22, 10:18, 14:17, 11:13, 17:5},
      27:{7:55, 13:20, 10:15, 9:10},
   }},
}

START_WEIGHTS = {
    ('classical','major'):{0:70,5:10,1:5,3:8,4:5,2:2},
    ('classical','minor'):{7:70,13:10,9:8,10:7,11:5},
    ('pop','major'):{0:50,5:15,1:10,3:12,4:8,2:5},
    ('pop','minor'):{7:50,13:15,9:10,10:12,11:8,14:5},
    ('rock','major'):{0:45,5:15,3:12,18:12,4:8,16:5,17:3},
    ('rock','minor'):{7:45,13:15,9:12,14:12,10:8,17:5,18:3},
    ('blues','major'):{26:35,0:30,25:20,3:10,4:5},
    ('blues','minor'):{7:55,10:20,13:15,14:10},
    ('jazz','major'):{0:35,1:15,28:15,3:10,5:12,2:8,22:5},
    ('jazz','minor'):{7:40,10:15,8:15,13:12,11:10,28:8},
    ('cinematic','major'):{0:30, 5:22, 3:15, 18:13, 17:8, 4:7, 1:5},
    ('cinematic','minor'):{7:38, 13:18, 9:12, 14:12, 10:8, 17:6, 18:6},
}

# Map level (1-5) to Markov difficulty gates
LEVEL_TO_MARKOV = {1:'beginner',2:'beginner',3:'intermediate',4:'intermediate',5:'advanced'}
DIFFICULTY_ALLOWED = {
    'beginner':     {0,1,3,4,5,6,7,9,10,11,13,14},
    'intermediate': {0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,16,17,18,21,22,25,26,27,28},
    'advanced':     set(range(30)),
}
TONIC_IDX = {'major':0,'minor':7}

def _weighted_choice(weights: dict, allowed: set) -> Optional[int]:
    filtered = {k:v for k,v in weights.items() if k in allowed}
    if not filtered: return None
    total = sum(filtered.values()); r = random.random()*total; cum = 0
    for idx,w in filtered.items():
        cum += w
        if r <= cum: return idx
    return list(filtered.keys())[-1]

def generate_progression(length=4, genre='pop', tonality='major',
                         difficulty='intermediate', tonic_semitone=0,
                         cadence=True) -> list:
    allowed = DIFFICULTY_ALLOWED[difficulty]
    mat = TRANS.get(genre, TRANS['pop']).get(tonality, {})
    tonic_idx = TONIC_IDX[tonality]
    sw = START_WEIGHTS.get((genre,tonality), {tonic_idx:100})
    current = _weighted_choice(sw, allowed) or tonic_idx
    progression = []; prev = None
    for step in range(length):
        chord = CHORD_BY_IDX.get(current, CHORD_BY_IDX[tonic_idx])
        ivs = QUALITY_INTERVALS.get(chord.quality, [0,4,7])
        root = (tonic_semitone + chord.semitones) % 12
        notes = [NOTES[(root+iv)%12] for iv in ivs]
        progression.append({'chord':chord,'roman':chord.roman,'quality':chord.quality,
                            'function':chord.function,'root_semitone':root,
                            'notes':notes,'description':chord.description})
        prev = current
        if cadence and step == length-2 and length >= 3:
            dom = 4 if tonality=='major' else 11
            if dom in allowed: current = dom; continue
        transitions = mat.get(current, {})
        if not transitions: transitions = mat.get(tonic_idx, {tonic_idx:1})
        nxt = _weighted_choice(transitions, allowed)
        if nxt is None: nxt = tonic_idx
        if nxt == prev and length > 2:
            alt = _weighted_choice(transitions, allowed-{prev})
            if alt is not None: nxt = alt
        current = nxt
    if cadence and progression:
        t = CHORD_BY_IDX[tonic_idx]
        ivs = QUALITY_INTERVALS.get(t.quality,[0,3,7])
        root = (tonic_semitone+t.semitones)%12
        notes = [NOTES[(root+iv)%12] for iv in ivs]
        progression[-1]={'chord':t,'roman':t.roman,'quality':t.quality,
                         'function':t.function,'root_semitone':root,
                         'notes':notes,'description':t.description}
    return progression

# ─── Algorithmic inversion / subset voicing generator ─────────────────────────

def get_inversions(base_intervals: list) -> list:
    ordinals = ['Root position','1st inversion','2nd inversion','3rd inversion',
                '4th inversion','5th inversion','6th inversion']
    names = ordinals[:len(base_intervals)]
    inversions = []; current = list(base_intervals)
    for i in range(len(base_intervals)):
        inversions.append((names[i], current[:]))
        lowest = current[0]
        rotated = [iv-lowest for iv in current[1:]] + [12-lowest+current[0] if lowest!=0 else 12]
        mn = min(rotated); current = [iv-mn for iv in rotated]
    return inversions

def _interval_names(intervals: list) -> list:
    n = {0:'root',2:'9th',3:'m3',4:'M3',5:'P4/11th',6:'b5',7:'5th',8:'#5',
         9:'dim7',10:'m7',11:'M7',13:'b9',14:'9th',15:'#9',17:'11th',
         18:'#11',20:'b13',21:'13th'}
    return [n.get(iv%12 if iv>12 else iv, str(iv)) for iv in intervals]

def get_guitar_subsets(intervals: list, min_notes=3, max_notes=4) -> list:
    if len(intervals) <= max_notes:
        return [('Full voicing', intervals, [])]
    root   = 0
    third  = next((iv for iv in intervals if iv in [3,4,5]), None)
    seventh= next((iv for iv in intervals if iv in [9,10,11]), None)
    colour = max(intervals)
    must_keep = {root, colour}
    if third   is not None: must_keep.add(third)
    if seventh is not None: must_keep.add(seventh)
    results = []; seen = set()
    for n in range(min_notes, max_notes+1):
        for combo in combinations(intervals, n):
            combo_set = set(combo)
            required = must_keep & set(intervals)
            if not required.issubset(combo_set): continue
            if max(combo)-min(combo) > 14: continue
            key = tuple(sorted(combo))
            if key in seen: continue
            seen.add(key)
            dropped = [iv for iv in intervals if iv not in combo_set]
            label = f'Drop {", ".join(_interval_names(dropped))}' if dropped else 'Full voicing'
            results.append((label, list(combo), dropped))
    results.sort(key=lambda x:(len(x[2]), max(x[1])-min(x[1])))
    return results[:8]

def get_all_voicings(chord_name: str) -> list:
    if chord_name not in CHORD_LIBRARY: return []
    base = CHORD_LIBRARY[chord_name]['intervals']
    inversions = get_inversions(base); all_voicings = []
    for inv_name, inv_intervals in inversions:
        if len(base) <= 4:
            all_voicings.append({'label':inv_name,'intervals':inv_intervals,
                                 'dropped':[],'inversion':inv_name})
        else:
            for sub_label,sub_ivs,dropped in get_guitar_subsets(inv_intervals):
                all_voicings.append({'label':f'{inv_name} — {sub_label}',
                                     'intervals':sub_ivs,'dropped':dropped,
                                     'inversion':inv_name})
    return all_voicings

# ─── Self-test ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    random.seed(42)
    print('=== Markov generator ===')
    for args in [('pop','major','intermediate',0,4),('rock','minor','advanced',4,4),
                 ('jazz','major','advanced',0,6),('blues','major','intermediate',9,12),
                 ('classical','minor','intermediate',9,4)]:
        genre,ton,diff,tonic,ln = args
        prog = generate_progression(ln,genre,ton,diff,tonic)
        romans = '  →  '.join(p['roman'] for p in prog)
        print(f'  {genre:10} {ton:5} {diff:12} key={NOTES[tonic]:3}: {romans}')
    print()
    print('=== Voicing generator ===')
    for name in ['Major','Minor','Full-dim 7','Minor/Major 7','Dominant 9','Minor 11','Dominant 13']:
        v = get_all_voicings(name)
        notes0 = [NOTES[(0+iv)%12] for iv in v[0]['intervals']] if v else []
        print(f'  {name:20} → {len(v):2d} voicings  e.g. {v[0]["label"]}: {notes0}')
    print()
    print('=== Triad/mode counts ===')
    for lv in range(1,6):
        t = sum(1 for v in TRIADS.values() if v['level']<=lv)
        m = sum(1 for v in MODES.values()  if v['level']<=lv)
        p = sum(1 for v in NAMED_PROGRESSIONS if v['level']<=lv)
        print(f'  Level ≤{lv}: {t:2d} triads, {m:2d} modes, {p:2d} named progressions')