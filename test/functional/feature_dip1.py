#!/usr/bin/env python3
# Copyright (c) 2014-2019 The Bitcoin Core developers
# Copyright (c) DeFi Blockchain Developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
"""Test DIP1 activation

- verify basic block rewards on DIP1 activation
"""

from test_framework.test_framework import DefiTestFramework

from test_framework.authproxy import JSONRPCException
from test_framework.util import assert_equal, \
    connect_nodes_bi

from decimal import Decimal
import time

class Dip1Test (DefiTestFramework):
    def set_test_params(self):
        self.num_nodes = 2
        # node0: main
        # node1: secondary tester
        self.setup_clean_chain = True
        self.extra_args = [['-txnotokens=0', '-dip1height=2'], ['-txnotokens=0']]

    def run_test(self):
        assert_equal(self.nodes[0].getblockchaininfo()['softforks']['dip1']['active'], False)

        # BLOCK#1 - old values
        self.nodes[0].generate(1)
        # print("")
        # print("blocks:    ", self.nodes[0].getblockcount())
        # print("balance:    ", self.nodes[0].getbalances(True)) # immature 50
        # print("community:    ", self.nodes[0].listcommunitybalances()) #00
        assert_equal(self.nodes[0].getblockcount(), 1)
        assert_equal(self.nodes[0].getbalances()['mine']['immature'], 50)
        assert_equal(self.nodes[0].listcommunitybalances()['AnchorReward'], 0)
        assert_equal(self.nodes[0].listcommunitybalances()['IncentiveFunding'], 0)
        assert_equal(self.nodes[0].getblockchaininfo()['softforks']['dip1']['active'], True) # not active IRL, so getblockchaininfo works like "height+1"


        # BLOCK#2 - DIP1 activated
        self.nodes[0].generate(1)
        # print("")
        # print("blocks:    ", self.nodes[0].getblockcount())
        # print("community:    ", self.nodes[0].listcommunitybalances()) # 0.1 / 10
        # print("balance:    ", self.nodes[0].getbalances(True)) # immature 88
        assert_equal(self.nodes[0].getblockcount(), 2)

        assert_equal(self.nodes[0].getbalances()['mine']['immature'], 88)
        # import foundation address, so we can check foundation share (due to listunspent doesn't show immatured coinbases)
        self.nodes[0].importprivkey('cMv1JaaZ9Mbb3M3oNmcFvko8p7EcHJ8XD7RCQjzNaMs7BWRVZTyR') # foundationAddress (2NCWAKfEehP3qibkLKYQjXaWMK23k4EDMVS) privkey
        assert_equal(self.nodes[0].getbalances()['mine']['immature'], Decimal('89.9'))

        assert_equal(self.nodes[0].listcommunitybalances()['AnchorReward'], Decimal('0.1'))
        assert_equal(self.nodes[0].listcommunitybalances()['IncentiveFunding'], 10)

        self.sync_blocks()
        # block was accepted by "old" node1, but nothing applyed for communitybalances -> hardfork
        assert_equal(self.nodes[1].getblockcount(), 2)
        assert_equal(self.nodes[1].listcommunitybalances()['AnchorReward'], 0)
        assert_equal(self.nodes[1].listcommunitybalances()['IncentiveFunding'], 0)


        # BLOCK#3 by node1 (rejected by node0)
        self.nodes[1].generate(1)
        time.sleep(2) # can't sync here
        assert_equal(self.nodes[1].getblockcount(), 3)
        assert_equal(self.nodes[0].getblockcount(), 2) # block rejected by "new" node!

        # restart node1 with activated fork
        self.stop_node(1)
        self.start_node(1, ['-txnotokens=0', '-dip1height=2'])
        connect_nodes_bi(self.nodes, 0, 1)
        self.nodes[0].generate(2)
        self.sync_blocks()
        # check that w/o reindex node1 has wrong values
        assert_equal(self.nodes[0].listcommunitybalances()['AnchorReward'], Decimal('0.3'))
        assert_equal(self.nodes[0].listcommunitybalances()['IncentiveFunding'], 30)
        assert_equal(self.nodes[1].listcommunitybalances()['AnchorReward'], Decimal('0.2'))
        assert_equal(self.nodes[1].listcommunitybalances()['IncentiveFunding'], 20)

        # restart node1 with activated fork and reindex
        self.stop_node(1)
        self.start_node(1, ['-txnotokens=0', '-dip1height=2', '-reindex-chainstate'])
        assert_equal(self.nodes[1].getblockcount(), 4)
        assert_equal(self.nodes[1].listcommunitybalances()['AnchorReward'], Decimal('0.3'))
        assert_equal(self.nodes[1].listcommunitybalances()['IncentiveFunding'], 30)


if __name__ == '__main__':
    Dip1Test ().main ()
