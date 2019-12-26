from gi.repository import Gio, GLib

class system_gsetting:
    def __init__(self, schema, path, value):
        self.schema = schema
        self.path = path
        self.value = GLib.Variant('as', value)

    def apply(self):
        variants = gso.get_property(self.path)
        if (variants.has_key(self.path)):
            key = variants.get_key(self.path)
            print(key.get_range())

class user_gsetting:
    def __init__(self, schema, path, value):
        self.schema = schema
        self.path = path
        self.value = value

    def apply(self):
        gso = Gio.Settings.new(seVlf.schema)
        variants = gso.get_property(self.path)
        if (variants.has_key(self.path)):
            key = variants.get_key(self.path)
            print(key.get_range())

