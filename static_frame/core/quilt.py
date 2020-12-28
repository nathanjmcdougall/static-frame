import typing as tp
from itertools import zip_longest

import numpy as np

from static_frame.core.container import ContainerBase
from static_frame.core.store_client_mixin import StoreClientMixin
from static_frame.core.frame import Frame
from static_frame.core.index_base import IndexBase
from static_frame.core.bus import Bus
from static_frame.core.util import NameType
from static_frame.core.store import StoreConfigMapInitializer
from static_frame.core.doc_str import doc_inject
from static_frame.core.display_config import DisplayConfig
from static_frame.core.display import Display
from static_frame.core.series import Series
from static_frame.core.exception import AxisInvalid
from static_frame.core.util import NULL_SLICE
from static_frame.core.util import GetItemKeyType
from static_frame.core.util import GetItemKeyTypeCompound
from static_frame.core.node_selector import InterfaceGetItem
from static_frame.core.index_hierarchy import IndexHierarchy
from static_frame.core.hloc import HLoc
from static_frame.core.util import duplicate_filter
from static_frame.core.util import INT_TYPES
from static_frame.core.store import Store
from static_frame.core.node_iter import IterNodeAxis
from static_frame.core.node_iter import IterNodeType
from static_frame.core.node_iter import IterNodeConstructorAxis

from static_frame.core.exception import ErrorInitQuilt
from static_frame.core.exception import NotImplementedAxis
from static_frame.core.util import get_tuple_constructor

# from static_frame.core.store import StoreConfigMap
# from static_frame.core.store import StoreConfigMapInitializer

class AxisMap:
    '''
    An AxisMap is a Series where index values point to string label in a Bus.
    '''

    @staticmethod
    def get_axis_series(
            tree: tp.Dict[tp.Hashable, IndexBase],
            ) -> Series:

        index = IndexHierarchy.from_tree(tree)
        return Series(
                index.values_at_depth(0), # store the labels as series values
                index=index,
                own_index=True,
                )

    @classmethod
    def from_bus(cls, bus: Bus, axis: int) -> tp.Tuple[Series, IndexBase]:
        '''
        Given a :obj:`Bus` and an axis, derive a :obj:`Series` with an :obj:`IndexHierarchy`; also return and validate the :obj:`Index` of the opposite axis.
        '''
        # NOTE: need to extract just axis labels, not the full Frame; need new Store/Bus loaders just for label data

        tree = {}
        opposite = None
        for label, f in bus.items():
            if axis == 0:
                tree[label] = f.index
                if opposite is None:
                    opposite = f.columns
                else:
                    if not opposite.equals(f.columns):
                        raise ErrorInitQuilt('opposite axis must have equivalent indices')
            elif axis == 1:
                tree[label] = f.columns
                if opposite is None:
                    opposite = f.index
                else:
                    if not opposite.equals(f.index):
                        raise ErrorInitQuilt('opposite axis must have equivalent indices')
            else:
                raise AxisInvalid(f'invalid axis {axis}')

        return cls.get_axis_series(tree), opposite # type: ignore


class Quilt(ContainerBase, StoreClientMixin):
    '''
    A :obj:`Frame`-like view of the contents of a :obj:`Bus`. With the Quilt, :obj:`Frame` contained in a :obj:`Bus` can be conceived as stacking vertically (primary axis 0) or horizontally (primary axis 1). If the labels of the primary axis are unique accross all contained :obj:`Frame, ``retain_labels`` can be set to ``False`` and underlying labels are simply concatenated; otherwise, ``retain_labels`` must be set to ``True`` and an additional depth-level is added to the primary axis labels. A :obj:`Quilt` can only be created if labels of the opposite axis of all contained :obj:`Frame` are aligned.
    '''

    __slots__ = (
            '_bus',
            '_axis',
            '_axis_map',
            '_retain_labels',
            '_axis_opposite',
            '_assign_axis',
            '_columns',
            '_index',
            )

    _bus: Bus
    _axis: int
    _axis_map: tp.Optional[Series]
    _axis_opposite: tp.Optional[IndexBase]
    _columns: IndexBase
    _index: IndexBase
    _assign_axis: bool

    _NDIM: int = 2

    @classmethod
    def from_frame(cls,
            frame: Frame,
            *,
            chunksize: int,
            retain_labels: bool,
            axis: int = 0,
            name: NameType = None,
            label_extractor: tp.Optional[tp.Callable[[IndexBase], tp.Hashable]] = None,
            config: StoreConfigMapInitializer = None,
            ) -> 'Quilt':
        '''
        Given a :obj:`Frame`, create a :obj:`Quilt` by partitioning it along the specified ``axis`` in units of ``chunksize``, where ``axis`` 0 partitions vertically (retaining aligned columns) and 1 partions horizontally (retaining aligned index).

        Args:
            label_extractor: Function that, given the partitioned index component along the specified axis, returns a string label for that chunk.
        '''
        vector = frame._index if axis == 0 else frame._columns
        vector_len = len(vector)

        starts = range(0, vector_len, chunksize)
        if len(starts) == 1:
            ends: tp.Iterable[int] = (vector_len,)
        else:
            ends = range(starts[1], vector_len, chunksize)

        if label_extractor is None:
            label_extractor = lambda x: x.iloc[0] #type: ignore

        axis_map_components: tp.Dict[tp.Hashable, IndexBase] = {}
        opposite = None

        def values() -> tp.Iterator[Frame]:
            nonlocal opposite

            for start, end in zip_longest(starts, ends, fillvalue=vector_len):
                if axis == 0: # along rows
                    f = frame.iloc[start:end]
                    label = label_extractor(f.index) #type: ignore
                    axis_map_components[label] = f.index
                    if opposite is None:
                        opposite = f.columns
                elif axis == 1: # along columns
                    f = frame.iloc[:, start:end]
                    label = label_extractor(f.columns) #type: ignore
                    axis_map_components[label] = f.columns
                    if opposite is None:
                        opposite = f.index
                else:
                    raise AxisInvalid(f'invalid axis {axis}')
                yield f.rename(label)

        name = name if name else frame.name
        bus = Bus.from_frames(values(), config=config, name=name)

        axis_map = AxisMap.get_axis_series(axis_map_components)

        return cls(bus,
                axis=axis,
                axis_map=axis_map,
                axis_opposite=opposite,
                retain_labels=retain_labels,
                )

    @classmethod
    def _from_store(cls,
            store: Store,
            *,
            config: StoreConfigMapInitializer = None,
            **kwargs: tp.Any,
            ) -> 'Quilt':
        '''
        For compatibility with StoreClientMixin.
        '''
        bus = Bus._from_store(store=store,
                config=config,
                max_persist=kwargs.get('max_persist'), # None is default
                )
        return cls(bus,
                axis=kwargs.get('axis', 0),
                retain_labels=kwargs['retain_labels'],
                )

    #---------------------------------------------------------------------------
    def __init__(self,
            bus: Bus,
            *,
            axis: int = 0,
            retain_labels: bool,
            axis_map: tp.Optional[Series] = None,
            axis_opposite: tp.Optional[IndexBase] = None,
            ) -> None:
        self._bus = bus
        self._axis = axis
        self._retain_labels = retain_labels

        if (axis_map is None) ^ (axis_opposite is None):
            raise ErrorInitQuilt('if supplying axis_map, supply axis_opposite')

        # can creation until needed
        self._axis_map = axis_map
        self._axis_opposite = axis_opposite
        # will be set with re-axis
        # self._index = None
        # self._columns = None
        self._assign_axis = True


    #---------------------------------------------------------------------------
    # deferred loading of axis info

    def _update_axis_labels(self) -> None:
        if self._axis_map is None or self._axis_opposite is None:
            self._axis_map, self._axis_opposite = AxisMap.from_bus(self._bus, self._axis)

        if self._axis == 0:
            if not self._retain_labels:
                self._index = self._axis_map.index.level_drop(1) #type: ignore
            else: # get hierarchical
                self._index = self._axis_map.index
            self._columns = self._axis_opposite
        else:
            if not self._retain_labels:
                self._columns = self._axis_map.index.level_drop(1) #type: ignore
            else:
                self._columns = self._axis_map.index
            self._index = self._axis_opposite
        self._assign_axis = False

    #---------------------------------------------------------------------------
    # name interface

    @property #type: ignore
    @doc_inject()
    def name(self) -> NameType:
        '''{}'''
        return self._bus._name

    def rename(self, name: NameType) -> 'Quilt':
        '''
        Return a new Quilt with an updated name attribute.
        '''
        return self.__class__(self._bus.rename(name),
                axis=self._axis,
                retain_labels=self._retain_labels,
                axis_map=self._axis_map,
                axis_opposite=self._axis_opposite,
                )

    #---------------------------------------------------------------------------

    def __repr__(self) -> str:
        '''Provide a display of the :obj:`Quilt` that does not exhaust the generator.
        '''
        if self.name:
            header = f'{self.__class__.__name__}: {self.name}'
        else:
            header = self.__class__.__name__
        return f'<{header} at {hex(id(self))}>'

    def display(self,
            config: tp.Optional[DisplayConfig] = None
            ) -> Display:
        '''Provide a :obj:`Frame`-style display of the :obj:`Quilt`.
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return self.to_frame().display(config) #type: ignore

    #---------------------------------------------------------------------------
    # accessors

    @property #type: ignore
    @doc_inject(selector='values_2d', class_name='Quilt')
    def values(self) -> np.ndarray:
        '''
        {}
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return self.to_frame().values

    @property
    def index(self) -> IndexBase:
        '''The ``IndexBase`` instance assigned for row labels.
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return self._index

    @property
    def columns(self) -> IndexBase:
        '''The ``IndexBase`` instance assigned for column labels.
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return self._columns

    #---------------------------------------------------------------------------

    @property
    def shape(self) -> tp.Tuple[int, int]:
        '''
        Return a tuple describing the shape of the underlying NumPy array.

        Returns:
            :obj:`tp.Tuple[int]`
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return len(self._index), len(self._columns)

    @property
    def ndim(self) -> int:
        '''
        Return the number of dimensions, which for a `Frame` is always 2.

        Returns:
            :obj:`int`
        '''
        return self._NDIM

    @property
    def size(self) -> int:
        '''
        Return the size of the underlying NumPy array.

        Returns:
            :obj:`int`
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return len(self._index) * len(self._columns)

    @property
    def nbytes(self) -> int:
        '''
        Return the total bytes of the underlying NumPy arrays.

        Returns:
            :obj:`int`
        '''
        # return self._blocks.nbytes
        if self._assign_axis:
            self._update_axis_labels()
        return sum(f.nbytes for _, f in self._bus.items())

    #---------------------------------------------------------------------------
    # dictionary-like interface

    def keys(self) -> tp.Iterable[tp.Hashable]:
        '''Iterator of column labels.
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return self._columns

    def __iter__(self) -> tp.Iterable[tp.Hashable]:
        '''
        Iterator of column labels, same as :py:meth:`Frame.keys`.
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return self._columns.__iter__()

    def __contains__(self, value: tp.Hashable) -> bool:
        '''
        Inclusion of value in column labels.
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return self._columns.__contains__(value)

    def items(self) -> tp.Iterator[tp.Tuple[tp.Hashable, Series]]:
        '''Iterator of pairs of column label and corresponding column :obj:`Series`.
        '''
        if self._assign_axis:
            self._update_axis_labels()
        yield from self._axis_series_items(axis=0) # iterate columns

    def get(self,
            key: tp.Hashable,
            default: tp.Optional[Series] = None,
            ) -> tp.Optional[Series]:
        '''
        Return the value found at the columns key, else the default if the key is not found. This method is implemented to complete the dictionary-like interface.
        '''
        if self._assign_axis:
            self._update_axis_labels()
        if key not in self._columns:
            return default
        return self.__getitem__(key) #type: ignore

    #---------------------------------------------------------------------------
    # compatibility with StoreClientMixin

    def _items_store(self) -> tp.Iterator[tp.Tuple[str, Frame]]:
        '''Iterator of pairs of :obj:`Bus` label and contained :obj:`Frame`.
        '''
        yield from self._bus.items()


    #---------------------------------------------------------------------------
    # axis iterators

    def _axis_array(self, axis: int) -> tp.Iterator[np.ndarray]:
        '''Generator of arrays across an axis

        Args:
            axis: 0 iterates over columns, 1 iterates over rows
        '''
        if axis == 1: # iterate over rows
            if self._axis == 0: # bus components aligned vertically
                for _, component in self._bus.items():
                    yield from component._blocks.axis_values(axis)
            else: # bus components aligned horizontally
                raise NotImplementedAxis()
        elif axis == 0: # iterate over columns
            if self._axis == 1: # bus components aligned horizontally
                for _, component in self._bus.items():
                    yield from component._blocks.axis_values(axis)
            else: # bus components aligned horizontally
                raise NotImplementedAxis()
        else:
            raise AxisInvalid(f'no support for axis {axis}')

    def _axis_array_items(self, axis: int) -> tp.Iterator[tp.Tuple[tp.Hashable, np.ndarray]]:
        keys = self._index if axis == 1 else self._columns
        yield from zip(keys, self._axis_array(axis))


    def _axis_tuple(self, *,
            axis: int,
            constructor: tp.Optional[tp.Type[tp.NamedTuple]] = None,
            ) -> tp.Iterator[tp.NamedTuple]:
        '''Generator of named tuples across an axis.

        Args:
            axis: 0 iterates over columns (index axis), 1 iterates over rows (column axis)
        '''
        if constructor is None:
            if axis == 1:
                labels = self._columns.values
            elif axis == 0:
                labels = self._index.values
            else:
                raise AxisInvalid(f'no support for axis {axis}')
            # uses _make method to call with iterable
            constructor = get_tuple_constructor(labels) #type: ignore
        elif (isinstance(constructor, type) and
                issubclass(constructor, tuple) and
                hasattr(constructor, '_make')):
            constructor = constructor._make #type: ignore

        assert constructor is not None

        for axis_values in self._axis_array(axis):
            yield constructor(axis_values)

    def _axis_tuple_items(self, *,
            axis: int,
            constructor: tp.Optional[tp.Type[tp.NamedTuple]] = None,
            ) -> tp.Iterator[tp.Tuple[tp.Hashable, tp.NamedTuple]]:
        keys = self._index if axis == 1 else self._columns
        yield from zip(keys, self._axis_tuple(axis=axis, constructor=constructor))


    def _axis_series(self, axis: int) -> tp.Iterator[Series]:
        '''Generator of Series across an axis
        '''
        index = self._index if axis == 0 else self._columns
        for label, axis_values in self._axis_array_items(axis):
            yield Series(axis_values, index=index, name=label, own_index=True)

    def _axis_series_items(self, axis: int) -> tp.Iterator[tp.Tuple[tp.Hashable, np.ndarray]]:
        keys = self._index if axis == 1 else self._columns
        yield from zip(keys, self._axis_series(axis=axis))


    #---------------------------------------------------------------------------
    def _extract_array(self,
            row_key: GetItemKeyType = None,
            column_key: GetItemKeyType = None,
            ) -> np.ndarray:
        '''
        Extract a consolidated array based on iloc selection.
        '''
        row_key = NULL_SLICE if row_key is None else row_key
        column_key = NULL_SLICE if column_key is None else column_key

        if row_key == NULL_SLICE and column_key == NULL_SLICE:
            arrays = [f.values for _, f in self._bus.items()]
            return np.concatenate( #type: ignore
                    arrays,
                    axis=self._axis,
                    )

        parts: tp.List[np.ndarray] = []

        sel = np.full(len(self._axis_map), False) #type: ignore
        if self._axis == 0:
            sel_key = row_key
            opposite_key = column_key
        else:
            sel_key = column_key
            opposite_key = row_key

        sel_reduces = isinstance(sel_key, INT_TYPES)
        opposite_reduces = isinstance(opposite_key, INT_TYPES)

        sel[sel_key] = True
        sel.flags.writeable = False
        sel_map = Series(sel, index=self._axis_map.index, own_index=True) #type: ignore

        # get ordered unique Bus labels from AxisMap Series values; cannot use .unique as need order
        axis_map_sub = self._axis_map.iloc[sel_key] #type: ignore
        if not isinstance(axis_map_sub, Series): # we have an element integer
            bus_keys = (axis_map_sub,)
        else:
            bus_keys = duplicate_filter(axis_map_sub.values) #type: ignore

        for key_count, key in enumerate(bus_keys):
            sel_component = sel_map[HLoc[key]].values # get Boolean array

            if self._axis == 0:
                component = self._bus.loc[key]._extract_array(sel_component, opposite_key)
                if sel_reduces:
                    component = component[0]
            else:
                component = self._bus.loc[key]._extract_array(opposite_key, sel_component)
                if sel_reduces:
                    if component.ndim == 1:
                        component = component[0]
                    elif component.ndim == 2:
                        component = component[NULL_SLICE, 0]
            parts.append(component)
        # import ipdb; ipdb.set_trace()
        if len(parts) == 1:
            return parts.pop() #type: ignore
        if sel_reduces or opposite_reduces:
            return np.concatenate(parts) #type: ignore
        return np.concatenate(parts, axis=self._axis) #type: ignore

    def _extract(self,
            row_key: GetItemKeyType = None,
            column_key: GetItemKeyType = None,
            ) -> tp.Union[Frame, Series]:
        '''
        Extract Container based on iloc selection.
        '''
        row_key = NULL_SLICE if row_key is None else row_key
        column_key = NULL_SLICE if column_key is None else column_key

        if row_key == NULL_SLICE and column_key == NULL_SLICE:
            if self._retain_labels and self._axis == 0:
                frames = (f.relabel_level_add(index=k) for k, f in self._bus.items())
            elif self._retain_labels and self._axis == 1:
                frames = (f.relabel_level_add(columns=k) for k, f in self._bus.items())
            else:
                frames = (f for _, f in self._bus.items())
            return Frame.from_concat( #type: ignore
                    frames,
                    axis=self._axis,
                    )

        parts: tp.List[tp.Any] = []

        sel = np.full(len(self._axis_map), False) #type: ignore
        if self._axis == 0:
            sel_key = row_key
            opposite_key = column_key
        else:
            sel_key = column_key
            opposite_key = row_key

        sel_reduces = isinstance(sel_key, INT_TYPES)

        sel[sel_key] = True
        sel.flags.writeable = False
        sel_map = Series(sel, index=self._axis_map.index, own_index=True) #type: ignore

        # get ordered unique Bus labels from AxisMap Series values; cannot use .unique as need order
        axis_map_sub = self._axis_map.iloc[sel_key] #type: ignore
        if not isinstance(axis_map_sub, Series): # we have an element integer
            bus_keys = (axis_map_sub,)
        else:
            bus_keys = duplicate_filter(axis_map_sub.values) #type: ignore

        for key_count, key in enumerate(bus_keys):
            sel_component = sel_map[HLoc[key]].values # get Boolean array

            if self._axis == 0:
                component = self._bus.loc[key].iloc[sel_component, opposite_key]
                if key_count == 0:
                    component_is_series = isinstance(component, Series)
                if self._retain_labels:
                    # component might be a Series, can call the same with first arg
                    component = component.relabel_level_add(key)
                if sel_reduces: # make Frame into a Series, Series into an element
                    component = component.iloc[0]
            else:
                component = self._bus.loc[key].iloc[opposite_key, sel_component]
                if key_count == 0:
                    component_is_series = isinstance(component, Series)
                if self._retain_labels:
                    if component_is_series:
                        component = component.relabel_level_add(key)
                    else:
                        component = component.relabel_level_add(columns=key)
                if sel_reduces: # make Frame into a Series, Series into an element
                    if component_is_series:
                        component = component.iloc[0]
                    else:
                        component = component.iloc[NULL_SLICE, 0]
            parts.append(component)

        if len(parts) == 1:
            return parts.pop() #type: ignore
        if component_is_series:
            return Series.from_concat(parts)
        return Frame.from_concat(parts, axis=self._axis) #type: ignore

    #---------------------------------------------------------------------------

    def _extract_iloc(self, key: GetItemKeyTypeCompound) -> tp.Union[Series, Frame]:
        '''
        Give a compound key, return a new Frame. This method simply handles the variabiliyt of single or compound selectors.
        '''
        if self._assign_axis:
            self._update_axis_labels()
        if isinstance(key, tuple):
            return self._extract(*key)
        return self._extract(row_key=key)

    def _compound_loc_to_iloc(self,
            key: GetItemKeyTypeCompound) -> tp.Tuple[GetItemKeyType, GetItemKeyType]:
        '''
        Given a compound iloc key, return a tuple of row, column keys. Assumes the first argument is always a row extractor.
        '''
        if isinstance(key, tuple):
            loc_row_key, loc_column_key = key
            iloc_column_key = self._columns.loc_to_iloc(loc_column_key)
        else:
            loc_row_key = key
            iloc_column_key = None

        iloc_row_key = self._index.loc_to_iloc(loc_row_key)
        return iloc_row_key, iloc_column_key

    def _extract_loc(self, key: GetItemKeyTypeCompound) -> tp.Union[Series, Frame]:
        if self._assign_axis:
            self._update_axis_labels()
        return self._extract(*self._compound_loc_to_iloc(key))

    def _compound_loc_to_getitem_iloc(self,
            key: GetItemKeyTypeCompound) -> tp.Tuple[GetItemKeyType, GetItemKeyType]:
        '''Handle a potentially compound key in the style of __getitem__. This will raise an appropriate exception if a two argument loc-style call is attempted.
        '''
        iloc_column_key = self._columns.loc_to_iloc(key)
        return None, iloc_column_key

    @doc_inject(selector='selector')
    def __getitem__(self, key: GetItemKeyType) -> tp.Union[Frame, Series]:
        '''Selector of columns by label.

        Args:
            key: {key_loc}
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return self._extract(*self._compound_loc_to_getitem_iloc(key))

    #---------------------------------------------------------------------------
    # interfaces

    @property
    def loc(self) -> InterfaceGetItem['Frame']:
        return InterfaceGetItem(self._extract_loc) #type: ignore

    @property
    def iloc(self) -> InterfaceGetItem['Frame']:
        return InterfaceGetItem(self._extract_iloc) #type: ignore

    #---------------------------------------------------------------------------
    # iterators

    @property
    def iter_array(self) -> IterNodeAxis['Quilt']:
        '''
        Iterator of :obj:`np.array`, where arrays are drawn from columns (axis=0) or rows (axis=1)
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return IterNodeAxis(
                container=self,
                function_values=self._axis_array,
                function_items=self._axis_array_items,
                yield_type=IterNodeType.VALUES
                )

    @property
    def iter_array_items(self) -> IterNodeAxis['Quilt']:
        '''
        Iterator of pairs of label, :obj:`np.array`, where arrays are drawn from columns (axis=0) or rows (axis=1)
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return IterNodeAxis(
                container=self,
                function_values=self._axis_array,
                function_items=self._axis_array_items,
                yield_type=IterNodeType.ITEMS
                )

    @property
    def iter_tuple(self) -> IterNodeConstructorAxis['Quilt']:
        '''
        Iterator of :obj:`NamedTuple`, where tuples are drawn from columns (axis=0) or rows (axis=1). An optional ``constructor`` callable can be used to provide a :obj:`NamedTuple` class (or any other constructor called with a single iterable) to be used to create each yielded axis value.
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return IterNodeConstructorAxis(
                container=self,
                function_values=self._axis_tuple,
                function_items=self._axis_tuple_items,
                yield_type=IterNodeType.VALUES
                )

    @property
    def iter_tuple_items(self) -> IterNodeConstructorAxis['Quilt']:
        '''
        Iterator of pairs of label, :obj:`NamedTuple`, where tuples are drawn from columns (axis=0) or rows (axis=1)
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return IterNodeConstructorAxis(
                container=self,
                function_values=self._axis_tuple,
                function_items=self._axis_tuple_items,
                yield_type=IterNodeType.ITEMS
                )

    @property
    def iter_series(self) -> IterNodeAxis['Quilt']:
        '''
        Iterator of :obj:`Series`, where :obj:`Series` are drawn from columns (axis=0) or rows (axis=1)
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return IterNodeAxis(
                container=self,
                function_values=self._axis_series,
                function_items=self._axis_series_items,
                yield_type=IterNodeType.VALUES
                )

    @property
    def iter_series_items(self) -> IterNodeAxis['Quilt']:
        '''
        Iterator of pairs of label, :obj:`Series`, where :obj:`Series` are drawn from columns (axis=0) or rows (axis=1)
        '''
        if self._assign_axis:
            self._update_axis_labels()
        return IterNodeAxis(
                container=self,
                function_values=self._axis_series,
                function_items=self._axis_series_items,
                yield_type=IterNodeType.ITEMS
                )

    #---------------------------------------------------------------------------
    def to_frame(self) -> Frame:
        '''
        Return a consolidated :obj:`Frame`.
        '''
        return self._extract(NULL_SLICE, NULL_SLICE) #type: ignore
