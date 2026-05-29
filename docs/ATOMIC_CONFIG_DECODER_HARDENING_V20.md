# Atomic Config And Decoder Hardening (V20)

This version records hardening work around staged AXI-Lite configuration and
decoder pipeline safety.

## Scope

- Enforce shadow-to-active commit model through CFG_APPLY semantics.
- Preserve deterministic register update ordering for multi-register config.
- Keep decoder alignment and saturation behavior explicit and testable.

## Key Properties

- Shadow registers receive writes without touching active decode parameters.
- Active decode parameters update only on explicit apply pulse.
- Control pulses (clear/telemetry/apply) remain one-shot style outputs.
- Decoder arithmetic stages preserve signed saturation behavior.

## Validation Hooks

- Static checks in tests around staged register naming and apply semantics.
- Behavioral AXI-Lite simulation confirms staged-vs-active behavior under
  AW/W ordering permutations and backpressure.

## Notes

V20 is pre-board hardening. It improves determinism and safety of runtime
configuration but does not by itself prove timing/CDC/DRC closure.
