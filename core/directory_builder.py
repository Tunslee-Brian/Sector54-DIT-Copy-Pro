import os
import re

class DirectoryBuilder:
    """
    Dynamic Directory Template Engine.
    Constructs output paths based on token templates for one or multiple destinations.
    """

    def __init__(self, template: str = "{Destination}/Footage/{Camera}/Roll_{Roll}/"):
        self.template = template

    def build_path_for_destination(self, destination_root: str, tokens: dict, filename: str) -> str:
        """
        Builds full destination file path for a single destination root with path traversal protections.
        """
        dest_clean = os.path.realpath(destination_root)

        # Sanitize token values to prevent path traversal via token injection
        context = {}
        for key, value in tokens.items():
            val_str = str(value)
            # Replace any sequence of 2 or more dots with a single underscore to block all variations of ..
            val_str = re.sub(r'\.{2,}', '_', val_str)
            val_str = val_str.replace("/", "_").replace("\\", "_")
            context[key] = val_str
        context["Destination"] = dest_clean.rstrip("/\\")

        # Format template
        rel_or_abs = self.template
        for key, value in context.items():
            token_placeholder = f"{{{key}}}"
            rel_or_abs = rel_or_abs.replace(token_placeholder, str(value))

        # Clean trailing slashes and normalize path
        safe_filename = os.path.basename(filename)
        target_dir = os.path.normpath(rel_or_abs)
        target_filepath = os.path.normpath(os.path.join(target_dir, safe_filename))
        abs_target = os.path.realpath(target_filepath)

        # Validate that the target file path resides strictly inside destination_root
        try:
            dest_norm = os.path.normcase(dest_clean)
            target_norm = os.path.normcase(abs_target)
            if os.path.commonpath([dest_norm, target_norm]) != dest_norm:
                raise ValueError(f"Path traversal attempt detected: {abs_target} is outside {dest_clean}")
        except Exception as e:
            if isinstance(e, ValueError):
                raise e
            raise ValueError(f"Invalid path traversal: {abs_target}")

        return abs_target

    def build_paths_for_all_destinations(self, destinations: list[str], tokens: dict, filename: str) -> list[str]:
        """
        Builds full target file paths for all provided destination roots.
        """
        target_paths = []
        for dest in destinations:
            if dest and dest.strip():
                filepath = self.build_path_for_destination(dest.strip(), tokens, filename)
                target_paths.append(filepath)
        return target_paths

    def ensure_directory_exists(self, filepath: str):
        """
        Ensures target parent directory exists before writing file.
        """
        directory = os.path.dirname(filepath)
        if directory:
            os.makedirs(directory, exist_ok=True)
