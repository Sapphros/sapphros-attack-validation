# Detection Validation 001: Persistence, Credential Access, and Defense Evasion

**Date:** 2026-09-19
**Target:** `win-target-01` (Windows 11 25H2, Sysmon 15.22, Defender enabled)
**Attack platform:** MITRE Caldera (`sapphros-attack`)
**Operation:** [`sapphros-detection-validation-v1`](../scenarios/sapphros-detection-validation-v1.yml)

## Summary

This exercise ran three MITRE ATT&CK techniques via Caldera against an
instrumented Windows victim and validated each against the lab's Sysmon
telemetry configuration ([`configs/sysmon/sysmonconfig.xml`](../configs/sysmon/sysmonconfig.xml)):

| Technique | Tactic | Result |
|---|---|---|
| T1547.001 – Registry Run Keys | Persistence | **Detected** |
| T1003.001 – LSASS Memory (comsvcs.dll) | Credential Access | **Prevented** |
| T1070.004 – File Deletion | Defense Evasion | **Detected** |

Two techniques produced clean, expected telemetry matches. The third
produced a more interesting result: the attack was blocked before it could
execute, and the investigation into *why* it registered as a Sysmon event
anyway led to a real detection-engineering finding and a rule fix.

## T1547.001 — Registry Run Key Persistence

Caldera's "Reg Key Run" ability wrote a value to
`HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run`. Sysmon Event ID 13
recorded the exact key modification:

This matches the `persistence-run` filter in the lab's Sysmon configuration
and is captured by
[`t1547_001_registry_run_key.yml`](../detections/sigma/t1547_001_registry_run_key.yml).
Straightforward pass — the pipeline worked exactly as designed.

## T1003.001 — LSASS Memory Access, and a False-Positive Finding

Caldera ran an ability that calls `rundll32.exe` with `comsvcs.dll`'s
`MiniDump` export against the LSASS process — a well-known, well-signatured
credential-dumping technique.

**What actually happened:** Microsoft Defender intercepted and remediated
the command before it produced a dump file, classifying it as
`Trojan:Win32/RundllLolBin.AF`. Critically, Sysmon's Event ID 1
(ProcessCreate) log shows **no `rundll32.exe` process ever launched** in
the relevant window — Defender stopped it early enough that the technique
never reached the point of opening a real handle to LSASS as the attacker.

The two Sysmon Event ID 10 (ProcessAccess) events that *did* target
`lsass.exe` in that window both had `SourceImage` set to
`MsMpEng.exe` — Defender's own engine, performing its detection and
remediation scan of LSASS, not the simulated attacker.

**The finding:** the lab's original Sysmon rule for this technique
(`attack-t1003-lsass-access` in `sysmonconfig.xml`) matches any process
accessing `lsass.exe`, with no filter on the source process. Left as-is,
this rule would have logged Defender's own remediation activity as a
"detected" attacker technique — a false positive baked directly into the
detection logic, discovered by actually running the attack rather than by
inspecting the rule on paper.

**The fix:**
[`t1003_001_lsass_access_non_defender.yml`](../detections/sigma/t1003_001_lsass_access_non_defender.yml)
adds an explicit exclusion for `SourceImage` paths under
`\Windows Defender\`, so the rule only fires on non-Defender processes
accessing LSASS.

**How this is scored:** because the technique was stopped by an existing
preventive control (Defender) before it could execute, and no attacker
process ever generated the ProcessAccess event, this result is recorded as
**PREVENTED**, not **DETECTED** — a meaningfully different and more honest
validation outcome than a Sigma match against attacker telemetry would be.

## T1070.004 — File Deletion

A seeded decoy file (`%TEMP%\deleteme_T1551.004`) was removed via
PowerShell's `Remove-Item`. Sysmon Event ID 26 recorded the deletion within
seconds of Caldera's reported operation finish time, with an exact
`TargetFilename` match. Captured by
[`t1070_004_temp_file_deletion.yml`](../detections/sigma/t1070_004_temp_file_deletion.yml).

## Incidental Finding: Sandcat's Own Execution Mechanism

Independent of the three planned techniques, Sysmon Event ID 8
(CreateRemoteThread) recorded `sandcat.exe` injecting into `powershell.exe`
— this is simply how the Caldera agent executes commands on the host, but
it happens to produce telemetry resembling a T1055 process-injection
technique. Not a scored result here, but worth noting: adversary emulation
tooling itself generates real telemetry, and a detection engineer needs to
be able to distinguish tooling artifacts from the techniques under test.

## Raw Evidence

Full operation chain, Sysmon event excerpts, and the Defender detection
record are preserved in
[`reports/operations/sapphros-detection-validation-v1.json`](../reports/operations/sapphros-detection-validation-v1.json).

## Lessons Learned

1. Running a technique end-to-end surfaces false positives that reviewing
   a detection rule in isolation does not — the LSASS rule looked correct
   until Defender's own scan tripped it.
2. "Detected" and "prevented" are different outcomes and should be modeled
   differently in a validation pipeline; collapsing them loses information
   a defender needs.
3. Adversary-emulation tooling has its own telemetry footprint, distinct
   from the techniques it's executing, and that needs to be accounted for
   when interpreting results.
