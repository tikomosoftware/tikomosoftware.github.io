#!/usr/bin/env python3
"""
Prism v0 -- the static checker (the "missing organ").

Focus, by design: rigorously track the two voices the runtime could NOT enforce:
  !  effect row    -- every effect a function performs must be declared
  ?  failure row   -- every failure that can escape must be declared
...with ROW POLYMORPHISM so one `map` stays honest across pure / effectful / fallible f.
Nominal type checking is deliberately light (Unknown unifies with anything); Prism's
distinctive payload is effect+failure tracking, so that is where the rigor goes.

Run:  python check.py examples/divide.prism
"""
import sys
from prism import (lex, Parser, parse_program_with_includes,
                   FuncDef, ValDef, TypeDef, Capability, Provides, Member,
                   Block, Seq, Num, Text, Bool, Var,
                   ListLit, Bin, Call, Field, Lambda, Ctor, OkE, FailE, TryE,
                   EffectCall, Match, Attempt, PWild, PLit, PVar, PTag, POk, PFail,
                   PList, Row, TName, TFunc, Sig)

class Fal:                       # a fallible result: success type + the failures it carries
    def __init__(s, ty, fails): s.ty, s.fails = ty, fails

def fmt_set(xs): return "{" + ", ".join(sorted(xs)) + "}"

BUILTINS = {
    "parseNum": ("fn", [TName("Text")], TName("Num"), Row(), Row(["BadNumber"]), []),
    "sin":  ("fn", [TName("Num")], TName("Num"), Row(), Row(), []),
    "cos":  ("fn", [TName("Num")], TName("Num"), Row(), Row(), []),
    "sqrt": ("fn", [TName("Num")], TName("Num"), Row(), Row(), []),
    "abs":  ("fn", [TName("Num")], TName("Num"), Row(), Row(), []),
    "floor": ("fn", [TName("Num")], TName("Num"), Row(), Row(), []),
    "slider": ("fn", [TName("Num"), TName("Num"), TName("Num")], TName("Num"), Row(), Row(), []),
    "at":  ("fn", [TName("List"), TName("Num")], TName("?"), Row(), Row(), []),   # O(1) read; element type is gradual
    "len": ("fn", [TName("List")], TName("Num"), Row(), Row(), []),               # O(1) length
    "words": ("fn", [TName("Text")], TName("List"), Row(), Row(), []),            # split Text on whitespace
}
BUILTIN_VALUES = {"pi": TName("Num")}   # math constants

# Effect granularity: a coarse effect SUBSUMES finer ones, so a signature may declare `!io`
# and the body is free to use any concrete I/O effect. One-way: `!io` covers `!console`, but a
# `!console` signature does NOT cover a body that performs `!io`. (Only `console` exists in v0;
# the rest are reserved so the relation is ready as real effects are added.)
EFFECT_SUBSUMES = {"io": {"console", "read", "show", "file", "net", "random", "time", "io"}}
def effect_allowed(e, allowed):
    if e in allowed: return True
    return any(e in EFFECT_SUBSUMES.get(a, ()) for a in allowed)

class Checker:
    def __init__(s):
        s.globals = {}; s.errors = []
        s.sumtypes = {}        # sum-type name -> set of variant tags  (for exhaustiveness)
        s.variant_owner = {}   # variant tag -> owning sum-type name   (so a Ctor is its `or`-type)
        s.record_fields = {}   # variant tag -> {field name -> declared type}  (for `.field` typing)
        s.record_fieldnames = {}  # variant tag -> [all declared field names]  (for construction completeness)
        s.capabilities = {}    # capability name -> {method name: Member (its signature)}
        s.cap_tvar = {}        # capability name -> its FIRST type variable (back-compat)
        s.cap_tvars = {}       # capability name -> all type vars [T] / [A, B] (>1 = multiple dispatch)
        s.cap_kind = {}        # capability name -> 0 (plain type) or arity (higher-kinded F[_])
        s.cap_of_method = {}   # method name -> owning capability name (for call resolution)
        s.instances = set()    # {(type name, capability name)}  -- the `provides` facts
        s.instance_methods = {}  # (type, cap) -> {method name: Member (its definition)}
        s.active_constraints = set()   # {(tvar, cap)} of the function currently being checked
        s.cur_who = "<flow>"           # name of the definition currently being checked
        s.cur_line = 0                 # source line of the node currently being synthesized

    def err(s, who, msg):
        loc = f"line {s.cur_line}: " if s.cur_line else ""
        s.errors.append(f"{loc}{who}: {msg}")

    # ---- type-var / row substitution helpers ----
    def row_to_set(s, row, subst):
        out = set(row.labels)
        if row.var:
            out |= subst.get(row.var, {row.var})   # unresolved var stays as a symbol
        return out

    def subst_type(s, ty, subst):
        if isinstance(ty, TName):
            rep = subst.get(ty.name)
            if isinstance(rep, (TName, TFunc, Fal)):
                if ty.args and isinstance(rep, TName):    # ctor var applied: F[..] with F:=List
                    return TName(rep.name, [s.subst_type(a, subst) for a in ty.args])
                return rep
            return TName(ty.name, [s.subst_type(a, subst) for a in ty.args])
        if isinstance(ty, TFunc):
            return TFunc([s.subst_type(p, subst) for p in ty.params],
                         s.subst_type(ty.ret, subst), ty.eff, ty.fail)
        return ty

    # ---- the `:` voice: nominal type compatibility (gradual) ----
    def show(s, ty):
        if isinstance(ty, Fal):
            return s.show(ty.ty) + (f" ?{fmt_set(ty.fails)}" if ty.fails else "")
        if isinstance(ty, TFunc):
            return "(" + ", ".join(s.show(p) for p in ty.params) + ") -> " + s.show(ty.ret)
        if isinstance(ty, TName):
            if ty.name == "?": return "_"      # the gradual Unknown type displays as `_` (`?` is failure-only)
            if ty.args: return ty.name + "[" + ", ".join(s.show(a) for a in ty.args) + "]"
            return ty.name
        return str(ty)

    def is_unknown(s, ty): return isinstance(ty, TName) and ty.name == "?"

    def fields_of(s, tyname):
        # declared {field -> type} for a SINGLE-variant record type (e.g. Point/Box/Picture),
        # else None. Multi-variant `or` types are ambiguous for `.field` access -> stay gradual.
        if tyname in s.record_fields: return s.record_fields[tyname]      # tyname is the tag itself
        vs = s.sumtypes.get(tyname)
        if vs and len(vs) == 1: return s.record_fields.get(next(iter(vs)))
        return None

    def compat(s, a, b):
        # `?` (Unknown) is the gradual boundary -- compatible with anything.
        a = a.ty if isinstance(a, Fal) else a
        b = b.ty if isinstance(b, Fal) else b
        if s.is_unknown(a) or s.is_unknown(b): return True
        if isinstance(a, TName) and isinstance(b, TName):
            if a.name != b.name: return False
            if not a.args or not b.args: return True   # List vs List[Num]: tolerate bare
            if len(a.args) != len(b.args): return False
            return all(s.compat(x, y) for x, y in zip(a.args, b.args))
        if isinstance(a, TFunc) and isinstance(b, TFunc):
            return (len(a.params) == len(b.params)
                    and all(s.compat(x, y) for x, y in zip(a.params, b.params))
                    and s.compat(a.ret, b.ret))
        return False

    def join(s, a, b, who, what):
        # unify two types that MUST agree (list elements, match arms); concretize.
        if s.is_unknown(a): return b
        if s.is_unknown(b): return a
        if s.compat(a, b):
            return a if (isinstance(a, TName) and a.args) else b if (isinstance(b, TName) and b.args) else a
        s.err(who, f"{what} have differing types: {s.show(a)} vs {s.show(b)}")
        return a

    def expect_num(s, ty, who):
        if isinstance(ty, TName) and ty.name in ("Num", "?"): return
        s.err(who, f"arithmetic needs Num, got {s.show(ty)}")

    # ---- type-var / row unification (generic instantiation at a call site) ----
    def unify(s, pat, act, subst, tvars, rvars, cvars=(), who=""):
        pat = pat.ty if isinstance(pat, Fal) else pat
        act = act.ty if isinstance(act, Fal) else act
        if isinstance(pat, TName):
            if pat.name in cvars:                  # higher-kinded var: F[..] := List[..]
                if isinstance(act, TName) and act.name != "?":
                    prev = subst.get(pat.name)
                    if isinstance(prev, TName) and prev.name != act.name:
                        s.err(who, f"container variable {pat.name} bound to both "
                                   f"{prev.name} and {act.name}")
                    else:
                        subst[pat.name] = TName(act.name)          # bind F := List (head only)
                    for pa, aa in zip(pat.args, act.args):         # ..then T := Num inside
                        s.unify(pa, aa, subst, tvars, rvars, cvars, who)
                return
            if pat.name in tvars:
                prev = subst.get(pat.name)
                if isinstance(prev, (TName, TFunc, Fal)):
                    if not s.compat(prev, act):
                        s.err(who, f"type variable {pat.name} bound to both "
                                   f"{s.show(prev)} and {s.show(act)}")
                else:
                    subst[pat.name] = act          # first binding (may be ?)
                return
            if pat.name == "?": return
            if isinstance(act, TName):
                if act.name == "?": return
                if act.name != pat.name:
                    s.err(who, f"expected {s.show(pat)}, got {s.show(act)}"); return
                for pa, aa in zip(pat.args, act.args): s.unify(pa, aa, subst, tvars, rvars, cvars, who)
            elif isinstance(act, TFunc):
                s.err(who, f"expected {s.show(pat)}, got a function")
            return
        if isinstance(pat, TFunc):
            if isinstance(act, TName) and act.name == "?": return
            if not isinstance(act, TFunc):
                s.err(who, f"expected a function {s.show(pat)}, got {s.show(act)}"); return
            for pp, ap in zip(pat.params, act.params): s.unify(pp, ap, subst, tvars, rvars, cvars, who)
            s.unify(pat.ret, act.ret, subst, tvars, rvars, cvars, who)
            s.bind_row(pat.eff, s.row_to_set(act.eff, {}), subst, rvars)
            s.bind_row(pat.fail, s.row_to_set(act.fail, {}), subst, rvars)

    def bind_row(s, patrow, actset, subst, rvars):
        if patrow.var and patrow.var in rvars:
            subst[patrow.var] = subst.get(patrow.var, set()) | (actset - patrow.labels)

    # ---- registration ----
    def register(s, defs):
        for d in defs:
            if isinstance(d, TypeDef):
                s.sumtypes[d.name] = set(d.variants)
                for v in d.variants: s.variant_owner[v] = d.name
                for tag, flds in (getattr(d, "fields", {}) or {}).items():
                    s.record_fields[tag] = {fn: ft for (fn, ft) in flds if ft is not None}
                    s.record_fieldnames[tag] = [fn for (fn, ft) in flds]   # all names (even untyped)
            elif isinstance(d, Capability):
                s.capabilities[d.name] = {m.name: m for m in d.methods}
                s.cap_tvar[d.name] = d.tvar; s.cap_tvars[d.name] = d.tvars; s.cap_kind[d.name] = d.kind
                for m in d.methods: s.cap_of_method[m.name] = d.name
            elif isinstance(d, Provides):
                s.instances.add((tuple(d.types), d.cap))   # keyed by the type TUPLE (len 1 = single dispatch)
                s.instance_methods[(tuple(d.types), d.cap)] = {m.name: m for m in d.methods}
        for name, (_, params, ret, eff, fail, gens) in BUILTINS.items():
            tf = TFunc(params, ret, eff, fail)
            tf.generics = gens; tf.constraints = []; s.globals[name] = tf
        for name, ty in BUILTIN_VALUES.items():
            s.globals[name] = ty
        seen_def = {}                                    # includes merge flat -> top-level names must be unique
        for d in defs:
            nm = getattr(d, "name", None)
            if nm is None or not isinstance(d, (FuncDef, ValDef, TypeDef)): continue
            if nm in seen_def:
                s.cur_line = getattr(d, "line", 0)
                s.err(nm, f"`{nm}` is defined more than once -- includes merge into one flat "
                          f"namespace, so top-level names must be unique")
            seen_def[nm] = True
        for d in defs:
            if isinstance(d, FuncDef):
                if d.sig:
                    params = [pt if pt else TName("?") for (_, pt) in (d.sig.params or [])]
                    tf = TFunc(params, d.sig.ret or TName("?"),
                               d.sig.eff or Row(), d.sig.fail or Row())
                    tf.generics = d.sig.generics; tf.constraints = d.sig.constraints
                else:
                    tf = TFunc([TName("?") for _ in d.params], TName("?"), Row(), Row())
                    tf.generics = []; tf.constraints = []
                s.globals[d.name] = tf
            elif isinstance(d, ValDef):
                s.globals[d.name] = (d.sig.ret if (d.sig and d.sig.ret) else TName("?"))

    # ---- `provides` instances must be COMPLETE (dual of `and`) and COHERENT (unique) ----
    def check_instances(s, defs):
        seen = set()
        for d in defs:
            if not isinstance(d, Provides): continue
            s.cur_line = getattr(d, "line", 0)
            tkey = tuple(d.types)
            who = f"{' + '.join(d.types)} provides {d.cap}"
            if (tkey, d.cap) in seen:               # coherence: one instance per type-combination+capability
                s.err(who, f"duplicate instance -- {' + '.join(d.types)} already provides {d.cap} "
                           f"(at most one instance per type-combination+capability)")
            seen.add((tkey, d.cap))
            if d.cap not in s.capabilities:
                s.err(who, f"no such capability `{d.cap}`"); continue
            want_n = len(s.cap_tvars.get(d.cap, [d.cap]))   # instance must name as many types as the cap has vars
            if len(d.types) != want_n:
                s.err(who, f"{d.cap} is over {want_n} type(s) but this instance names {len(d.types)} "
                           f"({', '.join(d.types)}) -- use `T provides {d.cap} for U, ...`")
            have, need = {m.name for m in d.methods}, set(s.capabilities[d.cap])
            for m in sorted(need - have):
                s.err(who, f"missing method `{m}` required by {d.cap}")
            for m in sorted(have - need):
                s.err(who, f"`{m}` is not a method of {d.cap}")

    # ---- an instance method body must honour the capability's declared signature ----
    def check_instance_bodies(s, defs):
        for d in defs:
            if not isinstance(d, Provides) or d.cap not in s.capabilities: continue
            sub = dict(zip(s.cap_tvars[d.cap], [TName(t) for t in d.types]))   # cap vars := the instance types
            for m in d.methods:
                decl = s.capabilities[d.cap].get(m.name)
                if m.body is None or decl is None: continue
                env, declps, myps = dict(s.globals), (decl.sig.params or []), (m.params or [])
                for i, (pn, _) in enumerate(myps):
                    pt = declps[i][1] if (i < len(declps) and declps[i][1]) else TName("?")
                    env[pn] = s.subst_type(pt, sub)
                s.cur_who, s.active_constraints = f"{d.type_name}.{m.name}", set()
                bty, be, bp = s.synth(m.body, env)
                s.cur_line = getattr(m, "line", 0)       # report at the method, not deep in its body
                succ = bty.ty if isinstance(bty, Fal) else bty
                want = s.subst_type(decl.sig.ret, sub) if decl.sig.ret else TName("?")
                if not s.compat(want, succ):
                    s.err(s.cur_who, f"returns {s.show(succ)} but {d.cap} declares "
                                     f"{m.name} : {s.show(want)}")
                deff, dfail = decl.sig.eff or Row(), decl.sig.fail or Row()
                allowed_e = set(deff.labels) | ({deff.var} if deff.var else set())
                for e in be:
                    if not effect_allowed(e, allowed_e):
                        s.err(s.cur_who, f"performs effect !{e} that {d.cap}.{m.name} does not declare")
                allowed_f = set(dfail.labels) | ({dfail.var} if dfail.var else set())
                mfails = set(bp) | (bty.fails if isinstance(bty, Fal) else set())
                for f in mfails - allowed_f:
                    s.err(s.cur_who, f"can fail with ?{f} that {d.cap}.{m.name} does not declare")

    # ---- a `given T: Cap` constraint is a FACT discharged at the call site ----
    def satisfies(s, ty, cap):
        if not isinstance(ty, TName) or ty.name == "?": return True   # gradual: lenient
        if ((ty.name,), cap) in s.instances: return True              # a single-type `provides` instance
        if (ty.name, cap) in s.active_constraints: return True        # propagated from caller
        return False

    # ---- checking definitions ----
    def check(s, defs):
        s.register(defs)
        s.check_instances(defs)
        s.check_instance_bodies(defs)
        for d in defs:
            if isinstance(d, FuncDef):
                s.active_constraints = set(d.sig.constraints) if d.sig else set()
                s.cur_who = d.name
                env = dict(s.globals)
                if d.sig and d.sig.params:
                    for (pn, pt) in d.sig.params: env[pn] = pt if pt else TName("?")
                else:
                    for pn in d.params: env[pn] = TName("?")
                bty, be, bp = s.synth(d.body, env)
                if d.sig:
                    s.cur_line = d.line          # signature mismatches point at the declaration
                    s.verify(d.name, d.sig, bty, be, bp)
            elif isinstance(d, ValDef):
                s.active_constraints = set(d.sig.constraints) if d.sig else set()
                s.cur_who = d.name
                bty, be, bp = s.synth(d.body, dict(s.globals))   # always synth -- catches errors even
                if d.sig:                                        # without a signature (e.g. `picture <- [..]`)
                    s.cur_line = d.line
                    s.verify(d.name, d.sig, bty, be, bp)
        return s.errors

    def verify(s, name, sig, bty, be, bp):
        deff = sig.eff or Row(); dfail = sig.fail or Row()
        if sig.ret is not None:                 # the `:` voice: body must match declared type
            succ = bty.ty if isinstance(bty, Fal) else bty
            if not s.compat(sig.ret, succ):
                s.err(name, f"returns {s.show(succ)} but its signature declares "
                            f": {s.show(sig.ret)}")
        func_fails = set(bp) | (bty.fails if isinstance(bty, Fal) else set())
        allowed_eff = set(deff.labels) | ({deff.var} if deff.var else set())
        for e in be:
            if not effect_allowed(e, allowed_eff):       # `!io` subsumes finer effects (e.g. `!console`)
                s.err(name, f"performs effect !{e} but its signature declares "
                            f"{'!'+fmt_set(allowed_eff) if allowed_eff else 'no effects (pure)'}")
        allowed_fail = set(dfail.labels) | ({dfail.var} if dfail.var else set())
        for f in func_fails:
            if f not in allowed_fail:
                s.err(name, f"can fail with ?{f} but its signature declares "
                            f"{'?'+fmt_set(allowed_fail) if allowed_fail else 'no failures'}")

    # ---- the plain() guard: a fallible value must be handled before use ----
    def plain(s, ty, ctx, node):
        if isinstance(ty, Fal):
            if ty.fails:
                s.err("<flow>", f"unhandled failure ?{fmt_set(ty.fails)} in {ctx} "
                                f"-- discharge it with `try` or `match`")
            return ty.ty
        return ty

    # ---- synthesis: returns (type, effect-set, propagated-failure-set) ----
    def synth(s, n, env):
        if n.line: s.cur_line = n.line          # track source line for error locality
        t = type(n)
        if t is Num:  return TName("Num"), set(), set()
        if t is Bool: return TName("Bool"), set(), set()
        if t is Text: return s.synth_text(n, env)             # interpolation can carry ! and ?
        if t is Var:  return env.get(n.name, TName("?")), set(), set()
        if t is ListLit:
            eff, prop, elem = set(), set(), TName("?")
            for it in n.items:
                ity, ie, ip = s.synth(it, env)
                elem = s.join(elem, s.plain(ity, "list element", it), "<list>",
                              "list elements"); eff |= ie; prop |= ip
            if n.rest is not None:
                rty, re_, rp = s.synth(n.rest, env)
                s.plain(rty, "list spread", n.rest); eff |= re_; prop |= rp
            return TName("List", [elem]), eff, prop
        if t is Bin:
            lt, le, lp = s.synth(n.l, env); rt, re_, rp = s.synth(n.r, env)
            lt = s.plain(lt, "operand", n.l); rt = s.plain(rt, "operand", n.r)
            op = n.op
            if op in ("-", "*", "/"):
                s.expect_num(lt, "<flow>"); s.expect_num(rt, "<flow>"); ty = TName("Num")
            elif op == "+":          # Num+Num->Num, Text+Text->Text; mixing = hidden coercion
                lT, rT = s.compat(lt, TName("Text")), s.compat(rt, TName("Text"))
                if (isinstance(lt, TName) and lt.name == "Text") or \
                   (isinstance(rt, TName) and rt.name == "Text"):
                    if not (lT and rT):
                        s.err("<flow>", f"'+' mixes {s.show(lt)} and {s.show(rt)} "
                                        f"-- no implicit coercion; build text with \"{{..}}\"")
                    ty = TName("Text")
                else:
                    s.expect_num(lt, "<flow>"); s.expect_num(rt, "<flow>"); ty = TName("Num")
            elif op in ("<", ">", "<=", ">="):
                s.expect_num(lt, "<flow>"); s.expect_num(rt, "<flow>"); ty = TName("Bool")
            else:                    # == / !=
                if not s.compat(lt, rt):
                    s.err("<flow>", f"'{op}' compares incompatible types "
                                    f"{s.show(lt)} and {s.show(rt)}")
                ty = TName("Bool")
            return ty, le | re_, lp | rp
        if t is OkE:
            ity, ie, ip = s.synth(n.e, env)
            return Fal(s.plain(ity, "ok", n.e), set()), ie, ip
        if t is FailE:
            tag = s.error_tag(n.e)
            _, ee, ep = s.synth(n.e, env)
            return Fal(TName("?"), {tag} if tag else set()), ee, ep
        if t is TryE:
            ity, ie, ip = s.synth(n.e, env)
            if isinstance(ity, Fal):
                return ity.ty, ie, ip | ity.fails       # try PROPAGATES the failures
            return ity, ie, ip
        if t is EffectCall:
            eff = {n.world}; prop = set()
            if n.arg is not None:
                _, ae, ap = s.synth(n.arg, env); eff |= ae; prop |= ap   # a failure in the arg propagates
            return (TName("Text") if n.op == "read" else TName("Unit")), eff, prop
        if t is Lambda:
            local = dict(env)
            for p in n.params: local[p] = TName("?")
            bty, be, bp = s.synth(n.body, local)
            bret = bty.ty if isinstance(bty, Fal) else bty
            bfails = (bty.fails if isinstance(bty, Fal) else set()) | bp
            tf = TFunc([TName("?") for _ in n.params], bret, Row(be), Row(bfails))
            tf.generics = []
            return tf, set(), set()
        if t is Ctor:
            if n.tag == "Unit": return TName("Unit"), set(), set()
            decl = s.record_fieldnames.get(n.tag)        # a DECLARED record? then require its fields
            if decl is not None:
                missing = [fn for fn in decl if fn not in n.fields]
                if missing:
                    s.err(n.tag, f"missing field{'s' if len(missing) > 1 else ''} "
                                 f"{', '.join(missing)} (declared {n.tag}{{{', '.join(decl)}}})")
            return TName(s.variant_owner.get(n.tag, n.tag)), set(), set()   # Circle -> Shape (extra fields OK: records stay open)
        if t is Field:
            ot, e, p = s.synth(n.obj, env)
            ft = TName("?")                       # default gradual: unknown obj, or undeclared field
            if isinstance(ot, TName):
                flds = s.fields_of(ot.name)
                if flds and n.name in flds: ft = flds[n.name]   # declared field -> its type
            return ft, e, p                        # records stay OPEN: undeclared `.field` is gradual
        if t is Call:    return s.synth_call(n, env)
        if t is Match:   return s.synth_match(n, env)
        if t is Attempt: return s.synth_attempt(n, env)
        if t is Block:   return s.synth_block(n, env)
        if t is Seq:     return s.synth_seq(n, env)
        return TName("?"), set(), set()

    def synth_text(s, n, env):
        # a `"...{expr}..."` string is Text, but its interpolated exprs are real code:
        # their effects propagate and their failures must be handled -- no hiding in a string.
        eff, prop, raw, i, m = set(), set(), n.v, 0, len(n.v)
        while i < m:
            if raw[i] != "{": i += 1; continue
            depth, j = 1, i + 1                           # brace-depth aware (records can nest)
            while j < m and depth > 0:
                if raw[j] == "{": depth += 1
                elif raw[j] == "}":
                    depth -= 1
                    if depth == 0: break
                j += 1
            if depth != 0: break
            try:
                sub = Parser(lex(raw[i+1:j])).parse_expr()
            except (SyntaxError, RuntimeError):
                i = j + 1; continue
            ety, ee, ep = s.synth(sub, env)
            s.cur_line = n.line or s.cur_line              # report at the string, not the re-parsed fragment
            s.plain(ety, "interpolated value", sub)        # a fallible value in a string must be handled
            eff |= ee; prop |= ep
            i = j + 1
        return TName("Text"), eff, prop

    def synth_seq(s, n, env):
        # the TIME voice. Each non-final step is sequenced FOR its effect/failure and
        # its value discarded -- so it must actually TOUCH TIME (have a `!` or a `?`);
        # a pure step has no order and belongs in a `<-` derivation, not a `~>` chain.
        eff, prop, ty, last = set(), set(), TName("Unit"), len(n.steps) - 1
        for i, st in enumerate(n.steps):
            sty, se, sp = s.synth(st, env); eff |= se
            if i < last:
                step_fails = sp | (sty.fails if isinstance(sty, Fal) else set())
                if not se and not step_fails:
                    s.err(f"{s.cur_who} (~>)", "orders a step, but this step is pure -- pure "
                                    "derivation has no order; use `<-` instead of `~>`")
                prop |= step_fails          # a failed step aborts the sequence -> propagates
                ty = TName("Unit")
            else:
                prop |= sp; ty = sty        # the last step is the value of the whole `~>`
        return ty, eff, prop

    def error_tag(s, e):
        if isinstance(e, Ctor): return e.tag
        if isinstance(e, Var) and e.name[:1].isupper(): return e.name
        return None

    def synth_call(s, n, env):
        if (isinstance(n.fn, Var) and n.fn.name in s.cap_of_method
                and n.fn.name not in s.globals):
            cap = s.cap_of_method[n.fn.name]
            if len(s.cap_tvars.get(cap, [None])) > 1:
                return s.synth_multi_method_call(n, env, cap)   # multiple dispatch (>1 type var)
            return s.synth_method_call(n, env)        # a capability method -> resolve + dispatch
        fty, fe, fp = s.synth(n.fn, env)
        who = f"call to {n.fn.name}" if isinstance(n.fn, Var) else "call"
        return s.apply_call(n, fty, env, fe, fp, who)

    def synth_method_call(s, n, env):
        # `compare(a,b)` / `fmap(xs,f)` -- build the method's signature as a generic function
        # whose cap var (Ord's T / Functor's F) is an extra hole carrying a `given _: Cap`
        # constraint, then reuse apply_call: unification infers the receiver, and the
        # constraint discharge demands the receiver actually `provides Cap`.
        cap = s.cap_of_method[n.fn.name]
        m = s.capabilities[cap][n.fn.name]
        capvar, kind = s.cap_tvar[cap], s.cap_kind[cap]
        params = [pt if pt else TName("?") for (_, pt) in (m.sig.params or [])]
        fty = TFunc(params, m.sig.ret or TName("?"), m.sig.eff or Row(), m.sig.fail or Row())
        fty.generics = list(m.sig.generics) + [("ctor" if kind else "type", capvar)]
        fty.constraints = [(capvar, cap)]
        return s.apply_call(n, fty, env, set(), set(), f"call to {n.fn.name} (method of {cap})")

    def synth_multi_method_call(s, n, env, cap):
        # MULTIPLE DISPATCH: infer each capability type var from the argument at its position, then
        # require an instance for that exact type combination (e.g. `(Ship, Asteroid) provides Collide`).
        m = s.capabilities[cap][n.fn.name]
        tvars = s.cap_tvars[cap]
        who = f"call to {n.fn.name} (method of {cap})"
        eff, prop, argtypes = set(), set(), []
        for a in n.args:
            at, ae, ap = s.synth(a, env)
            argtypes.append(s.plain(at, "argument", a)); eff |= ae; prop |= ap
        subst = {}
        for i, (pn, pt) in enumerate(m.sig.params or []):     # infer tvar := the arg type at its position
            if i < len(argtypes) and isinstance(pt, TName) and pt.name in tvars and pt.name not in subst:
                subst[pt.name] = argtypes[i]
        bounds = [subst.get(tv, TName("?")) for tv in tvars]
        if all(isinstance(b, TName) and b.name != "?" for b in bounds):   # all known -> demand an instance
            key = tuple(b.name for b in bounds)
            if (key, cap) not in s.instances:
                s.err(who, f"no instance ({', '.join(key)}) provides {cap} "
                           f"-- no `{key[0]} provides {cap} for {', '.join(key[1:])}` in scope")
        ret = s.subst_type(m.sig.ret or TName("?"), subst)
        return ret, eff | set((m.sig.eff or Row()).labels), prop | set((m.sig.fail or Row()).labels)

    def apply_call(s, n, fty, env, fe, fp, who):
        eff, prop = set(fe), set(fp)
        if not isinstance(fty, TFunc):
            for a in n.args:
                at, ae, ap = s.synth(a, env); s.plain(at, "argument", a); eff |= ae; prop |= ap
            return TName("?"), eff, prop
        gens = getattr(fty, "generics", [])
        tvars = {g[1] for g in gens if g[0] == "type"}
        rvars = {g[1] for g in gens if g[0] in ("effect", "failure")}
        cvars = {g[1] for g in gens if g[0] == "ctor"}      # higher-kinded "container" holes
        subst = {}
        for i, a in enumerate(n.args):                  # pass 1: non-lambda args
            if isinstance(a, Lambda): continue
            at, ae, ap = s.synth(a, env)
            at = s.plain(at, "argument", a); eff |= ae; prop |= ap
            if i < len(fty.params): s.unify(fty.params[i], at, subst, tvars, rvars, cvars, who)
        for i, a in enumerate(n.args):                  # pass 2: lambda args (need subst)
            if not isinstance(a, Lambda): continue
            expected = fty.params[i] if i < len(fty.params) else None
            s.check_lambda(a, expected, subst, env, tvars, rvars, cvars, who)
        for tv, cap in getattr(fty, "constraints", []):   # discharge `given tv: cap`
            bound = subst.get(tv, TName("?"))
            if not s.satisfies(bound, cap):
                s.err(who, f"{s.show(bound)} does not provide {cap} "
                           f"-- no `{s.show(bound)} provides {cap}` instance in scope")
        ceff = s.row_to_set(fty.eff, subst)
        cfail = s.row_to_set(fty.fail, subst)
        ret = s.subst_type(fty.ret, subst)
        eff |= ceff
        return (Fal(ret, cfail) if cfail else ret), eff, prop

    def check_lambda(s, lam, expected, subst, env, tvars, rvars, cvars=(), who=""):
        if not isinstance(expected, TFunc):
            s.synth(lam, env); return
        local = dict(env)
        for p, pt in zip(lam.params, expected.params):
            local[p] = s.subst_type(pt, subst)
        bty, be, bp = s.synth(lam.body, local)
        bret = bty.ty if isinstance(bty, Fal) else bty
        bfails = (bty.fails if isinstance(bty, Fal) else set()) | bp
        if expected.eff.var in rvars:
            subst[expected.eff.var] = subst.get(expected.eff.var, set()) | be
        if expected.fail.var in rvars:
            subst[expected.fail.var] = subst.get(expected.fail.var, set()) | bfails
        s.unify(expected.ret, bret, subst, tvars, rvars, cvars, who)

    def synth_match(s, n, env):
        sty, se, sp = s.synth(n.scrut, env)
        eff, prop = set(se), set(sp)
        result, any_fal, res_fails = TName("?"), False, set()
        for pat, expr in n.arms:
            local = dict(env)
            s.bind_pattern(pat, sty, local)
            ety, ee, ep = s.synth(expr, local); eff |= ee; prop |= ep
            if isinstance(ety, Fal): any_fal = True; res_fails |= ety.fails; armty = ety.ty
            else: armty = ety
            result = s.join(result, armty, "<match>", "match arms")
        who = f"match on {n.scrut.name}" if isinstance(n.scrut, Var) else "<match>"
        s.check_exhaustive(sty, [p for p, _ in n.arms], who)
        # matching on the scrutinee HANDLES its failures -> they are not propagated
        return (Fal(result, res_fails) if any_fal else result), eff, prop

    def check_exhaustive(s, sty, pats, who):
        # a `match` must cover every case of its scrutinee -- the dual of "an `and`
        # type demands every field". A catch-all (`_` or a bare binding) covers all.
        base = sty.ty if isinstance(sty, Fal) else sty
        if any(isinstance(p, (PWild, PVar)) for p in pats):
            return
        if isinstance(sty, Fal) or any(isinstance(p, (POk, PFail)) for p in pats):
            miss = [m for m, has in (("ok", any(isinstance(p, POk) for p in pats)),
                                     ("fail", any(isinstance(p, PFail) for p in pats))) if not has]
            if miss:
                s.err(who, f"non-exhaustive: missing {', '.join(miss)} case "
                           f"-- a fallible value is `ok or fail`; cover both or add `_`")
            return
        if isinstance(base, TName):
            if base.name == "List":
                if any(isinstance(p, PList) and not p.items and p.rest is not None for p in pats):
                    return                                   # `[..t]` alone covers all lists
                miss = [m for m, has in (
                    ("[] (empty)",     any(isinstance(p, PList) and not p.items and p.rest is None for p in pats)),
                    ("[h, ..t] (non-empty)", any(isinstance(p, PList) and p.rest is not None for p in pats)),
                ) if not has]
                if miss: s.err(who, f"non-exhaustive match on List: missing {', '.join(miss)}")
                return
            if base.name in s.sumtypes:
                covered = {p.tag for p in pats if isinstance(p, PTag)}
                miss = sorted(s.sumtypes[base.name] - covered)
                if miss:
                    s.err(who, f"non-exhaustive match on {base.name}: missing {', '.join(miss)} "
                               f"-- every `or` case must be handled (or add `_`)")
                for u in sorted(covered - s.sumtypes[base.name]):
                    s.err(who, f"arm `{u}` is not a variant of {base.name}")
                return
            if base.name == "Bool":                          # Bool = true or false (2 variants)
                miss = [m for m, has in (
                    ("true",  any(isinstance(p, PLit) and p.v is True  for p in pats)),
                    ("false", any(isinstance(p, PLit) and p.v is False for p in pats)),
                ) if not has]
                if miss: s.err(who, f"non-exhaustive match on Bool: missing {', '.join(miss)} "
                                    f"-- cover both true and false (or add `_`)")
                return
            if base.name in ("Num", "Text"):
                s.err(who, f"non-exhaustive match on {base.name}: add a catch-all `_` "
                           f"(or a binding) -- {base.name} has unbounded values")
            # `?` / unannotated scrutinee -> gradual: stay lenient

    def synth_attempt(s, n, env):
        bty, be, bp = s.synth(n.body, env)
        body_fails = set(bp) | (bty.fails if isinstance(bty, Fal) else set())
        eff, prop = set(be), set()
        handled, catchall = set(), False
        armty = bty.ty if isinstance(bty, Fal) else bty   # attempt yields body- or rescue-value
        for pat, expr in n.arms:
            if isinstance(pat, PWild): catchall = True
            elif isinstance(pat, PTag): handled.add(pat.tag)
            local = dict(env); s.bind_pattern(pat, TName("?"), local)
            ety, ee, ep = s.synth(expr, local); eff |= ee; prop |= ep
            armty = s.join(armty, ety.ty if isinstance(ety, Fal) else ety,
                           "<attempt>", "attempt and rescue")
        remaining = set() if catchall else (body_fails - handled)
        return armty, eff, prop | remaining           # unhandled failures escape the attempt

    def synth_block(s, n, env):
        local, eff, prop, ty = dict(env), set(), set(), TName("Unit")
        for i, (kind, *rest) in enumerate(n.stmts):
            last = (i == len(n.stmts) - 1)
            if kind == "let":
                name, expr = rest
                ety, ee, ep = s.synth(expr, local); eff |= ee; prop |= ep
                local[name] = s.plain(ety, f"binding '{name}'", expr); ty = TName("Unit")
            else:
                (expr,) = rest
                ety, ee, ep = s.synth(expr, local); eff |= ee; prop |= ep
                if not last: s.plain(ety, "statement", expr)
                ty = ety
        return ty, eff, prop

    # ---- the OTHER half of "compiler infers, tool reveals": show the contract ----
    def reveal(s, defs):
        s.register(defs)
        out = []
        for d in defs:
            if isinstance(d, FuncDef):
                env = dict(s.globals)
                if d.sig and d.sig.params:
                    for (pn, pt) in d.sig.params: env[pn] = pt if pt else TName("?")
                else:
                    for pn in d.params: env[pn] = TName("?")
                s.active_constraints = set(d.sig.constraints) if d.sig else set()
                s.cur_who = d.name
                bty, be, bp = s.synth(d.body, env)
                out.append(s.contract_line(d.name, d.params, d.sig, bty, be, bp))
            elif isinstance(d, ValDef):
                s.active_constraints = set(d.sig.constraints) if d.sig else set()
                s.cur_who = d.name
                bty, be, bp = s.synth(d.body, dict(s.globals))
                out.append(s.contract_line(d.name, None, d.sig, bty, be, bp))
        return out

    def contract_line(s, name, params, sig, bty, be, bp):
        succ = bty.ty if isinstance(bty, Fal) else bty
        fails = set(bp) | (bty.fails if isinstance(bty, Fal) else set())
        if sig:                                         # a written contract -- show as declared
            eff, fl = sig.eff or Row(), sig.fail or Row()
            ret = sig.ret or TName("?")
            effs = set(eff.labels) | ({eff.var} if eff.var else set())
            fls = set(fl.labels) | ({fl.var} if fl.var else set())
            tag = "declared"
        else:                                           # no contract -- INFER it from the body
            ret, effs, fls, tag = succ, be, fails, "inferred"
        out = s.show(ret)
        if effs: out += " !" + fmt_set(effs)
        if fls:  out += " ?" + fmt_set(fls)
        head = name + ("(" + ", ".join(params) + ")" if params is not None else "")
        return (f"{head} : {out}", tag)

    def bind_pattern(s, pat, ty, env):
        t = type(pat)
        if t is PVar: env[pat.name] = TName("?")
        elif t is POk:  s.bind_pattern(pat.inner, ty.ty if isinstance(ty, Fal) else TName("?"), env)
        elif t is PFail: s.bind_pattern(pat.inner, TName("?"), env)
        elif t is PTag and pat.fields:
            for fp in pat.fields.values(): s.bind_pattern(fp, TName("?"), env)
        elif t is PList:
            for p in pat.items: s.bind_pattern(p, TName("?"), env)
            if pat.rest: env[pat.rest] = TName("?")

def check_file(path):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    defs = parse_program_with_includes(src)
    errors = list(dict.fromkeys(Checker().check(defs)))   # dedupe, keep order
    if not errors:
        print(f"OK  {path}  -- effects and failures all accounted for")
        return 0
    print(f"FAIL  {path}  -- {len(errors)} problem(s):")
    for e in errors:
        print(f"  - {e}")
    return 1

def reveal_file(path):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    lines = Checker().reveal(parse_program_with_includes(src))
    print(f"REVEAL  {path}  -- the full contract of each definition:")
    for sigstr, tag in lines:
        print(f"  {sigstr:<46}  [{tag}]")
    return 0

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # avoid cp932 issues on Windows consoles
    except Exception:
        pass
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        print("usage: python check.py [--reveal] <file.prism>"); sys.exit(2)
    try:
        sys.exit(reveal_file(args[0]) if "--reveal" in flags else check_file(args[0]))
    except (SyntaxError, RuntimeError) as e:
        print(f"[parse error] {e}", file=sys.stderr); sys.exit(2)
