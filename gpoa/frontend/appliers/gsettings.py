from gi.repository import Gio, GLib

class system_gsetting:
    def __init__(self, schema, path, value):
        self.schema = schema
        self.path = path
        self.value = value

    def apply(self):
        pass
        #source = Gio.SettingsSchemaSource.get_default()
        #schema = source.lookup(self.schema, True)
        #key = schema.get_key(self.path)
        #gvformat = key.get_value_type()
        #val = GLib.Variant(gvformat.dup_string(), self.value)
        #schema.set_value(self.path, val)

        #variants = gso.get_property(self.path)
        #if (variants.has_key(self.path)):
        #    key = variants.get_key(self.path)
        #    print(key.get_range())

class user_gsetting:
    def __init__(self, schema, path, value):
        self.schema = schema
        self.path = path
        self.value = value

    def apply(self):
        source = Gio.SettingsSchemaSource.get_default()
        schema = source.lookup(self.schema, True)
        key = schema.get_key(self.path)
        gvformat = key.get_value_type()
        val = GLib.Variant(gvformat.dup_string(), self.value)
        schema.set_value(self.path, val)
        #gso = Gio.Settings.new(self.schema)
        #variants = gso.get_property(self.path)
        #if (variants.has_key(self.path)):
        #    key = variants.get_key(self.path)
        #    print(key.get_range())

