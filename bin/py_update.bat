@echo off
echo going to update some requirement files
uv pip install pip setuptools wheel
for %%x in (core, dev) do (
    uv pip compile %%x_requirements.in -o %%x_requirements.txt
)
uv pip sync core_requirements.txt dev_requirements.txt
uv add -r core_requirements.in
uv add --dev -r dev_requirements.in
echo finished!
@echo on
