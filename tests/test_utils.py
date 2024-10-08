import numpy as np
import pytest

import sc2ts
import sc2ts.utils as utils
import util


class TestPadSites:
    def check_site_padding(self, ts):
        ts = sc2ts.pad_sites(ts)
        ref = sc2ts.core.get_reference_sequence(as_array=True)
        assert ts.num_sites == len(ref) - 1
        ancestral_state = ts.tables.sites.ancestral_state.view("S1").astype(str)
        assert np.all(ancestral_state == ref[1:])

    def test_initial(self):
        self.check_site_padding(sc2ts.initial_ts())


class TestDetachSingletonRecombinants:
    def make_recombinant_tree(self, db_path, num_samples=1):
        # Make a tree sequence by adding num_samples samples under a
        # single recombination node. Start with the following tree:
        # 4.00┊  0  ┊
        #     ┊  ┃  ┊
        # 3.00┊  1  ┊
        #     ┊  ┃  ┊
        # 2.00┊  4  ┊
        #     ┊ ┏┻┓ ┊
        # 1.00┊ 2 3 ┊
        #     0   29904
        ts = util.example_binary(2)
        L = ts.sequence_length
        x = L / 2
        samples = util.get_samples(ts, [[(0, x, 2), (x, L, 3)]] * num_samples)
        date = "2021-01-01"

        # This is pretty ugly, need to figure out how to neatly factor this
        # model of Sample object vs metadata vs alignment QC
        # NOTE: code copied from test_inference.py
        for sample in samples:
            sample.date = date
            sample.metadata["date"] = date
            sample.metadata["strain"] = sample.strain
        match_db = util.get_match_db(ts, db_path, samples, date, num_mismatches=1000)
        # print("Match DB", len(match_db))
        # match_db.print_all()
        ts_rec = sc2ts.add_matching_results(
            "True",
            match_db=match_db,
            ts=ts,
            date=date,
        )
        assert ts_rec.num_trees == 2
        return ts_rec

    @pytest.mark.parametrize(
        "ts",
        # Should probably add sc2ts.initial_ts() here, but see
        # https://github.com/jeromekelleher/sc2ts/issues/152
        [util.example_binary(1), util.example_binary(2), util.example_binary(3)],
    )
    def test_no_recombinants(self, ts, tmp_path):
        ts2 = utils.detach_singleton_recombinants(ts)
        ts.tables.assert_equals(ts2.tables, ignore_provenance=True)

    def test_one_sample_recombinant(self, tmp_path):
        ts = self.make_recombinant_tree(tmp_path / "match.db")
        assert ts.num_samples == 4
        re_nodes = [
            node.id for node in ts.nodes() if node.flags & sc2ts.NODE_IS_RECOMBINANT
        ]
        assert len(re_nodes) == 1
        re_node = re_nodes[0]
        nodes_under_re = {re_node}
        for tree in ts.trees():
            nodes_under_re.update(tree.nodes(re_node))
        for u in nodes_under_re:
            for tree in ts.trees():
                assert not tree.is_isolated(u)
        ts2 = utils.detach_singleton_recombinants(ts)
        assert ts2 != ts
        assert ts2.num_samples == ts.num_samples - 1
        assert ts2.num_nodes == ts.num_nodes
        for u in nodes_under_re:
            for tree in ts2.trees():
                assert tree.is_isolated(u)
        ts3 = utils.detach_singleton_recombinants(ts2, filter_nodes=True)
        assert ts3.num_samples == ts.num_samples - 1
        assert ts3.num_nodes == ts.num_nodes - 2  # both sample and re node gone

    def test_two_sample_recombinant(self, tmp_path):
        """Test that we don't detach anything if the recombinant node is not a singleton"""
        ts = self.make_recombinant_tree(num_samples=2, db_path=tmp_path / "match.db")
        assert ts.num_samples == 5
        ts2 = utils.detach_singleton_recombinants(ts)
        ts.tables.assert_equals(ts2.tables, ignore_provenance=True)
