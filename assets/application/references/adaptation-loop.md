# Finish this application skill

Use scnet-app's [source-to-skill workflow](https://github.com/lql341/scnet-app/blob/main/references/adaptation-loop.md).
The user fixes acceptance in app.json and level-A delivery in delivery.json.
Port the source into runtime/app/, add a short reproducible input and check in
runtime/case/, and environment setup in runtime/scripts/. Stage every runtime
file in app.json files. Run a bounded SCNet job, retain raw logs, and record each
attempt. `gate` reports remaining blockers and attempts; `build` produces the
skill directory and official tar only after the declared gate passes. Finish the
English/Chinese installation, usage, prerequisites and test-case instructions.
Do not treat the generated scaffold or self-reported runtime.json as certification.
