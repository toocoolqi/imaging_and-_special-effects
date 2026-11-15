"""Generate short original encounter cues using our existing standard-library synth.

Run: python -m tools.make_encounter_sounds. Does not change music or food cues.
"""
from tools.make_sounds import at, bell, mix, noise, note, save


def build():
    cues = {
        "ghost_warning": mix(note(650, .7, "sine", .4, attack=.1, sweep_to=240),
                             at(.12, note(680, .6, "triangle", .2, sweep_to=270))),
        "ghost_steal": note(700, .28, "triangle", .45, decay=.12, sweep_to=150),
        "ghost_recover": mix(bell(660, .45, .4), at(.1, bell(990, .5, .3))),
        "blocker_warning": mix(bell(220, .4, .3), at(.26, bell(220, .4, .3))),
        "blocker_arrive": mix(note(110, .18, "sine", .6, decay=.07, sweep_to=45),
                              noise(.1, .2, decay=.04, smooth=.7)),
        "vampire_warning": mix(note(440, .3, "triangle", .35, sweep_to=620),
                               at(.35, note(440, .3, "triangle", .35, sweep_to=620))),
        "vampire_sweep": mix(noise(.4, .4, smooth=.88), note(180, .3, "sine", .2, sweep_to=80)),
        "vampire_bite": mix(note(240, .15, "square", .16, sweep_to=90),
                            at(.12, bell(950, .6, .3))),
        "shift_fail": mix(note(440, .24, "triangle", .35),
                          at(.22, note(330, .24, "triangle", .35)),
                          at(.44, note(220, .65, "triangle", .35, decay=.4))),
    }
    return {name: save(name, samples) for name, samples in cues.items()}


if __name__ == "__main__":
    for name, seconds in build().items():
        print(name, seconds)
