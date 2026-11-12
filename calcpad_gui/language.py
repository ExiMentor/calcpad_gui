"""Install the bundled GtkSource language only when the desktop starts."""
from .bootstrap import GtkSource
from .config import CALCPAD_LANG, LANG_DIR, LANG_FILE

def ensure_calcpad_language():
    try:
        if not LANG_FILE.exists():
            LANG_FILE.write_text(CALCPAD_LANG, encoding="utf-8")
        lm = GtkSource.LanguageManager.get_default()
        paths = list(lm.get_search_path() or [])
        if str(LANG_DIR) not in paths:
            paths.insert(0, str(LANG_DIR))
            lm.set_search_path(paths)
        return lm.get_language("calcpad") is not None
    except OSError:
        return False
