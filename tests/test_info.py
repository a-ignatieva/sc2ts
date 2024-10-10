import inspect

import pytest
import numpy as np
import pandas as pd
import matplotlib

import msprime
import tskit

from sc2ts import info


@pytest.fixture
def fx_ti_2020_02_13(fx_ts_map):
    ts = fx_ts_map["2020-02-13"]
    return info.TreeInfo(ts, show_progress=False)


class TestTallyLineages:

    def test_last_date(self, fx_ts_map, fx_metadata_db):
        date = "2020-02-13"
        df = info.tally_lineages(fx_ts_map[date], fx_metadata_db)
        assert list(df["pango"]) == [
            "B",
            "A",
            "B.1",
            "B.40",
            "B.33",
            "B.4",
            "A.5",
            "B.1.177",
            "B.1.36.29",
        ]
        assert list(df["db_count"]) == [26, 15, 4, 4, 1, 3, 1, 1, 1]
        assert list(df["arg_count"]) == [23, 15, 4, 3, 1, 1, 0, 0, 0]


class TestCountMutations:
    def test_1tree_0mut(self):
        # 2.00┊    6    ┊
        #     ┊  ┏━┻━┓  ┊
        # 1.00┊  4   5  ┊
        #     ┊ ┏┻┓ ┏┻┓ ┊
        # 0.00┊ 0 1 2 3 ┊
        #     0         1
        ts = tskit.Tree.generate_balanced(4, arity=2).tree_sequence
        expected = np.zeros(ts.num_nodes, dtype=np.int32)
        actual = info.get_num_muts(ts)
        np.testing.assert_equal(expected, actual)

    def test_1tree_1mut_below_root(self):
        ts = tskit.Tree.generate_balanced(4, arity=2).tree_sequence
        tables = ts.dump_tables()
        tables.sites.add_row(0, "A")
        tables.mutations.add_row(site=0, node=0, derived_state="T")
        ts = tables.tree_sequence()
        expected = np.zeros(ts.num_nodes, dtype=np.int32)
        expected[0] = 1
        actual = info.get_num_muts(ts)
        np.testing.assert_equal(expected, actual)

    def test_1tree_1mut_above_root(self):
        ts = tskit.Tree.generate_balanced(4, arity=2).tree_sequence
        tables = ts.dump_tables()
        tables.sites.add_row(0, "A")
        tables.mutations.add_row(site=0, node=6, derived_state="T")
        ts = tables.tree_sequence()
        expected = np.ones(ts.num_nodes, dtype=np.int32)
        actual = info.get_num_muts(ts)
        np.testing.assert_equal(expected, actual)

    def test_1tree_2mut_homoplasies(self):
        ts = tskit.Tree.generate_balanced(4, arity=2).tree_sequence
        tables = ts.dump_tables()
        tables.sites.add_row(0, "A")
        tables.mutations.add_row(site=0, node=0, derived_state="T")
        tables.mutations.add_row(site=0, node=3, derived_state="T")
        ts = tables.tree_sequence()
        expected = np.zeros(ts.num_nodes, dtype=np.int32)
        expected[0] = 1
        expected[3] = 1
        actual = info.get_num_muts(ts)
        np.testing.assert_equal(expected, actual)

    def test_1tree_2mut_reversion(self):
        ts = tskit.Tree.generate_balanced(4, arity=2).tree_sequence
        tables = ts.dump_tables()
        tables.sites.add_row(0, "A")
        tables.mutations.add_row(site=0, node=0, derived_state="A")
        tables.mutations.add_row(site=0, node=4, derived_state="T")
        ts = tables.tree_sequence()
        expected = np.zeros(ts.num_nodes, dtype=np.int32)
        expected[0] = 2
        expected[1] = 1
        expected[4] = 1
        actual = info.get_num_muts(ts)
        np.testing.assert_equal(expected, actual)

    def test_2trees_0mut(self):
        ts = msprime.sim_ancestry(
            2,
            recombination_rate=1e6,  # Nearly guarantee recomb.
            sequence_length=2,
        )
        assert ts.num_trees == 2
        expected = np.zeros(ts.num_nodes, dtype=np.int32)
        actual = info.get_num_muts(ts)
        np.testing.assert_equal(expected, actual)

    def test_2trees_1mut(self):
        ts = msprime.sim_ancestry(
            4,
            ploidy=1,
            recombination_rate=1e6,  # Nearly guarantee recomb.
            sequence_length=2,
        )
        tables = ts.dump_tables()
        tables.sites.add_row(0, "A")
        tables.mutations.add_row(site=0, node=0, derived_state="T")
        ts = tables.tree_sequence()
        assert ts.num_trees == 2
        expected = np.zeros(ts.num_nodes, dtype=np.int32)
        expected[0] = 1
        actual = info.get_num_muts(ts)
        np.testing.assert_equal(expected, actual)

    def test_2trees_2mut_diff_trees(self):
        ts = msprime.sim_ancestry(
            4,
            ploidy=1,
            recombination_rate=1e6,  # Nearly guarantee recomb.
            sequence_length=2,
        )
        tables = ts.dump_tables()
        tables.sites.add_row(0, "A")
        tables.sites.add_row(1, "A")
        tables.mutations.add_row(site=0, node=0, derived_state="T")
        tables.mutations.add_row(site=1, node=0, derived_state="T")
        ts = tables.tree_sequence()
        assert ts.num_trees == 2
        expected = np.zeros(ts.num_nodes, dtype=np.int32)
        expected[0] = 2
        actual = info.get_num_muts(ts)
        np.testing.assert_equal(expected, actual)

    def test_2trees_2mut_same_tree(self):
        ts = msprime.sim_ancestry(
            4,
            ploidy=1,
            recombination_rate=1e6,  # Nearly guarantee recomb.
            sequence_length=2,
        )
        tables = ts.dump_tables()
        tables.sites.add_row(0, "A")
        tables.sites.add_row(1, "A")
        tables.mutations.add_row(site=0, node=0, derived_state="T")
        tables.mutations.add_row(site=1, node=3, derived_state="T")
        ts = tables.tree_sequence()
        assert ts.num_trees == 2
        expected = np.zeros(ts.num_nodes, dtype=np.int32)
        expected[0] = 1
        expected[3] = 1
        actual = info.get_num_muts(ts)
        np.testing.assert_equal(expected, actual)


class TestTreeInfo:
    def test_tree_info_values(self, fx_ti_2020_02_13):
        ti = fx_ti_2020_02_13
        assert list(ti.nodes_num_missing_sites[:5]) == [0, 0, 121, 693, 667]
        assert list(ti.sites_num_missing_samples[:5]) == [39] * 5
        assert list(ti.sites_num_deletion_samples[:5]) == [0] * 5

    @pytest.mark.parametrize(
        "method",
        [
            func
            for (name, func) in inspect.getmembers(info.TreeInfo)
            if name.startswith("plot")
        ],
    )
    def test_plots(self, fx_ti_2020_02_13, method):
        fig, axes = method(fx_ti_2020_02_13)
        assert isinstance(fig, matplotlib.figure.Figure)
        for ax in axes:
            assert isinstance(ax, matplotlib.axes.Axes)
