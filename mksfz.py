#!/usr/bin/env python3

import enum
import sys

next_cc = 102 # next available CC number
instrument_first_cc = {} # dict on abbr of first cc# for controls

# tuple per level range, of (name, lo CC, hi CC)
level_ranges = {
      0: ("00", 0,                      int(1.0 * 0.125 * 128)-1)
    , 1: ("25", int(1.0 * 0.125 * 128), int(3.0 * 0.125 * 128)-1)
    , 2: ("50", int(3.0 * 0.125 * 128), int(5.0 * 0.125 * 128)-1)
    , 3: ("75", int(5.0 * 0.125 * 128), int(7.0 * 0.125 * 128)-1)
    , 4: ("10", int(7.0 * 0.125 * 128), 127)
}

class Control(enum.Enum):
    TONE = "tone"
    TUNING = "tuning"
    DECAY = "decay"
    SNAPPY = "snappy"

class Instrument(object):
    abbrev = ""
    name = ""
    controls = () # tuple of Control, at most two

    def __init__(self, abbr:str, key:str, n:str, ctrls:list[Control], group:int=None):
        global instrument_first_cc
        global next_cc
        self.abbr = abbr
        self.note = key
        self.name = n
        self.controls = ctrls
        self.ccs = {}
        self.group = group

        if not self.abbr in instrument_first_cc:
            # reserve a MIDI CC number for each control
            instrument_first_cc[self.abbr] = next_cc
            for cc in self.controls:
                next_cc += 1

    def sample_fname(self, levels:list[str]):
        n = f"{self.abbr}8/{self.abbr.upper()}"
        for lev in levels:
            # append level string for this control to name
            n += lev
        return n + ".WAV"

    def render_region(self, ctrl_indexes:list[int]):
        print(f"<region> key={self.note:3} loop_mode=one_shot", end="")
        match len(ctrl_indexes):
            case 0:
                print(f" sample={self.sample_fname(())}", end="")
            case 1:
                c1_cc = instrument_first_cc[self.abbr]
                c1_ix = ctrl_indexes[0]
                c1_id = level_ranges[c1_ix][0]
                c1_lo = level_ranges[c1_ix][1]
                c1_hi = level_ranges[c1_ix][2]
                print(f" sample={self.sample_fname((c1_id,)):14}", end="")
                print(f" locc{c1_cc}={c1_lo:03} hicc{c1_cc}={c1_hi:03}", end="")
            case 2:
                c1_cc = instrument_first_cc[self.abbr]
                c1_ix = ctrl_indexes[0]
                c1_id = level_ranges[c1_ix][0]
                c1_lo = level_ranges[c1_ix][1]
                c1_hi = level_ranges[c1_ix][2]
                c1_cc = instrument_first_cc[self.abbr]
                c2_ix = ctrl_indexes[1]
                c2_id = level_ranges[c2_ix][0]
                c2_lo = level_ranges[c2_ix][1]
                c2_hi = level_ranges[c2_ix][2]
                c2_cc = c1_cc + 1
                print(f" sample={self.sample_fname((c1_id,c2_id)):14}", end="")
                print(f" locc{c1_cc}={c1_lo:03} hicc{c1_cc}={c1_hi:03}", end="")
                print(f" locc{c2_cc}={c2_lo:03} hicc{c2_cc}={c2_hi:03}", end="")

        if self.group:
            print(f" group={self.group} off_by={self.group}", end="")
        print()

    def render_sfz(self):
        match len(self.controls):
            case 0:
                self.render_region(())
            case 1:
                for lev in level_ranges.keys():
                    self.render_region((lev,))
            case 2:
                for lev1 in level_ranges.keys():
                    for lev2 in level_ranges.keys():
                        self.render_region((lev1, lev2))

    def render_control_labels(self):
        cc = instrument_first_cc[self.abbr]
        for ctrl in self.controls:
            print(f"label_cc{cc}={self.name} {ctrl.value} set_cc{cc}=64")
            cc += 1

    def render_comments(self):
        print(f"# {self.note:3} {self.abbr} {self.name}", end="")
        if len(self.controls) > 0:
            print(f", controls:", end="")
            for ctrl in self.controls:
                print(f" {ctrl.value}", end="")
        print()


instruments = (
    Instrument(  "bd", "C1",  "bass drum", (Control.TONE, Control.DECAY,))
    , Instrument("sd", "D1",  "snare drum", (Control.TONE, Control.SNAPPY,))
    , Instrument("lt", "F1",  "low tom", (Control.TUNING,))
    , Instrument("mt", "B1",  "medium tom", (Control.TUNING,))
#   , Instrument("sd", "E1",  "+electric snare", (Control.TONE, Control.SNAPPY,))
    , Instrument("ht", "C2",  "high tom", (Control.TUNING,))
#   , Instrument("ht", "D2",  "+high tom", (Control.TUNING,))
    , Instrument("lc", "D3",  "low conga", (Control.TUNING,))
    , Instrument("mc", "Eb3", "medium conga", (Control.TUNING,))
    , Instrument("hc", "E3",  "high conga", (Control.TUNING,))
    , Instrument("cl", "Eb4", "clave", ())
    , Instrument("rs", "Db1", "rimshot", ())
    , Instrument("ma", "Bb3", "maracas", ())
    , Instrument("cp", "Eb1", "hand clap", ())
    , Instrument("cb", "Ab2", "cowbell", ())
    , Instrument("cy", "Eb2", "cymbal", (Control.TONE, Control.DECAY,))
#   , Instrument("cy", "B2",  "+cymbal", (Control.TONE, Control.DECAY,))
    , Instrument("oh", "Bb1", "open hihat", (Control.DECAY,), group=1)
    , Instrument("ch", "Gb1", "closed hihat", (), group=1)
)

def main():
    for inst in instruments:
        inst.render_comments()

    print("<control>")
    for inst in instruments:
        txt = inst.render_control_labels()

    print("<master>")
    for inst in instruments:
        txt = inst.render_sfz()

main()
