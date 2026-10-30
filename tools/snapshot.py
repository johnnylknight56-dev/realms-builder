#!/usr/bin/env python3
"""Rebuild data.js, sheets.js and img/ from The Remembered Realms on Kanka.

Runs in GitHub Actions (see .github/workflows/kanka-sync.yml), or locally:

    KANKA_TOKEN=... python3 tools/snapshot.py

Settings live in builder-config.json and hand-written blurbs in blurbs.json.
Files are only rewritten when their content actually changes, so a run with
nothing new in Kanka leaves the repository untouched.
"""
import datetime
import html
import io
import json
import os
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.kanka.io/1.0/campaigns/{}/"
IMG_SIZE = 360


def path(*p):
    return os.path.join(ROOT, *p)


def load_json(name):
    with open(path(name), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- Kanka API

def kanka_get(url, token):
    for attempt in range(5):
        req = urllib.request.Request(url, headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "User-Agent": "realms-builder-snapshot",
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                time.sleep(15 * (attempt + 1))
                continue
            if e.code == 401:
                sys.exit("Kanka rejected the token (401). Make a new token and update the KANKA_TOKEN secret.")
            raise
    sys.exit("Kanka kept refusing requests: " + url)


def fetch_all(base, kind, token):
    rows, page = [], 1
    while True:
        d = kanka_get("{}{}?related=1&page={}".format(base, kind, page), token)
        rows += d["data"]
        if page >= d["meta"]["last_page"]:
            return rows
        page += 1


# ---------------------------------------------------------------- HTML cleanup

KEEP = {"h1", "h2", "h3", "h4", "h5", "h6", "div", "p", "b", "strong", "i", "em", "u",
        "a", "br", "ul", "ol", "li", "table", "thead", "tbody", "tr", "td", "th"}
VOID = {"br"}
DROP_WITH_CONTENT = {"script", "style", "iframe", "img", "svg", "button"}


class Cleaner(HTMLParser):
    """Keep simple formatting and links; drop Kanka's colors, fonts, ids and tooltips."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip, self.stack = [], 0, []

    def handle_starttag(self, tag, attrs):
        if tag in DROP_WITH_CONTENT:
            if tag != "img":
                self.skip += 1
            return
        if self.skip or tag in VOID:
            if not self.skip and tag in VOID and tag in KEEP:
                self.out.append("<{}>".format(tag))
            return
        a = dict(attrs)
        style = (a.get("style") or "").replace(" ", "").lower()
        opened = []
        if tag in KEEP:
            extra = ""
            if tag == "a" and a.get("href"):
                extra = ' href="{}"'.format(html.escape(a["href"], quote=True))
            elif tag == "div" and ("indent" in (a.get("class") or "").split() or "margin-left:" in style):
                extra = ' class="indent"'
            self.out.append("<{}{}>".format(tag, extra))
            opened.append(tag)
        # Kanka's editor sometimes writes bold/italic as inline styles
        if re.search(r"font-weight:(bold|bolder|[6-9]00)", style) and tag not in ("b", "strong", "h1", "h2", "h3", "h4", "h5", "h6", "th"):
            self.out.append("<b>")
            opened.append("b")
        if "font-style:italic" in style and tag not in ("i", "em"):
            self.out.append("<i>")
            opened.append("i")
        self.stack.append((tag, opened))

    def handle_startendtag(self, tag, attrs):
        if not self.skip and tag in VOID and tag in KEEP:
            self.out.append("<{}>".format(tag))

    def handle_endtag(self, tag):
        if tag in DROP_WITH_CONTENT:
            if tag != "img":
                self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag in VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                # close anything left open inside it, then the tag itself
                for _, opened in reversed(self.stack[i:]):
                    self.out.extend("</{}>".format(t) for t in reversed(opened))
                del self.stack[i:]
                return

    def close(self):
        super().close()
        for _, opened in reversed(self.stack):
            self.out.extend("</{}>".format(t) for t in reversed(opened))
        self.stack = []

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(re.sub(r"\s+", " ", data.replace("\xa0", " ")), quote=False))


def clean_html(h):
    c = Cleaner()
    c.feed(h or "")
    c.close()
    out = "".join(c.out)
    # drop empty paragraphs and blank lines Kanka's editor leaves behind
    prev = None
    while prev != out:
        prev = out
        out = re.sub(r"<(p|div|b|i|strong|em|u)>(\s|<br>)*</\1>", "", out)
        out = re.sub(r"<(p|div)( class=\"indent\")?>(\s|<br>)+", r"<\1\2>", out)
        out = re.sub(r"(<div>)\s+(<)", r"\1\2", out)
    return out.strip()


def plain_text(h):
    """Text of an entry without its headings, for starter blurbs."""
    h = re.sub(r"<h[1-6][^>]*>.*?</h[1-6]>", " ", h or "", flags=re.S)
    t = re.sub(r"<[^>]+>", " ", h)
    t = html.unescape(t).replace("\xa0", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return re.sub(r"\s+([,.;:!?)])", r"\1", t)


def first_sentence(h):
    t = plain_text(h)
    m = re.match(r"(.{20,}?[.!?])(\s|$)", t)
    s = m.group(1) if m else t[:200]
    return s.strip()


# ---------------------------------------------------------------- images

def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class Images:
    """Square 360px JPEG copies of Kanka art, re-downloaded only when the art changes."""

    def __init__(self):
        self.manifest_path = path("img", "manifest.json")
        try:
            with open(self.manifest_path, encoding="utf-8") as f:
                self.manifest = json.load(f)
        except FileNotFoundError:
            self.manifest = {}
        self.used = set()
        self.changed = []

    def get(self, prefix, entry):
        if not entry.get("has_custom_image") or not entry.get("image_full"):
            return None
        fn = "{}-{}.jpg".format(prefix, slug(entry["name"]))
        self.used.add(fn)
        key = entry.get("image_uuid") or entry["image_full"]
        full = path("img", fn)
        if self.manifest.get(fn) != key or not os.path.exists(full):
            req = urllib.request.Request(entry["image_full"], headers={"User-Agent": "realms-builder-snapshot"})
            with urllib.request.urlopen(req, timeout=120) as r:
                im = Image.open(io.BytesIO(r.read()))
            im = im.convert("RGBA")
            bg = Image.new("RGBA", im.size, (20, 18, 28, 255))
            im = Image.alpha_composite(bg, im).convert("RGB")
            w, h = im.size
            side = min(w, h)
            fx = entry.get("focus_x")
            fy = entry.get("focus_y")
            cx = fx if isinstance(fx, (int, float)) and fx else w // 2
            cy = fy if isinstance(fy, (int, float)) and fy else h // 2
            left = min(max(0, int(cx - side / 2)), w - side)
            top = min(max(0, int(cy - side / 2)), h - side)
            im = im.crop((left, top, left + side, top + side)).resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
            im.save(full, "JPEG", quality=85, optimize=True)
            self.manifest[fn] = key
            self.changed.append(fn)
        return "img/" + fn

    def finish(self):
        removed = []
        for fn in sorted(os.listdir(path("img"))):
            if fn.endswith(".jpg") and fn not in self.used:
                os.remove(path("img", fn))
                self.manifest.pop(fn, None)
                removed.append(fn)
        self.manifest = {k: self.manifest[k] for k in sorted(self.manifest) if k in self.used}
        write_if_changed(self.manifest_path, json.dumps(self.manifest, indent=1, ensure_ascii=False) + "\n")
        return removed


# ---------------------------------------------------------------- output

def write_if_changed(full, text):
    try:
        with open(full, encoding="utf-8") as f:
            if f.read() == text:
                return False
    except FileNotFoundError:
        pass
    with open(full, "w", encoding="utf-8") as f:
        f.write(text)
    return True


def without_date(text):
    return re.sub(r"taken \d{4}-\d{2}-\d{2}|\"snapshot\": \"[^\"]*\"", "", text)


def write_data_js(realms):
    full = path("data.js")
    today = datetime.date.today().isoformat()

    def render(date):
        realms["snapshot"] = date
        head = ("/* Snapshot of The Remembered Realms on Kanka, taken {}. Built automatically by "
                "tools/snapshot.py: edit blurbs.json or builder-config.json, not this file. */\n").format(date)
        return head + "window.REALMS = " + json.dumps(realms, indent=1, ensure_ascii=False) + ";\n"

    try:
        with open(full, encoding="utf-8") as f:
            old = f.read()
    except FileNotFoundError:
        old = ""
    new = render(today)
    if without_date(old) == without_date(new):
        return False
    with open(full, "w", encoding="utf-8") as f:
        f.write(new)
    return True


# ---------------------------------------------------------------- build

def main():
    token = os.environ.get("KANKA_TOKEN", "").strip()
    if not token:
        sys.exit("Set KANKA_TOKEN (in GitHub: Settings > Secrets and variables > Actions).")
    cfg = load_json("builder-config.json")
    blurbs = load_json("blurbs.json")
    base = API.format(cfg["campaign_id"])

    races = [r for r in fetch_all(base, "races", token) if not r.get("is_private")]
    abilities = [a for a in fetch_all(base, "abilities", token) if not a.get("is_private")]
    characters = [c for c in fetch_all(base, "characters", token) if not c.get("is_private")]
    tag_ids = {t["name"].lower(): t["id"] for t in fetch_all(base, "tags", token)}

    race_by_entity = {r["entity_id"]: r for r in races}
    race_by_id = {r["id"]: r for r in races}
    ability_by_id = {a["id"]: a for a in abilities}
    images = Images()
    report = []

    def blurb(section, entry):
        key = str(entry["entity_id"])
        sec = blurbs.setdefault(section, {})
        if key not in sec:
            starter = first_sentence(entry.get("entry_parsed") or entry.get("entry"))
            if not starter:
                report.append("Needs a blurb (its Kanka entry has no text yet): " + entry["name"])
                return ""
            sec[key] = {"name": entry["name"], "blurb": starter}
            report.append("New {} blurb, starter text from Kanka: {}".format(section, entry["name"]))
        sec[key]["name"] = entry["name"]
        return sec[key]["blurb"]

    # ---- species
    fam_ids = [f["id"] for f in cfg["families"]]
    through = {g["id"] for g in cfg.get("group_through", [])}
    together = {g["id"]: g.get("order") or [] for g in cfg.get("group_through", []) if g.get("keep_together")}
    moves = {m["id"]: m["to_family"] for m in cfg.get("move_species", [])}
    skip = {s["id"] for s in cfg.get("skip_species", [])}
    skip_tag = tag_ids.get((cfg.get("skip_tag") or "").lower())
    members = {f: [] for f in fam_ids}
    for r in races:
        p = r.get("parents") or []
        e = r["entity_id"]
        if not p or e in through or e in skip or e in fam_ids or (skip_tag and skip_tag in r["tags"]):
            continue
        fam, sort_name, order = None, r["name"], 0
        if p[0] in fam_ids:
            fam = p[0]
        elif p[0] in through and len(p) > 1 and p[1] in fam_ids:
            fam = p[1]
            group = race_by_entity.get(p[0])
            if group and p[0] in together:
                sort_name = group["name"]
                kids = together[p[0]] or [race_by_id[k]["entity_id"] for k in group.get("children") or [] if k in race_by_id]
                order = kids.index(e) if e in kids else len(kids)
        if e in moves:
            fam = moves[e]
        if fam is None:
            continue
        members[fam].append((sort_name.lower(), order, r["name"].lower(), r))

    sheets = {}
    families = []
    for f in cfg["families"]:
        out = []
        for _, _, _, r in sorted(members[f["id"]], key=lambda x: x[:3]):
            sp = {"name": r["name"], "id": r["entity_id"], "img": images.get("sp", r),
                  "kanka_img": r["image_full"] if r.get("has_custom_image") else None,
                  "blurb": blurb("species", r)}
            stats = [ability_by_id[x["ability_id"]] for x in r.get("entity_abilities") or []
                     if x.get("ability_id") in ability_by_id and ability_by_id[x["ability_id"]].get("type") == "Species Stats"]
            sheet = None
            sp["stats"] = sp["stats_entity"] = None
            if stats:
                sp["stats"] = stats[0]["name"]
                sp["stats_entity"] = stats[0]["entity_id"]
                sheet = stats[0].get("entry_parsed")
            else:
                post = next((p for p in r.get("posts") or [] if p["name"].strip().lower() == "in-game stats"
                             and p.get("visibility_id", 1) == 1), None)
                if post:
                    sheet = post.get("entry_parsed") or post.get("entry")
                    if sheet and "[" in sheet and "entry_parsed" not in post:
                        sheet = re.sub(r"\[[a-z_]+:\d+\|([^\]]+)\]", r"\1", sheet)
                        sheet = re.sub(r"\[[a-z_]+:\d+\]", "", sheet)
            if sheet and clean_html(sheet):
                sheets[str(r["entity_id"])] = clean_html(sheet)
            else:
                report.append("No statblock yet: " + r["name"])
            out.append(sp)
        families.append({"name": f["name"], "id": f["id"], "species": out})

    # ---- classes, subclasses, backgrounds (abilities tagged Class / Subclass / Background)
    def tagged(name):
        t = tag_ids.get(name)
        return [a for a in abilities if t in (a.get("tags") or [])]

    def by_name(rows):
        return sorted(rows, key=lambda a: a["name"].lower())

    subs = tagged("subclass")
    classes = []
    for c in by_name(tagged("class")):
        kids = [s for s in subs if (s.get("parents") or [None])[0] == c["entity_id"]]
        classes.append({"name": c["name"], "id": c["entity_id"], "img": images.get("cls", c),
                        "subclasses": [{"name": s["name"], "id": s["entity_id"], "img": images.get("sub", s)}
                                       for s in by_name(kids)]})
    backgrounds = [{"name": b["name"], "id": b["entity_id"], "img": images.get("bg", b), "blurb": blurb("backgrounds", b)}
                   for b in by_name(tagged("background"))]

    # ---- deities (characters whose type is one of deity_types, or starts with "Deity, ...")
    def is_deity(t):
        t = (t or "").strip()
        return any(t == d or t.startswith(d + ",") for d in cfg["deity_types"])

    deities = [{"name": c["name"], "id": c["entity_id"], "type": c["type"], "blurb": blurb("deities", c)}
               for c in by_name([c for c in characters if is_deity(c.get("type"))])]

    realms = {"snapshot": "", "wiki": cfg["wiki"], "families": families, "classes": classes,
              "backgrounds": backgrounds, "deities": deities}

    changed = []
    removed = images.finish()
    if write_data_js(realms):
        changed.append("data.js")
    sheets_js = ("/* Species statblocks from The Remembered Realms on Kanka (sanitized). Keyed by species entity id. */\n"
                 "window.REALMS_SHEETS = " + json.dumps(dict(sorted(sheets.items())), ensure_ascii=False) + ";\n")
    if write_if_changed(path("sheets.js"), sheets_js):
        changed.append("sheets.js")
    if write_if_changed(path("blurbs.json"), json.dumps(blurbs, indent=2, ensure_ascii=False) + "\n"):
        changed.append("blurbs.json")

    n_species = sum(len(f["species"]) for f in families)
    print("Species: {}  Classes: {}  Subclasses: {}  Backgrounds: {}  Deities: {}  Statblocks: {}".format(
        n_species, len(classes), sum(len(c["subclasses"]) for c in classes), len(backgrounds), len(deities), len(sheets)))
    for line in report:
        print("  " + line)
    print("Changed files: " + (", ".join(changed + ["img/" + x for x in images.changed]) or "none"))
    if removed:
        print("Removed images: " + ", ".join(removed))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### Kanka snapshot\n\n{} species, {} classes, {} backgrounds, {} deities, {} statblocks.\n\n".format(
                n_species, len(classes), len(backgrounds), len(deities), len(sheets)))
            for line in report:
                f.write("- {}\n".format(line))


if __name__ == "__main__":
    main()
