# knowledge-dump

A private wiki of markdown pages, plus an agent that files new notes into it.

## Language

**Vault**:
The git repo of markdown pages on the host (`~/notes`). SilverBullet serves it; the sandbox has a clone.
_Avoid_: Space, Wiki repo, Data repo

**Page**:
One markdown file in the Vault, named by its path without `.md`, e.g. `Cues/Change data capture`.
_Avoid_: Note (a Spark field in tab-squasher), Document

**Inbox**:
The `Inbox/` folder of the Vault. Every Page in it is an Item waiting to be filed. Not tab-squasher's Inbox, which is where Sparks arrive.
_Avoid_: Queue

**Item**:
One Page in the Inbox.
_Avoid_: Capture, Entry

**Triage**:
An hourly run in the sandbox: import new Sparks as Items, apply ticked Proposals, propose filing for new Items, file to-dos without a tick. Also the name of the Page listing the Proposals.

**Proposal**:
The agent's suggestion for one Item: file it into a Page (append a block) or discard it. Shown as a checkbox on the Triage page with an id like `kd:3f9a1c`.

**Parked**:
An Item left in the Inbox because you deleted its Proposal or the model had nothing usable. It's proposed again once its text changes.

**Cue**:
A note of the form "when I face X, consider Y", filed under `Cues/` and tagged `#cue`.

**Queue item**:
Something to read or research later. Triage files it on its topic page as a task tagged `#queue`, with the quote and source under it. The `Queue` page lists the open ones from every page.
_Avoid_: Reading list

**To-do**:
A Queue item for something to do or change, not just read. It carries a Why. One from a note starting with `Todo:` or `To-do:` is filed without waiting for a tick; one Triage judged a to-do from an unmarked note waits for a tick.

**Agent branch**:
`agent`, the only branch the sandbox may push to. A hook on the host merges it into `main`.
