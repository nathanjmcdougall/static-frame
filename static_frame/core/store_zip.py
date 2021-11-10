import typing as tp
import zipfile
import pickle
from io import StringIO
from io import BytesIO
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import Future
# import multiprocessing as mp
# mp_context = mp.get_context('spawn')

from static_frame.core.frame import Frame
from static_frame.core.store import Store
from static_frame.core.store import store_coherent_non_write
from static_frame.core.store import store_coherent_write
from static_frame.core.store import StoreConfigMap
from static_frame.core.store import StoreConfig
from static_frame.core.store import StoreConfigHE
from static_frame.core.store import StoreConfigMapInitializer
from static_frame.core.util import AnyCallable
from static_frame.core.container_util import container_to_exporter_attr


# class FrameExporter(tp.Protocol):
#     def __call__(self, frame: Frame, *args: tp.Any, **kwargs: tp.Any) -> tp.Any:
#         raise NotImplementedError

FrameExporter = AnyCallable # Protocol not supported yet...
FrameConstructor = tp.Callable[[tp.Any], Frame]
LabelAndBytes = tp.Tuple[tp.Hashable, tp.Union[str, bytes]]

class PayloadBytesToFrame(tp.NamedTuple):
    '''
    Defines the necessary objects to construct a Frame. Used for multiprocessing.
    '''
    src: bytes
    name: tp.Hashable
    config: StoreConfigHE
    constructor: FrameConstructor

class PayloadFrameToBytes(tp.NamedTuple):
    '''
    Defines the necessary objects to construct writeable Frame bytes. Used for multiprocessing.
    '''
    name: tp.Hashable
    config: StoreConfigHE
    frame: Frame
    exporter: FrameExporter


class _StoreZip(Store):

    _EXT: tp.FrozenSet[str] = frozenset(('.zip',))
    _EXT_CONTAINED: str = ''
    _EXPORTER: AnyCallable

    @classmethod
    def _container_type_to_constructor(cls, container_type: tp.Type[Frame]) -> FrameConstructor:
        raise NotImplementedError

    @staticmethod
    def _build_frame(
            src: bytes,
            name: tp.Hashable,
            config: tp.Union[StoreConfigHE, StoreConfig],
            constructor: FrameConstructor,
            ) -> Frame:
        raise NotImplementedError

    @classmethod
    def _payload_to_frame(cls, payload: PayloadBytesToFrame) -> Frame:
        '''
        Single argument wrapper for _build_frame().
        '''
        return cls._build_frame(
                src=payload.src,
                name=payload.name,
                config=payload.config,
                constructor=payload.constructor,
                )

    @classmethod
    def _payloads_to_frames(cls,
            payloads: tp.List[PayloadBytesToFrame],
            ) -> tp.List[Frame]:
        '''
        Single argument wrapper for _build_frame().
        '''
        return [cls._payload_to_frame(payload) for payload in payloads]

    @staticmethod
    def _set_container_type(frame: Frame, container_type: tp.Type[Frame]) -> Frame:
        """
        Helper method to coerce a frame to the expected type, or return it as is
        if the type is already correct
        """
        if frame.__class__ is not container_type:
            return frame._to_frame(container_type)
        return frame

    @store_coherent_non_write
    def labels(self, *,
            config: StoreConfigMapInitializer = None,
            strip_ext: bool = True,
            ) -> tp.Iterator[tp.Hashable]:

        config_map = StoreConfigMap.from_initializer(config)

        with zipfile.ZipFile(self._fp) as zf:
            for name in zf.namelist():
                if strip_ext:
                    name = name.replace(self._EXT_CONTAINED, '')
                # always use default decoder
                yield config_map.default.label_decode(name)

    @store_coherent_non_write
    def _read_many_single_thread(self,
            labels: tp.Iterable[tp.Hashable],
            *,
            config_map: StoreConfigMap,
            constructor: FrameConstructor,
            container_type: tp.Type[Frame],
            ) -> tp.Iterator[Frame]:
        """
        Simplified logic path for reading many frames in a single thread, using
        the weak_cache when possible.
        """
        not_in_cache_sentinel = object()

        with zipfile.ZipFile(self._fp) as zf:
            for label in labels:
                # Since the value can be deallocated between lookup & extraction,
                # we have to handle it with `get`` & a sentinel to ensure we
                # don't have a race condition
                cache_lookup = self._weak_cache.get(label, not_in_cache_sentinel)
                if cache_lookup is not not_in_cache_sentinel:
                    yield self._set_container_type(cache_lookup, container_type)
                    return

                c: StoreConfig = config_map[label]

                label_encoded: str = config_map.default.label_encode(label)
                src: bytes = zf.read(label_encoded + self._EXT_CONTAINED)

                frame = self._build_frame(
                        src=src,
                        name=label,
                        config=c,
                        constructor=constructor,
                )
                # Newly read frame, add it to our weak_cache
                self._weak_cache[label] = frame
                yield frame

    @store_coherent_non_write
    def read_many(self,
            labels: tp.Iterable[tp.Hashable],
            *,
            config: StoreConfigMapInitializer = None,
            container_type: tp.Type[Frame] = Frame,
            ) -> tp.Iterator[Frame]:

        config_map = StoreConfigMap.from_initializer(config)
        multiprocess: bool = config_map.default.read_max_workers is not None
        constructor: FrameConstructor = self._container_type_to_constructor(container_type)

        if not multiprocess:
            yield from self._read_many_single_thread(
                    labels=labels,
                    config_map=config_map,
                    constructor=constructor,
                    container_type=container_type,
            )
            return

        # To ensure race-conditions don't happen, and to simplifiy the code
        # we lock in the state of our weak_cache for the rest of the function
        strong_cache = dict(self._weak_cache)

        def gen_multiprocess() -> tp.Iterator[PayloadBytesToFrame]:
            with zipfile.ZipFile(self._fp) as zf:
                for label in labels:
                    if label in strong_cache:
                        continue

                    c: StoreConfig = config_map[label]

                    label_encoded: str = config_map.default.label_encode(label)
                    src: bytes = zf.read(label_encoded + self._EXT_CONTAINED)

                    yield PayloadBytesToFrame( # pylint: disable=no-value-for-parameter
                            src=src,
                            name=label,
                            config=c.to_store_config_he(),
                            constructor=constructor,
                    )

        cache_hits = sum(label in strong_cache for label in labels)

        # Avoid spinning up a process pool if all requested labels have weakrefs
        if cache_hits == len(labels):
            for label in labels:
                yield self._set_container_type(strong_cache[label], container_type)
            return

        payload_iter = gen_multiprocess()
        chunksize = config_map.default.read_chunksize

        if not cache_hits:
            # Simplify the logic for cases when nothing exists in our cache
            with ProcessPoolExecutor(max_workers=config_map.default.read_max_workers) as executor:
                for label, frame in zip(
                        labels,
                        executor.map(self._payload_to_frame, payload_iter, chunksize=chunksize)
                        ):
                    # Newly read frame, add it to our weak_cache
                    self._weak_cache[label] = frame
                    yield frame
                return

        # We have a case where there are some cache hits, and some cache misses
        with ProcessPoolExecutor(max_workers=config_map.default.read_max_workers) as executor:
            futures: tp.List[Future[tp.List[Frame]]] = []

            current_chunk: tp.List[PayloadBytesToFrame] = []
            for label in labels:
                if label in strong_cache:
                    continue

                current_chunk.append(next(payload_iter))

                if len(current_chunk) == chunksize:
                    futures.append(executor.submit(self._payloads_to_frames, current_chunk))
                    current_chunk = []

            if current_chunk:
                futures.append(executor.submit(self._payloads_to_frames, current_chunk))
                current_chunk = []

            futures_iter = iter(futures)
            current_future = iter(next(futures_iter).result())

            for label in labels:
                if label in strong_cache:
                    yield self._set_container_type(strong_cache[label], container_type)
                    continue

                try:
                    frame = next(current_future)
                except StopIteration:
                    current_future = iter(next(futures_iter).result())
                    frame = next(current_future)

                # Newly read frame, add it to our weak_cache
                self._weak_cache[label] = frame
                yield frame

    # --------------------------------------------------------------------------

    @staticmethod
    def _payload_to_bytes(payload: PayloadFrameToBytes) -> LabelAndBytes:
        raise NotImplementedError('implement on derived class') #pragma: no cover

    @store_coherent_write
    def write(self,
            items: tp.Iterable[tp.Tuple[tp.Hashable, Frame]],
            *,
            config: StoreConfigMapInitializer = None
            ) -> None:
        config_map = StoreConfigMap.from_initializer(config)
        multiprocess = (config_map.default.write_max_workers is not None and
                        config_map.default.write_max_workers > 1)

        def gen() -> tp.Iterable[PayloadFrameToBytes]:
            for label, frame in items:
                yield PayloadFrameToBytes( # pylint: disable=no-value-for-parameter
                        name=label,
                        config=config_map[label].to_store_config_he(),
                        frame=frame,
                        exporter=self.__class__._EXPORTER,
                        )

        if multiprocess:
            def label_and_bytes() -> tp.Iterator[LabelAndBytes]:
                with ProcessPoolExecutor(max_workers=config_map.default.write_max_workers) as executor:
                    yield from executor.map(self._payload_to_bytes,
                            gen(),
                            chunksize=config_map.default.write_chunksize)
        else:
            label_and_bytes = lambda: (self._payload_to_bytes(x) for x in gen())

        with zipfile.ZipFile(self._fp, 'w', zipfile.ZIP_DEFLATED) as zf:
            for label, frame_bytes in label_and_bytes():
                label_encoded = config_map.default.label_encode(label)
                # this will write it without a container
                zf.writestr(label_encoded + self._EXT_CONTAINED, frame_bytes)


class _StoreZipDelimited(_StoreZip):
    # store attribute of passed-in container_type to use for construction
    _EXPORTER_ATTR: str
    _CONSTRUCTOR_ATTR: str

    @classmethod
    def _container_type_to_constructor(cls, container_type: tp.Type[Frame]) -> FrameConstructor:
        return getattr(container_type, cls._CONSTRUCTOR_ATTR) # type: ignore

    @staticmethod
    def _build_frame(
            src: bytes,
            name: tp.Hashable,
            config: tp.Union[StoreConfigHE, StoreConfig],
            constructor: FrameConstructor,
            ) -> Frame:

        return constructor( # type: ignore
            StringIO(src.decode()),
            index_depth=config.index_depth,
            index_name_depth_level=config.index_name_depth_level,
            index_constructors=config.index_constructors,
            columns_depth=config.columns_depth,
            columns_name_depth_level=config.columns_name_depth_level,
            columns_constructors=config.columns_constructors,
            dtypes=config.dtypes,
            name=name,
            consolidate_blocks=config.consolidate_blocks,
            )

    @staticmethod
    def _payload_to_bytes(payload: PayloadFrameToBytes) -> LabelAndBytes:
        c = payload.config

        dst = StringIO()
        # call from class to explicitly pass self as frame
        payload.exporter(payload.frame,
                dst,
                include_index=c.include_index,
                include_index_name=c.include_index_name,
                include_columns=c.include_columns,
                include_columns_name=c.include_columns_name
                )
        return payload.name, dst.getvalue()


class StoreZipTSV(_StoreZipDelimited):
    '''
    Store of TSV files contained within a ZIP file.
    '''
    _EXT_CONTAINED = '.txt'
    _EXPORTER = Frame.to_tsv
    _CONSTRUCTOR_ATTR = Frame.from_tsv.__name__


class StoreZipCSV(_StoreZipDelimited):
    '''
    Store of CSV files contained within a ZIP file.
    '''
    _EXT_CONTAINED = '.csv'
    _EXPORTER = Frame.to_csv
    _CONSTRUCTOR_ATTR = Frame.from_csv.__name__


#-------------------------------------------------------------------------------

class StoreZipPickle(_StoreZip):
    '''A zip of pickles, permitting incremental loading of Frames.
    '''
    _EXT_CONTAINED = '.pickle'
    _EXPORTER = pickle.dumps

    @classmethod
    def _container_type_to_constructor(cls, container_type: tp.Type[Frame]) -> FrameConstructor:
        return pickle.loads

    @staticmethod
    def _build_frame(
            src: bytes,
            name: tp.Hashable,
            config: tp.Union[StoreConfigHE, StoreConfig],
            constructor: FrameConstructor,
        ) -> Frame:
        return constructor(src)

    @store_coherent_non_write
    def read_many(self,
            labels: tp.Iterable[tp.Hashable],
            *,
            config: StoreConfigMapInitializer = None,
            container_type: tp.Type[Frame] = Frame,
            ) -> tp.Iterator[Frame]:

        exporter = container_to_exporter_attr(container_type)

        for frame in _StoreZip.read_many(self,
                labels,
                config=config,
                container_type=container_type,
                ):
            if frame.__class__ is container_type:
                yield frame
            else:
                yield getattr(frame, exporter)()

    @staticmethod
    def _payload_to_bytes(payload: PayloadFrameToBytes) -> LabelAndBytes:
        return payload.name, payload.exporter(payload.frame)

#-------------------------------------------------------------------------------
class StoreZipNPZ(_StoreZip):
    '''A zip of npz files, permitting incremental loading of Frames.
    '''
    _EXT_CONTAINED = '.npz'
    _EXPORTER = Frame.to_npz

    @classmethod
    def _container_type_to_constructor(cls, container_type: tp.Type[Frame]) -> FrameConstructor:
        return container_type.from_npz

    @staticmethod
    def _build_frame(
            src: bytes,
            name: tp.Hashable,
            config: tp.Union[StoreConfigHE, StoreConfig],
            constructor: FrameConstructor,
        ) -> Frame:
        return constructor(
            BytesIO(src),
            )

    @staticmethod
    def _payload_to_bytes(payload: PayloadFrameToBytes) -> LabelAndBytes:
        c = payload.config
        dst = BytesIO()
        payload.exporter(payload.frame,
                dst,
                include_index=c.include_index,
                include_columns=c.include_columns,
                )
        return payload.name, dst.getvalue()

#-------------------------------------------------------------------------------

class StoreZipParquet(_StoreZip):
    '''A zip of parquet files, permitting incremental loading of Frames.
    '''
    _EXT_CONTAINED = '.parquet'
    _EXPORTER = Frame.to_parquet

    @classmethod
    def _container_type_to_constructor(cls, container_type: tp.Type[Frame]) -> FrameConstructor:
        return container_type.from_parquet

    @staticmethod
    def _build_frame(
            src: bytes,
            name: tp.Hashable,
            config: tp.Union[StoreConfigHE, StoreConfig],
            constructor: FrameConstructor,
        ) -> Frame:
        return constructor( # type: ignore
            BytesIO(src),
            index_depth=config.index_depth,
            index_name_depth_level=config.index_name_depth_level,
            index_constructors=config.index_constructors,
            columns_depth=config.columns_depth,
            columns_name_depth_level=config.columns_name_depth_level,
            columns_constructors=config.columns_constructors,
            columns_select=config.columns_select,
            dtypes=config.dtypes,
            name=name,
            consolidate_blocks=config.consolidate_blocks,
            )

    @staticmethod
    def _payload_to_bytes(payload: PayloadFrameToBytes) -> LabelAndBytes:
        c = payload.config

        dst = BytesIO()
        payload.exporter(payload.frame,
                dst,
                include_index=c.include_index,
                include_index_name=c.include_index_name,
                include_columns=c.include_columns,
                include_columns_name=c.include_columns_name,
                )
        return payload.name, dst.getvalue()
