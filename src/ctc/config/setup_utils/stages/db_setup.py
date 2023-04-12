from __future__ import annotations

import os
import typing

import aiohttp
import toolcli
import toolstr
import toolsql

from ctc import db
from ctc import spec
from ... import config_defaults


def setup_dbs(
    *,
    styles: toolcli.StyleTheme,
    data_dir: str,
    network_data: spec.PartialConfig,
    db_config: toolsql.DBConfig | None = None,
) -> spec.PartialConfig:

    print()
    print()
    toolstr.print('## Database Setup', style=styles['title'])
    print()
    print('ctc stores its collected chain data in an sql database')

    db_configs = config_defaults.get_default_db_configs(data_dir)

    # check database versions
    check_db_versions(list(db_configs.values()))

    # create db
    print()
    for db_config in db_configs.values():
        db_path = db_config.get('path')
        if db_path is not None:
            db_dirpath = os.path.dirname(db_path)
            os.makedirs(db_dirpath, exist_ok=True)

            if not os.path.isfile(db_path):
                toolstr.print(
                    'Creating database at path ['
                    + styles['description']
                    + ']'
                    + db_path
                    + '[/'
                    + styles['description']
                    + ']'
                )
            else:
                toolstr.print(
                    'Existing database detected at path ['
                    + styles['description']
                    + ']'
                    + db_path
                    + '[/'
                    + styles['description']
                    + ']'
                )

    print()
    _delete_incomplete_chainlink_schemas(db_configs['main'])

    # create tables
    used_networks: set[spec.NetworkReference] = set()
    default_network = network_data.get('default_network')
    if default_network is not None:
        used_networks.add(default_network)
    for provider in network_data['providers'].values():
        network = provider.get('network')
        if network is not None:
            used_networks.add(network)
    used_networks = {
        network for network in used_networks if network is not None
    }
    print()

    with toolsql.connect(db_configs['main']) as conn:
        db.create_missing_tables(
            networks=list(used_networks),
            conn=conn,
            confirm=True,
        )

    return {'db_configs': db_configs}


async def async_populate_db_tables(
    db_config: toolsql.DBConfig,
    styles: toolcli.StyleTheme,
) -> None:
    from ctc.protocols.chainlink_utils import chainlink_db
    from ..default_data import default_erc20s

    print()
    print()
    toolstr.print('## Populating Database', style=styles['title'])

    # populate data: erc20s
    print()
    print('Populating database with metadata of common ERC20 tokens...')
    print()
    await default_erc20s.async_intake_default_erc20s(
        context=dict(network='ethereum'),
    )

    # populate data: chainlink
    print()
    print('Populating database with latest Chainlink oracle feeds...')
    print()
    try:
        await chainlink_db.async_import_networks_to_db(db_config=db_config)
    except aiohttp.client_exceptions.ClientConnectorError:
        print('Could not connect to Chainlink server, skipping')
    except Exception:
        print('Could not add feeds to db, skipping')


def _delete_incomplete_chainlink_schemas(db_config: toolsql.DBConfig) -> None:
    """detect any tables missing in chainlink schema

    this is a stopgap until a more comprehensive migration system is in place
    """

    from ctc import db

    # looking for schemas that have already been created, but are missing tables
    networks = list(config_defaults.get_default_networks_metadata().keys())
    with toolsql.connect(db_config) as conn:
        table_names = toolsql.get_table_names(conn)
        if 'schema_versions' not in table_names:
            return
        for network in networks:
            context: spec.Context = {'network': network}
            schema_version = db.get_schema_version(
                schema_name='chainlink',
                context=dict(network=network),
                conn=conn,
            )
            if schema_version is not None:
                schema = db.get_prepared_schema(
                    schema_name='chainlink', context=context
                )
                for table_name in schema['tables'].keys():
                    if table_name not in table_names:
                        print(
                            'missing chainlink_aggregator_updates table, rebuilding schema'
                        )
                        db.drop_schema(
                            schema_name='chainlink',
                            context=context,
                            confirm=True,
                            conn=conn,
                        )


def check_db_versions(db_configs: typing.Sequence[toolsql.DBConfig]) -> None:

    dbms_set = {db_config.get('dbms') for db_config in db_configs}
    for dbms in dbms_set:

        # check sqlite
        if dbms == 'sqlite':
            import sqlite3

            # get sqlite3 version
            if sqlite3.sqlite_version.count('.') == 2:
                major_str, minor_str, _ = sqlite3.sqlite_version.split('.')
            elif sqlite3.sqlite_version.count('.') == 1:
                major_str, minor_str = sqlite3.sqlite_version.split('.')
            else:
                major_str, minor_str = '0', '0'
            major = int(major_str)
            minor = int(minor_str)

            if (major < 3) or (major == 3 and minor < 24):
                raise Exception(
                    'ctc requires sqlite verison >= 3.24. This environment is using sqlite version '
                    + str(sqlite3.sqlite_version)
                    + '. You must upgrade sqlite3 before continuing.'
                    + ' If using apt, this can be accomplished using `apt install sqlite3` or `sudo apt-get install sqlite3`'
                )

        else:
            raise Exception('dbms not supported: ' + str(dbms))

