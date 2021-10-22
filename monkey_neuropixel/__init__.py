from pathlib import Path

base_path = Path.cwd() / Path(__file__).parent

brain_location_path = base_path / "data/brain_location_map.json"

metadata_location_path = base_path / "data/metadata.json"
