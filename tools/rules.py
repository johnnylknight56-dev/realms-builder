"""Read the mechanics out of Kanka statblocks for the level 20 sheet.

Every parser here is forgiving on purpose: it reads what it can recognise and
ignores the rest, so a statblock written a little differently still mostly works.
The format is described in the project doc "Kanka format for the character builder".
"""
import html
import re

SKILLS = ["Acrobatics", "Animal Handling", "Arcana", "Athletics", "Deception", "History",
          "Insight", "Intimidation", "Investigation", "Medicine", "Nature", "Perception",
          "Performance", "Persuasion", "Religion", "Sleight of Hand", "Stealth", "Survival"]
ABILITIES = {"strength": "str", "dexterity": "dex", "constitution": "con",
             "intelligence": "int", "wisdom": "wis", "charisma": "cha",
             "str": "str", "dex": "dex", "con": "con", "int": "int", "wis": "wis", "cha": "cha"}
SIZES = ["Tiny", "Small", "Medium", "Large", "Huge", "Gargantuan"]
NUMBERS = {"one": 1, "two": 2, "three": 3, "four": 4, "a": 1, "an": 1}

# Settings lines: "Label: value". Several spellings map to one key.
LABELS = {
    "hit die": "hit_die", "hit point die": "hit_die", "hit dice": "hit_die",
    "primary ability": "primary",
    "saving throws": "saves", "saving throw proficiencies": "saves", "saves": "saves",
    "skill choices": "skill_choices",
    "skills": "skills", "skill proficiencies": "skills", "skill proficiency": "skills",
    "armor": "armor", "armor training": "armor", "armor proficiencies": "armor",
    "weapons": "weapons", "weapon proficiencies": "weapons",
    "tools": "tools", "tool proficiencies": "tools", "tool proficiency": "tools",
    "languages": "languages",
    "at level 20": "level20",
    "score increases": "score_increase", "score increase": "score_increase",
    "ability scores": "ability_scores",
    "feat": "feat",
    "equipment": "equipment",
}
LABEL_RE = re.compile(r"^(" + "|".join(sorted(map(re.escape, LABELS), key=len, reverse=True)) + r")\s*:\s*(.*)$", re.I)
FEATURE_RE = re.compile(r"^level\s+(\d{1,2})\s*(?:—|–|-|:)+\s*(.+)$", re.I)
USES_RE = re.compile(r"^uses\s*:\s*(.+?)\s*(?:per|/|,|times per|each)\s*(.*)$", re.I)
CHOOSE_RE = re.compile(r"^choose\s*:\s*(\d+|one|two|three)\s+skills?(?:\s+(?:from|of)\s+(.*))?$", re.I)
SKIP_FEATURE = re.compile(r"^(ability score improvements?|feat\s*/\s*asi|asi|epic boon|.*\bsubclass( feature)?)$", re.I)


# ---------------------------------------------------------------- text helpers

def lines_of(h):
    """Turn statblock HTML into a list of plain text lines."""
    if not h:
        return []
    h = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", h)
    # a bold "Label:" starts a new line even if the editor didn't break the line
    h = re.sub(r"(?i)<(b|strong)\b[^>]*>", "\n", h)
    h = re.sub(r"(?i)<br\s*/?>", "\n", h)
    h = re.sub(r"(?i)</?(div|p|h[1-6]|li|ul|ol|dl|dt|dd|tr|table|thead|tbody|section)\b[^>]*>", "\n", h)
    h = re.sub(r"(?i)</t[dh]>", " | ", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = html.unescape(h).replace("\xa0", " ")
    out = []
    for ln in h.split("\n"):
        ln = re.sub(r"\s+", " ", ln).strip()
        ln = re.sub(r"\s+([.,;:!?)])", r"\1", ln)
        if ln:
            out.append(ln)
    # a bold label that ended up alone on its line ("Feat:" / "Tough") joins the next line
    merged = []
    for ln in out:
        if merged and re.fullmatch(r"[A-Za-z][A-Za-z /'-]{0,40}:", merged[-1]):
            merged[-1] = merged[-1] + " " + ln
        else:
            merged.append(ln)
    return merged


def first_sentence(t, limit=150):
    t = (t or "").strip()
    w = re.match(r"^\((.*)\)\.?$", t, re.S)
    if w:
        t = w.group(1).strip()
    if len(t) <= limit and "\n" not in t:
        return t
    t = t.split("\n")[0]
    m = re.match(r"(.+?[.!?])(\s|$)", t)
    s = m.group(1) if m else t
    if len(s) > limit:
        s = s[:limit - 1].rsplit(" ", 1)[0] + "…"
    return s


def split_list(v):
    v = re.sub(r"\s*\(.*?\)", "", v or "")
    parts = re.split(r",\s*(?:and|or)?\s*|\s+and\s+|\s+or\s+|;\s*", v)
    return [p.strip(" .") for p in parts if p.strip(" .") and p.strip(" .").lower() not in ("none", "-", "—")]


def skills_in(text):
    found = []
    for s in SKILLS:
        if re.search(r"\b" + re.escape(s) + r"\b", text, re.I):
            found.append(s)
    return found


def abilities_in(text):
    out = []
    for w in re.findall(r"[A-Za-z]+", text or ""):
        a = ABILITIES.get(w.lower())
        if a and a not in out:
            out.append(a)
    return out


def count_word(text, default=1):
    m = re.search(r"\b(\d+|one|two|three|four)\b", text or "", re.I)
    if not m:
        return default
    w = m.group(1).lower()
    return int(w) if w.isdigit() else NUMBERS[w]


# ---------------------------------------------------------------- classes, subclasses, backgrounds

def parse_post(h):
    """Split a class/subclass/background statblock into settings and features."""
    settings, features, loose = {}, [], []
    cur = None
    last = None
    for ln in lines_of(h):
        if last and not features and settings[last].rstrip().endswith((",", ";", "and", "or")) \
                and not LABEL_RE.match(ln) and not FEATURE_RE.match(ln):
            settings[last] = settings[last].rstrip() + " " + ln
            continue
        m = FEATURE_RE.match(ln)
        if m:
            rest = m.group(2).strip()
            nm = re.match(r"^([^.(]+?)\s*(?:\.\s*|(?=\())(.*)$", rest)
            name, text = (nm.group(1), nm.group(2)) if nm else (rest.rstrip("."), "")
            cur = {"lv": int(m.group(1)), "name": name.strip(), "text": text.strip()}
            features.append(cur)
            continue
        m = USES_RE.match(ln)
        if m and cur is not None:
            amt, rec = m.group(1).strip(), m.group(2)
            u = {"rec": "Short Rest" if re.search(r"short", rec, re.I) else ("Dawn" if re.search(r"dawn", rec, re.I) else "Long Rest")}
            if amt.isdigit():
                u["n"] = int(amt)
            elif re.search(r"proficiency", amt, re.I):
                u["pb"] = True
            elif abilities_in(amt) and re.search(r"mod", amt, re.I):
                u["mod"] = abilities_in(amt)[0]
            else:
                u["col"] = amt.strip()
            cur["uses"] = u
            continue
        m = CHOOSE_RE.match(ln)
        if m and cur is not None:
            frm = m.group(2) or ""
            cur["choose"] = {"n": count_word(m.group(1)),
                             "from": "class" if re.search(r"class", frm, re.I) else (skills_in(frm) or "any")}
            continue
        m = LABEL_RE.match(ln)
        if m and not features:
            last = LABELS[m.group(1).lower()]
            settings[last] = m.group(2).strip()
            continue
        last = None
        if cur is not None:
            cur["text"] = (cur["text"] + "\n" + ln).strip()
        else:
            loose.append(ln)
    out = []
    for f in features:
        if SKIP_FEATURE.match(f["name"]):
            continue
        f["text"] = f["text"].strip()
        f["summary"] = first_sentence(f["text"])
        out.append(f)
    return settings, out, loose


def common_profs(st, rules):
    if "skills" in st:
        rules["skills"] = skills_in(st["skills"])
    if "skill_choices" in st:
        v = st["skill_choices"]
        opts = skills_in(v) or list(SKILLS)
        rules["skill_choices"] = {"n": count_word(v, 1), "from": opts}
    if "armor" in st:
        rules["armor"] = [a.capitalize() for a in split_list(st["armor"])]
    if "weapons" in st:
        rules["weapons"] = [w.capitalize() for w in split_list(st["weapons"])]
    for k in ("tools", "languages"):
        if k in st and split_list(st[k]):
            rules[k] = st[k].strip().rstrip(".")


def parse_class(h):
    st, feats, _ = parse_post(h)
    r = {"features": feats}
    m = re.search(r"d\s*(\d+)", st.get("hit_die", ""))
    if m:
        r["hit_die"] = int(m.group(1))
    if "primary" in st:
        r["primary"] = st["primary"]
    if "saves" in st:
        r["saves"] = abilities_in(st["saves"])
    common_profs(st, r)
    if "level20" in st:
        pairs = []
        for part in re.split(r"[;·|]", st["level20"]):
            m = re.match(r"\s*(.+?)\s+([+-]?\d+\S*)\s*$", part)
            if m:
                pairs.append([m.group(1).strip(), m.group(2)])
        r["level20"] = pairs
    if "score_increase" in st:
        r["score_increase"] = parse_increase(st["score_increase"])
    else:
        found = feature_increase(feats)
        if found:
            r["score_increase"] = found
    for f in feats:
        if f["name"].lower() == "unarmored defense":
            ab = [a for a in abilities_in(f["text"]) if a != "dex"]
            r["unarmored"] = ab[:1] or ["con"]
    return r


def parse_increase(v):
    out = {}
    for m in re.finditer(r"(strength|dexterity|constitution|intelligence|wisdom|charisma|str|dex|con|int|wis|cha)\s*\+\s*(\d+)", v, re.I):
        out[ABILITIES[m.group(1).lower()]] = int(m.group(2))
    m = re.search(r"max(?:imum)?\D{0,8}(\d+)", v, re.I)
    if m:
        out["max"] = int(m.group(1))
    return out


def feature_increase(feats):
    """'STR & CON increase by 4 to max of 25' style capstones (Primal Champion, Body and Mind)."""
    for f in feats:
        t = f["text"]
        m = re.search(r"increase\w*\s+by\s+(\d+)", t, re.I)
        mx = re.search(r"max(?:imum)?\D{0,8}(\d+)", t, re.I)
        ab = abilities_in(t[:m.start()]) if m else []
        if m and mx and ab:
            out = {a: int(m.group(1)) for a in ab}
            out["max"] = int(mx.group(1))
            out["from"] = f["name"]
            out["lv"] = f["lv"]
            return out
    return None


def parse_subclass(h):
    st, feats, _ = parse_post(h)
    r = {"features": feats}
    common_profs(st, r)
    if "score_increase" in st:
        r["score_increase"] = parse_increase(st["score_increase"])
    return r


def parse_background(h):
    st, feats, loose = parse_post(h)
    r = {}
    r["abilities"] = abilities_in(st.get("ability_scores", ""))[:3]
    common_profs(st, r)
    feat = st.get("feat", "").strip().rstrip(".")
    if feat:
        feat = re.split(r"\s*[(\[]", feat)[0].strip()
        r["feat"] = feat
    equip = st.get("equipment", "")
    # The feat's description: a line starting "<Feat>." — possibly glued onto the end of another line.
    text_lines = list(loose)
    if feat:
        pat = re.compile(r"(?:^|(?<=[\s\d.;)]))" + re.escape(feat) + r"\.\s+(.+)$")
        m = pat.search(equip)
        if m:
            equip = equip[:m.start()].strip()
            text_lines.insert(0, feat + ". " + m.group(1))
        for i, ln in enumerate(text_lines):
            if ln.lower().startswith(feat.lower() + "."):
                r["feat_text"] = " ".join([ln[len(feat) + 1:].strip()] + text_lines[i + 1:]).strip()
                break
    if equip:
        r["equipment"] = equip.rstrip(";, ")
    if feats:
        r["features"] = feats
    return r


# ---------------------------------------------------------------- species

def parse_species(h):
    """Best-effort read of a free-form species statblock."""
    text = " ".join(lines_of(h))
    r = {}
    m = re.search(r"\bsize\b[^.]{0,80}", text, re.I)
    if m:
        sizes = [s for s in SIZES if re.search(r"\b" + s + r"\b", m.group(0))]
        if sizes:
            r["size"] = sizes
    m = re.search(r"\bspeed\b[^.]{0,60}?(\d{2,3})\s*(?:feet|ft)", text, re.I)
    r["speed"] = int(m.group(1)) if m else 30
    m = re.search(r"\bdarkvision\b[^.]{0,120}?(\d{2,3})\s*(?:feet|ft)", text, re.I)
    if m:
        r["darkvision"] = int(m.group(1))
    m = re.search(r"\bcreature type\b\W+(?:you are an? )?([A-Z][a-z]+)", text, re.I)
    if m:
        r["type"] = m.group(1).capitalize()

    # Trait names, read with tables removed (variant tables aren't the species' own traits).
    notables = re.sub(r"(?is)<table\b.*?</table>", " ", h)
    body = re.sub(r"(?is)<a\b[^>]*>.*?</a>", " ", notables)
    heads = [m.group(2) for m in re.finditer(r"(?is)<(h[3-6])\b[^>]*>(.*?)</\1>", body)]
    bolditalic = [m.group(3) for m in re.finditer(
        r"(?is)<(b|strong|i|em)\b[^>]*>\s*<(b|strong|i|em)\b[^>]*>(.*?)</\2>\s*</\1>", body)]
    leadbold = [m.group(2) for m in re.finditer(
        r"(?is)(?:<div[^>]*>|<p[^>]*>|<br\s*/?>)\s*<(b|strong)\b[^>]*>(.*?)</\1>\s*[.:]", body)]
    traits, seen = [], set()
    skipnames = {"creature type", "size", "speed", "languages", "ability score increase", "age", "alignment"}
    plain = " ".join(lines_of(notables))
    for group in (heads, bolditalic, leadbold):
        for n in group:
            n = html.unescape(re.sub(r"<[^>]+>", "", n)).strip().rstrip(".:").strip()
            low = n.lower()
            if (not n or low in skipnames or low.endswith("traits") or len(n) > 40 or low in seen
                    or not n[0].isupper()):
                continue
            seen.add(low)
            after = plain.split(n, 1)[1] if n in plain else ""
            traits.append({"name": n, "summary": first_sentence(after.lstrip(" .:"))})
        if traits:
            break
    r["traits"] = traits

    # Skill proficiencies. Fixed ones are suggestions the player can change in the builder.
    fixed, choices = [], []
    for sent in re.split(r"(?<=[.!?])\s+", " ".join(lines_of(notables))):
        if not re.search(r"proficien", sent, re.I):
            continue
        if re.search(r"long rest|short rest|until|already have|already proficient|expertise|bonus", sent, re.I):
            continue
        sk = skills_in(sent)
        if not sk and not re.search(r"\bskills?\b", sent, re.I):
            continue
        choice = (re.search(r"following|skills? of your choice|\b(one|two|three|\d)\s+(other\s+)?skills?\b", sent, re.I)
                  or (len(sk) > 1 and re.search(r"\b(" + "|".join(sk) + r")\b,?\s+or\s+", sent, re.I)))
        if choice:
            m = re.search(r"\b(one|two|three|\d)\b\s+(?:other\s+)?(?:of the following\s+)?skills?", sent, re.I)
            n = count_word(m.group(1)) if m else 1
            pre = re.search(r"proficiency in ([A-Za-z ]+?) as well as", sent, re.I)
            if pre:
                fixed += skills_in(pre.group(1))
                sk = [x for x in sk if x not in fixed]
            choices.append({"n": n, "from": sk if len(sk) > n else list(SKILLS)})
        elif sk:
            fixed += sk
    sp = {}
    if fixed:
        sp["skills"] = list(dict.fromkeys(fixed))
    if choices:
        sp["skill_choices"] = choices
    r.update(sp)
    return r


# ---------------------------------------------------------------- full feature text and class tables

HEAD_LEVEL = re.compile(r"^level\s+(\d{1,2})\s*(?:—|–|-|:)+\s*(.+?)\.?$", re.I)


def norm(name):
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def rich_lines(h):
    """HTML to lines, keeping headings (as ('h', level, text)), list bullets and table rows."""
    if not h:
        return []
    h = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", h)
    h = re.sub(r"(?is)<(h[1-6])\b[^>]*>(.*?)</\1>", lambda m: "\n\x01" + m.group(1)[1] + re.sub(r"<[^>]+>", " ", m.group(2)) + "\n", h)
    h = re.sub(r"(?i)<li\b[^>]*>", "\n• ", h)
    h = re.sub(r"(?i)<br\s*/?>", "\n", h)
    h = re.sub(r"(?i)</t[dh]>", " | ", h)
    h = re.sub(r"(?i)</?(div|p|ul|ol|dl|dt|dd|tr|table|thead|tbody|section|blockquote)\b[^>]*>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = html.unescape(h).replace("\xa0", " ")
    out = []
    for ln in h.split("\n"):
        head = ln.startswith("\x01")
        if head:
            lvl, ln = int(ln[1]), ln[2:]
        ln = re.sub(r"\s+", " ", ln).strip()
        ln = re.sub(r"\s+([.,;:!?)])", r"\1", ln).rstrip(" |").strip()
        if ln:
            out.append(("h", lvl, ln) if head else ("t", 0, ln))
    return out


def full_sections(h):
    """Every 'Level N: Name' heading in the HTML with the text under it, until the next heading at its level or above."""
    out, cur = [], None
    for kind, lvl, ln in rich_lines(h):
        if kind == "h":
            m = HEAD_LEVEL.match(ln)
            if m:
                cur = {"lv": int(m.group(1)), "name": m.group(2).strip(), "hl": lvl, "lines": []}
                out.append(cur)
                continue
            if cur and lvl <= cur["hl"]:
                cur = None
                continue
        if cur is not None:
            cur["lines"].append(ln)
    for s in out:
        s["text"] = "\n".join(s.pop("lines")).strip()
        s.pop("hl")
    return [s for s in out if s["text"]]


def attach_full_text(features, sources):
    """Give each feature its full text from the entry's posts, matched by level and name."""
    secs = []
    for h in sources:
        secs += full_sections(h)
    by_both = {(s["lv"], norm(s["name"])): s["text"] for s in secs}
    by_name = {}
    for s in secs:
        by_name.setdefault(norm(s["name"]), s["text"])
    for f in features:
        key = norm(f["name"])
        full = by_both.get((f["lv"], key)) or by_name.get(key)
        if not full and "," in f["name"]:
            parent = norm(f["name"].split(",")[0])
            if (f["lv"], parent) in by_both or parent in by_name:
                f["covered"] = True       # an option already described in its parent feature's text
        f["full"] = full or f["text"]
        detect_choice(f)
    return features


def detect_choice(f):
    """Features that grant a skill proficiency choice (e.g. Primal Knowledge)."""
    if f.get("choose"):
        return
    t = f.get("full") or f.get("text") or ""
    m = re.search(r"proficiency in (another|one|two|three|\d) (?:more |additional )?skills? of your choice"
                  r"(?: from the (?:skill )?list)?", t, re.I)
    if not m or re.search(r"long rest|until the end", t[max(0, m.start() - 80):m.end() + 80], re.I):
        return
    n = 1 if m.group(1).lower() == "another" else count_word(m.group(1))
    f["choose"] = {"n": n, "from": "class" if "list" in m.group(0).lower() else "any"}


def class_table(sources):
    """The class progression table: a table whose first column runs Level 1..20."""
    best = None
    for h in sources:
        for t in re.findall(r"(?is)<table\b.*?</table>", h or ""):
            rows = []
            for tr in re.findall(r"(?is)<tr\b.*?</tr>", t):
                cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                         for c in re.findall(r"(?is)<t[dh]\b[^>]*>(.*?)</t[dh]>", tr)]
                rows.append(cells)
            data = [r for r in rows if r and re.fullmatch(r"\d{1,2}(st|nd|rd|th)?", r[0])]
            if len(data) < 20:
                continue
            width = len(data[0])
            header = None
            for r in rows:
                if r in data:
                    break
                if len(r) == width:
                    header = r
            if not header:
                continue
            keep = [i for i, c in enumerate(header)
                    if i > 0 and not re.match(r"(?i)^(level|proficiency bonus|class features|features)$", c)]
            table = {"cols": [header[i] for i in keep],
                     "rows": {str(int(re.match(r"\d+", r[0]).group(0))): [r[i] if i < len(r) else "" for i in keep] for r in data}}
            if best is None:
                best = table
    return best


def link_uses(features, table):
    """'Uses: 6' on Rage becomes the Rages column when the class table has one, so it scales with level."""
    if not table:
        return
    cols = {c.lower(): c for c in table["cols"]}
    for f in features:
        u = f.get("uses")
        if not u or u.get("col"):
            continue
        n = f["name"].lower()
        for cand in (n, n + "s", n + "es", n + " uses"):
            if cand in cols:
                u["col"] = cols[cand]
                break
