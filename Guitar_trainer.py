"""
guitar_trainer.py
=================
Guitar Trainer — desktop GUI app.
Run: python guitar_trainer.py
Requires: Python 3.8+ with tkinter (standard on Windows/Mac; `apt install python3-tk` on Linux)
Place harmony_engine.py in the same folder.
"""

import tkinter as tk
from tkinter import ttk
import random, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from harmony_engine import (
        NOTES, TRIADS, MODES, NAMED_PROGRESSIONS, CHORD_GRAPH,
        QUALITY_INTERVALS, QUALITY_DOT_TYPES, QUALITY_LABEL, DEG_NAMES,
        CHORD_LIBRARY, get_all_voicings, get_inversions, LEVEL_TO_MARKOV,
        generate_progression, TONIC_IDX,
    )
    ENGINE_OK = True
except ImportError as e:
    ENGINE_OK = False; ENGINE_ERR = str(e)

TUNINGS = {
    'Standard (EADGBe)': [4,9,2,7,11,4],
    'Drop D (DADGBe)':   [2,9,2,7,11,4],
    'Open G (DGDGBd)':   [2,7,2,7,11,2],
    'DADGAD':            [2,9,2,7,9,2],
    'Half Down (Eb)':    [3,8,1,6,10,3],
}
TUNING_LABELS = {
    'Standard (EADGBe)': ['E','A','D','G','B','e'],
    'Drop D (DADGBe)':   ['D','A','D','G','B','e'],
    'Open G (DGDGBd)':   ['D','G','D','G','B','d'],
    'DADGAD':            ['D','A','D','G','A','D'],
    'Half Down (Eb)':    ['Eb','Ab','Db','Gb','Bb','eb'],
}

BG='#1a1a1a'; PANEL='#252525'; PANEL2='#2e2e2e'
ACCENT='#e8a838'; BLUE='#5b9fd4'; GREEN='#4db896'
PURPLE='#9b8fe0'; TEXT='#e8e8e8'; MUTED='#888888'; BTN_BG='#333333'

class GuitarTrainer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Guitar Trainer')
        self.configure(bg=BG); self.minsize(1280, 720); self.resizable(True,True)
        # Aspect-ratio target: 16:9. Set initial size to 1600x900 if screen allows.
        try:
            sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
            w = min(1600, int(sw * 0.95)); h = min(900, int(sh * 0.92))
            self.geometry(f'{w}x{h}')
        except Exception:
            pass

        # ── Core state ─────────────────────────────────────────────────────
        self.mode        = 'Notes'
        self.tuning_name = tk.StringVar(value='Standard (EADGBe)')
        self.root_note   = 0
        self.reveal      = tk.StringVar(value='Full shape')
        # Two independent dials:
        #   adventure  = musical adventurousness (which library items unlock)
        #   difficulty = fretboard scope / voicing complexity (positions, inversions)
        self.adventure  = 1   # 1–5
        self.difficulty = 1   # 1–5

        # Triads state
        self.triad_type  = 'Major'
        self.triad_inv   = 0           # inversion index into get_all_voicings()

        # Modes state
        self.mode_type   = 'Ionian (Major)'

        # Progressions state
        self.prog_submode   = 'Named'   # 'Named' | 'Random' | 'Markov'
        self.named_prog_idx = 0
        self.prog_chord     = 0
        self._available_progs = []
        self._rand_prog       = [(0,'M'),(5,'M'),(7,'M'),(0,'M')]
        self._markov_prog     = []      # list of dicts from generate_progression()
        self.markov_genre     = tk.StringVar(value='pop')
        self.markov_tonality  = tk.StringVar(value='major')

        # ── Practice mode state ───────────────────────────────────────────
        self.prac_drill      = tk.StringVar(value='Triads')
        self.prac_sequence   = tk.StringVar(value='Random')
        # Tempo: BPM (beats per minute) + beats-per-target
        # Standard drills use 1-16 beats; Modes drill allows 1-30 beats.
        self.prac_bpm    = tk.IntVar(value=80)
        self.prac_beats  = tk.IntVar(value=4)
        self.prac_root_mode  = tk.StringVar(value='Random')  # 'Fixed' | 'Random'
        self.prac_running    = False
        self.prac_timer_id   = None   # after() handle
        self._prac_target    = None   # current target dict
        self._prac_history   = []     # last 6 targets (name, got_it)
        self._prac_score     = {'correct':0,'missed':0,'streak':0,'best':0}
        # Infinite progression state (Markov never-repeat)
        self._inf_prog_idx   = 0
        self._inf_prog_cache = []     # growing list of Markov chord dicts
        self._inf_history    = []     # rolling last-16 chord dicts for infinite mode

        # Strings setting — which strings the root may appear on (0=low E … 5=high e)
        # Stored as list of BooleanVars, one per string
        self._string_vars = [tk.BooleanVar(value=True) for _ in range(6)]

        # Inversion root mode — when True, colour position-0 of voicing as 'root'
        self.prac_inv_root = tk.BooleanVar(value=False)

        # Use 24-fret display (else 12)
        self.prac_24frets = tk.BooleanVar(value=False)
        # Currently-highlighted target note within a Modes scale (rendered red)
        self._modes_target_note = None   # semitone of note user should land on

        # Loop mode: which named progression to cycle (index into NAMED_PROGRESSIONS filtered by level)
        self.prac_loop_prog_idx = tk.IntVar(value=0)
        # Loop mode internal cursor — which chord in the progression we're on
        self._loop_chord_idx = 0
        # When True, Loop mode auto-generates a Markov progression each cycle
        # drawn from the selected genres. When False, uses the dropdown.
        self.prac_loop_generate = tk.BooleanVar(value=False)
        # When True, the random triad shape re-rolls on every loop cycle.
        # When False, each chord position locks its shape until something changes.
        self.prac_loop_change_triads = tk.BooleanVar(value=False)
        # Cache of picked triad shapes per chord position in the current loop
        self._loop_triad_shapes = {}
        # Which genres the Loop generator pulls from (multi-select)
        self.prac_loop_genres = {
            'classical': tk.BooleanVar(value=True),
            'pop':       tk.BooleanVar(value=True),
            'rock':      tk.BooleanVar(value=False),
            'blues':     tk.BooleanVar(value=False),
            'jazz':      tk.BooleanVar(value=False),
            'cinematic': tk.BooleanVar(value=False),
        }
        # Length of the auto-generated loop progression
        self.prac_loop_length = tk.IntVar(value=4)
        # Cache of the currently generated loop progression (list of chord dicts)
        self._generated_loop_prog = []

        # For Triads/Modes drill inside Loop/Infinite mode:
        #   'Follow progression' = use chord quality from progression (Major/minor/dim)
        #   specific name        = always use this triad type regardless of progression
        self.prac_triad_override = tk.StringVar(value='Follow progression')
        self.prac_mode_override  = tk.StringVar(value='Follow progression')

        self._build_ui()
        self._set_mode('Notes')

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _lbl(self, p, t, bg=None):
        return tk.Label(p, text=t, bg=bg or PANEL2, fg=MUTED, font=('Helvetica',10))

    def _btn(self, p, text, cmd, active=False, color=None, bg_override=None):
        bg = bg_override if bg_override else (color if color else (ACCENT if active else BTN_BG))
        fg = '#1a1a1a' if (active or bg_override in (GREEN,BLUE)) else TEXT
        return tk.Button(p, text=text, bg=bg, fg=fg, relief='flat',
                         padx=10, pady=4, font=('Helvetica',10), cursor='hand2', command=cmd)

    # ── UI build ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top bar
        top = tk.Frame(self, bg=PANEL, pady=10, padx=16); top.pack(fill='x')
        tk.Label(top, text='🎸  Guitar Trainer', bg=PANEL, fg=TEXT,
                 font=('Helvetica',16,'bold')).pack(side='left')
        self._tab_btns = {}
        tf = tk.Frame(top, bg=PANEL); tf.pack(side='left', padx=24)
        for m in ['Notes','Triads','Modes','Progressions','Practice']:
            b = tk.Button(tf, text=m, bg=BTN_BG, fg=TEXT, relief='flat',
                          padx=14, pady=5, font=('Helvetica',11), cursor='hand2', bd=0,
                          command=lambda v=m: self._set_mode(v))
            b.pack(side='left', padx=3); self._tab_btns[m] = b

        # Global controls
        ctrl = tk.Frame(self, bg=PANEL2, padx=16, pady=8); ctrl.pack(fill='x')
        self._lbl(ctrl,'Tuning:').pack(side='left')
        ttk.Combobox(ctrl, textvariable=self.tuning_name,
                     values=list(TUNINGS.keys()), state='readonly', width=22
                     ).pack(side='left', padx=(4,18))
        self.tuning_name.trace_add('write', lambda *_: self._render())

        self._lbl(ctrl,'Root:').pack(side='left')
        self._root_cb = ttk.Combobox(ctrl, values=NOTES, state='readonly', width=5)
        self._root_cb.current(0); self._root_cb.pack(side='left', padx=(4,18))
        self._root_cb.bind('<<ComboboxSelected>>', self._on_root)

        self._lbl(ctrl,'Reveal:').pack(side='left')
        ttk.Combobox(ctrl, textvariable=self.reveal,
                     values=['Full shape','Root only','Partial (root + 5th)'],
                     state='readonly', width=22).pack(side='left', padx=(4,18))
        self.reveal.trace_add('write', lambda *_: self._render())

        self._lbl(ctrl,'Level:').pack(side='left')
        self._lvl_btns = {}
        lf = tk.Frame(ctrl, bg=PANEL2); lf.pack(side='left', padx=(4,18))
        for lv in range(1,6):
            b = tk.Button(lf, text=str(lv), width=2,
                          bg=ACCENT if lv==1 else BTN_BG,
                          fg='#1a1a1a' if lv==1 else TEXT,
                          relief='flat', pady=4, font=('Helvetica',10), cursor='hand2',
                          command=lambda v=lv: self._set_level(v))
            b.pack(side='left', padx=1); self._lvl_btns[lv] = b

        tk.Button(ctrl, text='⟳  Random root', bg=BTN_BG, fg=TEXT, relief='flat',
                  padx=12, pady=4, font=('Helvetica',10), cursor='hand2',
                  command=self._random_root).pack(side='left', padx=4)

        # Sub-control panel
        self._sub = tk.Frame(self, bg=PANEL, padx=16, pady=8); self._sub.pack(fill='x')

        # Fretboard
        fb = tk.Frame(self, bg=PANEL2, padx=12, pady=12)
        fb.pack(fill='x', padx=16, pady=(10,0))
        self._canvas = tk.Canvas(fb, bg='#1e1510', height=210, highlightthickness=0)
        self._canvas.pack(fill='x')
        self._canvas.bind('<Configure>', lambda e: self._render())

        # Legend
        self._legend = tk.Frame(self, bg=BG, padx=16, pady=6); self._legend.pack(fill='x')

        # Info card
        ic = tk.Frame(self, bg=PANEL, padx=16, pady=14)
        ic.pack(fill='x', padx=16, pady=(8,4))
        self._info_title = tk.Label(ic, bg=PANEL, fg=TEXT,
                                    font=('Helvetica',13,'bold'), anchor='w')
        self._info_title.pack(fill='x')
        self._info_desc = tk.Label(ic, bg=PANEL, fg=MUTED, font=('Helvetica',10),
                                   anchor='w', wraplength=920, justify='left')
        self._info_desc.pack(fill='x', pady=(4,0))
        self._info_hint = tk.Label(ic, bg=PANEL, fg='#555555',
                                   font=('Helvetica',9,'italic'), anchor='w')
        self._info_hint.pack(fill='x', pady=(3,0))

        # Chord chips (progressions only)
        self._chip_frame = tk.Frame(self, bg=PANEL2, padx=16, pady=8)
        self._chip_frame.pack(fill='x', padx=16, pady=(4,12))

        # Keep refs for page-swap
        self._fb_outer = fb
        self._info_card = ic

        # Build practice page (hidden until Practice tab selected)
        self._build_practice_page()

    # ── Mode / level ───────────────────────────────────────────────────────────

    def _set_mode(self, m):
        prev = self.mode
        self.mode = m
        for name, btn in self._tab_btns.items():
            btn.configure(bg=ACCENT if name==m else BTN_BG,
                          fg='#1a1a1a' if name==m else TEXT,
                          font=('Helvetica',11,'bold' if name==m else 'normal'))
        # Stop practice timer when leaving Practice tab
        if prev == 'Practice' and m != 'Practice':
            self._prac_stop()
        if m == 'Practice':
            self._show_practice_page()
        else:
            self._show_library_page()
        self.prog_chord = 0; self._render()

    def _set_level(self, lv):
        self.level = lv
        for v,b in self._lvl_btns.items():
            b.configure(bg=ACCENT if v==lv else BTN_BG, fg='#1a1a1a' if v==lv else TEXT)
        self.prog_chord = 0; self._render()

    def _on_root(self, *_):
        self.root_note = NOTES.index(self._root_cb.get()); self._render()

    def _random_root(self):
        n = random.randint(0,11); self.root_note = n
        self._root_cb.current(n); self._render()

    # ── Sub-controls ───────────────────────────────────────────────────────────

    def _rebuild_sub(self):
        for w in self._sub.winfo_children(): w.destroy()
        m = self.mode; adv = self.adventure

        if m == 'Triads':
            available = [k for k,v in TRIADS.items() if v['level'] <= lv]
            if self.triad_type not in available: self.triad_type = available[0]
            row = tk.Frame(self._sub, bg=PANEL); row.pack(fill='x', pady=(0,4))
            self._lbl(row,'Type:', PANEL).pack(side='left')
            cb = ttk.Combobox(row, values=available, state='readonly', width=20)
            cb.set(self.triad_type); cb.pack(side='left', padx=(4,12))
            cb.bind('<<ComboboxSelected>>', lambda e,c=cb: self._on_triad_cb(c))
            # Inversion selector (from get_all_voicings)
            voicings = get_all_voicings(self.triad_type) if self.triad_type in CHORD_LIBRARY else []
            if voicings:
                self._lbl(row,'Voicing:', PANEL).pack(side='left')
                inv_labels = [v['label'] for v in voicings]
                self.triad_inv = min(self.triad_inv, len(voicings)-1)
                cb2 = ttk.Combobox(row, values=inv_labels, state='readonly', width=36)
                cb2.current(self.triad_inv); cb2.pack(side='left', padx=(4,0))
                cb2.bind('<<ComboboxSelected>>', lambda e,c=cb2,vs=voicings: self._on_inv_cb(c,vs))
            # Category / level info
            data = TRIADS.get(self.triad_type, {})
            self._lbl(row, f'  Lv{data.get("level","")}  [{data.get("category","")}]', PANEL
                      ).pack(side='left', padx=8)

        elif m == 'Modes':
            available = [k for k,v in MODES.items() if v['level'] <= lv]
            if self.mode_type not in available: self.mode_type = available[0]
            self._lbl(self._sub,'Mode:', PANEL).pack(side='left')
            cb = ttk.Combobox(self._sub, values=available, state='readonly', width=26)
            cb.set(self.mode_type); cb.pack(side='left', padx=(4,12))
            cb.bind('<<ComboboxSelected>>', lambda e,c=cb: self._on_mode_cb(c))
            data = MODES.get(self.mode_type, {})
            self._lbl(self._sub, f'Lv{data.get("level","")}', PANEL).pack(side='left')

        elif m == 'Progressions':
            self._build_prog_sub()

    def _on_triad_cb(self, cb):
        self.triad_type = cb.get(); self.triad_inv = 0; self._render()

    def _on_inv_cb(self, cb, voicings):
        self.triad_inv = cb.current(); self._render()

    def _on_mode_cb(self, cb):
        self.mode_type = cb.get(); self._render()

    def _build_prog_sub(self):
        lv = self.level
        r1 = tk.Frame(self._sub, bg=PANEL); r1.pack(fill='x', pady=(0,4))
        r2 = tk.Frame(self._sub, bg=PANEL); r2.pack(fill='x')

        # Sub-mode toggle
        for pm in ['Named','Random','Markov']:
            active = self.prog_submode == pm
            self._btn(r1, pm, lambda v=pm: self._set_prog_submode(v),
                      active=active).pack(side='left', padx=2)

        tk.Frame(r1, bg=PANEL, width=14).pack(side='left')

        if self.prog_submode == 'Named':
            avail = [p for p in NAMED_PROGRESSIONS if p['level'] <= lv]
            self._available_progs = avail
            idx = min(self.named_prog_idx, len(avail)-1)
            self.named_prog_idx = idx
            names = [f'{p["name"]}  [{p["genre"]}]' for p in avail]
            cb = ttk.Combobox(r1, values=names, state='readonly', width=42)
            cb.current(idx); cb.pack(side='left', padx=(4,8))
            cb.bind('<<ComboboxSelected>>', lambda e,c=cb: self._on_named_cb(c))
            self._btn(r2, '→  Next chord', self._next_chord, bg_override=GREEN
                      ).pack(side='left', padx=2)

        elif self.prog_submode == 'Random':
            self._available_progs = []
            self._btn(r1, '⟳  Generate', self._gen_random, bg_override=GREEN
                      ).pack(side='left', padx=4)
            self._btn(r2, '→  Next chord', self._next_chord, bg_override=GREEN
                      ).pack(side='left', padx=2)

        elif self.prog_submode == 'Markov':
            self._available_progs = []
            self._lbl(r1,'Genre:', PANEL).pack(side='left')
            for g in ['classical','pop','rock','blues','jazz','cinematic']:
                active = self.markov_genre.get() == g
                self._btn(r1, g.title(), lambda v=g: self._set_markov_genre(v),
                          active=active).pack(side='left', padx=2)
            tk.Frame(r1, bg=PANEL, width=10).pack(side='left')
            self._lbl(r1,'Tonality:', PANEL).pack(side='left')
            for t in ['major','minor']:
                active = self.markov_tonality.get() == t
                self._btn(r1, t.title(), lambda v=t: self._set_markov_tonality(v),
                          active=active).pack(side='left', padx=2)
            self._btn(r2, '⟳  Generate', self._gen_markov, bg_override=GREEN
                      ).pack(side='left', padx=2)
            self._btn(r2, '→  Next', self._next_chord, bg_override=BLUE
                      ).pack(side='left', padx=4)
            self._btn(r2, '◀  Prev', self._prev_chord).pack(side='left', padx=2)

    def _set_prog_submode(self, pm):
        self.prog_submode = pm; self.prog_chord = 0; self._render()

    def _on_named_cb(self, cb):
        self.named_prog_idx = cb.current(); self.prog_chord = 0; self._render()

    def _set_markov_genre(self, v):
        self.markov_genre.set(v); self._gen_markov()

    def _set_markov_tonality(self, v):
        self.markov_tonality.set(v); self._gen_markov()

    def _next_chord(self):
        total = self._prog_length()
        if total: self.prog_chord = (self.prog_chord+1) % total; self._render()

    def _prev_chord(self):
        total = self._prog_length()
        if total: self.prog_chord = (self.prog_chord-1) % total; self._render()

    def _prog_length(self):
        if self.prog_submode == 'Named':
            if not self._available_progs: return 0
            return len(self._available_progs[self.named_prog_idx]['chords'])
        elif self.prog_submode == 'Random':
            return len(self._rand_prog)
        elif self.prog_submode == 'Markov':
            return len(self._markov_prog)
        return 0

    def _gen_random(self):
        adv = self.adventure
        starts = [(0,'M'),(0,'m'),(9,'m'),(5,'M')]
        current = random.choice(starts); prog = [current]
        for _ in range(3):
            candidates = [(st,q) for st,q,ml in CHORD_GRAPH.get(current,[]) if ml <= adv]
            if not candidates: break
            current = random.choice(candidates); prog.append(current)
        self._rand_prog = prog; self.prog_chord = 0; self._render()

    def _gen_markov(self):
        diff = LEVEL_TO_MARKOV.get(self.adventure, 'intermediate')
        length = [4,4,4,6,8][self.adventure-1]
        self._markov_prog = generate_progression(
            length=length, genre=self.markov_genre.get(),
            tonality=self.markov_tonality.get(), difficulty=diff,
            tonic_semitone=self.root_note, cadence=True)
        self.prog_chord = 0; self._render()

    # ── Dot calculation ────────────────────────────────────────────────────────

    def _get_dots(self):
        tuning = TUNINGS[self.tuning_name.get()]
        root   = self.root_note
        reveal = self.reveal.get()
        mode   = self.mode
        dots   = []

        def note_at(s,f): return (tuning[s]+f)%12

        if mode == 'Notes':
            for s in range(6):
                for f in range(self._max_fret() + 1):
                    n = note_at(s,f)
                    dots.append((s,f,'root' if n==root else 'all', NOTES[n]))

        elif mode == 'Triads':
            # If chord is in CHORD_LIBRARY and a voicing is selected, use that
            voicings = get_all_voicings(self.triad_type) if self.triad_type in CHORD_LIBRARY else []
            if voicings:
                inv_idx = min(self.triad_inv, len(voicings)-1)
                ivs = voicings[inv_idx]['intervals']
                # dot_types: position 0=root, rest by interval size
                dt = TRIADS.get(self.triad_type, {}).get('dot_types', [])
            else:
                data = TRIADS.get(self.triad_type, {})
                ivs  = data.get('intervals', [0,4,7])
                dt   = data.get('dot_types', ['root','third','fifth'])

            # Normalise intervals to within one octave for matching
            ivs_mod = [iv%12 for iv in ivs]
            for s in range(6):
                for f in range(self._max_fret() + 1):
                    n  = note_at(s,f)
                    iv = (n-root)%12
                    if iv in ivs_mod:
                        idx = ivs_mod.index(iv)
                        t   = dt[idx] if idx < len(dt) else 'interval'
                        if reveal=='Root only' and t!='root': continue
                        if reveal=='Partial (root + 5th)' and t=='third': continue
                        dots.append((s,f,t,NOTES[n]))

        elif mode == 'Modes':
            ivs = MODES[self.mode_type]['intervals']
            for s in range(6):
                for f in range(self._max_fret() + 1):
                    n  = note_at(s,f); iv = (n-root)%12
                    if iv in ivs:
                        idx = ivs.index(iv)
                        t = 'root' if idx==0 else ('fifth' if iv==7 else 'interval')
                        if reveal=='Root only' and t!='root': continue
                        if reveal=='Partial (root + 5th)' and t=='interval': continue
                        dots.append((s,f,t,NOTES[n]))

        elif mode == 'Progressions':
            chord_root, ivs, dt = None, [0,4,7], ['root','third','fifth']
            pm = self.prog_submode

            if pm == 'Named' and self._available_progs:
                prog = self._available_progs[self.named_prog_idx]
                st, q = prog['chords'][self.prog_chord % len(prog['chords'])]
                chord_root = (root+st)%12
                ivs = QUALITY_INTERVALS.get(q,[0,4,7])
                dt  = QUALITY_DOT_TYPES.get(q,['root','third','fifth'])

            elif pm == 'Random' and self._rand_prog:
                st, q = self._rand_prog[self.prog_chord % len(self._rand_prog)]
                chord_root = (root+st)%12
                ivs = QUALITY_INTERVALS.get(q,[0,4,7])
                dt  = QUALITY_DOT_TYPES.get(q,['root','third','fifth'])

            elif pm == 'Markov' and self._markov_prog:
                p = self._markov_prog[self.prog_chord % len(self._markov_prog)]
                chord_root = p['root_semitone']
                from harmony_engine import QUALITY_INTERVALS as QI
                ivs = QI.get(p['quality'],[0,4,7])
                dt  = ['root','third','fifth']

            if chord_root is not None:
                for s in range(6):
                    for f in range(self._max_fret() + 1):
                        n  = note_at(s,f); iv = (n-chord_root)%12
                        if iv in ivs:
                            idx = ivs.index(iv)
                            t   = dt[idx] if idx<len(dt) else 'interval'
                            if reveal=='Root only' and t!='root': continue
                            if reveal=='Partial (root + 5th)' and t=='third': continue
                            dots.append((s,f,t,NOTES[n]))

        return dots

    # ── Fretboard ──────────────────────────────────────────────────────────────

    def _draw_fretboard(self, dots):
        c = self._canvas; c.delete('all')
        W = c.winfo_width() or 920
        FRETS = 24 if (self.mode == 'Practice' and self.prac_24frets.get()) else 12
        H=210; L=48; R=16; T=28; SG=28; FW=(W-L-R)/FRETS

        for f in range(FRETS+1):
            x = L+f*FW
            c.create_line(x,T-6,x,T+5*SG+6,
                          fill='#5a4a30' if f==0 else '#3d3020',
                          width=3 if f==0 else 1)
        marker_frets = [3,5,7,9,12,15,17,19,21,24] if FRETS == 24 else [3,5,7,9,12]
        for f in marker_frets:
            mx = L+(f-0.5)*FW
            if f in (12, 24):
                c.create_oval(mx-18,H-14,mx-10,H-6,fill='#3d3020',outline='')
                c.create_oval(mx+10,H-14,mx+18,H-6,fill='#3d3020',outline='')
            else:
                c.create_oval(mx-5,H-14,mx+5,H-6,fill='#3d3020',outline='')
        for f in range(1,FRETS+1):
            c.create_text(L+(f-0.5)*FW,H-2,text=str(f),fill='#4a4030',font=('Helvetica',9))

        labels = TUNING_LABELS[self.tuning_name.get()]
        for s in range(6):
            y = T+(5-s)*SG; thick = max(0.5,3.5-s*0.5)
            c.create_line(L-4,y,W-R,y,fill='#7a6a50',width=thick)
            c.create_text(L-8,y,text=labels[s],anchor='e',fill=MUTED,font=('Helvetica',10))
        c.create_rectangle(L-5,T-6,L-1,T+5*SG+6,fill='#c8b878',outline='')

        DC = {'root':(ACCENT,'#412402'),'third':(GREEN,'#04342C'),
              'fifth':(BLUE,'#042C53'),'interval':(PURPLE,'#26215C'),
              'target':('#e02020','#FFE0E0'),'all':(None,MUTED)}
        for (s,f,typ,label) in dots:
            x = L-20 if f==0 else L+(f-0.5)*FW; y = T+(5-s)*SG
            fc,tc = DC.get(typ,(None,MUTED))
            if typ=='all':
                c.create_oval(x-9,y-9,x+9,y+9,fill='#2a2010',outline='#3a3020',width=1)
                c.create_text(x,y,text=label,fill='#4a4535',font=('Helvetica',8))
            else:
                c.create_oval(x-13,y-13,x+13,y+13,fill=fc,outline='')
                c.create_text(x,y+1,text=label,fill=tc,font=('Helvetica',9,'bold'))

    # ── Legend ─────────────────────────────────────────────────────────────────

    def _rebuild_legend(self):
        for w in self._legend.winfo_children(): w.destroy()
        items = [('●',ACCENT,'Root')]
        if self.mode != 'Notes':
            items += [('●',GREEN,'3rd / scale tone'),('●',BLUE,'5th')]
        if self.mode in ('Modes','Triads'):
            items.append(('●',PURPLE,'Other interval'))
        for sym,col,lbl in items:
            f = tk.Frame(self._legend,bg=BG); f.pack(side='left',padx=8)
            tk.Label(f,text=sym,bg=BG,fg=col,font=('Helvetica',14)).pack(side='left')
            tk.Label(f,text=lbl,bg=BG,fg=MUTED,font=('Helvetica',9)).pack(side='left',padx=(2,0))

    # ── Chord chips (Markov only) ───────────────────────────────────────────────

    def _rebuild_chips(self):
        for w in self._chip_frame.winfo_children(): w.destroy()
        if self.mode!='Progressions' or self.prog_submode!='Markov' or not self._markov_prog:
            return
        hdr = tk.Frame(self._chip_frame, bg=PANEL2); hdr.pack(fill='x',pady=(0,6))
        tk.Label(hdr, text=f'{NOTES[self.root_note]} {self.markov_tonality.get().title()}  —  '
                          f'{self.markov_genre.get().title()}  [Adv{self.adventure}/Diff{self.difficulty}]',
                 bg=PANEL2, fg=TEXT, font=('Helvetica',11,'bold')).pack(side='left')
        chips = tk.Frame(self._chip_frame, bg=PANEL2); chips.pack(fill='x')
        fmap = {'T':'T','S':'S','D':'D','X':'X'}
        for i,p in enumerate(self._markov_prog):
            active = (i==self.prog_chord)
            chip = tk.Frame(chips, bg=ACCENT if active else BTN_BG, padx=8, pady=4)
            chip.pack(side='left', padx=3, pady=2)
            col = '#1a1a1a' if active else TEXT; sub = '#412402' if active else MUTED
            rn = NOTES[p['root_semitone']]
            tk.Label(chip, text=p['roman'], bg=chip['bg'], fg=col,
                     font=('Helvetica',11,'bold')).pack()
            tk.Label(chip, text=f"{rn} {p['quality']}", bg=chip['bg'], fg=sub,
                     font=('Helvetica',8)).pack()
            tk.Label(chip, text=p['function'], bg=chip['bg'], fg=sub,
                     font=('Helvetica',8)).pack()
            for w in [chip]+list(chip.winfo_children()):
                w.bind('<Button-1>', lambda e,v=i: self._jump_chord(v))

    def _jump_chord(self, i):
        self.prog_chord = i; self._render()

    # ── Info card ──────────────────────────────────────────────────────────────

    def _update_info(self):
        mode = self.mode; root = NOTES[self.root_note]

        if mode == 'Notes':
            self._info_title.config(text=f'All  {root}  notes on the neck')
            self._info_desc.config(text='Every amber dot is this note. Play each one ascending and descending, saying the name aloud.')
            self._info_hint.config(text='Tip: notice the octave shapes — same note, 12 frets higher, same dot pattern.')

        elif mode == 'Triads':
            t = self.triad_type; data = TRIADS.get(t,{})
            ivs = data.get('intervals',[])
            formula    = ' – '.join(DEG_NAMES.get(i%12,str(i)) for i in ivs)
            note_names = '  –  '.join(NOTES[(self.root_note+i)%12] for i in ivs)
            voicings = get_all_voicings(t) if t in CHORD_LIBRARY else []
            inv_info = ''
            if voicings:
                idx = min(self.triad_inv, len(voicings)-1)
                inv_info = f'  ·  Voicing: {voicings[idx]["label"]}'
                if voicings[idx]['dropped']:
                    from harmony_engine import _interval_names
                    inv_info += f'  (dropped: {", ".join(_interval_names(voicings[idx]["dropped"]))})'
            self._info_title.config(text=f'{root}  {t}')
            self._info_desc.config(text=f'{formula}     ({note_names}){inv_info}')
            self._info_hint.config(text=f'Level {data.get("level","")}  [{data.get("category","")}]  ·  Use "Root only" to quiz yourself.')

        elif mode == 'Modes':
            mt = self.mode_type; data = MODES.get(mt,{})
            ivs = data.get('intervals',[])
            formula = '  '.join(DEG_NAMES.get(i,str(i)) for i in ivs)
            self._info_title.config(text=f'{root}  {mt}')
            self._info_desc.config(text=f'{formula}\n{data.get("desc","")}')
            self._info_hint.config(text=f'Level {data.get("level","")}  ·  Learn one position, then connect across the neck.')

        elif mode == 'Progressions':
            pm = self.prog_submode
            if pm == 'Named':
                if not self._available_progs:
                    self._info_title.config(text='No progressions at this level'); return
                prog = self._available_progs[self.named_prog_idx]
                chords = prog['chords']; total = len(chords)
                st,q = chords[self.prog_chord % total]
                cr = NOTES[(self.root_note+st)%12]
                seq = '  →  '.join(f'{NOTES[(self.root_note+s)%12]}{QUALITY_LABEL[q2]}' for s,q2 in chords)
                self._info_title.config(text=f'{root} — {prog["name"]}  [{prog["genre"]}  Lv{prog["level"]}]')
                self._info_desc.config(text=f'{seq}\nNow: {cr}{QUALITY_LABEL[q]}  (chord {self.prog_chord%total+1}/{total})')
                self._info_hint.config(text='→ Next steps through. Change level to unlock more progressions.')

            elif pm == 'Random':
                prog = self._rand_prog; total = max(1,len(prog))
                st,q = prog[self.prog_chord%total]
                cr = NOTES[(self.root_note+st)%12]
                seq = '  →  '.join(f'{NOTES[(self.root_note+s)%12]}{QUALITY_LABEL[q2]}' for s,q2 in prog)
                self._info_title.config(text=f'{root} — Random  [Adv{self.adventure}/Diff{self.difficulty}]')
                self._info_desc.config(text=f'{seq}\nNow: {cr}{QUALITY_LABEL[q]}  (chord {self.prog_chord%total+1}/{total})')
                self._info_hint.config(text='⟳ Generate for a new random progression.')

            elif pm == 'Markov':
                if not self._markov_prog:
                    self._info_title.config(text='Hit  ⟳ Generate  to create a Markov progression')
                    self._info_desc.config(text='Genre-aware weighted Markov chain — built from Temperley classical corpus + Hooktheory 40k-song database.')
                    self._info_hint.config(text='Select genre and tonality, then generate.')
                    return
                p = self._markov_prog[self.prog_chord%len(self._markov_prog)]
                rn = NOTES[p['root_semitone']]; total = len(self._markov_prog)
                romans = '  →  '.join(x['roman'] for x in self._markov_prog)
                fmap = {'T':'Tonic','S':'Subdominant','D':'Dominant','X':'Chromatic/borrowed'}
                self._info_title.config(text=f'Chord {self.prog_chord%total+1}/{total}:  {rn} {p["quality"]}  ({p["roman"]})  —  {fmap.get(p["function"],"")}')
                self._info_desc.config(text=f'{p["description"]}\n\nProgression:  {romans}')
                self._info_hint.config(text='Click chips to jump. →/◀ to step. Functional labels: T=tonic S=subdominant D=dominant X=chromatic.')

    # ── Master render ──────────────────────────────────────────────────────────

    def _render(self, *_):
        self._rebuild_sub()
        self._rebuild_legend()
        self._rebuild_chips()
        self._draw_fretboard(self._get_dots())
        self._update_info()


    # ── Page switching ─────────────────────────────────────────────────────────

    def _show_library_page(self):
        """Show the normal library UI (sub, canvas, legend, info, chips)."""
        self._practice_page.pack_forget()
        self._sub.pack(fill='x')
        self._fb_outer.pack(fill='x', padx=16, pady=(10,0))
        self._legend.pack(fill='x')
        self._info_card.pack(fill='x', padx=16, pady=(8,4))
        self._chip_frame.pack(fill='x', padx=16, pady=(4,12))

    def _show_practice_page(self):
        """Hide library UI and show practice page."""
        self._sub.pack_forget()
        self._fb_outer.pack_forget()
        self._legend.pack_forget()
        self._info_card.pack_forget()
        self._chip_frame.pack_forget()
        self._practice_page.pack(fill='both', expand=True, padx=16, pady=8)
        self._prac_rebuild_settings()

    # ── Practice page construction ─────────────────────────────────────────────

    def _build_practice_page(self):
        """Called once from _build_ui. Builds the practice page frame."""
        self._practice_page = tk.Frame(self, bg=BG)
        # (not packed until Practice tab is selected)

        # ── Settings panel ─────────────────────────────────────────────────
        self._prac_settings = tk.Frame(self._practice_page, bg=PANEL, padx=16, pady=10)
        self._prac_settings.pack(fill='x', pady=(0,8))

        # ── Target display ─────────────────────────────────────────────────
        tgt = tk.Frame(self._practice_page, bg=PANEL2, padx=16, pady=14)
        tgt.pack(fill='x', pady=(0,6))

        # Big target name
        self._prac_target_lbl = tk.Label(tgt, text='— press Start —', bg=PANEL2,
                                          fg=ACCENT, font=('Helvetica',28,'bold'))
        self._prac_target_lbl.pack()

        # Subtitle (interval formula / notes)
        self._prac_sub_lbl = tk.Label(tgt, text='', bg=PANEL2, fg=MUTED,
                                       font=('Helvetica',12))
        self._prac_sub_lbl.pack()

        # Score row
        score_row = tk.Frame(tgt, bg=PANEL2); score_row.pack(fill='x', pady=(10,0))
        self._prac_score_lbl = tk.Label(score_row, text='', bg=PANEL2, fg=TEXT,
                                         font=('Helvetica',11))
        self._prac_score_lbl.pack(side='left')
        self._prac_streak_lbl = tk.Label(score_row, text='', bg=PANEL2, fg=ACCENT,
                                          font=('Helvetica',11,'bold'))
        self._prac_streak_lbl.pack(side='right')

        # ── Fretboard (reuse canvas but embed a copy in practice page) ────
        prac_fb = tk.Frame(self._practice_page, bg=PANEL2, padx=12, pady=10)
        prac_fb.pack(fill='x', pady=(0,6))
        self._prac_canvas = tk.Canvas(prac_fb, bg='#1e1510', height=210,
                                       highlightthickness=0)
        self._prac_canvas.pack(fill='x')
        self._prac_canvas.bind('<Configure>', lambda e: self._prac_draw())

        # ── History strip ──────────────────────────────────────────────────
        self._prac_history_frame = tk.Frame(self._practice_page, bg=BG, padx=16, pady=4)
        self._prac_history_frame.pack(fill='x', pady=(0,6))

        # ── Control buttons ────────────────────────────────────────────────
        btn_row = tk.Frame(self._practice_page, bg=BG, padx=16, pady=6)
        btn_row.pack(fill='x')
        self._prac_start_btn = tk.Button(btn_row, text='▶  Start',
                                          bg=GREEN, fg='#04342C', relief='flat',
                                          padx=18, pady=7,
                                          font=('Helvetica',12,'bold'), cursor='hand2',
                                          command=self._prac_toggle)
        self._prac_start_btn.pack(side='left', padx=(0,8))

        tk.Button(btn_row, text='✓  Got it', bg='#2a5c3a', fg='#90EE90',
                  relief='flat', padx=14, pady=7,
                  font=('Helvetica',11), cursor='hand2',
                  command=lambda: self._prac_mark(True)).pack(side='left', padx=4)

        tk.Button(btn_row, text='✗  Missed', bg='#5c2a2a', fg='#FF9999',
                  relief='flat', padx=14, pady=7,
                  font=('Helvetica',11), cursor='hand2',
                  command=lambda: self._prac_mark(False)).pack(side='left', padx=4)

        tk.Button(btn_row, text='↩  Reset score', bg=BTN_BG, fg=MUTED,
                  relief='flat', padx=12, pady=7,
                  font=('Helvetica',10), cursor='hand2',
                  command=self._prac_reset_score).pack(side='right')

    def _prac_rebuild_settings(self):
        for w in self._prac_settings.winfo_children(): w.destroy()
        s = self._prac_settings

        r1 = tk.Frame(s, bg=PANEL); r1.pack(fill='x', pady=(0,6))
        r2 = tk.Frame(s, bg=PANEL); r2.pack(fill='x')
        # Adventure (green) = which musical items unlock; Difficulty (orange) = fretboard scope & inversions

        # Drill type
        tk.Label(r1, text='Drill:', bg=PANEL, fg=MUTED,
                 font=('Helvetica',10)).pack(side='left')
        for d in ['Notes','Triads','Modes','Progressions']:
            active = self.prac_drill.get() == d
            tk.Button(r1, text=d,
                      bg=ACCENT if active else BTN_BG,
                      fg='#1a1a1a' if active else TEXT,
                      relief='flat', padx=10, pady=4,
                      font=('Helvetica',10), cursor='hand2',
                      command=lambda v=d: self._prac_set_drill(v)
                      ).pack(side='left', padx=2)

        tk.Frame(r1, bg=PANEL, width=16).pack(side='left')

        # Sequence mode
        tk.Label(r1, text='Sequence:', bg=PANEL, fg=MUTED,
                 font=('Helvetica',10)).pack(side='left')
        seq_info = {'Loop':'cycles fixed set','Random':'random each time',
                    'Infinite':'Markov — never repeats'}
        for seq in ['Loop','Random','Infinite']:
            active = self.prac_sequence.get() == seq
            tk.Button(r1, text=seq,
                      bg=ACCENT if active else BTN_BG,
                      fg='#1a1a1a' if active else TEXT,
                      relief='flat', padx=10, pady=4,
                      font=('Helvetica',10), cursor='hand2',
                      command=lambda v=seq: self._prac_set_sequence(v)
                      ).pack(side='left', padx=2)

        tk.Frame(r1, bg=PANEL, width=16).pack(side='left')

        # Root mode
        tk.Label(r1, text='Key:', bg=PANEL, fg=MUTED,
                 font=('Helvetica',10)).pack(side='left')
        for rm in ['Fixed','Random']:
            active = self.prac_root_mode.get() == rm
            tk.Button(r1, text=rm,
                      bg=ACCENT if active else BTN_BG,
                      fg='#1a1a1a' if active else TEXT,
                      relief='flat', padx=10, pady=4,
                      font=('Helvetica',10), cursor='hand2',
                      command=lambda v=rm: self._prac_set_root_mode(v)
                      ).pack(side='left', padx=2)

        # BPM spinner
        tk.Label(r2, text='BPM:', bg=PANEL, fg=MUTED,
                 font=('Helvetica',10)).pack(side='left')
        bpm_spin = tk.Spinbox(r2, from_=30, to=300, increment=1,
                              textvariable=self.prac_bpm, width=5,
                              font=('Helvetica',10),
                              bg=BTN_BG, fg=TEXT, buttonbackground=BTN_BG,
                              insertbackground=TEXT, relief='flat',
                              command=self._prac_tempo_changed)
        bpm_spin.pack(side='left', padx=(4,14))

        # Beats slider — range depends on drill (1-30 for Modes, 1-16 otherwise)
        max_beats = 30 if self.prac_drill.get() == 'Modes' else 16
        tk.Label(r2, text='Beats per target:', bg=PANEL, fg=MUTED,
                 font=('Helvetica',10)).pack(side='left')
        beats_lbl = tk.Label(r2, text=f'{self.prac_beats.get()}', bg=PANEL, fg=TEXT,
                              font=('Helvetica',10,'bold'), width=3)
        beats_lbl.pack(side='left', padx=(4,0))
        def on_beats(val, lbl=beats_lbl):
            lbl.config(text=f'{int(float(val))}')
            self._prac_tempo_changed()
        sl = ttk.Scale(r2, from_=1, to=max_beats, orient='horizontal', length=180,
                       variable=self.prac_beats, command=on_beats)
        sl.pack(side='left', padx=(4,16))

        # Use 24 frets checkbox
        tk.Checkbutton(r2, text='Use 24 frets', variable=self.prac_24frets,
                       bg=PANEL, fg=TEXT, selectcolor=BTN_BG,
                       activebackground=PANEL, activeforeground=TEXT,
                       font=('Helvetica',10), cursor='hand2',
                       command=self._prac_draw
                       ).pack(side='left', padx=(0,14))

        # Reveal (reuse global)
        tk.Label(r2, text='Show:', bg=PANEL, fg=MUTED,
                 font=('Helvetica',10)).pack(side='left')
        ttk.Combobox(r2, textvariable=self.reveal,
                     values=['Full shape','Root only','Partial (root + 5th)'],
                     state='readonly', width=20).pack(side='left', padx=(4,20))

        # Adventure (musical scope) and Difficulty (fretboard scope)
        tk.Label(r2, text='Adventure:', bg=PANEL, fg=MUTED,
                 font=('Helvetica',10)).pack(side='left')
        af = tk.Frame(r2, bg=PANEL); af.pack(side='left', padx=(4,12))
        for lv in range(1,6):
            active = self.adventure == lv
            tk.Button(af, text=str(lv), width=2,
                      bg='#4db896' if active else BTN_BG,
                      fg='#04342C' if active else TEXT,
                      relief='flat', pady=3,
                      font=('Helvetica',10,'bold' if active else 'normal'),
                      cursor='hand2',
                      command=lambda v=lv: self._prac_set_adventure(v)
                      ).pack(side='left', padx=1)

        tk.Label(r2, text='Difficulty:', bg=PANEL, fg=MUTED,
                 font=('Helvetica',10)).pack(side='left')
        df = tk.Frame(r2, bg=PANEL); df.pack(side='left', padx=(4,0))
        for lv in range(1,6):
            active = self.difficulty == lv
            tk.Button(df, text=str(lv), width=2,
                      bg='#e08838' if active else BTN_BG,
                      fg='#412402' if active else TEXT,
                      relief='flat', pady=3,
                      font=('Helvetica',10,'bold' if active else 'normal'),
                      cursor='hand2',
                      command=lambda v=lv: self._prac_set_difficulty(v)
                      ).pack(side='left', padx=1)

        # Row 3: Strings + inversion root checkbox
        r3 = tk.Frame(s, bg=PANEL); r3.pack(fill='x', pady=(6,0))

        tk.Label(r3, text='Root on strings:', bg=PANEL, fg=MUTED,
                 font=('Helvetica',10)).pack(side='left')
        str_labels = TUNING_LABELS[self.tuning_name.get()]
        for i, (sv, lbl) in enumerate(zip(self._string_vars, str_labels)):
            tk.Checkbutton(r3, text=lbl, variable=sv,
                           bg=PANEL, fg=TEXT, selectcolor=BTN_BG,
                           activebackground=PANEL, activeforeground=TEXT,
                           font=('Helvetica',10), cursor='hand2',
                           command=self._prac_draw
                           ).pack(side='left', padx=2)

        tk.Frame(r3, bg=PANEL, width=24).pack(side='left')

        tk.Checkbutton(r3, text='Inversion root (bass note = root colour)',
                       variable=self.prac_inv_root,
                       bg=PANEL, fg=TEXT, selectcolor=BTN_BG,
                       activebackground=PANEL, activeforeground=TEXT,
                       font=('Helvetica',10), cursor='hand2',
                       command=self._prac_draw
                       ).pack(side='left', padx=2)

        # ── Row 4: progression picker (Loop mode) and triad/mode override ────
        seq   = self.prac_sequence.get()
        drill = self.prac_drill.get()

        if seq == 'Loop':
            r4 = tk.Frame(s, bg=PANEL); r4.pack(fill='x', pady=(6,0))

            # Generate-progression checkbox
            tk.Checkbutton(r4, text='Generate progression',
                           variable=self.prac_loop_generate,
                           bg=PANEL, fg=TEXT, selectcolor=BTN_BG,
                           activebackground=PANEL, activeforeground=TEXT,
                           font=('Helvetica',10,'bold'), cursor='hand2',
                           command=self._prac_loop_gen_toggled
                           ).pack(side='left', padx=(0,12))

            # Re-roll triads each cycle? (only relevant for Triads drill)
            if self.prac_drill.get() == 'Triads':
                tk.Checkbutton(r4, text='Change triads each loop',
                               variable=self.prac_loop_change_triads,
                               bg=PANEL, fg=TEXT, selectcolor=BTN_BG,
                               activebackground=PANEL, activeforeground=TEXT,
                               font=('Helvetica',10), cursor='hand2',
                               command=self._prac_change_triads_toggled
                               ).pack(side='left', padx=(0,12))

            if not self.prac_loop_generate.get():
                # Show the named-progression dropdown
                tk.Label(r4, text='Loop progression:', bg=PANEL, fg=MUTED,
                         font=('Helvetica',10)).pack(side='left')
                avail_progs = [p for p in NAMED_PROGRESSIONS if p['level'] <= self.adventure]
                idx = min(self.prac_loop_prog_idx.get(), len(avail_progs)-1)
                self.prac_loop_prog_idx.set(idx)
                names = [f'{p["name"]}  [{p["genre"]}]' for p in avail_progs]
                cb = ttk.Combobox(r4, values=names, state='readonly', width=40)
                if names: cb.current(idx)
                cb.pack(side='left', padx=(4,8))
                cb.bind('<<ComboboxSelected>>', lambda e,c=cb: self._prac_set_loop_prog(c.current()))
            else:
                # Show genre tickboxes and length spinner
                r4b = tk.Frame(s, bg=PANEL); r4b.pack(fill='x', pady=(4,0))
                tk.Label(r4b, text='Draw from genres:', bg=PANEL, fg=MUTED,
                         font=('Helvetica',10)).pack(side='left')
                for g, var in self.prac_loop_genres.items():
                    tk.Checkbutton(r4b, text=g.title(), variable=var,
                                   bg=PANEL, fg=TEXT, selectcolor=BTN_BG,
                                   activebackground=PANEL, activeforeground=TEXT,
                                   font=('Helvetica',10), cursor='hand2',
                                   command=self._prac_loop_regenerate
                                   ).pack(side='left', padx=4)
                tk.Frame(r4b, bg=PANEL, width=16).pack(side='left')
                tk.Label(r4b, text='Length:', bg=PANEL, fg=MUTED,
                         font=('Helvetica',10)).pack(side='left')
                tk.Spinbox(r4b, from_=2, to=32, increment=1,
                           textvariable=self.prac_loop_length, width=4,
                           font=('Helvetica',10),
                           bg=BTN_BG, fg=TEXT, buttonbackground=BTN_BG,
                           insertbackground=TEXT, relief='flat',
                           command=self._prac_loop_regenerate
                           ).pack(side='left', padx=(4,8))
                tk.Button(r4b, text='⟳ Regenerate',
                          bg=GREEN, fg='#04342C', relief='flat',
                          padx=12, pady=4, font=('Helvetica',10,'bold'),
                          cursor='hand2', command=self._prac_loop_regenerate
                          ).pack(side='left', padx=4)
                if self._generated_loop_prog:
                    preview = ' → '.join(p['roman'] for p in self._generated_loop_prog)
                    tk.Label(r4b, text=f'  Current: {preview}', bg=PANEL, fg=MUTED,
                             font=('Helvetica',9,'italic'),
                             wraplength=600, justify='left'
                             ).pack(side='left', padx=(8,0))

        # Triad type override (when drilling Triads with a progression-driven sequence)
        if drill == 'Triads' and seq in ('Loop','Infinite'):
            r5 = tk.Frame(s, bg=PANEL); r5.pack(fill='x', pady=(6,0))
            tk.Label(r5, text='Triad type:', bg=PANEL, fg=MUTED,
                     font=('Helvetica',10)).pack(side='left')
            triad_opts = ['Follow progression'] + [k for k,v in TRIADS.items() if v['level'] <= self.adventure]
            if self.prac_triad_override.get() not in triad_opts:
                self.prac_triad_override.set('Follow progression')
            cb2 = ttk.Combobox(r5, values=triad_opts, state='readonly', width=24)
            cb2.set(self.prac_triad_override.get())
            cb2.pack(side='left', padx=(4,8))
            cb2.bind('<<ComboboxSelected>>', lambda e,c=cb2: self._prac_set_triad_override(c.get()))

        # Mode override (when drilling Modes with progression sequence)
        if drill == 'Modes' and seq in ('Loop','Infinite'):
            r5 = tk.Frame(s, bg=PANEL); r5.pack(fill='x', pady=(6,0))
            tk.Label(r5, text='Mode/scale:', bg=PANEL, fg=MUTED,
                     font=('Helvetica',10)).pack(side='left')
            mode_opts = ['Follow progression (Major/Minor)'] + [k for k,v in MODES.items() if v['level'] <= self.adventure]
            if self.prac_mode_override.get() not in mode_opts:
                self.prac_mode_override.set('Follow progression (Major/Minor)')
            cb3 = ttk.Combobox(r5, values=mode_opts, state='readonly', width=30)
            cb3.set(self.prac_mode_override.get())
            cb3.pack(side='left', padx=(4,8))
            cb3.bind('<<ComboboxSelected>>', lambda e,c=cb3: self._prac_set_mode_override(c.get()))

    # ── Practice settings setters ──────────────────────────────────────────────

    def _modes_position_dots(self, intervals, root, ticked):
        """
        Build scale dots with graduated position scope:
          D1: full primary 4-fret position
          D2: primary + ~30% of notes borrowed from ONE adjacent position
          D3: primary + full adjacent position
          D4: primary + full positions on BOTH sides (2 adjacent)
          D5: primary + full positions on both sides + extra ~50% bleed beyond
        Position size = 4 frets (one hand span).
        The 'target' note (self._modes_target_note) gets red colour.
        """
        max_fret = self._max_fret()
        lv       = self.difficulty
        tuning   = TUNINGS[self.tuning_name.get()]

        # ── 1. Find the primary anchor fret (lowest root on lowest ticked string) ──
        anchor_max = self._max_anchor_fret()
        anchor_fret = None
        for s in ticked:
            for f in range(min(max_fret, anchor_max) + 1):
                if (tuning[s] + f) % 12 == root % 12:
                    anchor_fret = f
                    break
            if anchor_fret is not None:
                break

        if anchor_fret is None:
            anchor_fret = 0  # fallback

        # ── 2. Build primary and adjacent 4-fret position windows ──
        POS_SIZE = 4
        primary_start = max(0, anchor_fret - 1)
        primary_end   = min(max_fret, primary_start + POS_SIZE)

        lower_start = max(0, primary_start - POS_SIZE)
        lower_end   = max(0, primary_start - 1)
        if lower_end < lower_start:
            lower_start = lower_end  # no room for lower position

        upper_start = min(max_fret, primary_end + 1)
        upper_end   = min(max_fret, primary_end + POS_SIZE)
        if upper_end < upper_start:
            upper_start = upper_end

        # ── 3. Decide which windows are included and what fraction of borrowed notes ──
        # primary always 100%. lower/upper get fractions depending on lv.
        # We'll prefer borrowing from the UPPER (higher frets) first, then both.
        if lv == 1:
            windows = [(primary_start, primary_end, 1.0)]
        elif lv == 2:
            windows = [(primary_start, primary_end, 1.0),
                       (upper_start, upper_end, 0.35)]   # borrow ~35% from upper
        elif lv == 3:
            windows = [(primary_start, primary_end, 1.0),
                       (upper_start, upper_end, 1.0)]    # full adjacent
        elif lv == 4:
            windows = [(primary_start, primary_end, 1.0),
                       (lower_start, lower_end, 1.0),
                       (upper_start, upper_end, 1.0)]
        else:  # lv == 5
            windows = [(primary_start, primary_end, 1.0),
                       (lower_start, lower_end, 1.0),
                       (upper_start, upper_end, 1.0),
                       # extra bleed beyond the two adjacent, ~50%
                       (max(0, lower_start - POS_SIZE),
                        max(0, lower_start - 1), 0.5),
                       (min(max_fret, upper_end + 1),
                        min(max_fret, upper_end + POS_SIZE), 0.5)]

        # ── 4. Collect candidate notes per window, then apply fraction sampling ──
        dots = []
        seen = set()
        for (start, end, frac) in windows:
            if start > end:
                continue
            candidates = []
            for s in range(6):
                for f in range(start, end + 1):
                    n = (tuning[s] + f) % 12
                    iv = (n - root) % 12
                    if iv in intervals and (s, f) not in seen:
                        candidates.append((s, f, n, iv))
            # Sample by fraction
            if frac < 1.0:
                k = max(1, int(round(len(candidates) * frac)))
                # Deterministic seed per target so the borrowed pattern is stable
                # while the target is up (won't reshuffle on every redraw)
                seed_state = (anchor_fret, start, end, tuple(intervals), root)
                rng = random.Random(hash(seed_state))
                candidates = rng.sample(candidates, min(k, len(candidates)))
            for (s, f, n, iv) in candidates:
                if (s, f) in seen:
                    continue
                seen.add((s, f))
                role = 'root' if iv == 0 else ('fifth' if iv == 7 else 'interval')
                if self._modes_target_note is not None and n == self._modes_target_note:
                    role = 'target'
                dots.append((s, f, role, NOTES[n]))

        return dots

    def _max_fret(self):
        """Highest fret index drawn on the canvas.
        Practice mode visual is ALWAYS 24 frets.
        Library mode stays at 12 frets."""
        if self.mode == 'Practice':
            return 24
        return 12

    def _max_anchor_fret(self):
        """Highest fret that root anchors are allowed to sit on.
        Determined by the 'Use 24 frets' checkbox."""
        if self.mode == 'Practice' and self.prac_24frets.get():
            return 24
        return 12

    def _prac_tempo_changed(self):
        """Called when BPM or beats slider changes. Reschedule timer if running."""
        if self.prac_running and self.prac_timer_id:
            self.after_cancel(self.prac_timer_id)
            ms = self._prac_target_ms()
            self.prac_timer_id = self.after(ms, self._prac_auto_advance)

    def _prac_target_ms(self):
        """Compute milliseconds-per-target from BPM + beats."""
        try:
            bpm = max(30, int(self.prac_bpm.get()))
            beats = max(1, int(self.prac_beats.get()))
        except (tk.TclError, ValueError):
            bpm, beats = 80, 4
        # ms = beats * (60000 / bpm)
        return int(beats * 60000 / bpm)

    def _prac_set_drill(self, v):
        self.prac_drill.set(v)
        self._loop_chord_idx = 0
        self._inf_prog_cache = []; self._inf_prog_idx = 0
        self._clear_triad_cache()
        self._prac_rebuild_settings()
        if self.prac_running: self._prac_advance()

    def _prac_set_sequence(self, v):
        self.prac_sequence.set(v)
        self._inf_prog_cache = []; self._inf_prog_idx = 0
        self._loop_chord_idx = 0
        self._clear_triad_cache()
        self._prac_rebuild_settings()

    def _prac_set_root_mode(self, v):
        self.prac_root_mode.set(v)
        self._prac_rebuild_settings()

    def _prac_set_adventure(self, v):
        self.adventure = v
        self._loop_chord_idx = 0
        self._inf_prog_cache = []; self._inf_prog_idx = 0
        self._clear_triad_cache()
        self._prac_rebuild_settings()
        if self.prac_running: self._prac_advance()

    def _prac_set_difficulty(self, v):
        self.difficulty = v
        self._prac_rebuild_settings()
        if self.prac_running: self._prac_advance()

    def _prac_change_triads_toggled(self):
        """Called when 'Change triads each loop' is toggled — clear cache so
        next chord re-picks shapes."""
        self._loop_triad_shapes = {}
        if self.prac_running: self._prac_advance()

    def _clear_triad_cache(self):
        """Invalidate the locked triad shapes for the loop."""
        self._loop_triad_shapes = {}

    def _prac_loop_gen_toggled(self):
        """Called when the 'Generate progression' checkbox is toggled."""
        self._generated_loop_prog = []
        self._loop_chord_idx = 0
        if self.prac_loop_generate.get():
            self._prac_loop_regenerate()
        else:
            self._prac_rebuild_settings()
            if self.prac_running: self._prac_advance()

    def _prac_loop_regenerate(self):
        """Generate a new Markov-based loop progression from selected genres."""
        try:
            length = max(2, min(32, int(self.prac_loop_length.get())))
        except (tk.TclError, ValueError):
            length = 4
        selected = [g for g,v in self.prac_loop_genres.items() if v.get()]
        if not selected:
            selected = ['pop']

        # Generate one progression per selected genre using the Adv-boosted Markov,
        # then concatenate / interleave. Simplest: pick one genre uniformly and
        # generate the whole progression from it. For multi-genre blends, we
        # alternate per chord-step by picking a genre per transition.
        # We'll use the alternating approach if multiple genres selected.
        if len(selected) == 1:
            genre = selected[0]
            self._generated_loop_prog = self._generate_with_adv_boost(
                length, genre, self.markov_tonality.get(),
                self.root_note, cadence=False)
        else:
            # Build a mixed progression by sampling transitions from multiple genres.
            # Cleaner approach: pre-generate from each genre and round-robin pick.
            pools = []
            for g in selected:
                pool = self._generate_with_adv_boost(
                    length, g, self.markov_tonality.get(),
                    self.root_note, cadence=False)
                pools.append(pool)
            # Take chord-by-chord from rotating pool sources
            blended = []
            for i in range(length):
                pool_idx = i % len(pools)
                if i < len(pools[pool_idx]):
                    blended.append(pools[pool_idx][i])
            self._generated_loop_prog = blended

        self._loop_chord_idx = 0
        self._clear_triad_cache()
        self._prac_rebuild_settings()
        if self.prac_running: self._prac_advance()

    def _prac_set_loop_prog(self, idx):
        self.prac_loop_prog_idx.set(idx)
        self._loop_chord_idx = 0
        self._clear_triad_cache()
        self._prac_rebuild_settings()
        if self.prac_running: self._prac_advance()

    def _prac_set_triad_override(self, v):
        self.prac_triad_override.set(v)
        self._clear_triad_cache()
        if self.prac_running: self._prac_advance()

    def _prac_set_mode_override(self, v):
        self.prac_mode_override.set(v)
        if self.prac_running: self._prac_advance()

    # ── Practice pool builders ─────────────────────────────────────────────────

    def _prac_pool(self):
        """Return list of target dicts for current drill + adventure level."""
        lv   = self.adventure
        drill = self.prac_drill.get()
        pool  = []

        if drill == 'Notes':
            for n in NOTES:
                pool.append({'name': n, 'subtitle': 'Find all occurrences on the neck',
                             'root': NOTES.index(n), 'intervals': None, 'dot_types': None})

        elif drill == 'Triads':
            for name, data in TRIADS.items():
                if data['level'] <= adv:
                    bass_off, ivs, dt, inv_label = self._pick_inversion(data['intervals'], data['dot_types'])
                    pool.append({'name': name, 'root': None,
                                 'bass_off': bass_off,
                                 'intervals': ivs,
                                 'dot_types': dt,
                                 'subtitle': f'{data.get("desc","")}  ·  {inv_label}',
                                 'inv_label': inv_label})

        elif drill == 'Modes':
            for name, data in MODES.items():
                if data['level'] <= adv:
                    ivs = data['intervals']
                    formula = '  '.join(DEG_NAMES.get(i,str(i)) for i in ivs)
                    pool.append({'name': name, 'root': None,
                                 'intervals': ivs, 'dot_types': None,
                                 'subtitle': formula})

        elif drill == 'Progressions':
            avail = [p for p in NAMED_PROGRESSIONS if p['level'] <= lv]
            for prog in avail:
                pool.append({'name': prog['name'], 'root': None,
                             'intervals': None, 'dot_types': None,
                             'prog': prog,
                             'subtitle': f'{prog["genre"]}  Lv{prog["level"]}'})
        return pool

    def _prac_pick_root(self, target):
        """Return semitone root (bass anchor) for this target."""
        if self.prac_drill.get() == 'Notes':
            return target['root']
        if target.get('root') is not None:
            # Target already specifies the bass (e.g. from progression-driven mode)
            return target['root']
        # For static pool targets: pick chord root then add bass offset
        if self.prac_root_mode.get() == 'Fixed':
            chord_root = self.root_note
        else:
            chord_root = random.randint(0, 11)
        return (chord_root + target.get('bass_off', 0)) % 12

    # ── Sequence generators ────────────────────────────────────────────────────

    def _pick_inversion(self, intervals, dot_types):
        """
        If inversion mode is on, randomly choose between root pos / 1st / 2nd / 3rd inv.
        Returns (bass_offset_from_chord_root, new_intervals, new_dot_types, label).

          bass_offset = semitones from the chord root up to the new bass note.
                        For root pos this is 0. For 1st inv of major it's 4 (3rd).
                        For 2nd inv of major it's 7 (5th).
          new_intervals = intervals measured FROM THE BASS NOTE, in ascending order.
          new_dot_types = dot type for each position in the inversion:
                          position 0 (the bass) is always 'root' colour (the anchor).
                          The original chord-root note (if it appears higher up) is
                          coloured 'interval' so it visually differs from the bass.
                          The 3rd and 5th retain their colours.
        """
        if not self.prac_inv_root.get():
            return 0, intervals, dot_types, 'Root position'

        inversions = get_inversions(intervals)
        if not inversions or len(inversions) <= 1:
            return 0, intervals, dot_types, 'Root position'

        # Difficulty gates which inversions are allowed:
        #   D1 → root pos only (inversion checkbox effectively off)
        #   D2 → up to 1st inversion
        #   D3 → up to 1st inversion
        #   D4 → up to 2nd inversion
        #   D5 → all inversions including 3rd (for 7th chords)
        max_inv = {1: 0, 2: 1, 3: 1, 4: 2, 5: len(inversions) - 1}.get(self.difficulty, 0)
        max_inv = min(max_inv, len(inversions) - 1)
        if max_inv == 0:
            return 0, intervals, dot_types, 'Root position'
        inv_idx = random.randrange(max_inv + 1)
        inv_name, inv_ivs = inversions[inv_idx]

        # Offset from chord root up to the new bass note = the interval at
        # position `inv_idx` in the ORIGINAL interval list (mod 12).
        bass_offset = intervals[inv_idx] % 12

        # Build dot_types for the rotated voicing.
        # We rotate the original dot_types by inv_idx so each position carries
        # its original role (root/third/fifth). Then we override:
        #   - position 0 of the new voicing always = 'root' (the bass anchor)
        #   - any position whose ORIGINAL role was 'root' (the chord root)
        #     becomes 'interval' to visually distinguish from the bass.
        if dot_types and len(dot_types) >= len(intervals):
            rotated = dot_types[inv_idx:] + dot_types[:inv_idx]
        else:
            rotated = ['root','third','fifth','interval','interval'][:len(inv_ivs)]
        new_dt = []
        for i, role in enumerate(rotated):
            if i == 0:
                new_dt.append('root')        # bass anchor = amber
            elif role == 'root':
                new_dt.append('interval')    # original chord root → purple (not amber)
            else:
                new_dt.append(role)          # third/fifth keep their colours

        return bass_offset, inv_ivs, new_dt, inv_name

    # ── Triad shape selection by Adventure level ─────────────────────────────
    # Compatible "flavoured" shapes for each progression chord quality.
    # As Adventure rises, more shapes from CHORD_LIBRARY become available.
    # Each shape must still produce a 3-note voicing (we always slice to 3 notes
    # in the builder).
    _TRIAD_FAMILY = {
        # major-flavoured  (root + M3 implied or root + dominant feel)
        'major': {
            1: ['Major'],
            2: ['Major', 'Power'],
            3: ['Major', 'Power', 'Sus2', 'Sus4', 'Shell Maj7', 'Shell Maj6'],
            4: ['Major', 'Power', 'Sus2', 'Sus4', 'Shell Maj7', 'Shell Maj6',
                'Shell Dom7', 'Major b5', 'Power + Maj7', 'Power + 6', 'Quartal'],
            5: ['Major', 'Power', 'Sus2', 'Sus4', 'Shell Maj7', 'Shell Maj6',
                'Shell Dom7', 'Major b5', 'Power + Maj7', 'Power + 6',
                'Power + b6', 'Quartal', 'Tritone Shell', 'Whole Tone Tri',
                'Aug Quartal', 'Augmented', 'Phrygian'],
        },
        # minor-flavoured
        'minor': {
            1: ['Minor'],
            2: ['Minor', 'Power'],
            3: ['Minor', 'Power', 'Sus2', 'Sus4', 'Shell Min7', 'Shell Min6'],
            4: ['Minor', 'Power', 'Sus2', 'Sus4', 'Shell Min7', 'Shell Min6',
                'Minor #5', 'Shell MinMaj7', 'Power + b7', 'Power + b6', 'Quartal'],
            5: ['Minor', 'Power', 'Sus2', 'Sus4', 'Shell Min7', 'Shell Min6',
                'Minor #5', 'Shell MinMaj7', 'Power + b7', 'Power + b6',
                'Quartal', 'Phrygian', 'Phrygian Tri', 'Minor Cluster',
                'Diminished', 'Aug Sus4'],
        },
        # dominant 7 chords
        'dom7': {
            1: ['Major'],
            2: ['Shell Dom7', 'Major'],
            3: ['Shell Dom7', 'Major', 'Power + b7', 'Sus4'],
            4: ['Shell Dom7', 'Major', 'Power + b7', 'Sus4', 'Tritone Shell', 'Major b5'],
            5: ['Shell Dom7', 'Major', 'Power + b7', 'Sus4', 'Tritone Shell',
                'Major b5', 'Sus2 + b7', 'Cluster b7', 'Augmented'],
        },
        # maj7
        'maj7': {
            1: ['Major'],
            2: ['Shell Maj7', 'Major'],
            3: ['Shell Maj7', 'Major', 'Shell Maj6', 'Power + Maj7'],
            4: ['Shell Maj7', 'Major', 'Shell Maj6', 'Power + Maj7', 'Power + 6', 'Sus2'],
            5: ['Shell Maj7', 'Major', 'Shell Maj6', 'Power + Maj7', 'Power + 6',
                'Sus2', 'Quartal', 'Tritone Shell'],
        },
        # min7
        'min7': {
            1: ['Minor'],
            2: ['Shell Min7', 'Minor'],
            3: ['Shell Min7', 'Minor', 'Shell Min6', 'Power + b7'],
            4: ['Shell Min7', 'Minor', 'Shell Min6', 'Power + b7', 'Sus2', 'Sus4'],
            5: ['Shell Min7', 'Minor', 'Shell Min6', 'Power + b7', 'Sus2',
                'Sus4', 'Quartal', 'Shell MinMaj7'],
        },
        'dim': {
            1: ['Diminished'],
            2: ['Diminished'],
            3: ['Diminished', 'Shell Min7'],
            4: ['Diminished', 'Shell Min7', 'Sus2 b5'],
            5: ['Diminished', 'Shell Min7', 'Sus2 b5', 'Sus4 b5', 'Tritone Shell'],
        },
        'aug': {
            1: ['Augmented'],
            2: ['Augmented'],
            3: ['Augmented', 'Major b5'],
            4: ['Augmented', 'Major b5', 'Aug Sus4'],
            5: ['Augmented', 'Major b5', 'Aug Sus4', 'Aug Quartal', 'Whole Tone Tri'],
        },
    }

    def _pick_triad_shape_for_quality(self, quality):
        """Given a progression chord quality (e.g. 'major'), pick a triad shape
        name from the Adventure-gated family. Higher Adventure unlocks more shapes.
        Returns a triad name from TRIADS (always 3 notes after voicing build)."""
        family = self._TRIAD_FAMILY.get(quality, self._TRIAD_FAMILY['major'])
        adv = max(1, min(5, self.adventure))
        candidates = family.get(adv, family[1])
        # Filter to only those whose level <= adventure (defensive)
        valid = [c for c in candidates if c in TRIADS and TRIADS[c]['level'] <= adv]
        if not valid:
            valid = [c for c in candidates if c in TRIADS] or ['Major']
        return random.choice(valid)


    # Adventure-boosted Markov progression generator
    _ADV_BOOST_CHORDS = {
        # idx: (boost factor at Adv 3, Adv 4, Adv 5)
        # bII, bIII, bVI, bVII
        15: (1.5, 3.0, 6.0),
        16: (2.0, 5.0, 10.0),
        17: (2.0, 4.0, 8.0),
        18: (1.5, 3.0, 5.0),
        # Secondary dominants
        19: (2.0, 4.0, 8.0),
        20: (2.0, 4.0, 8.0),
        21: (1.5, 3.0, 6.0),
        22: (1.5, 3.0, 6.0),
        # Augmented sixth chords
        23: (1.0, 3.0, 8.0),
        24: (1.0, 3.0, 8.0),
        # Tritone sub
        29: (1.0, 3.0, 6.0),
    }

    def _generate_with_adv_boost(self, length, genre, tonality, tonic, cadence=False):
        """Generate a Markov progression with Adventure-boosted weights for
        borrowed/chromatic chords. Falls back to the standard generator for A1-A2."""
        # Import here to access engine internals
        from harmony_engine import TRANS, START_WEIGHTS, DIFFICULTY_ALLOWED, TONIC_IDX, CHORD_BY_IDX, NOTES as HE_NOTES, QUALITY_INTERVALS
        import copy as _copy

        adv = self.adventure
        if adv < 3:
            # Use the unboosted standard generator
            return generate_progression(length, genre, tonality,
                                        LEVEL_TO_MARKOV.get(adv, 'beginner'),
                                        tonic, cadence=cadence)

        # Pick boost column
        boost_col = {3: 0, 4: 1, 5: 2}.get(adv, 0)

        # Copy transition matrix and apply boosts to destination weights
        mat = _copy.deepcopy(TRANS.get(genre, TRANS['pop']).get(tonality, {}))
        for from_idx, dests in mat.items():
            for to_idx in list(dests.keys()):
                boost_tuple = self._ADV_BOOST_CHORDS.get(to_idx)
                if boost_tuple:
                    factor = boost_tuple[boost_col]
                    dests[to_idx] = int(round(dests[to_idx] * factor))

        # Boost starting weights similarly
        sw = dict(START_WEIGHTS.get((genre, tonality), {}))
        for idx in list(sw.keys()):
            boost_tuple = self._ADV_BOOST_CHORDS.get(idx)
            if boost_tuple:
                factor = boost_tuple[boost_col]
                sw[idx] = int(round(sw[idx] * factor))

        # Reuse the engine's generator pattern but with our patched matrices.
        # Implementation is small enough to inline here.
        difficulty = LEVEL_TO_MARKOV.get(adv, 'advanced')
        allowed = DIFFICULTY_ALLOWED[difficulty]
        tonic_idx = TONIC_IDX[tonality]

        def wpick(weights):
            filtered = {k: v for k, v in weights.items() if k in allowed}
            if not filtered: return None
            total = sum(filtered.values())
            if total <= 0: return None
            r = random.random() * total
            cum = 0
            for idx, w in filtered.items():
                cum += w
                if r <= cum: return idx
            return list(filtered.keys())[-1]

        current = wpick(sw) or tonic_idx
        progression = []
        prev = None
        for step in range(length):
            chord = CHORD_BY_IDX.get(current, CHORD_BY_IDX[tonic_idx])
            ivs = QUALITY_INTERVALS.get(chord.quality, [0,4,7])
            root = (tonic + chord.semitones) % 12
            notes = [HE_NOTES[(root + iv) % 12] for iv in ivs]
            progression.append({'chord': chord, 'roman': chord.roman,
                                'quality': chord.quality, 'function': chord.function,
                                'root_semitone': root, 'notes': notes,
                                'description': chord.description})
            prev = current
            if cadence and step == length - 2 and length >= 3:
                dom = 4 if tonality == 'major' else 11
                if dom in allowed:
                    current = dom; continue
            transitions = mat.get(current, {}) or mat.get(tonic_idx, {tonic_idx: 1})
            nxt = wpick(transitions) or tonic_idx
            if nxt == prev and length > 2:
                alt_filtered = {k: v for k, v in transitions.items() if k != prev}
                alt = wpick(alt_filtered)
                if alt is not None: nxt = alt
            current = nxt
        return progression

    def _target_from_chord(self, chord_info):
        """
        Given chord info from a progression {root_semitone, quality, roman, function, description},
        produce a practice target dict appropriate for the current drill.
        For Triads: use override triad type if set, else map chord quality to a basic triad.
        For Modes:  use override mode if set, else default to Ionian for major chords / Aeolian for minor.
        For Notes:  drill the root note of the chord.
        For Progressions: just use the chord's intervals.
        """
        drill = self.prac_drill.get()
        rn    = NOTES[chord_info['root_semitone']]
        q     = chord_info['quality']
        roman = chord_info.get('roman', '')

        if drill == 'Notes':
            return {
                'name': rn,
                'subtitle': f'Root of {rn} {q} ({roman})',
                'root': chord_info['root_semitone'],
                'intervals': None,
                'dot_types': None,
                'prog_chord': chord_info,
            }

        if drill == 'Triads':
            override = self.prac_triad_override.get()
            if override and override != 'Follow progression' and override in TRIADS:
                td = TRIADS[override]
                triad_name = override
            else:
                # Follow progression: in Loop mode the picked shape may be locked
                # per chord position, unless 'Change triads each loop' is ticked.
                seq = self.prac_sequence.get()
                slot = chord_info.get('chord_idx')
                use_lock = (seq == 'Loop'
                            and slot is not None
                            and not self.prac_loop_change_triads.get())
                if use_lock and slot in self._loop_triad_shapes:
                    triad_name = self._loop_triad_shapes[slot]
                else:
                    triad_name = self._pick_triad_shape_for_quality(q)
                    if use_lock:
                        self._loop_triad_shapes[slot] = triad_name
                td = TRIADS.get(triad_name, TRIADS['Major'])
            bass_off, ivs, dt, inv_label = self._pick_inversion(td['intervals'], td['dot_types'])
            bass_semi = (chord_info['root_semitone'] + bass_off) % 12
            slash = f'/{NOTES[bass_semi]}' if inv_label != 'Root position' else ''
            return {
                'name': triad_name,
                'subtitle': f'{rn}{slash} {triad_name}  —  {roman} in progression  ·  {inv_label}',
                'root': bass_semi,        # fretboard math is now relative to the bass
                'chord_root': chord_info['root_semitone'],
                'intervals': ivs,
                'dot_types': dt,
                'prog_chord': chord_info,
                'inv_label': inv_label,
            }

        if drill == 'Modes':
            override = self.prac_mode_override.get()
            if override and not override.startswith('Follow') and override in MODES:
                md = MODES[override]
                mode_name = override
            else:
                mode_map = {'major':'Ionian (Major)','minor':'Aeolian (Minor)',
                            'dim':'Locrian','aug':'Lydian',
                            'dom7':'Mixolydian','maj7':'Ionian (Major)','min7':'Dorian'}
                mode_name = mode_map.get(q, 'Ionian (Major)')
                md = MODES.get(mode_name, MODES['Ionian (Major)'])
            ivs = md['intervals']
            formula = '  '.join(DEG_NAMES.get(i, str(i)) for i in ivs)
            # Modes drill: scale is built around the KEY's root (not the chord root),
            # but the TARGET LANDING NOTE for this chord step is the chord's root.
            # The scale stays in the key; the user must land on the current chord root.
            key_root = self.root_note  # fixed key when Loop/Infinite
            self._modes_target_note = chord_info['root_semitone']
            return {
                'name': mode_name,
                'subtitle': f'In {NOTES[key_root]} {mode_name} — land on {NOTES[chord_info["root_semitone"]]} ({roman})  ·  {formula}',
                'root': key_root,
                'intervals': ivs,
                'dot_types': None,
                'prog_chord': chord_info,
                'target_note': chord_info['root_semitone'],
            }

        # Progressions drill → just show the chord
        from harmony_engine import QUALITY_INTERVALS as QI
        base_ivs = QI.get(q, [0, 4, 7])
        base_dt  = ['root','third','fifth'] + ['interval']*(len(base_ivs)-3)
        bass_off, ivs, dt, inv_label = self._pick_inversion(base_ivs, base_dt)
        bass_semi = (chord_info['root_semitone'] + bass_off) % 12
        slash = f'/{NOTES[bass_semi]}' if inv_label != 'Root position' else ''
        return {
            'name': f'{rn}{slash} {roman}',
            'subtitle': f'{chord_info.get("description","")}  —  {chord_info.get("function","")}  ·  {inv_label}',
            'root': bass_semi,
            'chord_root': chord_info['root_semitone'],
            'intervals': ivs,
            'dot_types': dt,
            'prog_chord': chord_info,
            'inv_label': inv_label,
        }

    def _markov_extend(self):
        """Ensure the infinite Markov cache has enough chords ahead of current index."""
        if not self._inf_prog_cache:
            self._inf_prog_cache = self._generate_with_adv_boost(
                8, self.markov_genre.get(), self.markov_tonality.get(),
                self.root_note, cadence=False)
            self._inf_prog_idx = 0
        if self._inf_prog_idx >= len(self._inf_prog_cache):
            extension = self._generate_with_adv_boost(
                4, self.markov_genre.get(), self.markov_tonality.get(),
                self.root_note, cadence=False)
            self._inf_prog_cache.extend(extension[1:])

    def _prac_next_target(self):
        """Pick next target according to sequence mode."""
        seq   = self.prac_sequence.get()
        drill = self.prac_drill.get()

        # ── LOOP mode ───────────────────────────────────────────────────────
        if seq == 'Loop':
            # Decide source: generated Markov progression or named progression
            if self.prac_loop_generate.get():
                if not self._generated_loop_prog:
                    self._prac_loop_regenerate()
                if not self._generated_loop_prog: return None

                prog_list = self._generated_loop_prog
                chord_idx = self._loop_chord_idx % len(prog_list)
                # Regenerate at start of new cycle (so each loop iteration
                # produces a fresh progression from the same settings)
                if chord_idx == 0 and self._loop_chord_idx > 0:
                    self._prac_loop_regenerate()
                    prog_list = self._generated_loop_prog
                    if self.prac_loop_change_triads.get():
                        self._clear_triad_cache()
                self._loop_chord_idx = (self._loop_chord_idx + 1) % len(prog_list)
                p = prog_list[chord_idx]
                # Random key: re-pick at start of cycle (chord_idx == 0)
                if self.prac_root_mode.get() == 'Random' and chord_idx == 0:
                    self._loop_key_root = random.randint(0, 11)
                elif not hasattr(self, '_loop_key_root'):
                    self._loop_key_root = self.root_note
                if self.prac_root_mode.get() == 'Fixed':
                    self._loop_key_root = self.root_note
                # The Markov generator already used self.root_note as key. If the
                # user has changed the key since, the generator output's
                # root_semitone is still anchored to the OLD key. For now we
                # trust the generator's output (it regenerates when settings
                # change). Pass through directly.
                chord_info = dict(p)  # copy to avoid mutating cache
                chord_info['chord_idx'] = chord_idx
                chord_info['description'] = (
                    f'Generated [{",".join([g for g,v in self.prac_loop_genres.items() if v.get()]) or "pop"}]  '
                    f'—  chord {chord_idx+1}/{len(prog_list)}'
                )
                return self._target_from_chord(chord_info)

            # Named-progression branch (unchanged)
            avail = [p for p in NAMED_PROGRESSIONS if p['level'] <= self.adventure]
            if not avail: return None
            prog_idx = min(self.prac_loop_prog_idx.get(), len(avail)-1)
            prog     = avail[prog_idx]
            chords   = prog['chords']
            if not chords: return None
            chord_idx = self._loop_chord_idx % len(chords)
            # Detect cycle boundary BEFORE incrementing
            if chord_idx == 0 and self._loop_chord_idx > 0:
                if self.prac_loop_change_triads.get():
                    self._clear_triad_cache()
            self._loop_chord_idx = (self._loop_chord_idx + 1) % len(chords)
            offset, quality_code = chords[chord_idx]
            if self.prac_root_mode.get() == 'Random' and chord_idx == 0:
                self._loop_key_root = random.randint(0, 11)
            elif not hasattr(self, '_loop_key_root'):
                self._loop_key_root = self.root_note
            if self.prac_root_mode.get() == 'Fixed':
                self._loop_key_root = self.root_note
            key_root = self._loop_key_root
            chord_root = (key_root + offset) % 12
            q_map = {'M':'major','m':'minor','d':'dim','a':'aug','p':'power'}
            chord_info = {
                'root_semitone': chord_root,
                'quality': q_map.get(quality_code, 'major'),
                'roman': f'{["I","bII","II","bIII","III","IV","#IV","V","bVI","VI","bVII","VII"][offset]}{["","m","°","+","5"][["M","m","d","a","p"].index(quality_code)]}',
                'function': 'T',
                'chord_idx': chord_idx,
                'description': f'{prog["name"]}  ({prog["genre"]}  Lv{prog["level"]})  —  chord {chord_idx+1}/{len(chords)}',
            }
            return self._target_from_chord(chord_info)

        # ── RANDOM mode ─────────────────────────────────────────────────────
        if seq == 'Random':
            self._modes_target_note = None
            pool = self._prac_pool()
            if not pool: return None
            prev_name = self._prac_target['name'] if self._prac_target else None
            choices = [t for t in pool if t['name'] != prev_name] or pool
            return random.choice(choices)

        # ── INFINITE mode (Markov chain for all drills) ────────────────────
        if seq == 'Infinite':
            self._markov_extend()
            p = self._inf_prog_cache[self._inf_prog_idx]
            self._inf_prog_idx += 1
            # Track in 16-chord history
            self._inf_history.append(p)
            if len(self._inf_history) > 16: self._inf_history.pop(0)
            return self._target_from_chord(p)

        return None

    # ── Game loop ──────────────────────────────────────────────────────────────

    def _prac_toggle(self):
        if self.prac_running:
            self._prac_stop()
        else:
            self._prac_start()

    def _prac_start(self):
        self.prac_running = True
        self._prac_start_btn.config(text='■  Stop', bg='#8B2020', fg='#FFB0B0')
        self._loop_pool = []
        self._prac_advance()

    def _prac_stop(self):
        self.prac_running = False
        if self.prac_timer_id:
            self.after_cancel(self.prac_timer_id); self.prac_timer_id = None
        self._prac_start_btn.config(text='▶  Start', bg=GREEN, fg='#04342C')

    def _prac_advance(self):
        """Move to next target and restart the timer."""
        if self.prac_timer_id:
            self.after_cancel(self.prac_timer_id)

        target = self._prac_next_target()
        if not target: return

        # Pick root
        root = self._prac_pick_root(target)
        target = dict(target); target['active_root'] = root
        self._prac_target = target

        self._prac_update_display()
        self._prac_update_history()
        self.prac_running = True

        # Schedule next advance
        ms = self._prac_target_ms()
        self.prac_timer_id = self.after(ms, self._prac_auto_advance)


    def _prac_auto_advance(self):
        """Called when timer expires — no self-report, just move on."""
        self._prac_advance()

    def _prac_mark(self, correct: bool):
        """User self-reports got_it or missed."""
        if not self.prac_running or not self._prac_target: return
        s = self._prac_score
        if correct:
            s['correct'] += 1; s['streak'] += 1
            s['best'] = max(s['best'], s['streak'])
        else:
            s['missed'] += 1; s['streak'] = 0
        # Record in history
        name = self._prac_target['name']
        rn   = NOTES[self._prac_target['active_root']]
        label = f'{rn} {name}' if self.prac_drill.get() != 'Notes' else rn
        self._prac_history.append((label, correct))
        if len(self._prac_history) > 16: self._prac_history.pop(0)
        self._prac_update_score()
        self._prac_update_history()
        self._prac_advance()   # immediately show next

    def _prac_reset_score(self):
        self._prac_score = {'correct':0,'missed':0,'streak':0,'best':0}
        self._prac_history = []
        self._inf_history  = []
        self._prac_update_score()
        self._prac_update_history()

    # ── Practice display ───────────────────────────────────────────────────────

    def _prac_update_display(self):
        target = self._prac_target
        if not target: return
        root = target['active_root']
        rn   = NOTES[root]
        drill = self.prac_drill.get()

        if drill == 'Notes':
            self._prac_target_lbl.config(text=f'Find all:  {rn}')
            self._prac_sub_lbl.config(text='Locate every occurrence across all 6 strings')
        elif drill in ('Triads','Modes'):
            self._prac_target_lbl.config(text=f'{rn}  {target["name"]}')
            self._prac_sub_lbl.config(text=target.get('subtitle',''))
        elif drill == 'Progressions':
            self._prac_target_lbl.config(text=target['name'])
            self._prac_sub_lbl.config(
                text=f'Key of {rn}  ·  {target.get("subtitle","")}')

        self._prac_update_score()
        self._prac_draw()

    def _prac_update_score(self):
        s = self._prac_score
        total = s['correct'] + s['missed']
        pct   = int(100 * s['correct'] / total) if total else 0
        self._prac_score_lbl.config(
            text=f'✓ {s["correct"]}   ✗ {s["missed"]}   {pct}%   Best streak: {s["best"]}')
        streak_text = f'🔥 {s["streak"]}' if s['streak'] >= 3 else (f'Streak: {s["streak"]}' if s['streak'] else '')
        self._prac_streak_lbl.config(text=streak_text)

    def _prac_update_history(self):
        for w in self._prac_history_frame.winfo_children(): w.destroy()
        seq = self.prac_sequence.get()

        # ── Infinite mode: show last 16 chord history as a grid ────────────
        if seq == 'Infinite' and self._inf_history:
            tk.Label(self._prac_history_frame, text='Chord history (last 16):',
                     bg=BG, fg=MUTED, font=('Helvetica',9,'bold')
                     ).grid(row=0, column=0, columnspan=8, sticky='w', pady=(0,4))
            for i, chord in enumerate(self._inf_history[-16:]):
                row, col = divmod(i, 8)
                rn   = NOTES[chord['root_semitone']]
                roman = chord['roman']
                fn   = chord['function']
                fn_col = {'T':ACCENT,'S':BLUE,'D':'#e06060','X':PURPLE}.get(fn, MUTED)
                cell = tk.Frame(self._prac_history_frame, bg=PANEL2,
                                padx=6, pady=3, relief='flat')
                cell.grid(row=row+1, column=col, padx=2, pady=2, sticky='nsew')
                # Highlight current (last) chord
                is_current = (i == len(self._inf_history[-16:]) - 1)
                cell.config(bg=ACCENT if is_current else PANEL2)
                lc = '#1a1a1a' if is_current else TEXT
                sc = '#412402' if is_current else fn_col
                tk.Label(cell, text=roman, bg=cell['bg'], fg=lc,
                         font=('Helvetica',10,'bold')).pack()
                tk.Label(cell, text=f'{rn}', bg=cell['bg'], fg=sc,
                         font=('Helvetica',8)).pack()
            return

        # ── Normal mode: single row of last 16 ─────────────────────────────
        if not self._prac_history: return
        tk.Label(self._prac_history_frame, text='History:', bg=BG, fg=MUTED,
                 font=('Helvetica',9,'bold')).pack(side='left', padx=(0,8))
        for name, correct in self._prac_history[-16:]:
            col = '#4db896' if correct else '#c05050'
            sym = '✓' if correct else '✗'
            tk.Label(self._prac_history_frame,
                     text=f'{sym} {name}', bg=BG, fg=col,
                     font=('Helvetica',9)).pack(side='left', padx=3)

    def _prac_get_dots(self):
        """Compute fretboard dots for the current practice target.

        Strings filter logic:
          - When NOT all strings are ticked, dots are only drawn around root
            occurrences that sit on a ticked string. For each such root, we add
            the chord's 3rd, 5th and other intervals on neighbouring strings/frets
            within ~5 frets, building a CAGED-style "shape" anchored to that root.
          - When all strings are ticked, behaviour is the standard full fretboard.
        """
        target = self._prac_target
        if not target: return []
        tuning   = TUNINGS[self.tuning_name.get()]
        root     = target['active_root']
        reveal   = self.reveal.get()
        drill    = self.prac_drill.get()
        inv_root = self.prac_inv_root.get()

        ticked = [i for i, v in enumerate(self._string_vars) if v.get()]
        if not ticked: ticked = list(range(6))
        all_strings = (len(ticked) == 6)

        def note_at(s, f): return (tuning[s] + f) % 12

        # ── Notes drill: just show every occurrence of the target note ────────
        if drill == 'Notes':
            dots = []
            anchor_max = self._max_anchor_fret()
            for s in range(6):
                for f in range(self._max_fret() + 1):
                    n = note_at(s, f)
                    if n == root:
                        if not all_strings and s not in ticked:
                            continue
                        if f > anchor_max:
                            # Beyond anchor range — show as faded background note
                            if reveal == 'Root only': continue
                            dots.append((s, f, 'all', NOTES[n]))
                        else:
                            dots.append((s, f, 'root', NOTES[n]))
                    else:
                        if reveal == 'Root only': continue
                        dots.append((s, f, 'all', NOTES[n]))
            return dots

        # ── Resolve chord/scale intervals and dot-type labels ─────────────────
        ivs = target.get('intervals') or [0, 4, 7]
        dt  = target.get('dot_types') or ['root','third','fifth','interval','interval','interval','interval']
        ivs_mod = [iv % 12 for iv in ivs]

        # Inversion handling: when intervals already encode an inversion
        # (target has 'inv_label' set), the dot_types are already correctly
        # rotated so position 0 carries 'root' colour for the bass note.
        # Otherwise (legacy / no inversion), behave as before.
        target_has_inversion = bool(target.get('inv_label')) and target.get('inv_label') != 'Root position'
        bass_iv_mod  = ivs[0] % 12
        true_root_iv = 0
        def role_for_iv(iv):
            if iv in ivs_mod:
                idx = ivs_mod.index(iv)
                return dt[idx] if idx < len(dt) else 'interval'
            return None

        # ── ALL STRINGS TICKED: show all chord tones across the whole neck ───
        if all_strings:
            out = []
            for s in range(6):
                for f in range(self._max_fret() + 1):
                    iv = (note_at(s, f) - root) % 12
                    role = role_for_iv(iv)
                    if role is None: continue
                    if reveal == 'Root only' and role != 'root': continue
                    if reveal == 'Partial (root + 5th)' and role == 'third': continue
                    out.append((s, f, role, NOTES[note_at(s, f)]))
            return out

        # ── PARTIAL STRINGS: build ONE closed-position voicing per root anchor ─
        # Algorithm:
        #   1. Find each root occurrence on a ticked string (the "anchor").
        #   2. Walk the intervals in order (e.g. [0, 4, 7] for major):
        #      - Anchor uses interval 0 on the ticked string.
        #      - For each subsequent interval, look on the NEXT ascending string
        #        for that note within ±4 frets of the anchor.
        #      - If not found on the next string, try the string after (skip one).
        #      - If still not found, drop that note from the voicing (rare).
        #   3. This gives one playable closed-position triad/chord per anchor.
        #   4. Reveal filters apply: 'Root only' shows just the anchor;
        #      'Partial' drops the 3rd.

        FRET_REACH = 4

        # Decide which intervals correspond to which roles (using dot_types order)
        # ivs may have an octave (e.g. Power = [0,7,12]); we still want to voice it.
        # For Triads drill: always limit to 3 notes (drop any extensions from richer shapes
        # like Quartal/Shell chords). For other drills, use the full interval list.
        interval_list = list(ivs)
        if drill == 'Triads':
            interval_list = interval_list[:3]
        role_list = []
        for i, iv in enumerate(interval_list):
            role = dt[i] if i < len(dt) else 'interval'
            role_list.append(role)

        # Skip 3rd if reveal == Partial
        if reveal == 'Partial (root + 5th)':
            keep_mask = [r != 'third' for r in role_list]
        else:
            keep_mask = [True] * len(role_list)

        # Find anchor positions on ticked strings.
        # Anchor on whatever the voicing's position-0 note is (the bass).
        target_root_iv = bass_iv_mod
        anchors = []  # list of (string, fret)
        for s in ticked:
            for f in range(self._max_fret() + 1):
                if (note_at(s, f) - root) % 12 == target_root_iv:
                    anchors.append((s, f))

        out = []

        def find_note_on_string(target_iv_mod, string_idx, anchor_fret):
            """Return fret on this string within ±FRET_REACH of anchor_fret
               that matches target_iv_mod, or None."""
            best = None
            best_dist = 999
            for f in range(max(0, anchor_fret - FRET_REACH),
                           min(13, anchor_fret + FRET_REACH + 1)):
                if (note_at(string_idx, f) - root) % 12 == target_iv_mod:
                    dist = abs(f - anchor_fret)
                    if dist < best_dist:
                        best = f; best_dist = dist
            return best

        for (anchor_s, anchor_f) in anchors:
            # Always include the anchor (interval 0 = root, or first interval if inv_root)
            anchor_iv_mod = interval_list[0] % 12
            anchor_role = role_list[0]
            if keep_mask[0]:
                out.append((anchor_s, anchor_f, anchor_role, NOTES[note_at(anchor_s, anchor_f)]))

            if reveal == 'Root only':
                continue

            # Walk through remaining intervals, placing each on next available string
            next_string = anchor_s + 1   # strings ascend: low E (0) → high e (5)
            for idx in range(1, len(interval_list)):
                if not keep_mask[idx]:
                    continue
                iv_mod = interval_list[idx] % 12
                role   = role_list[idx]

                # Try next adjacent string, then skip-one as fallback
                placed = False
                for try_string in [next_string, next_string + 1]:
                    if try_string >= 6:
                        break
                    fret = find_note_on_string(iv_mod, try_string, anchor_f)
                    if fret is not None:
                        out.append((try_string, fret, role, NOTES[note_at(try_string, fret)]))
                        next_string = try_string + 1   # advance past the string we used
                        placed = True
                        break
                # If we couldn't place this interval, it's simply dropped from the voicing

        return out

    def _prac_draw(self):
        """Draw fretboard on the practice canvas."""
        c = self._prac_canvas
        c.delete('all')
        W = c.winfo_width() or 920
        FRETS = 24 if self.prac_24frets.get() else 12
        H=210; L=48; R=16; T=28; SG=28; FW=(W-L-R)/FRETS

        for f in range(FRETS+1):
            x = L+f*FW
            c.create_line(x,T-6,x,T+5*SG+6,
                          fill='#5a4a30' if f==0 else '#3d3020',
                          width=3 if f==0 else 1)
        marker_frets = [3,5,7,9,12,15,17,19,21,24] if FRETS == 24 else [3,5,7,9,12]
        for f in marker_frets:
            mx = L+(f-0.5)*FW
            if f in (12, 24):
                c.create_oval(mx-18,H-14,mx-10,H-6,fill='#3d3020',outline='')
                c.create_oval(mx+10,H-14,mx+18,H-6,fill='#3d3020',outline='')
            else:
                c.create_oval(mx-5,H-14,mx+5,H-6,fill='#3d3020',outline='')
        for f in range(1,FRETS+1):
            c.create_text(L+(f-0.5)*FW,H-2,text=str(f),fill='#4a4030',font=('Helvetica',9))

        labels = TUNING_LABELS[self.tuning_name.get()]
        for s in range(6):
            y = T+(5-s)*SG; thick = max(0.5,3.5-s*0.5)
            c.create_line(L-4,y,W-R,y,fill='#7a6a50',width=thick)
            c.create_text(L-8,y,text=labels[s],anchor='e',fill=MUTED,font=('Helvetica',10))
        c.create_rectangle(L-5,T-6,L-1,T+5*SG+6,fill='#c8b878',outline='')

        DC = {'root':(ACCENT,'#412402'),'third':(GREEN,'#04342C'),
              'fifth':(BLUE,'#042C53'),'interval':(PURPLE,'#26215C'),
              'target':('#e02020','#FFE0E0'),'all':(None,MUTED)}
        for (s,f,typ,label) in self._prac_get_dots():
            x = L-20 if f==0 else L+(f-0.5)*FW; y = T+(5-s)*SG
            fc,tc = DC.get(typ,(None,MUTED))
            if typ=='all':
                c.create_oval(x-9,y-9,x+9,y+9,fill='#2a2010',outline='#3a3020',width=1)
                c.create_text(x,y,text=label,fill='#4a4535',font=('Helvetica',8))
            else:
                c.create_oval(x-13,y-13,x+13,y+13,fill=fc,outline='')
                c.create_text(x,y+1,text=label,fill=tc,font=('Helvetica',9,'bold'))


if __name__ == '__main__':
    if not ENGINE_OK:
        print(f'ERROR: harmony_engine.py not found.\n{ENGINE_ERR}')
        sys.exit(1)
    GuitarTrainer().mainloop()