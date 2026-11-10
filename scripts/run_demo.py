from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ultron_2_0 import OrchestratorBridge


if __name__ == "__main__":
    bridge = OrchestratorBridge(ROOT.parent)
    print("BRIDGE STATUS")
    print(bridge.status())
    print("\nTOOLS:")
    for tool in bridge.tool_registry.list_contracts():
        print(f"- {tool.name}: {tool.description}")
