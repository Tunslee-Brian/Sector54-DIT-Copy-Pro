import os
import json
from typing import List, Dict, Optional

from core.path_utils import get_preset_dir
from core.logger_config import logger

DEFAULT_PRESETS = [
    {
        "name": "ARRI ALEXA Standard",
        "naming_rule": "{Camera:1}{Roll:3}C{Clip:3}_{Date:YYMMDD}",
        "folder_template": "{Destination}/Footage/{Camera}/Roll_{Roll}/",
        "date_format": "YYMMDD",
        "hash_algorithm": "MD5",
        "log_format": "TXT",
        "buffer_size_mb": 64,
        "file_extension_blacklist": [],
        "suppress_output_reports": False
    },
    {
        "name": "RED V-RAPTOR Cinema",
        "naming_rule": "{Camera:1}{Roll:3}_{Clip:3}_{Date:YYMMDD}",
        "folder_template": "{Destination}/{Date}/{Project}/CAM_{Camera}/",
        "date_format": "YYMMDD",
        "hash_algorithm": "XXHash64",
        "log_format": "TXT",
        "buffer_size_mb": 64,
        "file_extension_blacklist": [],
        "suppress_output_reports": False
    },
    {
        "name": "Sony FX6 / FX9 Standard",
        "naming_rule": "{Camera:1}{Roll:3}C{Clip:3}",
        "folder_template": "{Destination}/Footage/{Camera}/Roll_{Roll}/",
        "date_format": "YYMMDD",
        "hash_algorithm": "MD5",
        "log_format": "TXT",
        "buffer_size_mb": 32,
        "file_extension_blacklist": [],
        "suppress_output_reports": False
    },
    {
        "name": "Fast Size-Only Copy",
        "naming_rule": "{Camera:1}{Roll:3}C{Clip:3}",
        "folder_template": "{Destination}/Footage/{Camera}/",
        "date_format": "YYMMDD",
        "hash_algorithm": "Size-only",
        "log_format": "TXT",
        "buffer_size_mb": 64,
        "file_extension_blacklist": [],
        "suppress_output_reports": False
    }
]


class PresetManager:
    """
    Manages loading, saving, and storing configuration Presets.
    """

    def __init__(self, preset_dir: str = None):
        if not preset_dir:
            preset_dir = get_preset_dir()
        self.preset_dir = os.path.abspath(preset_dir)
        os.makedirs(self.preset_dir, exist_ok=True)
        self._ensure_defaults()

    def _ensure_defaults(self):
        marker_file = os.path.join(self.preset_dir, ".initialized")
        has_presets = any(fname.endswith(".json") for fname in os.listdir(self.preset_dir)) if os.path.exists(self.preset_dir) else False
        if os.path.exists(marker_file) and has_presets:
            return

        for p in DEFAULT_PRESETS:
            filepath = os.path.join(self.preset_dir, f"{self._sanitize_filename(p['name'])}.json")
            if not os.path.exists(filepath):
                self.save_preset(p)

        try:
            with open(marker_file, "w", encoding="utf-8") as f:
                f.write("initialized")
        except Exception as e:
            logger.warning(f"Failed to create preset marker file: {e}")

    def _sanitize_filename(self, name: str) -> str:
        return "".join([c if c.isalnum() or c in (" ", "_", "-") else "_" for c in name]).strip()

    def list_presets(self) -> List[str]:
        presets = []
        if os.path.exists(self.preset_dir):
            for fname in sorted(os.listdir(self.preset_dir)):
                if fname.endswith(".json"):
                    filepath = os.path.join(self.preset_dir, fname)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, dict) and "name" in data:
                                presets.append(data["name"])
                                continue
                    except Exception:
                        pass
                    presets.append(fname[:-5])
        return presets


    def load_preset(self, name: str) -> Optional[Dict]:
        fname = f"{self._sanitize_filename(name)}.json"
        filepath = os.path.join(self.preset_dir, fname)
        if not os.path.exists(filepath):
            # Try matching raw filename
            filepath = os.path.join(self.preset_dir, f"{name}.json")

        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load preset {name}: {e}")
        return None

    def save_preset(self, preset_data: Dict, old_name: Optional[str] = None) -> bool:
        name = preset_data.get("name", "Untitled")
        fname = f"{self._sanitize_filename(name)}.json"
        filepath = os.path.join(self.preset_dir, fname)

        # Write new file first, then delete old one to prevent data loss
        old_filepath = None
        if old_name and old_name != name:
            old_fname = f"{self._sanitize_filename(old_name)}.json"
            old_filepath = os.path.join(self.preset_dir, old_fname)
            if not os.path.exists(old_filepath):
                old_filepath = os.path.join(self.preset_dir, f"{old_name}.json")
                if not os.path.exists(old_filepath):
                    old_filepath = None

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(preset_data, f, indent=2, ensure_ascii=False)
            # Only delete old file after new file is successfully written
            if old_filepath and old_filepath != filepath:
                try:
                    os.remove(old_filepath)
                except Exception as e:
                    logger.debug(f"Failed to remove old preset file {old_filepath}: {e}")
            return True
        except Exception as e:
            logger.error(f"Failed to save preset {name}: {e}")
            return False

    def delete_preset(self, name: str) -> bool:
        fname = f"{self._sanitize_filename(name)}.json"
        filepath = os.path.join(self.preset_dir, fname)
        if not os.path.exists(filepath):
            filepath = os.path.join(self.preset_dir, f"{name}.json")

        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                return True
            except Exception as e:
                logger.error(f"Failed to delete preset {name}: {e}")
        return False

    def export_preset(self, name: str, export_path: str) -> bool:
        """Exports an existing preset to an external JSON file path."""
        preset_data = self.load_preset(name)
        if not preset_data:
            return False
        try:
            export_dir = os.path.dirname(os.path.abspath(export_path))
            if export_dir:
                os.makedirs(export_dir, exist_ok=True)
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(preset_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to export preset {name} to {export_path}: {e}")
            return False

    def import_preset(self, source_path: str) -> Optional[Dict]:
        """Imports a preset from an external JSON file path into the preset directory."""
        if not source_path or not os.path.exists(source_path):
            return None
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                preset_data = json.load(f)
            if not isinstance(preset_data, dict) or "name" not in preset_data:
                return None
            if self.save_preset(preset_data):
                return preset_data
        except Exception as e:
            logger.error(f"Failed to import preset from {source_path}: {e}")
        return None


