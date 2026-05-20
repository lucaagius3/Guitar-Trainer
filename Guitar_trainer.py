"""
Guitar Trainer - Desktop App
Run: python guitar_trainer.py
Requires: Python 3.8+
"""

import tkinter as tk
from tkinter import ttk
import random

# ─── Music Data ────────────────────────────────────────────────────────────────

NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

TUNINGS = {
    'Standard (EADGBe)': [4, 9, 2, 7, 11, 4],
    'Drop D (DADGBe)':   [2, 9, 2, 7, 11, 4],
    'Open G (DGDGBd)':   [2, 7, 2, 7, 11, 2],
    'DADGAD':            [2, 9, 2, 7, 9,  2],
    'Half Down (Eb...)': [3, 8, 1, 6, 10, 3],
}
TUNING_LABELS = {
    'Standard (EADGBe)': ['E','A','D','G','B','e'],
    'Drop D (DADGBe)':   ['D','A','D','G','B','e'],
    'Open G (DGDGBd)':   ['D','G','D','G','B','d'],
    'DADGAD':            ['D','A','D','G','A','D'],
    'Half Down (Eb...)': ['Eb','Ab','Db','Gb','Bb','eb'],
}

# dot_types: colour role per note — root=amber, third=green, fifth=blue, interval=purple
TRIADS = {
    # ── Level 1: Fundamentals ──────────────────────────────────────────────────
    'Power':          {'intervals': [0, 7],        'level': 1, 'dot_types': ['root','fifth']},
    'Major':          {'intervals': [0, 4, 7],     'level': 1, 'dot_types': ['root','third','fifth']},
    'Minor':          {'intervals': [0, 3, 7],     'level': 1, 'dot_types': ['root','third','fifth']},
    # ── Level 2: Core Extensions ───────────────────────────────────────────────
    'Sus2':           {'intervals': [0, 2, 7],     'level': 2, 'dot_types': ['root','interval','fifth']},
    'Sus4':           {'intervals': [0, 5, 7],     'level': 2, 'dot_types': ['root','interval','fifth']},
    'Diminished':     {'intervals': [0, 3, 6],     'level': 2, 'dot_types': ['root','third','fifth']},
    'Augmented':      {'intervals': [0, 4, 8],     'level': 2, 'dot_types': ['root','third','fifth']},
    # ── Level 3: Shell Voicings & Alterations ─────────────────────────────────
    'Major b5':       {'intervals': [0, 4, 6],     'level': 3, 'dot_types': ['root','third','fifth']},
    'Minor #5':       {'intervals': [0, 3, 8],     'level': 3, 'dot_types': ['root','third','fifth']},
    'Shell Dom7':     {'intervals': [0, 4, 10],    'level': 3, 'dot_types': ['root','third','interval']},
    'Shell Min7':     {'intervals': [0, 3, 10],    'level': 3, 'dot_types': ['root','third','interval']},
    'Shell Maj7':     {'intervals': [0, 4, 11],    'level': 3, 'dot_types': ['root','third','interval']},
    'Shell Maj6':     {'intervals': [0, 4, 9],     'level': 3, 'dot_types': ['root','third','interval']},
    'Shell Min6':     {'intervals': [0, 3, 9],     'level': 3, 'dot_types': ['root','third','interval']},
    # ── Level 4: Advanced Colours ──────────────────────────────────────────────
    'Quartal':        {'intervals': [0, 5, 10],    'level': 4, 'dot_types': ['root','interval','interval']},
    'Shell MinMaj7':  {'intervals': [0, 3, 11],    'level': 4, 'dot_types': ['root','third','interval']},
    'Power + b7':     {'intervals': [0, 7, 10],    'level': 4, 'dot_types': ['root','fifth','interval']},
    'Power + Maj7':   {'intervals': [0, 7, 11],    'level': 4, 'dot_types': ['root','fifth','interval']},
    'Power + 6':      {'intervals': [0, 7, 9],     'level': 4, 'dot_types': ['root','fifth','interval']},
    'Power + b6':     {'intervals': [0, 7, 8],     'level': 4, 'dot_types': ['root','fifth','interval']},
    'Phrygian':       {'intervals': [0, 1, 7],     'level': 4, 'dot_types': ['root','interval','fifth']},
    'Tritone Shell':  {'intervals': [0, 6, 10],    'level': 4, 'dot_types': ['root','interval','interval']},
    # ── Level 5: Exotic / Niche ────────────────────────────────────────────────
    'Aug Sus4':       {'intervals': [0, 5, 8],     'level': 5, 'dot_types': ['root','interval','fifth']},
    'Sus2 b5':        {'intervals': [0, 2, 6],     'level': 5, 'dot_types': ['root','interval','fifth']},
    'Sus4 b5':        {'intervals': [0, 5, 6],     'level': 5, 'dot_types': ['root','interval','interval']},
    'Phrygian Tri':   {'intervals': [0, 1, 5],     'level': 5, 'dot_types': ['root','interval','interval']},
    'Whole Tone Tri': {'intervals': [0, 2, 4],     'level': 5, 'dot_types': ['root','interval','third']},
    'Aug Quartal':    {'intervals': [0, 6, 11],    'level': 5, 'dot_types': ['root','interval','interval']},
    'Minor Cluster':  {'intervals': [0, 2, 3],     'level': 5, 'dot_types': ['root','interval','third']},
    'Sus2 + b7':      {'intervals': [0, 2, 10],    'level': 5, 'dot_types': ['root','interval','interval']},
    'Cluster b7':     {'intervals': [0, 1, 10],    'level': 5, 'dot_types': ['root','interval','interval']},
}

MODES = {
    # ── Level 1 ────────────────────────────────────────────────────────────────
    'Ionian (Major)':     {'intervals': [0,2,4,5,7,9,11],     'level': 1},
    'Aeolian (Minor)':    {'intervals': [0,2,3,5,7,8,10],     'level': 1},
    # ── Level 2 ────────────────────────────────────────────────────────────────
    'Major Pentatonic':   {'intervals': [0,2,4,7,9],           'level': 2},
    'Minor Pentatonic':   {'intervals': [0,3,5,7,10],          'level': 2},
    'Blues':              {'intervals': [0,3,5,6,7,10],        'level': 2},
    'Dorian':             {'intervals': [0,2,3,5,7,9,10],      'level': 2},
    'Mixolydian':         {'intervals': [0,2,4,5,7,9,10],      'level': 2},
    # ── Level 3 ────────────────────────────────────────────────────────────────
    'Phrygian':           {'intervals': [0,1,3,5,7,8,10],      'level': 3},
    'Lydian':             {'intervals': [0,2,4,6,7,9,11],      'level': 3},
    'Locrian':            {'intervals': [0,1,3,5,6,8,10],      'level': 3},
    'Harmonic Minor':     {'intervals': [0,2,3,5,7,8,11],      'level': 3},
    'Melodic Minor':      {'intervals': [0,2,3,5,7,9,11],      'level': 3},
    # ── Level 4 ────────────────────────────────────────────────────────────────
    'Phrygian Dominant':  {'intervals': [0,1,4,5,7,8,10],      'level': 4},
    'Lydian Dominant':    {'intervals': [0,2,4,6,7,9,10],      'level': 4},
    'Whole Tone':         {'intervals': [0,2,4,6,8,10],        'level': 4},
    'Half-Whole Dim':     {'intervals': [0,1,3,4,6,7,9,10],    'level': 4},
    'Whole-Half Dim':     {'intervals': [0,2,3,5,6,8,9,11],    'level': 4},
    # ── Level 5 ────────────────────────────────────────────────────────────────
    'Altered':            {'intervals': [0,1,3,4,6,8,10],      'level': 5},
    'Hungarian Minor':    {'intervals': [0,2,3,6,7,8,11],      'level': 5},
    'Double Harmonic':    {'intervals': [0,1,4,5,7,8,11],      'level': 5},
    'Bebop Major':        {'intervals': [0,2,4,5,7,8,9,11],    'level': 5},
}

# quality codes: M=major  m=minor  d=diminished  a=augmented  p=power
QUALITY_INTERVALS = {
    'M': [0, 4, 7],
    'm': [0, 3, 7],
    'd': [0, 3, 6],
    'a': [0, 4, 8],
    'p': [0, 7],
}
QUALITY_DOT_TYPES = {
    'M': ['root','third','fifth'],
    'm': ['root','third','fifth'],
    'd': ['root','third','fifth'],
    'a': ['root','third','fifth'],
    'p': ['root','fifth'],
}
QUALITY_LABEL = {'M': '', 'm': 'm', 'd': '°', 'a': '+', 'p': '5'}

# Named progressions — chords are (semitone_offset_from_key_root, quality_code)
NAMED_PROGRESSIONS = [
    # ── Level 1 ────────────────────────────────────────────────────────────────
    {'name': 'I – IV – V',             'genre': 'Blues/Rock',    'level': 1,
     'chords': [(0,'M'),(5,'M'),(7,'M')]},
    {'name': 'I – V – vi – IV',        'genre': 'Pop',           'level': 1,
     'chords': [(0,'M'),(7,'M'),(9,'m'),(5,'M')]},
    {'name': 'I – vi – IV – V',        'genre': 'Pop / 50s',     'level': 1,
     'chords': [(0,'M'),(9,'m'),(5,'M'),(7,'M')]},
    {'name': 'vi – IV – I – V',        'genre': 'Pop',           'level': 1,
     'chords': [(9,'m'),(5,'M'),(0,'M'),(7,'M')]},
    {'name': 'i – bVII – bVI – bVII',  'genre': 'Rock/Metal',    'level': 1,
     'chords': [(0,'m'),(10,'M'),(8,'M'),(10,'M')]},
    # ── Level 2 ────────────────────────────────────────────────────────────────
    {'name': 'I – bVII – IV',          'genre': 'Rock',          'level': 2,
     'chords': [(0,'M'),(10,'M'),(5,'M')]},
    {'name': 'I – V – vi – iii – IV',  'genre': 'Pop/Classical',  'level': 2,
     'chords': [(0,'M'),(7,'M'),(9,'m'),(4,'m'),(5,'M')]},
    {'name': 'I – IV – V – IV',        'genre': 'Rock/Blues',    'level': 2,
     'chords': [(0,'M'),(5,'M'),(7,'M'),(5,'M')]},
    {'name': 'i – bVI – bIII – bVII',  'genre': 'Rock/Metal',    'level': 2,
     'chords': [(0,'m'),(8,'M'),(3,'M'),(10,'M')]},
    {'name': 'I – III – IV – iv',      'genre': 'Rock/Pop',      'level': 2,
     'chords': [(0,'M'),(4,'M'),(5,'M'),(5,'m')]},
    {'name': 'I – IV – ii – V',        'genre': 'Pop/Jazz',      'level': 2,
     'chords': [(0,'M'),(5,'M'),(2,'m'),(7,'M')]},
    {'name': 'i – iv – v – i',         'genre': 'Classical',     'level': 2,
     'chords': [(0,'m'),(5,'m'),(7,'m'),(0,'m')]},
    {'name': 'I – IV – I – V',         'genre': 'Blues',         'level': 2,
     'chords': [(0,'M'),(5,'M'),(0,'M'),(7,'M')]},
    # ── Level 3 ────────────────────────────────────────────────────────────────
    {'name': 'ii – V – I',             'genre': 'Jazz',          'level': 3,
     'chords': [(2,'m'),(7,'M'),(0,'M')]},
    {'name': 'I – vi – ii – V',        'genre': 'Jazz/Pop',      'level': 3,
     'chords': [(0,'M'),(9,'m'),(2,'m'),(7,'M')]},
    {'name': 'IV – V – iii – vi',      'genre': 'Pop',           'level': 3,
     'chords': [(5,'M'),(7,'M'),(4,'m'),(9,'m')]},
    {'name': 'I – bIII – IV',          'genre': 'Blues/Rock',    'level': 3,
     'chords': [(0,'M'),(3,'M'),(5,'M')]},
    {'name': 'I – bVI – bVII – I',     'genre': 'Rock',          'level': 3,
     'chords': [(0,'M'),(8,'M'),(10,'M'),(0,'M')]},
    {'name': 'i – V – i',              'genre': 'Classical',     'level': 3,
     'chords': [(0,'m'),(7,'M'),(0,'m')]},
    {'name': 'I – IV – bVII – IV',     'genre': 'Rock',          'level': 3,
     'chords': [(0,'M'),(5,'M'),(10,'M'),(5,'M')]},
    {'name': 'vi – ii – V – I',        'genre': 'Jazz/Pop',      'level': 3,
     'chords': [(9,'m'),(2,'m'),(7,'M'),(0,'M')]},
    {'name': 'i – iv – bVII – bIII',   'genre': 'Metal/Rock',    'level': 3,
     'chords': [(0,'m'),(5,'m'),(10,'M'),(3,'M')]},
    {'name': 'V – IV – I',             'genre': 'Blues',         'level': 3,
     'chords': [(7,'M'),(5,'M'),(0,'M')]},
    {'name': 'I – II – IV – I',        'genre': 'Rock/Pop',      'level': 3,
     'chords': [(0,'M'),(2,'M'),(5,'M'),(0,'M')]},
    # ── Level 4 ────────────────────────────────────────────────────────────────
    {'name': 'I–IV–vii°–iii–vi–ii–V–I','genre': 'Classical',    'level': 4,
     'chords': [(0,'M'),(5,'M'),(11,'d'),(4,'m'),(9,'m'),(2,'m'),(7,'M'),(0,'M')]},
    {'name': 'iii – IV – I – V',       'genre': 'Pop/Classical', 'level': 4,
     'chords': [(4,'m'),(5,'M'),(0,'M'),(7,'M')]},
    {'name': 'I – III – vi – IV',      'genre': 'Jazz/Pop',      'level': 4,
     'chords': [(0,'M'),(4,'M'),(9,'m'),(5,'M')]},
    {'name': 'i – iv – bII – V',       'genre': 'Classical',     'level': 4,
     'chords': [(0,'m'),(5,'m'),(1,'M'),(7,'M')]},
    {'name': 'I – bVI – IV – bII',     'genre': 'Modern',        'level': 4,
     'chords': [(0,'M'),(8,'M'),(5,'M'),(1,'M')]},
    {'name': 'bVI – bVII – I',         'genre': 'Rock/Classical', 'level': 4,
     'chords': [(8,'M'),(10,'M'),(0,'M')]},
    {'name': 'i – bVI – V – i',        'genre': 'Classical/Metal','level': 4,
     'chords': [(0,'m'),(8,'M'),(7,'M'),(0,'m')]},
    {'name': 'I – IV – #iv° – V',      'genre': 'Classical',     'level': 4,
     'chords': [(0,'M'),(5,'M'),(6,'d'),(7,'M')]},
    {'name': 'i – bVII – bVI – V',     'genre': 'Flamenco',      'level': 4,
     'chords': [(0,'m'),(10,'M'),(8,'M'),(7,'M')]},
    # ── Level 5 ────────────────────────────────────────────────────────────────
    {'name': 'I–V–vi–iii–IV–I–IV–V',  'genre': 'Classical (Canon)','level': 5,
     'chords': [(0,'M'),(7,'M'),(9,'m'),(4,'m'),(5,'M'),(0,'M'),(5,'M'),(7,'M')]},
    {'name': 'I – bII – I',            'genre': 'Jazz/Classical', 'level': 5,
     'chords': [(0,'M'),(1,'M'),(0,'M')]},
    {'name': 'ii – bII – I',           'genre': 'Jazz',           'level': 5,
     'chords': [(2,'m'),(1,'M'),(0,'M')]},
    {'name': 'I – bIII – bVI – bII',   'genre': 'Modern/Jazz',    'level': 5,
     'chords': [(0,'M'),(3,'M'),(8,'M'),(1,'M')]},
    {'name': 'I – #IV° – V',           'genre': 'Classical',      'level': 5,
     'chords': [(0,'M'),(6,'d'),(7,'M')]},
    {'name': 'i – II – iv – I',        'genre': 'Flamenco',       'level': 5,
     'chords': [(0,'m'),(2,'M'),(5,'m'),(0,'M')]},
]

# Transition graph for random progression generation.
# Keys: (semitone, quality).  Values: [(next_semitone, next_quality, min_level), ...]
CHORD_GRAPH = {
    (0, 'M'):  [(5,'M',1),(7,'M',1),(9,'m',1),(2,'m',1),
                (4,'m',2),(10,'M',2),(8,'M',3),(3,'M',3),
                (11,'d',3),(5,'m',3),(1,'M',4)],
    (0, 'm'):  [(5,'m',1),(7,'M',1),(10,'M',1),(8,'M',2),
                (3,'M',2),(5,'M',3),(7,'m',3)],
    (5, 'M'):  [(7,'M',1),(0,'M',1),(2,'m',2),(10,'M',2),(5,'m',3),(11,'d',3)],
    (5, 'm'):  [(0,'M',2),(7,'M',2),(10,'M',2),(0,'m',3)],
    (7, 'M'):  [(0,'M',1),(9,'m',2),(5,'M',2),(2,'m',3),(0,'m',3)],
    (7, 'm'):  [(0,'m',2),(3,'M',2),(8,'M',3)],
    (9, 'm'):  [(2,'m',1),(5,'M',1),(7,'M',2),(0,'M',2),(4,'m',3)],
    (2, 'm'):  [(7,'M',1),(5,'M',2),(11,'d',2),(0,'M',3),(1,'M',4)],
    (4, 'm'):  [(9,'m',2),(5,'M',2),(0,'M',3),(7,'M',3)],
    (4, 'M'):  [(9,'m',3),(7,'M',3),(0,'M',4)],
    (10,'M'):  [(0,'M',2),(5,'M',2),(8,'M',3),(3,'M',3)],
    (8, 'M'):  [(10,'M',2),(7,'M',3),(0,'M',4),(5,'M',3)],
    (3, 'M'):  [(10,'M',2),(5,'M',3),(0,'M',4)],
    (11,'d'):  [(0,'M',2),(7,'M',3)],
    (6, 'd'):  [(7,'M',4),(0,'M',5)],
    (1, 'M'):  [(0,'M',4),(7,'M',4),(5,'M',5)],
    (2, 'M'):  [(5,'M',3),(7,'M',3),(0,'M',4)],
}

DEG_NAMES = {0:'1',1:'b2',2:'2',3:'b3',4:'3',5:'4',6:'b5',7:'5',8:'b6',9:'6',10:'b7',11:'7'}

# ─── Colours ───────────────────────────────────────────────────────────────────

BG     = '#1a1a1a'
PANEL  = '#252525'
PANEL2 = '#2e2e2e'
ACCENT = '#e8a838'
BLUE   = '#5b9fd4'
GREEN  = '#4db896'
PURPLE = '#9b8fe0'
TEXT   = '#e8e8e8'
MUTED  = '#888888'
BTN_BG = '#333333'

# ─── Main App ──────────────────────────────────────────────────────────────────

class GuitarTrainer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Guitar Trainer')
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(900, 600)

        self.mode          = tk.StringVar(value='Notes')
        self.tuning_name   = tk.StringVar(value='Standard (EADGBe)')
        self.root_note     = tk.IntVar(value=0)
        self.reveal        = tk.StringVar(value='Full shape')
        self.difficulty    = tk.IntVar(value=1)
        self.triad_type    = tk.StringVar(value='Major')
        self.mode_type     = tk.StringVar(value='Ionian (Major)')
        self.prog_mode     = tk.StringVar(value='Named')
        self.named_prog_idx = tk.IntVar(value=0)
        self.prog_chord    = 0
        self._rand_prog    = [(0,'M'),(5,'M'),(7,'M'),(0,'M')]
        self._available_progs = NAMED_PROGRESSIONS[:]

        self._build_ui()
        self._render()

    # ── UI Construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        top = tk.Frame(self, bg=PANEL, pady=10, padx=16)
        top.pack(fill='x', side='top')

        tk.Label(top, text='Guitar Trainer', bg=PANEL, fg=TEXT,
                 font=('Helvetica', 16, 'bold')).pack(side='left')

        tab_frame = tk.Frame(top, bg=PANEL)
        tab_frame.pack(side='left', padx=24)
        self._tab_buttons = {}
        for m in ['Notes', 'Triads', 'Modes', 'Progressions']:
            b = tk.Button(tab_frame, text=m, bg=BTN_BG, fg=TEXT, relief='flat',
                          padx=14, pady=5, font=('Helvetica', 11), cursor='hand2',
                          command=lambda v=m: self._set_mode(v))
            b.pack(side='left', padx=3)
            self._tab_buttons[m] = b
        self._highlight_tab('Notes')

        ctrl = tk.Frame(self, bg=PANEL2, padx=16, pady=8)
        ctrl.pack(fill='x')

        self._lbl(ctrl, 'Tuning:').pack(side='left')
        ttk.Combobox(ctrl, textvariable=self.tuning_name,
                     values=list(TUNINGS.keys()), state='readonly', width=22
                     ).pack(side='left', padx=(4, 18))
        self.tuning_name.trace_add('write', lambda *_: self._render())

        self._lbl(ctrl, 'Root:').pack(side='left')
        self._root_cb = ttk.Combobox(ctrl, values=NOTES, state='readonly', width=5)
        self._root_cb.current(0)
        self._root_cb.pack(side='left', padx=(4, 18))
        self._root_cb.bind('<<ComboboxSelected>>', self._on_root_change)

        self._lbl(ctrl, 'Reveal:').pack(side='left')
        ttk.Combobox(ctrl, textvariable=self.reveal,
                     values=['Full shape', 'Root only', 'Partial (root + 5th)'],
                     state='readonly', width=20).pack(side='left', padx=(4, 18))
        self.reveal.trace_add('write', lambda *_: self._render())

        self._lbl(ctrl, 'Level:').pack(side='left')
        lf = tk.Frame(ctrl, bg=PANEL2)
        lf.pack(side='left', padx=(4, 18))
        self._level_btns = {}
        for lv in range(1, 6):
            b = tk.Button(lf, text=str(lv), width=2,
                          bg=ACCENT if lv == 1 else BTN_BG,
                          fg='#1a1a1a' if lv == 1 else TEXT,
                          relief='flat', pady=4, font=('Helvetica', 10),
                          cursor='hand2',
                          command=lambda v=lv: self._set_difficulty(v))
            b.pack(side='left', padx=1)
            self._level_btns[lv] = b

        tk.Button(ctrl, text='⟳ Random root', bg=BTN_BG, fg=TEXT, relief='flat',
                  padx=12, pady=4, font=('Helvetica', 10), cursor='hand2',
                  command=self._random_root).pack(side='left', padx=4)

        self._sub = tk.Frame(self, bg=PANEL, padx=16, pady=8)
        self._sub.pack(fill='x')

        fb_wrap = tk.Frame(self, bg=PANEL2, padx=12, pady=12)
        fb_wrap.pack(fill='x', padx=16, pady=(10, 0))
        self._canvas = tk.Canvas(fb_wrap, bg='#1e1510', height=210, highlightthickness=0)
        self._canvas.pack(fill='x')
        self._canvas.bind('<Configure>', lambda e: self._render())

        self._legend_frame = tk.Frame(self, bg=BG, padx=16, pady=6)
        self._legend_frame.pack(fill='x')

        info_wrap = tk.Frame(self, bg=PANEL, padx=16, pady=14)
        info_wrap.pack(fill='x', padx=16, pady=(8, 16))
        self._info_title = tk.Label(info_wrap, bg=PANEL, fg=TEXT,
                                    font=('Helvetica', 13, 'bold'), anchor='w')
        self._info_title.pack(fill='x')
        self._info_desc = tk.Label(info_wrap, bg=PANEL, fg=MUTED,
                                   font=('Helvetica', 10), anchor='w',
                                   wraplength=860, justify='left')
        self._info_desc.pack(fill='x', pady=(4, 0))
        self._info_hint = tk.Label(info_wrap, bg=PANEL, fg='#555555',
                                   font=('Helvetica', 9, 'italic'), anchor='w')
        self._info_hint.pack(fill='x', pady=(4, 0))

    def _lbl(self, parent, text):
        return tk.Label(parent, text=text, bg=PANEL2, fg=MUTED, font=('Helvetica', 10))

    # ── Mode & Difficulty ──────────────────────────────────────────────────────

    def _set_mode(self, m):
        self.mode.set(m)
        self._highlight_tab(m)
        self.prog_chord = 0
        self._render()

    def _highlight_tab(self, active):
        for name, btn in self._tab_buttons.items():
            if name == active:
                btn.configure(bg=ACCENT, fg='#1a1a1a', font=('Helvetica', 11, 'bold'))
            else:
                btn.configure(bg=BTN_BG, fg=TEXT, font=('Helvetica', 11))

    def _set_difficulty(self, lv):
        self.difficulty.set(lv)
        for v, b in self._level_btns.items():
            b.configure(bg=ACCENT if v == lv else BTN_BG,
                        fg='#1a1a1a' if v == lv else TEXT)
        self.prog_chord = 0
        self._render()

    def _on_root_change(self, _=None):
        self.root_note.set(NOTES.index(self._root_cb.get()))
        self._render()

    def _random_root(self):
        n = random.randint(0, 11)
        self.root_note.set(n)
        self._root_cb.current(n)
        self._render()

    # ── Sub-controls ───────────────────────────────────────────────────────────

    def _rebuild_sub(self):
        for w in self._sub.winfo_children():
            w.destroy()
        m = self.mode.get()
        lv = self.difficulty.get()

        if m == 'Triads':
            available = [k for k, v in TRIADS.items() if v['level'] <= lv]
            if self.triad_type.get() not in available:
                self.triad_type.set(available[0])
            self._lbl(self._sub, 'Type:').pack(side='left')
            cb = ttk.Combobox(self._sub, values=available, state='readonly', width=18)
            cb.set(self.triad_type.get())
            cb.pack(side='left', padx=(4, 8))
            cb.bind('<<ComboboxSelected>>', lambda _, c=cb: self._on_triad_cb(c))

        elif m == 'Modes':
            available = [k for k, v in MODES.items() if v['level'] <= lv]
            if self.mode_type.get() not in available:
                self.mode_type.set(available[0])
            self._lbl(self._sub, 'Mode:').pack(side='left')
            cb = ttk.Combobox(self._sub, values=available, state='readonly', width=22)
            cb.set(self.mode_type.get())
            cb.pack(side='left', padx=(4, 8))
            cb.bind('<<ComboboxSelected>>', lambda _, c=cb: self._on_mode_cb(c))

        elif m == 'Progressions':
            for pm in ('Named', 'Random'):
                active = self.prog_mode.get() == pm
                tk.Button(self._sub, text=pm,
                          bg=ACCENT if active else BTN_BG,
                          fg='#1a1a1a' if active else TEXT,
                          relief='flat', padx=10, pady=4,
                          font=('Helvetica', 10), cursor='hand2',
                          command=lambda v=pm: self._set_prog_mode(v)
                          ).pack(side='left', padx=2)

            if self.prog_mode.get() == 'Named':
                available = [p for p in NAMED_PROGRESSIONS if p['level'] <= lv]
                self._available_progs = available
                idx = min(self.named_prog_idx.get(), len(available) - 1)
                self.named_prog_idx.set(idx)
                names = [f'{p["name"]}  [{p["genre"]}]' for p in available]
                cb = ttk.Combobox(self._sub, values=names, state='readonly', width=38)
                cb.current(idx)
                cb.pack(side='left', padx=(8, 4))
                cb.bind('<<ComboboxSelected>>', lambda _, c=cb: self._on_named_prog_cb(c))
            else:
                self._available_progs = []
                tk.Button(self._sub, text='⟳ Generate',
                          bg=BTN_BG, fg=TEXT, relief='flat', padx=12, pady=4,
                          font=('Helvetica', 10), cursor='hand2',
                          command=self._generate_random_prog
                          ).pack(side='left', padx=8)

            tk.Button(self._sub, text='→ Next',
                      bg=GREEN, fg='#04342C', relief='flat', padx=12, pady=4,
                      font=('Helvetica', 10, 'bold'), cursor='hand2',
                      command=self._next_chord).pack(side='left', padx=(4, 0))

    def _on_triad_cb(self, cb):
        self.triad_type.set(cb.get())
        self._render()

    def _on_mode_cb(self, cb):
        self.mode_type.set(cb.get())
        self._render()

    def _set_prog_mode(self, pm):
        self.prog_mode.set(pm)
        self.prog_chord = 0
        self._render()

    def _on_named_prog_cb(self, cb):
        self.named_prog_idx.set(cb.current())
        self.prog_chord = 0
        self._render()

    def _next_chord(self):
        if self.prog_mode.get() == 'Named':
            prog = self._available_progs[self.named_prog_idx.get()]
            total = len(prog['chords'])
        else:
            total = max(1, len(self._rand_prog))
        self.prog_chord = (self.prog_chord + 1) % total
        self._render()

    def _generate_random_prog(self):
        lv = self.difficulty.get()
        starts = [(0,'M'),(0,'m'),(9,'m'),(5,'M')]
        current = random.choice(starts)
        prog = [current]
        for _ in range(3):
            candidates = [(st, q) for st, q, ml in CHORD_GRAPH.get(current, []) if ml <= lv]
            if not candidates:
                break
            current = random.choice(candidates)
            prog.append(current)
        self._rand_prog = prog
        self.prog_chord = 0
        self._render()

    # ── Dot calculation ────────────────────────────────────────────────────────

    def _get_dots(self):
        tuning = TUNINGS[self.tuning_name.get()]
        root   = self.root_note.get()
        reveal = self.reveal.get()
        mode   = self.mode.get()
        dots   = []

        def note_at(s, f):
            return (tuning[s] + f) % 12

        if mode == 'Notes':
            for s in range(6):
                for f in range(13):
                    n = note_at(s, f)
                    dots.append((s, f, 'root' if n == root else 'all', NOTES[n]))

        elif mode == 'Triads':
            data = TRIADS[self.triad_type.get()]
            intervals  = data['intervals']
            dot_types  = data['dot_types']
            for s in range(6):
                for f in range(13):
                    n  = note_at(s, f)
                    iv = (n - root) % 12
                    if iv in intervals:
                        idx = intervals.index(iv)
                        t   = dot_types[idx] if idx < len(dot_types) else 'interval'
                        if reveal == 'Root only' and t != 'root': continue
                        if reveal == 'Partial (root + 5th)' and t == 'third': continue
                        dots.append((s, f, t, NOTES[n]))

        elif mode == 'Modes':
            intervals = MODES[self.mode_type.get()]['intervals']
            for s in range(6):
                for f in range(13):
                    n  = note_at(s, f)
                    iv = (n - root) % 12
                    if iv in intervals:
                        idx = intervals.index(iv)
                        t = 'root' if idx == 0 else ('fifth' if iv == 7 else 'interval')
                        if reveal == 'Root only' and t != 'root': continue
                        if reveal == 'Partial (root + 5th)' and t == 'interval': continue
                        dots.append((s, f, t, NOTES[n]))

        elif mode == 'Progressions':
            if self.prog_mode.get() == 'Named':
                if not self._available_progs:
                    return dots
                prog   = self._available_progs[self.named_prog_idx.get()]
                chords = prog['chords']
            else:
                if not self._rand_prog:
                    return dots
                chords = self._rand_prog

            chord_st, quality = chords[self.prog_chord % len(chords)]
            chord_root = (root + chord_st) % 12
            intervals  = QUALITY_INTERVALS.get(quality, [0, 4, 7])
            dot_types  = QUALITY_DOT_TYPES.get(quality, ['root','third','fifth'])
            for s in range(6):
                for f in range(13):
                    n  = note_at(s, f)
                    iv = (n - chord_root) % 12
                    if iv in intervals:
                        idx = intervals.index(iv)
                        t   = dot_types[idx] if idx < len(dot_types) else 'interval'
                        if reveal == 'Root only' and t != 'root': continue
                        if reveal == 'Partial (root + 5th)' and t == 'third': continue
                        dots.append((s, f, t, NOTES[n]))

        return dots

    # ── Fretboard drawing ──────────────────────────────────────────────────────

    def _draw_fretboard(self, dots):
        c = self._canvas
        c.delete('all')
        W = c.winfo_width() or 900
        H, LEFT, RIGHT, TOP, STR_GAP, FRETS = 210, 48, 16, 28, 28, 12
        FW = (W - LEFT - RIGHT) / FRETS

        for f in range(FRETS + 1):
            x = LEFT + f * FW
            c.create_line(x, TOP-6, x, TOP+5*STR_GAP+6,
                          fill='#5a4a30' if f == 0 else '#3d3020',
                          width=3 if f == 0 else 1)

        for f in [3, 5, 7, 9, 12]:
            mx = LEFT + (f - 0.5) * FW
            if f == 12:
                c.create_oval(mx-18, H-14, mx-10, H-6, fill='#3d3020', outline='')
                c.create_oval(mx+10, H-14, mx+18, H-6, fill='#3d3020', outline='')
            else:
                c.create_oval(mx-5, H-14, mx+5, H-6, fill='#3d3020', outline='')

        for f in range(1, FRETS + 1):
            c.create_text(LEFT + (f-0.5)*FW, H-3, text=str(f),
                          fill='#4a4030', font=('Helvetica', 9))

        str_labels = TUNING_LABELS[self.tuning_name.get()]
        for s in range(6):
            y = TOP + s * STR_GAP
            c.create_line(LEFT-4, y, W-RIGHT, y,
                          fill='#7a6a50', width=max(0.5, 3.5-s*0.5))
            c.create_text(LEFT-8, y, text=str_labels[s],
                          anchor='e', fill=MUTED, font=('Helvetica', 10))

        c.create_rectangle(LEFT-5, TOP-6, LEFT-1, TOP+5*STR_GAP+6,
                           fill='#c8b878', outline='')

        DOT_COLORS = {
            'root':     (ACCENT,  '#412402'),
            'third':    (GREEN,   '#04342C'),
            'fifth':    (BLUE,    '#042C53'),
            'interval': (PURPLE,  '#26215C'),
            'all':      (None,    MUTED),
        }

        for (s, f, typ, label) in dots:
            x = LEFT - 20 if f == 0 else LEFT + (f-0.5)*FW
            y = TOP + s * STR_GAP
            fill_col, text_col = DOT_COLORS.get(typ, (None, MUTED))
            if typ == 'all':
                r = 9
                c.create_oval(x-r, y-r, x+r, y+r, outline='#3a3020', fill='#2a2010', width=1)
                c.create_text(x, y, text=label, fill='#4a4535', font=('Helvetica', 8))
            else:
                r = 13
                c.create_oval(x-r, y-r, x+r, y+r, fill=fill_col, outline='', width=0)
                c.create_text(x, y+1, text=label, fill=text_col, font=('Helvetica', 9, 'bold'))

    # ── Legend ─────────────────────────────────────────────────────────────────

    def _rebuild_legend(self):
        for w in self._legend_frame.winfo_children():
            w.destroy()
        mode = self.mode.get()
        items = [('●', ACCENT, 'Root')]
        if mode != 'Notes':
            items += [('●', GREEN, '3rd'), ('●', BLUE, '5th')]
        if mode in ('Modes', 'Triads'):
            items.append(('●', PURPLE, 'Other'))
        for sym, col, lbl in items:
            f = tk.Frame(self._legend_frame, bg=BG)
            f.pack(side='left', padx=8)
            tk.Label(f, text=sym, bg=BG, fg=col, font=('Helvetica', 14)).pack(side='left')
            tk.Label(f, text=lbl, bg=BG, fg=MUTED, font=('Helvetica', 9)).pack(side='left', padx=(2,0))

    # ── Info card ──────────────────────────────────────────────────────────────

    def _update_info(self):
        mode = self.mode.get()
        root = NOTES[self.root_note.get()]

        if mode == 'Notes':
            self._info_title.config(text=f'All {root} notes on the neck')
            self._info_desc.config(text='')
            self._info_hint.config(text='Say the note name aloud each time you play it.')

        elif mode == 'Triads':
            t    = self.triad_type.get()
            data = TRIADS[t]
            ivs  = data['intervals']
            formula    = ' – '.join(DEG_NAMES.get(i, str(i)) for i in ivs)
            note_names = '  –  '.join(NOTES[(self.root_note.get() + i) % 12] for i in ivs)
            self._info_title.config(text=f'{root} {t}')
            self._info_desc.config(text=f'{formula}     ({note_names})')
            self._info_hint.config(text=f'Level {data["level"]}  ·  Use "Root only" to quiz yourself.')

        elif mode == 'Modes':
            mt   = self.mode_type.get()
            data = MODES[mt]
            formula = '  '.join(DEG_NAMES.get(i, str(i)) for i in data['intervals'])
            self._info_title.config(text=f'{root} {mt}')
            self._info_desc.config(text=formula)
            self._info_hint.config(text=f'Level {data["level"]}  ·  Learn one position, then connect across the neck.')

        elif mode == 'Progressions':
            if self.prog_mode.get() == 'Named':
                if not self._available_progs:
                    return
                prog   = self._available_progs[self.named_prog_idx.get()]
                chords = prog['chords']
                total  = len(chords)
                st, q  = chords[self.prog_chord % total]
                cr     = NOTES[(self.root_note.get() + st) % 12]
                seq    = '  →  '.join(
                    f'{NOTES[(self.root_note.get()+s)%12]}{QUALITY_LABEL[q2]}'
                    for s, q2 in chords)
                self._info_title.config(
                    text=f'{root} — {prog["name"]}  [{prog["genre"]}  Lv{prog["level"]}]')
                self._info_desc.config(
                    text=f'{seq}\nNow: {cr}{QUALITY_LABEL[q]}  (chord {self.prog_chord%total+1} of {total})')
                self._info_hint.config(text='→ Next steps through the progression.')
            else:
                prog  = self._rand_prog
                total = max(1, len(prog))
                st, q = prog[self.prog_chord % total]
                cr    = NOTES[(self.root_note.get() + st) % 12]
                seq   = '  →  '.join(
                    f'{NOTES[(self.root_note.get()+s)%12]}{QUALITY_LABEL[q2]}'
                    for s, q2 in prog)
                self._info_title.config(text=f'{root} — Random Progression  [Lv{self.difficulty.get()}]')
                self._info_desc.config(
                    text=f'{seq}\nNow: {cr}{QUALITY_LABEL[q]}  (chord {self.prog_chord%total+1} of {total})')
                self._info_hint.config(text='⟳ Generate for a new progression. → Next to step through.')

    # ── Master render ──────────────────────────────────────────────────────────

    def _render(self, *_):
        self._rebuild_sub()
        self._rebuild_legend()
        dots = self._get_dots()
        self._draw_fretboard(dots)
        self._update_info()


# ─── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app = GuitarTrainer()
    app.mainloop()
