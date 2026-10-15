"""Close native interaction LOS gaps only while playing a large Location.

Only UnitPlayer.actions and UnitPlayer.crackAction change. No added host
methods/fields, Interact changes, inventory changes, or telemaster nerfs.
The initial E gate remains native; the same exception rule is reused below.
"""
import re


def _replace(source, old, new):
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Interaction anchor expected once, got {count}: {old[:120]}")
    return source.replace(old, new)


def _method(source, name, change):
    matches = list(re.finditer(r"\bfunction " + re.escape(name) + r"\(", source))
    if len(matches) != 1:
        raise RuntimeError(f"Interaction method {name} expected once, got {len(matches)}")
    start = matches[0].start()
    after = re.search(r"\n      (?:override )?(?:public|private|internal|protected) function ", source[start + 1:])
    end = start + 1 + after.start() if after else source.rfind("   }")
    return source[:start] + change(source[start:end]) + source[end:]


def apply_unit_player(source):
    large = "(loc.spaceX > World.cellsX || loc.spaceY > World.cellsY)"
    # Use the owner geometry, exactly as the initial E gate does. Interact.X/Y
    # are not the box's visual centre. Passing owner also preserves the native
    # exception that a closed door itself does not block interaction with it.
    owner = "this.actionObj.owner"
    need_los = (
        f"(this.pers.telemaster == 0 || !loc.portOn || {owner} is Loot || "
        'this.actionObj.allact == "comein")'
    )
    blocked = (
        f"!loc.isLine(X,Y - scY * 0.75,{owner}.X,"
        f"{owner}.Y - {owner}.scY / 2,{owner})"
    )
    source = _method(source, "actions", lambda body: _replace(
        body,
        "if(this.actionObj.active == 0)",
        "if(this.actionObj.active == 0 || (" + large + " && (" + owner +
        " == null || " + owner + ".loc != loc || (" + need_los + " && " + blocked + "))))",
    ))
    anchor = (
        "         if(Boolean(this.actionReady && loc.celObj) && Boolean(loc.celObj.onCursor) && loc.celDist <= World.w.actionDist)\n"
        "         {\n"
        "            if(Boolean(loc.celObj.inter) && Boolean(loc.celObj.inter.needRuna(this)))"
    )
    guard = (
        "            if(" + large + " &&\n"
        '               (this.pers.telemaster == 0 || !loc.portOn || loc.celObj is Loot || (loc.celObj.inter && loc.celObj.inter.allact == "comein")) &&\n'
        "               !loc.isLine(X,Y - scY * 0.75,loc.celObj.X,loc.celObj.Y - loc.celObj.scY / 2,loc.celObj))\n"
        "            {\n"
        '               World.w.gui.infoText("noVisible",null,null,false);\n'
        "               return;\n"
        "            }\n"
    )
    return _method(source, "crackAction", lambda body: _replace(
        body, anchor,
        anchor.replace("            if(Boolean(loc.celObj.inter)", guard + "            if(Boolean(loc.celObj.inter)"),
    ))
