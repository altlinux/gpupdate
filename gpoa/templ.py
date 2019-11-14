from jinja2 import  Environment, PackageLoader, FileSystemLoader, StrictUndefined, select_autoescape

templateLoader = FileSystemLoader(searchpath="./templates")
env = Environment(loader=templateLoader, undefined=StrictUndefined)
template = env.get_template('printers.bash.j2')

print(template.render(printer_name="HP_via_script", printer_address="10.64.128.250", DEBUG=False))