from ctc import spec
from ctc.evm import binary_utils
from .. import rpc_format


def digest_web3_client_version(response: spec.RpcResponse) -> spec.RpcResponse:
    return response


def digest_web3_sha3(response: spec.RpcResponse) -> spec.RpcResponse:
    return response


def digest_net_version(response: spec.RpcResponse) -> spec.RpcResponse:
    return response


def digest_net_peer_count(response: spec.RpcResponse) -> spec.RpcResponse:
    return response


def digest_net_listening(response: spec.RpcResponse) -> spec.RpcResponse:
    return response


def digest_eth_protocol_version(
    response: spec.RpcResponse, decode_response: bool = True
) -> spec.RpcResponse:
    if decode_response:
        response = binary_utils.convert_binary_format(response, 'integer')
    return response


def digest_eth_syncing(
    response: spec.RpcResponse, snake_case_response: bool = True
) -> spec.RpcResponse:
    if snake_case_response:
        if isinstance(response, dict):
            response = rpc_format.keys_to_snake_case(response)
    return response

