#!/usr/bin/env python3
"""
Prism v0 -- a tree-walking interpreter for the "four voices" language.

Design under test:
  :   fact / type        ->  parsed, NOT yet checked (v0 is dynamically typed)
  <-  flow / derivation  ->  definitions; line order is MEANINGLESS (lazy thunks)
  !   effect             ->  show!console / read!console actually do IO
  ?   failure            ->  ok / fail values, `try` propagates, attempt/rescue handles
  ~>  time               ->  explicit ordered steps; each step must touch time (! or ?)

Run:  python prism.py examples/divide.prism
"""
import sys, re, math, os

# --------------------------------------------------------------------------
# 1. LEXER  (indentation-aware: emits INDENT / DEDENT / NEWLINE)
# --------------------------------------------------------------------------
KEYWORDS = {"match", "try", "attempt", "rescue", "ok", "fail", "include",
            "for", "given", "and", "or", "capability", "provides", "true", "false",
            "if", "then", "else"}

class Tok:
    def __init__(self, kind, val, line):
        self.kind, self.val, self.line = kind, val, line
    def __repr__(self): return f"{self.kind}:{self.val!r}"

# multi-char operators first
OPS = ["<-", "~>", "=>", "->", "|>", "..", "==", "<=", ">=", "!=",
       ":", "!", "?", "(", ")", "{", "}", "[", "]", ",",
       "=", "+", "-", "*", "/", "<", ">", "."]

def strip_line_comment(raw):
    # cut a trailing `--` comment, but NOT when the `--` sits inside a "..." string literal
    # (mirrors the string lexer's escape rule). Otherwise `show!console "a -- b"` loses "-- b".
    i, n = 0, len(raw)
    while i < n:
        c = raw[i]
        if c == '"':                                  # skip over a string literal
            i += 1
            while i < n and raw[i] != '"':
                i += 2 if (raw[i] == "\\" and i + 1 < n) else 1
            i += 1; continue
        if c == '-' and i + 1 < n and raw[i + 1] == '-':
            return raw[:i]                            # comment starts here (outside any string)
        i += 1
    return raw

def lex(src):
    lines = src.split("\n")
    toks = []
    indents = [0]
    bracket_depth = 0
    for lineno, raw in enumerate(lines, 1):
        # strip comments (string-aware: a `--` inside a "..." literal is NOT a comment)
        if "--" in raw:
            raw = strip_line_comment(raw)
        stripped = raw.strip()
        if stripped == "" and bracket_depth == 0:
            continue  # blank line -> ignored
        # indentation (only matters at bracket depth 0)
        if bracket_depth == 0:
            indent = len(raw) - len(raw.lstrip(" "))
            if indent > indents[-1]:
                indents.append(indent)
                toks.append(Tok("INDENT", indent, lineno))
            while indent < indents[-1]:
                indents.pop()
                toks.append(Tok("DEDENT", indent, lineno))
        i, n, s = 0, len(raw), raw
        while i < n:
            c = s[i]
            if c == " " or c == "\t":
                i += 1; continue
            # string literal
            if c == '"':
                j = i + 1; buf = []
                while j < n and s[j] != '"':
                    if s[j] == "\\" and j + 1 < n:
                        buf.append(s[j+1]); j += 2; continue
                    buf.append(s[j]); j += 1
                toks.append(Tok("TEXT", "".join(buf), lineno))
                i = j + 1; continue
            # number
            m = re.match(r'\d+(\.\d+)?', s[i:])
            if m:
                txt = m.group(0)
                toks.append(Tok("NUM", float(txt) if "." in txt else int(txt), lineno))
                i += len(txt); continue
            # identifier / keyword
            m = re.match(r'[A-Za-z_][A-Za-z0-9_]*', s[i:])
            if m:
                name = m.group(0)
                kind = "KW" if name in KEYWORDS else "ID"
                toks.append(Tok(kind, name, lineno))
                i += len(name); continue
            # operators
            for op in OPS:
                if s.startswith(op, i):
                    if op in "([{": bracket_depth += 1
                    if op in ")]}": bracket_depth = max(0, bracket_depth - 1)
                    toks.append(Tok("OP", op, lineno))
                    i += len(op); break
            else:
                raise SyntaxError(f"line {lineno}: unexpected char {c!r}")
        if bracket_depth == 0:
            toks.append(Tok("NEWLINE", None, lineno))
    while len(indents) > 1:
        indents.pop(); toks.append(Tok("DEDENT", 0, lineno))
    toks.append(Tok("EOF", None, lineno))
    return toks

# --------------------------------------------------------------------------
# 2. AST
# --------------------------------------------------------------------------
class Node: line = 0          # source line, stamped by the parser (0 = unknown)
class Num(Node):
    def __init__(s, v): s.v = v
class Text(Node):
    def __init__(s, v): s.v = v
class Bool(Node):
    def __init__(s, v): s.v = v
class Var(Node):
    def __init__(s, name): s.name = name
class ListLit(Node):
    def __init__(s, items, rest=None): s.items, s.rest = items, rest
class Bin(Node):
    def __init__(s, op, l, r): s.op, s.l, s.r = op, l, r
class Call(Node):
    def __init__(s, fn, args): s.fn, s.args = fn, args
class Field(Node):
    def __init__(s, obj, name): s.obj, s.name = obj, name
class Lambda(Node):
    def __init__(s, params, body): s.params, s.body = params, body
class Ctor(Node):              # Circle{radius: e} or bare DivByZero
    def __init__(s, tag, fields): s.tag, s.fields = tag, fields
class OkE(Node):
    def __init__(s, e): s.e = e
class FailE(Node):
    def __init__(s, e): s.e = e
class TryE(Node):
    def __init__(s, e): s.e = e
class EffectCall(Node):        # show!console arg
    def __init__(s, op, world, arg): s.op, s.world, s.arg = op, world, arg
class Match(Node):
    def __init__(s, scrut, arms): s.scrut, s.arms = scrut, arms   # arms: [(pat, expr)]
class Attempt(Node):
    def __init__(s, body, arms): s.body, s.arms = body, arms
class Block(Node):
    def __init__(s, stmts): s.stmts = stmts        # stmts: [("let",name,e) | ("expr",e)]
class Seq(Node):           # e1 ~> e2 ~> ...  -- the TIME voice: explicit ordered steps
    def __init__(s, steps): s.steps = steps
class FuncDef(Node):
    def __init__(s, name, params, body): s.name, s.params, s.body, s.sig = name, params, body, None
class ValDef(Node):
    def __init__(s, name, body): s.name, s.body, s.sig = name, body, None
class TypeDef(Node):           # Shape : Circle{..} or Square{..}  -- a sum (`or`) type
    def __init__(s, name, variants, fields=None):
        s.name, s.variants = name, variants            # variants: [tag]
        s.fields = fields or {}                        # {tag: [(field_name, type)]}  (declared fields)
class Capability(Node):        # capability Ord for T { .. } / Collide for A, B { .. }  -- a trait
    def __init__(s, name, tvars, kind, methods):    # tvars: list of type vars (>1 = multiple dispatch)
        s.tvars, s.name, s.kind, s.methods = tvars, name, kind, methods
        s.tvar = tvars[0] if tvars else None        # back-compat: the first/only type var
class Provides(Node):          # Num provides Ord { .. } / Ship provides Collide for Asteroid { .. }
    def __init__(s, types, cap, methods):           # types: list (>1 = a multi-type instance)
        s.types, s.cap, s.methods = types, cap, methods
        s.type_name = types[0] if types else None   # back-compat: the primary/only type
class Member(Node):            # one method: a capability SIGNATURE (body=None) or an instance DEF
    def __init__(s, name, params, sig, body): s.name, s.params, s.sig, s.body = name, params, sig, body
class Include(Node):           # include "path"  -- merge another file's definitions (no namespaces)
    def __init__(s, path): s.path = path

# ---- type-annotation AST (parsed by the signature parser, consumed by the checker) ----
class Row:        # an effect row or a failure row: labels + optional tail variable
    def __init__(s, labels=(), var=None): s.labels, s.var = set(labels), var
class TName:      # named type, possibly applied: Num, Text, List[T], or a type-var T
    def __init__(s, name, args=None): s.name, s.args = name, (args or [])
class TFunc:      # (params) -> ret  carrying effect & failure rows
    def __init__(s, params, ret, eff, fail): s.params, s.ret, s.eff, s.fail = params, ret, eff, fail
class Sig:
    def __init__(s, generics, params, ret, eff, fail, constraints=()):
        s.generics, s.params, s.ret, s.eff, s.fail = generics, params, ret, eff, fail
        s.constraints = list(constraints)        # [(tvar, capability)]  from `given T: Cap`

# patterns
class PWild(Node): pass
class PLit(Node):
    def __init__(s, v): s.v = v
class PVar(Node):
    def __init__(s, name): s.name = name
class PTag(Node):              # uppercase nullary tag, e.g. DivByZero  (also Ctor{..})
    def __init__(s, tag, fields): s.tag, s.fields = tag, fields   # fields: dict name->pat or None
class POk(Node):
    def __init__(s, inner): s.inner = inner
class PFail(Node):
    def __init__(s, inner): s.inner = inner
class PList(Node):
    def __init__(s, items, rest): s.items, s.rest = items, rest

# --------------------------------------------------------------------------
# 3. PARSER  (recursive descent + Pratt for expressions)
# --------------------------------------------------------------------------
class Parser:
    def __init__(s, toks): s.toks, s.i, s.cur_rowvars = toks, 0, set()
    def peek(s, k=0): return s.toks[s.i + k]
    def kind(s): return s.toks[s.i].kind
    def val(s):  return s.toks[s.i].val
    def at_op(s, *ops):  return s.kind() == "OP" and s.val() in ops
    def at_kw(s, *kws):  return s.kind() == "KW" and s.val() in kws
    def adv(s): t = s.toks[s.i]; s.i += 1; return t
    def eat_op(s, op):
        if not s.at_op(op): s.err(f"expected '{op}'")
        return s.adv()
    def eat_kind(s, kind):
        if s.kind() != kind: s.err(f"expected {kind}")
        return s.adv()
    def err(s, msg):
        t = s.peek(); raise SyntaxError(f"line {t.line}: {msg}, got {t.kind}:{t.val!r}")
    def skipnl(s):
        while s.kind() == "NEWLINE": s.adv()

    # ---- top level ----
    def parse_program(s):
        defs = []
        s.skip_sep()
        while s.kind() != "EOF":
            d = s.parse_def()
            if d is not None: defs.append(d)
            s.skip_sep()
        return defs

    def skip_sep(s):
        # between top-level defs we are back at column 0; tolerate stray NEWLINE/DEDENT
        # (a signature continuation line consumes an INDENT whose DEDENT lands here)
        while s.kind() in ("NEWLINE", "DEDENT", "INDENT"): s.adv()

    def skip_sig_continuation(s):
        # allow a signature to continue on an indented next line:
        #     map for T, U, !e, ?g
        #       (xs: List[T], ...) : List[U] !e ?g  <-
        if s.kind() != "NEWLINE": return
        save = s.i
        s.skipnl()
        if s.kind() == "INDENT" and s.peek(1).kind == "OP" and s.peek(1).val in ("(", ":"):
            s.adv()           # consume the INDENT; its DEDENT is absorbed by skip_sep()
            return
        s.i = save            # not a continuation -> leave the body indentation alone

    def parse_def(s):
        def_ln = s.peek().line
        if s.at_kw("include"):
            s.adv()
            return Include(s.eat_kind("TEXT").val)
        if s.at_kw("capability"):
            return s.parse_capability()
        name = s.eat_kind("ID").val
        if s.at_kw("provides"):
            return s.parse_provides(name)
        generics, constraints = [], []
        s.cur_rowvars = set()
        if s.at_kw("for"):
            generics, constraints = s.parse_generics()
            s.cur_rowvars = {g[1] for g in generics if g[0] in ("effect", "failure")}
        s.skip_sig_continuation()
        params = None
        if s.at_op("("):
            params = s.parse_params()
        ret = eff = fail = None
        has_sig = False
        if s.at_op(":"):
            if params is None and not s.line_has_arrow():
                # `Name : A or B ...` with no `<-` is a TYPE declaration, not a value.
                s.adv()
                decl = s.parse_decl_variants()
                s.cur_rowvars = set()
                if not decl: return None
                variants, fields = decl
                return TypeDef(name, variants, fields)
            s.adv(); has_sig = True
            ret, eff, fail = s.parse_sig_tail()
        if not s.at_op("<-"):
            # capability / provides / record decl: v0 ignores it, consume the line/block
            s.consume_decl_block()
            s.cur_rowvars = set()
            return None
        s.eat_op("<-")
        body = s.parse_body()
        s.cur_rowvars = set()
        sig = (Sig(generics, params, ret, eff, fail, constraints)
               if (has_sig or generics) else None)
        if params is not None:
            d = FuncDef(name, [p[0] for p in params], body); d.sig = sig; d.line = def_ln; return d
        d = ValDef(name, body); d.sig = sig; d.line = def_ln; return d

    def parse_generics(s):
        s.adv()  # 'for'
        gens = []
        while True:
            if s.at_op("!"):   s.adv(); gens.append(("effect", s.eat_kind("ID").val))
            elif s.at_op("?"): s.adv(); gens.append(("failure", s.eat_kind("ID").val))
            elif s.kind() == "ID":
                nm = s.adv().val
                if s.at_op("["):              # F[_] : a higher-kinded "container hole"
                    s.adv(); arity = 0
                    while not s.at_op("]"):
                        s.adv(); arity += 1   # each placeholder `_`
                        if s.at_op(","): s.adv()
                    s.eat_op("]")
                    gens.append(("ctor", nm, arity))
                else:
                    gens.append(("type", nm))
            else: break
            if s.at_op(","): s.adv(); continue
            break
        constraints = []        # `given T: Ord, U: Show` -- a membership FACT to discharge
        if s.at_kw("given"):
            s.adv()
            while s.kind() == "ID":
                tv = s.adv().val
                s.eat_op(":")
                constraints.append((tv, s.eat_kind("ID").val))
                if s.at_op(","): s.adv(); continue
                break
        return gens, constraints

    def parse_capability(s):
        cap_ln = s.peek().line
        s.adv()  # 'capability'
        cap = s.eat_kind("ID").val
        tvars, kind = [], 0
        if s.at_kw("for"):
            s.adv()
            while True:                            # `for T` | `for F[_]` | `for A, B` (multi-dispatch)
                tvars.append(s.eat_kind("ID").val)
                if s.at_op("["):                   # higher-kinded: `for F[_]` / `F[_, _]`
                    s.adv()
                    while not s.at_op("]") and s.kind() != "EOF":
                        if not s.at_op(","): kind += 1
                        s.adv()
                    s.eat_op("]")
                if not s.at_op(","): break
                s.adv()                            # consume `,` and read the next type var
        c = Capability(cap, tvars, kind, s.parse_member_block()); c.line = cap_ln; return c

    def parse_provides(s, type_name):
        p_ln = s.peek().line
        s.adv()  # 'provides'
        cap = s.eat_kind("ID").val
        types = [type_name]
        if s.at_kw("for"):                         # multi-type instance: `Ship provides Collide for Asteroid`
            s.adv()
            while True:
                types.append(s.eat_kind("ID").val)
                if not s.at_op(","): break
                s.adv()
        p = Provides(types, cap, s.parse_member_block()); p.line = p_ln; return p

    def parse_member_block(s):
        # an indented block of members, each parsed in full (sig and, for instances, body).
        members = []
        if s.kind() == "NEWLINE": s.skipnl()
        if s.kind() != "INDENT": return members
        s.eat_kind("INDENT"); s.skipnl()
        while s.kind() not in ("DEDENT", "EOF"):
            members.append(s.parse_member())
            s.skipnl()
        if s.kind() == "DEDENT": s.adv()
        return members

    def parse_member(s):
        # name [for generics] [(params)] [: ret !e ?g] [<- body]
        m_ln = s.peek().line
        name = s.eat_kind("ID").val
        generics, constraints = [], []
        s.cur_rowvars = set()
        if s.at_kw("for"):
            generics, constraints = s.parse_generics()
            s.cur_rowvars = {g[1] for g in generics if g[0] in ("effect", "failure")}
        s.skip_sig_continuation()
        params = None
        if s.at_op("("):
            params = s.parse_params()
        ret = eff = fail = None
        if s.at_op(":"):
            s.adv(); ret, eff, fail = s.parse_sig_tail()
        body = None
        if s.at_op("<-"):
            s.adv(); body = s.parse_body()
        s.cur_rowvars = set()
        mem = Member(name, params, Sig(generics, params, ret, eff, fail, constraints), body)
        mem.line = m_ln; return mem

    def line_has_arrow(s):
        # does a `<-` appear on the current logical line? (brackets suppress NEWLINE,
        # so scanning to the next NEWLINE/INDENT spans the whole line)
        j = s.i
        while s.toks[j].kind not in ("NEWLINE", "EOF", "INDENT"):
            t = s.toks[j]
            if t.kind == "OP" and t.val == "<-": return True
            j += 1
        return False

    def parse_decl_variants(s):
        # `Tag{..}? (or Tag{..}?)*` -> ([tags], {tag: [(field, type)]}) if a sum (>=1 `or`)
        # or a single record (`Name : C{...}`), else None. The `or` chain may wrap across
        # indented lines, so skip layout between variants.
        tags, fields, saw_or, saw_brace = [], {}, False, False
        if not (s.kind() == "ID" and s.val()[:1].isupper()):
            s.consume_decl_block(); return None
        cur = s.adv().val; tags.append(cur)
        if s.at_op("{"): saw_brace = True; fields[cur] = s.parse_braced_fields()
        while True:
            save = s.i
            while s.kind() in ("NEWLINE", "INDENT", "DEDENT"): s.adv()
            if s.at_kw("or"):
                s.adv(); saw_or = True
                if s.kind() == "ID" and s.val()[:1].isupper():
                    cur = s.adv().val; tags.append(cur)
                    if s.at_op("{"): saw_brace = True; fields[cur] = s.parse_braced_fields()
                continue
            s.i = save; break                 # no more variants -> rewind the skipped layout
        s.consume_decl_block()
        # a real type: a sum (`or`) OR a single constructor with fields (`Name : C{...}`),
        # but NOT a bare alias like `Temp : Num`.
        return (tags, fields) if (saw_or or saw_brace) else None

    def parse_braced_fields(s):
        # `{ name: Type, name: Type }` -> [(name, type-or-None)]
        s.eat_op("{")
        out = []
        while not s.at_op("}"):
            fname = s.eat_kind("ID").val
            ftype = None
            if s.at_op(":"): s.adv(); ftype = s.parse_type()
            out.append((fname, ftype))
            if s.at_op(","): s.adv()
        s.eat_op("}")
        return out

    def consume_decl_block(s):
        while s.kind() not in ("NEWLINE", "EOF"): s.adv()
        s.skipnl()
        if s.kind() == "INDENT":
            depth = 0
            s.adv(); depth = 1
            while depth > 0 and s.kind() != "EOF":
                if s.kind() == "INDENT": depth += 1
                elif s.kind() == "DEDENT": depth -= 1
                s.adv()

    def parse_params(s):
        s.eat_op("(")
        params = []
        while not s.at_op(")"):
            pname = s.eat_kind("ID").val
            ptype = None
            if s.at_op(":"):
                s.adv(); ptype = s.parse_type()
            params.append((pname, ptype))
            if s.at_op(","): s.adv()
        s.eat_op(")")
        return params

    def parse_type(s):
        if s.at_op("_") or (s.kind() == "ID" and s.val() == "_"):   # `_` = the gradual Unknown type
            s.adv(); return TName("?")
        if s.at_op("("):
            s.adv()
            inner = []
            while not s.at_op(")"):
                inner.append(s.parse_type())
                if s.at_op(","): s.adv()
            s.eat_op(")")
            if s.at_op("->"):
                s.adv()
                ret, eff, fail = s.parse_sig_tail()
                return TFunc(inner, ret, eff, fail)
            return inner[0] if inner else TName("Unit")
        name = s.eat_kind("ID").val
        args = []
        if s.at_op("["):
            s.adv()
            while not s.at_op("]"):
                args.append(s.parse_type())
                if s.at_op(","): s.adv()
            s.eat_op("]")
        return TName(name, args)

    def parse_sig_tail(s):
        ret = s.parse_type()
        eff, fail = Row(), Row()
        while s.at_op("!") or s.at_op("?"):
            if s.at_op("!"):
                s.adv(); eff = s.merge_row(eff, s.parse_row())
            else:
                s.adv(); fail = s.merge_row(fail, s.parse_row())
        return ret, eff, fail

    def merge_row(s, a, b):
        return Row(a.labels | b.labels, b.var or a.var)

    def parse_row(s):
        labels, var = [], None
        if s.at_op("{"):
            s.adv()
            while not s.at_op("}"):
                if s.at_op(".."):
                    s.adv(); var = s.eat_kind("ID").val
                else:
                    nm = s.eat_kind("ID").val
                    (labels.append(nm) if nm not in s.cur_rowvars else (var := nm))
                if s.at_op(","): s.adv()
            s.eat_op("}")
        else:
            nm = s.eat_kind("ID").val
            if nm in s.cur_rowvars: var = nm
            else: labels.append(nm)
        return Row(labels, var)

    # ---- bodies / blocks ----
    def parse_body(s):
        # body is either an inline expression, or a newline+indented block
        if s.kind() == "NEWLINE":
            s.skipnl()
            if s.kind() == "INDENT":
                return s.parse_block()
        return s.parse_expr()

    def parse_block(s):
        s.eat_kind("INDENT")
        stmts = []
        s.skipnl()
        while s.kind() not in ("DEDENT", "EOF"):
            stmts.append(s.parse_stmt())
            s.skipnl()
        if s.kind() == "DEDENT": s.adv()
        return Block(stmts)

    def parse_stmt(s):
        # let-binding:  name <- expr
        if s.kind() == "ID" and s.peek(1).kind == "OP" and s.peek(1).val == "<-":
            name = s.adv().val
            s.eat_op("<-")
            return ("let", name, s.parse_expr())
        return ("expr", s.parse_expr())

    # ---- expressions (Pratt) ----
    PREC = {"==":1, "!=":1, "<":1, ">":1, "<=":1, ">=":1,
            "+":2, "-":2, "*":3, "/":3}

    def parse_expr(s, min_prec=0):
        ln = s.peek().line
        left = s.parse_postfix()
        # lambda:  x -> body   (single bare param already parsed as Var)
        if s.at_op("->") and isinstance(left, Var):
            s.adv()
            lam = Lambda([left.name], s.parse_expr()); lam.line = ln; return lam
        while s.at_op(*s.PREC.keys()):
            op = s.val(); prec = s.PREC[op]
            if prec < min_prec: break
            s.adv()
            right = s.parse_expr(prec + 1)
            left = Bin(op, left, right); left.line = ln
        # postfix `match`
        while s.at_kw("match"):
            left = s.parse_match(left)
        # pipe sugar (flow voice):  x |> f  ==>  f(x) ;  x |> f(a)  ==>  f(x, a)  (left-assoc).
        # The piped value becomes the FIRST argument (Prism's libs are data-first: clamp/nth/at/..).
        # Pure desugar to a Call, so the checker/runtime treat `x |> f` exactly as `f(x)`.
        while min_prec == 0 and s.at_op("|>"):
            s.adv()
            rhs = s.parse_postfix()                       # the function (a name or a call f(a))
            left = Call(rhs.fn, [left] + rhs.args) if isinstance(rhs, Call) else Call(rhs, [left])
            left.line = ln
        # time voice `~>` : lowest precedence, only at the top of an expression
        if min_prec == 0 and s.at_op("~>"):
            steps = [left]
            while s.at_op("~>"):
                s.adv()
                steps.append(s.parse_expr(1))    # min_prec=1 so a step never re-eats `~>`
            seq = Seq(steps); seq.line = ln; return seq
        return left

    def parse_match(s, scrut):
        m_ln = getattr(scrut, "line", 0) or s.peek().line
        s.adv()  # 'match'
        s.skipnl()
        s.eat_kind("INDENT")
        arms = []
        s.skipnl()
        while s.kind() not in ("DEDENT", "EOF"):
            pat = s.parse_pattern()
            s.eat_op("=>")
            expr = s.parse_body()
            arms.append((pat, expr))
            s.skipnl()
        if s.kind() == "DEDENT": s.adv()
        m = Match(scrut, arms); m.line = m_ln; return m

    def parse_postfix(s):
        ln = s.peek().line
        e = s.parse_atom()
        while True:
            if s.at_op("("):           # call
                args = s.parse_args()
                e = Call(e, args)
            elif s.at_op("."):
                s.adv(); name = s.eat_kind("ID").val
                e = Field(e, name)
            elif s.kind() == "OP" and s.val() == "!" and isinstance(e, Var):
                # effect call:  show!console <arg?>
                s.adv()
                world = s.eat_kind("ID").val
                arg = None
                if s.starts_expr():
                    arg = s.parse_expr(1)        # arg binds tighter than a `~>` sequence
                e = EffectCall(e.name, world, arg)
            else:
                break
        if not e.line: e.line = ln       # stamp the leaf / call / field / effect node
        return e

    def parse_args(s):
        s.eat_op("(")
        args = []
        while not s.at_op(")"):
            args.append(s.parse_expr())
            if s.at_op(","): s.adv()
        s.eat_op(")")
        return args

    def starts_expr(s):
        if s.kind() in ("NUM", "TEXT", "ID"): return True
        if s.kind() == "KW" and s.val() in ("ok", "fail", "try", "true", "false", "if"): return True
        if s.at_op("(", "[", "-"): return True
        return False

    def parse_atom(s):
        t = s.peek()
        if t.kind == "NUM": s.adv(); return Num(t.val)
        if t.kind == "TEXT": s.adv(); return Text(t.val)
        if s.at_kw("true"):  s.adv(); return Bool(True)
        if s.at_kw("false"): s.adv(); return Bool(False)
        if s.at_kw("ok"):    s.adv(); return OkE(s.parse_postfix())
        if s.at_kw("fail"):  s.adv(); return FailE(s.parse_postfix())
        if s.at_kw("try"):   s.adv(); return TryE(s.parse_postfix())  # binds to the call, like ok/fail
        if s.at_kw("attempt"): return s.parse_attempt()
        if s.at_kw("if"):    return s.parse_if()
        if s.at_op("-"):     s.adv(); return Bin("-", Num(0), s.parse_postfix())
        if s.at_op("("):
            # could be grouped expr, unit literal (), or lambda params (a, b) -> ...
            save = s.i
            s.adv()
            if s.at_op(")"):
                s.adv(); return Ctor("Unit", {})
            # try lambda param list
            if s.kind() == "ID":
                names = []; ok_lambda = True
                while True:
                    if s.kind() != "ID": ok_lambda = False; break
                    names.append(s.adv().val)
                    if s.at_op(","): s.adv(); continue
                    break
                if ok_lambda and s.at_op(")") and s.peek(1).kind == "OP" and s.peek(1).val == "->":
                    s.adv()  # )
                    s.adv()  # ->
                    return Lambda(names, s.parse_expr())
            s.i = save
            s.eat_op("(")
            e = s.parse_expr()
            s.eat_op(")")
            return e
        if s.at_op("["):
            return s.parse_list()
        if t.kind == "ID":
            s.adv()
            # constructor literal  Name{...}
            if s.at_op("{"):
                fields = s.parse_record_fields()
                return Ctor(t.val, fields)
            # bare uppercase name with no fields = nullary ctor (DivByZero)
            if t.val[:1].isupper():
                return Ctor(t.val, {})
            return Var(t.val)
        s.err("expected expression")

    def parse_record_fields(s):
        s.eat_op("{")
        fields = {}
        while not s.at_op("}"):
            fname = s.eat_kind("ID").val
            if s.at_op(":"):
                s.adv(); fields[fname] = s.parse_expr()
            else:
                fields[fname] = Var(fname)
            if s.at_op(","): s.adv()
        s.eat_op("}")
        return fields

    def parse_list(s):
        s.eat_op("[")
        items, rest = [], None
        while not s.at_op("]"):
            if s.at_op(".."):
                s.adv(); rest = s.parse_expr()
            else:
                items.append(s.parse_expr())
            if s.at_op(","): s.adv()
        s.eat_op("]")
        return ListLit(items, rest)

    def parse_if(s):
        # `if cond then a else b` -- an expression, desugared to a Bool match (both arms required).
        ln = s.peek().line
        s.adv()                                   # 'if'
        cond = s.parse_expr()
        if not s.at_kw("then"): s.err("expected 'then'")
        s.adv()
        thenE = s.parse_expr()
        if not s.at_kw("else"): s.err("expected 'else'")
        s.adv()
        elseE = s.parse_expr()
        m = Match(cond, [(PLit(True), thenE), (PLit(False), elseE)]); m.line = ln
        return m

    def parse_attempt(s):
        s.adv()  # attempt
        body = s.parse_body()
        s.skipnl()
        arms = []
        if s.at_kw("rescue"):
            s.adv()
            s.skipnl()
            s.eat_kind("INDENT")
            s.skipnl()
            while s.kind() not in ("DEDENT", "EOF"):
                pat = s.parse_pattern()
                s.eat_op("=>")
                expr = s.parse_body()
                arms.append((pat, expr))
                s.skipnl()
            if s.kind() == "DEDENT": s.adv()
        return Attempt(body, arms)

    # ---- patterns ----
    def parse_pattern(s):
        if s.at_op("_") or (s.kind() == "ID" and s.val() == "_"):
            s.adv(); return PWild()
        t = s.peek()
        if t.kind == "NUM": s.adv(); return PLit(t.val)
        if t.kind == "TEXT": s.adv(); return PLit(t.val)
        if s.at_kw("true"):  s.adv(); return PLit(True)     # Bool is a 2-variant `or` type
        if s.at_kw("false"): s.adv(); return PLit(False)
        if s.at_kw("ok"):   s.adv(); return POk(s.parse_pattern())
        if s.at_kw("fail"): s.adv(); return PFail(s.parse_pattern())
        if s.at_op("["):
            s.adv(); items, rest = [], None
            while not s.at_op("]"):
                if s.at_op(".."):
                    s.adv(); rest = s.eat_kind("ID").val
                else:
                    items.append(s.parse_pattern())
                if s.at_op(","): s.adv()
            s.eat_op("]")
            return PList(items, rest)
        if t.kind == "ID":
            s.adv()
            if t.val == "_": return PWild()
            if t.val[:1].isupper():
                fields = None
                if s.at_op("{"):
                    s.eat_op("{"); fields = {}
                    while not s.at_op("}"):
                        fn = s.eat_kind("ID").val
                        if s.at_op(":"):
                            s.adv(); fields[fn] = s.parse_pattern()
                        else:
                            fields[fn] = PVar(fn)
                        if s.at_op(","): s.adv()
                    s.eat_op("}")
                return PTag(t.val, fields)
            return PVar(t.val)
        s.err("expected pattern")

# --------------------------------------------------------------------------
# 4. VALUES + RUNTIME
# --------------------------------------------------------------------------
class Tagged:
    __slots__ = ("tag", "fields")
    def __init__(s, tag, fields): s.tag, s.fields = tag, fields
class Closure:
    def __init__(s, params, body, env, name="?"):
        s.params, s.body, s.env, s.name = params, body, env, name
class Thunk:
    def __init__(s, body, env): s.body, s.env, s.done, s.val = body, env, False, None
class PrismFailure(Exception):
    def __init__(s, error): s.error = error
UNIT = Tagged("Unit", {})

class Env:
    def __init__(s, parent=None): s.vars, s.parent = {}, parent
    def get(s, name):
        e = s
        while e is not None:
            if name in e.vars: return e.vars[name]
            e = e.parent
        raise NameError(f"unknown name '{name}'")
    def set(s, name, v): s.vars[name] = v

def is_fail(v): return isinstance(v, Tagged) and v.tag == "fail"

def prism_str(v):
    if v is UNIT or (isinstance(v, Tagged) and v.tag == "Unit"): return "()"
    if isinstance(v, bool): return "true" if v else "false"
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else str(v)
    if isinstance(v, int): return str(v)
    if isinstance(v, str): return v
    if isinstance(v, list): return "[" + ", ".join(prism_str(x) for x in v) + "]"
    if isinstance(v, Tagged):
        if v.tag == "ok": return prism_str(v.fields["value"])
        if v.tag == "fail": return "fail " + prism_str(v.fields["error"])
        if not v.fields: return v.tag
        inner = ", ".join(f"{k}: {prism_str(x)}" for k, x in v.fields.items())
        return f"{v.tag}{{{inner}}}"
    if isinstance(v, Closure): return f"<fn {v.name}>"
    return str(v)

# --------------------------------------------------------------------------
# 5. EVALUATOR
# --------------------------------------------------------------------------
def interpolate(s, env):
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == "{":
            depth, j = 1, i + 1            # find the MATCHING `}` (records nest inside interp)
            while j < n and depth > 0:
                if s[j] == "{": depth += 1
                elif s[j] == "}":
                    depth -= 1
                    if depth == 0: break
                j += 1
            if depth != 0: out.append(s[i:]); break    # unbalanced -> emit literally
            expr_src = s[i+1:j]
            sub = Parser(lex(expr_src)).parse_expr()
            out.append(prism_str(ev(sub, env)))
            i = j + 1
        else:
            out.append(c); i += 1
    return "".join(out)

def force(v):
    if isinstance(v, Thunk):
        if not v.done:
            v.val = ev(v.body, v.env); v.done = True
        return v.val
    return v

def ev(node, env):
    t = type(node)
    if t is Num or t is Bool: return node.v
    if t is Text: return interpolate(node.v, env)
    if t is Var:
        return force(env.get(node.name))
    if t is ListLit:
        out = [ev(x, env) for x in node.items]
        if node.rest is not None:
            r = ev(node.rest, env)
            r = force_unwrap(r)
            if not isinstance(r, list): raise TypeError("'..' rest must be a list")
            out = out + r
        return out
    if t is Bin: return eval_bin(node, env)
    if t is OkE:  return Tagged("ok", {"value": ev(node.e, env)})
    if t is FailE:
        err = ev(node.e, env)
        return Tagged("fail", {"error": err})
    if t is TryE:
        v = ev(node.e, env)
        if is_fail(v): raise PrismFailure(v.fields["error"])
        if isinstance(v, Tagged) and v.tag == "ok": return v.fields["value"]
        return v  # lenient: a bare value is implicitly ok
    if t is Ctor:
        return Tagged(node.tag, {k: ev(x, env) for k, x in node.fields.items()})
    if t is Field:
        obj = ev(node.obj, env)
        if isinstance(obj, Tagged) and node.name in obj.fields: return obj.fields[node.name]
        raise TypeError(f"no field '{node.name}'")
    if t is Lambda:
        return Closure(node.params, node.body, env, "lambda")
    if t is Call:
        fn = ev(node.fn, env)
        args = [ev(a, env) for a in node.args]
        return apply_fn(fn, args)
    if t is EffectCall:
        return eval_effect(node, env)
    if t is Match:
        return eval_match(node, env)
    if t is Attempt:
        return eval_attempt(node, env)
    if t is Block:
        return eval_block(node, env, Env(env))
    if t is Seq:
        v = UNIT
        last = len(node.steps) - 1
        for i, st in enumerate(node.steps):
            v = ev(st, env)
            if i < last and is_fail(v):           # a failed step aborts the sequence (time stops)
                raise PrismFailure(v.fields["error"])
        return v
    raise RuntimeError(f"cannot eval {t.__name__}")

def force_unwrap(v):
    v = force(v)
    return v

def eval_bin(node, env):
    l = force_unwrap(ev(node.l, env)); r = force_unwrap(ev(node.r, env))
    op = node.op
    if op == "+":
        if isinstance(l, str) and isinstance(r, str): return l + r       # Text ++ Text
        if isinstance(l, str) or isinstance(r, str):                     # no hidden coercion
            raise TypeError(f"'+' mixes Text and Num: {prism_str(l)} + {prism_str(r)}")
        return l + r
    if op in ("-", "*", "/"):                            # arithmetic: Num only -- no hidden coercion
        if isinstance(l, str) or isinstance(r, str):     # (else `"ab" * 2` would silently repeat the string)
            raise TypeError(f"'{op}' needs Num, got {prism_str(l)} {op} {prism_str(r)}")
        return l - r if op == "-" else l * r if op == "*" else l / r
    if op == "==": return l == r
    if op == "!=": return l != r
    if op in ("<", ">", "<=", ">="):                     # ordering: compare like-with-like, never Text vs Num
        if isinstance(l, str) != isinstance(r, str):
            raise TypeError(f"'{op}' can't compare Text and Num: {prism_str(l)} {op} {prism_str(r)}")
        return l < r if op == "<" else l > r if op == ">" else l <= r if op == "<=" else l >= r
    raise RuntimeError(f"bad op {op}")

def apply_fn(fn, args):
    fn = force(fn)
    if callable(fn) and not isinstance(fn, (Closure,)):   # builtin
        return fn(*args)
    if isinstance(fn, Closure):
        local = Env(fn.env)
        for p, a in zip(fn.params, args):
            local.set(p, a)
        # function boundary: a failure that escapes becomes a `fail` value
        try:
            return ev(fn.body, local)
        except PrismFailure as pf:
            return Tagged("fail", {"error": pf.error})
    raise TypeError(f"not callable: {prism_str(fn)}")

def eval_block(node, env, local):
    val = UNIT
    for kind, *rest in node.stmts:
        if kind == "let":
            name, expr = rest
            local.set(name, ev(expr, local))
            val = UNIT
        else:
            (expr,) = rest
            val = ev(expr, local)
    return val

def eval_effect(node, env):
    if node.op == "show" and node.world == "console":
        arg = ev(node.arg, env) if node.arg is not None else ""
        sys.stdout.write(prism_str(arg) + "\n")
        return UNIT
    if node.op == "read" and node.world == "console":
        line = sys.stdin.readline()
        if line == "": return ""
        return line.rstrip("\n")
    raise RuntimeError(f"unknown effect {node.op}!{node.world}")

def eval_match(node, env):
    v = ev(node.scrut, env)
    for pat, expr in node.arms:
        b = {}
        if match_pat(pat, v, b):
            local = Env(env)
            for k, val in b.items(): local.set(k, val)
            return ev(expr, local)
    raise RuntimeError(f"no match arm for {prism_str(v)}")

def eval_attempt(node, env):
    try:
        return ev(node.body, env)
    except PrismFailure as pf:
        for pat, expr in node.arms:
            b = {}
            if match_pat(pat, pf.error, b):
                local = Env(env)
                for k, val in b.items(): local.set(k, val)
                return ev(expr, local)
        raise  # unhandled failure re-propagates

def match_pat(pat, v, b):
    t = type(pat)
    if t is PWild: return True
    if t is PVar: b[pat.name] = v; return True
    if t is PLit: return v == pat.v
    if t is POk:
        if is_fail(v): return False
        inner = v.fields["value"] if (isinstance(v, Tagged) and v.tag == "ok") else v
        return match_pat(pat.inner, inner, b)
    if t is PFail:
        if not is_fail(v): return False
        return match_pat(pat.inner, v.fields["error"], b)
    if t is PTag:
        if not (isinstance(v, Tagged) and v.tag == pat.tag): return False
        if pat.fields is None: return True
        for fn, fp in pat.fields.items():
            if fn not in v.fields: return False
            if not match_pat(fp, v.fields[fn], b): return False
        return True
    if t is PList:
        if not isinstance(v, list): return False
        if pat.rest is None:
            if len(v) != len(pat.items): return False
            return all(match_pat(p, x, b) for p, x in zip(pat.items, v))
        if len(v) < len(pat.items): return False
        for p, x in zip(pat.items, v):
            if not match_pat(p, x, b): return False
        b[pat.rest] = v[len(pat.items):]
        return True
    return False

# --------------------------------------------------------------------------
# 6. BUILTINS + DRIVER
# --------------------------------------------------------------------------
def builtin_parseNum(t):
    try:
        x = float(t)
        return Tagged("ok", {"value": int(x) if x.is_integer() else x})
    except (ValueError, TypeError):
        return Tagged("fail", {"error": Tagged("BadNumber", {})})

def builtin_words(t):
    # split Text into a list of whitespace-separated words (drops empties). Pure -- a string utility,
    # not I/O. Needed to tokenise a line; same spirit as `floor`/`at`: a small primitive use revealed.
    t = force_unwrap(t)
    if not isinstance(t, str): raise TypeError("words: argument is not Text")
    return t.split()

def builtin_at(xs, i):
    # O(1) random access into a list. Lists stay immutable -- this only READS. Out-of-bounds is a
    # hard error (like sqrt of a negative), not a silent default, so a mis-indexed grid is caught.
    xs = force_unwrap(xs); i = int(force_unwrap(i))
    if not isinstance(xs, list): raise TypeError("at: first argument is not a list")
    if i < 0 or i >= len(xs):
        raise IndexError(f"at: index {i} out of range for a list of length {len(xs)}")
    return xs[i]

def type_tag(v, variant_owner):
    v = force(v)
    if isinstance(v, bool): return "Bool"
    if isinstance(v, (int, float)): return "Num"
    if isinstance(v, str): return "Text"
    if isinstance(v, list): return "List"
    if isinstance(v, Tagged): return variant_owner.get(v.tag, v.tag)
    return "?"

def make_dispatcher(mname, positions, table, variant_owner):
    # A capability method dispatches on the runtime types at its `positions` (the parameters typed
    # by a capability type variable). One position = ordinary single dispatch; several = MULTIPLE
    # DISPATCH (the instance is chosen by the combination of argument types).
    def dispatch(*args):
        key = tuple(type_tag(args[p], variant_owner) if p < len(args) else "?" for p in positions)
        fn = table.get((mname, key))
        if fn is None:
            raise RuntimeError(f"no instance: no `{mname}` for {', '.join(key)}")
        return apply_fn(fn, list(args))
    return dispatch

def build_env(defs):
    # Prism has no loops -- iteration is recursion, and the tree-walker uses the Python
    # stack, so a long simulation recurses deep. Lift the ceiling (well above any real run).
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 40000))
    genv = Env()
    genv.set("parseNum", builtin_parseNum)
    genv.set("sin",  lambda x: math.sin(force_unwrap(x)))
    genv.set("cos",  lambda x: math.cos(force_unwrap(x)))
    genv.set("sqrt", lambda x: math.sqrt(force_unwrap(x)))
    genv.set("abs",  lambda x: abs(force_unwrap(x)))
    genv.set("floor", lambda x: math.floor(force_unwrap(x)))
    genv.set("at",   builtin_at)            # O(1) indexed read (lists are immutable; in-bounds is the caller's contract)
    genv.set("len",  lambda xs: float(len(force_unwrap(xs))))   # O(1) length
    genv.set("words", builtin_words)        # Text -> List[Text], split on whitespace
    genv.set("pi",   math.pi)
    genv.set("slider", lambda d, lo, hi: force_unwrap(d))   # = default; the playground makes it live
    variant_owner = {}
    for d in defs:
        if isinstance(d, TypeDef):
            for v in d.variants: variant_owner[v] = d.name
    # pass 1: capabilities -- for each method find the dispatch positions (params typed by a cap
    # type var) and the type var at each, so single- and multiple-dispatch share one mechanism.
    cap_by_name, method_pos, method_postv = {}, {}, {}
    for d in defs:
        if isinstance(d, Capability):
            cap_by_name[d.name] = d
            tvs = set(d.tvars)
            for m in d.methods:
                params = (m.sig.params if getattr(m, "sig", None) else None) or []
                pos = [i for i, (pn, pt) in enumerate(params)
                       if isinstance(pt, TName) and pt.name in tvs]
                method_pos[m.name] = pos or [0]     # fallback: dispatch on the first argument
                method_postv[m.name] = [params[i][1].name for i in pos]
    method_table = {}
    for d in defs:
        if isinstance(d, FuncDef):
            genv.set(d.name, Closure(d.params, d.body, genv, d.name))
        elif isinstance(d, ValDef):
            genv.set(d.name, Thunk(d.body, genv))   # lazy: order does not matter
        elif isinstance(d, Provides):
            c = cap_by_name.get(d.cap)
            binding = dict(zip(c.tvars, d.types)) if c else {}   # cap type vars := the instance types
            for m in d.methods:
                if m.body is not None:
                    key = tuple(binding.get(tv, "?") for tv in method_postv.get(m.name, []))
                    ps = [p[0] for p in (m.params or [])]
                    method_table[(m.name, key)] = Closure(ps, m.body, genv, m.name)
    for mname, pos in method_pos.items():           # each method dispatches on its receiver type(s)
        genv.set(mname, make_dispatcher(mname, pos, method_table, variant_owner))
    return genv

def expand_includes(defs, seen):
    # replace each `include "path"` with that file's definitions (paths are relative to
    # the current working directory); guard against cycles / double-includes.
    out = []
    for d in defs:
        if isinstance(d, Include):
            real = os.path.abspath(d.path)
            if real in seen: continue
            seen.add(real)
            try:
                with open(real, encoding="utf-8") as f:
                    sub = f.read()
            except OSError as e:
                raise RuntimeError(f"cannot include {d.path!r}: {e}")
            out.extend(expand_includes(Parser(lex(sub)).parse_program(), seen))
        else:
            out.append(d)
    return out

def parse_program_with_includes(src):
    return expand_includes(Parser(lex(src)).parse_program(), set())

def run(src):
    genv = build_env(parse_program_with_includes(src))
    if "main" not in genv.vars:
        raise RuntimeError("no 'main' defined")
    force(genv.get("main"))

def value_of(src, name):
    # evaluate a named top-level value and return its runtime value (for tools that
    # render a program's output, e.g. the playground reading a `picture`).
    genv = build_env(parse_program_with_includes(src))
    if name not in genv.vars:
        raise RuntimeError(f"no '{name}' defined")
    return force(genv.get(name))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python prism.py <file.prism>"); sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        src = f.read()
    try:
        run(src)
    except (SyntaxError, RuntimeError, NameError, TypeError) as e:
        print(f"[prism error] {e}", file=sys.stderr); sys.exit(1)
