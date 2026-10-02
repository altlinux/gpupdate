import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree

from tools.parsing_chrom_admx_intvalues import extract_integer_values, main


class AdmxIntegerValuesTest(unittest.TestCase):
    FIXTURE = '''<policyDefinitions>
      <policies>
        <policy name="DelayEditorName" key="Software\\Policies\\Browser">
          <elements><decimal id="Delay" valueName="BrowserDelay" /></elements>
        </policy>
        <policy name="ChoiceEditorName" valueName="BrowserChoice">
          <elements><enum id="Choice">
            <item><value><decimal value="0" /></value></item>
            <item><value><decimal value="1" /></value></item>
          </enum></elements>
        </policy>
        <policy name="Delay_recommended">
          <elements><decimal id="Delay" valueName="BrowserDelay" /></elements>
        </policy>
        <policy name="TwoNumbers">
          <elements>
            <decimal id="One" valueName="FirstNumber" />
            <decimal id="Two" valueName="SecondNumber" />
          </elements>
        </policy>
        <policy name="StringChoice">
          <elements><enum id="Text" valueName="TextMode">
            <item><value><string>enabled</string></value></item>
          </enum></elements>
        </policy>
        <policy name="Boolean" valueName="BooleanFlag">
          <enabledValue><decimal value="1" /></enabledValue>
          <disabledValue><decimal value="0" /></disabledValue>
        </policy>
        <policy name="BooleanElement">
          <elements><boolean id="Flag" valueName="AnotherBoolean">
            <trueValue><decimal value="1" /></trueValue>
          </boolean></elements>
        </policy>
        <policy name="Unmapped">
          <elements><decimal id="MissingValueName" /></elements>
        </policy>
      </policies>
    </policyDefinitions>'''

    def test_numeric_elements_use_registry_names_and_keep_boolean_semantics(self):
        for namespace in ('', 'urn:test:admx'):
            text = self.FIXTURE
            if namespace:
                text = text.replace('<policyDefinitions>',
                                    f'<policyDefinitions xmlns="{namespace}">')
            root = ElementTree.fromstring(text)
            original = ElementTree.tostring(root)
            self.assertEqual((['BrowserDelay', 'BrowserChoice',
                               'FirstNumber', 'SecondNumber'], 8),
                             extract_integer_values(root))
            self.assertEqual(original, ElementTree.tostring(root))

    def test_cli_output_and_error_status(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, 'browser.admx')
            path.write_text(self.FIXTURE)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(0, main([str(path)]))
            self.assertEqual("'BrowserDelay',\n'BrowserChoice',\n'FirstNumber',\n"
                             "'SecondNumber'\n\nkey_int: 4\ntotal: 8\n",
                             output.getvalue())
            for text in ('<broken>', ''):
                path.write_text(text)
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        main([str(path)])
                self.assertEqual(1, raised.exception.code)
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    main([str(Path(directory, 'missing.admx'))])
            self.assertEqual(1, raised.exception.code)
