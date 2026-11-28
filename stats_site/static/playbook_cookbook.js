(() => {
  const data = JSON.parse(document.getElementById("book-data").textContent);
  const side = document.getElementById("book-side");
  const school = document.getElementById("book-school");
  const list = document.getElementById("book-packages");
  const preferred = document.getElementById("book-preferred");
  const practiceBudget = document.getElementById("book-practice-budget");
  const practiceFocus = document.getElementById("book-practice-focus");
  const practiceSettings = document.getElementById("book-practice-settings");
  const pairs = document.getElementById("book-pairs");
  const pairControl = document.getElementById("book-pair-control");
  const save = document.getElementById("book-save");
  const replay = document.getElementById("book-replay");
  const field = document.getElementById("book-field");
  const variant = document.getElementById("book-variant");
  const variants = {
    gaelic_kick_and_follow: [["keep", "Receiver keeps"], ["give", "Lateral to support"]],
    afl_boundary_switch: [["setup", "Work the boundary"], ["switch", "Switch to the far side"]],
    rugby_carry_release: [["setup", "Carry toward the setup side"], ["release", "Sweep the far edge"]],
    ball_protect_bonus: [["carry", "Inside carry"], ["outlet", "Short outlet"]],
    // Cross code books (engine/cross_code.py): one choice per branch of the read.
    fm_switchback: [["vacated", "Missed switch: pitch to the Slotback"], ["switched", "Clean switch: Zeroback keeps"]],
    fm_twin_trigger: [["carry", "Halfback takes the snap and carries"], ["kick", "Halfback takes the snap and kicks"]],
    fm_false_lead: [["counter", "Defense chases the Viper: counter"], ["seam", "Defense holds: kick to the seam"]],
    fm_anchor_release: [["release", "Blitz: lateral to the released lineman"], ["protect", "No blitz: run inside"]],
    fm_mirror_flood: [["flood", "Kick into the flood"], ["weak", "Flood side loaded: Halfback alone"]],
    ph_pullback: [["pullback", "Stacked box: pull back to the Slotback"], ["kick", "Balanced front: kick over"], ["secure", "Pressure: Halfback keeps it"]],
    ph_short_side_strike: [["pitch", "Pitch to the Viper on the short side"], ["sweep", "Sweep the short side"]],
    rl_wall_return: [["keep", "Defender waits: Halfback keeps"], ["return", "Defender jumps: back to the Zeroback"]],
    rl_up_back_across: [["back", "Up and back"], ["across", "Up, back and across"], ["held", "Tackled at once: receiver holds"]],
    rl_safe_outlet: [["kick", "Quick kick outlet"], ["pitch", "Pitch to the back"]],
    cf_slip_cross: [["slip", "Missed switch: kick to the Slotback"], ["switched", "Clean switch: inside run"]],
    cf_pivot_turn: [["pivot", "Edge takes the Zeroback: pitch"], ["keep", "Edge stays home: Zeroback keeps"]],
    cf_double_clear: [["seam", "A decoy draws his man: Viper through the seam"], ["kick", "Nobody bites: kick to the Viper"]],
    cf_same_look_reverse: [["look", "The look"], ["reverse", "The reverse from the same look"]],
  };

  const width = 640;
  const height = 320;
  const line = 350;
  const color = {
    field: 0x1b4438, marking: 0x578273, line: 0xc9dcce,
    offense: 0x91d5ff, defense: 0xffa98d, run: 0xf8f5cc,
    lateral: 0xffcf68, kick: 0xa4f6df, move: 0xc8b6ff,
  };
  const captions = {
    tight: "Tight", split: "Split", spread: "Spread", heavy: "Heavy",
    stacked: "Stacked front", aggressive: "Pressure front",
    balanced: "Balanced front",
  };
  const label = (value) => value.replaceAll("_", " ");
  const pairKey = (pair) => [pair.formation, ...pair.packages].join("|");
  const selectedPairs = new Set((data.draft.same_look_pairs || []).map(pairKey));
  let checked = new Set(data.draft.packages || []);
  let packageId;
  let openDescription;
  let scene;
  let ball;

  function paintPackageList() {
    const base = data.schools[side.value].find((entry) => entry.scheme_id === school.value);
    const ids = base?.packages || [];
    checked = new Set(ids.filter((id) => checked.has(id)));
    if (!ids.includes(openDescription)) openDescription = undefined;
    const rows = ids.map((id) => {
      const item = data.packages[id];
      const row = document.createElement("div");
      row.className = "book-package";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.name = "packages";
      checkbox.value = id;
      checkbox.id = "package-" + id;
      checkbox.checked = checked.has(id);
      const name = document.createElement("label");
      name.htmlFor = checkbox.id;
      name.textContent = item.name;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn-small";
      button.textContent = "Preview";
      button.setAttribute("aria-label", "Preview " + item.name);
      const summary = document.createElement("p");
      summary.className = "book-package-summary";
      summary.id = "package-summary-" + id;
      summary.textContent = item.summary;
      summary.hidden = openDescription !== id;
      button.setAttribute("aria-controls", summary.id);
      button.setAttribute("aria-expanded", String(!summary.hidden));
      button.addEventListener("click", () => {
        const previous = list.querySelector('button[aria-expanded="true"]');
        const expanding = previous !== button;
        if (previous) {
          previous.setAttribute("aria-expanded", "false");
          document.getElementById(previous.getAttribute("aria-controls")).hidden = true;
        }
        if (expanding) {
          button.setAttribute("aria-expanded", "true");
          summary.hidden = false;
        }
        openDescription = expanding ? id : undefined;
        preview(id);
      });
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          checked.add(id);
          preview(id);
        } else {
          checked.delete(id);
        }
        updateChoices(preferred.value);
      });
      row.append(checkbox, name, button, summary);
      return row;
    });
    // Group the list so each set of concepts reads on its own.
    const crossCode = new Set(["gaelic_kick_and_follow", "afl_boundary_switch",
      "rugby_carry_release", "ball_protect_bonus", "cfl_corner_chase"]);
    // The clinic's cross code books each get their own group (engine/cross_code.py).
    const books = { fm: "free", ph: "phase", rl: "relay", cf: "crossfire", dx: "crossdefense" };
    const groupOf = (id) => id.startsWith("cape_cod_") ? "cape"
      : crossCode.has(id) ? "cross"
      : books[id.split("_")[0]] || (id.startsWith("clinic_") ? "clinic"
      : /^(pp|pko|pk)_/.test(id) ? "delta" : "base");
    const groupNames = {
      base: "Base packages",
      cape: "Cape Cod",
      cross: "Cross code concepts",
      free: "Free Motion",
      phase: "Phase Attack",
      relay: "Relay",
      crossfire: "Crossfire",
      crossdefense: "Cross code answers",
      clinic: "Clinic concepts",
      delta: side.value === "defense" ? "Delta penalty kill" : "Delta power play and penalty kill exits",
    };
    const grouped = [];
    for (const group of ["cape", "cross", "free", "phase", "relay", "crossfire", "crossdefense",
                         "base", "clinic", "delta"]) {
      const members = rows.filter((row, i) => groupOf(ids[i]) === group);
      if (!members.length) continue;
      const heading = document.createElement("h4");
      heading.className = "book-group";
      heading.textContent = groupNames[group];
      grouped.push(heading, ...members);
    }
    list.replaceChildren(...grouped);
    if (!ids.includes(packageId)) {
      preview(ids.find((id) => checked.has(id)) || ids[0]);
    }
  }

  function updateSchools(wanted) {
    school.replaceChildren(...data.schools[side.value].map((entry) =>
      new Option(entry.label, entry.scheme_id)));
    if ([...school.options].some((option) => option.value === wanted)) {
      school.value = wanted;
    }
    paintPackageList();
    updateChoices(preferred.value);
  }

  function updateChoices(wanted) {
    preferred.replaceChildren(new Option("Coordinator decides", ""), ...[...checked].map((id) =>
      new Option(data.packages[id].name, id)));
    if (checked.has(wanted)) {
      preferred.value = wanted;
    }
    const atLimit = checked.size >= data.maxPackages;
    list.querySelectorAll("input").forEach((input) => {
      input.disabled = atLimit && !input.checked;
    });
    document.getElementById("book-count").textContent =
      `${checked.size} of ${data.maxPackages} packages selected`;
    save.disabled = checked.size === 0;
    updatePractice(practiceFocus.value);
  }

  function updatePractice(focus) {
    practiceFocus.replaceChildren(new Option("Divide time evenly", ""), ...[...checked].map((id) =>
      new Option(data.packages[id].name, id)));
    if (checked.has(focus)) practiceFocus.value = focus;
    const options = data.sameLookOptions.filter((pair) => pair.packages.every((id) => checked.has(id)));
    const validKeys = new Set(options.map(pairKey));
    for (const key of selectedPairs) {
      if (!validKeys.has(key)) selectedPairs.delete(key);
    }
    pairs.replaceChildren(...options.map((pair) => {
      const key = pairKey(pair);
      const row = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.name = "same_look_pairs";
      checkbox.value = key;
      checkbox.checked = selectedPairs.has(key);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) selectedPairs.add(key);
        else selectedPairs.delete(key);
      });
      const names = pair.packages.map((id) => data.packages[id].name).join(" + ");
      row.append(checkbox, ` ${names} (${captions[pair.formation]})`);
      return row;
    }));
    pairControl.hidden = options.length === 0;
  }

  function showPracticeSettings() {
    practiceSettings.hidden = !practiceBudget.checked;
    practiceSettings.disabled = !practiceBudget.checked;
  }

  function preview(id) {
    if (id !== packageId) {
      const options = variants[id] || [];
      variant.replaceChildren(...options.map(([value, title]) => new Option(title, value)));
      document.getElementById("book-variant-control").hidden = options.length === 0;
    }
    packageId = id;
    const item = data.packages[id];
    const origin = item && data.schools[item.side].find((entry) => entry.scheme_id === item.origin_family);
    const shape = item && (item.alignment || item.formation_tags[0]);
    const focus = item && (item.focus || [...item.play_family_tags, ...item.kick_pass_tags]);
    document.getElementById("book-package-name").textContent = item?.name || "No compatible packages";
    document.getElementById("book-package-origin").textContent = origin ? "From " + origin.label : "";
    document.getElementById("book-package-shape").textContent = shape
      ? `${captions[shape] || label(shape)} · ${focus.map(label).join(", ")}` : "";
    document.getElementById("book-package-scenario").textContent = item ? "When to use it: " + item.scenario : "";
    document.getElementById("book-package-personnel").textContent = item?.personnel_tags.length
      ? "Roster requirements: " + item.personnel_tags.map((tag) => data.vocabulary.personnel[tag].plain).join("; ")
      : item ? "Roster requirements: any roster" : "";
    document.getElementById("book-package-tradeoff").textContent = item ? "Tradeoff: " + item.cost : "";
    replay.disabled = !scene || !item;
    const choice = variant.selectedOptions[0]?.text;
    field.setAttribute("aria-label", item ? [item.name, choice].filter(Boolean).join(", ") : "Empty field");
    drawField();
  }

  // Cross code offense: the read's branches, from the Zeroback (Z), the
  // Halfback (H), the Viper (V), the Wingback (W), the Slotback (S) and the
  // fourth flanker (F). The top of the field is the weak or short side.
  const crossOffense = {
    fm_switchback: (v, p) => [
      [p.W.x, p.W.y, 395, p.S.y - 10, color.move], [p.S.x, p.S.y, 395, p.W.y + 10, color.move],
      ...(v === "switched"
        ? [[p.Z.x, p.Z.y, 440, 150, color.run]]
        : [[p.Z.x, p.Z.y, 350, 95, color.lateral], [350, 95, 500, 70, color.run]]),
    ],
    fm_twin_trigger: (v, p) => [
      [339, 160, p.H.x, p.H.y, color.lateral],
      ...(v === "kick"
        ? [[p.H.x, p.H.y, 470, p.W.y, color.kick]]
        : [[p.H.x, p.H.y, 365, 60, color.run], [365, 60, 505, 45, color.run]]),
    ],
    fm_false_lead: (v, p) => [
      [p.V.x, p.V.y, 430, 25, color.move],
      ...(v === "seam"
        ? [[p.S.x, p.S.y, 430, 235, color.move], [p.Z.x, p.Z.y, 430, 235, color.kick]]
        : [[p.Z.x, p.Z.y, 330, 200, color.run], [330, 200, 495, 270, color.run]]),
    ],
    fm_anchor_release: (v) => v === "protect"
      ? [[307, 160, 431, 169, color.run]]
      : [[339, 202, 315, 238, color.move], [307, 160, 315, 238, color.lateral], [315, 238, 470, 260, color.run]],
    fm_mirror_flood: (v, p) => v === "weak"
      ? [[p.V.x, p.V.y, 470, 30, color.move], [p.W.x, p.W.y, 425, 75, color.move],
         [p.H.x, p.H.y, 365, 265, color.run], [365, 265, 510, 280, color.run]]
      : [[p.V.x, p.V.y, 470, 30, color.move], [p.W.x, p.W.y, 425, 75, color.move],
         [p.S.x, p.S.y, 395, 120, color.move], [p.Z.x, p.Z.y, 425, 75, color.kick]],
    ph_pullback: (v, p) => {
      if (v === "kick") return [[p.H.x, p.H.y, 335, 165, color.move], [p.Z.x, p.Z.y, 470, p.W.y, color.kick]];
      if (v === "secure") return [[p.H.x, p.H.y, 431, 169, color.run]];
      return [[p.S.x, p.S.y, 295, 225, color.move], [p.H.x, p.H.y, 338, 168, color.run],
              [338, 168, 295, 225, color.lateral], [295, 225, 470, 265, color.run]];
    },
    ph_short_side_strike: (v, p) => v === "sweep"
      ? [[p.H.x, p.H.y, 360, 50, color.run], [360, 50, 500, 35, color.run]]
      : [[p.Z.x, p.Z.y, p.V.x, p.V.y, color.lateral], [p.V.x, p.V.y, 485, 30, color.run]],
    rl_wall_return: (v, p) => v === "return"
      ? [[p.Z.x, p.Z.y, 300, 100, color.lateral], [300, 100, 355, 92, color.run],
         [p.Z.x, p.Z.y, 335, 128, color.move], [355, 92, 335, 128, color.lateral], [335, 128, 485, 120, color.run]]
      : [[p.Z.x, p.Z.y, 300, 100, color.lateral], [300, 100, 470, 80, color.run]],
    rl_up_back_across: (v, p) => {
      const out = [[p.Z.x, p.Z.y, 400, p.W.y, color.kick]];
      if (v === "held") return [...out, [400, p.W.y, 470, p.W.y, color.run]];
      out.push([400, p.W.y, 385, 170, color.lateral]);
      if (v === "back") return [...out, [385, 170, 480, 175, color.run]];
      return [...out, [385, 170, 375, 232, color.lateral], [375, 232, 490, 242, color.run]];
    },
    rl_safe_outlet: (v, p) => v === "pitch"
      ? [[p.Z.x, p.Z.y, 290, 215, color.lateral], [290, 215, 450, 250, color.run]]
      : [[p.S.x, p.S.y, 380, 200, color.move], [p.Z.x, p.Z.y, 380, 200, color.kick]],
    cf_slip_cross: (v, p) => [
      [p.V.x, p.V.y, 400, 150, color.move], [p.S.x, p.S.y, 415, 90, color.move],
      ...(v === "switched" ? [[p.Z.x, p.Z.y, 431, 169, color.run]] : [[p.Z.x, p.Z.y, 415, 90, color.kick]]),
    ],
    cf_pivot_turn: (v, p) => [
      [p.H.x, p.H.y, 335, 72, color.move], [p.Z.x, p.Z.y, 362, 82, color.run],
      ...(v === "keep" ? [[362, 82, 500, 60, color.run]]
        : [[362, 82, 335, 72, color.lateral], [335, 72, 500, 40, color.run]]),
    ],
    cf_double_clear: (v, p) => [
      [p.W.x, p.W.y, 400, 35, color.move], [p.S.x, p.S.y, 400, 285, color.move],
      ...(v === "kick" ? [[p.V.x, p.V.y, 440, 160, color.move], [p.Z.x, p.Z.y, 440, 160, color.kick]]
        : [[p.V.x, p.V.y, 365, 150, color.run], [365, 150, 505, 160, color.run]]),
    ],
    cf_handoff_punish: (v, p) => [[p.S.x, p.S.y, 435, 232, color.move], [p.Z.x, p.Z.y, 435, 232, color.kick]],
    cf_same_look_reverse: (v, p) => v === "reverse"
      ? [[p.Z.x, p.Z.y, 335, 128, color.run], [335, 128, 470, 250, color.run], [470, 250, 520, 262, color.run]]
      : [[p.Z.x, p.Z.y, 362, 82, color.run], [362, 82, 500, 60, color.run]],
  };

  // Cross code defense: which real defenders move, and where.
  const crossDefense = {
    dx_exchange: ({ back, bx }) => [[bx, back[1], 478, back[2] + 6], [bx, back[2], 478, back[1] - 6]],
    dx_stagger: ({ back, bx }) => [[bx, back[2], 420, 150], [bx, back[3], 480, 180], [bx, back[4], 545, 215]],
    dx_edge_anchor: ({ x }) => [[x, 139, 430, 40]],
    dx_slide_replace: ({ back, bx }) => [[bx, back[3], 410, back[2] + 4], [bx, back[4], bx, back[3]]],
    dx_channel_press: ({ x }) => [[x, 139, 322, 150], [x, 181, 322, 170], [x, 160, 430, 280]],
    dx_transition_net: ({ back, bx }) => [[bx, back[2], 392, 150], [bx, back[3], 392, 170],
                                          [bx, back[0], 545, back[0]], [bx, back[5], 545, back[5]]],
    dx_cross_rush: ({ x }) => [[x, 139, 330, 176], [x, 181, 330, 144]],
    dx_set_breaker: ({ back, bx }) => [[bx, back[2], 405, 150], [bx, back[3], 405, 170]],
  };

  function diagram() {
    const item = data.packages[packageId];
    if (!item) return { players: [], routes: [] };

    const front = [118, 139, 160, 181, 202];
    const shape = item.side === "offense" ? item.formation_tags[0] : "split";
    const lanes = {
      tight: [96, 125, 194, 224],
      split: [65, 112, 208, 255],
      spread: [38, 91, 229, 282],
      heavy: [99, 130, 190, 219],
    }[shape] || [65, 112, 208, 255];
    const players = [
      ...front.map((y) => [339, y, color.offense]),
      [307, 160, color.offense], [278, 160, color.offense],
      ...lanes.map((y, i) => [i % 2 ? 301 : 330, y, color.offense]),
    ];
    const defense = item.alignment || "balanced";
    const back = defense === "spread" ? [40, 92, 133, 189, 229, 279] : [72, 108, 140, 180, 212, 248];
    players.push(
      ...front.map((y) => [defense === "stacked" ? 362 : 375, y, color.defense]),
      ...back.map((y) => [defense === "aggressive" ? 414 : 451, y, color.defense]),
    );
    if (item.side === "defense" && crossDefense[item.package_id]) {
      const routes = crossDefense[item.package_id]({ front, back, x: defense === "stacked" ? 362 : 375,
                                                     bx: defense === "aggressive" ? 414 : 451 });
      return { players, routes: routes.map(([x, y, tx, ty, tint]) => ({ x, y, tx, ty, tint: tint || color.defense,
                                                                           noBall: tint === color.move })) };
    }
    if (item.side === "defense") {
      let routes;
      if (defense === "aggressive" || defense === "stacked") {
        routes = [[375, 139, 306, 149], [375, 181, 306, 171]];
      } else {
        routes = [[451, back[0], 518, 59], [451, back[5], 518, 261]];
      }
      return { players, routes: routes.map(([x, y, tx, ty]) => ({ x, y, tx, ty, tint: color.defense })) };
    }
    const family = item.play_family_tags[0];
    const subtype = item.kick_pass_tags[0];
    const origin = { x: 307, y: 160 };
    const route = (from, tx, ty, tint) => ({ ...from, tx, ty, tint });
    const routes = [];
    const spots = {
      Z: { x: 307, y: 160 }, H: { x: 278, y: 160 },
      V: { x: 330, y: lanes[0] }, W: { x: 301, y: lanes[1] },
      S: { x: 330, y: lanes[2] }, F: { x: 301, y: lanes[3] },
    };
    if (crossOffense[item.package_id]) {
      // Each step: [from x, from y, to x, to y, tint]. Movement without the
      // ball is drawn but the animated ball skips it.
      for (const [x, y, tx, ty, tint] of crossOffense[item.package_id](variant.value, spots)) {
        routes.push({ x, y, tx, ty, tint, noBall: tint === color.move });
      }
      return { players, routes };
    }
    if (item.package_id === "gaelic_kick_and_follow") {
      const catchSpot = { x: 397, y: lanes[0] };
      routes.push(route(origin, catchSpot.x, catchSpot.y, color.kick));
      if (variant.value === "give") {
        routes.push(route(catchSpot, 379, lanes[1], color.lateral));
        routes.push(route({ x: 379, y: lanes[1] }, 467, lanes[1], color.run));
      } else {
        routes.push(route(catchSpot, 462, lanes[0], color.run));
      }
    } else if (item.package_id === "afl_boundary_switch") {
      if (variant.value === "switch") {
        routes.push(route(origin, 493, lanes[3], color.kick));
      } else {
        routes.push(route(origin, 390, lanes[0], color.kick));
      }
    } else if (item.package_id === "rugby_carry_release") {
      const release = variant.value === "release";
      routes.push(route(origin, 408, release ? lanes[0] : 213, color.run));
      if (release) routes.push(route({ x: 408, y: lanes[0] }, 511, lanes[0], color.run));
    } else if (item.package_id === "ball_protect_bonus" && variant.value === "outlet") {
      routes.push(route(origin, 390, lanes[0], color.kick));
    } else if (family === "punt") {
      routes.push(route(origin, 616, 45, color.kick));
    } else if (family === "kick_pass") {
      const target = { x: { bomb: 555, territory: 520 }[subtype] || 482, y: lanes[0] };
      routes.push(route(origin, target.x, target.y, color.kick));
      if (subtype === "kick_lateral") {
        routes.push(route(target, 426, lanes[1], color.lateral));
      }
    } else if (family === "lateral_spread") {
      routes.push(route(origin, 301, lanes[1], color.lateral));
      routes.push(route({ x: 301, y: lanes[1] }, 291, lanes[0], color.lateral));
      routes.push(route({ x: 291, y: lanes[0] }, 492, lanes[0], color.run));
    } else {
      const wide = ["speed_option", "sweep_option", "viper_jet"].includes(family);
      routes.push(route(origin, wide ? 393 : 431, wide ? lanes[2] : 169, color.run));
      if (wide) routes.push(route({ x: 393, y: lanes[2] }, 519, lanes[2], color.run));
    }
    return { players, routes };
  }

  function arrowPoints(route) {
    const angle = Math.atan2(route.ty - route.y, route.tx - route.x);
    return [-0.55, 0.55].map((turn) => [
      route.tx - 12 * Math.cos(angle + turn),
      route.ty - 12 * Math.sin(angle + turn),
    ]);
  }

  function drawField() {
    const { players, routes } = diagram();
    if (!scene) {
      drawStill(players, routes);
      return;
    }
    const g = scene.fieldGraphics;
    g.clear().fillStyle(color.field).fillRect(0, 0, width, height);
    for (let x = 30; x < width; x += 40) {
      g.lineStyle(x === line ? 3 : 1, x === line ? color.line : color.marking);
      g.lineBetween(x, 0, x, height);
    }
    for (const [x, y, tint] of players) {
      g.fillStyle(tint).fillCircle(x, y, 7);
    }
    for (const route of routes) {
      g.lineStyle(4, route.tint).lineBetween(route.x, route.y, route.tx, route.ty);
      for (const [x, y] of arrowPoints(route)) g.lineBetween(route.tx, route.ty, x, y);
    }
    scene.tweens.killTweensOf(ball);
    ball.setVisible(false);
  }

  function drawStill(players, routes) {
    const ns = "http://www.w3.org/2000/svg";
    const hex = (tint) => "#" + tint.toString(16).padStart(6, "0");
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    function add(tag, attrs) {
      const node = document.createElementNS(ns, tag);
      for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
      svg.append(node);
    }
    for (let x = 30; x < width; x += 40) {
      add("line", { x1: x, x2: x, y1: 0, y2: height, stroke: hex(x === line ? color.line : color.marking) });
    }
    for (const [x, y, tint] of players) {
      add("circle", { cx: x, cy: y, r: 7, fill: hex(tint) });
    }
    for (const route of routes) {
      const stroke = hex(route.tint);
      add("line", { x1: route.x, y1: route.y, x2: route.tx, y2: route.ty, stroke, "stroke-width": 4 });
      for (const [x, y] of arrowPoints(route)) {
        add("line", { x1: route.tx, y1: route.ty, x2: x, y2: y, stroke, "stroke-width": 4 });
      }
    }
    field.replaceChildren(svg);
  }

  side.value = data.draft.side === "defense" ? "defense" : "offense";
  updateSchools(data.draft.school);
  updateChoices(data.draft.preferred);
  if (checked.has(data.draft.practice_focus)) practiceFocus.value = data.draft.practice_focus;
  showPracticeSettings();
  practiceBudget.addEventListener("change", showPracticeSettings);
  variant.addEventListener("change", () => preview(packageId));
  side.addEventListener("change", () => updateSchools());
  school.addEventListener("change", () => {
    paintPackageList();
    updateChoices(preferred.value);
  });

  replay.addEventListener("click", () => {
    const { routes } = diagram();
    scene.tweens.killTweensOf(ball);
    const animate = (index) => {
      const route = routes[index];
      if (!route) return;
      if (route.noBall) {
        animate(index + 1);
        return;
      }
      ball.setPosition(route.x, route.y).setVisible(true);
      scene.tweens.add({
        targets: ball, x: route.tx, y: route.ty, duration: 550,
        ease: "Sine.inOut", onComplete: () => animate(index + 1),
      });
    };
    animate(0);
  });

  document.getElementById("book-import-file").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    const input = document.getElementById("book-import");
    if (!file) return;
    input.setCustomValidity("");
    if (file.size > 8192) {
      input.setCustomValidity("Playbook imports are limited to 8 KB.");
      input.reportValidity();
      return;
    }
    try {
      input.value = await file.text();
    } catch {
      input.setCustomValidity("Could not read that file. Paste the playbook JSON instead.");
      input.reportValidity();
    }
  });
  document.getElementById("book-import").addEventListener("input", (event) => {
    event.target.setCustomValidity("");
  });

  if (window.Phaser) {
    field.replaceChildren();
    new window.Phaser.Game({
      type: window.Phaser.CANVAS, parent: field, width, height,
      audio: { noAudio: true },
      scale: { mode: window.Phaser.Scale.FIT, autoCenter: window.Phaser.Scale.CENTER_BOTH },
      scene: {
        create() {
          scene = this;
          this.fieldGraphics = this.add.graphics();
          ball = this.add.circle(0, 0, 5, 0xffffff).setStrokeStyle(2, 0x172423);
          preview(packageId);
        },
      },
    });
  }
})();
