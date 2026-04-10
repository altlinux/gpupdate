#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2019-2025 BaseALT Ltd.
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

from .dynamic_attributes import DynamicAttributes

class Filter(DynamicAttributes):
    """
    Filter element for targeting preferences.

    Attributes:
        filter_type (str): XML tag name (e.g., 'FilterComputer', 'filterBattery')
        bool (str): Logical operator 'AND' or 'OR' for combining with other filters
        negate (bool): Whether to negate the filter (0/1 as string or bool)
        Other attributes: any attributes from XML (speedMHz, name, userContext, type, etc.)
    """
    # Fields to exclude from serialization
    _ignore_fields = {'filters', 'policy_name', 'filter_type'}

    def __init__(self, filter_type=None, **kwargs):
        # Rename 'not' attribute to 'negate' to avoid Python keyword conflict
        processed_kwargs = dict(kwargs)
        if 'not' in processed_kwargs:
            # 'not' attribute from XML is always string '0' or '1'
            processed_kwargs['negate'] = processed_kwargs.pop('not') == '1'
        elif 'negate' in processed_kwargs:
            # negate might be bool, string '0'/'1', or other string
            negate_val = processed_kwargs['negate']
            if isinstance(negate_val, bool):
                # Already bool, keep as is
                pass
            elif isinstance(negate_val, str):
                processed_kwargs['negate'] = negate_val == '1'
            else:
                # Convert to bool (e.g., int 0/1)
                processed_kwargs['negate'] = bool(negate_val)

        super().__init__(**processed_kwargs)

        # Store filter type (XML tag name)
        if filter_type:
            self.filter_type = filter_type
        else:
            self.filter_type = ''

        # Ensure mandatory attributes have default values
        if not hasattr(self, 'bool'):
            self.bool = 'AND'
        if not hasattr(self, 'negate'):
            self.negate = False

    def items(self):
        return ((k, v) for k, v in super().items() if k not in self._ignore_fields)

    def __iter__(self):
        # Return iterator for dict conversion: {filter_type: {attributes}}
        if not self.filter_type:
            # Fallback to regular items if filter_type not set
            return iter(self.items())
        # Create attributes dict without filter_type
        attrs = dict(self.items())
        return iter([(self.filter_type, attrs)])

def parse_filters(parent_element):
    """
    Parse <Filters> section from XML element.

    Args:
        parent_element: XML element that may contain <Filters> child

    Returns:
        list: List of Filter objects, empty if no filters found
    """
    filters = []
    filters_elem = parent_element.find('Filters')

    if filters_elem is not None:
        for filter_elem in filters_elem:
            # Pass all attributes as-is, Filter.__init__ will handle conversion
            attrs = dict(filter_elem.attrib)
            tag = filter_elem.tag
            filter_obj = Filter(filter_type=tag, **attrs)
            filters.append(filter_obj)

    return filters