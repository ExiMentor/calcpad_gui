@@
         self._autocomplete_popover = Gtk.Popover()
         self._autocomplete_popover.set_parent(self.editor)
-        self._autocomplete_popover.set_autohide(False)
+        self._autocomplete_popover.set_autohide(True)
@@
     def _on_autocomplete_key_pressed(self, controller, keyval, keycode, state):
         if not getattr(self, "_autocomplete_popover", None):
             return False
 
         if not self._autocomplete_popover.get_visible():
             return False
 
         if keyval == Gdk.KEY_Escape:
-            self._autocomplete_popover.popdown()
+            self._hide_autocomplete_popover()
             return True
@@
         if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
-            self._autocomplete_popover.popdown()
+            self._hide_autocomplete_popover()
             return False
 
         return False
+
+    def _hide_autocomplete_popover(self):
+        self._autocomplete_prefix = ""
+        self._autocomplete_suggestions = []
+        self._autocomplete_index = 0
+        if self._autocomplete_popover.get_visible():
+            self._autocomplete_popover.popdown()
 
     def _update_autocomplete(self):
         self._autocomplete_update_id = 0
 
         try:
             if not self.editor.has_focus():
-                self._autocomplete_popover.popdown()
+                self._hide_autocomplete_popover()
                 return False
         except Exception:
             pass
 
         prefix = self._get_autocomplete_prefix()
 
         if len(prefix) < 2:
-            self._autocomplete_popover.popdown()
+            self._hide_autocomplete_popover()
             return False
 
         suggestions = self._get_autocomplete_suggestions(prefix)
 
         if not suggestions:
-            self._autocomplete_popover.popdown()
+            self._hide_autocomplete_popover()
             return False
@@
         self._autocomplete_suppress_once = True
 
         self.buffer.begin_user_action()
         self.buffer.delete(start, cursor)
         self.buffer.insert(start, suggestion)
         self.buffer.end_user_action()
 
-        self._autocomplete_popover.popdown()
+        self._hide_autocomplete_popover()
