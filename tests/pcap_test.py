#!/usr/bin/env python3

import io
from datetime import datetime

import kamene.all
from kamene.layers.l2 import Ether


def col256(text, fg=None, bg=None, bold=False):
    def _get_color(col):
        return "8;5;{0:d}".format(_to_color(col))

    def _to_color(num):
        if isinstance(num, int):
            return num  # Assume it is already a color

        if isinstance(num, str) and len(num) <= 3:
            return 16 + int(num, 6)

        raise ValueError("Invalid color: {0!r}".format(num))

    if not isinstance(text, str):
        text = repr(text)

    buf = io.StringIO()

    if bold:
        buf.write("\x1b[1m")

    if fg is not None:
        buf.write("\x1b[3{0}m".format(_get_color(fg)))

    if bg is not None:
        buf.write("\x1b[4{0}m".format(_get_color(bg)))

    buf.write(text)
    buf.write("\x1b[0m")
    return buf.getvalue()


def pprint_options(options):
    if len(options):
        yield "--"
        for key, values in options.iter_all_items():
            for value in values:
                yield col256(key + ":", bold=True, fg="453")
                yield col256(str(value), fg="340")


def make_printable(data):  # todo: preserve unicode
    stream = io.StringIO()
    for ch in data:
        if ch == "\\":
            stream.write("\\\\")
        elif ch in "\n\r" or (32 <= ord(ch) <= 126):
            stream.write(ch)
        else:
            stream.write("\\x{0:02x}".format(ord(ch)))
    return stream.getvalue()


def pprint_enhanced_packet(block):
    text = [
        col256(" Packet+ ", bg="001", fg="345"),
        # col256('NIC:', bold=True),
        # col256(str(block.interface_id), fg='145'),
        col256(str(block.interface.options["if_name"]), fg="140"),
        col256(
            str(
                datetime.utcfromtimestamp(block.timestamp).strftime("%Y-%m-%d %H:%M:%S")
            ),
            fg="455",
        ),
    ]
    try:
        text.extend(
            [
                col256("NIC:", bold=True),
                col256(block.interface_id, fg="145"),
                col256(block.interface.options["if_name"], fg="140"),
            ]
        )
    except KeyError:
        pass

    text.extend(
        [
            # col256('Size:', bold=True),
            col256(str(block.packet_len) + " bytes", fg="025")
        ]
    )

    if block.captured_len != block.packet_len:
        text.extend(
            [
                col256("Truncated to:", bold=True),
                col256(str(block.captured_len) + "bytes", fg="145"),
            ]
        )

    text.extend(pprint_options(block.options))
    print(" ".join(text))

    if block.interface.link_type == 1:

        _info = format_kamene_packet(Ether(block.packet_data))
        print("\n".join("    " + line for line in _info))

    else:
        print("        Printing information for non-ethernet packets")
        print("        is not supported yet.")


def format_kamene_packet(packet):
    fields = []
    for f in packet.fields_desc:
        # if isinstance(f, ConditionalField) and not f._evalcond(self):
        #     continue
        if f.name in packet.fields:
            if isinstance(packet.fields[f.name], (bytes, bytearray)):
                val = packet.fields[f.name].hex()
            else:
                val = f.i2repr(packet, packet.fields[f.name])

        elif f.name in packet.overloaded_fields:
            val = f.i2repr(packet, packet.overloaded_fields[f.name])

        else:
            continue

        fields.append("{0}={1}".format(col256(f.name, "542"), col256(val, "352")))

    yield "{0} {1}".format(col256(packet.__class__.__name__, "501"), " ".join(fields))

    if packet.payload:
        if isinstance(packet.payload, kamene.packet.Packet):
            for line in format_kamene_packet(packet.payload):
                yield "    " + line
        elif isinstance(packet.payload, kamene.packet.Raw):
            for line in format_kamene_packet(packet.payload):
                yield "    " + line
        else:
            for line in repr(packet.payload).splitlines():
                yield "    " + bytes(line).hex()


if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 2:
        print("use as %s <path-to-pcap-file>" % sys.argv[0])
        exit(0)

    sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

    from pcapng.scanner import FileScanner
    from pcapng.blocks import EnhancedPacket
    import kamene.packet

    with open(sys.argv[1], "rb") as testfile:
        scanner = FileScanner(testfile)
        print("print first 100 packets")
        limit = 100
        counter = 0
        for block in scanner:
            if isinstance(block, EnhancedPacket):
                counter += 1
                pprint_enhanced_packet(block)
                if counter >= limit:
                    print("100 packets printed")
                    break