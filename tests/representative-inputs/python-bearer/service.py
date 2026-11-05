def bearer(header):
    return header.split(" ")[-1] if header else None
