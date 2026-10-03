"""
A stand-in for the `genlayer` module, so the deterministic half of the contract
can be exercised on a laptop.

This is not a GenVM emulator and does not pretend to be one. It replaces storage
types with plain Python containers and replaces the two equivalence principles
with direct calls, which means it tests exactly the part of the contract that
consensus is not involved in: commit ordering, reveal binding, attempt
accounting, advancement, the winner rule and finalisation. Those are the parts
where a bug produces a wrong race result rather than a failed transaction, so
they are the parts worth testing off chain.

The non-deterministic half is scripted through `set_page` and `set_verdicts`.
Stage A and Stage B still run their real code paths, they just read fixtures
instead of the web.
"""

import sys
import types
import inspect


# -- types -------------------------------------------------------------------


class Address:
    SIZE = 20
    ZERO = None

    def __init__(self, val):
        if isinstance(val, Address):
            val = val._hex
        self._hex = val.lower()

    @property
    def as_hex(self):
        return self._hex

    def __eq__(self, other):
        return isinstance(other, Address) and self._hex == other._hex

    def __lt__(self, other):
        return self._hex < other._hex

    def __hash__(self):
        return hash(self._hex)

    def __repr__(self):
        return f"Address({self._hex})"


_ZERO_ADDRESS = Address("0x" + "00" * 20)


def _passthrough(x):
    return x


u8 = u32 = u256 = int
bigint = int
DynArray = list
TreeMap = dict
allow_storage = _passthrough


def Keccak256(b=None):  # pragma: no cover - hashlib is present in practice
    raise NotImplementedError


# -- gl ----------------------------------------------------------------------


class _Message:
    sender_address = _ZERO_ADDRESS


class _Public:
    @staticmethod
    def view(f):
        return f

    class _Write:
        def __call__(self, f):
            return f

        def payable(self, f):
            return f

    write = _Write()


class _Web:
    page = ""
    fail = False

    @classmethod
    def render(cls, url, mode="text"):
        if cls.fail:
            raise RuntimeError("fetch failed")
        return cls.page


class _Nondet:
    web = _Web
    verdicts = []

    @classmethod
    def exec_prompt(cls, prompt, response_format="text"):
        if not cls.verdicts:
            return {"verdict": "undetermined", "reasoning": "no fixture"}
        return cls.verdicts.pop(0)


class _EqPrinciple:
    @staticmethod
    def strict_eq(fn):
        return fn()

    @staticmethod
    def prompt_comparative(fn, principle):
        return fn()


class Event:
    log = []

    def __init_subclass__(cls, **kw):
        # Contract events declare __init__ with an empty body, the way the real
        # SDK expects. Reinstate the capturing __init__ so the harness can log.
        super().__init_subclass__(**kw)
        params = list(inspect.signature(cls.__init__).parameters.values())
        if not params or params[0].name != "self":
            raise TypeError("first argument must be self")
        indexed = []
        for param in params[1:]:
            if param.kind == inspect.Parameter.POSITIONAL_ONLY:
                indexed.append(param.name)
            elif param.kind != inspect.Parameter.VAR_KEYWORD:
                raise TypeError("SDK events require positional-only indexed fields and **data")
        # v0.2.16 binds positional values to alphabetically sorted field names.
        cls.indexed = tuple(sorted(indexed))
        cls.__init__ = Event.__init__

    def __init__(self, *args, **kwargs):
        if len(args) != len(self.indexed):
            raise TypeError("indexed fields mismatch")
        if any(name in kwargs for name in self.indexed):
            raise TypeError("indexed field must not be present in blob")
        self._args = args
        self._kwargs = kwargs
        self._blob = dict(kwargs, **dict(zip(self.indexed, args)))

    def emit(self):
        Event.log.append((type(self).__name__, self._args, self._kwargs))


class Contract:
    pass


class gl:
    Contract = Contract
    Event = Event
    public = _Public
    message_raw = {"datetime": "2026-10-03T00:00:00+00:00"}
    message = _Message
    nondet = _Nondet
    eq_principle = _EqPrinciple


# -- install -----------------------------------------------------------------

_mod = types.ModuleType("genlayer")
for _name in (
    "Address", "u8", "u32", "u256", "bigint", "DynArray", "TreeMap",
    "allow_storage", "Keccak256", "gl",
):
    setattr(_mod, _name, globals()[_name])
_mod.__all__ = [
    "Address", "u8", "u32", "u256", "bigint", "DynArray", "TreeMap",
    "allow_storage", "Keccak256", "gl",
]
sys.modules["genlayer"] = _mod


# -- harness helpers ---------------------------------------------------------


def set_sender(hex_addr):
    _Message.sender_address = Address(hex_addr)


def set_page(text, fail=False):
    _Web.page = text
    _Web.fail = fail


def set_verdicts(*verdicts):
    """Queue LLM replies, e.g. set_verdicts({"verdict": "correct", ...})."""
    _Nondet.verdicts = list(verdicts)


def verdict(kind, reasoning="fixture"):
    return {"verdict": kind, "reasoning": reasoning}


def events(name=None):
    if name is None:
        return list(Event.log)
    return [e for e in Event.log if e[0] == name]


def clear_events():
    Event.log = []


def instantiate(cls, *args, **kwargs):
    """
    Build a contract instance with its declared storage containers initialised,
    the way GenVM does it before __init__ runs.
    """
    obj = object.__new__(cls)
    for name, ann in getattr(cls, "__annotations__", {}).items():
        origin = getattr(ann, "__origin__", ann)
        if origin is list:
            setattr(obj, name, [])
        elif origin is dict:
            setattr(obj, name, {})
    cls.__init__(obj, *args, **kwargs)
    return obj


def set_time(timestamp):
    from datetime import datetime, timezone
    gl.message_raw["datetime"] = datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
