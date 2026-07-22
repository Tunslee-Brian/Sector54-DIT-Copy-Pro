import re
import os
from datetime import datetime

def format_date(dt: datetime = None, date_format: str = "YYMMDD") -> str:
    """
    Format a datetime object according to a date format string.
    Supports standard DIT formats: YYMMDD, DDMMYY, DDMMYYYY, YYYYMMDD, YYYY-MM-DD, etc.
    """
    if dt is None:
        dt = datetime.now()
    fmt = (date_format or "YYMMDD").upper().strip()
    if fmt in ("YYMMDD", "6"):
        return dt.strftime("%y%m%d")
    elif fmt in ("DDMMYY",):
        return dt.strftime("%d%m%y")
    elif fmt in ("DDMMYYYY", "8"):
        return dt.strftime("%d%m%Y")
    elif fmt in ("YYYYMMDD",):
        return dt.strftime("%Y%m%d")
    elif fmt in ("YYYY-MM-DD", "YYYY_MM_DD"):
        return dt.strftime("%Y-%m-%d")
    elif fmt in ("YY-MM-DD", "YY_MM_DD"):
        return dt.strftime("%y-%m-%d")
    else:
        try:
            return dt.strftime(date_format)
        except Exception:
            return dt.strftime("%y%m%d")


class TokenParser:
    """
    Token-based Naming Parser for camera card filenames.
    Converts rule patterns like '{Camera:1}{Roll:3}C{Clip:3}_{Date:YYMMDD}'
    into Regular Expressions to extract token values from filenames.
    """
    
    TOKEN_REGEX = re.compile(r'\{([A-Za-z0-9_]+)(?::([A-Za-z0-9_\-]+))?\}')

    def __init__(self, rule_pattern: str = "{Camera:1}{Roll:3}C{Clip:3}_{Date:8}", date_format: str = "YYMMDD"):
        self.rule_pattern = rule_pattern
        self.date_format = date_format
        self.regex, self.token_names = self._build_regex(rule_pattern)

    def _build_regex(self, pattern: str):
        token_names = []
        last_pos = 0
        regex_parts = ["^"]

        for match in self.TOKEN_REGEX.finditer(pattern):
            start, end = match.span()
            # Escape static text between tokens
            if start > last_pos:
                regex_parts.append(re.escape(pattern[last_pos:start]))

            token_name = match.group(1)
            length_str = match.group(2)
            token_names.append(token_name)

            if length_str:
                if length_str.isdigit():
                    length = int(length_str)
                    regex_parts.append(f"(?P<{token_name}>.{{{length}}})")
                elif token_name == "Date":
                    sample_d = format_date(datetime.now(), length_str)
                    regex_parts.append(f"(?P<{token_name}>.{{{len(sample_d)}}})")
                else:
                    regex_parts.append(f"(?P<{token_name}>[A-Za-z0-9_\\-]+)")
            else:
                regex_parts.append(f"(?P<{token_name}>[A-Za-z0-9_\\-]+)")

            last_pos = end

        if last_pos < len(pattern):
            regex_parts.append(re.escape(pattern[last_pos:]))

        # Optional extension at end
        regex_parts.append(r"(?:\.[A-Za-z0-9]+)?$")

        try:
            compiled_regex = re.compile("".join(regex_parts), re.IGNORECASE)
        except re.error:
            # Fallback if custom pattern regex compilation fails
            compiled_regex = re.compile(r"^(?P<Clip>.+?)(?:\.[A-Za-z0-9]+)?$", re.IGNORECASE)

        return compiled_regex, token_names

    def set_pattern(self, rule_pattern: str, date_format: str = None):
        self.rule_pattern = rule_pattern
        if date_format:
            self.date_format = date_format
        self.regex, self.token_names = self._build_regex(rule_pattern)

    def parse(self, filename: str, fallback_project: str = "Project", dt: datetime = None) -> dict:
        """
        Extracts token values from a given filename.
        Returns a dictionary of token_name -> value.
        """
        basename = os.path.basename(filename)
        name_without_ext, ext = os.path.splitext(basename)

        match = self.regex.match(basename) or self.regex.match(name_without_ext)

        result = {
            "Camera": "A",
            "Roll": "001",
            "Clip": name_without_ext,
            "Date": format_date(dt or datetime.now(), self.date_format),
            "Project": fallback_project,
            "Filename": basename,
            "Stem": name_without_ext,
            "Extension": ext.lstrip(".")
        }

        if match:
            group_dict = match.groupdict()
            for key, val in group_dict.items():
                if val is not None:
                    result[key] = val

        return result

