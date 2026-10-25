"""Give installed manual pages distinct names without forking upstream manuals."""

from pathlib import Path
import re
import sys


commands = {"mc": "emcx", "mcedit": "emcx-edit", "mcview": "emcx-view", "mcdiff": "emcx-diff"}
command_pattern = re.compile(r"(?<![\w./-])(mcedit|mcview|mcdiff|mc)(?![\w.-])")
for output in sys.argv[1:]:
    man = Path(output) / "share/man"
    if not man.exists():
        continue
    for path in list(man.rglob("*.1")):
        name = path.name[:-2]
        if name not in commands:
            continue
        text = path.read_text()
        for old, new in commands.items():
            text = text.replace(old + ".1", new + ".1")
        text = command_pattern.sub(lambda match: commands[match.group()], text)
        for variable in ("MC_TMPDIR", "MC_SID", "MC_SKIN", "MC_KEYMAP"):
            text = text.replace(variable, "EMCX_" + variable[3:])
        for directory in ("/etc/mc", "/share/mc", "/libexec/mc", "/.config/mc", "/.cache/mc"):
            text = text.replace(directory, directory[:-2] + "emcx")
        target = path.with_name(commands[name] + ".1")
        target.write_text(text)
        path.unlink()
