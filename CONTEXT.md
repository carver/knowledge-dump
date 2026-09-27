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
An hourly run in the sandbox: import new Sparks as Items, apply ticked Proposals, propose filing for new Items. Also the name of the Page listing the Proposals.

**Proposal**:
The agent's suggestion for one Item: file it into a Page (append a block) or discard it. Shown as a checkbox on the Triage page with an id like `kd:3f9a1c`.

**Parked**:
An Item left in the Inbox because you deleted its Proposal or the model had nothing usable. It's proposed again once its text changes.

**Cue**:
A note of the form "when I face X, consider Y", filed under `Cues/` and tagged `#cue`.

**Agent branch**:
`agent`, the only branch the sandbox may push to. A hook on the host merges it into `main`.
