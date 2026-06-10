from pathlib import Path
from typing import Dict, Any, Optional

from codegraphcontext.cli.config_manager import get_config_value
from codegraphcontext.tools.tree_sitter_parser import TreeSitterParser
from codegraphcontext.utils.debug_log import error_logger
from codegraphcontext.tools.indexing.constants import PARSER_MAP, GENERIC_EXTENSIONS, GENERIC_FILENAMES

# Cache to store instantiated parsers within the current worker process
_PROCESS_PARSER_CACHE: Dict[str, TreeSitterParser] = {}


def get_parser_in_worker(ext: str) -> Optional[TreeSitterParser]:
    """Retrieves or instantiates a TreeSitterParser per process."""
    lang_name = PARSER_MAP.get(ext)
    if not lang_name:
        return None

    if lang_name not in _PROCESS_PARSER_CACHE:
        try:
            _PROCESS_PARSER_CACHE[lang_name] = TreeSitterParser(lang_name)
        except Exception as e:
            error_logger(f"Failed to instantiate parser for {lang_name} ({ext}): {e}")
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
    if ext in GENERIC_EXTENSIONS or path.name in GENERIC_FILENAMES:
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
