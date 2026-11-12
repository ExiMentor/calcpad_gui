"""Explicit test-only GI doubles, not substitutes for desktop validation."""
from __future__ import annotations
import contextlib
import html
import json
import os
from pathlib import Path
import sys
import tempfile
import types
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / '.test-work'


@contextlib.contextmanager
def isolated_directory():
    """Keep test filesystem operations inside the extracted project."""
    SCRATCH.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
        yield Path(directory)
    try:
        SCRATCH.rmdir()
    except OSError:
        pass


class Widget:
    """Record connected callbacks without implementing GTK layout."""
    widgets = []

    def __init__(self, *args, **kwargs):
        self.signals = []
        self.actions = {}
        self.values = kwargs
        self.widgets.append(self)

    @classmethod
    def new(cls, *args, **kwargs):
        return cls(*args, **kwargs)

    new_with_range = new
    new_from_icon_name = new
    parse_string = new

    def connect(self, signal, callback, *args):
        self.signals.append((signal, callback, args))

    def add_action(self, action):
        self.actions[action.values.get('name', '')] = action

    def lookup_action(self, name):
        return self.actions.get(name)

    def __getattr__(self, name):
        return Mock(name=name)


class Application(Widget):
    def run(self, argv):
        print('TEST_GI_RUN ' + json.dumps(argv))
        return 0


def install_gi(config: Path, data: Path, *, gtk_version=(4, 10)):
    """Install doubles before importing desktop modules; never use real GI."""
    gi = types.ModuleType('gi')
    gi.require_version = Mock()
    repository = types.ModuleType('gi.repository')
    gtk = Mock()
    gtk.Application = Application
    gtk.ApplicationWindow = Widget
    gtk.get_major_version.return_value = gtk_version[0]
    gtk.get_minor_version.return_value = gtk_version[1]
    gtk.get_micro_version.return_value = 0
    for name in ('HeaderBar', 'Button', 'MenuButton', 'ToggleButton', 'Separator',
                 'SpinButton', 'AlertDialog', 'FileDialog', 'FileFilter',
                 'ShortcutController', 'ShortcutTrigger', 'CallbackAction',
                 'Shortcut', 'GestureClick', 'Image'):
        setattr(gtk, name, type(name, (Widget,), {}))
    gtk.Image.new_from_file = Mock(return_value=Widget())
    glib = Mock()
    glib.get_user_config_dir.return_value = str(config)
    glib.get_user_data_dir.return_value = str(data)
    glib.markup_escape_text = lambda text: html.escape(text, quote=False).replace("'", '&apos;')
    glib.path_get_basename = os.path.basename
    glib.Error = type('GLibError', (Exception,), {})
    gio = Mock()
    gio.ApplicationFlags.HANDLES_OPEN = 1
    gio.ApplicationFlags.NON_UNIQUE = 2
    for name in ('Menu', 'SimpleAction', 'ListStore'):
        setattr(gio, name, type(name, (Widget,), {}))
    gio.SimpleAction.new = lambda name, parameter: Widget(name=name)
    gdk = Mock()
    gdk.ModifierType.CONTROL_MASK = 4
    gdk.ModifierType.SHIFT_MASK = 1
    source = Mock(MAJOR_VERSION=5, MINOR_VERSION=0)
    for name, value in [('Gtk', gtk), ('GLib', glib), ('Gio', gio), ('Gdk', gdk),
                        ('GtkSource', source), ('WebKit', Mock())]:
        setattr(repository, name, value)
    sys.modules['gi'] = gi
    sys.modules['gi.repository'] = repository
    return repository
