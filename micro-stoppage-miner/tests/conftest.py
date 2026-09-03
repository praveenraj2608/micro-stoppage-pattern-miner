import sys
from pathlib import Path

# Make the project root importable (so `import src...` works under pytest).
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
