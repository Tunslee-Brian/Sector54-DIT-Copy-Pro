import os

class DirectoryBuilder:
    """
    Dynamic Directory Template Engine.
    Constructs output paths based on token templates for one or multiple destinations.
    """

    def __init__(self, template: str = "{Destination}/Footage/{Camera}/Roll_{Roll}/"):
        self.template = template

    def build_path_for_destination(self, destination_root: str, tokens: dict, filename: str) -> str:
        """
        Builds full destination file path for a single destination root.
        """
        context = dict(tokens)
        context["Destination"] = destination_root.rstrip("/\\")

        # Format template
        rel_or_abs = self.template
        for key, value in context.items():
            token_placeholder = f"{{{key}}}"
            rel_or_abs = rel_or_abs.replace(token_placeholder, str(value))

        # Clean trailing slashes and normalize path
        target_dir = os.path.normpath(rel_or_abs)
        target_filepath = os.path.join(target_dir, filename)
        return target_filepath

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
