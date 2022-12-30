from __future__ import annotations

import typing

from ctc import evm
from ctc import spec
from ... import connect_utils
from ... import management
from . import events_statements


async def async_intake_encoded_events(
    *,
    encoded_events: typing.Sequence[spec.EncodedEvent] | spec.DataFrame,
    # encoded_events: spec.DataFrame,
    query: spec.DBEventQuery,
    context: spec.Context,
    latest_block: int | None = None,
) -> None:

    import sqlalchemy.exc  # type: ignore
    import numpy as np

    if spec.is_dataframe(encoded_events):
        blocks = encoded_events.index.get_level_values('block_number')
        encoded_events = encoded_events.reset_index().to_dict(orient='records')  # type: ignore
    else:
        blocks = np.array([event['block_number'] for event in encoded_events])  # type: ignore

    # only insert blocks after a given number of confirmations
    if latest_block is None:
        latest_block = await evm.async_get_latest_block_number()
    required_confirmations = management.get_required_confirmations(
        context=context
    )
    latest_allowed_block = latest_block - required_confirmations
    if query['start_block'] > latest_allowed_block:
        return
    if query['end_block'] > latest_allowed_block:
        if len(blocks) > 0:
            confirmed_mask = blocks <= latest_allowed_block
            encoded_events = [
                event  # type: ignore
                for event, confirmed in zip(encoded_events, confirmed_mask)
                if confirmed
            ]
        query['end_block'] = latest_allowed_block

    if len(encoded_events) == 0:
        return

    engine = connect_utils.create_engine(schema_name='events', context=context)
    if engine is None:
        return None

    try:
        with engine.begin() as conn:

            await events_statements.async_upsert_event_query(
                event_query=query,
                conn=conn,
                context=context,
            )
            await events_statements.async_upsert_events(
                encoded_events=encoded_events,
                conn=conn,
                context=context,
            )
    except sqlalchemy.exc.OperationalError:
        pass

    return None

