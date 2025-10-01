# osrs-recolor-gui
Turning the recolorFrom and recolorTo values from the cache to useful rgb value

## Launching the GUI with a double-click

You no longer need to open a terminal each time you want to use the tool. Pick the launcher that matches your operating system and double-click it from your file explorer.

### Windows

1. Ensure Python 3 is installed and available through either the **Python Launcher** (`py`) or the regular `python` command.
2. Double-click `run_osrs_recolor_gui.bat`.
   * The script automatically changes into the project directory before launching `osrs_recolor_gui.py`.
   * If Python is not found you will see an error window—install Python and try again.

### macOS

1. Run `chmod +x run_osrs_recolor_gui.command` once (right-click → “Open With Terminal” also works the first time).
2. Double-click `run_osrs_recolor_gui.command` to start the GUI in a new Terminal window.

### Linux

1. Run `chmod +x run_osrs_recolor_gui.sh` to make the launcher executable.
2. Double-click `run_osrs_recolor_gui.sh` (choose **Run** if prompted) or create a desktop shortcut that executes the script.

## Finding NPC recolor data

You can quickly look up recolor data for any NPC and feed it into the GUI with the following workflow:

1. Open the raw NPC dump: <https://raw.githubusercontent.com/Joshua-F/osrs-dumps/refs/heads/master/config/dump.npc>.
   * Use your browser’s **Ctrl+F** search (or **⌘+F** on macOS) to locate the NPC by name. For example, searching for `varrock_guard02` jumps to the entry for that guard.
   * The NPC ID appears at the top of each entry immediately after the `//` comment.
2. Visit the cache viewer at <https://abextm.github.io/cache2/#/viewer/npc> and switch to the **NPC** tab.
   * Enter one or more NPC IDs separated by commas to load their data blocks.
   * Each block includes a `recolorTo` section along with other useful metadata.
3. Launch the OSRS Recolor GUI and paste the entire result block from the cache viewer for all of the NPC IDs you queried.
   * The GUI converts the values into the format expected by the OSBM API.
   * Adjust the comparator and threshold values as needed, then click **Copy Java Array** to export an array that includes the NPC name, comparator, and threshold you selected.
4. (Optional) In the **Visual Debug → Pixel Clusters** tab, use **Parse Array** to experiment with the resulting data.

> **Note:** It is unclear whether every `recolorTo` entry represents the complete set of HSL values for that NPC or only the values that the client swaps from `recolorFrom`. However, the workflow above has produced reliable results in practice.
