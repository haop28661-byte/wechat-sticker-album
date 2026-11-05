# Contributing

1. Keep image providers model-agnostic.
2. Do not add a default vendor API, default model, or embedded credential.
3. Add tests for changes to config resolution, provider routing, installation, image finalization, or output structure.
4. Preserve project-relative output behavior.
5. Keep ZIP output optional.
6. Preserve third-party MIT licenses and source notices when updating vendored code.
7. Run `python -m pytest` and the skill validator before submitting changes.
