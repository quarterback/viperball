(() => {
  const data = JSON.parse(document.getElementById("book-data").textContent);
  const side = document.getElementById("book-side");
  const school = document.getElementById("book-school");
  const list = document.getElementById("book-packages");
  const preferred = document.getElementById("book-preferred");
  const save = document.getElementById("book-save");
  const replay = document.getElementById("book-replay");
  const field = document.getElementById("book-field");

  const width = 640;
  const height = 320;
  const line = 350;
  const color = {
    field: 0x1b4438, marking: 0x578273, line: 0xc9dcce,
    offense: 0x91d5ff, defense: 0xffa98d, run: 0xf8f5cc,
    lateral: 0xffcf68, kick: 0xa4f6df,
  };
  const captions = {
    tight: "Tight", split: "Split", spread: "Spread", heavy: "Heavy",
    stacked: "Stacked front", aggressive: "Pressure front",
    balanced: "Balanced front",
  };
  const label = (value) => value.replaceAll("_", " ");
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
    list.replaceChildren(...rows);
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
  }

  function preview(id) {
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
    field.setAttribute("aria-label", item ? item.name + " schematic" : "Empty field");
    drawField();
  }

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
    if (family === "kick_pass") {
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
