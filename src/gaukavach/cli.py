"""
Command line interface. `python -m gaukavach <command>`.

Commands are grouped by what a sceptical reviewer would want to check:

    evidence    every constant, its grade and its source
    citations   references still needing first-party checking
    species     comparative audiogram - who ELSE hears this carrier
    hazards     the full hazard register, including what we cannot mitigate
    physics     propagation validated against published values
    envelope    the acoustic range envelope, computed not asserted
    refuse      proof that the governor rejects the 142 dB prototype level
    spectrum    the audible-click artefact and why ramping matters
    behaviour   dose-response with credible intervals, and trial sizing
    traffic     queueing impact of a blockage
    run         drive a scenario end to end and write the ledger
    sim         rebuild the interactive browser simulator
    render      render a scenario to MP4, or overlay real video
    demo        the full sequence, in the order to present it
    video       run perception on a real video file, if one is supplied
    cattle      run the cow-only road/speaker MVP (no hardware)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from . import __version__
from . import evidence as ev
from . import hazard as hz
from . import species as sp
from .acoustics import (
    Atmosphere,
    human_audibility_risk,
    lawrence_simmons_alpha,
    max_effective_range_m,
    model_disagreement,
    select_carrier,
    spreading_loss_db,
    sweep_frequencies,
)
from .detect import DEMO_SITE, SimpleTracker
from .emitter import PATTERNS, build_emission, compare_gating, write_wav
from .ledger import Ledger
from .policy import EngineConfig, PolicyEngine
from .scenario import SCENARIOS, run as run_scenario
from .traffic import RoadParams, blockage_impact, intervention_benefit
from .twin import BehaviourTwin
from .welfare import prove_refusal

BANNER = f"GauKavach v{__version__} - evidence-graded livestock deterrence"
RULE = "=" * 74


def _atm(args) -> Atmosphere:
    return Atmosphere(temp_c=args.temp, rh_pct=args.rh, ambient_spl_db=args.ambient)


def _default_cow_weights() -> str:
    repo_model = Path(__file__).resolve().parents[2] / "models" / "cow_best.pt"
    if repo_model.is_file():
        return str(repo_model)
    return "models/cow_best.pt"


def cmd_cattle_configure(args) -> int:
    from .cattle_mvp import configure_scene  # noqa: PLC0415

    configure_scene(args.source, args.output, args.camera_id)
    return 0


def cmd_cattle(args) -> int:
    from .cattle_mvp import run_cattle  # noqa: PLC0415

    result = run_cattle(
        source_path=args.source,
        weights=args.weights,
        scene_path=args.scene,
        output_path=args.output,
        confidence=args.conf,
        confirmation_frames=args.confirm_frames,
        max_frames=args.max_frames,
        show=args.show,
        camera_id=args.camera_id,
        event_log_path=args.event_log,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_server(args) -> int:
    from .server import main as server_main  # noqa: PLC0415

    server_main()
    return 0



# ---------------------------------------------------------------------------


def cmd_evidence(args) -> int:
    audit = ev.audit()
    print(BANNER)
    print(RULE)
    print(f"{audit['total_constants']} declared constants from {audit['sources']} sources")
    print()
    for grade, count in audit["by_grade"].items():
        print(f"  {grade:<32} {count}")
    print()
    print("Constants that may NOT authorise emission on their own "
          f"({len(audit['non_actionable'])}):")
    for name in audit["non_actionable"]:
        c = ev.REGISTRY[name]
        print(f"  - {name} = {c.value} {c.unit}  [{c.grade.value}]")
    if args.full:
        print()
        print(RULE)
        for c in ev.REGISTRY.values():
            print()
            print(f"{c.name} = {c.value} {c.unit}")
            print(f"  grade    : {c.grade.value}")
            print(f"  sources  : {', '.join(c.sources)}")
            print(f"  rationale: {c.rationale}")
    if args.json:
        Path(args.json).write_text(json.dumps(ev.export(), indent=2), encoding="utf-8")
        print()
        print(f"wrote {args.json}")
    return 0


def cmd_citations(args) -> int:
    """Pre-submission checklist: which references still need first-party checking."""
    print(BANNER)
    print(RULE)
    unver = ev.unverified_sources()
    checked = [k for k in unver if ev.SOURCES[k].metadata_checked]
    neither = [k for k in unver if not ev.SOURCES[k].metadata_checked]

    print(f"{len(ev.SOURCES)} sources.")
    print(f"  {len(checked):>2} metadata checked against the publisher's record, "
          f"not yet read")
    print(f"  {len(neither):>2} neither checked nor read")
    print()
    print("These are two different claims and the registry keeps them apart.")
    print("A metadata check confirms the reference exists and that its year,")
    print("volume and pages are right - the error that gets caught in review.")
    print("It says nothing about whether the source supports the claim drawn")
    print("from it. Only reading it does that, and only a person can.")
    print()
    print("Re-run the machine half any time:  python tools/check_citations.py")
    print()

    if neither:
        print("NOT CHECKED BY ANY MEANS - start here:")
        for k in neither:
            src = ev.SOURCES[k]
            print(f"  [ ] {k:<5} {src.citation}")
            if src.url:
                print(f"            {src.url}")
        print()

    print("METADATA CONFIRMED, STILL NEEDS READING:")
    for k in checked:
        src = ev.SOURCES[k]
        print(f"  [ ] {k:<5} {src.citation[:64]}")
        print(f"            checked {src.metadata_checked}")
    return 0


def cmd_species(args) -> int:
    carrier = args.carrier
    v = sp.selectivity_verdict(carrier)
    print(BANNER)
    print(RULE)
    print(f"Who can hear a {carrier / 1000:.1f} kHz carrier?")
    print()
    print("Hearing-range endpoints, all measured at the same 60 dB SPL criterion")
    print("as the cattle audiogram - which is what makes the comparison valid.")
    print()
    print(f"{'species':<20} {'group':<11} {'limit':>10} {'octaves':>9}  note")
    for r in sp.audibility_table(carrier):
        if not r["audible"]:
            note = "INAUDIBLE - not at risk"
        elif r["key"] == sp.TARGET_KEY:
            note = "<<< THE TARGET"
        elif r["more_sensitive_than_target"]:
            note = "hears it BETTER than the target"
        else:
            note = ""
        if not r["detectable"]:
            note += "  [UNDETECTABLE by our perception stack]"
        print(f"{r['name']:<20} {r['group']:<11} {r['limit_khz']:>8.1f}kHz "
              f"{r['octaves_below_limit']:>+9.3f}  {note}")
    print()
    print(RULE)
    print(v["conclusion"])
    print()
    print(f"  frequency_is_selective  : {v['frequency_is_selective']}")
    print(f"  target sensitivity rank : {v['target_sensitivity_rank']}")
    print(f"  non-target species hit  : {v['non_target_species_affected']}")
    print()
    print(f"  Adult audibility risk at this carrier : {human_audibility_risk(carrier):.2%}")
    print(f"  CHILD audibility risk at this carrier : {sp.child_audibility_risk(carrier):.1%}")
    print("  Children hear materially higher than adults, so a carrier chosen")
    print("  because adults cannot hear it is not automatically safe near a")
    print("  school. The band floor rises to 25 kHz at such sites.")
    bats = sp.bat_echolocation_overlap(carrier)
    print()
    print(f"  Bat echolocation overlap: {bats['overlaps_bat_echolocation']}")
    print(f"    {bats['note']}")
    print(f"    mitigation: {bats['mitigation']}")
    print(f"    residual  : {bats['residual']}")
    print()
    amb = ", ".join(sp.summary(carrier)["ambiguous_labels"])
    print(f"  Ambiguous detector labels: {amb}")
    print(f"  {sp.UNDETECTABLE_NOTE}")
    return 0


def cmd_hazards(args) -> int:
    s = hz.summary()
    print(BANNER)
    print(RULE)
    print(f"{s['total_hazards']} hazards across {s['categories']} categories")
    print()
    for k, v in sorted(s["by_status"].items()):
        print(f"  {k:<32} {v}")
    print()
    print(f"  Catastrophic severity : {', '.join(s['catastrophic'])}")
    print(f"  Open or undetectable  : {', '.join(s['open_or_undetectable'])}")
    print()
    print(f"  {s['honesty_note']}")
    print()
    print(RULE)

    if args.open_only:
        rows = hz.unmitigated()
        print("Hazards this system CANNOT mitigate")
    else:
        rows = hz.by_score()
        print("Full register, highest risk first")
    print()

    for h in rows:
        print(f"[{h.id}] {h.title}   "
              f"({h.severity.value}/{h.likelihood.value}, score {h.score})")
        print(f"      category  : {h.category}")
        print(f"      affected  : {h.affected}")
        print(f"      mechanism : {h.mechanism}")
        print(f"      detection : {h.detection}")
        print(f"      mitigation: {h.mitigation}")
        print(f"      RESIDUAL  : {h.residual}")
        tail = f"   [{', '.join(h.sources)}]" if h.sources else ""
        print(f"      status    : {h.status.value}{tail}")
        print()
    return 0


def cmd_physics(args) -> int:
    print(BANNER)
    print(RULE)
    print("Validation against the source report's Table 7.2")
    print("(0.7 dB/m at 30 kHz, Lawrence & Simmons, 25 C / 50% RH)")
    print()
    expected = {2: 6.7, 5: 16.8, 10: 26.3, 20: 39.3, 30: 49.8}
    print(f"{'dist':>6} {'geometric':>10} {'absorption':>11} {'total':>8} {'report':>8}")
    ok = True
    for d, exp in expected.items():
        g = spreading_loss_db(d)
        a = lawrence_simmons_alpha(30_000.0) * (d - 1)
        t = g + a
        match = abs(t - exp) < 0.1
        ok &= match
        flag = "ok" if match else "MISMATCH"
        print(f"{d:>5}m {g:>10.1f} {a:>11.1f} {t:>8.1f} {exp:>8.1f}  {flag}")
    print()
    print(f"All rows reproduced: {ok}")

    atm = _atm(args)
    print()
    print(RULE)
    print(f"Model disagreement at site conditions ({atm.temp_c} C, {atm.rh_pct}% RH)")
    print()
    for f in (22_000, 25_000, 30_000):
        d = model_disagreement(f, 20.0, atm)
        print(f"  {f / 1000:>4.0f} kHz @ 20 m : "
              f"ISO {d['iso9613_total_loss_db']:>6.2f} dB | "
              f"L&S {d['lawrence_simmons_total_loss_db']:>6.2f} dB | "
              f"delta {d['disagreement_db']:>5.2f} dB")
    print()
    print("  Policy: range uses the pessimistic model, exposure the optimistic")
    print("  one, so both errors fall on the safe side.")
    print("  Caveat: ISO 9613-1 is specified to 10 kHz. Every use above that is")
    print("  an extrapolation and is labelled as such in the output.")
    return 0 if ok else 1


def cmd_envelope(args) -> int:
    atm = _atm(args)
    cap = ev.get("osha_ultrasound_ceiling_db")
    print(BANNER)
    print(RULE)
    print(f"Site: {atm.temp_c} C, {atm.rh_pct}% RH, ambient {atm.ambient_spl_db} dB")
    print(f"Emitter ceiling {cap} dB @1m, directivity +{args.directivity} dB")
    print()
    print(f"{'carrier':>9} {'range':>9} {'alpha':>10} {'human risk':>11}  status")
    sweep = sweep_frequencies(atm, 15.0, cap, directivity_gain_db=args.directivity)
    for c in sweep:
        if c.freq_hz % 1000 != 0:
            continue
        rng = max_effective_range_m(
            c.freq_hz, atm, cap - c.sensitivity_penalty_db,
            directivity_gain_db=args.directivity,
        )
        status = "usable" if c.feasible else (c.reject_reason or "")[:38]
        print(f"{c.freq_hz / 1000:>7.0f}kHz {rng:>8.1f}m {c.alpha_db_per_m:>9.3f} "
              f"{c.human_risk:>10.2%}  {status}")
    best, _ = select_carrier(atm, args.distance, cap, directivity_gain_db=args.directivity)
    print()
    if best:
        print(f"Selected for a {args.distance:.0f} m target: {best.freq_hz / 1000:.1f} kHz "
              f"at {best.required_at_1m_db:.1f} dB @1m "
              f"({cap - best.required_at_1m_db:.1f} dB of headroom)")
    else:
        print(f"REFUSED for a {args.distance:.0f} m target: no carrier in the "
              "documented band reaches it inside the welfare ceiling.")
        print("The correct response is escalation, not a louder emitter.")
    return 0


def cmd_refuse(args) -> int:
    print(BANNER)
    print(RULE)
    print(json.dumps(prove_refusal(_atm(args)), indent=2))
    return 0


def cmd_spectrum(args) -> int:
    print(BANNER)
    print(RULE)
    r = compare_gating(args.carrier)
    print(f"Carrier {r['carrier_khz']} kHz, pattern '{r['pattern']}'")
    print()
    for key in ("hard_gated", "raised_cosine"):
        d = r[key]
        print(f"  {key:<15} worst audible {d['audible_energy_db']:>8.1f} dB "
              f"@ {d['worst_audible_hz'] / 1000:>5.2f} kHz | "
              f"f/2 probe {d['subharmonic_level_db']:>8.1f} dB")
    print()
    print(f"  Ramping improves the audible band by {r['improvement_db']:.0f} dB.")
    print()
    print(f"  {r['interpretation']}")
    print()
    print(f"  Honesty note: {r['honesty_note']}")
    if args.wav:
        wave, rep = build_emission(args.carrier, PATTERNS[0])
        write_wav(args.wav, wave)
        print()
        print(f"  wrote {args.wav} ({wave.size} samples @ {rep.sample_rate} Hz)")
        print("  NOTE: most laptop DACs and speakers cannot reproduce this band.")
        print("  Verify with a calibrated ultrasonic transducer and microphone.")
    return 0


def cmd_behaviour(args) -> int:
    twin = BehaviourTwin()
    print(BANNER)
    print(RULE)
    print("Dose-response for cattle at 22-30 kHz.")
    print("There is NO published curve for this. What follows is an explicit")
    print("prior with uncertainty propagated, not a measurement.")
    print()
    print(f"{'received':>9} {'P(turn)':>9} {'90% credible':>18}  verdict")
    for d in range(55, 111, 5):
        o = twin.response_probability(float(d))
        print(f"{d:>7} dB {o.p_response_median:>9.2f} "
              f"  [{o.p_response_lo:.2f}, {o.p_response_hi:.2f}]     {o.verdict[:44]}")
    print()
    print(RULE)
    print(f"Habituation at {args.received} dB received, 3 encounters/day")
    print()
    for row in twin.habituation_projection(args.received, days=10):
        if row["day"] % 3 == 1:
            print(f"  day {row['day']:>2}  P(turn) {row['p_response_median']:.3f}  "
                  f"(habituation factor {row['habituation_factor']:.2f})")
    print()
    print("  A deterrent that only works on day one is not a deterrent.")
    print()
    print(RULE)
    print("Field trial sizing")
    print()
    print(json.dumps(twin.required_sample_size(), indent=2))
    return 0


def cmd_traffic(args) -> int:
    params = RoadParams(lanes=args.lanes, demand_veh_h=args.demand)
    print(BANNER)
    print(RULE)
    print(f"{args.lanes} lanes, demand {args.demand} veh/h, "
          f"saturation {params.saturation_flow_veh_h_lane:.0f} veh/h/lane")
    print()
    for secs in (60, 120, 300, 600):
        i = blockage_impact(float(secs), params)
        print(f"  {secs:>4}s blockage -> peak queue {i.max_queue_veh:>6.1f} veh | "
              f"clears in {i.queue_clear_s:>7.1f}s | "
              f"{i.person_hours_lost:>7.2f} person-h | INR {i.cost_inr:>9.1f}")
    print()
    print(RULE)
    b = intervention_benefit(args.baseline, args.improved, params,
                             incidents_per_day=args.incidents)
    print(f"Clearing in {args.improved:.0f}s instead of {args.baseline:.0f}s:")
    print()
    print(json.dumps(b["per_incident"], indent=2))
    print()
    print("Per day:")
    print(json.dumps(b["per_day"], indent=2))
    print()
    print(b["caveat"])
    return 0


def cmd_run(args) -> int:
    if args.scenario not in SCENARIOS:
        print(f"unknown scenario {args.scenario!r}. Available:")
        for k, s in SCENARIOS.items():
            print(f"  {k:<22} {s.description[:60]}")
        return 2
    sc = SCENARIOS[args.scenario]
    atm = _atm(args)
    ledger = Ledger(args.ledger) if args.ledger else Ledger()
    engine = PolicyEngine(
        DEMO_SITE, atm, ledger,
        EngineConfig(directivity_gain_db=args.directivity, dry_run=True),
    )
    print(BANNER)
    print(RULE)
    print(f"Scenario : {sc.name}")
    print(f"           {sc.description}")
    print()
    snaps = run_scenario(sc, engine, SimpleTracker(), verbose=args.verbose)

    counts: dict[str, int] = {}
    for s in snaps:
        for a in s["actions"]:
            counts[a["action"]] = counts.get(a["action"], 0) + 1
    print("Actions:")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {k:<14} {v}")

    print()
    print("Key events from the ledger:")
    for r in engine.ledger:
        p = r.payload
        if r.kind == "emission":
            pr = p["predicted_response"]
            print(f"  [{r.seq:>3}] EMISSION   {p['carrier_hz'] / 1000:.1f} kHz "
                  f"{p['level_at_1m_db']} dB@1m -> {p['predicted_received_db']} dB "
                  f"at {p['distance_m']} m | P(turn) {pr['p_response_median']} "
                  f"[{pr['p_response_lo']}, {pr['p_response_hi']}] | "
                  f"dry_run={p['dry_run']}")
        elif r.kind == "escalation":
            print(f"  [{r.seq:>3}] ESCALATION {p['reason'][:78]}")
        elif r.kind == "traffic_response":
            print(f"  [{r.seq:>3}] TRAFFIC    warning at {p['trigger_distance_m']} m; "
                  f"advance sign {p['plan']['advance_warning_position_m']} m upstream")
        elif r.kind == "stop":
            print(f"  [{r.seq:>3}] STOP       {p.get('reason', '')[:78]}")
        elif r.kind == "observation":
            print(f"  [{r.seq:>3}] OBSERVED   {p['outcome_name']}")

    summary = engine.close()
    gov = summary["governor"]
    print()
    print("Governor vetoes:")
    if gov["denials_by_reason"]:
        for reason, n in sorted(gov["denials_by_reason"].items(), key=lambda kv: -kv[1]):
            print(f"  x{n:<5} {reason}")
    else:
        print("  none")
    chain = engine.ledger.verify()
    print()
    print(f"Incidents {summary['incidents']} | escalated {summary['escalated']} | "
          f"total emission {summary['total_emission_s']} s")
    print(f"Ledger: {chain['records']} records, chain valid = {chain['valid']}")
    if args.ledger:
        print(f"Written to {args.ledger}")
    if args.json:
        Path(args.json).write_text(
            json.dumps({
                "scenario": {"name": sc.name, "description": sc.description},
                "snapshots": snaps,
                "ledger": engine.ledger.export(),
                "summary": summary,
                "evidence": ev.export(),
                "hazards": hz.export(),
            }, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"Full record written to {args.json}")
    return 0


def cmd_video(args) -> int:
    """Run real perception over a video file. Requires opencv + YOLO weights."""
    import cv2  # noqa: PLC0415

    from .detect import Perception  # noqa: PLC0415

    per = Perception(weights=args.weights, conf=args.conf)
    if not per.available:
        print(f"YOLO unavailable: {per.error}")
        return 1
    cap = cv2.VideoCapture(args.path)
    if not cap.isOpened():
        print(f"cannot open {args.path}")
        return 1

    atm = _atm(args)
    engine = PolicyEngine(
        DEMO_SITE, atm, Ledger(args.ledger) if args.ledger else Ledger(),
        EngineConfig(directivity_gain_db=args.directivity, dry_run=True),
    )
    tracker = SimpleTracker()
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    idx = 0
    print(BANNER)
    print(RULE)
    print(f"Reading {args.path} at {fps:.1f} fps. Detector: {args.weights}")
    print()
    print("NOTE: DEMO_SITE geometry is a placeholder. Distances are meaningless")
    print("until camera height, focal length and horizon are calibrated for this")
    print("specific camera. Treat the zone overlay as illustrative.")
    print()

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % max(args.stride, 1) == 0:
            dets = per.detect(frame)
            tracks = tracker.update(dets)
            snap = engine.step(tracks, idx / fps)
            for a in snap["actions"]:
                if a["action"] in ("emit", "denied", "escalate", "out_of_range"):
                    detail = a.get("reason", a.get("carrier_khz", ""))
                    print(f"  t={idx / fps:6.2f}s  {a['action']:<13} {detail}")
        idx += 1
        if args.max_frames and idx >= args.max_frames:
            break
    cap.release()
    summary = engine.close()
    print()
    print(f"Frames {idx} | incidents {summary['incidents']} | "
          f"emission {summary['total_emission_s']} s")
    print(f"Ledger chain valid: {engine.ledger.verify()['valid']}")
    return 0



def cmd_sim(args) -> int:
    """Rebuild dashboard/sim.json and re-inject it into the simulator page."""
    from .simulate import export  # noqa: PLC0415

    print(BANNER)
    print(RULE)
    print("Running every scenario through the real engine and evaluating the")
    print("decision field. This is what makes the browser demo trustworthy:")
    print("it replays Python verdicts, it does not re-implement them.")
    print()
    data = export(args.out, step_px=args.step)
    frames = sum(len(s["frames"]) for s in data["scenarios"].values())
    cells = len(data["field"]["cells"])
    verdicts: dict[str, int] = {}
    for c in data["field"]["cells"]:
        verdicts[c["v"]] = verdicts.get(c["v"], 0) + 1
    print(f"  scenarios    {len(data['scenarios'])}")
    print(f"  frames       {frames}")
    print(f"  field cells  {cells}   {verdicts}")
    print(f"  written      {args.out}")

    # The built page is a few megabytes of data wrapped around 45 KB of code,
    # so only the code is tracked. The page is assembled here from the
    # template plus whichever data files exist, which is what makes the
    # console reproducible from a clean checkout instead of being a binary
    # that has to be carried around by hand.
    page = Path(args.page)
    tmpl = Path(args.template)
    # Take the template whenever it is newer than the built page, not only when
    # the page is missing.
    #
    # It used to be "only when missing", which meant every edit to the
    # template - the code, the part under review - was silently ignored on any
    # machine that already had a built page. You changed the console, rebuilt,
    # reloaded, and studied the old code. The page is fully derived from the
    # template plus the payload files, so there is nothing in it to protect.
    stale = (tmpl.exists() and page.exists()
             and tmpl.stat().st_mtime > page.stat().st_mtime)
    if not page.exists() or stale:
        if not tmpl.exists():
            print(f"  note: neither {page} nor {tmpl} found, wrote JSON only")
            return 0
        missing = [p for p in ("dashboard/footage.json", "dashboard/outcome.json")
                   if not Path(p).exists()]
        if missing and stale:
            # Rebuilding from the template drops whatever is only in the page.
            print(f"  WARNING: rebuilding from {tmpl} but {', '.join(missing)} "
                  f"is missing - those tabs will be empty")
        page.write_text(tmpl.read_text(encoding="utf-8"), encoding="utf-8")
        why = "template is newer" if stale else "no page yet"
        print(f"  page         built from {tmpl}  ({why})")

    html = page.read_text(encoding="utf-8")
    end = "</script>"
    for pid, src_path in (("sim", args.out),
                          ("foot", "dashboard/footage.json"),
                          ("outc", "dashboard/outcome.json")):
        data_file = Path(src_path)
        marker = f'<script id="{pid}" type="application/json">'
        i = html.find(marker)
        if i < 0:
            print(f"  WARNING: no '{pid}' payload marker in {page}")
            continue
        j = html.find(end, i)
        current = html[i + len(marker): j]
        if not data_file.exists():
            # Never blank a payload that is already in the page just because
            # its source file is missing - that silently guts a working demo.
            if not current.strip():
                print(f"  note: {pid:5} has no data ({data_file} missing)")
            continue
        html = html[: i + len(marker)] + data_file.read_text(encoding="utf-8") + html[j:]
    # Stamp the build. Without it there is no way to tell a freshly rebuilt
    # 6.6 MB page from the copy the browser kept, and reading yesterday's
    # verdicts while believing they are today's is the expensive kind of wrong.
    stamp = time.strftime("%Y-%m-%d %H:%M")
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        if sha.returncode == 0 and sha.stdout.strip():
            stamp += "  " + sha.stdout.strip()
    except Exception:
        pass                            # a stamp without a sha still dates it
    a, b = "<!--BUILD-->", "<!--/BUILD-->"
    i, j = html.find(a), html.find(b)
    if i >= 0 and j > i:
        html = html[: i + len(a)] + stamp + html[j:]
    else:
        print("  WARNING: no build stamp marker in the page")

    page.write_text(html, encoding="utf-8")
    print(f"  injected     {page}  ({page.stat().st_size / 1048576:.2f} MB)")
    print(f"  build        {stamp}")
    print()
    print("Open the page in any browser. It is fully self-contained.")
    return 0


def cmd_render(args) -> int:
    from .render import render_all, render_scenario, render_video  # noqa: PLC0415

    print(BANNER)
    print(RULE)
    if args.video:
        print(f"Overlaying the decision loop on {args.video}")
        print("Frames are watermarked UNCALIBRATED: the site geometry is not")
        print("measured for this camera, so distances are indicative only.")
        out = render_video(args.video, args.out or "gaukavach_overlay.mp4",
                           weights=args.weights, conf=args.conf,
                           stride=args.stride, max_frames=args.max_frames,
                           show=args.show)
        print(f"wrote {out}")
        return 0
    if args.all:
        made = render_all(args.outdir, fps=args.fps)
        for m in made:
            print(f"  wrote {m}")
        print()
        print(f"{len(made)} clips in {args.outdir}/")
        return 0
    out = args.out or f"{args.scenario}.mp4"
    render_scenario(args.scenario, out, fps=args.fps)
    print(f"wrote {out}  (watermarked SIMULATED)")
    return 0


def cmd_demo(args) -> int:
    """The full sequence, in the order it should be presented."""
    steps = [
        ("What every number in this system is based on", cmd_evidence),
        ("Who ELSE hears this - the finding that reshaped the design", cmd_species),
        ("The propagation model, validated against published values", cmd_physics),
        ("What the physics actually permits", cmd_envelope),
        ("Proof the device refuses the one published cattle exposure", cmd_refuse),
        ("Why a hard-gated ultrasonic burst is audible", cmd_spectrum),
        ("What we honestly do not know about cattle response", cmd_behaviour),
        ("Every way this could hurt something, including what we cannot fix",
         cmd_hazards),
    ]
    for i, (title, fn) in enumerate(steps, 1):
        print()
        print()
        print("#" * 74)
        print(f"# {i}. {title}")
        print("#" * 74)
        print()
        fn(args)
    print()
    print()
    print("#" * 74)
    print("# 9. The closed loop, end to end")
    print("#" * 74)
    for name in ("person-in-cone", "goat-flock", "cow-with-calf",
                 "flight-into-road", "single-approach", "persistent-blocker"):
        args.scenario = name
        print()
        cmd_run(args)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gaukavach", description=BANNER,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--temp", type=float, default=32.0, help="air temperature C")
    p.add_argument("--rh", type=float, default=60.0, help="relative humidity %%")
    p.add_argument("--ambient", type=float, default=58.0, help="ambient SPL dB")
    p.add_argument("--directivity", type=float, default=12.0, help="emitter gain dB")
    p.add_argument("--json", default=None, help="write machine-readable output here")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("evidence", help="every constant, grade and source")
    s.add_argument("--full", action="store_true")
    s.set_defaults(func=cmd_evidence)

    s = sub.add_parser("citations", help="references needing first-party checking")
    s.set_defaults(func=cmd_citations)

    s = sub.add_parser("species", help="comparative audiogram - who else hears this")
    s.add_argument("--carrier", type=float, default=25_000.0)
    s.set_defaults(func=cmd_species)

    s = sub.add_parser("hazards", help="full hazard register")
    s.add_argument("--open-only", action="store_true",
                   help="show only hazards with no mitigation")
    s.set_defaults(func=cmd_hazards)

    s = sub.add_parser("physics", help="propagation validated against the report")
    s.set_defaults(func=cmd_physics)

    s = sub.add_parser("envelope", help="computed acoustic range envelope")
    s.add_argument("--distance", type=float, default=15.0)
    s.set_defaults(func=cmd_envelope)

    s = sub.add_parser("refuse", help="proof the 142 dB level is rejected")
    s.set_defaults(func=cmd_refuse)

    s = sub.add_parser("spectrum", help="audible-click artefact analysis")
    s.add_argument("--carrier", type=float, default=25_000.0)
    s.add_argument("--wav", default=None, help="also write a WAV file")
    s.set_defaults(func=cmd_spectrum)

    s = sub.add_parser("behaviour", help="dose-response intervals and trial sizing")
    s.add_argument("--received", type=float, default=85.0)
    s.set_defaults(func=cmd_behaviour)

    s = sub.add_parser("traffic", help="queueing impact of a blockage")
    s.add_argument("--lanes", type=int, default=2)
    s.add_argument("--demand", type=float, default=900.0)
    s.add_argument("--baseline", type=float, default=300.0)
    s.add_argument("--improved", type=float, default=90.0)
    s.add_argument("--incidents", type=float, default=4.0)
    s.set_defaults(func=cmd_traffic)

    s = sub.add_parser("run", help="drive a scenario end to end")
    s.add_argument("scenario", nargs="?", default="single-approach")
    s.add_argument("--ledger", default=None, help="append the ledger to this path")
    s.add_argument("--verbose", action="store_true")
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("sim", help="rebuild the interactive browser simulator")
    s.add_argument("--out", default="dashboard/sim.json")
    s.add_argument("--page", default="dashboard/simulator.html")
    s.add_argument("--template", default="dashboard/simulator_template.html",
                   help="code-only page used when --page does not exist yet")
    s.add_argument("--step", type=int, default=16, help="decision-field grid, px")
    s.set_defaults(func=cmd_sim)

    s = sub.add_parser("render", help="render a scenario to MP4, or overlay real video")
    s.add_argument("scenario", nargs="?", default="single-approach")
    s.add_argument("--out", default=None)
    s.add_argument("--all", action="store_true", help="render every scenario")
    s.add_argument("--outdir", default="media")
    s.add_argument("--fps", type=int, default=15)
    s.add_argument("--video", default=None, help="overlay this real video instead")
    s.add_argument("--weights", default="yolov8n.pt")
    s.add_argument("--conf", type=float, default=0.35)
    s.add_argument("--stride", type=int, default=1)
    s.add_argument("--max-frames", type=int, default=0)
    s.add_argument("--show", action="store_true", help="live window while rendering")
    s.set_defaults(func=cmd_render)

    s = sub.add_parser("video", help="run real perception on a video file")
    s.add_argument("path")
    s.add_argument("--weights", default="yolov8n.pt")
    s.add_argument("--conf", type=float, default=0.35)
    s.add_argument("--stride", type=int, default=3)
    s.add_argument("--max-frames", type=int, default=0)
    s.add_argument("--ledger", default=None)
    s.set_defaults(func=cmd_video)

    s = sub.add_parser("cattle-configure", help="configure a road polygon and speaker locations from a video first frame")
    s.add_argument("--source", required=True, help="reference image or video; a video's first frame is used")
    s.add_argument("--output", default="calibration/scene_config.json")
    s.add_argument("--camera-id", default="default-camera", help="stable ID reused for videos from this fixed camera")
    s.set_defaults(func=cmd_cattle_configure)

    s = sub.add_parser("cattle", help="run fixed-polygon cow detection and nearest-speaker selection; never activates hardware")
    s.add_argument("source", help="image or video path")
    s.add_argument("--weights", default=_default_cow_weights(), help="cow detector weights (default: models/cow_best.pt)")
    s.add_argument("--scene", default="calibration/scene_config.json", help="persistent scene configuration from cattle-configure")
    s.add_argument("--camera-id", default="default-camera", help="must match the ID used during cattle-configure")
    s.add_argument("--output", default=None, help="annotated image or video output")
    s.add_argument("--conf", type=float, default=0.30)
    s.add_argument("--confirm-frames", type=int, default=3)
    s.add_argument("--max-frames", type=int, default=0)
    s.add_argument("--event-log", default=None, help="optional JSONL nearest-speaker event log")
    s.add_argument("--show", action="store_true")
    s.set_defaults(func=cmd_cattle)

    s = sub.add_parser("server", help="start real-time WebSocket and MJPEG API server")
    s.set_defaults(func=cmd_server)


    s = sub.add_parser("demo", help="the whole sequence, in presentation order")
    s.add_argument("--full", action="store_true")
    s.add_argument("--distance", type=float, default=15.0)
    s.add_argument("--carrier", type=float, default=25_000.0)
    s.add_argument("--received", type=float, default=85.0)
    s.add_argument("--wav", default=None)
    s.add_argument("--ledger", default=None)
    s.add_argument("--verbose", action="store_true")
    s.add_argument("--open-only", action="store_true")
    s.add_argument("--lanes", type=int, default=2)
    s.add_argument("--demand", type=float, default=900.0)
    s.add_argument("--baseline", type=float, default=300.0)
    s.add_argument("--improved", type=float, default=90.0)
    s.add_argument("--incidents", type=float, default=4.0)
    s.set_defaults(func=cmd_demo, scenario="single-approach")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
