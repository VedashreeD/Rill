"""
The 6 synthetic stream-condition classes, as a plain constant with zero
dependencies (not even torch). Deliberately kept separate so status
checks (ml/status.py) and the startup warning can report which classes
*would* be classified once trained, without importing torch just to
answer that question.

Single source of truth — training/dataset.py and everything else that
needs this list imports it from here.
"""

CLASSES = ["clear", "murky", "flooded", "whitewater", "algae", "debris"]
