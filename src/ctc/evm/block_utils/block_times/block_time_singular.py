from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    import tooltime

from ctc import rpc
from ctc import spec
from .. import block_crud
from . import block_time_search


async def async_get_block_of_timestamp(
    timestamp: tooltime.Timestamp,
    nary: typing.Optional[int] = None,
    cache: typing.Optional[block_time_search.BlockTimestampSearchCache] = None,
    block_timestamps: typing.Optional[typing.Mapping[int, int]] = None,
    block_timestamp_array: typing.Optional[spec.NumpyArray] = None,
    block_number_array: typing.Optional[spec.NumpyArray] = None,
    verbose: bool = False,
    provider: spec.ProviderSpec = None,
    use_db: bool = True,
    mode: typing.Literal['before', 'after', 'equal'] = 'after',
) -> int:

    if not isinstance(timestamp, int):
        import tooltime

        timestamp = tooltime.timestamp_to_seconds(timestamp)

    if block_timestamps is not None or (
        block_timestamp_array is not None and block_number_array is not None
    ):
        return get_block_of_timestamp_from_arrays(
            timestamp=timestamp,
            block_timestamp_array=block_timestamp_array,
            block_number_array=block_number_array,
            block_timestamps=block_timestamps,
            verbose=verbose,
        )
    else:

        # db
        if use_db:
            from ctc import db
            network = rpc.get_provider_network(provider=provider)
            block = await db.async_query_timestamp_block(
                network=network,
                timestamp=timestamp,
                mode=mode,
            )
            if block is not None:
                return block

        # rpc node
        return await block_time_search.async_get_block_of_timestamp_from_node(
            timestamp=timestamp,
            nary=nary,
            cache=cache,
            verbose=verbose,
            provider=provider,
            mode=mode,
        )


def get_block_of_timestamp_from_arrays(
    timestamp: tooltime.Timestamp,
    block_timestamp_array: spec.NumpyArray | None = None,
    block_number_array: spec.NumpyArray | None = None,
    block_timestamps: typing.Mapping[int, int] | None = None,
    verbose: bool = False,
) -> int:
    import numpy as np

    if block_timestamp_array is None:
        if block_timestamps is None:
            raise Exception('must specify more arguments')
        block_timestamp_array = np.array(list(block_timestamps.values()))
    if block_number_array is None:
        if block_timestamps is None:
            raise Exception('must specify more arguments')
        block_number_array = np.array(list(block_timestamps.keys()))

    if not isinstance(timestamp, int):
        import tooltime

        timestamp = tooltime.timestamp_to_seconds(timestamp)

    index = np.searchsorted(block_timestamp_array, timestamp)
    return block_number_array[index]


async def async_get_block_number_and_time(
    block_number: typing.Optional[spec.BlockNumberReference] = None,
    block_timestamp: typing.Optional[tooltime.Timestamp] = None,
    provider: spec.ProviderSpec = None,
) -> tuple[int, int]:

    if block_timestamp is not None and block_number is not None:
        raise Exception('must specify start_time or block_number')

    if block_number is not None:
        block = await block_crud.async_get_block(
            block_number, provider=provider
        )
        return block['number'], block['timestamp']

    elif block_timestamp is not None:
        block_number = await async_get_block_of_timestamp(
            block_timestamp, provider=provider
        )
        block = await block_crud.async_get_block(
            block_number, provider=provider
        )
        return block['number'], block['timestamp']

    else:
        raise Exception('must specify start_time or block_number')

