# Known inconsistencies — accepted, do not re-raise

Places where the manuscript deliberately differs from the implementation behind it. Each
entry was found, examined, and closed with a decision to keep the difference: the text is
written for a reader following the physics, and matching it word for word to the code
would cost more clarity than the precision it would buy. They are recorded here so a later
audit does not spend time rediscovering them, and so a reviewer question can be answered
from one place.

**This file is not a defect list.** Do not "fix" an entry, do not flag it in a review, and
do not add a caveat to the draft about it. A new finding of the same kind goes here only
after the author has decided to accept it; until then it belongs in `TODO.md`.

When this manuscript shares its model section with a sibling manuscript, the shared entries
are inherited from that manuscript's file of the same name, with this manuscript's
locations; a shared entry is added to both files, and the numbering is kept aligned.

<!--
Entry format (delete this comment once the file has a real entry):

## N. One-line statement of the difference

**The manuscript says** (Section x.y, Eq. (n)) ...

**The implementation** (file, function) ...

**Why it stands.** ...

Closed YYYY-MM-DD (author); inherited from <manuscript> YYYY-MM-DD if shared.
-->
