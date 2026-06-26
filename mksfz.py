#!/usr/bin/env python3

import enum
import sys

next_cc = 75 # next available CC number
instrument_first_cc = {} # dict on abbr of first cc# for controls

header = '''# Fischer TR-808 SFZ mapping
#
# samples by: "Michael Fischer"
# SFZ by: "Jeff Learman & Jofemodo (Zynthian)"
# license: "CC0"
# original source_url: "https://github.com/tidalcycles/sounds-tr808-fischer"
# current (temporary) source_url: "https://github.com/jlearman/sounds-tr808-fischer"
# size: "12MB"
'''

header_no_xfades = '''
# No control crossfades. Uses one voice per note.
'''

header_keyswitches = '''
# Keyswitches:
#  A0  = crossfades for decay/snappy control, uses two voices per note,
#        for bass drum, snare drum, and cymbal only
#  Bb0 = no control crossfades - uses one voice per note
'''

header_zynthian_yaml = '''
controllers:
 Global:
  volume:
   midi_cc: 7
   value: 127
   name: "Volume"
  pan:
   midi_cc: 10
   value: 64
   name: "Pan"
  expression:
   midi_cc: 11
   value: 127
   name: "Expression"
'''

header_zynthian_yaml_keyswitches = header_zynthian_yaml + '''
  crossfade:
   graph_path: 'note_on'
   labels: ['OFF', 'ON']
   ticks: [22, 21]
   name: "Cross-Fade Samples"

'''

# tuple per level range, of (name, lo CC, hi CC)
level_ranges = {
      0: ("00", 0,                      int(1.0 * 0.125 * 128)-1)
    , 1: ("25", int(1.0 * 0.125 * 128), int(3.0 * 0.125 * 128)-1)
    , 2: ("50", int(3.0 * 0.125 * 128), int(5.0 * 0.125 * 128)-1)
    , 3: ("75", int(5.0 * 0.125 * 128), int(7.0 * 0.125 * 128)-1)
    , 4: ("10", int(7.0 * 0.125 * 128), 127)
}

def level_midpoint(ix:int):
    match ix:
        case 0:
            return 0
        case 4:
            return 127
        case _:
            return (level_ranges[ix][1] + level_ranges[ix][2]) // 2

# Generate Zynthian YAML Controller label & ticks
control_labels = ["0", "25", "50", "75", "100"]
control_ticks = []
for i in range(len(level_ranges)):
    control_ticks.append(level_midpoint(i))


class Control(enum.Enum):
    LEVEL = "Level"
    PAN = "Pan"
    TONE = "Tone"
    TUNING = "Tuning"
    DECAY = "Decay"
    SNAPPY = "Snappy"

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

    def render_region(self, ctrl_level_indexes:list[int], keyswitch=False):
        res = f"<region>"
        match len(ctrl_level_indexes):
            case 0:
                res += f" sample={self.sample_fname(()):14}"
            case 1:
                c1_cc = instrument_first_cc[self.abbr] + 2
                c1_ix = ctrl_level_indexes[0]
                c1_id = level_ranges[c1_ix][0]
                c1_lo = level_ranges[c1_ix][1]
                c1_hi = level_ranges[c1_ix][2]
                res += f" sample={self.sample_fname((c1_id,)):14}"
                res += f" locc{c1_cc}={c1_lo:03} hicc{c1_cc}={c1_hi:03}"
            case 2:
                c1_cc = instrument_first_cc[self.abbr] + 2
                c1_ix = ctrl_level_indexes[0]
                c1_id = level_ranges[c1_ix][0]
                c1_lo = level_ranges[c1_ix][1]
                c1_hi = level_ranges[c1_ix][2]
                c2_cc = c1_cc + 1
                c2_ix = ctrl_level_indexes[1]
                c2_id = level_ranges[c2_ix][0]
                c2_lo = level_ranges[c2_ix][1]
                c2_hi = level_ranges[c2_ix][2]
                res += f" sample={self.sample_fname((c1_id,c2_id)):14}"
                res += f" locc{c1_cc}={c1_lo:03} hicc{c1_cc}={c1_hi:03}"
                # Only dual-control instruments have tone keyswitch, and tone is always 1st control
                if keyswitch:
                    match c2_ix:
                        case 0: # bottom special case
                            c2_lo       = 0
                            c2_xfout_lo = 0
                            c2_hi       = level_midpoint(c2_ix+1)
                            res += f" locc{c2_cc}={c2_lo:03}"
                            res += f" xfout_locc{c2_cc:3}={c2_xfout_lo:03} xfout_hicc{c2_cc:3}={c2_hi:03}"
                            res += f" hicc{c2_cc:03}={c2_hi:03}"
                        case 4: # top special case
                            c2_lo       = level_midpoint(c2_ix-1)
                            c2_xfin_lo  = c2_lo
                            c2_xfin_hi  = level_midpoint(c2_ix)
                            c2_xfout_lo = c2_xfin_hi
                            c2_xfout_hi = 127
                            c2_hi       = 127
                            res += f" locc{c2_cc}={c2_lo:03}"
                            res += f" xfin_locc{c2_cc:3}={c2_lo:03} xfin_hicc{c2_cc:3}={c2_hi:03}"
                            res += f" hicc{c2_cc:03}={c2_hi:03}"
                        case _: # middle cases
                            c2_lo       = level_midpoint(c2_ix-1)
                            c2_xfin_lo  = c2_lo
                            c2_xfin_hi  = level_midpoint(c2_ix)
                            c2_xfout_lo = c2_xfin_hi
                            c2_xfout_hi = level_midpoint(c2_ix+1)
                            res += f" locc{c2_cc}={c2_lo:03}"
                            res += f" xfin_locc{c2_cc:3}={c2_lo:03} xfin_hicc{c2_cc:3}={c2_hi:03}"
                            res += f" xfout_locc{c2_cc:3}={c2_xfout_lo:03} xfout_hicc{c2_cc:3}={c2_hi:03}"
                            res += f" hicc{c2_cc:03}={c2_hi:03}"
                else:
                    res += f" locc{c2_cc}={c2_lo:03} hicc{c2_cc}={c2_hi:03}"

        if self.group:
            res += f" group={self.group} off_by={self.group}"
        return res + "\n"

    def render_sfz(self, keyswitch=False):
        if keyswitch:
            key_sw = "A0"
        else:
            key_sw = "Bb0"

        res = f"<group> sw_last={key_sw} key={self.note:3} loop_mode=one_shot\n"
        ccnum = instrument_first_cc[self.abbr]
        res += f"volume=-24\n"
        res += f"volume_oncc{ccnum}=48\n"
        res += f"pan_oncc{ccnum + 1}=100\n"
        res += f"pan_curvecc{ccnum + 1}=1\n"
        match len(self.controls):
            case 2:
                res += self.render_region(())
            case 3:
                for lev in level_ranges.keys():
                    res += self.render_region((lev,))
            case 4:
                for lev1 in level_ranges.keys():
                    for lev2 in level_ranges.keys():
                        # only dual-control instruments have tone controls
                        res += self.render_region((lev1, lev2), keyswitch)
        return res

    def render_control_labels(self):
        res = ""
        cc = instrument_first_cc[self.abbr]
        for ctrl in self.controls:
            res += f"label_cc{cc}={self.name} {ctrl.value}\n"
            res += f"set_cc{cc}=64\n"
            cc += 1
        return res

    def render_comments(self):
        res = "# {self.note:3} {self.abbr} {self.name}"
        if len(self.controls) > 0:
            res += f", controls:"
            for ctrl in self.controls:
                res += f" {ctrl.value}"
        return res + "\n"

    def render_zynthian_yaml(self, ticks=True):
        res = f" {self.name}:\n"
        cc = instrument_first_cc[self.abbr]
        for ctrl in self.controls:
            res += self.render_zynthian_yaml_control(ctrl, cc, ticks)
            cc += 1
        return res + "\n"

    def render_zynthian_yaml_control(self, ctrl, cc, ticks=True):
        res = f"  {self.abbr}_{ctrl.value.lower()}:\n"
        res += f"    midi_cc: {cc}\n"
        res += f"    name: {self.name} {ctrl.value}\n"
        res += f"    value: {64}\n"
        if ticks and ctrl not in (Control.LEVEL, Control.PAN):
            res += f"    labels: {control_labels}\n"
            res += f"    ticks: {control_ticks}\n"
        return res

instruments = (
    Instrument(  "bd", "C1",  "BassDrum", (Control.LEVEL, Control.PAN, Control.TONE, Control.DECAY,))
    , Instrument("rs", "Db1", "Rimshot", (Control.LEVEL, Control.PAN, ))
    , Instrument("sd", "D1",  "SnareDrum", (Control.LEVEL, Control.PAN, Control.TONE, Control.SNAPPY,))
    , Instrument("cp", "Eb1", "HandClap", (Control.LEVEL, Control.PAN, ))
#   , Instrument("sd", "E1",  "+Elec.Snare", (Control.LEVEL, Control.PAN, Control.TONE, Control.SNAPPY,))
    , Instrument("lt", "F1",  "LowTom", (Control.LEVEL, Control.PAN, Control.TUNING,))
    , Instrument("ch", "Gb1", "Closed HiHat", (Control.LEVEL, Control.PAN, ), group=1)
    , Instrument("oh", "Bb1", "Open HiHat", (Control.LEVEL, Control.PAN, Control.DECAY,), group=1)
    , Instrument("mt", "B1",  "MidTom", (Control.LEVEL, Control.PAN, Control.TUNING,))
    , Instrument("ht", "C2",  "HiTom", (Control.LEVEL, Control.PAN, Control.TUNING,))
#   , Instrument("ht", "D2",  "+HiTom", (Control.LEVEL, Control.PAN, Control.TUNING,))
    , Instrument("cy", "Eb2", "Cymbal", (Control.LEVEL, Control.PAN, Control.TONE, Control.DECAY,))
    , Instrument("cb", "Ab2", "CowBell", (Control.LEVEL, Control.PAN, ))
#   , Instrument("cy", "B2",  "+cymbal", (Control.LEVEL, Control.PAN, Control.TONE, Control.DECAY,))

    , Instrument("lc", "D3",  "LowConga", (Control.LEVEL, Control.PAN, Control.TUNING,))
    , Instrument("mc", "Eb3", "MidConga", (Control.LEVEL, Control.PAN, Control.TUNING,))
    , Instrument("hc", "E3",  "HiConga", (Control.LEVEL, Control.PAN, Control.TUNING,))
    , Instrument("ma", "Bb3", "Maracas", (Control.LEVEL, Control.PAN, ))
    , Instrument("cl", "Eb4", "Clave", (Control.LEVEL, Control.PAN, ))
)

def generate():
    filename = "TR808"

    # Generate SFZ file
    res = header
    res += header_no_xfades
    res += "\n# Instrument note assignments (close to GM drum mapping)\n"
    for inst in instruments:
        inst.render_comments()
    res += "\n<control>\n"
    for inst in instruments:
        res += inst.render_control_labels()
    res += "\n<master> sw_lokey=Bb0 sw_hikey=Bb0 sw_default=Bb0\n"
    for inst in instruments:
        res += inst.render_sfz(keyswitch=False)
    with open(filename + ".sfz", 'w') as fd:
        fd.write(res)
    #print(res)

    # Generate Zynthian Yaml file
    res = header_zynthian_yaml
    for inst in instruments:
        res += inst.render_zynthian_yaml(ticks=True)
    with open(filename + ".yml", 'w') as fd:
        fd.write(res)
    #print(res)

def generate_xfades():
    filename = "TR808_xfades"

    # Generate SFZ file
    res = header
    res += header_keyswitches
    res += "\n# Instrument note assignments (close to GM drum mapping)\n"
    for inst in instruments:
        inst.render_comments()
    res += "\n<control>\n"
    for inst in instruments:
        res += inst.render_control_labels()
    res += "\n<master> sw_lokey=A0 sw_hikey=Bb0 sw_default=A0\n"
    for inst in instruments:
        res += inst.render_sfz(keyswitch=True)
    for inst in instruments:
        res += inst.render_sfz(keyswitch=False)
    with open(filename + ".sfz", 'w') as fd:
        fd.write(res)
    #print(res)

    # Generate Zynthian Yaml file
    res = header_zynthian_yaml_keyswitches
    for inst in instruments:
        res += inst.render_zynthian_yaml(ticks=False)
    with open(filename + ".yml", 'w') as fd:
        fd.write(res)
    #print(res)


generate()
generate_xfades()
