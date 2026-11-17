# Packaging recipes, rendered only for packaged projects (template answer
# `packaged`). Owned by the galtzagorri template; imported with `import?`.

# Install the project's [project.scripts] on PATH as an editable uv tool
install-tool:
    @{{ info }} "editable: the commands follow the working tree; reinstall after changing [project.scripts]"
    uv tool install --editable --force .
