#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2023 BaseALT Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from configobj import (ConfigObj, NestingError, Section,
                        DuplicateError, ParseError, UnreprError,
                        UnknownType,UnreprError,
                        BOM_UTF8, DEFAULT_INDENT_TYPE, BOM_LIST,
                        match_utf8, unrepr)
import six
import re
import sys
import os

# Michael Foord: fuzzyman AT voidspace DOT org DOT uk
# Nicola Larosa: nico AT tekNico DOT net
# Rob Dennis: rdennis AT gmail DOT com
# Eli Courtwright: eli AT courtwright DOT org
# This class based on the ConfigObj module, distributed under the BSD-3-Clause license.
# This class includes modified code from the ConfigObj module mentioned above.
# The original authors and their contact information are listed in the comments above.
# For more information about ConfigObj, please visit the main repository:
# https://github.com/DiffSK/configobj


class GpoaConfigObj(ConfigObj):

    _sectionmarker = re.compile(r'''^
        (\s*)                     # 1: indentation
        ((?:\[\s*)+)              # 2: section marker open
        (                         # 3: section name open
            (?:"\s*\S.*?\s*")|    # at least one non-space with double quotes
            (?:'\s*\S.*?\s*')|    # at least one non-space with single quotes
            (?:[^'"\s].*?)        # at least one non-space unquoted
        )                         # section name close
        ((?:\s*\])+)              # 4: section marker close
        (\s*(?:[#;].*)?)?           # 5: optional comment
        $''',
        re.VERBOSE)

    _valueexp = re.compile(r'''^
        (?:
            (?:
                (
                    (?:
                        (?:
                            (?:".*?")|              # double quotes
                            (?:'.*?')|              # single quotes
                            (?:[^'",\#][^,\#]*?)    # unquoted
                        )
                        \s*,\s*                     # comma
                    )*      # match all list items ending in a comma (if any)
                )
                (
                    (?:".*?")|                      # double quotes
                    (?:'.*?')|                      # single quotes
                    (?:[^'",\#\s][^,]*?)|           # unquoted
                    (?:(?<!,))                      # Empty value
                )?          # last item in a list - or string value
            )|
            (,)             # alternatively a single comma - empty list
        )
        (\s*(?:[#;].*)?)?     # optional comment
        $''',
        re.VERBOSE)

    COMMENT_MARKERS = ['#', ';']

    def _handle_comment(self, comment):
        """Deal with a comment."""
        if not comment:
            return ''
        start = self.indent_type
        if not comment.lstrip().startswith(tuple(self.COMMENT_MARKERS)):
            start += ' # '
        return start + comment.strip()

    def _parse(self, infile):
        """Actually parse the config file."""
        temp_list_values = self.list_values
        if self.unrepr:
            self.list_values = False

        comment_list = []
        done_start = False
        this_section = self
        maxline = len(infile) - 1
        cur_index = -1
        reset_comment = False
        comment_markers = tuple(self.COMMENT_MARKERS)

        while cur_index < maxline:
            if reset_comment:
                comment_list = []
            cur_index += 1
            line = infile[cur_index]
            sline = line.strip()
            # do we have anything on the line ?
            if not sline or sline.startswith(comment_markers):
                reset_comment = False
                comment_list.append(line)
                continue

            if not done_start:
                # preserve initial comment
                self.initial_comment = comment_list
                comment_list = []
                done_start = True

            reset_comment = True
            # first we check if it's a section marker
            mat = self._sectionmarker.match(line)
            if mat is not None:
                # is a section line
                (indent, sect_open, sect_name, sect_close, comment) = mat.groups()
                if indent and (self.indent_type is None):
                    self.indent_type = indent
                cur_depth = sect_open.count('[')
                if cur_depth != sect_close.count(']'):
                    self._handle_error("Cannot compute the section depth",
                                       NestingError, infile, cur_index)
                    continue

                if cur_depth < this_section.depth:
                    # the new section is dropping back to a previous level
                    try:
                        parent = self._match_depth(this_section,
                                                   cur_depth).parent
                    except SyntaxError:
                        self._handle_error("Cannot compute nesting level",
                                           NestingError, infile, cur_index)
                        continue
                elif cur_depth == this_section.depth:
                    # the new section is a sibling of the current section
                    parent = this_section.parent
                elif cur_depth == this_section.depth + 1:
                    # the new section is a child the current section
                    parent = this_section
                else:
                    self._handle_error("Section too nested",
                                       NestingError, infile, cur_index)
                    continue

                sect_name = self._unquote(sect_name)
                if sect_name in parent:
                    self._handle_error('Duplicate section name',
                                       DuplicateError, infile, cur_index)
                    continue

                # create the new section
                this_section = Section(
                    parent,
                    cur_depth,
                    self,
                    name=sect_name)
                parent[sect_name] = this_section
                parent.inline_comments[sect_name] = comment
                parent.comments[sect_name] = comment_list
                continue
            #
            # it's not a section marker,
            # so it should be a valid ``key = value`` line
            mat = self._keyword.match(line)
            if mat is None:
                self._handle_error(
                    'Invalid line ({!r}) (matched as neither section nor keyword)'.format(line),
                    ParseError, infile, cur_index)
            else:
                # is a keyword value
                # value will include any inline comment
                (indent, key, value) = mat.groups()
                if indent and (self.indent_type is None):
                    self.indent_type = indent
                # check for a multiline value
                if value[:3] in ['"""', "'''"]:
                    try:
                        value, comment, cur_index = self._multiline(
                            value, infile, cur_index, maxline)
                    except SyntaxError:
                        self._handle_error(
                            'Parse error in multiline value',
                            ParseError, infile, cur_index)
                        continue
                    else:
                        if self.unrepr:
                            comment = ''
                            try:
                                value = unrepr(value)
                            except Exception as cause:
                                if isinstance(cause, UnknownType):
                                    msg = 'Unknown name or type in value'
                                else:
                                    msg = 'Parse error from unrepr-ing multiline value'
                                self._handle_error(msg, UnreprError, infile, cur_index)
                                continue
                else:
                    if self.unrepr:
                        comment = ''
                        try:
                            value = unrepr(value)
                        except Exception as cause:
                            if isinstance(cause, UnknownType):
                                msg = 'Unknown name or type in value'
                            else:
                                msg = 'Parse error from unrepr-ing value'
                            self._handle_error(msg, UnreprError, infile, cur_index)
                            continue
                    else:
                        # extract comment and lists
                        try:
                            (value, comment) = self._handle_value(value)
                        except SyntaxError:
                            self._handle_error(
                                'Parse error in value',
                                ParseError, infile, cur_index)
                            continue
                #
                key = self._unquote(key)
                if key in this_section:
                    self._handle_error(
                        'Duplicate keyword name',
                        DuplicateError, infile, cur_index)
                    continue
                # add the key.
                # we set unrepr because if we have got this far we will never
                # be creating a new section
                this_section.__setitem__(key, value, unrepr=True)
                this_section.inline_comments[key] = comment
                this_section.comments[key] = comment_list
                continue
        #
        if self.indent_type is None:
            # no indentation used, set the type accordingly
            self.indent_type = ''

        # preserve the final comment
        if not self and not self.initial_comment:
            self.initial_comment = comment_list
        elif not reset_comment:
            self.final_comment = comment_list
        self.list_values = temp_list_values


    def write(self, outfile=None, section=None):
        if self.indent_type is None:
            # this can be true if initialised from a dictionary
            self.indent_type = DEFAULT_INDENT_TYPE

        out = []
        comment_markers = tuple(self.COMMENT_MARKERS)
        comment_marker_default = comment_markers[0] + ' '
        if section is None:
            int_val = self.interpolation
            self.interpolation = False
            section = self
            for line in self.initial_comment:
                line = self._decode_element(line)
                stripped_line = line.strip()
                if stripped_line and not stripped_line.startswith(comment_markers):
                    line = comment_marker_default + line
                out.append(line)

        indent_string = self.indent_type * section.depth
        for entry in (section.scalars + section.sections):
            if entry in section.defaults:
                # don't write out default values
                continue
            for comment_line in section.comments[entry]:
                comment_line = self._decode_element(comment_line.lstrip())
                if comment_line and not comment_line.startswith(comment_markers):
                    comment_line = comment_marker_default + comment_line
                out.append(indent_string + comment_line)
            this_entry = section[entry]
            comment = self._handle_comment(section.inline_comments[entry])

            if isinstance(this_entry, Section):
                # a section
                out.append(self._write_marker(
                    indent_string,
                    this_entry.depth,
                    entry,
                    comment))
                out.extend(self.write(section=this_entry))
            else:
                out.append(self._write_line(
                    indent_string,
                    entry,
                    this_entry,
                    comment))

        if section is self:
            for line in self.final_comment:
                line = self._decode_element(line)
                stripped_line = line.strip()
                if stripped_line and not stripped_line.startswith(comment_markers):
                    line = comment_marker_default + line
                out.append(line)
            self.interpolation = int_val

        if section is not self:
            return out

        if (self.filename is None) and (outfile is None):
            # output a list of lines
            # might need to encode
            # NOTE: This will *screw* UTF16, each line will start with the BOM
            if self.encoding:
                out = [l.encode(self.encoding) for l in out]
            if (self.BOM and ((self.encoding is None) or
                (BOM_LIST.get(self.encoding.lower()) == 'utf_8'))):
                # Add the UTF8 BOM
                if not out:
                    out.append('')
                out[0] = BOM_UTF8 + out[0]
            return out

        # Turn the list to a string, joined with correct newlines
        newline = self.newlines or os.linesep
        if (getattr(outfile, 'mode', None) is not None and outfile.mode == 'w'
            and sys.platform == 'win32' and newline == '\r\n'):
            # Windows specific hack to avoid writing '\r\r\n'
            newline = '\n'
        output = newline.join(out)
        if not output.endswith(newline):
            output += newline

        if isinstance(output, six.binary_type):
            output_bytes = output
        else:
            output_bytes = output.encode(self.encoding or
                                         self.default_encoding or
                                         'ascii')

        if self.BOM and ((self.encoding is None) or match_utf8(self.encoding)):
            # Add the UTF8 BOM
            output_bytes = BOM_UTF8 + output_bytes

        if outfile is not None:
            outfile.write(output_bytes)
        else:
            with open(self.filename, 'wb') as h:
                h.write(output_bytes)
