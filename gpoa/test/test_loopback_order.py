import unittest
from types import SimpleNamespace
from backend.samba_backend import effective_user_gpts


class LoopbackOrderTests(unittest.TestCase):
    def test_shared_policy_keeps_later_precedence_without_duplicate_actions(self):
        a = SimpleNamespace(path='A', value=1)
        b = SimpleNamespace(path='B', value=2)
        for mode, expected in ((0, [a, b]), (1, [b, a]), (2, [a])):
            chain = effective_user_gpts([a, b], [a], mode)
            self.assertEqual(chain, expected)
            self.assertEqual(chain[-1].value, 2 if mode == 0 else 1)
            self.assertEqual(len(chain), len({p.path for p in chain}))

    def test_disjoint_chains_keep_normal_loopback_order(self):
        a, b = SimpleNamespace(path='A'), SimpleNamespace(path='B')
        self.assertEqual(effective_user_gpts([a], [b], 1), [a, b])
        self.assertEqual(effective_user_gpts([a], [b], 2), [b])
