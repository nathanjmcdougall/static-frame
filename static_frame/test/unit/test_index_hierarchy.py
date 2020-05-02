
import unittest
import pickle
import datetime
import numpy as np

from collections import OrderedDict

from static_frame import Index
# from static_frame import IndexGO
from static_frame import IndexDate
from static_frame import Series
from static_frame import Frame
from static_frame import FrameGO
# from static_frame import IndexYearMonth
# from static_frame import IndexYear
from static_frame import DisplayConfig

from static_frame import IndexHierarchy
from static_frame import IndexHierarchyGO
from static_frame import IndexLevel
from static_frame import IndexYearMonth

# from static_frame import IndexLevelGO
from static_frame import HLoc
from static_frame.core.array_go import ArrayGO
from static_frame.core.exception import ErrorInitIndex

from static_frame.test.test_case import temp_file
from static_frame.test.test_case import TestCase
from static_frame.test.test_case import skip_win


class TestUnit(TestCase):

    def test_hierarchy_slotted_a(self) -> None:

        labels = (('I', 'A'),
                ('I', 'B'),
                )
        ih1 = IndexHierarchy.from_labels(labels, name='foo')

        with self.assertRaises(AttributeError):
            ih1.g = 30 # type: ignore #pylint: disable=E0237
        with self.assertRaises(AttributeError):
            ih1.__dict__ #pylint: disable=W0104

    def test_hierarchy_init_a(self) -> None:

        labels = (('I', 'A'),
                ('I', 'B'),
                )

        ih1 = IndexHierarchy.from_labels(labels, name='foo')
        ih2 = IndexHierarchy(ih1)
        self.assertEqual(ih1.name, 'foo')
        self.assertEqual(ih2.name, 'foo')


    def test_hierarchy_init_b(self) -> None:

        labels = (
                ('I', 'A'),
                ('I', 'B'),
                ('II', 'B'),
                ('I', 'C')
                )

        with self.assertRaises(RuntimeError):
            ih1 = IndexHierarchy.from_labels(labels)

    def test_hierarchy_init_c(self) -> None:

        labels = (
                ('I', 'A'),
                ('I', 'B'),
                ('II', 'B'),
                ('III', 'B'),
                ('III', 'A')
                )

        ih1 = IndexHierarchy.from_labels(labels)
        self.assertEqual(ih1.values.tolist(),
            [['I', 'A'], ['I', 'B'], ['II', 'B'], ['III', 'B'], ['III', 'A']])


    def test_hierarchy_init_d(self) -> None:

        labels = (
                ('I', 'A'),
                ('I', 'B'),
                ('II', 'B'),
                ('III', 'B'),
                ('III', 'B')
                )
        with self.assertRaises(ErrorInitIndex):
            ih1 = IndexHierarchy.from_labels(labels)

    def test_hierarchy_init_e(self) -> None:

        labels = (
                ('I', 'A'),
                ('I', 'B'),
                ('II', 'B'),
                ('III', 'B'),
                ('I', 'B'),
                )

        with self.assertRaises(RuntimeError):
            ih1 = IndexHierarchy.from_labels(labels)



    def test_hierarchy_init_f(self) -> None:

        labels = (
                ('I', 'A'),
                ('I', 'B'),
                ('II', 'B'),
                ('III', 'B'),
                ('I', 'B'),
                )

        with self.assertRaises(RuntimeError):
            ih1 = IndexHierarchy.from_labels(labels)

    def test_hierarchy_init_g(self) -> None:

        labels = (
                ('I', 'A', 1),
                ('I', 'B', 1),
                ('II', 'A', 1),
                ('II', 'A', 2),
                ('II', 'A', 1),
                )
        with self.assertRaises(ErrorInitIndex):
            ih1 = IndexHierarchy.from_labels(labels)

    def test_hierarchy_init_h(self) -> None:

        labels = (
                ('I', 'A', 1),
                ('I', 'B', 1),
                ('II', 'A', 1),
                ('II', 'A', 2),
                ('II', 'B', 1),
                ('II', 'A', 3),
                )
        with self.assertRaises(RuntimeError):
            ih1 = IndexHierarchy.from_labels(labels)


    def test_hierarchy_init_i(self) -> None:
        with self.assertRaises(RuntimeError):
            ih1 = IndexHierarchy((3,))  # type: ignore

    def test_hierarchy_init_j(self) -> None:

        labels = (('I', 'A'),
                ('I', 'B'),
                )

        ih1 = IndexHierarchy.from_labels(labels, name=('a', 'b', 'c'))

        # can access as a .name, but not a .names
        self.assertEqual(ih1.name, ('a', 'b', 'c'))
        # names does not use name as it is the wrong size
        self.assertEqual(ih1.names, ('__index0__', '__index1__'))


    #---------------------------------------------------------------------------

    def test_hierarchy_loc_to_iloc_a(self) -> None:


        groups = Index(('A', 'B', 'C'))
        dates = IndexDate.from_date_range('2018-01-01', '2018-01-04')
        observations = Index(('x', 'y'))


        lvl2a = IndexLevel(index=observations)
        lvl2b = IndexLevel(index=observations, offset=2)
        lvl2c = IndexLevel(index=observations, offset=4)
        lvl2d = IndexLevel(index=observations, offset=6)
        lvl2_targets = ArrayGO((lvl2a, lvl2b, lvl2c, lvl2d))


        lvl1a = IndexLevel(index=dates,
                targets=lvl2_targets, offset=0)
        lvl1b = IndexLevel(index=dates,
                targets=lvl2_targets, offset=len(lvl1a))
        lvl1c = IndexLevel(index=dates,
                targets=lvl2_targets, offset=len(lvl1a) * 2)

        # we need as many targets as len(index)
        lvl0 = IndexLevel(index=groups,
                targets=ArrayGO((lvl1a, lvl1b, lvl1c)))


        self.assertEqual(len(lvl2a), 2)
        self.assertEqual(len(lvl1a), 8)
        self.assertEqual(len(lvl0), 24)

        self.assertEqual(list(lvl2a.depths()),
                [1])
        self.assertEqual(list(lvl1a.depths()),
                [2, 2, 2, 2])
        self.assertEqual(list(lvl0.depths()),
                [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3])

        ih = IndexHierarchy(lvl0)

        self.assertEqual(len(ih), 24)

        post = ih.loc_to_iloc(HLoc[
                ['A', 'B', 'C'],
                slice('2018-01-01', '2018-01-04'),  # type: ignore
                ['x', 'y']])
        # this will break if we recognize this can be a slice
        self.assertEqual(post, list(range(len(ih))))

        post = ih.loc_to_iloc(HLoc[
                ['A', 'B', 'C'],
                slice('2018-01-01', '2018-01-04'),  # type: ignore
                'x'])

        self.assertEqual(post, list(range(0, len(ih), 2)))

        post = ih.loc_to_iloc(HLoc[
                'C',
                '2018-01-03',
                'y'])

        self.assertEqual(post, 21)

        post = ih.loc_to_iloc(HLoc['B', '2018-01-03':, 'y'])  # type: ignore  # https://github.com/python/typeshed/pull/3024
        self.assertEqual(post, [13, 15])


        post = ih.loc_to_iloc(HLoc[['B', 'C'], '2018-01-03'])
        self.assertEqual(post, [12, 13, 20, 21])

        post = ih.loc_to_iloc(HLoc[['A', 'C'], :, 'y'])
        self.assertEqual(post, [1, 3, 5, 7, 17, 19, 21, 23])

        post = ih.loc_to_iloc(HLoc[['A', 'C'], :, 'x'])
        self.assertEqual(post, [0, 2, 4, 6, 16, 18, 20, 22])



    def test_hierarchy_loc_to_iloc_b(self) -> None:
        OD = OrderedDict
        tree = OD([
                ('I', OD([
                        ('A', (1, 2)), ('B', (1, 2, 3)), ('C', (2, 3))
                        ])
                ),
                ('II', OD([
                        ('A', (1, 2, 3)), ('B', (1,))
                        ])
                ),
                ])

        ih = IndexHierarchy.from_tree(tree)

        post = ih.loc_to_iloc(HLoc['I', 'B', 1])
        self.assertEqual(post, 2)

        post = ih.loc_to_iloc(HLoc['I', 'B', 3])
        self.assertEqual(post, 4)

        post = ih.loc_to_iloc(HLoc['II', 'A', 3])
        self.assertEqual(post, 9)

        post = ih.loc_to_iloc(HLoc['II', 'A'])
        self.assertEqual(post, slice(7, 10))

        post = ih.loc_to_iloc(HLoc['I', 'C'])
        self.assertEqual(post, slice(5, 7))


        post = ih.loc_to_iloc(HLoc['I', ['A', 'C']])
        self.assertEqual(post, [0, 1, 5, 6])


        post = ih.loc_to_iloc(HLoc[:, 'A', :])
        self.assertEqual(post, [0, 1, 7, 8, 9])


        post = ih.loc_to_iloc(HLoc[:, 'C', 3])
        self.assertEqual(post, [6])

        post = ih.loc_to_iloc(HLoc[:, :, 3])
        self.assertEqual(post, [4, 6, 9])

        post = ih.loc_to_iloc(HLoc[:, :, 1])
        self.assertEqual(post, [0, 2, 7, 10])

        # TODO: not sure what to do when a multiple selection, [1, 2], is a superset of the leaf index; we do not match with a normal loc
        # ih.loc_to_iloc((slice(None), slice(None), [1,2]))


    def test_hierarchy_loc_to_iloc_c(self) -> None:
        OD = OrderedDict
        tree = OD([
                ('I', OD([
                        ('A', (1, 2)), ('B', (1, 2, 3)), ('C', (2, 3))
                        ])
                ),
                ('II', OD([
                        ('A', (1, 2, 3)), ('B', (1,))
                        ])
                ),
                ])

        ih = IndexHierarchy.from_tree(tree)

        # TODO: add additional validaton
        post = ih.loc[('I', 'B', 2): ('II', 'A', 2)]  # type: ignore  # https://github.com/python/typeshed/pull/3024
        self.assertTrue(len(post), 6)

        post = ih.loc[[('I', 'B', 2), ('II', 'A', 2)]]
        self.assertTrue(len(post), 2)


    def test_hierarchy_loc_to_iloc_d(self) -> None:

        labels = (
                ('I', 'A', 1),
                ('I', 'B', 1),
                ('II', 'A', 1),
                ('II', 'A', 2),
                ('II', 'B', 1),
                ('II', 'B', 2),
                )

        ih = IndexHierarchy.from_labels(labels)

        # selection with an Index objext
        iloc1 = ih.loc_to_iloc(Index((labels[2], labels[5])))
        self.assertEqual(iloc1, [2, 5])

        iloc2 = ih.loc_to_iloc(Index(labels))
        self.assertEqual(iloc2, [0, 1, 2, 3, 4, 5])



    def test_hierarchy_loc_to_iloc_e(self) -> None:

        labels = (
                ('I', 'A', 1),
                ('I', 'B', 1),
                ('II', 'A', 1),
                ('II', 'A', 2),
                ('II', 'B', 1),
                ('II', 'B', 2),
                )

        ih1 = IndexHierarchy.from_labels(labels)

        ih2 = IndexHierarchy.from_labels(labels[:3])
        ih3 = IndexHierarchy.from_labels(labels[-3:])

        # selection with an IndexHierarchy
        self.assertEqual(ih1.loc_to_iloc(ih2), [0, 1, 2])
        self.assertEqual(ih1.loc_to_iloc(ih3), [3, 4, 5])



    def test_hierarchy_loc_to_iloc_f(self) -> None:

        labels = (
                ('I', 'A', 1),
                ('I', 'B', 1),
                ('II', 'A', 1),
                ('II', 'A', 2),
                ('II', 'B', 1),
                ('II', 'B', 2),
                )

        ih1 = IndexHierarchy.from_labels(labels)

        # selection with Boolean and non-Bolean Series
        a1 = ih1.loc_to_iloc(Series((True, True), index=(labels[1], labels[4])))
        self.assertEqual(a1.tolist(), [False, True, False, False, True, False]) #type: ignore

        a2 = ih1.loc_to_iloc(Series((labels[5], labels[2], labels[4])))
        self.assertEqual(a2, [5, 2, 4])

    #---------------------------------------------------------------------------

    def test_hierarchy_extract_iloc_a(self) -> None:

        labels = (
                ('I', 'A', 1),
                ('I', 'B', 1),
                ('II', 'A', 1),
                ('II', 'A', 2),
                ('II', 'B', 1),
                ('II', 'B', 2),
                )

        ih1 = IndexHierarchy.from_labels(labels)

        ih2 = ih1._extract_iloc(None) # will get a copy
        self.assertTrue((ih1.values == ih2.values).all()) #type: ignore

        ih3 = ih1._extract_iloc(slice(None)) # will get a copy
        self.assertTrue((ih1.values == ih3.values).all()) #type: ignore
        # reduces to a tuple
        ih4 = ih1._extract_iloc(3)
        self.assertEqual(ih4, ('II', 'A', 2))

    #---------------------------------------------------------------------------

    def test_hierarchy_extract_getitem_astype_a(self) -> None:

        labels = (
                ('I', 'A', 1),
                ('I', 'B', 1),
                ('II', 'A', 1),
                ('II', 'A', 2),
                ('II', 'B', 1),
                ('II', 'B', 2),
                )

        ih1 = IndexHierarchy.from_labels(labels)

        with self.assertRaises(KeyError):
            ih1._extract_getitem_astype(('A', 1))

    #--------------------------------------------------------------------------

    def test_hierarchy_from_product_a(self) -> None:

        groups = Index(('A', 'B', 'C'))
        dates = IndexDate.from_date_range('2018-01-01', '2018-01-04')
        observations = Index(('x', 'y'))

        ih = IndexHierarchy.from_product(groups, dates, observations)


    def test_hierarchy_from_product_b(self) -> None:

        with self.assertRaises(RuntimeError):
            IndexHierarchy.from_product((1, 2))

    #--------------------------------------------------------------------------

    def test_hierarchy_from_tree_a(self) -> None:

        OD = OrderedDict

        tree = OD([('A', (1, 2, 3, 4)), ('B', (1, 2))])

        ih = IndexHierarchy.from_tree(tree)

        self.assertEqual(ih.to_frame().to_pairs(0),
                ((0, ((0, 'A'), (1, 'A'), (2, 'A'), (3, 'A'), (4, 'B'), (5, 'B'))), (1, ((0, 1), (1, 2), (2, 3), (3, 4), (4, 1), (5, 2))))
                )


    def test_hierarchy_from_tree_b(self) -> None:

        OD = OrderedDict

        tree = OD([
                ('I', OD([
                        ('A', (1, 2)), ('B', (1, 2, 3)), ('C', (2, 3))
                        ])
                ),
                ('II', OD([
                        ('A', (1, 2, 3)), ('B', (1,))
                        ])
                ),
                ])

        ih = IndexHierarchy.from_tree(tree)
        self.assertEqual(ih.to_frame().to_pairs(0),
                ((0, ((0, 'I'), (1, 'I'), (2, 'I'), (3, 'I'), (4, 'I'), (5, 'I'), (6, 'I'), (7, 'II'), (8, 'II'), (9, 'II'), (10, 'II'))), (1, ((0, 'A'), (1, 'A'), (2, 'B'), (3, 'B'), (4, 'B'), (5, 'C'), (6, 'C'), (7, 'A'), (8, 'A'), (9, 'A'), (10, 'B'))), (2, ((0, 1), (1, 2), (2, 1), (3, 2), (4, 3), (5, 2), (6, 3), (7, 1), (8, 2), (9, 3), (10, 1))))
                )
    #---------------------------------------------------------------------------

    def test_hierarchy_from_labels_a(self) -> None:

        labels1 = (('I', 'A', 1),
                ('I', 'A', 2),
                ('I', 'B', 1),
                ('I', 'B', 2),
                ('II', 'A', 1),
                ('II', 'A', 2),
                ('II', 'B', 1),
                ('II', 'B', 2),
                )

        ih = IndexHierarchy.from_labels(labels1)
        self.assertEqual(len(ih), 8)
        self.assertEqual(ih.depth, 3)

        self.assertEqual([ih.loc_to_iloc(x) for x in labels1],
                [0, 1, 2, 3, 4, 5, 6, 7])


        labels2 = (('I', 'A', 1),
                ('I', 'A', 2),
                ('I', 'B', 1),
                ('II', 'B', 2),
                )

        ih = IndexHierarchy.from_labels(labels2)
        self.assertEqual(len(ih), 4)
        self.assertEqual(ih.depth, 3)

        self.assertEqual([ih.loc_to_iloc(x) for x in labels2], [0, 1, 2, 3])


    def test_hierarchy_from_labels_b(self) -> None:

        labels = (('I', 'A'),
                ('I', 'B'),
                )

        ih = IndexHierarchy.from_labels(labels)

        self.assertEqual(ih.to_frame().to_pairs(0),
                ((0, ((0, 'I'), (1, 'I'))), (1, ((0, 'A'), (1, 'B')))))


    def test_hierarchy_from_labels_c(self) -> None:

        ih = IndexHierarchy.from_labels(tuple())
        self.assertEqual(len(ih), 0)


    def test_hierarchy_from_labels_d(self) -> None:

        with self.assertRaises(RuntimeError):
            ih = IndexHierarchy.from_labels([(3,), (4,)])


    def test_hierarchy_from_labels_e(self) -> None:

        index_constructors = (Index, IndexDate)

        labels = (
            ('a', '2019-01-01'),
            ('a', '2019-02-01'),
            ('b', '2019-01-01'),
            ('b', '2019-02-01'),
        )

        with self.assertRaises(ErrorInitIndex):
            ih = IndexHierarchy.from_labels(labels, index_constructors=(Index,))


        ih = IndexHierarchy.from_labels(labels, index_constructors=index_constructors)

        self.assertEqual(ih.loc[HLoc[:, '2019-02']].values.tolist(),
                [['a', datetime.date(2019, 2, 1)],
                ['b', datetime.date(2019, 2, 1)]])

        self.assertEqual(ih.loc[HLoc[:, '2019']].values.tolist(),
                [['a', datetime.date(2019, 1, 1)],
                ['a', datetime.date(2019, 2, 1)],
                ['b', datetime.date(2019, 1, 1)],
                ['b', datetime.date(2019, 2, 1)]])

        self.assertEqual(ih.loc[HLoc[:, '2019-02-01']].values.tolist(),
                [['a', datetime.date(2019, 2, 1)],
                ['b', datetime.date(2019, 2, 1)]]
                )

    def test_hierarchy_from_labels_f(self) -> None:

        labels1 = (('I', 'A', 1),
                ('I', 'A', 2),
                (None, 'B', 1),
                ('I', None, 2),
                ('II', 'A', 1),
                (None, 'A', 2),
                (None, 'B', 1),
                (None, 'B', 2),
                )

        ih = IndexHierarchy.from_labels(labels1, continuation_token=None) # type: ignore

        self.assertEqual(ih.values.tolist(),
                [['I', 'A', 1], ['I', 'A', 2], ['I', 'B', 1], ['I', 'B', 2], ['II', 'A', 1], ['II', 'A', 2], ['II', 'B', 1], ['II', 'B', 2]]
                )

    def test_hierarchy_from_labels_g(self) -> None:

        labels1 = (('II', 'A', 1),
                ('I', 'B', 1),
                ('II', 'B', 2),
                ('I', 'A', 2),
                ('I', 'B', 2),
                ('II', 'A', 2),
                ('II', 'B', 1),
                ('I', 'A', 1),
                )

        with self.assertRaises(ErrorInitIndex):
            ih1 = IndexHierarchy.from_labels(labels1)

        ih2 = IndexHierarchy.from_labels(labels1, reorder_for_hierarchy=True)
        self.assertEqual(ih2.shape, (8, 3))
        self.assertEqual(ih2.iloc[-1], ('I', 'B', 2))


    def test_hierarchy_from_labels_h(self) -> None:

        labels = (
                ('I', 'A', 1),
                ('II', 'B', 1),
                ('II', 'A', 1),
                ('II', 'A', 2),
                ('II', 'A', 3),
                ('I', 'B', 1),
                )
        with self.assertRaises(RuntimeError):
            ih1 = IndexHierarchy.from_labels(labels,
                    reorder_for_hierarchy=True,
                    continuation_token='')

    #---------------------------------------------------------------------------

    def test_hierarchy_from_index_items_a(self) -> None:

        idx1 = Index(('A', 'B', 'C'))
        idx2 = Index(('x', 'y'))
        idx3 = Index((4, 5, 6))

        ih = IndexHierarchy.from_index_items(dict(a=idx1, b=idx2, c=idx3).items())

        self.assertEqual(
                ih.values.tolist(),
                [['a', 'A'], ['a', 'B'], ['a', 'C'], ['b', 'x'], ['b', 'y'], ['c', 4], ['c', 5], ['c', 6]]
                )

    def test_hierarchy_from_index_items_b(self) -> None:

        idx1 = Index(('A', 'B', 'C'))
        idx2 = Index(('x', 'y'))
        idx3 = Index((4, 5, 6))

        ih = IndexHierarchyGO.from_index_items(dict(a=idx1, b=idx2, c=idx3).items())
        ih.append(('c', 7))

        self.assertEqual(ih.values.tolist(),
                [['a', 'A'], ['a', 'B'], ['a', 'C'], ['b', 'x'], ['b', 'y'], ['c', 4], ['c', 5], ['c', 6], ['c', 7]])



    def test_hierarchy_from_labels_delimited_a(self) -> None:

        labels = ("'I' 'A'", "'I' 'B'")

        ih = IndexHierarchy.from_labels_delimited(labels)

        self.assertEqual(ih.values.tolist(),
                [['I', 'A'], ['I', 'B']])



    def test_hierarchy_from_labels_delimited_b(self) -> None:

        labels = (
                "'I' 'A' 0",
                "'I' 'A' 1",
                "'I' 'B' 0",
                "'I' 'B' 1",
                "'II' 'A' 0",
                )

        ih = IndexHierarchy.from_labels_delimited(labels)

        self.assertEqual(ih.values.tolist(),
                [['I', 'A', 0], ['I', 'A', 1], ['I', 'B', 0], ['I', 'B', 1], ['II', 'A', 0]]
                )


    def test_hierarchy_from_labels_delimited_c(self) -> None:

        labels = (
                "['I' 'A' 0]",
                "['I' 'A' 1]",
                "['I' 'B' 0]",
                "['I' 'B' 1]",
                "['II' 'A' 0]",
                )

        ih = IndexHierarchy.from_labels_delimited(labels)

        self.assertEqual(ih.values.tolist(),
                [['I', 'A', 0], ['I', 'A', 1], ['I', 'B', 0], ['I', 'B', 1], ['II', 'A', 0]]
                )

    #---------------------------------------------------------------------------

    def test_hierarchy_from_type_blocks_a(self) -> None:
        f1 = Frame.from_element('a', index=range(3), columns=('a',))
        f2 = Frame.from_items((('a', tuple('AABB')), ('b', (1, 2, 1, 2))))
        f3 = Frame.from_items((('a', tuple('AABA')), ('b', (1, 2, 1, 2))))

        with self.assertRaises(ErrorInitIndex):
            ih = IndexHierarchy._from_type_blocks(f1._blocks)

        with self.assertRaises(ErrorInitIndex):
            IndexHierarchy._from_type_blocks(f2._blocks, index_constructors=(IndexDate,))

        with self.assertRaises(ErrorInitIndex):
            IndexHierarchy._from_type_blocks(f3._blocks)


    #---------------------------------------------------------------------------

    def test_hierarchy_contains_a(self) -> None:
        labels = (('I', 'A'),
                ('I', 'B'),
                )
        ih = IndexHierarchy.from_labels(labels)

        self.assertTrue(('I', 'A') in ih)


    def test_hierarchy_extract_a(self) -> None:
        idx = IndexHierarchy.from_product(['A', 'B'], [1, 2])

        self.assertEqual(idx.iloc[1], ('A', 2))
        self.assertEqual(idx.loc[('B', 1)], ('B', 1))
        self.assertEqual(idx[2], ('B', 1)) #pylint: disable=E1136
        self.assertEqual(idx.loc[HLoc['B', 1]], ('B', 1))



    def test_hierarchy_iter_a(self) -> None:
        OD = OrderedDict
        tree = OD([
                ('I', OD([
                        ('A', (1, 2)), ('B', (1, 2))
                        ])
                ),
                ('II', OD([
                        ('A', (1, 2)), ('B', (1, 2))
                        ])
                ),
                ])

        ih = IndexHierarchy.from_tree(tree)

        # this iterates over numpy arrays, which can be used with contains
        self.assertEqual([k in ih for k in ih], #pylint: disable=E1133
                [True, True, True, True, True, True, True, True]
                )


    def test_hierarchy_reversed(self) -> None:
        labels = (('a', 1), ('a', 2), ('b', 1), ('b', 2))
        hier_idx = IndexHierarchy.from_labels(labels)
        self.assertTrue(
            all(hidx_1 == hidx_2
                for hidx_1, hidx_2 in zip(reversed(hier_idx), reversed(labels)))
        )


    def test_hierarchy_keys_a(self) -> None:
        OD = OrderedDict
        tree = OD([
                ('I', OD([
                        ('A', (1, 2)), ('B', (1, 2))
                        ])
                ),
                ('II', OD([
                        ('A', (1, 2)), ('B', (1, 2))
                        ])
                ),
                ])

        ih = IndexHierarchyGO.from_tree(tree)

        self.assertEqual([k in ih for k in ih], #pylint: disable=E1133
                [True, True, True, True, True, True, True, True]
                )

        ih.append(('III', 'A', 1))

        self.assertEqual(set(ih),
                {('I', 'B', 1), ('I', 'A', 2), ('II', 'B', 2), ('II', 'A', 2), ('I', 'A', 1), ('III', 'A', 1), ('II', 'B', 1), ('II', 'A', 1), ('I', 'B', 2)}
                )


    def test_hierarchy_display_a(self) -> None:
        OD = OrderedDict
        tree = OD([
                ('I', OD([
                        ('A', (1, 2)), ('B', (1, 2))
                        ])
                ),
                ('II', OD([
                        ('A', (1, 2)), ('B', (1, 2))
                        ])
                ),
                ])

        ih = IndexHierarchy.from_tree(tree)

        post = ih.display()
        self.assertEqual(len(post), 10)

        s = Series(range(8), index=ih)
        post = s.display()
        self.assertEqual(len(post), 11)

    def test_hierarchy_loc_a(self) -> None:
        OD = OrderedDict
        tree = OD([
                ('I', OD([
                        ('A', (1, 2)), ('B', (1, 2))
                        ])
                ),
                ('II', OD([
                        ('A', (1, 2)), ('B', (1, 2))
                        ])
                ),
                ])

        ih = IndexHierarchy.from_tree(tree)

        s = Series(range(8), index=ih)

        self.assertEqual(
                s.loc[HLoc['I']].values.tolist(),
                [0, 1, 2, 3])

        self.assertEqual(
                s.loc[HLoc[:, 'A']].values.tolist(),
                [0, 1, 4, 5])

    def test_hierarchy_series_a(self) -> None:
        f1 = IndexHierarchy.from_tree
        s1 = Series.from_element(23, index=f1(dict(a=(1,2,3))))
        self.assertEqual(s1.values.tolist(), [23, 23, 23])

        f2 = IndexHierarchy.from_product
        s2 = Series.from_element(3, index=f2(Index(('a', 'b')), Index((1,2))))
        self.assertEqual(s2.to_pairs(),
                ((('a', 1), 3), (('a', 2), 3), (('b', 1), 3), (('b', 2), 3)))


    def test_hierarchy_frame_a(self) -> None:
        OD = OrderedDict
        tree = OD([
                ('I', OD([
                        ('A', (1,)), ('B', (1, 2))
                        ])
                ),
                ('II', OD([
                        ('A', (1,)), ('B', (1, 2))
                        ])
                ),
                ])

        ih = IndexHierarchy.from_tree(tree)

        data = np.arange(6*6).reshape(6, 6)
        f1 = Frame(data, index=ih, columns=ih)
        # self.assertEqual(len(f.to_pairs(0)), 8)


        f2 = f1.assign.loc[('I', 'B', 2), ('II', 'A', 1)](200)

        post = f2.to_pairs(0)
        self.assertEqual(post,
                ((('I', 'A', 1), ((('I', 'A', 1), 0), (('I', 'B', 1), 6), (('I', 'B', 2), 12), (('II', 'A', 1), 18), (('II', 'B', 1), 24), (('II', 'B', 2), 30))), (('I', 'B', 1), ((('I', 'A', 1), 1), (('I', 'B', 1), 7), (('I', 'B', 2), 13), (('II', 'A', 1), 19), (('II', 'B', 1), 25), (('II', 'B', 2), 31))), (('I', 'B', 2), ((('I', 'A', 1), 2), (('I', 'B', 1), 8), (('I', 'B', 2), 14), (('II', 'A', 1), 20), (('II', 'B', 1), 26), (('II', 'B', 2), 32))), (('II', 'A', 1), ((('I', 'A', 1), 3), (('I', 'B', 1), 9), (('I', 'B', 2), 200), (('II', 'A', 1), 21), (('II', 'B', 1), 27), (('II', 'B', 2), 33))), (('II', 'B', 1), ((('I', 'A', 1), 4), (('I', 'B', 1), 10), (('I', 'B', 2), 16), (('II', 'A', 1), 22), (('II', 'B', 1), 28), (('II', 'B', 2), 34))), (('II', 'B', 2), ((('I', 'A', 1), 5), (('I', 'B', 1), 11), (('I', 'B', 2), 17), (('II', 'A', 1), 23), (('II', 'B', 1), 29), (('II', 'B', 2), 35))))
        )


        f3 = f1.assign.loc[('I', 'B', 2):, HLoc[:, :, 2]](200)  # type: ignore  # https://github.com/python/typeshed/pull/3024

        self.assertEqual(f3.to_pairs(0),
                ((('I', 'A', 1), ((('I', 'A', 1), 0), (('I', 'B', 1), 6), (('I', 'B', 2), 12), (('II', 'A', 1), 18), (('II', 'B', 1), 24), (('II', 'B', 2), 30))), (('I', 'B', 1), ((('I', 'A', 1), 1), (('I', 'B', 1), 7), (('I', 'B', 2), 13), (('II', 'A', 1), 19), (('II', 'B', 1), 25), (('II', 'B', 2), 31))), (('I', 'B', 2), ((('I', 'A', 1), 2), (('I', 'B', 1), 8), (('I', 'B', 2), 200), (('II', 'A', 1), 200), (('II', 'B', 1), 200), (('II', 'B', 2), 200))), (('II', 'A', 1), ((('I', 'A', 1), 3), (('I', 'B', 1), 9), (('I', 'B', 2), 15), (('II', 'A', 1), 21), (('II', 'B', 1), 27), (('II', 'B', 2), 33))), (('II', 'B', 1), ((('I', 'A', 1), 4), (('I', 'B', 1), 10), (('I', 'B', 2), 16), (('II', 'A', 1), 22), (('II', 'B', 1), 28), (('II', 'B', 2), 34))), (('II', 'B', 2), ((('I', 'A', 1), 5), (('I', 'B', 1), 11), (('I', 'B', 2), 200), (('II', 'A', 1), 200), (('II', 'B', 1), 200), (('II', 'B', 2), 200))))
        )



    def test_hierarchy_frame_b(self) -> None:
        OD = OrderedDict
        tree = OD([
                ('I', OD([
                        ('A', (1,)), ('B', (1, 2))
                        ])
                ),
                ('II', OD([
                        ('A', (1,)), ('B', (1, 2))
                        ])
                ),
                ])

        ih = IndexHierarchyGO.from_tree(tree)
        data = np.arange(6*6).reshape(6, 6)
        # TODO: this only works if own_columns is True for now
        f1 = FrameGO(data, index=range(6), columns=ih, own_columns=True)
        f1[('II', 'B', 3)] = 0

        f2 = f1[HLoc[:, 'B']]
        self.assertEqual(f2.shape, (6, 5))

        self.assertEqual(f2.to_pairs(0),
                ((('I', 'B', 1), ((0, 1), (1, 7), (2, 13), (3, 19), (4, 25), (5, 31))), (('I', 'B', 2), ((0, 2), (1, 8), (2, 14), (3, 20), (4, 26), (5, 32))), (('II', 'B', 1), ((0, 4), (1, 10), (2, 16), (3, 22), (4, 28), (5, 34))), (('II', 'B', 2), ((0, 5), (1, 11), (2, 17), (3, 23), (4, 29), (5, 35))), (('II', 'B', 3), ((0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0))))
                )

        f3 = f1[HLoc[:, :, 1]]
        self.assertEqual(f3.to_pairs(0), ((('I', 'A', 1), ((0, 0), (1, 6), (2, 12), (3, 18), (4, 24), (5, 30))), (('I', 'B', 1), ((0, 1), (1, 7), (2, 13), (3, 19), (4, 25), (5, 31))), (('II', 'A', 1), ((0, 3), (1, 9), (2, 15), (3, 21), (4, 27), (5, 33))), (('II', 'B', 1), ((0, 4), (1, 10), (2, 16), (3, 22), (4, 28), (5, 34)))))


        f4 = f1.loc[[2, 5], HLoc[:, 'A']]
        self.assertEqual(f4.to_pairs(0),
                ((('I', 'A', 1), ((2, 12), (5, 30))), (('II', 'A', 1), ((2, 15), (5, 33)))))



    def test_hierarchy_index_go_a(self) -> None:

        OD = OrderedDict
        tree1 = OD([
                ('I', OD([
                        ('A', (1,)), ('B', (1, 2))
                        ])
                ),
                ('II', OD([
                        ('A', (1,)), ('B', (1, 2))
                        ])
                ),
                ])
        ih1 = IndexHierarchyGO.from_tree(tree1)

        tree2 = OD([
                ('III', OD([
                        ('A', (1,)), ('B', (1, 2))
                        ])
                ),
                ('IV', OD([
                        ('A', (1,)), ('B', (1, 2))
                        ])
                ),
                ])
        ih2 = IndexHierarchyGO.from_tree(tree2)

        ih1.extend(ih2)

        # self.assertEqual(ih1.loc_to_iloc(('IV', 'B', 2)), 11)
        self.assertEqual(len(ih2), 6)

        # need tuple here to distinguish from iterable type selection
        self.assertEqual([ih1.loc_to_iloc(tuple(v)) for v in ih1.values],
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
                )



    def test_hierarchy_relabel_a(self) -> None:

        labels = (
                ('I', 'A'),
                ('I', 'B'),
                ('II', 'A'),
                ('II', 'B'),
                )

        ih = IndexHierarchy.from_labels(labels)

        ih.relabel({('I', 'B'): ('I', 'C')})

        ih2 = ih.relabel({('I', 'B'): ('I', 'C')})

        self.assertEqual(ih2.values.tolist(),
                [['I', 'A'], ['I', 'C'], ['II', 'A'], ['II', 'B']])

        with self.assertRaises(Exception):
            ih3 = ih.relabel({('I', 'B'): ('I', 'C', 1)})

        ih3 = ih.relabel(lambda x: tuple(e.lower() for e in x))

        self.assertEqual(
                ih3.values.tolist(),
                [['i', 'a'], ['i', 'b'], ['ii', 'a'], ['ii', 'b']])



    def test_hierarchy_rehierarch_a(self) -> None:
        ih1 = IndexHierarchy.from_product(('I', 'II'), ('B', 'A'), (2, 1))
        ih2 = ih1.rehierarch((1, 0, 2))

        self.assertEqual(ih2.values.tolist(),
                [['B', 'I', 2], ['B', 'I', 1], ['B', 'II', 2], ['B', 'II', 1], ['A', 'I', 2], ['A', 'I', 1], ['A', 'II', 2], ['A', 'II', 1]]
                )

        ih3 = ih1.rehierarch((2, 1, 0))
        self.assertEqual(
                ih3.values.tolist(),
                [[2, 'B', 'I'], [2, 'B', 'II'], [2, 'A', 'I'], [2, 'A', 'II'], [1, 'B', 'I'], [1, 'B', 'II'], [1, 'A', 'I'], [1, 'A', 'II']]
                )


    def test_hierarchy_rehierarch_b(self) -> None:
        labels = (
                ('I', 'A'),
                ('I', 'B'),
                ('II', 'C'),
                ('II', 'B'),
                ('II', 'D'),
                ('III', 'D'),
                ('IV', 'A'),
                )

        ih1 = IndexHierarchyGO.from_labels(labels)
        self.assertEqual(ih1.rehierarch([1, 0]).values.tolist(),
                [['A', 'I'], ['A', 'IV'], ['B', 'I'], ['B', 'II'], ['C', 'II'], ['D', 'II'], ['D', 'III']]
                )

    def test_hierarchy_rehierarch_c(self) -> None:
        labels = (
                ('I', 'A'),
                ('I', 'B'),
                ('II', 'A'),
                ('II', 'B'),
                )
        ih1 = IndexHierarchy.from_labels(labels)

        with self.assertRaises(RuntimeError):
            ih1.rehierarch([0, 0])

        with self.assertRaises(RuntimeError):
            ih1.rehierarch([0,])


    def test_hierarchy_set_operators_a(self) -> None:

        labels = (
                ('I', 'A'),
                ('I', 'B'),
                ('II', 'A'),
                ('II', 'B'),
                )

        ih1 = IndexHierarchy.from_labels(labels)

        labels = (
                ('II', 'A'),
                ('II', 'B'),
                ('III', 'A'),
                ('III', 'B'),
                )

        ih2 = IndexHierarchy.from_labels(labels)

        post1 = ih1.intersection(ih2)
        self.assertEqual(post1.values.tolist(),
                [['II', 'A'], ['II', 'B']])

        post2 = ih1.union(ih2)
        self.assertEqual(post2.values.tolist(),
                [['I', 'A'], ['I', 'B'], ['II', 'A'], ['II', 'B'], ['III', 'A'], ['III', 'B']])

        post3 = ih1.difference(ih2)
        self.assertEqual(post3.values.tolist(),
                [['I', 'A'], ['I', 'B']])


    def test_hierarchy_set_operators_b(self) -> None:

        labels = (
                ('II', 'B'),
                ('II', 'A'),
                ('I', 'B'),
                ('I', 'A'),
                )

        ih1 = IndexHierarchy.from_labels(labels)
        ih2 = IndexHierarchy.from_labels(labels)

        post1 = ih1.union(ih2)
        self.assertEqual(post1.values.tolist(),
                [['II', 'B'], ['II', 'A'], ['I', 'B'], ['I', 'A']])

        post2 = ih1.intersection(ih2)
        self.assertEqual(post2.values.tolist(),
                [['II', 'B'], ['II', 'A'], ['I', 'B'], ['I', 'A']])

        post3 = ih1.difference(ih2)
        self.assertEqual(post3.values.tolist(),
                [])


    def test_hierarchy_set_operators_c(self) -> None:

        labels = (
                ('II', 'B'),
                ('II', 'A'),
                ('I', 'B'),
                ('I', 'A'),
                )

        ih1 = IndexHierarchy.from_labels(())
        ih2 = IndexHierarchy.from_labels(labels)

        post1 = ih1.union(ih2)
        self.assertEqual(post1.values.tolist(),
                [['II', 'B'], ['II', 'A'], ['I', 'B'], ['I', 'A']])

        post2 = ih1.intersection(ih2)
        self.assertEqual(post2.values.tolist(),
                [])

        post3 = ih1.difference(ih2)
        self.assertEqual(post3.values.tolist(),
                [])


    def test_hierarchy_set_operators_d(self) -> None:

        labels = (
                ('II', 'B'),
                ('II', 'A'),
                ('I', 'B'),
                ('I', 'A'),
                )

        ih1 = IndexHierarchy.from_labels(labels)
        ih2 = IndexHierarchy.from_labels(())

        post1 = ih1.union(ih2)
        self.assertEqual(post1.values.tolist(),
                [['II', 'B'], ['II', 'A'], ['I', 'B'], ['I', 'A']])

        post2 = ih1.intersection(ih2)
        self.assertEqual(post2.values.tolist(),
                [])

        post3 = ih1.difference(ih2)
        self.assertEqual(post3.values.tolist(),
                [['II', 'B'], ['II', 'A'], ['I', 'B'], ['I', 'A']])

    #---------------------------------------------------------------------------

    def test_hierarchy_unary_operators_a(self) -> None:

        labels = (
                (1, 1),
                (1, 2),
                (2, 1),
                (2, 2),
                )
        ih1 = IndexHierarchyGO.from_labels(labels)
        ih1.append((3, 1)) # force a recache state
        self.assertTrue(ih1._recache)

        self.assertEqual((-ih1).tolist(),
                [[-1, -1], [-1, -2], [-2, -1], [-2, -2], [-3, -1]]
                )



    #---------------------------------------------------------------------------
    def test_hierarchy_binary_operators_a(self) -> None:

        labels = (
                (1, 1),
                (1, 2),
                (2, 1),
                (2, 2),
                )
        ih1 = IndexHierarchy.from_labels(labels)
        self.assertEqual((ih1*2).tolist(),
                [[2, 2], [2, 4], [4, 2], [4, 4]])

        self.assertEqual((-ih1).tolist(),
                [[-1, -1], [-1, -2], [-2, -1], [-2, -2]])


    def test_hierarchy_binary_operators_b(self) -> None:

        labels = (
                (1, 1),
                (1, 2),
                )
        ih1 = IndexHierarchy.from_labels(labels)

        labels = (
                (3, 3),
                (1, 2),
                )
        ih2 = IndexHierarchy.from_labels(labels)

        self.assertEqual((ih1 @ ih2).tolist(),
                [[4, 5], [5, 7]]
                )

        self.assertEqual((ih1.values @ ih2).tolist(),
                [[4, 5], [5, 7]]
                )

        self.assertEqual((ih1 @ ih2.values).tolist(),
                [[4, 5], [5, 7]]
                )

        self.assertEqual((ih1.values @ ih2.values).tolist(),
                [[4, 5], [5, 7]]
                )



    def test_hierarchy_binary_operators_c(self) -> None:

        labels = (
                (1, 1),
                (1, 2),
                (2, 1),
                (2, 2),
                )
        ih1 = IndexHierarchyGO.from_labels(labels)

        a1 = ih1 * Index((1, 2, 3, 4))
        self.assertEqual(a1.tolist(), [[1, 1], [2, 4], [6, 3], [8, 8]])

        a2 = ih1 + ih1
        self.assertEqual(a2.tolist(), [[2, 2], [2, 4], [4, 2], [4, 4]])


    def test_hierarchy_binary_operators_d(self) -> None:

        labels = (
                (1, 1),
                (1, 2),
                )
        ih1 = IndexHierarchy.from_labels(labels)

        labels = (
                (3, 3),
                (1, 2),
                )
        ih2 = IndexHierarchy.from_labels(labels)

        a1 = ih1 @ ih2
        a2 = ih1.values.tolist() @ ih2 # force rmatmul
        self.assertEqual(a1.tolist(), a2.tolist())


    def test_hierarchy_binary_operators_e(self) -> None:

        labels = (
                (1, 1, 1),
                (2, 2, 2),
                )
        ih1 = IndexHierarchy.from_labels(labels)

        labels = (
                (1, 1, 1),
                (2, 2, 2),
                )
        ih2 = IndexHierarchy.from_labels(labels)

        a1 = ih1 == ih2
        self.assertEqual(a1.tolist(), [[True, True, True], [True, True, True]])


    def test_hierarchy_binary_operators_f(self) -> None:

        a1 = np.arange(25).reshape(5,5)
        a2 = np.arange(start=24, stop=-1, step=-1).reshape(5,5)

        f1_idx_labels = [
                ['i_I', 1, 'i'],
                ['i_I', 2, 'i'],
                ['i_I', 3, 'i'],
                ['i_II', 1, 'i'],
                ['i_II', 3, 'i']]

        f2_idx_labels = [
                ['i_II', 2, 'i'],
                ['i_II', 1, 'i'],
                ['i_I', 3, 'i'],
                ['i_I', 1, 'i'],
                ['i_I', 4, 'i']]

        f1 = Frame(a1, index=IndexHierarchy.from_labels(f1_idx_labels))
        f2 = Frame(a2, index=IndexHierarchy.from_labels(f2_idx_labels))
        int_index = f1.index.intersection(f2.index)

        post = f1.reindex(int_index).index == f2.reindex(int_index).index
        self.assertEqual(post.tolist(),
                [[True, True, True], [True, True, True], [True, True, True]])



    def test_hierarchy_binary_operators_g(self) -> None:

        a1 = np.arange(25).reshape(5,5)
        a2 = np.arange(start=24, stop=-1, step=-1).reshape(5,5)
        f1_idx_labels = [
                ['i_I', 'i'],
                ['i_I', 2],
                ['i_I', 'iii'],
                ['i_II', 'i'],
                ['i_III', 'ii']]

        f2_idx_labels = [
                ['i_IV', 'i'],
                ['i_II', 'ii'],
                ['i_I', 2],
                ['i_I', 'ii'],
                ['i_I', 'iii']]

        f1 = Frame(a1, index=IndexHierarchy.from_labels(f1_idx_labels)) #type: ignore
        f2 = Frame(a2, index=IndexHierarchy.from_labels(f2_idx_labels)) #type: ignore
        int_index = f1.index.intersection(f2.index)

        post = f1.reindex(int_index).index == f2.reindex(int_index).index
        self.assertEqual(post.tolist(),
                [[True, True], [True, True]]
                )

    def test_hierarchy_binary_operators_h(self) -> None:

        labels1 = (
                (1, 1),
                (2, 2),
                )
        ih1 = IndexHierarchy.from_labels(labels1)

        labels2 = (
                (1, 1, 1),
                (2, 2, 2),
                )
        ih2 = IndexHierarchy.from_labels(labels2)

        # for now, this returns na array of the shape of the left-hand opperatnd
        post1 = ih1 != ih2
        self.assertEqual(post1.shape, (2, 2))
        self.assertEqual(post1.all(), True)

        post2 = ih1 == ih2
        self.assertEqual(post2.shape, (2, 2))
        self.assertEqual(post2.any(), False)


    #---------------------------------------------------------------------------
    def test_hierarchy_flat_a(self) -> None:

        labels = (
                ('I', 'A'),
                ('I', 'B'),
                ('II', 'A'),
                ('II', 'B'),
                )

        ih = IndexHierarchy.from_labels(labels)
        self.assertEqual(ih.flat().values.tolist(),
                [('I', 'A'), ('I', 'B'), ('II', 'A'), ('II', 'B')]
                )


    #---------------------------------------------------------------------------
    def test_hierarchy_add_level_a(self) -> None:

        labels = (
                ('I', 'A'),
                ('I', 'B'),
                ('II', 'A'),
                ('II', 'B'),
                )

        ih = IndexHierarchy.from_labels(labels)
        ih2 = ih.add_level('b')

        self.assertEqual(ih2.values.tolist(),
                [['b', 'I', 'A'], ['b', 'I', 'B'], ['b', 'II', 'A'], ['b', 'II', 'B']])
        self.assertEqual([ih2.loc_to_iloc(tuple(x)) for x in ih2.values],
                [0, 1, 2, 3])


    def test_hierarchy_add_level_b(self) -> None:

        labels = (
                ('I', 'A'),
                ('I', 'B'),
                ('II', 'A'),
                ('II', 'B'),
                )

        ih1 = IndexHierarchyGO.from_labels(labels)
        ih1.append(('III', 'A'))
        ih2 = ih1.add_level('x')

        self.assertEqual(ih1.values.tolist(),
                [['I', 'A'], ['I', 'B'], ['II', 'A'], ['II', 'B'], ['III', 'A']])

        self.assertEqual(ih2.values.tolist(),
                [['x', 'I', 'A'], ['x', 'I', 'B'], ['x', 'II', 'A'], ['x', 'II', 'B'], ['x', 'III', 'A']])


    def test_hierarchy_add_level_c(self) -> None:

        labels = (
                (1, 'A'),
                (1, 'B'),
                (2, 'A'),
                (2, 'B'),
                )

        ih1 = IndexHierarchyGO.from_labels(labels)
        # force TB creation
        part = ih1.iloc[1:]
        ih2 = ih1.add_level('x')
        # proove we reused the underlying block arrays
        self.assertEqual(ih1._blocks.mloc.tolist(), ih2._blocks.mloc[1:].tolist())



    #---------------------------------------------------------------------------

    def test_hierarchy_drop_level_a(self) -> None:

        labels = (
                ('I', 'A', 1),
                ('I', 'B', 1),
                ('II', 'A', 1),
                ('II', 'B', 2),
                )

        ih = IndexHierarchy.from_labels(labels)
        ih2 = ih.drop_level(-1)

        self.assertEqual(ih2.values.tolist(),
                [['I', 'A'], ['I', 'B'], ['II', 'A'], ['II', 'B']])



    def test_hierarchy_drop_level_b(self) -> None:

        labels = (
                ('I', 'A', 1),
                ('I', 'B', 1),
                ('II', 'C', 1),
                ('II', 'C', 2),
                )

        ih = IndexHierarchy.from_labels(labels)
        ih2 = ih.drop_level(1)
        assert isinstance(ih2, IndexHierarchy)
        self.assertEqual(ih2.values.tolist(),
            [['A', 1], ['B', 1], ['C', 1], ['C', 2]])

        with self.assertRaises(ErrorInitIndex):
            ih2.drop_level(1)

    def test_hierarchy_drop_level_c(self) -> None:

        labels = (
                ('I', 'A', 1),
                ('I', 'B', 2),
                ('II', 'C', 3),
                ('II', 'C', 4),
                )

        ih = IndexHierarchy.from_labels(labels)
        self.assertEqual(ih.drop_level(1).values.tolist(),
                [['A', 1], ['B', 2], ['C', 3], ['C', 4]])

    def test_hierarchy_drop_level_d(self) -> None:

        labels = (
                ('A', 1),
                ('B', 2),
                ('C', 3),
                ('C', 4),
                )

        ih = IndexHierarchy.from_labels(labels)
        self.assertEqual(ih.drop_level(1).values.tolist(),
                [1, 2, 3, 4])


    def test_hierarchy_drop_level_e(self) -> None:

        ih = IndexHierarchy.from_product(('a',), (1,), ('x', 'y'))
        self.assertEqual(ih.drop_level(2).values.tolist(),
                ['x', 'y'])

        self.assertEqual(ih.drop_level(1).values.tolist(),
                [[1, 'x'], [1, 'y']])


    def test_hierarchy_drop_level_f(self) -> None:

        ih = IndexHierarchy.from_product(('a',), (1,), ('x',))
        self.assertEqual(ih.drop_level(1).values.tolist(),
                [[1, 'x']])

    def test_hierarchy_drop_level_g(self) -> None:

        ih = IndexHierarchy.from_product(('a',), (1,), ('x',))
        with self.assertRaises(NotImplementedError):
            _ = ih.drop_level(0)



    #---------------------------------------------------------------------------

    def test_hierarchy_boolean_loc(self) -> None:
        records = (
                ('a', 999999, 0.1),
                ('a', 201810, 0.1),
                ('b', 999999, 0.4),
                ('b', 201810, 0.4))
        f1 = Frame.from_records(records, columns=list('abc'))

        f1 = f1.set_index_hierarchy(['a', 'b'], drop=False)
        self.assertEqual(f1.index.names, ('a', 'b'))

        f2 = f1.loc[f1['b'] == 999999]

        self.assertEqual(f2.to_pairs(0),
                (('a', ((('a', 999999), 'a'), (('b', 999999), 'b'))), ('b', ((('a', 999999), 999999), (('b', 999999), 999999))), ('c', ((('a', 999999), 0.1), (('b', 999999), 0.4)))))

        f3 = f1.loc[Series([False, True], index=(('b', 999999), ('b', 201810)))]
        self.assertEqual(f3.to_pairs(0),
                (('a', ((('b', 201810), 'b'),)), ('b', ((('b', 201810), 201810),)), ('c', ((('b', 201810), 0.4),))))


    def test_hierarchy_name_a(self) -> None:

        idx1 = IndexHierarchy.from_product(list('ab'), list('xy'), name='q')
        self.assertEqual(idx1.name, 'q')

        idx2 = idx1.rename('w')
        self.assertEqual(idx2.name, 'w')
        # will provide one for each level
        self.assertEqual(idx2.names, ('__index0__', '__index1__'))


    def test_hierarchy_name_b(self) -> None:

        idx1 = IndexHierarchyGO.from_product(list('ab'), list('xy'), name='q')
        idx2 = idx1.rename('w')

        self.assertEqual(idx1.name, 'q')
        self.assertEqual(idx2.name, 'w')

        idx1.append(('c', 'c'))
        idx2.append(('x', 'x'))

        self.assertEqual(
                idx1.values.tolist(),
                [['a', 'x'], ['a', 'y'], ['b', 'x'], ['b', 'y'], ['c', 'c']]
                )

        self.assertEqual(
                idx2.values.tolist(),
                [['a', 'x'], ['a', 'y'], ['b', 'x'], ['b', 'y'], ['x', 'x']]
                )

    def test_hierarchy_name_c(self) -> None:

        idx1 = IndexHierarchyGO.from_product(list('ab'), list('xy'), name='q')
        idx2 = idx1.rename(('a', 'b', 'c'))

        # since the name attr is the wrong size, names use the generic from
        self.assertEqual(idx2.names, ('__index0__', '__index1__'))

    def test_hierarchy_name_d(self) -> None:

        idx1 = IndexHierarchy.from_product(list('ab'), list('xy'), name='q')
        self.assertEqual(idx1.name, 'q')


    def test_hierarchy_display_b(self) -> None:

        idx1 = IndexHierarchy.from_product(list('ab'), list('xy'), name='q')

        match = tuple(idx1.display(DisplayConfig(type_color=False)))

        self.assertEqual(
                match,
                (['<IndexHierarchy: q>', ''], ['a', 'x'], ['a', 'y'], ['b', 'x'], ['b', 'y'], ['<<U1>', '<<U1>'])
                )

    #---------------------------------------------------------------------------
    def test_hierarchy_to_frame_a(self) -> None:

        ih1 = IndexHierarchy.from_product(list('ab'), list('xy'), name='q')

        self.assertEqual(ih1.to_frame().to_pairs(0),
                ((0, ((0, 'a'), (1, 'a'), (2, 'b'), (3, 'b'))), (1, ((0, 'x'), (1, 'y'), (2, 'x'), (3, 'y'))))
                )

        f2 = ih1.to_frame_go()
        f2[-1] = None

        self.assertEqual(f2.to_pairs(0),
                ((0, ((0, 'a'), (1, 'a'), (2, 'b'), (3, 'b'))), (1, ((0, 'x'), (1, 'y'), (2, 'x'), (3, 'y'))), (-1, ((0, None), (1, None), (2, None), (3, None))))
                )


    def test_hierarchy_to_frame_b(self) -> None:

        ih1 = IndexHierarchy.from_product(list('ab'), [10.1, 20.2], name='q')
        f1 = ih1.to_frame()
        self.assertEqual(f1.dtypes.to_pairs(),
                ((0, np.dtype('<U1')), (1, np.dtype('float64')))
                )

    #---------------------------------------------------------------------------

    def test_hierarchy_to_html_datatables(self) -> None:

        ih1 = IndexHierarchy.from_product(list('ab'), list('xy'), name='q')

        with temp_file('.html', path=True) as fp:
            ih1.to_html_datatables(fp, show=False)
            with open(fp) as file:
                data = file.read()
                self.assertTrue('SFTable' in data)
                self.assertTrue(len(data) > 1000)


    def test_hierarchy_to_pandas_a(self) -> None:

        idx1 = IndexHierarchy.from_product(list('ab'), list('xy'), name='q')

        pdidx = idx1.to_pandas()
        self.assertEqual(pdidx.name, 'q')
        self.assertEqual(
                idx1.values.tolist(),
                [list(x) for x in pdidx.values.tolist()])



    def test_hierarchy_from_pandas_a(self) -> None:
        import pandas

        pdidx = pandas.MultiIndex.from_product((('I', 'II'), ('A', 'B')))

        idx = IndexHierarchy.from_pandas(pdidx)

        self.assertEqual(idx.values.tolist(),
                [['I', 'A'], ['I', 'B'], ['II', 'A'], ['II', 'B']]
                )


    def test_hierarchy_from_pandas_b(self) -> None:
        import pandas

        idx = IndexHierarchy.from_product(('I', 'II'), ('A', 'B'), (1, 2))

        self.assertEqual(list(idx.iter_label(0)), ['I', 'II'])
        self.assertEqual(list(idx.iter_label(1)), ['A', 'B', 'A', 'B'])
        self.assertEqual(list(idx.iter_label(2)), [1, 2, 1, 2, 1, 2, 1, 2])

        post = idx.iter_label(1).apply(lambda x: x.lower())
        self.assertEqual(post.to_pairs(),
                ((0, 'a'), (1, 'b'), (2, 'a'), (3, 'b')))



    def test_hierarchy_from_pandas_c(self) -> None:
        import pandas

        pdidx = pandas.MultiIndex.from_product((('I', 'II'), ('A', 'B')))

        idx = IndexHierarchyGO.from_pandas(pdidx)

        self.assertEqual(idx.values.tolist(),
                [['I', 'A'], ['I', 'B'], ['II', 'A'], ['II', 'B']]
                )

        self.assertEqual(idx.values.tolist(),
                [['I', 'A'], ['I', 'B'], ['II', 'A'], ['II', 'B']])

        idx.append(('III', 'A')) #type: ignore

        self.assertEqual(idx.values.tolist(),
                [['I', 'A'], ['I', 'B'], ['II', 'A'], ['II', 'B'], ['III', 'A']])


    def test_hierarchy_copy_a(self) -> None:

        labels = (
                ('I', 'A'),
                ('I', 'B'),
                ('II', 'A'),
                ('II', 'B'),
                )

        ih1 = IndexHierarchy.from_labels(labels)
        ih2 = ih1.copy()

        self.assertEqual(ih2.values.tolist(),
            [['I', 'A'], ['I', 'B'], ['II', 'A'], ['II', 'B']])



    def test_hierarchy_copy_b(self) -> None:

        labels = (
                ('I', 'A'),
                ('I', 'B'),
                ('II', 'A'),
                ('II', 'B'),
                )

        ih1 = IndexHierarchyGO.from_labels(labels)
        ih2 = ih1.copy()
        ih2.append(('II', 'C'))

        self.assertEqual(ih2.values.tolist(),
            [['I', 'A'], ['I', 'B'], ['II', 'A'], ['II', 'B'], ['II', 'C']]
            )

        self.assertEqual(ih1.values.tolist(),
            [['I', 'A'], ['I', 'B'], ['II', 'A'], ['II', 'B']]
            )

    #---------------------------------------------------------------------------

    def test_hierarchy_ufunc_axis_skipna_a(self) -> None:

        ih1 = IndexHierarchy.from_product((10, 20), (3.1, np.nan))

        self.assertAlmostEqualValues(
                ih1.sum(axis=1, skipna=False).tolist(),
                [13.1, np.nan, 23.1, np.nan])
        self.assertAlmostEqualValues(
                ih1.sum(axis=0, skipna=False).tolist(),
                [60.0, np.nan]
                )

    def test_hierarchy_ufunc_axis_skipna_b(self) -> None:

        ih1 = IndexHierarchy.from_product((10, 20), (3, 7))

        # sum applies to the labels
        self.assertEqual(ih1.sum().tolist(),
                [60, 20]
                )

        self.assertEqual(ih1.cumprod().tolist(),
                [[10, 3], [100, 21], [2000, 63], [40000, 441]]
                )


    #---------------------------------------------------------------------------

    def test_index_hierarchy_pickle_a(self) -> None:

        a = IndexHierarchy.from_product((10, 20), (3, 7))
        b = IndexHierarchy.from_product(('a', 'b'), ('x', 'y'))

        for index in (a, b):
            # force creating of ._labels
            self.assertTrue(len(index.values), len(index))

            pbytes = pickle.dumps(index)
            index_new = pickle.loads(pbytes)

            for v in index: # iter labels (arrays here)
                self.assertFalse(index_new.values.flags.writeable)
                self.assertEqual(index_new.loc[tuple(v)], index.loc[tuple(v)])


    # def test_index_hierarchy_get_a(self) -> None:

    #     ih1 = IndexHierarchy.from_product((10, 20), (3, 7))
    #     self.assertEqual(ih1.get((20, 3)), 2)
    #     self.assertEqual(ih1.get((20, 7)), 3)
    #     self.assertEqual(ih1.get((20, 200)), None)


    def test_index_hierarchy_sort_a(self) -> None:

        ih1 = IndexHierarchy.from_product((1, 2), (30, 70))

        self.assertEqual(ih1.sort(ascending=False).values.tolist(),
            [[2, 70], [2, 30], [1, 70], [1, 30]]
            )



    def test_index_hierarchy_isin_a(self) -> None:

        ih1 = IndexHierarchy.from_product((1, 2), (30, 70), (2, 5))

        post = ih1.isin([(2, 30, 2),])
        self.assertEqual(post.dtype, bool)
        self.assertEqual(post.tolist(),
            [False, False, False, False, True, False, False, False])

        extract = ih1.loc[post]
        self.assertEqual(extract.values.shape, (1, 3))


    def test_index_hierarchy_isin_b(self) -> None:

        ih1 = IndexHierarchy.from_product((1, 2), (30, 70), (2, 5))

        with self.assertRaises(RuntimeError):
            ih1.isin([3,4,5]) #type: ignore # not an iterable of iterables

        post = ih1.isin(([3,4], [2,5,1,5]))
        self.assertEqual(post.sum(), 0)


    def test_index_hierarchy_isin_c(self) -> None:

        ih1 = IndexHierarchy.from_product((1, 2), ('a', 'b'), (2, 5))

        # multiple matches

        post1 = ih1.isin([(1, 'a', 5), (2, 'b', 2)])
        self.assertEqual(post1.tolist(),
                [False, True, False, False, False, False, True, False])

        post2 = ih1.isin(ih1)
        self.assertEqual(post2.sum(), len(ih1))


    def test_index_hierarchy_isin_d(self) -> None:

        ih1 = IndexHierarchy.from_product((1, 2), (30, 70), (2, 5))

        # Index is an iterable
        index_iter1 = (val for val in (2, 30, 2))
        index_non_iter = (1, 70, 5)

        post = ih1.isin([index_iter1, index_non_iter])
        self.assertEqual(post.dtype, bool)
        self.assertEqual(post.tolist(),
            [False, False, False, True, True, False, False, False])

        extract = ih1.loc[post]
        self.assertEqual(extract.values.shape, (2, 3))

    def test_index_hierarchy_roll_a(self) -> None:

        ih1 = IndexHierarchy.from_product((1, 2), (30, 70))

        with self.assertRaises(RuntimeError):
            ih1.roll(1) # result in invalid tree form

        self.assertEqual(ih1.roll(2).values.tolist(),
            [[2, 30], [2, 70], [1, 30], [1, 70]]
            )


    def test_index_hierarchy_roll_b(self) -> None:

        ih1 = IndexHierarchy.from_labels((('a', 1), ('b', 20), ('c', 400), ('d', 50)))

        self.assertEqual(
                ih1.roll(1).values.tolist(),
                [['d', 50], ['a', 1], ['b', 20], ['c', 400]]
                )

        self.assertEqual(
                ih1.roll(-1).values.tolist(),
                [['b', 20], ['c', 400], ['d', 50], ['a', 1]]
                )

    def test_index_hierarchy_dtypes_a(self) -> None:
        idx1 = Index(('A', 'B'))
        idx2 = IndexDate.from_date_range('2019-01-05', '2019-01-08')
        idx3 = Index((1, 2))
        hidx = IndexHierarchy.from_product(idx1, idx2, idx3)

        self.assertEqual(
            [(x, y.kind) for x, y in hidx.dtypes.to_pairs()],
            [(0, 'U'), (1, 'M'), (2, 'i')]
            )

    def test_index_hierarchy_dtypes_b(self) -> None:
        idx1 = Index(('A', 'B'), name='a')
        idx2 = IndexDate.from_date_range('2019-01-05', '2019-01-08', name='b')
        idx3 = Index((1, 2), name='c')
        hidx = IndexHierarchy.from_product(idx1, idx2, idx3)

        self.assertEqual(
            [(x, y.kind) for x, y in hidx.dtypes.to_pairs()],
            [('a', 'U'), ('b', 'M'), ('c', 'i')]
            )

    def test_index_hierarchy_index_types_a(self) -> None:
        idx1 = Index(('A', 'B'))
        idx2 = IndexDate.from_date_range('2019-01-05', '2019-01-08')
        idx3 = Index((1, 2))
        hidx = IndexHierarchy.from_product(idx1, idx2, idx3)

        self.assertEqual(
            [(x, y.__name__) for x, y in hidx.index_types.to_pairs()],
            [(0, 'Index'), (1, 'IndexDate'), (2, 'Index')]
            )

    def test_index_hierarchy_index_types_b(self) -> None:
        idx1 = Index(('A', 'B'), name='a')
        idx2 = IndexDate.from_date_range('2019-01-05', '2019-01-08', name='b')
        idx3 = Index((1, 2), name='c')
        hidx = IndexHierarchy.from_product(idx1, idx2, idx3)

        self.assertEqual(
            [(x, y.__name__) for x, y in hidx.index_types.to_pairs()],
            [('a', 'Index'), ('b', 'IndexDate'), ('c', 'Index')]
            )


    #---------------------------------------------------------------------------
    def test_index_hierarchy_label_widths_at_depth_a(self) -> None:
        idx1 = Index(('A', 'B'), name='a')
        idx2 = IndexDate.from_date_range('2019-01-05', '2019-01-08', name='b')
        idx3 = Index((1, 2), name='c')
        hidx = IndexHierarchy.from_product(idx1, idx2, idx3)

        self.assertEqual(tuple(hidx.label_widths_at_depth(0)),
                (('A', 8), ('B', 8))
                )

        self.assertEqual(tuple(hidx.label_widths_at_depth(1)),
                ((np.datetime64('2019-01-05'), 2), (np.datetime64('2019-01-06'), 2), (np.datetime64('2019-01-07'), 2), (np.datetime64('2019-01-08'), 2), (np.datetime64('2019-01-05'), 2), (np.datetime64('2019-01-06'), 2), (np.datetime64('2019-01-07'), 2), (np.datetime64('2019-01-08'), 2))
                )

        self.assertEqual(tuple(hidx.label_widths_at_depth(2)),
                ((1, 1), (2, 1), (1, 1), (2, 1), (1, 1), (2, 1), (1, 1), (2, 1), (1, 1), (2, 1), (1, 1), (2, 1), (1, 1), (2, 1), (1, 1), (2, 1))
                )


    def test_index_hierarchy_label_widths_at_depth_b(self) -> None:
        idx1 = Index(('A', 'B'), name='a')
        idx2 = IndexDate.from_date_range('2019-01-05', '2019-01-08', name='b')
        idx3 = Index((1, 2), name='c')
        hidx = IndexHierarchy.from_product(idx1, idx2, idx3)


        with self.assertRaises(NotImplementedError):
            _ = next(hidx.label_widths_at_depth(None))



    #---------------------------------------------------------------------------

    def test_index_hierarchy_astype_a(self) -> None:

        ih1 = IndexHierarchy.from_product((1, 2), ('a', 'b'), (2, 5))

        ih2 = ih1.astype[[0, 2]](float)

        self.assertEqual(ih2.dtypes.values.tolist(),
                [np.dtype('float64'), np.dtype('<U1'), np.dtype('float64')])


    def test_index_hierarchy_astype_b(self) -> None:

        ih1 = IndexHierarchy.from_product((1, 2), (100, 200))
        ih2 = ih1.astype(float)
        self.assertEqual(ih2.dtypes.values.tolist(),
                [np.dtype('float64'), np.dtype('float64')])


    def test_index_hierarchy_astype_c(self) -> None:
        ih1 = IndexHierarchy.from_product((1, 2), (100, 200), ('2020-01', '2020-03'))

        self.assertEqual(
                ih1.astype[[0, 1]](float).dtypes.to_pairs(),
                ((0, np.dtype('float64')), (1, np.dtype('float64')), (2, np.dtype('<U7')))
                )


    def test_index_hierarchy_astype_d(self) -> None:
        ih1 = IndexHierarchy.from_product(
            ('1945-01-02', '1843-07-07'), ('2020-01', '2020-03'))

        self.assertEqual(
                ih1.astype('datetime64[M]').index_types.to_pairs(),
                ((0, IndexYearMonth),
                (1, IndexYearMonth))
                )

    @skip_win #type: ignore
    def test_index_hierarchy_astype_e(self) -> None:
        ih1 = IndexHierarchy.from_product((1, 2), (100, 200), ('2020-01', '2020-03'))

        self.assertEqual(
                ih1.astype[[0, 1]](float).dtypes.to_pairs(),
                ((0, np.dtype('float64')), (1, np.dtype('float64')), (2, np.dtype('<U7')))
                )

        ih2 = ih1.astype[2]('datetime64[M]')

        self.assertEqual(
                ih2.dtypes.to_pairs(),
                ((0, np.dtype('int64')), (1, np.dtype('int64')), (2, np.dtype('<M8[M]')))
                )

        self.assertEqual(ih2.index_types.to_pairs(),
                ((0, Index), (1, Index), (2, IndexYearMonth))
                )

        post = ih2.loc[HLoc[:, 200, '2020-03']]
        self.assertEqual(post.shape, (2, 3))
        self.assertEqual(post.dtypes.to_pairs(),
                ((0, np.dtype('int64')), (1, np.dtype('int64')), (2, np.dtype('<M8[M]')))
                )


    #---------------------------------------------------------------------------

    @skip_win #type: ignore
    def test_index_hierarchy_values_at_depth_a(self) -> None:
        ih1 = IndexHierarchy.from_product((1, 2), (100, 200), ('2020-01', '2020-03'))
        post = ih1.values_at_depth([0, 1])
        self.assertEqual(post.shape, (8, 2))
        self.assertEqual(post.dtype, np.dtype(int))
        self.assertEqual(ih1.values_at_depth(2).dtype, np.dtype('<U7'))


    #---------------------------------------------------------------------------

    def test_index_hierarchy_head_a(self) -> None:

        ih1 = IndexHierarchy.from_product((1, 2), ('a', 'b'), (2, 5))

        self.assertEqual(ih1.head().values.tolist(),
            [[1, 'a', 2], [1, 'a', 5], [1, 'b', 2], [1, 'b', 5], [2, 'a', 2]]
            )

    def test_index_hierarchy_tail_a(self) -> None:

        ih1 = IndexHierarchy.from_product((1, 2), ('a', 'b'), (2, 5))

        self.assertEqual(ih1.tail().values.tolist(),
            [[1, 'b', 5], [2, 'a', 2], [2, 'a', 5], [2, 'b', 2], [2, 'b', 5]]
            )

    #---------------------------------------------------------------------------


if __name__ == '__main__':
    unittest.main()
