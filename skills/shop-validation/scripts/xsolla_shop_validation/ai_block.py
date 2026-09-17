"""The nine static-analysis rules for a custom (AI) block's React source.

Every one is a runtime or compile failure, not a style preference -- and two of
them crash the editor's settings sidebar, which is worse than a broken block
because the user cannot get back in to fix it.

These are textual pattern checks and are best-effort by construction.  A
violation written across several lines, generated dynamically, or hidden behind
a helper will pass.  A clean run means "no matched pattern", not "correct".
"""

from __future__ import annotations

import re

from .errors import violation

BLOCK_UTILS = r"['\"]@site-builder/block-utils['\"]"

# Injected into scope automatically.  Importing one declares the symbol twice
# and the block fails to compile.
FORBIDDEN_GLOBALS = (
    "useControls",
    "text",
    "color",
    "toggle",
    "number",
    "select",
    "localizedText",
    "AutoControls",
)

CONTROL_FACTORIES = ("color", "toggle", "number", "select", "text")


def _forbidden_import(symbol):
    return re.compile(
        r"import\s*\{[^}]*\b%s\b[^}]*\}\s*from\s*%s" % (re.escape(symbol), BLOCK_UTILS)
    )


TEXT_EDITOR_USAGE = re.compile(r"\bTextEditor\b")
TEXT_EDITOR_IMPORT = re.compile(r"import\s*\{[^}]*\bTextEditor\b[^}]*\}\s*from\s*" + BLOCK_UTILS)
TEXT_EDITOR_JSX = re.compile(r"<TextEditor\b")
# Either form of taking the global as a prop: a named function's destructured
# parameter, or an arrow component's.
LOCALIZED_TEXT_PROP = re.compile(
    r"function\s+\w+\s*\(\s*\{[^)]*\blocalizedText\b"
    r"|\(\s*\{[^)]*\blocalizedText\b[^)]*\}\s*\)\s*=>"
)
EXPORT_DEFAULT_CLASS = re.compile(r"export\s+default\s+class")
LOCALIZED_TEXT_CALLS = re.compile(r"localizedText\(\s*['\"](\w+)['\"]\s*\)")
USE_CONTROLS_OBJECT = re.compile(r"useControls\s*\(\s*\{")
CONTROL_FACTORY_OBJECT = re.compile(
    r"\b(?:%s)\s*\(\s*\{" % "|".join(CONTROL_FACTORIES)
)
TEXT_CONTROL_WITH_LOCALIZED = re.compile(
    r"\btext\s*\(\s*['\"][^'\"]*['\"]\s*,\s*localizedText\s*\("
)


def collect_violations(component_code, settings_code=None, text_fields=None):
    """Run all nine rules.  Returns a list of ``{rule, message, suggestion}``.

    Rules 1 and 4 scan the component and settings source joined; rule 2 looks
    for *usage* in either and the *import* in the joined text; the rest scan the
    component source only.  Getting that wrong makes a rule look broken.
    """
    component_code = component_code or ""
    all_code = "\n\n".join(c for c in (component_code, settings_code) if c)
    out = []

    # 1 - forbidden-import
    for symbol in FORBIDDEN_GLOBALS:
        if _forbidden_import(symbol).search(all_code):
            out.append(
                violation(
                    "forbidden-import",
                    '"%s" is a runtime global -- importing it declares the symbol twice and '
                    'the block fails to compile with "symbol already declared".' % symbol,
                    'Remove "%s" from the import list and call it directly, unimported. '
                    "If the braces are left empty, delete the whole import statement." % symbol,
                )
            )

    # 2 - missing-texteditor-import
    uses_text_editor = bool(
        TEXT_EDITOR_USAGE.search(component_code)
        or (settings_code and TEXT_EDITOR_USAGE.search(settings_code))
    )
    if uses_text_editor and not TEXT_EDITOR_IMPORT.search(all_code):
        out.append(
            violation(
                "missing-texteditor-import",
                "TextEditor is used but not imported. Unlike the injected globals it is a real "
                "import, so this throws a ReferenceError at runtime and the block renders nothing.",
                "Add: import { TextEditor } from '@site-builder/block-utils';",
            )
        )

    # 3 - localized-text-prop-shadow
    if LOCALIZED_TEXT_PROP.search(component_code):
        out.append(
            violation(
                "localized-text-prop-shadow",
                "localizedText is destructured from the component's props. The prop shadows the "
                'injected global and arrives undefined, so the first call fails with '
                '"localizedText is not a function".',
                "Take no props at all -- export default function MyBlock() { ... } -- and call "
                "localizedText('key') directly.",
            )
        )

    # 4 - export-default-class
    if EXPORT_DEFAULT_CLASS.search(all_code):
        out.append(
            violation(
                "export-default-class",
                "export default class is not supported by the transform pipeline that compiles "
                "block source.",
                "Use export default function MyBlock() { ... } or export default () => { ... }.",
            )
        )

    # 5 - undeclared-text-fields
    called = []
    for match in LOCALIZED_TEXT_CALLS.finditer(component_code):
        if match.group(1) not in called:
            called.append(match.group(1))
    declared = set()
    for field in text_fields or []:
        if isinstance(field, dict) and isinstance(field.get("name"), str):
            declared.add(field["name"])
    missing = [name for name in called if name not in declared]
    if missing:
        out.append(
            violation(
                "undeclared-text-fields",
                "localizedText() is called with names that are not declared in textFields: %s. "
                "The field is silently missing -- nothing appears on the canvas and nothing is "
                "editable, with no error to explain it."
                % ", ".join('"%s"' % name for name in missing),
                "Add to textFields: %s"
                % ", ".join('{ name: "%s", default: "..." }' % name for name in missing),
            )
        )

    # 6 - missing-text-fields
    if TEXT_EDITOR_JSX.search(component_code) and not (text_fields or []):
        out.append(
            violation(
                "missing-text-fields",
                "<TextEditor> is rendered but no textFields are declared. The editor mounts with "
                "no bound fields, so the block looks finished and nothing on it is editable.",
                'Declare textFields: [{ name: "...", default: "..." }], one entry per TextEditor '
                "field.",
            )
        )

    # 7 - use-controls-object-arg
    if USE_CONTROLS_OBJECT.search(component_code):
        out.append(
            violation(
                "use-controls-object-arg",
                "useControls() was called with an object literal. Only one control per call is "
                "supported; passing an object returns undefined, so the destructuring or "
                "assignment that follows throws at runtime.",
                "One call per field: const label = useControls(text('Label', 'default')). For "
                "canvas-editable text use <TextEditor id={localizedText('key')} /> instead.",
            )
        )

    # 8 - control-factory-object-arg
    if CONTROL_FACTORY_OBJECT.search(component_code):
        out.append(
            violation(
                "control-factory-object-arg",
                "A control factory (color/toggle/number/select/text) was called with an object "
                "literal in the first position. The first argument is the control's NAME, so the "
                "object is stored as the name; the settings panel then renders a raw object as a "
                "React child and the whole sidebar crashes, leaving the user unable to open "
                "settings to undo it.",
                "Use positional string-first arguments: color('My Colour', '#ff0000'), "
                "toggle('Show badge', true), number('Count', 0, { min: 0, max: 10 }), "
                "select('Size', ['sm','lg'], 'sm'), text('Label', 'default'). number()'s options "
                "object is the third argument and is legitimate there.",
            )
        )

    # 9 - text-control-with-localized-text
    if TEXT_CONTROL_WITH_LOCALIZED.search(component_code):
        out.append(
            violation(
                "text-control-with-localized-text",
                "text() is used with localizedText() as its value. text() produces a sidebar-only "
                "string control and does not bind to a canvas-editable text field, so the value "
                "edited on the canvas and the value the control writes are not the same thing.",
                "Render canvas text directly: <TextEditor id={localizedText('title')} />. Keep "
                "text() for plain sidebar strings with a plain string default.",
            )
        )

    return out


def check_text_refs(component_code, text_refs):
    """The one signal only a fetched block carries.

    If the source registers canvas text -- ``localizedText(`` or ``<TextEditor``
    -- then ``textRefs`` must not be empty.  An empty map means the text was
    never registered and nothing on the block is editable.  A block created
    through the CLI comes back this way, because the CLI cannot declare text
    fields at all.
    """
    component_code = component_code or ""
    registers_text = bool(
        LOCALIZED_TEXT_CALLS.search(component_code) or TEXT_EDITOR_JSX.search(component_code)
    )
    if not registers_text:
        return []
    if text_refs:
        return []
    return [
        violation(
            "empty-text-refs",
            "The source registers canvas text (localizedText( or <TextEditor) but the block's "
            "textRefs is empty, so nothing on the block is editable. This is the "
            "missing-text-fields fault visible after the fact -- a block created through the CLI "
            "always lands this way, because the CLI has no text-fields flag.",
            "Recreate the block through tooling that accepts textFields, or drop the "
            "canvas-editable text from the source.",
        )
    ]
