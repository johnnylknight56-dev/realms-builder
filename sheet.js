/* Character sheet (levels 1–20): the numbers, and filling character-sheet-template.pdf.
   Runs in the player's browser (window.RealmsSheet) and in Node for testing (module.exports).
   Nothing leaves the browser: the template is fetched from this site, filled, and handed back as a download. */
(function (root) {
  'use strict';

  // Experience needed for each level (2024 rules).
  var XP = [0, 0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000, 85000, 100000, 120000, 140000, 165000,
    195000, 225000, 265000, 305000, 355000];
  function pbAt(level) { return Math.ceil(level / 4) + 1; }
  function levelOf(S) { var l = parseInt(S.level, 10); return l >= 1 && l <= 20 ? l : 20; }
  var AB = ['str', 'dex', 'con', 'int', 'wis', 'cha'];
  var AB_NAME = { str: 'Strength', dex: 'Dexterity', con: 'Constitution', int: 'Intelligence', wis: 'Wisdom', cha: 'Charisma' };
  var AB_FIELD = { str: 'Str', dex: 'Dex', con: 'Con', int: 'Int', wis: 'Wis', cha: 'Cha' };
  var SKILLS = [
    ['Acrobatics', 'dex', 'Acr'], ['Animal Handling', 'wis', 'Ani'], ['Arcana', 'int', 'Arc'], ['Athletics', 'str', 'Ath'],
    ['Deception', 'cha', 'Dec'], ['History', 'int', 'His'], ['Insight', 'wis', 'Ins'], ['Intimidation', 'cha', 'Inti'],
    ['Investigation', 'int', 'Inv'], ['Medicine', 'wis', 'Med'], ['Nature', 'int', 'Nat'], ['Perception', 'wis', 'Perc'],
    ['Performance', 'cha', 'Perf'], ['Persuasion', 'cha', 'Pers'], ['Religion', 'int', 'Rel'], ['Sleight of Hand', 'dex', 'Sle'],
    ['Stealth', 'dex', 'Ste'], ['Survival', 'wis', 'Sur']];
  var ARRAY = [15, 14, 13, 12, 10, 8];
  var BUY_COST = { 8: 0, 9: 1, 10: 2, 11: 3, 12: 4, 13: 5, 14: 7, 15: 9 };
  var BUY_POINTS = 27;

  // Ruled-line geometry of the big text boxes, measured from the template (points).
  // first: distance from the top of the box to its first rule; pitch: distance between rules; rules: how many.
  var BOXES = {
    'Class Features': { first: -0.34, pitch: 11.020, rules: 45 },
    'Racial Traits': { first: -0.43, pitch: 11.113, rules: 11 },
    'Background Feature Description': { first: 11.73, pitch: 11.000, rules: 6 },
    'Personality Trait': { first: -0.28, pitch: 11.281, rules: 5 },
    'Ideal': { first: -0.27, pitch: 11.375, rules: 4 },
    'Bond': { first: -0.34, pitch: 11.417, rules: 4 },
    'Flaw': { first: -0.28, pitch: 11.417, rules: 4 },
    'Feat Description 1': { first: 12.19, pitch: 11.344, rules: 5 },
    'Background_Enemies': { first: -0.49, pitch: 11.047, rules: 17 },
    'Background_Organisation.Left': { first: -0.48, pitch: 11.044, rules: 21 },
    'Background_History': { first: -0.43, pitch: 11.015, rules: 34 },
    'Background_Appearance': { first: -0.43, pitch: 11.068, rules: 12 },
    'P5.ASnotes.Notes.Left': { first: -0.34, pitch: 11.021, rules: 67 },
    'P5.ASnotes.Notes.Right': { first: -0.34, pitch: 11.021, rules: 67 },
    'Extra.Notes': { first: -0.41, pitch: 11.040, rules: 35 }
  };
  var BOX_FONT = 8;

  function mod(score) { return Math.floor((score - 10) / 2); }
  function signed(n) { return (n >= 0 ? '+' : '') + n; }
  function byId(list, id) { for (var i = 0; i < (list || []).length; i++) if (list[i].id === id) return list[i]; return null; }
  function uniq(a) { var o = []; a.forEach(function (x) { if (x && o.indexOf(x) < 0) o.push(x); }); return o; }

  // ---------------------------------------------------------------- choices

  /** Everything the player picked, resolved against data.js and rules.js. */
  function resolve(S, D, R) {
    var sp = null;
    (D.families || []).forEach(function (f) { f.species.forEach(function (s) { if (s.id === S.species) sp = s; }); });
    var c = byId(D.classes, S.cls), sub = c ? byId(c.subclasses, S.sub) : null, bg = byId(D.backgrounds, S.bg);
    function rule(kind, x) { return x && R[kind] ? R[kind][String(x.id)] || null : null; }
    var level = levelOf(S), subR = rule('subclasses', sub) || {};
    var subLevel = subclassLevel(c, R);
    return {
      sp: sp, cls: c, sub: sub, bg: bg, level: level, pb: pbAt(level), subLevel: subLevel,
      subActive: !!sub && level >= subLevel,
      spR: rule('species', sp) || {}, clsR: rule('classes', c) || {}, subR: subR, bgR: rule('backgrounds', bg) || {}
    };
  }
  /** The level a class's subclass starts at: the earliest subclass feature, else 3. */
  function subclassLevel(c, R) {
    var lv = 99;
    ((c && c.subclasses) || []).forEach(function (s) {
      var r = R.subclasses && R.subclasses[String(s.id)];
      ((r && r.features) || []).forEach(function (f) { if (f.lv < lv) lv = f.lv; });
    });
    return lv === 99 ? 3 : lv;
  }
  /** Class and (active) subclass features up to the character's level. */
  function featuresAt(X) {
    var out = [];
    function add(list, label) {
      (list || []).forEach(function (f) { if (f.lv <= X.level) out.push(Object.assign({ from: label }, f)); });
    }
    add(X.clsR.features, X.cls ? X.cls.name : '');
    if (X.subActive) add(X.subR.features, X.sub ? X.sub.name : '');
    out.sort(function (a, b) { return a.lv - b.lv; });
    return out;
  }
  /** Class table values at the character's level, e.g. [['Rages','3'], ['Rage Damage','+2']]. */
  function tableAt(X) {
    var t = X.clsR.table;
    if (t && t.rows[String(X.level)]) {
      return t.cols.map(function (c, i) { return [/^\d+$/.test(c) ? 'Level ' + c + ' slots' : c, t.rows[String(X.level)][i]]; })
        .filter(function (p) { return p[1] && !/^[—–-]$/.test(p[1]); });
    }
    return X.level === 20 ? (X.clsR.level20 || []) : [];
  }
  /** How many uses a limited feature has at this level. */
  function usesAt(u, X, mods) {
    if (!u) return null;
    if (u.col) {
      var t = X.clsR.table, i = t ? t.cols.indexOf(u.col) : -1;
      if (i >= 0) { var v = parseInt(t.rows[String(X.level)][i], 10); if (!isNaN(v)) return v; }
      if (X.level === 20) (X.clsR.level20 || []).forEach(function (p) { if (p[0].toLowerCase() === u.col.toLowerCase()) u = { n: parseInt(p[1], 10) }; });
    }
    if (u.pb) return X.pb;
    if (u.mod) return Math.max(1, mods[u.mod] || 0);
    return typeof u.n === 'number' ? u.n : null;
  }

  /** Skill groups the player chooses from, in display order. */
  function skillGroups(S, D, R) {
    var X = resolve(S, D, R), groups = [];
    if (X.bg && X.bgR.skills && X.bgR.skills.length)
      groups.push({ key: 'bg', label: X.bg.name + ' background', fixed: X.bgR.skills, n: 0, from: [] });
    if (X.cls && X.clsR.skill_choices)
      groups.push({ key: 'cls', label: X.cls.name, fixed: X.clsR.skills || [], n: X.clsR.skill_choices.n, from: X.clsR.skill_choices.from });
    else if (X.cls && X.clsR.skills)
      groups.push({ key: 'cls', label: X.cls.name, fixed: X.clsR.skills, n: 0, from: [] });
    if (X.subActive && (X.subR.skills || X.subR.skill_choices))
      groups.push({ key: 'sub', label: X.sub.name, fixed: X.subR.skills || [], n: X.subR.skill_choices ? X.subR.skill_choices.n : 0,
        from: X.subR.skill_choices ? X.subR.skill_choices.from : [] });
    // features that grant a skill choice once you reach their level (e.g. Primal Knowledge)
    featuresAt(X).forEach(function (f) {
      if (!f.choose) return;
      var from = f.choose.from === 'class' ? ((X.clsR.skill_choices && X.clsR.skill_choices.from) || SKILLS.map(function (s) { return s[0]; }))
        : (Array.isArray(f.choose.from) ? f.choose.from : SKILLS.map(function (s) { return s[0]; }));
      groups.push({ key: 'f:' + f.lv + ':' + f.name, label: f.name + ' (' + f.from + ' ' + f.lv + ')', fixed: [], n: f.choose.n, from: from });
    });
    // Species text varies a lot, so species skills are one editable group, pre-filled with what the statblock seems to say.
    var spFixed = X.spR.skills || [], spCh = X.spR.skill_choices || [];
    var spN = spFixed.length + spCh.reduce(function (t, c) { return t + c.n; }, 0);
    if (X.sp && spN) {
      var hint = spFixed.slice();
      spCh.forEach(function (c) {
        hint.push(c.from.length >= SKILLS.length ? (c.n === 1 ? 'one skill of your choice' : c.n + ' skills of your choice')
          : (c.n === 1 ? 'one of ' : c.n + ' of ') + c.from.join(', ').replace(/, ([^,]*)$/, ' or $1'));
      });
      groups.push({ key: 'sp', label: X.sp.name, fixed: [], n: spN, from: SKILLS.map(function (s) { return s[0]; }),
        suggested: spFixed, editable: true, hint: hint.join('; ') });
    }
    return groups;
  }

  /** The skills the player ends up proficient in, and which group each came from. */
  function proficientSkills(S, D, R) {
    var got = {};
    skillGroups(S, D, R).forEach(function (g) {
      g.fixed.forEach(function (s) { got[s] = got[s] || g.label; });
      var picks = (S.skills && S.skills[g.key]) || (g.suggested || []);
      picks.slice(0, g.n).forEach(function (s) { if (g.from.indexOf(s) >= 0) got[s] = got[s] || g.label; });
    });
    return got;
  }

  /** Base scores from standard array or point buy. */
  function baseScores(S) {
    var out = {};
    AB.forEach(function (a) {
      var v = S.method === 'buy' ? (S.buy && S.buy[a]) : (S.arr && S.arr[a]);
      out[a] = typeof v === 'number' ? v : (S.method === 'buy' ? 8 : null);
    });
    return out;
  }
  function pointsSpent(S) {
    var b = baseScores(S), t = 0;
    AB.forEach(function (a) { t += BUY_COST[b[a]] || 0; });
    return t;
  }

  /** Background bonus: +2/+1 or +1/+1/+1 among the background's three abilities. */
  function bgBonus(S, D, R) {
    var X = resolve(S, D, R), list = X.bgR.abilities || [], out = {};
    if (!list.length) return out;
    if (S.bgMode === '111') list.forEach(function (a) { out[a] = 1; });
    else {
      if (S.bgPlus2 && list.indexOf(S.bgPlus2) >= 0) out[S.bgPlus2] = 2;
      if (S.bgPlus1 && list.indexOf(S.bgPlus1) >= 0 && S.bgPlus1 !== S.bgPlus2) out[S.bgPlus1] = 1;
    }
    return out;
  }

  /** Final level 20 scores: base + background (max 20), then capstone increases like Primal Champion. */
  function finalScores(S, D, R) {
    var X = resolve(S, D, R), base = baseScores(S), bonus = bgBonus(S, D, R), out = {};
    var inc = X.clsR.score_increase || (X.subActive && X.subR.score_increase) || null;
    if (inc && (inc.lv || 20) > X.level) inc = null;
    AB.forEach(function (a) {
      if (base[a] == null) { out[a] = null; return; }
      var v = Math.min(20, base[a] + (bonus[a] || 0));
      if (inc && inc[a]) v = Math.min(inc.max || 30, v + inc[a]);
      out[a] = v;
    });
    return { scores: out, base: base, bonus: bonus, increase: inc };
  }

  // ---------------------------------------------------------------- the whole sheet

  function compute(S, D, R) {
    var X = resolve(S, D, R);
    var LEVEL = X.level, PB = X.pb;
    var F = finalScores(S, D, R), sc = F.scores, m = {};
    AB.forEach(function (a) { m[a] = sc[a] == null ? 0 : mod(sc[a]); });
    var profs = proficientSkills(S, D, R);
    var feats = featuresAt(X);
    feats.forEach(function (f) { f.usesN = usesAt(f.uses, X, m); });
    var saves = X.clsR.saves || [];
    var hd = X.clsR.hit_die || 8;
    var feat = X.bgR.feat || '', featText = X.bgR.feat_text || '';

    // Hit points: max die at level 1, then the fixed average (die/2 + 1) for 19 levels, plus Con each level.
    var hp = hd + m.con + (LEVEL - 1) * (hd / 2 + 1 + m.con);
    var hpNotes = [];
    if (/twice your (character )?level/i.test(featText) || /^tough$/i.test(feat)) { hp += 2 * LEVEL; hpNotes.push(feat + ' +' + 2 * LEVEL); }

    var unarmored = feats.some(function (f) { return /^unarmored defense$/i.test(f.name); }) ? (X.clsR.unarmored || X.subR.unarmored) : null;
    var ac = 10 + m.dex + (unarmored ? m[unarmored[0]] : 0);
    var init = m.dex + ((/^alert$/i.test(feat) || /proficiency bonus to (your )?initiative/i.test(featText)) ? PB : 0);
    var skillTotal = {};
    SKILLS.forEach(function (s) { skillTotal[s[0]] = m[s[1]] + (profs[s[0]] ? PB : 0); });


    // "+10 speed" / "speed increases by 10" features (Fast Movement, Unarmored Movement at level 20)
    var speedBonus = 0, speedFrom = '';
    feats.forEach(function (f) {
      var t = f.text || '', mm = t.match(/\+\s*(\d+)\s*(?:ft\.?|feet)?\s*(?:walking\s+)?speed\b/i) || t.match(/\bspeed increases by (\d+)/i);
      if (mm && +mm[1] > speedBonus) { speedBonus = +mm[1]; speedFrom = f.name; }
    });
    var size = S.size && (X.spR.size || []).indexOf(S.size) >= 0 ? S.size : ((X.spR.size || ['Medium']).indexOf('Medium') >= 0 ? 'Medium' : (X.spR.size || ['Medium'])[0]);
    return {
      X: X, level: LEVEL, pb: PB, xp: XP[LEVEL], table: tableAt(X), scores: sc, mods: m, base: F.base, bonus: F.bonus, increase: F.increase,
      saves: saves, profs: profs, skillTotal: skillTotal, hp: hp, hpNotes: hpNotes, hd: hd, ac: ac,
      acNote: unarmored ? 'Unarmored Defense (10 + DEX + ' + unarmored[0].toUpperCase() + ')' : 'No armor (10 + DEX)',
      init: init, passive: 10 + skillTotal.Perception, speed: (X.spR.speed || 30) + speedBonus, baseSpeed: X.spR.speed || 30,
      speedFrom: speedFrom, darkvision: X.spR.darkvision || 0,
      size: size, features: feats, feat: feat, featText: featText
    };
  }

  // ---------------------------------------------------------------- PDF

  // Characters the built-in Helvetica can't draw are swapped for close equivalents.
  var WIN_EXTRA = '€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ';
  var SWAP = { '≥': '>=', '≤': '<=', '→': '->', '←': '<-', '−': '-', '‑': '-', '′': "'", '″': '"', '✓': 'v', '◆': '•', '★': '*', '​': '' };
  function winAnsi(t) {
    t = String(t == null ? '' : t).replace(/\r\n?/g, '\n').replace(/\t/g, ' ');
    var out = '';
    for (var i = 0; i < t.length; i++) {
      var ch = t[i], c = ch.charCodeAt(0);
      if (ch === '\n' || (c >= 32 && c <= 126) || (c >= 160 && c <= 255) || WIN_EXTRA.indexOf(ch) >= 0) out += ch;
      else if (SWAP[ch] != null) out += SWAP[ch];
      else if (c >= 0xD800 && c <= 0xDBFF) { i++; out += '?'; }
      else if (c >= 32) out += '?';
    }
    return out;
  }

  function wrap(text, font, size, width) {
    var lines = [];
    winAnsi(text).split('\n').forEach(function (para) {
      if (!para.trim()) { lines.push(''); return; }
      var words = para.split(/ +/), line = '';
      words.forEach(function (w) {
        var trial = line ? line + ' ' + w : w;
        if (font.widthOfTextAtSize(trial, size) <= width || !line) {
          // a single word wider than the box gets broken by characters
          while (!line && font.widthOfTextAtSize(trial, size) > width && trial.length > 1) {
            var k = trial.length;
            while (k > 1 && font.widthOfTextAtSize(trial.slice(0, k), size) > width) k--;
            lines.push(trial.slice(0, k)); trial = trial.slice(k);
          }
          line = trial;
        } else { lines.push(line); line = w; }
      });
      lines.push(line);
    });
    return lines;
  }

  function oneLine(text, font, size, width) {
    var t = winAnsi(text).replace(/\s*\n\s*/g, ' ');
    if (font.widthOfTextAtSize(t, size) <= width) return t;
    while (t.length > 1 && font.widthOfTextAtSize(t + '…', size) > width) t = t.slice(0, -1);
    return t.replace(/\s+$/, '') + '…';
  }

  /** Capacity of a ruled box: usable line count and the text width. */
  function boxInfo(field, name) {
    var g = BOXES[name], w = field.acroField.getWidgets()[0], r = w.getRectangle();
    var skipTop = g.first < 3 ? 1 : 0;           // a rule on the top edge has no room above it
    return { lines: g.rules - skipTop, width: r.width - 6, rect: r, g: g, skipTop: skipTop };
  }

  async function build(PDFLib, templateBytes, S, D, R) {
    var C = compute(S, D, R), X = C.X;
    var doc = await PDFLib.PDFDocument.load(templateBytes);
    var form = doc.getForm();
    var font = await doc.embedFont(PDFLib.StandardFonts.Helvetica);
    var done = [];   // [field, linesOrNull]

    function get(name) { try { return form.getField(name); } catch (e) { return null; } }
    function text(name, v) {
      var f = get(name); if (!f || v == null || v === '') return;
      v = winAnsi(v);
      if (f instanceof PDFLib.PDFTextField) { f.setText(v); done.push([f, null]); }
      else if (f instanceof PDFLib.PDFDropdown) {
        if (f.getOptions().indexOf(v) < 0) { f.enableEditing(); f.addOptions([v]); }
        f.select(v); done.push([f, null]);
      }
    }
    function check(name, on) { var f = get(name); if (f && f instanceof PDFLib.PDFCheckBox && on) f.check(); }
    /** Fill a ruled box; returns lines that didn't fit. */
    function box(name, lines) {
      var f = get(name); if (!f || !lines.length) return lines;
      var info = boxInfo(f, name), fit = lines.slice(0, info.lines);
      while (fit.length && !fit[fit.length - 1]) fit.pop();
      f.setText(fit.join('\n'));
      done.push([f, { lines: fit, info: info }]);
      return lines.slice(info.lines);
    }
    function boxLines(name, items, opts) {
      var f = get(name); if (!f) return [];
      var info = boxInfo(f, name), out = [], maxEach = opts && opts.maxEach;
      items.forEach(function (it) {
        var w = wrap(it, font, BOX_FONT, info.width);
        if (maxEach && w.length > maxEach) {
          w = w.slice(0, maxEach);
          w[maxEach - 1] = oneLine(w[maxEach - 1] + ' …', font, BOX_FONT, info.width).replace(/ …$/, '…');
        }
        out = out.concat(w);
      });
      return out;
    }
    /** Wrap items to fit a box: full text if it fits, else at most 2 lines each, else 1 line each. */
    function fitted(name, head, items) {
      var f = get(name); if (!f) return [];
      var cap = boxInfo(f, name).lines, tries = [0, 3, 2, 1], out = [];
      for (var i = 0; i < tries.length; i++) {
        out = boxLines(name, head).concat(boxLines(name, items, tries[i] ? { maxEach: tries[i] } : null));
        if (out.length <= cap) break;
      }
      return out;
    }
    /** Lines that overflowed one box, joined back into text so they can be re-wrapped for another box. */
    function unwrap(lines) {
      var out = [], para = [];
      lines.forEach(function (l) { if (l) para.push(l); else { if (para.length) out.push(para.join(' ')); para = []; out.push(''); } });
      if (para.length) out.push(para.join(' '));
      return out.join('\n');
    }

    // ---- page 1: identity and numbers
    var c = X.cls, s2 = X.sub;
    text('PC Name', S.name || 'Unnamed adventurer');
    text('Player Name', S.player);
    var LEVEL = C.level, PB = C.pb;
    if (!X.subActive) s2 = null;
    text('Class and Levels', c ? c.name + (s2 ? ' (' + s2.name + ')' : '') : '');
    text('Character Level', String(LEVEL));
    text('Total Experience', C.xp.toLocaleString('en-US'));
    text('Race', X.sp ? X.sp.name : '');
    text('Background', X.bg ? X.bg.name : '');
    AB.forEach(function (a) {
      if (C.scores[a] == null) return;
      text(AB_FIELD[a], String(C.scores[a]));
      text(AB_FIELD[a] + ' Mod', signed(C.mods[a]));
      var prof = C.saves.indexOf(a) >= 0;
      text(AB_FIELD[a] + ' ST Mod', signed(C.mods[a] + (prof ? PB : 0)));
      check(AB_FIELD[a] + ' ST Prof', prof);
    });
    SKILLS.forEach(function (s) {
      text(s[2], signed(C.skillTotal[s[0]]));
      check(s[2] + ' Prof', !!C.profs[s[0]]);
    });
    text('Proficiency Bonus', signed(PB));
    text('HP Max', String(C.hp));
    text('HD1 Level', String(LEVEL));
    text('HD1 Die', 'd' + C.hd);
    text('AC', String(C.ac));
    text('Initiative bonus', signed(C.init));
    text('Speed', C.speed + ' ft');
    text('Passive Perception', String(C.passive));
    if (C.darkvision) text('Vision', 'Darkvision ' + C.darkvision + ' ft');

    var armor = (X.clsR.armor || []).concat(X.subR.armor || []).map(function (a) { return a.toLowerCase(); });
    check('Proficiency Armor Light', armor.some(function (a) { return /light/.test(a); }));
    check('Proficiency Armor Medium', armor.some(function (a) { return /medium/.test(a); }));
    check('Proficiency Armor Heavy', armor.some(function (a) { return /heavy/.test(a); }));
    check('Proficiency Shields', armor.some(function (a) { return /shield/.test(a); }));
    var weapons = (X.clsR.weapons || []).concat(X.subR.weapons || []);
    var other = weapons.filter(function (w) { return !/^(simple|martial)( weapons)?$/i.test(w); });
    check('Proficiency Weapon Simple', weapons.some(function (w) { return /^simple/i.test(w); }));
    check('Proficiency Weapon Martial', weapons.some(function (w) { return /^martial/i.test(w); }));
    if (other.length) { check('Proficiency Weapon Other', true); text('Proficiency Weapon Other Description', other.join(', ')); }

    var langs = uniq(['Common'].concat(S.langs || []));
    langs.slice(0, 6).forEach(function (l, i) { text('Language ' + (i + 1), l); });
    var tools = [X.bgR.tools, X.clsR.tools, X.subR.tools].filter(function (t) { return t && !/^none$/i.test(t); });
    tools.slice(0, 6).forEach(function (t, i) { text('Tool ' + (i + 1), t); });

    var limited = C.features.filter(function (f) { return f.uses && f.usesN != null; });
    limited.slice(0, 8).forEach(function (f, i) {
      text('Limited Feature ' + (i + 1), f.name);
      text('Limited Feature Max Usages ' + (i + 1), String(f.usesN));
      text('Limited Feature Recovery ' + (i + 1), f.uses.rec === 'Short Rest' ? '   SR' : (f.uses.rec === 'Dawn' ? 'Dawn' : '   LR'));
    });

    // ---- page 2: features, traits, background
    var head = [];
    if (c) head.push(c.name + ' ' + LEVEL + (s2 ? ' · ' + s2.name : '') + (C.table.length ? ' · ' + C.table.map(function (p) { return p[0] + ' ' + p[1]; }).join(' · ') : ''));
    if (X.sub && !X.subActive) head.push(X.sub.name + ' features start at level ' + X.subLevel + '.');
    if (C.speedFrom) head.push('Speed ' + C.speed + ' ft includes ' + C.speedFrom + ' (' + C.baseSpeed + ' ft without it)');
    head.push(C.acNote + ' · HP ' + C.hp + ' (d' + C.hd + (C.hpNotes.length ? ', ' + C.hpNotes.join(', ') : '') + ')');
    if (C.increase && C.increase.from) head.push(C.increase.from + ' is included in your ability scores.');
    head.push('');
    var featLines = C.features.filter(function (f) { return f.summary; }).map(function (f) { return '• ' + f.name + ' (' + (f.from && s2 && f.from === s2.name ? s2.name.replace(/^(Path|Circle|College|Oath|Way|School) of (the )?/i, '') + ' ' : '') + f.lv + '): ' + f.summary; });
    box('Class Features', fitted('Class Features', head, featLines));

    var spHead = [[C.size, X.spR.type, 'Speed ' + C.speed + ' ft', C.darkvision ? 'Darkvision ' + C.darkvision + ' ft' : ''].filter(Boolean).join(' · ')];
    var traitLines = (X.spR.traits || []).map(function (t) { return '• ' + t.name + (t.summary ? ': ' + t.summary : ''); });
    box('Racial Traits', fitted('Racial Traits', spHead, traitLines));

    if (X.bg) {
      text('Background Feature', X.bg.name);
      var bgl = [];
      if (X.bgR.skills) bgl.push('Skills: ' + X.bgR.skills.join(', '));
      if (X.bgR.tools) bgl.push('Tools: ' + X.bgR.tools);
      if (X.bgR.feat) bgl.push('Origin feat: ' + X.bgR.feat);
      if (X.bgR.equipment) bgl.push('Equipment: ' + X.bgR.equipment);
      box('Background Feature Description', boxLines('Background Feature Description', bgl));
    }
    box('Ideal', boxLines('Ideal', [S.ideals || '']));
    box('Bond', boxLines('Bond', [S.bond || '']));

    // ---- page 3: feat
    if (C.feat) {
      text('Feat Name 1', C.feat);
      box('Feat Description 1', boxLines('Feat Description 1', [C.featText || ('Origin feat from the ' + (X.bg ? X.bg.name : '') + ' background.')]));
    }

    // ---- page 4: who they are
    text('Age', S.age); text('Height', S.height); text('Weight', S.weight);
    text('Hair colour', S.hair); text('Eyes colour', S.eyes);
    text('Faith/Deity', S.faithless ? 'Faithless' : S.deity);
    text('Alignment', S.align);
    text('Size Category', C.size);
    var look = [S.fashion ? 'Style: ' + S.fashion : '', S.extra || ''].filter(Boolean).join('\n\n');
    var lookLeft = box('Background_Appearance', boxLines('Background_Appearance', [look]));
    box('Background_Organisation.Left', boxLines('Background_Organisation.Left', [S.bond || '']));
    var storyLeft = box('Background_History', boxLines('Background_History', [S.story || '']));

    // ---- notes pages: full feature text, printed on page 6's design (plus copies of it as needed)
    var blocks = [];
    C.features.forEach(function (f) {
      if (f.covered) return;
      blocks.push({ head: 'Level ' + f.lv + ': ' + f.name, tag: X.sub && f.from === X.sub.name ? f.from : '',
        text: (f.full || f.text || '').replace(/^\(([\s\S]*)\)\.?$/, '$1') });
    });
    if (C.featText) blocks.push({ head: 'Origin feat: ' + C.feat, tag: X.bg ? X.bg.name : '', text: C.featText });
    if (storyLeft.length) blocks.push({ head: 'Backstory (continued)', tag: '', text: unwrap(storyLeft) });
    if (lookLeft.length) blocks.push({ head: 'Appearance (continued)', tag: '', text: unwrap(lookLeft) });
    var extraPages = await notesPages(blocks);

    async function notesPages(blocks) {
      var fl = get('P5.ASnotes.Notes.Left'), fr = get('P5.ASnotes.Notes.Right');
      if (!fl || !fr || !blocks.length) return 0;
      var g = BOXES['P5.ASnotes.Notes.Left'];
      var rl = fl.acroField.getWidgets()[0].getRectangle(), rr = fr.acroField.getWidgets()[0].getRectangle();
      var pageRef = fl.acroField.getWidgets()[0].P(), pages = doc.getPages(), at = -1;
      pages.forEach(function (pg, i) { if (pg.ref === pageRef || (pageRef && pg.ref.toString() === pageRef.toString())) at = i; });
      if (at < 0) return 0;
      var bold = await doc.embedFont(PDFLib.StandardFonts.HelveticaBold);
      var width = rl.width - 6, perCol = g.rules - (g.first < 3 ? 1 : 0);
      // lay out: [{t, bold, tag}] lines; blank line between features; keep a heading off the last line of a column
      var lines = [];
      blocks.forEach(function (b) {
        var hw = bold.widthOfTextAtSize(winAnsi(b.head), BOX_FONT);
        var tag = b.tag ? oneLine('  (' + b.tag + ')', font, BOX_FONT, Math.max(20, width - hw)) : '';
        var head = { t: winAnsi(b.head), bold: true, tag: tag };
        if (hw > width) head = { t: oneLine(b.head, bold, BOX_FONT, width), bold: true, tag: '' };
        var body = wrap(b.text, font, BOX_FONT, width).map(function (t) { return { t: t }; });
        while (body.length && !body[body.length - 1].t) body.pop();
        if (lines.length % perCol === perCol - 1) lines.push({ t: '' });
        lines.push(head);
        lines = lines.concat(body);
        lines.push({ t: '' });
      });
      // drop blank lines that would open a column
      var cols = [], col = [];
      lines.forEach(function (l) {
        if (!col.length && !l.t) return;
        col.push(l);
        if (col.length === perCol) { cols.push(col); col = []; }
      });
      if (col.length) cols.push(col);
      // the old notes fields are hidden so nothing can be typed over the printed text
      [fl, fr].forEach(function (f) {
        f.acroField.getWidgets().forEach(function (w) { w.setFlagTo(PDFLib.AnnotationFlags.Hidden, true); });
        f.enableReadOnly();
      });
      var design = await doc.embedPage(doc.getPage(at));
      await design.embed();   // snapshot the blank design now, before text is drawn on page 6
      var size = doc.getPage(at).getSize(), added = 0;
      for (var k = 0; k < cols.length; k += 2) {
        var page = doc.getPage(at);
        if (k > 0) {
          page = doc.insertPage(at + k / 2, [size.width, size.height]);
          page.drawPage(design, { x: 0, y: 0, width: size.width, height: size.height });
          added++;
        }
        [[cols[k], rl], [cols[k + 1], rr]].forEach(function (pair) {
          if (!pair[0]) return;
          var r = pair[1], top = r.y + r.height;
          pair[0].forEach(function (l, i) {
            if (!l.t) return;
            var y = top - g.first - (i + (g.first < 3 ? 1 : 0)) * g.pitch + 2.1;
            var f = l.bold ? bold : font;
            page.drawText(l.t, { x: r.x + 3, y: y, size: BOX_FONT, font: f });
            if (l.tag) page.drawText(l.tag, { x: r.x + 3 + f.widthOfTextAtSize(l.t, BOX_FONT), y: y, size: BOX_FONT, font: font, color: PDFLib.rgb(0.35, 0.35, 0.35) });
          });
        });
      }
      return added;
    }

    // ---- draw everything
    function ruledProvider(lines, info) {
      return function (field, widget, f) {
        var r = widget.getRectangle(), h = r.height, enc = [];
        lines.forEach(function (ln, i) {
          var y = h - info.g.first - (i + info.skipTop) * info.g.pitch + 2.1;
          if (ln) enc.push({ encoded: f.encodeText(ln), x: 3, y: y });
        });
        return PDFLib.drawTextField({
          x: 0, y: 0, width: r.width, height: h, borderWidth: 0, padding: 0,
          textColor: PDFLib.rgb(0, 0, 0), font: f.name, fontSize: BOX_FONT, textLines: enc
        });
      };
    }
    done.forEach(function (d) {
      var f = d[0];
      if (d[1]) f.updateAppearances(font, ruledProvider(d[1].lines, d[1].info));
      else f.updateAppearances(font);
    });
    return { bytes: await doc.save({ updateFieldAppearances: false }), overflow: 0, notesPagesAdded: extraPages, computed: C };
  }

  var API = {
    XP: XP, pbAt: pbAt, levelOf: levelOf, featuresAt: featuresAt, AB: AB, AB_NAME: AB_NAME, SKILLS: SKILLS, ARRAY: ARRAY, BUY_COST: BUY_COST, BUY_POINTS: BUY_POINTS,
    mod: mod, signed: signed, resolve: resolve, skillGroups: skillGroups, proficientSkills: proficientSkills,
    baseScores: baseScores, pointsSpent: pointsSpent, bgBonus: bgBonus, finalScores: finalScores, compute: compute,
    build: build, winAnsi: winAnsi
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = API; else root.RealmsSheet = API;
})(typeof window !== 'undefined' ? window : this);
