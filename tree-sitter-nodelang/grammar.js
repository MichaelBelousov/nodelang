const ident_regex = /[a-zA-Z_][a-zA-Z0-9_]*/;

module.exports = grammar({
  name: "nodelang",
  rules: {
    // NOTE: the first rule is the one is the top-level one!
    source_file: ($) => repeat(choice($._stmt, $.rule)),
    body: ($) => repeat1(choice($._stmt, $.rule)),
    identifier: ($) => ident_regex,
    // FIXME: probably need to allow escaping spaces or quoting or something
    path: ($) => /[^\s]+/,
    _stmt: ($) =>
      choice(
        $.assign,
        $.append_assign,
        $.expanding_assign,
        $.diagnostic,
        $.directive,
        $.if
      ),

    word: ($) => $.identifier,

    // note this is overloaded with `appendMacroSeparator` special command
    assign: ($) =>
      // NOTE: will have to manually evaluate `$()` in rest_of_line
      seq(
        field("identifier", $.identifier),
        "=",
        field("value", $.rest_of_line)
      ),
    append_assign: ($) =>
      seq(
        field("identifier", $.identifier),
        "+",
        field("value", $.rest_of_line)
      ),

    comment: ($) => token(/#.*/),

    else_clause: ($) => seq("%else", $.body),
    elif_cond: ($) => $.rest_of_line,
    elif_clause: ($) => seq("%elif", $.elif_cond, $.body),

    if_cond: ($) => $._expr,
    ifdef_cond: ($) => $.identifier,
    iffile_cond: ($) => $.rest_of_line,
    if: ($) =>
      choice(
        seq(
          field(
            "cond",
            choice(
              seq("%if", $.if_cond),
              seq("%ifdef", $.ifdef_cond),
              seq("%ifndef", $.ifdef_cond),
              seq("%iffile", $.iffile_cond),
              seq("%ifnofile", $.iffile_cond)
            )
          ),
          "\n",
          $.body,
          repeat($.elif_clause),
          optional($.else_clause),
          "%endif"
        )
      ),

    // TODO: definitely needs to have escapable slashes
    string: ($) => /"[^"]*"/,

    // unary
    not: ($) => prec(1000, seq("!", $._expr)),
    is_defined: ($) => prec(1000, seq("defined", "(", $.identifier, ")")),

    // binary
    eq: ($) => prec.left(2, seq($._expr, "==", $._expr)),
    or: ($) => prec.left(3, seq($._expr, "||", $._expr)),
    and: ($) => prec.left(4, seq($._expr, "&&", $._expr)),

    _expr: ($) =>
      choice(
        $.not,
        $.is_defined,
        $.eq,
        $.or,
        $.and,
        $.string,
        $.expand,
        $.identifier
      ),
  },
  // prettier-ignore
  extras: ($) => [
    $.comment,
    /\s/, // whitespace
  ],
});
