"""Статический анализ Python-кода проекта.

Строит таблицу символов (функции, методы, классы, константы модулей), разрешает импорты
и собирает из тел функций факты, которых не видно по графу импортов:

- вызовы и ссылки на функции проекта (в т.ч. функция, переданная аргументом: ``act(apps.approve)``);
- чтение и запись таблиц через ORM-модели (``select(M)``, ``session.get(M)``, ``M(...)``,
  присваивание атрибутов объекта модели, ``update(M)``/``delete(M)``);
- публикация событий ``events.publish(session, "topic", {...})``;
- подписки ``@subscribe("topic")`` и динамическая регистрация ``subscribe(t)(handler)`` в цикле;
- условия процесса ``@bpm.guard("name")`` и переходы ``bpm.transition(..., "dst", actor=...)``;
- слушатели ORM ``@event.listens_for(Target, "event")``;
- зависимости FastAPI ``Depends(...)`` (в т.ч. через ``Annotated``-псевдонимы);
- чтение констант модулей, используемых как настройки, и «магические» числа в ``timedelta(days=N)``;
- проверки, бросающие доменные ошибки (условие + сообщение).

ORM-таблицы берутся из ``Base.metadata`` после импорта моделей.
"""

import ast
import copy
import hashlib
import importlib
import inspect
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tools.knowledge.common import ROOT, rel

SOURCE_DIRS = ("libs", "services", "tests")
PUBLISH = "libs/events/outbox.py::publish"
SUBSCRIBE = "libs/events/registry.py::subscribe"
BPM_GUARD = "libs/bpm/engine.py::guard"
BPM_TRANSITION = "libs/bpm/engine.py::transition"
DB_BASE = "libs/db.py::Base"
ERRORS = {"DomainError", "AccessDenied", "NotFound", "TransitionError"}
WRITE_METHODS = {"append", "extend", "remove", "add", "clear", "pop", "insert"}


@dataclass
class Module:
    name: str
    path: str
    tree: ast.Module
    imports: dict[str, str] = field(default_factory=dict)
    defs: dict[str, Symbol] = field(default_factory=dict)
    aliases: dict[str, ast.expr] = field(default_factory=dict)  # Session = Annotated[..., Depends(x)]
    routers: dict[str, str] = field(default_factory=dict)  # имя APIRouter -> prefix


@dataclass
class Symbol:
    id: str
    module: Module
    qualname: str
    kind: str  # function | class | method | constant | module
    node: ast.AST
    line: int
    end_line: int
    doc: str = ""
    value: Any = None
    cls: Symbol | None = None

    @property
    def path(self) -> str:
        return self.module.path

    @property
    def is_function(self) -> bool:
        return self.kind in ("function", "method", "module")


@dataclass
class Facts:
    calls: list[tuple[str, int]] = field(default_factory=list)
    refs: list[tuple[str, int]] = field(default_factory=list)
    config: list[tuple[str, int]] = field(default_factory=list)
    reads: list[tuple[str, int, str | None]] = field(default_factory=list)  # (orm class id, line, column)
    writes: list[tuple[str, int, str | None]] = field(default_factory=list)
    publishes: list[dict[str, Any]] = field(default_factory=list)
    subscribes: list[dict[str, Any]] = field(default_factory=list)  # регистрации, найденные в этом символе
    transitions: list[dict[str, Any]] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    days_literals: list[tuple[int, int]] = field(default_factory=list)
    depends: list[tuple[str, int]] = field(default_factory=list)
    isinstance_of: list[tuple[str, int]] = field(default_factory=list)
    kwargs_literals: list[tuple[str, str, Any, int]] = field(
        default_factory=list
    )  # (callee, kw, value, line)


@dataclass
class Decoration:
    subscribe: list[str] = field(default_factory=list)
    guard: str | None = None
    listens_for: tuple[str, str] | None = None
    route: tuple[str, str] | None = None  # (METHOD, path)


def _first_doc(node: ast.AST) -> str:
    try:
        doc = ast.get_docstring(node)  # type: ignore[arg-type]
    except TypeError:
        return ""
    return doc.strip().splitlines()[0] if doc else ""


def _comment_above(lines: list[str], lineno: int) -> str:
    out: list[str] = []
    i = lineno - 2
    while i >= 0 and lines[i].lstrip().startswith("#"):
        out.insert(0, lines[i].lstrip()[1:].strip())
        i -= 1
    return " ".join(out)


def _strip_docstrings(node: ast.AST) -> ast.AST:
    node = copy.deepcopy(node)
    for n in ast.walk(node):
        body = getattr(n, "body", None)
        if (
            isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module))
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            n.body = body[1:] or [ast.Pass()]
    return node


def normalized_hash(node: ast.AST) -> str:
    """Хэш нормализованного AST: не зависит от форматирования, комментариев и docstring."""
    dump = ast.dump(_strip_docstrings(node), annotate_fields=True, include_attributes=False)
    return hashlib.sha256(dump.encode()).hexdigest()[:12]


def _is_upper(name: str) -> bool:
    return name.isupper() and not name.startswith("__")


class Project:
    def __init__(self, root: Path = ROOT, dirs: tuple[str, ...] = SOURCE_DIRS) -> None:
        self.root = root
        self.modules: dict[str, Module] = {}
        self.symbols: dict[str, Symbol] = {}
        self.source_lines: dict[str, list[str]] = {}
        for d in dirs:
            for path in sorted((root / d).rglob("*.py")):
                self._load(path)
        for m in self.modules.values():
            self._collect_module_level(m)
        self.orm: dict[str, dict[str, Any]] = {}  # class symbol id -> {table, columns, relationships}
        self.facts: dict[str, Facts] = {}
        self.decorations: dict[str, Decoration] = {}

    # ------------------------------------------------------------------ загрузка

    def _load(self, path: Path) -> None:
        relpath = path.resolve().relative_to(self.root.resolve()).as_posix()
        parts = list(Path(relpath).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        name = ".".join(parts)
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=relpath)
        m = Module(name=name, path=relpath, tree=tree)
        self.modules[name] = m
        lines = text.splitlines()
        self.source_lines[relpath] = lines
        for stmt in tree.body:
            if isinstance(stmt, ast.Import):
                for a in stmt.names:
                    if a.asname:
                        m.imports[a.asname] = a.name
                    else:
                        m.imports[a.name.split(".")[0]] = a.name.split(".")[0]
            elif isinstance(stmt, ast.ImportFrom):
                base = stmt.module or ""
                if stmt.level:
                    pkg = (
                        name.split(".")[: -stmt.level] if not path.name == "__init__.py" else name.split(".")
                    )
                    base = ".".join([*pkg, base] if base else pkg)
                for a in stmt.names:
                    m.imports[a.asname or a.name] = f"{base}.{a.name}"
            elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._add(m, stmt.name, "function", stmt, doc=_first_doc(stmt))
            elif isinstance(stmt, ast.ClassDef):
                cls = self._add(m, stmt.name, "class", stmt, doc=_first_doc(stmt))
                for sub in stmt.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        s = self._add(m, f"{stmt.name}.{sub.name}", "method", sub, doc=_first_doc(sub))
                        s.cls = cls
            elif isinstance(stmt, (ast.Assign, ast.AnnAssign)):
                targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
                for t in targets:
                    if isinstance(t, ast.Name) and _is_upper(t.id) and stmt.value is not None:
                        try:
                            value = ast.literal_eval(stmt.value)
                        except ValueError, SyntaxError, TypeError:
                            value = None
                        s = self._add(m, t.id, "constant", stmt, doc=_comment_above(lines, stmt.lineno))
                        s.value = value
        if self._module_has_code(tree):
            self._add(m, "<module>", "module", tree, doc=_first_doc(tree), line=1, end_line=len(lines))

    @staticmethod
    def _module_has_code(tree: ast.Module) -> bool:
        return any(isinstance(s, (ast.For, ast.Expr)) and not _is_docstring(s) for s in tree.body)

    def _add(self, m: Module, qualname: str, kind: str, node: ast.AST, *, doc: str = "", **kw: Any) -> Symbol:
        line = kw.get("line") or node.lineno  # type: ignore[attr-defined]
        end = kw.get("end_line") or node.end_lineno  # type: ignore[attr-defined]
        s = Symbol(f"{m.path}::{qualname}", m, qualname, kind, node, line, end, doc)
        self.symbols[s.id] = s
        if "." not in qualname:
            m.defs[qualname] = s
        return s

    def _collect_module_level(self, m: Module) -> None:
        for stmt in m.tree.body:
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
            ):
                name, value = stmt.targets[0].id, stmt.value
                if isinstance(value, ast.Subscript) and self.dotted(m, value.value).endswith("Annotated"):
                    m.aliases[name] = value
                if isinstance(value, ast.Call) and self.dotted(m, value.func).endswith("APIRouter"):
                    prefix = next(
                        (
                            k.value.value
                            for k in value.keywords
                            if k.arg == "prefix" and isinstance(k.value, ast.Constant)
                        ),
                        "",
                    )
                    m.routers[name] = prefix

    # ------------------------------------------------------------------ разрешение имён

    def dotted(self, m: Module, expr: ast.AST) -> str:
        """Полное имя выражения через импорты: ``event.listens_for`` -> ``sqlalchemy.event.listens_for``."""
        if isinstance(expr, ast.Name):
            return m.imports.get(expr.id, f"{m.name}.{expr.id}" if expr.id in m.defs else expr.id)
        if isinstance(expr, ast.Attribute):
            return f"{self.dotted(m, expr.value)}.{expr.attr}"
        return ""

    def resolve_dotted(self, dotted: str, depth: int = 0) -> Symbol | Module | None:
        if depth > 8 or not dotted:
            return None
        if dotted in self.modules:
            return self.modules[dotted]
        if "." not in dotted:
            return None
        mod, attr = dotted.rsplit(".", 1)
        base = self.resolve_dotted(mod, depth + 1)
        if isinstance(base, Module):
            if attr in base.defs:
                return base.defs[attr]
            if attr in base.imports:
                return self.resolve_dotted(base.imports[attr], depth + 1)
            return self.modules.get(f"{base.name}.{attr}")
        if isinstance(base, Symbol) and base.kind == "class":
            return self.symbols.get(f"{base.id}.{attr}")
        return None

    def resolve(self, m: Module, expr: ast.AST) -> Symbol | Module | None:
        if isinstance(expr, ast.Name):
            if expr.id in m.defs:
                return m.defs[expr.id]
            if expr.id in m.imports:
                return self.resolve_dotted(m.imports[expr.id])
            return None
        if isinstance(expr, ast.Attribute):
            base = self.resolve(m, expr.value)
            if isinstance(base, Module):
                if expr.attr in base.defs:
                    return base.defs[expr.attr]
                if expr.attr in base.imports:
                    return self.resolve_dotted(base.imports[expr.attr])
                return self.modules.get(f"{base.name}.{expr.attr}")
            if isinstance(base, Symbol) and base.kind == "class":
                return self.symbols.get(f"{base.id}.{expr.attr}")
        return None

    def resolve_symbol(self, m: Module, expr: ast.AST) -> Symbol | None:
        r = self.resolve(m, expr)
        return r if isinstance(r, Symbol) else None

    # ------------------------------------------------------------------ ORM

    def load_orm(self) -> None:
        """Импортирует модели и читает Base.metadata: класс -> таблица, колонки, связи."""
        if str(self.root) not in sys.path:
            sys.path.append(str(self.root))
        for name in self.modules:
            if name.endswith(".models") or name == "libs.events.outbox":
                importlib.import_module(name)
        from libs import db

        for mapper in db.Base.registry.mappers:
            cls = mapper.class_
            path = rel(inspect.getsourcefile(cls))
            sid = f"{path}::{cls.__qualname__}"
            table = mapper.local_table
            rels = {
                r.key: f"{rel(inspect.getsourcefile(r.mapper.class_))}::{r.mapper.class_.__qualname__}"
                for r in mapper.relationships
            }
            self.orm[sid] = {
                "table": table.fullname,
                "columns": {
                    c.name: {"type": str(c.type), "nullable": bool(c.nullable), "pk": bool(c.primary_key)}
                    for c in table.columns
                },
                "foreign_keys": sorted(
                    f"{fk.parent.name}->{fk.target_fullname}" for fk in table.foreign_keys
                ),
                "relationships": rels,
            }

    def orm_table(self, sym: Symbol | None) -> str | None:
        return self.orm[sym.id]["table"] if sym is not None and sym.id in self.orm else None

    # ------------------------------------------------------------------ анализ тел

    def analyze(self, orm: bool = True) -> None:
        if orm and not self.orm:
            self.load_orm()
        for s in list(self.symbols.values()):
            if s.kind in ("function", "method"):
                self.decorations[s.id] = self._decorations(s)
                self.facts[s.id] = _BodyVisitor(self, s).run()
            elif s.kind == "module":
                self.facts[s.id] = _BodyVisitor(self, s).run()
            elif s.kind == "class":
                self.decorations[s.id] = Decoration()

    def _decorations(self, s: Symbol) -> Decoration:
        d = Decoration()
        node = s.node
        assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            target = self.resolve_symbol(s.module, dec.func)
            args = [a.value for a in dec.args if isinstance(a, ast.Constant)]
            if target is not None and target.id == SUBSCRIBE and args:
                d.subscribe.append(args[0])
            elif target is not None and target.id == BPM_GUARD and args:
                d.guard = args[0]
            elif self.dotted(s.module, dec.func).endswith("event.listens_for") and len(dec.args) >= 2:
                d.listens_for = (
                    ast.unparse(dec.args[0]),
                    str(args[-1]) if args else ast.unparse(dec.args[1]),
                )
            elif (
                isinstance(dec.func, ast.Attribute)
                and isinstance(dec.func.value, ast.Name)
                and dec.func.value.id in s.module.routers
                and dec.func.attr in ("get", "post", "put", "patch", "delete")
            ):
                prefix = s.module.routers[dec.func.value.id]
                d.route = (dec.func.attr.upper(), prefix + (args[0] if args else ""))
        return d

    def returns_orm(self, fn: Symbol) -> str | None:
        node = fn.node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.returns is None:
            return None
        return self.annotation_orm(fn.module, node.returns)

    def annotation_orm(self, m: Module, ann: ast.AST) -> str | None:
        if isinstance(ann, ast.BinOp):
            return self.annotation_orm(m, ann.left) or self.annotation_orm(m, ann.right)
        if isinstance(ann, ast.Subscript):
            return self.annotation_orm(m, ann.slice)
        if isinstance(ann, ast.Constant) and isinstance(ann.value, str):
            try:
                return self.annotation_orm(m, ast.parse(ann.value, mode="eval").body)
            except SyntaxError:
                return None
        sym = self.resolve_symbol(m, ann)
        return sym.id if sym is not None and sym.id in self.orm else None

    # ------------------------------------------------------------------ хэши

    def own_hash(self, s: Symbol) -> str:
        return normalized_hash(s.node)

    def reachable(self, sid: str) -> set[str]:
        """Функции и настройки проекта, достижимые по вызовам и ссылкам (без тестов)."""
        seen: set[str] = set()
        stack = [sid]
        while stack:
            cur = stack.pop()
            f = self.facts.get(cur)
            if f is None:
                continue
            for target, _ in [*f.calls, *f.refs, *f.config, *f.depends]:
                if target in seen or target == sid or target.startswith("tests/"):
                    continue
                if target in self.symbols and self.symbols[target].kind in ("function", "method", "constant"):
                    seen.add(target)
                    stack.append(target)
        return seen

    def transitive_hash(self, sid: str) -> str:
        parts = [self.own_hash(self.symbols[sid])]
        parts += [f"{t}={self.own_hash(self.symbols[t])}" for t in sorted(self.reachable(sid))]
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:12]


def _is_docstring(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


class _BodyVisitor(ast.NodeVisitor):
    """Собирает факты из тела одной функции (или из кода модуля верхнего уровня)."""

    def __init__(self, project: Project, sym: Symbol) -> None:
        self.p = project
        self.s = sym
        self.m = sym.module
        self.f = Facts()
        self.types: dict[str, str] = {}  # переменная -> ORM-класс
        self.conds: list[str] = []
        self.loops: list[ast.For] = []
        self.write_ctx: set[int] = set()

    def run(self) -> Facts:
        node = self.s.node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for a in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]:
                if a.annotation is not None:
                    if cls := self.p.annotation_orm(self.m, a.annotation):
                        self.types[a.arg] = cls
                    self._depends_in_annotation(a.annotation, a.lineno)
            for default in [*node.args.defaults, *node.args.kw_defaults]:
                if default is not None:
                    self._depends_call(default)
            for stmt in node.body:
                self.visit(stmt)
        else:  # код модуля верхнего уровня
            for stmt in node.body:  # type: ignore[attr-defined]
                if isinstance(stmt, (ast.For, ast.Expr)) and not _is_docstring(stmt):
                    self.visit(stmt)
        return self.f

    # FastAPI Depends ---------------------------------------------------------

    def _depends_call(self, expr: ast.AST) -> None:
        if isinstance(expr, ast.Call) and self.p.dotted(self.m, expr.func).endswith("Depends") and expr.args:
            target = self.p.resolve_symbol(self.m, expr.args[0])
            if target is not None:
                self.f.depends.append((target.id, expr.lineno))

    def _depends_in_annotation(self, ann: ast.AST, line: int) -> None:
        if isinstance(ann, ast.Name) and ann.id in self.m.aliases:
            ann = self.m.aliases[ann.id]
        if isinstance(ann, ast.Subscript) and self.p.dotted(self.m, ann.value).endswith("Annotated"):
            elts = ann.slice.elts if isinstance(ann.slice, ast.Tuple) else [ann.slice]
            for e in elts:
                self._depends_call(e)

    # типы переменных -----------------------------------------------------------

    def _infer(self, expr: ast.AST | None) -> str | None:
        if expr is None:
            return None
        if isinstance(expr, ast.Await):
            return self._infer(expr.value)
        if isinstance(expr, ast.Name):
            return self.types.get(expr.id)
        if isinstance(expr, ast.Subscript):
            return self._infer(expr.value)
        if isinstance(expr, ast.Attribute):
            owner = self._infer(expr.value)
            if owner and (target := self.p.orm[owner]["relationships"].get(expr.attr)):
                return target
            return None
        if isinstance(expr, ast.Call):
            func = expr.func
            target = self.p.resolve_symbol(self.m, func)
            if target is not None:
                if target.id in self.p.orm:
                    return target.id
                if target.kind in ("function", "method"):
                    return self.p.returns_orm(target)
            if isinstance(func, ast.Attribute):
                if func.attr in ("all", "first", "one", "scalar_one", "one_or_none", "unique"):
                    return self._infer(func.value)
                if func.attr in ("get", "merge") and expr.args:
                    first = expr.args[0]
                    cls = self.p.resolve_symbol(self.m, first)
                    if cls is not None and cls.id in self.p.orm:
                        return cls.id
                    return self._infer(first)
                if func.attr in ("scalar", "scalars", "execute") and expr.args:
                    return self._select_entity(expr.args[0])
            if isinstance(func, ast.Name) and func.id in ("list", "sorted", "tuple") and expr.args:
                return self._infer(expr.args[0])
        return None

    def _select_entity(self, expr: ast.AST) -> str | None:
        while isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute):
            expr = expr.func.value  # select(M).where(...).order_by(...)
        if isinstance(expr, ast.Call) and self.p.dotted(self.m, expr.func).endswith("select") and expr.args:
            cls = self.p.resolve_symbol(self.m, expr.args[0])
            if cls is not None and cls.id in self.p.orm:
                return cls.id
        return None

    def _bind(self, target: ast.AST, cls: str | None) -> None:
        if isinstance(target, ast.Name):
            if cls:
                self.types[target.id] = cls
            else:
                self.types.pop(target.id, None)

    # посетители ------------------------------------------------------------------

    def visit_Assign(self, node: ast.Assign) -> None:
        cls = self._infer(node.value)
        for t in node.targets:
            self._write_target(t)
            self._bind(t, cls)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._write_target(node.target)
        self._bind(node.target, self._infer(node.value) or self.p.annotation_orm(self.m, node.annotation))
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._write_target(node.target)
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self._bind(node.target, self._infer(node.value))
        self.generic_visit(node)

    def _write_target(self, t: ast.AST) -> None:
        if isinstance(t, ast.Attribute):
            owner = self._infer(t.value)
            if owner:
                self.f.writes.append((owner, t.lineno, t.attr))

    def _visit_loop(self, node: ast.For | ast.AsyncFor) -> None:
        self._bind(node.target, self._infer(node.iter))
        self.loops.append(node)  # type: ignore[arg-type]
        self.generic_visit(node)
        self.loops.pop()

    visit_For = _visit_loop
    visit_AsyncFor = _visit_loop

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)
        narrowed = self._isinstance_narrowing(node.test)
        saved = dict(self.types)
        self.types.update(narrowed)
        self.conds.append(ast.unparse(node.test))
        for stmt in node.body:
            self.visit(stmt)
        self.conds.pop()
        self.types = saved
        if node.orelse:
            self.conds.append(f"not ({ast.unparse(node.test)})")
            for stmt in node.orelse:
                self.visit(stmt)
            self.conds.pop()

    def _isinstance_narrowing(self, test: ast.AST) -> dict[str, str]:
        if (
            isinstance(test, ast.Call)
            and isinstance(test.func, ast.Name)
            and test.func.id == "isinstance"
            and len(test.args) == 2
            and isinstance(test.args[0], ast.Name)
        ):
            cls = self.p.resolve_symbol(self.m, test.args[1])
            if cls is not None and cls.id in self.p.orm:
                self.f.isinstance_of.append((cls.id, test.lineno))
                return {test.args[0].id: cls.id}
        return {}

    def visit_Raise(self, node: ast.Raise) -> None:
        exc = node.exc
        if isinstance(exc, ast.Call):
            name = self.p.dotted(self.m, exc.func).rsplit(".", 1)[-1]
            if name in ERRORS:
                msg = ""
                if exc.args:
                    a = exc.args[0]
                    msg = a.value if isinstance(a, ast.Constant) else ast.unparse(a)
                self.f.checks.append(
                    {
                        "line": node.lineno,
                        "error": name,
                        "message": str(msg),
                        "condition": " and ".join(self.conds),
                    }
                )
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        self._reference(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if self._reference(node):
            return
        self.generic_visit(node)

    def _reference(self, node: ast.Name | ast.Attribute) -> bool:
        """Ссылка на символ проекта не в позиции вызова: настройка, ORM-модель или функция-аргумент."""
        if id(node) in self.write_ctx:
            return True
        target = self.p.resolve(self.m, node)
        if not isinstance(target, Symbol):
            return False
        line = node.lineno
        if target.kind == "constant":
            if not target.path.startswith("tests/"):
                self.f.config.append((target.id, line))
        elif target.id in self.p.orm:
            self.f.reads.append((target.id, line, None))
        elif target.kind == "method" and target.cls is not None and target.cls.id in self.p.orm:
            self.f.reads.append((target.cls.id, line, None))
        elif target.kind in ("function", "method"):
            self.f.refs.append((target.id, line))
        elif target.kind == "class":
            self.f.refs.append((target.id, line))
        return True

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        target = self.p.resolve_symbol(self.m, func)
        line = node.lineno
        if target is not None:
            self.write_ctx.add(id(func))
            if target.id in self.p.orm:
                self.f.writes.append((target.id, line, None))
            else:
                self.f.calls.append((target.id, line))
            if target.id == PUBLISH:
                self._publish(node)
            elif target.id == BPM_TRANSITION:
                self._transition(node)
            for kw in node.keywords:
                if kw.arg and isinstance(kw.value, ast.Constant):
                    self.f.kwargs_literals.append((target.id, kw.arg, kw.value.value, line))
        else:
            dotted = self.p.dotted(self.m, func)
            if (
                dotted.split(".")[-1] in ("update", "delete")
                and dotted.startswith("sqlalchemy")
                and node.args
            ):
                cls = self.p.resolve_symbol(self.m, node.args[0])
                if cls is not None and cls.id in self.p.orm:
                    self.write_ctx.add(id(node.args[0]))
                    self.f.writes.append((cls.id, line, None))
            elif dotted.endswith("timedelta"):
                for kw in node.keywords:
                    if (
                        kw.arg == "days"
                        and isinstance(kw.value, ast.Constant)
                        and isinstance(kw.value.value, int)
                    ):
                        self.f.days_literals.append((kw.value.value, line))
            elif isinstance(func, ast.Attribute) and func.attr in WRITE_METHODS:
                owner = self._infer(func.value)
                if owner and isinstance(func.value, ast.Attribute):
                    self.f.writes.append((owner, line, None))
            elif isinstance(func, ast.Call):
                inner = self.p.resolve_symbol(self.m, func.func)
                if inner is not None and inner.id == SUBSCRIBE:
                    self._dynamic_subscribe(func, node)
        self.generic_visit(node)

    def _publish(self, node: ast.Call) -> None:
        args = node.args
        topic_expr = (
            args[1] if len(args) > 1 else next((k.value for k in node.keywords if k.arg == "topic"), None)
        )
        payload = (
            args[2] if len(args) > 2 else next((k.value for k in node.keywords if k.arg == "payload"), None)
        )
        topic = topic_expr.value if isinstance(topic_expr, ast.Constant) else None
        keys = (
            [k.value for k in payload.keys if isinstance(k, ast.Constant)]
            if isinstance(payload, ast.Dict)
            else []
        )
        self.f.publishes.append(
            {
                "topic": topic,
                "expr": ast.unparse(topic_expr) if topic_expr is not None and topic is None else None,
                "line": node.lineno,
                "payload": keys,
                "condition": " and ".join(self.conds),
            }
        )

    def _transition(self, node: ast.Call) -> None:
        args = node.args
        dst_expr = (
            args[2] if len(args) > 2 else next((k.value for k in node.keywords if k.arg == "dst"), None)
        )
        actor_expr = (
            args[3] if len(args) > 3 else next((k.value for k in node.keywords if k.arg == "actor"), None)
        )
        if isinstance(dst_expr, ast.Constant):
            targets: list[str | None] = [dst_expr.value]
        elif isinstance(dst_expr, ast.Name):
            targets = self._assigned_strings(dst_expr.id) or [None]
        else:
            targets = [None]
        for dst in targets:
            self.f.transitions.append(
                {
                    "to": dst,
                    "to_expr": ast.unparse(dst_expr) if dst_expr is not None else None,
                    "actor": actor_expr.value if isinstance(actor_expr, ast.Constant) else None,
                    "line": node.lineno,
                    "condition": " and ".join(self.conds),
                }
            )

    def _assigned_strings(self, name: str) -> list[str]:
        """Строковые значения, которые функция присваивает переменной (``dst = "a" if x else "b"``)."""
        values: list[str] = []
        for n in ast.walk(self.s.node):
            if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets):
                for c in ast.walk(n.value):
                    if isinstance(c, ast.Constant) and isinstance(c.value, str) and c.value not in values:
                        values.append(c.value)
        return values

    def _dynamic_subscribe(self, sub_call: ast.Call, node: ast.Call) -> None:
        """``subscribe(topic)(handler)`` в цикле по константе-словарю: темы берутся из ключей константы."""
        topics: list[str] = []
        topic_values: dict[str, Any] = {}
        arg = sub_call.args[0] if sub_call.args else None
        if isinstance(arg, ast.Constant):
            topics = [arg.value]
        elif isinstance(arg, ast.Name):
            for loop in reversed(self.loops):
                names = [n.id for n in ast.walk(loop.target) if isinstance(n, ast.Name)]
                if arg.id not in names:
                    continue
                it = loop.iter
                if isinstance(it, ast.Call) and isinstance(it.func, ast.Attribute):
                    it = it.func.value
                const = self.p.resolve_symbol(self.m, it)
                if (
                    const is not None
                    and const.kind == "constant"
                    and isinstance(const.value, (dict, list, tuple))
                ):
                    topics = list(const.value)
                    if isinstance(const.value, dict):
                        topic_values = dict(const.value)
                    self.f.config.append((const.id, loop.lineno))
                break
        handler_expr = node.args[0] if node.args else None
        handler = None
        if isinstance(handler_expr, ast.Call):
            handler = self.p.resolve_symbol(self.m, handler_expr.func)
        elif handler_expr is not None:
            handler = self.p.resolve_symbol(self.m, handler_expr)
        for t in topics:
            self.f.subscribes.append(
                {
                    "topic": t,
                    "handler": handler.id if handler else None,
                    "line": node.lineno,
                    "dynamic": True,
                    "template": topic_values.get(t),
                }
            )
