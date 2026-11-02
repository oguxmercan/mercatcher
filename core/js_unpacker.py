#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dean Edwards Packer (p,a,c,k,e,d) JavaScript Açıcı (Unpacker)
MixDrop, FileMoon, DoodStream vb. video servislerinin şifrelenmiş JS bloklarını çözer.
"""

import re

def unpack_js(packed_code: str) -> str:
    """
    eval(function(p,a,c,k,e,d)...) biçimindeki JavaScript kodlarını çözer.
    """
    if not packed_code:
        return ""

    # p, a, c, k, e, d kalıbı
    pattern = r"\}\s*\(\s*['\"](.*?)['\"]\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*['\"](.*?)['\"]\.split\(\s*['\"]\|['\"]\s*\)"
    match = re.search(pattern, packed_code, re.DOTALL)
    if not match:
        return packed_code

    payload, radix_str, count_str, sym_str = match.groups()
    radix = int(radix_str)
    count = int(count_str)
    symtab = sym_str.split('|')

    digits = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def base_n(num, b):
        if num == 0:
            return digits[0]
        res = []
        while num > 0:
            res.append(digits[num % b])
            num //= b
        return "".join(reversed(res))

    word_map = {}
    for i in range(count):
        token = base_n(i, radix)
        word = symtab[i] if i < len(symtab) and symtab[i] else token
        word_map[token] = word

    def replace_word(m):
        w = m.group(0)
        return word_map.get(w, w)

    return re.sub(r"\b\w+\b", replace_word, payload)
