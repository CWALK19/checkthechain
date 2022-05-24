from __future__ import annotations

import typing
import re


async def async_decompile_function_abis(
    bytecode: str,
    sort: str | None = None,
) -> typing.Sequence[typing.Mapping[str, typing.Any]]:
    from ctc.protocols import fourbyte_utils

    function_selectors = re.findall('8063([a-f0-9]{8})146', bytecode)

    coroutines = [
        fourbyte_utils.async_query_function_signature('0x' + selector)
        for selector in function_selectors
    ]

    import asyncio

    abi_lists = await asyncio.gather(*coroutines)
    abis: list[fourbyte_utils.Entry] = [
        abi for abi_list in abi_lists for abi in abi_list
    ]

    if sort is not None:
        abis = sorted(abis, key=lambda item: item[sort])  # type: ignore

    return abis
