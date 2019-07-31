def ascii_zero(bytestr):
    return bytestr.rstrip(b"\x00").decode("ascii")
