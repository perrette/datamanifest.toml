# Resolution: the fetch and load ladders

At runtime each tool collapses the bindings to one effective **fetcher** (the function
that obtains the dataset's bytes) and **loader** (the function that opens them into
memory) per dataset, trying rungs in order.

**Fetch ladder:** own-language fetcher (explicit `_LANG.<self>` > bare `fetcher`) → `shell`
command → cross-language fetch (rung 3) → `uri` download → error.

**Load ladder:** own-language loader (explicit > bare) → manifest format default
(`_LANG.<self>.loaders` > `_LOADERS`) → built-in format default → error.

**Fail-loud.** A binding that is **present** for the running language (bare or
explicit `_LANG.<self>`) and fails to **resolve** is an **error**; one that resolves and
then **raises** propagates. There is no silent fall-through to a different loader/fetcher.
The ladder falls through **only** to skip rungs that are *absent* for the running language
(e.g. another language's `_LANG.<other>` fetcher).

*Normative: [SCHEMA.md §Resolution semantics](../schema.md#resolution-semantics).*

**Cross-language fetch (rung 3)** is the rare case: a dataset whose bytes can be produced
only by a fetcher in another language. The running tool delegates (mechanism
implementation-defined; the Python CLI is the reference peer), controlled by `delegate` /
`--delegate`. Loading never delegates — a live object can't cross a process boundary.

*Normative: [SCHEMA.md §Cross-language fetch](../schema.md#cross-language-fetch-rung-3).*
