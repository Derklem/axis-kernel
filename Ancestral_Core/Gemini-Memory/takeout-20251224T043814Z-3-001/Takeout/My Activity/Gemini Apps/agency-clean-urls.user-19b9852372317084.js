// ==UserScript==
// @name         Agency: Clean URLs + Safer Outbound (+ Controller & Log)
// @namespace    https://example.org/agency-node
// @version      0.3
// @description  Strip tracking params, add rel=noreferrer/noopener, show a toggle pill, per-site bypass, and log actions locally.
// @match        *://*/*
// @grant        none
// ==/UserScript==

(() => {
  "use strict";

  /* ------------------ settings / storage ------------------ */
  const KEY_ENABLED = "agency.enabled";                // "1" | "0"
  const KEY_BYPASS_PREFIX = "agency.siteBypass.";      // + hostname -> "1"
  const LOG_DB = "agency-log";
  const LOG_STORE = "events";
  const LOG_CAP = 500;

  const getHost = () => location.hostname.replace(/^www\./, "");
  const getEnabled = () => (localStorage.getItem(KEY_ENABLED) ?? "1") === "1";
  const setEnabled = (v) => localStorage.setItem(KEY_ENABLED, v ? "1" : "0");
  const getBypass = () => localStorage.getItem(KEY_BYPASS_PREFIX + getHost()) === "1";
  const toggleBypass = () => {
    const k = KEY_BYPASS_PREFIX + getHost();
    const nv = localStorage.getItem(k) === "1" ? "0" : "1";
    localStorage.setItem(k, nv);
    toast(`Agency: ${nv === "1" ? "Bypassing on this site" : "Active on this site"}`);
  };

  /* ------------------ tiny logger (IndexedDB) -------------- */
  let dbPromise;
  function openDB() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((res, rej) => {
      const req = indexedDB.open(LOG_DB, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(LOG_STORE)) {
          const store = db.createObjectStore(LOG_STORE, { keyPath: "id", autoIncrement: true });
          store.createIndex("t", "t");
        }
      };
      req.onsuccess = () => res(req.result);
      req.onerror = () => rej(req.error);
    });
    return dbPromise;
  }

  async function addEvent(evt) {
    try {
      const db = await openDB();
      const tx = db.transaction(LOG_STORE, "readwrite");
      const st = tx.objectStore(LOG_STORE);
      await new Promise((res, rej)=>{ const r = st.add({ t: Date.now(), ...evt }); r.onsuccess=()=>res(); r.onerror=()=>rej(r.error); });
      // keep ring buffer ~LOG_CAP
      const all = [];
      await new Promise((res, rej)=>{
        const idx = st.index("t").openCursor(null, "prev"); // newest first
        idx.onsuccess = e => {
          const cur = e.target.result;
          if (!cur) return res();
          if (all.length < LOG_CAP) all.push(cur.key);
          cur.continue();
        };
        idx.onerror = () => rej(idx.error);
      });
      if (all.length >= LOG_CAP) {
        const tx2 = db.transaction(LOG_STORE, "readwrite");
        const st2 = tx2.objectStore(LOG_STORE);
        // delete everything older than the newest LOG_CAP
        await new Promise((res, rej)=>{
          const cur = st2.openCursor();
          cur.onsuccess = e => {
            const c = e.target.result;
            if (!c) return res();
            if (!all.includes(c.key)) st2.delete(c.key);
            c.continue();
          };
          cur.onerror = ()=>rej(cur.error);
        });
      }
    } catch(_) {}
  }

  async function exportLog() {
    try {
      const db = await openDB();
      const tx = db.transaction(LOG_STORE, "readonly");
      const st = tx.objectStore(LOG_STORE);
      const evts = [];
      await new Promise((res, rej)=>{
        const cur = st.openCursor();
        cur.onsuccess = e => {
          const c = e.target.result;
          if (!c) return res();
          evts.push(c.value);
          c.continue();
        };
        cur.onerror = ()=>rej(cur.error);
      });
      const blob = new Blob([JSON.stringify(evts, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `agency-log-${new Date().toISOString().slice(0,10)}.json`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast("Agency: log exported.");
    } catch (e) { toast("Agency: export failed."); }
  }

  /* ------------------ core cleaners ------------------------ */
  const TRACK = new Set([
    "utm_source","utm_medium","utm_campaign","utm_term","utm_content",
    "utm_name","utm_id","utm_reader","utm_cid","utm_referrer",
    "fbclid","gclid","igshid","mc_cid","mc_eid","oly_anon_id","oly_enc_id",
    "msclkid","vero_conv","vero_id","stm_campaign","pk_campaign","pk_kwd","si","spm","ref"
  ]);

  const isExternal = (href) => {
    try { return new URL(href, location.href).origin !== location.origin; }
    catch { return false; }
  };

  function cleanUrl(u) {
    try {
      const url = new URL(u, location.href);
      const removed = [];
      [...url.searchParams.keys()].forEach(k => {
        if (TRACK.has(k) || k.toLowerCase().startsWith("utm_")) {
          url.searchParams.delete(k);
          removed.push(k);
        }
      });
      if (url.hash === "#") url.hash = "";
      return { href: url.toString(), removed };
    } catch { return { href: u, removed: [] }; }
  }

  function hardenLink(a) {
    if (!a || !a.href) return {removed:[], hardened:false};
    const { href, removed } = cleanUrl(a.href);
    let hardened = false;
    if (removed.length) a.href = href;
    if (isExternal(a.href)) {
      const rel = new Set((a.getAttribute("rel") || "").split(/\s+/).filter(Boolean));
      const before = rel.size;
      rel.add("noopener"); rel.add("noreferrer");
      a.setAttribute("rel", [...rel].join(" "));
      hardened = rel.size !== before;
    }
    return { removed, hardened };
  }

  function cleanLocationBar() {
    const { href, removed } = cleanUrl(location.href);
    if (removed.length) {
      history.replaceState({}, "", href);
      addEvent({ action:"clean-location", removed });
      toast(`Agency: cleaned ${removed.join(", ")}`);
    }
  }

  function scan(root=document) {
    let removedCt = 0, hardenedCt = 0;
    root.querySelectorAll("a[href]").forEach(a => {
      const r = hardenLink(a);
      removedCt += r.removed.length ? 1 : 0;
      hardenedCt += r.hardened ? 1 : 0;
    });
    if (removedCt || hardenedCt) addEvent({ action:"scan", removedCt, hardenedCt, url: location.href });
  }

  /* ------------------ UI: floating pill -------------------- */
  let longPressTimer = null;
  function pillColor() {
    return getBypass() ? "#999" : (getEnabled() ? "#2ecc71" : "#e67e22");
  }
  function ensurePill() {
    if (document.getElementById("agency-pill")) return;
    const el = document.createElement("button");
    el.id = "agency-pill";
    el.textContent = "Agency";
    Object.assign(el.style, {
      position:"fixed", right:"12px", bottom:"12px", padding:"8px 12px",
      background:pillColor(), color:"#fff", font:"12px system-ui, sans-serif",
      border:"0", borderRadius:"999px", boxShadow:"0 2px 8px rgba(0,0,0,.25)",
      zIndex: 2147483647, opacity: ".9"
    });
    el.title = "Tap: enable/disable • Long-press: bypass this site • Double-tap: export log";
    document.documentElement.appendChild(el);

    let lastTap = 0;
    el.addEventListener("click", () => {
      const now = Date.now();
      if (now - lastTap < 300) { exportLog(); return; } // double tap
      lastTap = now;
      if (getBypass()) { toggleBypass(); el.style.background = pillColor(); return; }
      const next = !getEnabled(); setEnabled(next);
      toast(`Agency: ${next ? "enabled" : "disabled"}`);
      el.style.background = pillColor();
      if (next) runAll(); // re-run when turning back on
    });

    el.addEventListener("mousedown", () => {
      longPressTimer = setTimeout(() => { toggleBypass(); el.style.background = pillColor(); }, 650);
    });
    ["mouseup","mouseleave","touchend","touchcancel"].forEach(ev=>el.addEventListener(ev, ()=>{ if(longPressTimer){clearTimeout(longPressTimer); longPressTimer=null;} }));
  }

  function toast(msg) {
    const n = document.createElement("div");
    n.textContent = msg;
    Object.assign(n.style, {
      position:"fixed", right:"10px", bottom:"58px",
      background:"rgba(0,0,0,.85)", color:"#fff", padding:"6px 10px",
      font:"12px/1.2 system-ui, sans-serif", borderRadius:"6px",
      zIndex:2147483647, opacity:"0", transform:"translateY(10px)", transition:"all .25s"
    });
    document.body.appendChild(n);
    requestAnimationFrame(()=>{ n.style.opacity="1"; n.style.transform="translateY(0)"; });
    setTimeout(()=>{ n.style.opacity="0"; n.style.transform="translateY(10px)"; setTimeout(()=>n.remove(), 300); }, 1500);
  }

  /* ------------------ observers & main --------------------- */
  const mo = new MutationObserver(muts => {
    if (!getEnabled() || getBypass()) return;
    muts.forEach(m => {
      m.addedNodes.forEach(n => {
        if (n.nodeType === 1) {
          if (n.tagName === "A") hardenLink(n);
          else scan(n);
        }
      });
    });
  });

  function runAll() {
    if (!getEnabled() || getBypass()) return;
    cleanLocationBar();
    scan(document);
  }

  function init() {
    ensurePill();
    runAll();
    mo.observe(document.documentElement, { childList:true, subtree:true });
    document.addEventListener("copy", (e) => {
      if (!getEnabled() || getBypass()) return;
      const sel = (document.getSelection()?.toString() || "").trim();
      if (/^https?:\/\//i.test(sel)) {
        const { href, removed } = cleanUrl(sel);
        if (removed.length && e.clipboardData) {
          e.preventDefault(); e.clipboardData.setData("text/plain", href);
          addEvent({ action:"clean-clipboard", removed });
          toast("Agency: cleaned copied URL");
        }
      }
    }, true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once:true });
  } else init();

})();
