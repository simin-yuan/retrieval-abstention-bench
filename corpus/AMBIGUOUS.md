# Names deliberately left out of `entities.json`

`entities.json` scopes every entity to **one book**, and that resolves most ambiguity: a
bare first name is unambiguous *within* a book. `Jane` in *Pride and Prejudice* is Jane
Bennet; `Jane` in *Emma* is Jane Fairfax; `Fanny` in *Sense and Sensibility* is Fanny
Dashwood, `Fanny` in *Mansfield Park* is Fanny Price. Both are real, distinct entities, and
each is matched only inside its own book.

This file records the names that **cannot** be resolved this way and are therefore unused —
neither as an anchor nor as an answer.

## Excluded surface forms

| Form | Why it is unusable |
|---|---|
| `Miss Bennet` | In *Pride and Prejudice* this refers to Jane in some chapters and to Elizabeth in others — the eldest unmarried daughter changes as the sisters marry. |
| `Fitzwilliam` | Colonel Fitzwilliam in almost every occurrence, but it is also Darcy's given name. |
| `Bennet` | The family collective: Mr., Mrs., Jane, Elizabeth, Mary, Kitty and Lydia Bennet. |
| `Catherine` | Lady Catherine de Bourgh, but also Catherine "Kitty" Bennet. |
| `Crawford` | Henry and Mary Crawford, two people. Only the full names are used. |
| `Bertram` | Sir Thomas, Tom, Edmund, Maria and Julia Bertram. |
| `Dashwood` | Mrs. Dashwood, Elinor, Marianne, Margaret, John and Fanny Dashwood. |
| `Price` | Fanny, William and Susan Price, and Mrs. Price. |
| `Knightley` | George and John Knightley. Only `Mr. Knightley` and `John Knightley` are used. |
| `Palmer`, `Middleton`, `Grant`, `Steele`, `Ferrars`, `Lucas`, `Gardiner` | Two or more people share the surname and both are referred to by it. |
| `Smith`, `Taylor` (bare, in *Emma*) | Common surnames that also attach to minor and off-page characters. |
| `London`, `Bath`, `Brighton` | Each appears in more than one of the four books, and all three are also ordinary words. |
| `Parsonage`, `Park`, `Street`, `House` | Generic place words, not one place. |
| `Mr.`, `Mrs.`, `Miss`, `Sir`, `Lady`, `Colonel` | Honorifics, not entities. |
| every numeral, and every number spelled as a word, e.g. `ten thousand` | Numbers are written out inconsistently in the source text, so string matching on them is unreliable. No numeric entity is used. |

## Deliberate exceptions, kept as single entities

Where two people share a name and are a couple or a household that the text never treats as
separate anchors, the surname is kept as one entity and both referents count towards it:
`Weston` (Mr. and Mrs. Weston), `Elton` (Mr. and Mrs. Elton), `Bates` (Miss and Mrs.
Bates), `Collins`, `Jennings`, `Norris`, `Fairfax`, `Churchill`, `Rushworth`,
`Willoughby`, `Brandon`. Using them as anchors is still sound — the question is about "the
Westons", not about which Weston.

## Known residual limitations

- A handful of kept forms occur a few times outside their own book (`Edward` once in
  *Pride and Prejudice*, `Kitty` three times in *Emma*, `Elizabeth` 17 times across the
  other three books). Those occurrences are **not attributed** to any entity; the match is
  scoped to the book, so they are ignored rather than mis-counted.
- Within a book, a kept name is assumed to refer to that entity throughout. If a book uses
  a kept surname for a second, minor character — a servant, an innkeeper — those
  occurrences are counted with the entity. This is rare, and it only ever makes a
  distance *shorter*, which makes a relation-fake question harder to pass the distance
  check, never easier.
- Pronoun references are invisible to string matching. A relation-fake question can in
  principle be answered through a pronoun elsewhere in the corpus. See the limitations
  section of the README.
