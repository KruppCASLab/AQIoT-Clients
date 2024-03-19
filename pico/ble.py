# Helpers for generating BLE advertising payloads.
from Crypto.PublicKey import ECC
import struct

# Advertising payloads are repeated packets of the following form:
#   1 byte data length (N + 1)
#   1 byte type (see constants below)
#   N bytes type-specific data

_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x3)
_ADV_TYPE_UUID32_COMPLETE = const(0x5)
_ADV_TYPE_UUID128_COMPLETE = const(0x7)
_ADV_TYPE_UUID16_MORE = const(0x2)
_ADV_TYPE_UUID32_MORE = const(0x4)
_ADV_TYPE_UUID128_MORE = const(0x6)
_ADV_TYPE_APPEARANCE = const(0x19)

# Aplpe AirTag UUID
# Define constants for the payload
ADV_TYPE_MANUFACTURER_SPECIFIC_DATA = const(0xFF)
APPLE_COMPANY_IDENTIFIER = const(0x004C)
APPLE_PAYLOAD_TYPE_FINDMY_BROADCAST = const(0x12)
APPLE_PAYLOAD_LENGTH = const(0x19)
STATUS_BYTE = const(0x10)
CRYPTO_COUNTER_UPPER_BITS = const(0x01)  # Assuming upper 2 bits are 01


# Generate a payload to be passed to gap_advertise(adv_data=...).
# This is where we need to make a change to return raw bytes
def advertising_payload():
    payload = bytearray()
    '''
    Format
    0-5     BLE Address
    6       Payload length in bytes (30 or 0x1E)
    7       Advertisement type (0xFF)
    8-9     Company ID (0x004C)
    10      OF Type (0x12)
    11      OF data length in bytes (25)
    12      Status (e.g battery level)
    13-34   Public key bytes
    35      Public key bits
    36      Hint (0x00 on iOS reports)

    C Example

    /** Advertisement payload */
    static uint8_t adv_data[31] = {
        0x1e, /* Length (30) */
        0xff, /* Manufacturer Specific Data (type 0xff) */
        0x4c, 0x00, /* Company ID (Apple) */
        0x12, 0x19, /* Offline Finding type and length */
        0x00, /* State */
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, /* First two bits */
        0x00, /* Hint (0x00) */
    };
    '''

    # BLE Address
    payload.extend(bytearray(struct.pack(">BBBBBB", 0x11, 0x00, 0x00, 0x00, 0x00, 0x00)))

    # Add length
    payload.append(0x1E)

    # Add advertising data type (Manufacturer Specific Data)
    payload.append(ADV_TYPE_MANUFACTURER_SPECIFIC_DATA)

    # Add Apple's company identifier (little-endian format)
    # TODO: Question? Should it be little-endian?
    payload.extend(struct.pack("<H", APPLE_COMPANY_IDENTIFIER))

    # Add Apple payload type
    payload.append(APPLE_PAYLOAD_TYPE_FINDMY_BROADCAST)

    # Add Apple payload length
    payload.append(APPLE_PAYLOAD_LENGTH)

    # Add status byte
    payload.append(STATUS_BYTE)

    # Add EC P-224 public key (dummy data for illustration)
    # Note: eventually, this should be replaced with the valid public key data
    ec_public_key = bytes([0x01] * 22)  # 22 bytes of dummy data
    payload.extend(ec_public_key)

    # Add upper 2 bits of the first byte of ECC public key
    payload.append(CRYPTO_COUNTER_UPPER_BITS)

    # Add crypto counter value (dummy data)
    # Note: eventually, this should be replaced with the actual counter value.
    crypto_counter = bytes([0x00] * 1)  # 1 byte of dummy data
    payload.extend(crypto_counter)

    # hex_string = ' '.join('{:02x}'.format(byte) for byte in payload)
    # # print(hex_string)
    # # print(len(payload))
    return payload

def demo():
    key = ECC.generate(curve='P-224')
    payload = advertising_payload()



if __name__ == "__main__":
    demo()