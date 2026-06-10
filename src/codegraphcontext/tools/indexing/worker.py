from pathlib import Path
from typing import Dict, Any, Optional

from codegraphcontext.cli.config_manager import get_config_value
from codegraphcontext.tools.tree_sitter_parser import TreeSitterParser

# Parsers mapped by file extension
_PARSER_MAP = {
    ".py": "python",
    ".ipynb": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".d.ts": "typescript",
    ".tsx": "tsx",
    ".cpp": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".rs": "rust",
    ".c": "c",
    ".java": "java",
    ".rb": "ruby",
    ".cs": "c_sharp",
    ".php": "php",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sc": "scala",
    ".swift": "swift",
    ".hs": "haskell",
    ".dart": "dart",
    ".pl": "perl",
    ".pm": "perl",
    ".lua": "lua",
    ".ex": "elixir",
    ".exs": "elixir",
    ".el": "elisp",
    ".html": "html",
    ".css": "css",
}

# Generic extensions that shouldn't be parsed with Tree-sitter but still get File nodes
_GENERIC_EXTS = {
    ".toml", ".sh", ".yaml", ".yml", ".json", ".ini", ".cfg", ".md", ".txt", ".env",
    ".bat", ".ps1", ".dockerignore", ".gitignore"
}
_GENERIC_NAMES = {"Dockerfile", "Makefile"}

# Cache to store instantiated parsers within the current worker process
_PROCESS_PARSER_CACHE: Dict[str, TreeSitterParser] = {}


def get_parser_in_worker(ext: str) -> Optional[TreeSitterParser]:
    """Retrieves or instantiates a TreeSitterParser per process."""
    lang_name = _PARSER_MAP.get(ext)
    if not lang_name:
        return None

    if lang_name not in _PROCESS_PARSER_CACHE:
        try:
            _PROCESS_PARSER_CACHE[lang_name] = TreeSitterParser(lang_name)
        except Exception:
            return None
    return _PROCESS_PARSER_CACHE[lang_name]


def worker_parse_file(repo_path_str: str, file_path_str: str, is_dependency: bool) -> Dict[str, Any]:
    """
    Stateless worker function for ProcessPoolExecutor.
    Receives scalar arguments, parses the AST, and returns a JSON-serializable dict.
    """
    repo_path = Path(repo_path_str)
    path = Path(file_path_str)
    
    ext = path.suffix
    if path.name.endswith(".d.ts"):
        ext = ".d.ts"

    # Handle unparsed but known files
    if ext in _GENERIC_EXTS or path.name in _GENERIC_NAMES:
        return {"path": str(path), "error": f"Generic file type {ext or path.name}", "unsupported": False}

    parser = get_parser_in_worker(ext)
    if not parser:
        return {"path": str(path), "error": f"No parser for {ext}", "unsupported": True}

    try:
        index_source = (get_config_value("INDEX_SOURCE") or "false").lower() == "true"
        if parser.language_name == "python":
            is_notebook = path.suffix == ".ipynb"
            file_data = parser.parse(
                path,
                is_dependency,
                is_notebook=is_notebook,
                index_source=index_source,
            )
        else:
            file_data = parser.parse(path, is_dependency, index_source=index_source)
            
        file_data["repo_path"] = str(repo_path)
        return file_data
    except Exception as e:
        return {"path": str(path), "error": str(e)}
