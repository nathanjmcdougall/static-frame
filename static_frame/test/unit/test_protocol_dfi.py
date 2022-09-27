import frame_fixtures as ff
import numpy as np

from static_frame.core.frame import Frame
from static_frame.core.index import Index
from static_frame.core.protocol_dfi import ArrowCType
from static_frame.core.protocol_dfi import DFIBuffer
from static_frame.core.protocol_dfi import DFIColumn
from static_frame.core.protocol_dfi import DFIDataFrame
from static_frame.core.protocol_dfi import np_dtype_to_dfi_dtype
from static_frame.core.protocol_dfi_abc import ColumnNullType
from static_frame.core.protocol_dfi_abc import DlpackDeviceType
from static_frame.core.protocol_dfi_abc import DtypeKind
from static_frame.core.series import Series
from static_frame.core.util import NAT
from static_frame.test.test_case import TestCase


class TestUnit(TestCase):

    def test_arrow_ctype_a(self):
        self.assertEqual(ArrowCType.from_dtype(np.dtype(np.float64)), 'g')
        self.assertEqual(ArrowCType.from_dtype(np.dtype(np.float32)), 'f')
        self.assertEqual(ArrowCType.from_dtype(np.dtype(np.float16)), 'e')

        self.assertEqual(ArrowCType.from_dtype(np.dtype(np.int64)), 'l')
        self.assertEqual(ArrowCType.from_dtype(np.dtype(np.int8)), 'c')

        self.assertEqual(ArrowCType.from_dtype(np.dtype(bool)), 'b')

        self.assertEqual(ArrowCType.from_dtype(np.dtype(np.uint64)), 'L')
        self.assertEqual(ArrowCType.from_dtype(np.dtype(np.uint8)), 'C')

    def test_arrow_ctype_b(self):
        with self.assertRaises(NotImplementedError):
            ArrowCType.from_dtype(np.dtype(object))

    def test_arrow_ctype_c(self):
        self.assertEqual(ArrowCType.from_dtype(np.dtype(str)), 'u')

    def test_arrow_ctype_d(self):
        self.assertEqual(ArrowCType.from_dtype(np.dtype(np.datetime64('2022-01-01'))), 'tdm')

    def test_arrow_ctype_e(self):
        self.assertEqual(ArrowCType.from_dtype(np.dtype(np.datetime64('2022-01-01T01:01:01'))), 'tts')
        self.assertEqual(ArrowCType.from_dtype(np.dtype(np.datetime64('2022-01-01', 'ns'))), 'ttn')

    def test_arrow_ctype_f(self):
        with self.assertRaises(NotImplementedError):
            ArrowCType.from_dtype(np.dtype(np.datetime64('2022-01')))

    def test_arrow_ctype_g(self):
        with self.assertRaises(NotImplementedError):
            ArrowCType.from_dtype(np.dtype(complex))

    #---------------------------------------------------------------------------
    def test_np_dtype_to_dfi_dtype_a(self):
        self.assertEqual(np_dtype_to_dfi_dtype(
                np.dtype(bool)),
                (DtypeKind.BOOL, 8, 'b', '='),
                )

    def test_np_dtype_to_dfi_dtype_b(self):
        self.assertEqual(np_dtype_to_dfi_dtype(
                np.dtype(np.float64)),
                (DtypeKind.FLOAT, 64, 'g', '='),
                )

    def test_np_dtype_to_dfi_dtype_c(self):
        self.assertEqual(np_dtype_to_dfi_dtype(
                np.dtype(np.uint8)),
                (DtypeKind.UINT, 8, 'C', '='),
                )

    #---------------------------------------------------------------------------
    def test_dfi_buffer_a(self):
        dfib = DFIBuffer(np.array((True, False)))
        self.assertEqual(str(dfib), '<DFIBuffer: shape=(2,) dtype=|b1>')
        self.assertTrue(dfib.__array__().data.contiguous)

    def test_dfi_buffer_b(self):
        dfib = DFIBuffer((np.arange(12).reshape(6, 2) % 3 == 0)[:, 0])
        self.assertEqual(str(dfib), '<DFIBuffer: shape=(6,) dtype=|b1>')
        self.assertTrue(dfib.__array__().data.contiguous)

    def test_dfi_buffer_array_a(self):
        a1 = np.array((True, False))
        dfib = DFIBuffer(a1)
        self.assertEqual(dfib.__array__().tolist(), a1.tolist())

    def test_dfi_buffer_array_b(self):
        a1 = np.array((True, False))
        dfib = DFIBuffer(a1)
        self.assertEqual(dfib.__array__(str).tolist(), a1.astype(str).tolist())

    def test_dfi_buffer_bufsize_a(self):
        a1 = np.array((True, False))
        dfib = DFIBuffer(a1)
        self.assertEqual(dfib.bufsize, 2)

    def test_dfi_buffer_ptr_a(self):
        a1 = np.array((True, False))
        dfib = DFIBuffer(a1)
        self.assertEqual(dfib.ptr, a1.__array_interface__['data'][0])

    def test_dfi_buffer_dlpack_a(self):
        a1 = np.array((True, False))
        dfib = DFIBuffer(a1)
        with self.assertRaises(NotImplementedError):
            dfib.__dlpack__()

    def test_dfi_buffer_dlpack_device_a(self):
        a1 = np.array((True, False))
        dfib = DFIBuffer(a1)
        self.assertEqual(dfib.__dlpack_device__(), (DlpackDeviceType.CPU, None))

    #---------------------------------------------------------------------------

    def test_dfi_column_init_a(self) -> None:
        a1 = np.array((True, False))
        idx1 = Index(('a', 'b'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(str(dfic), '<DFIColumn: shape=(2,) dtype=|b1>')

    def test_dfi_column_array_a(self):
        a1 = np.array((True, False))
        idx1 = Index(('a', 'b'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(dfic.__array__().tolist(), a1.tolist())

    def test_dfi_column_array_b(self):
        a1 = np.array((True, False))
        idx1 = Index(('a', 'b'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(dfic.__array__(str).tolist(), a1.astype(str).tolist())

    def test_dfi_column_size_a(self):
        a1 = np.array((True, False))
        idx1 = Index(('a', 'b'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(dfic.size(), 2)

    def test_dfi_column_offset_a(self):
        a1 = np.array((True, False))
        idx1 = Index(('a', 'b'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(dfic.offset, 0)

    def test_dfi_column_dtype_a(self):
        a1 = np.array((True, False))
        idx1 = Index(('a', 'b'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(dfic.dtype, (DtypeKind.BOOL, 8, 'b', '='))

    def test_dfi_column_dtype_b(self):
        a1 = np.array((1.1, 2.2), dtype=np.float64)
        idx1 = Index(('a', 'b'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(dfic.dtype, (DtypeKind.FLOAT, 64, 'g', '='))

    def test_dfi_column_dtype_c(self):
        a1 = np.array((1.1, 2.2), dtype=np.float16)
        idx1 = Index(('a', 'b'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(dfic.dtype, (DtypeKind.FLOAT, 16, 'e', '='))

    def test_dfi_column_describe_categorical_a(self):
        a1 = np.array((1.1, 2.2), dtype=np.float64)
        idx1 = Index(('a', 'b'))
        dfic = DFIColumn(a1, idx1)
        with self.assertRaises(TypeError):
            dfic.describe_categorical()

    def test_dfi_column_describe_null_a(self):
        a1 = np.array((1.1, 2.2, np.nan), dtype=np.float64)
        idx1 = Index(('a', 'b', 'c'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(dfic.describe_null, (ColumnNullType.USE_NAN, None))

    def test_dfi_column_describe_null_b(self):
        a1 = np.array(('2020-01', '2022-05', NAT), dtype=np.datetime64)
        idx1 = Index(('a', 'b', 'c'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(dfic.describe_null, (ColumnNullType.USE_SENTINEL, NAT))

    def test_dfi_column_describe_null_c(self):
        a1 = np.array((3, 4))
        idx1 = Index(('a', 'b'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(dfic.describe_null, (ColumnNullType.NON_NULLABLE, None))

    def test_dfi_column_null_count_a(self):
        a1 = np.array((1.1, 2.2, np.nan), dtype=np.float64)
        idx1 = Index(('a', 'b', 'c'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(dfic.null_count, 1)

    def test_dfi_column_null_count_b(self):
        a1 = np.array(('2020-01', '2022-05', NAT), dtype=np.datetime64)
        idx1 = Index(('a', 'b', 'c'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(dfic.null_count, 1)

    def test_dfi_column_null_count_c(self):
        a1 = np.array((3, 4))
        idx1 = Index(('a', 'b'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(dfic.null_count, 0)

    def test_dfi_column_metadata_a(self):
        a1 = np.array((3, 4))
        idx1 = Index(('a', 'b'))
        dfic = DFIColumn(a1, idx1)
        [(mk, mv)] = dfic.metadata.items()
        self.assertEqual(mk, 'static-frame.index')
        self.assertTrue(mv.equals(mv))

    def test_dfi_column_num_chunks_a(self):
        a1 = np.array((3, 4))
        idx1 = Index(('a', 'b'))
        dfic = DFIColumn(a1, idx1)
        self.assertEqual(dfic.num_chunks(), 1)

    def test_dfi_column_chunks_a(self):
        a1 = np.arange(5)
        idx1 = Index(('a', 'b', 'c', 'd', 'e'))
        dfic = DFIColumn(a1, idx1)
        post = tuple(dfic.get_chunks(2))

        self.assertEqual(
                [c.__array__().tolist() for c in post],
                [[0, 1, 2], [3, 4]],
                )

    def test_dfi_column_chunks_b(self):
        a1 = np.arange(5)
        idx1 = Index(('a', 'b', 'c', 'd', 'e'))
        dfic = DFIColumn(a1, idx1)
        post = tuple(dfic.get_chunks(5))

        self.assertEqual(
                [c.__array__().tolist() for c in post],
                [[0], [1], [2], [3], [4]],
                )

    def test_dfi_column_chunks_c(self):
        a1 = np.arange(5)
        idx1 = Index(('a', 'b', 'c', 'd', 'e'))
        dfic = DFIColumn(a1, idx1)
        post = tuple(dfic.get_chunks(1))

        self.assertEqual(
                [c.__array__().tolist() for c in post],
                [[0, 1, 2, 3, 4]],
                )

    def test_dfi_column_get_buffers_a(self):
        a1 = np.array((1.1, 2.2, np.nan), dtype=np.float64)
        idx1 = Index(('a', 'b', 'c'))
        dfic = DFIColumn(a1, idx1)
        post = dfic.get_buffers()

        self.assertEqual(str(post['data'][0]), '<DFIBuffer: shape=(3,) dtype=<f8>')
        self.assertEqual(post['data'][1], (DtypeKind.FLOAT, 64, 'g', '='))

        self.assertEqual(str(post['validity'][0]), '<DFIBuffer: shape=(3,) dtype=|b1>')
        self.assertEqual(post['validity'][1], (DtypeKind.BOOL, 8, 'b', '='))

        self.assertEqual(post['offsets'], None)

    def test_dfi_column_get_buffers_b(self):
        a1 = np.array((False, True, False), dtype=bool)
        idx1 = Index(('a', 'b', 'c'))
        dfic = DFIColumn(a1, idx1)
        post = dfic.get_buffers()

        self.assertEqual(str(post['data'][0]), '<DFIBuffer: shape=(3,) dtype=|b1>')
        self.assertEqual(post['data'][1], (DtypeKind.BOOL, 8, 'b', '='))

        self.assertEqual(post['validity'], None)
        self.assertEqual(post['offsets'], None)

    #---------------------------------------------------------------------------

        # import ipdb; ipdb.set_trace()


if __name__ == '__main__':
    import unittest
    unittest.main()