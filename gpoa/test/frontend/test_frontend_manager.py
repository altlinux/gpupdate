#
# GPOA - GPO Applier for Linux
#
# Copyright (C) 2026 BaseALT Ltd.
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

import ast
import os
import unittest


def _read_frontend_manager_ast():
    source_path = os.path.join(os.getcwd(), 'frontend', 'frontend_manager.py')
    with open(source_path, 'r', encoding='utf-8') as file_obj:
        source = file_obj.read()
    return ast.parse(source)


def _find_method(class_node, method_name):
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return node
    return None


def _has_call(node, function_name):
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if isinstance(child.func, ast.Name) and child.func.id == function_name:
            return True
        if isinstance(child.func, ast.Attribute) and child.func.attr == function_name:
            return True
    return False


def _find_stmt_index(statements, predicate):
    for index, statement in enumerate(statements):
        if predicate(statement):
            return index
    return None


class FrontendManagerOrderTestCase(unittest.TestCase):
    def test_machine_apply_primes_journal_after_reset_before_apply_loop(self):
        tree = _read_frontend_manager_ast()
        manager_class = next(node for node in tree.body
                             if isinstance(node, ast.ClassDef) and node.name == 'frontend_manager')
        method = _find_method(manager_class, 'machine_apply')
        self.assertIsNotNone(method)

        reset_index = _find_stmt_index(method.body, lambda stmt: _has_call(stmt, 'reset_change_journal'))
        prime_index = _find_stmt_index(method.body, lambda stmt: isinstance(stmt, ast.Try)
                                       and _has_call(stmt, 'prime_dependency_journal'))
        loop_index = _find_stmt_index(method.body, lambda stmt: isinstance(stmt, ast.For))

        self.assertIsNotNone(reset_index)
        self.assertIsNotNone(prime_index)
        self.assertIsNotNone(loop_index)
        self.assertLess(reset_index, prime_index)
        self.assertLess(prime_index, loop_index)

    def test_user_apply_primes_journal_after_reset_before_apply_branches(self):
        tree = _read_frontend_manager_ast()
        manager_class = next(node for node in tree.body
                             if isinstance(node, ast.ClassDef) and node.name == 'frontend_manager')
        method = _find_method(manager_class, 'user_apply')
        self.assertIsNotNone(method)

        reset_index = _find_stmt_index(method.body, lambda stmt: _has_call(stmt, 'reset_change_journal'))
        prime_index = _find_stmt_index(method.body, lambda stmt: isinstance(stmt, ast.Try)
                                       and _has_call(stmt, 'prime_dependency_journal'))
        branch_index = _find_stmt_index(method.body, lambda stmt: isinstance(stmt, ast.If))

        self.assertIsNotNone(reset_index)
        self.assertIsNotNone(prime_index)
        self.assertIsNotNone(branch_index)
        self.assertLess(reset_index, prime_index)
        self.assertLess(prime_index, branch_index)


if __name__ == '__main__':
    unittest.main()
