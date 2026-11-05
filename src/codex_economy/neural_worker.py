"""Isolated optional LLMLingua-2 doc experiment. Never import in the core runtime."""

import json
import resource
import sys
import time


def main():
    payload = json.load(sys.stdin)
    if not isinstance(payload.get("text"), str) or len(payload["text"]) > 16000:
        raise ValueError("Neural experiment supports at most 16000 document characters")
    if not 0.1 <= payload.get("rate", 0.5) <= 1:
        raise ValueError("Compression rate must be .1–1")
    import torch

    torch.set_num_threads(1)
    from llmlingua import PromptCompressor

    # Enforce offline execution at the kernel boundary, not just SDK configuration.
    import ctypes
    import ctypes.util

    library = ctypes.util.find_library("seccomp")
    if not library:
        raise ValueError("libseccomp is required for offline neural execution")
    seccomp = ctypes.CDLL(library, use_errno=True)
    seccomp.seccomp_init.argtypes = [ctypes.c_uint32]
    seccomp.seccomp_init.restype = ctypes.c_void_p
    seccomp.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    seccomp.seccomp_syscall_resolve_name.restype = ctypes.c_int
    seccomp.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    seccomp.seccomp_load.argtypes = [ctypes.c_void_p]
    seccomp.seccomp_release.argtypes = [ctypes.c_void_p]
    context = seccomp.seccomp_init(0x7FFF0000)
    if not context:
        raise ValueError("Cannot initialize offline filter")
    try:
        for name in (b"connect", b"sendto", b"sendmsg"):
            number = seccomp.seccomp_syscall_resolve_name(name)
            if number >= 0 and seccomp.seccomp_rule_add(context, 0x00050001, number, 0) != 0:
                raise ValueError("Cannot configure offline filter")
        if seccomp.seccomp_load(context) != 0:
            raise ValueError("Cannot enforce offline filter")
    finally:
        seccomp.seccomp_release(context)
    start = time.monotonic()
    model = PromptCompressor(
        model_name=payload["model"], device_map="cpu", use_llmlingua2=True, model_config={"local_files_only": True}
    )
    result = model.compress_prompt(payload["text"], rate=payload.get("rate", 0.5), force_tokens=["\n"])
    result.pop("saving", None)
    print(
        json.dumps(
            {
                "model": payload["model"],
                "provider": "LLMLingua-2",
                "result": result,
                "seconds": time.monotonic() - start,
                "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "offline": True,
                "network_enforcement": "seccomp denies connect/sendto/sendmsg",
                "source_code_compression": False,
            }
        )
    )


if __name__ == "__main__":
    main()
