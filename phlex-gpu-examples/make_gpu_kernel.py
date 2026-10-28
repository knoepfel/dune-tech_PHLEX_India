"""Make a personal copy of the phaindia apptainer kernel that starts the container with --nv.

Run it in a terminal OUTSIDE the container (prompt `jupyter-you@...`, not `Apptainer>`):

    python3 make_gpu_kernel.py              # finds the kernel whose name contains "phaindia"
    python3 make_gpu_kernel.py <kernel-name> # or name it (see: jupyter kernelspec list)

Then reload the notebook page and pick "<original name> (GPU)" from the kernel menu.
It writes only to ~/.local/share/jupyter/kernels/, so it never changes the hub's own kernels.
To remove it again: jupyter kernelspec remove <kernel-name>-gpu
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

APPTAINER_SUBCOMMANDS = ("exec", "run", "shell")


def main():
    specs = json.loads(subprocess.check_output(["jupyter", "kernelspec", "list", "--json"]))["kernelspecs"]

    wanted = sys.argv[1] if len(sys.argv) > 1 else None

    def is_match(name, info):
        if wanted:
            return name == wanted
        label = (name + " " + info["spec"]["display_name"]).lower()
        return "phaindia" in label and not name.endswith("-gpu")

    matches = [name for name, info in specs.items() if is_match(name, info)]
    if len(matches) != 1:
        print("Could not pick exactly one kernel. Available kernels:")
        for name, info in specs.items():
            print(f"  {name:30} {info['spec']['display_name']}")
        sys.exit("Run again with the kernel name: python3 make_gpu_kernel.py <kernel-name>")
    name = matches[0]
    resource_dir = Path(specs[name]["resource_dir"])
    # Copy the file itself, not the listing, which fills in defaults the original does not set
    spec = json.loads((resource_dir / "kernel.json").read_text())
    argv = list(spec["argv"])

    if "--nv" in argv:
        print(f"Kernel '{name}' already starts the container with --nv. Nothing to do.")
        return

    # Find the apptainer (or singularity) subcommand and put --nv right after it
    position = None
    for i, word in enumerate(argv[:-1]):
        if Path(word).name in ("apptainer", "singularity") and argv[i + 1] in APPTAINER_SUBCOMMANDS:
            position = i + 2
            break
    if position is None:
        print(f"Kernel '{name}' does not call apptainer directly. Its command is:")
        print("  " + " ".join(argv))
        sys.exit("Add --nv where that command (or the script it runs) starts apptainer, or ask your hub admin.")
    argv.insert(position, "--nv")

    new_name = f"{name}-gpu"
    target = Path.home() / ".local" / "share" / "jupyter" / "kernels" / new_name
    target.mkdir(parents=True, exist_ok=True)
    for item in resource_dir.iterdir():  # logos and any helper files
        if item.is_file() and item.name != "kernel.json":
            shutil.copy2(item, target / item.name)
    spec = dict(spec, argv=argv, display_name=f"{spec['display_name']} (GPU)")
    (target / "kernel.json").write_text(json.dumps(spec, indent=1) + "\n")

    print(f"Wrote {target / 'kernel.json'}")
    print("  " + " ".join(argv))
    print(f"Reload the notebook page and choose '{spec['display_name']}' from the kernel menu.")


if __name__ == "__main__":
    main()
